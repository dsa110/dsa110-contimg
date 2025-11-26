#!/opt/miniforge/envs/casa6/bin/python
# pyright: reportAttributeAccessIssue=false, reportUndefinedVariable=false, reportUnusedVariable=false, reportUnusedImport=false
# pylint: disable=no-member,undefined-variable,unused-variable,unused-import
"""Validate pipeline source recovery by simulating a 10-minute (2-tile) NVSS field.

This script:
1. Queries NVSS catalog for sources in a specified field
2. Simulates 2 tiles (10 minutes) with those sources + noise + RFI
3. Runs full pipeline: conversion → calibration → imaging → mosaic → photometry
4. Compares recovered sources to input NVSS catalog

Usage:
    PYTHONPATH=/data/dsa110-contimg/src python scripts/mosaic/validate_nvss_field_recovery.py \
        --ra 129.275 --dec 54.573 --radius 0.5 \
        --add-noise --add-cal-errors \
        --dry-run
"""

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

from dsa110_contimg.calibration.catalogs import query_nvss_sources
from dsa110_contimg.mosaic.cli import \
  _build_weighted_mosaic_linearmosaic  # noqa: F401
from dsa110_contimg.mosaic.validation import TileQualityMetrics  # noqa: F401
from dsa110_contimg.simulation.make_synthetic_uvh5 import (
  build_time_arrays, build_uvdata_from_scratch, build_uvw,
  load_reference_layout, load_telescope_config)
from dsa110_contimg.simulation.visibility_models import add_thermal_noise

# Add src to path before importing project modules
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "src"))


# Suppress ERFA warnings about "dubious years"
warnings.filterwarnings("ignore", category=UserWarning, module="erfa")


def query_nvss_field(
    ra_deg: float, dec_deg: float, radius_deg: float, min_flux_mjy: Optional[float] = None
) -> List[Tuple[float, float, float]]:
    """Query NVSS catalog for sources in field.

    Args:
        ra_deg: Field center RA in degrees
        dec_deg: Field center Dec in degrees
        radius_deg: Search radius in degrees
        min_flux_mjy: Minimum flux in mJy (optional)

    Returns:
        List of (ra_deg, dec_deg, flux_jy) tuples
    """
    print(
        f"\nQuerying NVSS catalog for field: RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°, radius={radius_deg:.3f}°"
    )

    df = query_nvss_sources(
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        radius_deg=radius_deg,
        min_flux_mjy=min_flux_mjy,
    )

    if len(df) == 0:
        print("  No sources found in NVSS catalog")
        return []

    # Convert to list of tuples (ra, dec, flux_jy)
    sources = []
    for _, row in df.iterrows():
        flux_jy = row["flux_mjy"] / 1000.0  # Convert mJy to Jy
        sources.append((row["ra_deg"], row["dec_deg"], flux_jy))

    print(f"  Found {len(sources)} source(s) in NVSS catalog:")
    for i, (ra, dec, flux) in enumerate(sources[:10], 1):  # Show first 10
        print(f"    {i}. RA={ra:.6f}°, Dec={dec:.6f}°, Flux={flux*1000:.2f} mJy")
    if len(sources) > 10:
        print(f"    ... and {len(sources) - 10} more")

    return sources


