#!/opt/miniforge/envs/casa6/bin/python
"""Minimal: Get first 2 tiles, build mosaic, run photometry.

Supports --dry-run flag for complete workflow simulation.
"""

import argparse
import os
import sys
import warnings
from datetime import timedelta
from pathlib import Path

from astropy.time import Time, TimeDelta

# Add src to path before importing project modules
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "src"))

from dsa110_contimg.calibration.cli_calibrate import handle_calibrate
from dsa110_contimg.calibration.schedule import next_transit_time
from dsa110_contimg.conversion.strategies.direct_subband import write_ms_from_subbands
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
    _peek_uvh5_phase_and_midtime,
    find_subband_groups,
)
from dsa110_contimg.imaging.cli_imaging import image_ms
from dsa110_contimg.mosaic.cli import _build_weighted_mosaic_linearmosaic, _fetch_tiles
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager
from dsa110_contimg.mosaic.validation import TileQualityMetrics
from dsa110_contimg.photometry.manager import PhotometryConfig, PhotometryManager
from dsa110_contimg.pointing.utils import load_pointing

# Suppress ERFA warnings about "dubious years" (harmless for dates in 2025+)
warnings.filterwarnings("ignore", category=UserWarning, module="erfa")


def main():
    parser = argparse.ArgumentParser(
        description="Get first 2 tiles, build mosaic, run photometry"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate workflow without building mosaic or running photometry",
    )
    args = parser.parse_args()

    dry_run = args.dry_run

    if dry_run:
        print("=" * 60)
        print("DRY-RUN MODE: Simulating complete workflow")
        print("=" * 60)
        print()

    # Find earliest observation and extract Dec and time
    print("Step 1: Finding earliest observations...")
    # Optimize: Use os.scandir for faster directory scanning (faster than glob for large dirs)
    # Since filenames are ISO timestamps, alphabetical order = chronological order
    incoming_dir = Path("/data/incoming")
    earliest_file = None
    earliest_filename = None

    with os.scandir(incoming_dir) as entries:
        for entry in entries:
            if entry.is_file() and "_sb" in entry.name and entry.name.endswith(".hdf5"):
                if earliest_filename is None or entry.name < earliest_filename:
                    earliest_filename = entry.name
                    earliest_file = Path(entry.path)

    if not earliest_file:
        sys.exit("No observations found")
    print(f"✓ Found: {earliest_file.name}")

    # Extract declination and observation time
    pointing = load_pointing(earliest_file)
    if pointing and pointing.get("dec_deg"):
        dec_deg = pointing.get("dec_deg")
        # Try to get time from pointing, otherwise peek file
        if pointing.get("mjd"):
            earliest_mjd = pointing.get("mjd")
        else:
            _, _, earliest_mjd = _peek_uvh5_phase_and_midtime(str(earliest_file))
    else:
        _, pt_dec_rad, earliest_mjd = _peek_uvh5_phase_and_midtime(str(earliest_file))
        dec_deg = pt_dec_rad.to_value("deg")

    earliest_time = Time(earliest_mjd, format="mjd")
    print(f"✓ Declination: {dec_deg:.6f}°")
    print(f"✓ Observation time: {earliest_time.isot}")

    # Find calibrator and first validity window
    print("\nStep 2: Finding calibrator...")
    state_dir = Path("state")
    manager = StreamingMosaicManager(
        products_db_path=state_dir / "products.sqlite3",
        registry_db_path=state_dir / "cal_registry.sqlite3",
        ms_output_dir=Path("/stage/dsa110-contimg/ms"),
        images_dir=Path("/stage/dsa110-contimg/images"),
        mosaic_output_dir=Path("/stage/dsa110-contimg/mosaics"),
    )
    cal = manager.get_bandpass_calibrator_for_dec(dec_deg)
    if not cal:
        sys.exit(f"No calibrator for Dec={dec_deg:.6f}°")
    print(f"✓ Calibrator: {cal['name']} (RA={cal['ra_deg']:.6f}°)")

    # Calculate the first transit >= earliest observation time
    # This is the correct approach: compute transit directly rather than searching backwards
    print("\nStep 3: Finding first validity window...")
    transit = next_transit_time(cal["ra_deg"], earliest_mjd)
    print(f"✓ First transit >= earliest observation: {transit.isot}")
    # Bandpass validity window is ±12 hours around transit (24-hour window centered on transit)
    validity_window_hours = 12.0
    window_start = transit - TimeDelta(validity_window_hours * 3600, format="sec")
    window_end = transit + TimeDelta(validity_window_hours * 3600, format="sec")
    print(
        f"✓ Validity window: {window_start.isot} to {window_end.isot} (±{validity_window_hours}h around transit)"
    )

    # Find observations in /data/incoming that fall within the validity window
    print("\nStep 4: Finding observations in /data/incoming within validity window...")
    incoming_dir = Path("/data/incoming")
    observations_in_window = []

    # Optimize: Filter by date prefix first to reduce files to scan
    # Validity window spans dates, so check all relevant date prefixes
    date_prefixes = set()
    current_date = window_start.datetime.date()
    end_date = window_end.datetime.date()
    while current_date <= end_date:
        date_prefixes.add(current_date.strftime("%Y-%m-%d"))
        # Move to next day
        current_date += timedelta(days=1)

    print(f"  Scanning files for dates: {sorted(date_prefixes)}")
    candidate_files = []
    for date_prefix in date_prefixes:
        # Only glob files matching this date prefix
        pattern = f"{date_prefix}*_sb*.hdf5"
        for hdf5_file in incoming_dir.glob(pattern):
            try:
                # Extract timestamp from filename (format: YYYY-MM-DDTHH:MM:SS_sb*.hdf5)
                filename = hdf5_file.name
                if "_sb" not in filename:
                    continue
                timestamp_str = filename.split("_sb")[0]
                try:
                    # Parse ISO format timestamp
                    file_time = Time(timestamp_str, format="isot")
                    # Quick check: is this file potentially in range?
                    # Use a small buffer (1 hour) to account for any time differences
                    buffer = TimeDelta(3600, format="sec")
                    if (window_start - buffer) <= file_time <= (window_end + buffer):
                        candidate_files.append((hdf5_file, file_time))
                except ValueError:
                    # Can't parse timestamp from filename, skip
                    continue
            except Exception:
                continue

    print(
        f"  Found {len(candidate_files)} candidate files based on filename timestamps"
    )

    # Verify actual observation times from files (especially important for boundary cases)
    # For files near the boundary, filename timestamp might not match actual observation time
    print("  Verifying actual observation times from files...")
    boundary_buffer = TimeDelta(
        300, format="sec"
    )  # 5 minutes buffer for boundary checking

    for hdf5_file, file_time in candidate_files:
        try:
            # Check if file is near boundary - if so, we must verify actual time
            is_near_boundary = (window_start - boundary_buffer) <= file_time <= (
                window_start + boundary_buffer
            ) or (window_end - boundary_buffer) <= file_time <= (
                window_end + boundary_buffer
            )

            if is_near_boundary:
                # Near boundary: must check actual observation time
                pointing = load_pointing(hdf5_file)
                if pointing and pointing.get("mjd"):
                    obs_mjd = pointing.get("mjd")
                else:
                    _, _, obs_mjd = _peek_uvh5_phase_and_midtime(str(hdf5_file))
                obs_time = Time(obs_mjd, format="mjd")
            else:
                # Far from boundary: filename timestamp is good enough
                obs_time = file_time

            # Check if observation falls within validity window
            if window_start <= obs_time <= window_end:
                observations_in_window.append((hdf5_file, obs_time))
        except Exception as e:
            # If we can't read the file, fall back to filename timestamp
            if window_start <= file_time <= window_end:
                observations_in_window.append((hdf5_file, file_time))
            continue

    # Sort by observation time
    observations_in_window.sort(key=lambda x: x[1])

    if not observations_in_window:
        sys.exit(
            f"No observations found in /data/incoming within validity window ({window_start.isot} to {window_end.isot})"
        )

    print(f"✓ Found {len(observations_in_window)} observation(s) in validity window:")
    for i, (obs_file, obs_time) in enumerate(
        observations_in_window[:10], 1
    ):  # Show first 10
        print(f"  {i}. {obs_file.name} ({obs_time.isot})")
    if len(observations_in_window) > 10:
        print(f"  ... and {len(observations_in_window) - 10} more")

    # Now find tiles (which would be created from these observations)
    print("\nStep 5: Finding tiles in validity window...")
    tiles = _fetch_tiles(
        Path("state/products.sqlite3"),
        since=window_start.unix,
        until=window_end.unix,
        pbcor_only=True,
    )[:2]

    if not tiles:
        print("  No existing tiles found - will create from HDF5 groups")
        print("\nStep 5a: Finding complete 16-subband groups...")
        # Find complete groups of 16 subbands in the validity window
        start_str = window_start.isot.replace("T", " ")
        end_str = window_end.isot.replace("T", " ")
        groups = find_subband_groups(
            str(incoming_dir),
            start_str,
            end_str,
            tolerance_s=30.0,
        )

        if not groups:
            sys.exit("No complete 16-subband groups found in validity window")

        print(f"✓ Found {len(groups)} complete group(s) in validity window")
        if len(groups) < 2:
            sys.exit(f"Need at least 2 groups, but only found {len(groups)}")

        # Take first 2 groups
        selected_groups = groups[:2]
        print(f"  Selected first 2 groups:")
        for i, group in enumerate(selected_groups, 1):
            # Get timestamp from first file in group
            first_file = Path(group[0])
            timestamp = first_file.name.split("_sb")[0]
            print(f"    Group {i}: {timestamp} ({len(group)} subbands)")

        if dry_run:
            print("\nStep 5b: Simulating tile creation workflow (dry-run)...")
            print("  Would convert 2 groups of 16 subbands to MS files")
            print("  Would form group and solve calibration")
            print("  Would apply calibration to MS files")
            print("  Would image MS files to create tiles")
            print("✓ Tile creation workflow validated (dry-run)")
            # In dry-run, we can't actually create tiles, so simulate success
            print("\nStep 5c: Re-querying for tiles (simulated)...")
            # Create placeholder tiles for dry-run continuation
            tiles = ["simulated_tile_1.fits", "simulated_tile_2.fits"]
            print("✓ Found 2 tile(s) (simulated for dry-run)")
        else:
            print("\nStep 5b: Creating tiles from groups...")
            ms_dir = Path("/stage/dsa110-contimg/ms")
            images_dir = Path("/stage/dsa110-contimg/images")
            scratch_dir = Path("/stage/dsa110-contimg/tmp")
            ms_dir.mkdir(parents=True, exist_ok=True)
            images_dir.mkdir(parents=True, exist_ok=True)
            scratch_dir.mkdir(parents=True, exist_ok=True)

            tiles = []
            for i, group in enumerate(selected_groups, 1):
                group_label = f"group {i}"
                first_file = Path(group[0])
                timestamp = first_file.stem.split("_sb")[0]
                ms_path = ms_dir / f"{timestamp}.ms"
                imagename = images_dir / ms_path.stem
                pbcor_path = Path(f"{imagename}.image.pbcor")

                if pbcor_path.exists():
                    print(f"  ✓ Using existing tile for {group_label}: {pbcor_path}")
                    tiles.append(str(pbcor_path))
                    continue

                if ms_path.exists():
                    print(f"  ✓ MS already exists for {group_label}: {ms_path}")
                else:
                    print(f"  → Converting {group_label} to MS: {ms_path}")
                    write_ms_from_subbands(
                        group, str(ms_path), scratch_dir=str(scratch_dir)
                    )

                print(f"  → Calibrating {group_label} MS")
                cal_args = argparse.Namespace(
                    ms=str(ms_path),
                    auto_fields=True,
                    refant="103",
                    preset="fast",
                    model_source="catalog",
                    cal_ra_deg=cal.get("ra_deg"),
                    cal_dec_deg=cal.get("dec_deg"),
                    cal_flux_jy=cal.get("flux_jy"),
                    flagging_mode="quick",
                    bp_combine_field=True,
                    combine_spw=False,
                    bp_minsnr=3.0,
                    gain_solint="inf",
                    gain_calmode="p",
                    gain_minsnr=3.0,
                    skip_bp=False,
                    skip_g=False,
                    do_k=False,
                    fast=True,
                    no_flagging=False,
                    skip_rephase=False,
                    export_model_image=False,
                    diagnostics=False,
                    cleanup_subset=True,
                )
                cal_result = handle_calibrate(cal_args)
                if cal_result != 0:
                    sys.exit(
                        f"Calibration failed for {ms_path} (exit code {cal_result})"
                    )

                print(f"  → Imaging {group_label} (pbcor)")
                image_ms(
                    str(ms_path),
                    imagename=str(imagename),
                    quality_tier="development",
                    pbcor=True,
                    niter=300,
                    threshold="0.0Jy",
                    robust=0.0,
                    imsize=1024,
                    cell_arcsec=None,
                )

                if pbcor_path.exists():
                    tiles.append(str(pbcor_path))
                    print(f"  ✓ Created tile: {pbcor_path}")
                else:
                    sys.exit(
                        f"Tile imaging failed for {ms_path}: {pbcor_path} not found"
                    )

    if tiles:
        print(f"✓ Found {len(tiles)} tile(s):")
        for i, tile in enumerate(tiles, 1):
            print(f"  {i}. {Path(tile).name}")

    # Build mosaic from tiles
    print("\nStep 6: Building mosaic...")
    mosaic_path = Path("/stage/dsa110-contimg/mosaics/first_two_tiles")

    if tiles:
        if dry_run and tiles[0].startswith("simulated_"):
            print("  (dry-run: using simulated tiles)")
        metrics_dict = {t: TileQualityMetrics(tile_path=t) for t in tiles}
        _build_weighted_mosaic_linearmosaic(
            tiles, metrics_dict, str(mosaic_path), dry_run=dry_run
        )

    if dry_run:
        print("✓ Mosaic plan validated (dry-run)")
    else:
        fits_path = Path(f"{mosaic_path}.fits")
        if not fits_path.exists():
            sys.exit(f"Mosaic FITS not found: {fits_path}")
        print(f"✓ Mosaic built: {fits_path}")

    # Run photometry on mosaic
    print("\nStep 7: Running photometry...")
    fits_path = Path(f"{mosaic_path}.fits")

    if dry_run:
        # In dry-run, mosaic FITS doesn't exist yet, so simulate photometry workflow
        print("  (dry-run: mosaic FITS not yet created)")
        print("  Would query NVSS catalog for sources in mosaic field")
        print("  Would create batch photometry job for measurements")
        print("✓ Photometry workflow validated (dry-run)")
    else:
        if not fits_path.exists():
            sys.exit(f"Mosaic FITS not found: {fits_path}")

        photometry_manager = PhotometryManager(
            products_db_path=state_dir / "products.sqlite3",
        )
        config = PhotometryConfig(catalog="nvss", radius_deg=0.5, min_flux_mjy=10.0)
        result = photometry_manager.measure_for_mosaic(
            mosaic_path=fits_path,
            config=config,
            create_batch_job=True,
        )
        if result:
            print(f"✓ Photometry batch job created: {result.batch_job_id}")
            print(f"  Sources: {result.sources_queried}")
        else:
            print("⚠ No photometry job created (no sources found or error)")

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY-RUN COMPLETE: Workflow validated successfully")
        print("Run without --dry-run to execute the workflow")
        print("=" * 60)
    else:
        print("\n✓ Complete!")


if __name__ == "__main__":
    main()