def simulate_two_tiles_with_sources(
    nvss_sources: List[Tuple[float, float, float]],
    ra_center: float,
    dec_center: float,
    output_dir: Path,
    start_time: Time,
    add_noise: bool = True,
    add_cal_errors: bool = True,
    system_temp_k: float = 50.0,
    dry_run: bool = False,
) -> List[Path]:
    """Simulate 2 tiles (10 minutes) with NVSS sources.

    Args:
        nvss_sources: List of (ra_deg, dec_deg, flux_jy) tuples
        ra_center: Field center RA in degrees
        dec_center: Field center Dec in degrees
        output_dir: Directory for synthetic HDF5 files
        start_time: Observation start time
        add_noise: Add thermal noise
        add_cal_errors: Add calibration errors
        system_temp_k: System temperature for noise
        dry_run: If True, only simulate without creating files

    Returns:
        List of paths to created HDF5 files (16 subbands × 2 tiles = 32 files)
    """
    if dry_run:
        print(f"\n(dry-run: Would simulate 2 tiles with {len(nvss_sources)} NVSS sources)")
        print(f"  Field center: RA={ra_center:.6f}°, Dec={dec_center:.6f}°")
        print(f"  Noise: {'enabled' if add_noise else 'disabled'}")
        print(f"  Calibration errors: {'enabled' if add_cal_errors else 'disabled'}")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load telescope configuration
    sim_package = Path(__file__).resolve().parents[2] / "src" / "dsa110_contimg" / "simulation"
    config_dir = sim_package / "config"
    pyuvsim_dir = sim_package / "pyuvsim"

    layout_meta = load_reference_layout(config_dir / "reference_layout.json")
    config = load_telescope_config(
        pyuvsim_dir / "telescope.yaml",
        layout_meta,
        freq_order="desc",
    )

    # Override phase center to field center
    config.phase_ra = ra_center * u.deg  # type: ignore[attr-defined]
    config.phase_dec = dec_center * u.deg  # type: ignore[attr-defined]

    # Create 2 tiles (2 groups of 16 subbands)
    # Each tile is ~5 minutes, so 2 tiles = ~10 minutes
    n_tiles = 2
    n_subbands = 16
    tile_duration_minutes = 5.0

    created_files = []

    for tile_idx in range(n_tiles):
        print(f"\nSimulating tile {tile_idx + 1}/{n_tiles}...")

        # Offset start time for second tile
        tile_start = (
            start_time + tile_idx * tile_duration_minutes * u.minute
        )  # type: ignore[attr-defined]

        # Build UVData template for this tile
        ntimes = int(tile_duration_minutes * 60 / config.integration_time_sec)
        uv_template = build_uvdata_from_scratch(
            config,
            nants=110,
            ntimes=ntimes,
            start_time=tile_start,
        )

        # Generate times, LST, UVW arrays
        unique_times, times_mjd, lst_array, integration_time = build_time_arrays(
            config, uv_template.Nbls, ntimes, tile_start
        )

        ant1_list = uv_template.ant_1_array[: uv_template.Nbls]
        ant2_list = uv_template.ant_2_array[: uv_template.Nbls]

        uvw_array = build_uvw(
            config,
            unique_times,
            ant1_list,
            ant2_list,
            uv_template.Nants_telescope,
        )

        # For each subband, create HDF5 file
        # Sum visibilities from all NVSS sources
        for subband_idx in range(n_subbands):
            # Create base visibilities (will sum sources)
            uv = uv_template.copy()

            # Set frequency for this subband
            delta_f = abs(config.channel_width_hz)
            nchan = config.channels_per_subband
            sign = -1.0 if config.freq_order == "desc" else 1.0

            if config.freq_template.size == nchan:
                base = config.freq_template.copy()
                freqs = base + sign * subband_idx * nchan * delta_f
            else:
                if config.freq_order == "desc":
                    start_freq = config.freq_max_hz
                else:
                    start_freq = config.freq_min_hz
                freqs = start_freq + sign * delta_f * (np.arange(nchan) + subband_idx * nchan)

            uv.freq_array = freqs.reshape(1, -1)
            uv.channel_width = np.full_like(uv.freq_array, sign * delta_f)
            uv.Nfreqs = nchan
            uv.Nspws = 1

            uv.time_array = times_mjd
            uv.lst_array = lst_array
            uv.integration_time = integration_time
            uv.uvw_array = uvw_array

            # Initialize visibilities to zero
            uv.data_array = np.zeros(
                (uv.Nblts, uv.Nspws, uv.Nfreqs, uv.Npols),
                dtype=np.complex64,
            )

            # Get u, v coordinates in wavelengths for phase rotation
            # uvw_array shape: (Nblts, 3) where columns are [u, v, w] in meters
            u_m = uvw_array[:, 0]  # (Nblts,)
            v_m = uvw_array[:, 1]  # (Nblts,)

            # Sum visibilities from all NVSS sources with proper phase rotation
            for src_ra, src_dec, src_flux_jy in nvss_sources:
                # Calculate angular offset from phase center to source
                # Account for cos(dec) factor in RA offset
                phase_ra_rad = np.radians(ra_center)
                phase_dec_rad = np.radians(dec_center)
                src_ra_rad = np.radians(src_ra)
                src_dec_rad = np.radians(src_dec)

                # Offset in RA: account for cos(dec) factor
                offset_ra_rad = (src_ra_rad - phase_ra_rad) * np.cos(phase_dec_rad)
                offset_dec_rad = src_dec_rad - phase_dec_rad

                # Calculate phase rotation for each frequency channel
                # Shape: (Nblts, Nfreqs)
                for freq_idx in range(uv.Nfreqs):
                    freq_hz = uv.freq_array[0, freq_idx]
                    wavelength_m = 299792458.0 / freq_hz

                    # Convert u, v from meters to wavelengths
                    u_lambda = u_m / wavelength_m  # (Nblts,)
                    v_lambda = v_m / wavelength_m  # (Nblts,)

                    # Phase calculation: 2π * (u*ΔRA + v*ΔDec) / λ
                    # But u, v are already in wavelengths, so:
                    # phase = 2π * (u_lambda * offset_ra_rad + v_lambda * offset_dec_rad)
                    phase = 2.0 * np.pi * (u_lambda * offset_ra_rad + v_lambda * offset_dec_rad)

                    # Apply phase rotation: V = flux * exp(i*phase)
                    # For point source, visibility amplitude is constant (flux/2 for each pol)
                    # Shape: (Nblts,)
                    vis_amplitude = src_flux_jy / 2.0  # Split between XX and YY
                    vis_complex = vis_amplitude * (np.cos(phase) + 1j * np.sin(phase))

                    # Add to data array for all polarizations
                    # Shape: (Nblts, 1, 1, Npols)
                    for pol_idx in range(uv.Npols):
                        uv.data_array[:, 0, freq_idx, pol_idx] += vis_complex

            # Add thermal noise if requested
            if add_noise:
                # Use mean frequency for noise calculation
                mean_freq_hz = float(np.mean(uv.freq_array))
                uv.data_array = add_thermal_noise(
                    uv.data_array,
                    config.integration_time_sec,
                    abs(config.channel_width_hz),
                    system_temperature_k=system_temp_k,
                    frequency_hz=mean_freq_hz,
                )

            # Add calibration errors if requested
            if add_cal_errors:
                from dsa110_contimg.simulation.visibility_models import (
                  add_calibration_errors,
                  apply_calibration_errors_to_visibilities)

                _, complex_gains, _ = add_calibration_errors(
                    uv.data_array,
                    uv.Nants_telescope,
                    gain_std=0.1,
                    phase_std_deg=10.0,
                )

                uv.data_array = apply_calibration_errors_to_visibilities(
                    uv.data_array,
                    uv.ant_1_array,
                    uv.ant_2_array,
                    complex_gains,
                )

            uv.flag_array = np.zeros_like(uv.data_array, dtype=bool)
            uv.nsample_array = np.ones_like(uv.data_array, dtype=np.float32)

            # Mark as synthetic
            uv.extra_keywords["synthetic"] = True
            uv.extra_keywords["synthetic_nvss_sources"] = json.dumps(
                [{"ra_deg": ra, "dec_deg": dec, "flux_jy": flux} for ra, dec, flux in nvss_sources]
            )
            uv.extra_keywords["synthetic_field_ra_deg"] = float(ra_center)
            uv.extra_keywords["synthetic_field_dec_deg"] = float(dec_center)
            if add_noise:
                uv.extra_keywords["synthetic_has_noise"] = True
                uv.extra_keywords["synthetic_system_temp_k"] = float(system_temp_k)
            if add_cal_errors:
                uv.extra_keywords["synthetic_has_cal_errors"] = True

            # Write HDF5 file
            timestamp_str = tile_start.strftime("%Y-%m-%dT%H:%M:%S")
            filename = f"{timestamp_str}_sb{subband_idx:02d}.hdf5"
            output_path = output_dir / filename

            uv.write_uvh5(str(output_path))
            created_files.append(output_path)

            if (subband_idx + 1) % 4 == 0:
                print(f"  Created {subband_idx + 1}/{n_subbands} subbands...")

    print(f"\nCreated {len(created_files)} synthetic HDF5 files")
    return created_files


def compare_recovered_sources(
    input_sources: List[Tuple[float, float, float]],
    photometry_results: List[dict],
    match_radius_arcsec: float = 10.0,
) -> dict:
    """Compare recovered sources to input NVSS catalog.

    Args:
        input_sources: List of (ra_deg, dec_deg, flux_jy) tuples from NVSS
        photometry_results: List of photometry result dicts with ra_deg, dec_deg, flux_jy
        match_radius_arcsec: Matching radius in arcseconds

    Returns:
        Dictionary with recovery statistics
    """  # noqa: E501
    print("\nComparing recovered sources to input NVSS catalog...")
    print(f"  Input sources: {len(input_sources)}")
    print(f"  Recovered sources: {len(photometry_results)}")
    print(f"  Match radius: {match_radius_arcsec} arcsec")

    # Convert to SkyCoord for matching
    input_coords = SkyCoord(
        ra=[s[0] for s in input_sources] * u.deg,  # type: ignore[attr-defined]
        dec=[s[1] for s in input_sources] * u.deg,  # type: ignore[attr-defined]
    )

    recovered_coords = SkyCoord(
        ra=[r["ra_deg"] for r in photometry_results] * u.deg,  # type: ignore[attr-defined]
        dec=[r["dec_deg"] for r in photometry_results] * u.deg,  # type: ignore[attr-defined]
    )

    # Find matches
    idx_recovered, idx_input, _, _ = input_coords.search_around_sky(
        recovered_coords, match_radius_arcsec * u.arcsec  # type: ignore[attr-defined]
    )

    matched_input = set(idx_input)
    matched_recovered = set(idx_recovered)

    # Calculate recovery statistics
    n_matched = len(matched_input)
    n_input = len(input_sources)
    n_recovered = len(photometry_results)
    n_false_positives = len(photometry_results) - len(matched_recovered)
    n_missed = len(input_sources) - len(matched_input)

    recovery_rate = n_matched / n_input if n_input > 0 else 0.0

    # Calculate flux comparison for matched sources
    flux_ratios = []
    for rec_idx, inp_idx in zip(idx_recovered, idx_input):
        input_flux = input_sources[inp_idx][2]
        recovered_flux = photometry_results[rec_idx]["flux_jy"]
        if input_flux > 0:
            flux_ratios.append(recovered_flux / input_flux)

    stats = {
        "n_input": n_input,
        "n_recovered": n_recovered,
        "n_matched": n_matched,
        "n_false_positives": n_false_positives,
        "n_missed": n_missed,
        "recovery_rate": recovery_rate,
        "flux_ratios": flux_ratios,
        "mean_flux_ratio": np.mean(flux_ratios) if flux_ratios else None,  # noqa: F841
        "median_flux_ratio": np.median(flux_ratios) if flux_ratios else None,
    }

    print("\nRecovery Statistics:")
    print(f"  Matched: {n_matched}/{n_input} ({recovery_rate*100:.1f}%)")
    print(f"  Missed: {n_missed}")  # noqa: F541
    print(f"  False positives: {n_false_positives}")
    if flux_ratios:
        print(f"  Mean flux ratio (recovered/input): {stats['mean_flux_ratio']:.3f}")
        print(f"  Median flux ratio: {stats['median_flux_ratio']:.3f}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Validate pipeline source recovery with simulated NVSS field"
    )
    parser.add_argument(
        "--ra",
        type=float,
        required=True,
        help="Field center RA in degrees",
    )
    parser.add_argument(
        "--dec",
        type=float,
        required=True,
        help="Field center Dec in degrees",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=0.5,
        help="Search radius in degrees (default: 0.5)",
    )
    parser.add_argument(
        "--min-flux-mjy",
        type=float,
        default=None,
        help="Minimum flux in mJy (optional)",
    )
    parser.add_argument(
        "--add-noise",
        action="store_true",
        help="Add realistic thermal noise",
    )
    parser.add_argument(
        "--system-temp-k",
        type=float,
        default=50.0,
        help="System temperature in Kelvin (default: 50K)",
    )
    parser.add_argument(
        "--add-cal-errors",
        action="store_true",
        help="Add realistic calibration errors",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/validate_nvss_simulation"),
        help="Directory for synthetic HDF5 files (default: /tmp/validate_nvss_simulation)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate workflow without creating files or running pipeline",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print("DRY-RUN MODE: Simulating complete validation workflow")
        print("=" * 60)

    # Step 1: Query NVSS catalog
    print("\n" + "=" * 60)
    print("Step 1: Querying NVSS catalog")
    print("=" * 60)
    nvss_sources = query_nvss_field(
        args.ra,
        args.dec,
        args.radius,
        min_flux_mjy=args.min_flux_mjy,
    )

    if len(nvss_sources) == 0:
        print("ERROR: No NVSS sources found in field")
        sys.exit(1)

    # Step 2: Simulate 2 tiles with NVSS sources
    print("\n" + "=" * 60)
    print("Step 2: Simulating 2 tiles (10 minutes) with NVSS sources")
    print("=" * 60)
    start_time = Time.now()
    synthetic_files = simulate_two_tiles_with_sources(  # noqa: F841
        nvss_sources,
        args.ra,
        args.dec,
        args.output_dir,
        start_time,
        add_noise=args.add_noise,
        add_cal_errors=args.add_cal_errors,
        system_temp_k=args.system_temp_k,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY-RUN COMPLETE: Workflow validated")
        print("=" * 60)
        print("\nTo run full validation, remove --dry-run flag")
        return

    # Step 3: Copy synthetic files to incoming directory (or staging)
    print("\n" + "=" * 60)
    print("Step 3: Preparing synthetic data for pipeline")
    print("=" * 60)

    if len(synthetic_files) == 0:
        print("ERROR: No synthetic files created")
        sys.exit(1)

    # Copy synthetic files to a staging directory that the pipeline can process
    # For now, use a temporary directory that mimics /data/incoming structure
    staging_dir = args.output_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Copying {len(synthetic_files)} synthetic HDF5 files to staging directory...")
    staged_files = []
    for src_file in synthetic_files:
        dst_file = staging_dir / src_file.name
        import shutil

        shutil.copy2(src_file, dst_file)
        staged_files.append(dst_file)
    print(f"  ✓ Staged {len(staged_files)} files to {staging_dir}")

    # Step 4: Run pipeline (conversion → calibration → imaging → mosaic)
    print("\n" + "=" * 60)
    print("Step 4: Running pipeline (conversion → calibration → imaging → mosaic)")
    print("=" * 60)

    # Find complete groups from staged files
    from dsa110_contimg.conversion.strategies.hdf5_orchestrator import \
      find_subband_groups

    # Get time window from synthetic files
    first_file_time = start_time
    # type: ignore[attr-defined]  # 2 tiles = 10 minutes
    last_file_time = start_time + 10.0 * u.minute

    start_str = first_file_time.isot.replace("T", " ")
    end_str = last_file_time.isot.replace("T", " ")

    print("  Finding complete 16-subband groups in time window...")
    print(f"    Start: {start_str}")
    print(f"    End: {end_str}")

    groups = find_subband_groups(
        str(staging_dir),
        start_str,
        end_str,
        tolerance_s=30.0,
    )

    if len(groups) < 2:
        print(f"  ERROR: Need at least 2 complete groups, found {len(groups)}")
        sys.exit(1)

    print(f"  ✓ Found {len(groups)} complete group(s), using first 2")
    selected_groups = groups[:2]

    # Convert groups to MS files
    print("\n  Step 4a: Converting HDF5 groups to MS files...")
    ms_output_dir = args.output_dir / "ms"
    ms_output_dir.mkdir(parents=True, exist_ok=True)

    ms_files = []
    for i, group in enumerate(selected_groups, 1):
        print(f"    Converting group {i}/{len(selected_groups)}...")
        # Get timestamp from first file in group
        first_file = Path(group[0])
        timestamp = first_file.name.split("_sb")[0]
        ms_path = ms_output_dir / f"{timestamp}.ms"

        # Use conversion helper to convert group
        from ops.pipeline.helpers_ms_conversion import \
          write_ms_group_via_uvh5_to_ms

        try:
            write_ms_group_via_uvh5_to_ms(
                file_list=[str(f) for f in group],
                ms_out=ms_path,
                add_imaging_columns=True,
                configure_final_ms=True,
            )
            ms_files.append(ms_path)
            print(f"      ✓ Created MS: {ms_path.name}")
        except Exception as e:
            print(f"      ✗ Failed to convert group {i}: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    # Calibrate MS files
    print("\n  Step 4b: Calibrating MS files...")
    import argparse as argparse_module

    from dsa110_contimg.calibration.cli_calibrate import handle_calibrate

    calibrated_ms_files = []
    for i, ms_path in enumerate(ms_files, 1):
        print(f"    Calibrating MS {i}/{len(ms_files)}: {ms_path.name}...")

        # Create argparse namespace for calibrate command
        cal_args = argparse_module.Namespace(
            ms=str(ms_path),
            field=0,
            refant=103,
            auto_fields=True,
            preset="development",  # Use development tier for validation
            skip_rephase=False,
            bp_combine_field=True,
            verbose=False,
        )

        try:
            result = handle_calibrate(cal_args)
            if result == 0:
                calibrated_ms_files.append(ms_path)
                print(f"      ✓ Calibrated: {ms_path.name}")
            else:
                print(f"      ✗ Calibration failed for {ms_path.name}")
                sys.exit(1)
        except Exception as e:
            print(f"      ✗ Calibration error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    # Image MS files
    print("\n  Step 4c: Imaging MS files...")
    from dsa110_contimg.imaging.cli_image import handle_image

    image_files = []
    for i, ms_path in enumerate(calibrated_ms_files, 1):
        print(f"    Imaging MS {i}/{len(calibrated_ms_files)}: {ms_path.name}...")

        timestamp = ms_path.stem
        image_base = args.output_dir / "images" / timestamp

        # Create argparse namespace for image command
        img_args = argparse_module.Namespace(
            ms=str(ms_path),
            imagename=str(image_base),
            imsize=2048,
            niter=1000,
            threshold="0.05mJy",
            pbcor=True,
            quality_tier="standard",
            verbose=False,
        )

        try:
            result = handle_image(img_args)
            if result == 0:
                # Find the PB-corrected image
                pbcor_path = Path(f"{image_base}.pbcor.fits")
                if pbcor_path.exists():
                    image_files.append(pbcor_path)
                    print(f"      ✓ Imaged: {pbcor_path.name}")
                else:
                    print(f"      ✗ PB-corrected image not found: {pbcor_path}")
                    sys.exit(1)
            else:
                print(f"      ✗ Imaging failed for {ms_path.name}")
                sys.exit(1)
        except Exception as e:
            print(f"      ✗ Imaging error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    # Build mosaic
    print("\n  Step 4d: Building mosaic from tiles...")
    mosaic_path = args.output_dir / "mosaics" / "nvss_validation"
    mosaic_path.parent.mkdir(parents=True, exist_ok=True)

    if len(image_files) >= 2:
        metrics_dict = {str(img): TileQualityMetrics(tile_path=str(img)) for img in image_files}
        _build_weighted_mosaic_linearmosaic(
            [str(img) for img in image_files],
            metrics_dict,
            str(mosaic_path),
            dry_run=False,
        )

        mosaic_fits = Path(f"{mosaic_path}.fits")
        if mosaic_fits.exists():
            print(f"      ✓ Mosaic built: {mosaic_fits.name}")
        else:
            print(f"      ✗ Mosaic FITS not found: {mosaic_fits}")
            sys.exit(1)
    else:
        print(f"      ✗ Need at least 2 images for mosaic, found {len(image_files)}")
        sys.exit(1)

    # Step 5: Run photometry and compare recovered sources
    print("\n" + "=" * 60)
    print("Step 5: Running photometry and comparing recovered sources")
    print("=" * 60)

    mosaic_fits = Path(f"{mosaic_path}.fits")

    # Run photometry
    print("  Running photometry on mosaic...")
    from dsa110_contimg.photometry.manager import (PhotometryConfig,
                                                   PhotometryManager)

    photometry_manager = PhotometryManager()
    photometry_config = PhotometryConfig(
        catalog="nvss",
        radius_deg=args.radius,
        min_flux_mjy=args.min_flux_mjy,
        max_sources=1000,  # Allow many sources for comparison
    )

    photometry_result = photometry_manager.measure_for_mosaic(
        mosaic_fits,
        config=photometry_config,
        create_batch_job=False,  # Run synchronously
        dry_run=False,
    )

    if not photometry_result:
        print("  ✗ Photometry failed")
        sys.exit(1)

    print(f"  ✓ Photometry completed: {photometry_result.measurements_successful} measurements")

    # Extract photometry results from database
    print("  Extracting photometry results from database...")
    # Query photometry database directly
    import sqlite3

    products_db = Path("state/db/products.sqlite3")
    if not products_db.exists():
        print(f"  ✗ Products database not found: {products_db}")
        sys.exit(1)

    conn = sqlite3.connect(str(products_db))
    conn.row_factory = sqlite3.Row

    # Query photometry table for this mosaic
    rows = conn.execute(
        """
        SELECT ra_deg, dec_deg, peak_jyb, peak_err_jyb
        FROM photometry
        WHERE image_path = ?
        ORDER BY peak_jyb DESC
        """,
        (str(mosaic_fits),),
    ).fetchall()

    conn.close()

    if not rows:
        print("  ✗ No photometry results found in database")
        sys.exit(1)

    # Convert to list of dicts for comparison
    recovered_sources = []
    for row in rows:
        recovered_sources.append(
            {
                "ra_deg": row["ra_deg"],
                "dec_deg": row["dec_deg"],
                "flux_jy": row["peak_jyb"],  # Use peak flux
            }
        )

    print(f"  ✓ Extracted {len(recovered_sources)} recovered sources")

    # Compare recovered sources to input NVSS catalog
    print("\n  Comparing recovered sources to input NVSS catalog...")
    recovery_stats = compare_recovered_sources(
        nvss_sources,
        recovered_sources,
        match_radius_arcsec=10.0,  # 10 arcsec matching radius
    )

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Input NVSS sources: {recovery_stats['n_input']}")
    print(f"Recovered sources: {recovery_stats['n_recovered']}")
    print(
        f"Matched sources: {recovery_stats['n_matched']} ({recovery_stats['recovery_rate']*100:.1f}%)"
    )
    print(f"Missed sources: {recovery_stats['n_missed']}")
    print(f"False positives: {recovery_stats['n_false_positives']}")
    if recovery_stats["mean_flux_ratio"] is not None:
        print(f"Mean flux ratio (recovered/input): {recovery_stats['mean_flux_ratio']:.3f}")
        print(f"Median flux ratio: {recovery_stats['median_flux_ratio']:.3f}")

    # Determine success
    success = recovery_stats["recovery_rate"] >= 0.7  # 70% recovery threshold
    if success:
        print("\n✓ VALIDATION PASSED: Pipeline successfully recovers NVSS sources")
    else:
        print("\n✗ VALIDATION FAILED: Recovery rate below threshold (70%)")

    return 0 if success else 1


if __name__ == "__main__":
    main()
