#!/opt/miniforge/envs/casa6/bin/python
"""
Comprehensive 60-minute mosaic generation script.

This script follows all phases from the granular mosaic generation plan:
1. Transit time calculation
2. Data discovery (HDF5 groups)
3. MS conversion
4. Calibrator identification
5. Calibration (flag, bandpass, gain)
6. Apply calibration to targets
7. Imaging
8-9. Mosaic planning and building

Usage:
    python scripts/build_60min_mosaic.py \
        --calibrator "0834+555" \
        --date "2025-11-02" \
        --incoming-dir /data/incoming \
        --output-dir /data/output
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from astropy.time import Time

# Add src to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from casacore.tables import table

from dsa110_contimg.calibration.catalogs import (get_calibrator_radec,
                                                 load_vla_catalog)
from dsa110_contimg.calibration.schedule import previous_transits
from dsa110_contimg.mosaic.cli import cmd_build, cmd_plan


def find_transit_on_date(calibrator_name: str, target_date: str, n: int = 10) -> Optional[Time]:
    """Find the transit time for a calibrator on a specific date."""
    catalog_df = load_vla_catalog()
    
    try:
        ra_deg, dec_deg = get_calibrator_radec(catalog_df, calibrator_name)
        print(f"Found calibrator {calibrator_name}: RA={ra_deg:.4f}°, Dec={dec_deg:.4f}°")
    except KeyError as e:
        print(f"Error: {e}")
        return None
    
    search_start = Time(f"{target_date} 23:59:59")
    transits = previous_transits(ra_deg=ra_deg, start_time=search_start, n=n)
    
    for transit in transits:
        transit_date = transit.datetime.date().isoformat()
        if transit_date == target_date:
            print(f"Found transit on {target_date}: {transit.isot}")
            return transit
    
    for transit in transits:
        transit_date = transit.datetime.date().isoformat()
        if transit_date <= target_date:
            print(f"Using closest transit before {target_date}: {transit.isot} ({transit_date})")
            return transit
    
    print(f"Warning: No transit found for {calibrator_name} on or before {target_date}")
    return None


def discover_groups(incoming_dir: Path, start_time: str, end_time: str) -> List[str]:
    """Discover available HDF5 groups in time window."""
    print(f"\n=== Phase 2: Data Discovery ===")
    print(f"Searching for groups between {start_time} and {end_time}...")
    
    # Use hdf5_orchestrator with --find-only
    cmd = [
        sys.executable, "-m", "dsa110_contimg.conversion.strategies.hdf5_orchestrator",
        str(incoming_dir),
        "/tmp/dummy",  # Dummy output path for find-only
        start_time,
        end_time,
        "--find-only"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: Group discovery failed:\n{result.stderr}")
        return []
    
    # Parse output to get group timestamps
    groups = []
    for line in result.stdout.split('\n'):
        if 'group' in line.lower() and any(c.isdigit() for c in line):
            # Extract timestamp or group ID from output
            # This is a simplified parser - adjust based on actual output format
            groups.append(line.strip())
    
    print(f"Found {len(groups)} groups")
    return groups


def convert_group_to_ms(incoming_dir: Path, output_dir: Path, group_time: str,
                        scratch_dir: Path, max_workers: int = 4) -> Optional[Path]:
    """Convert a single HDF5 group to MS."""
    ms_output = output_dir / "ms" / f"{group_time.replace(' ', 'T').replace(':', '-')}.ms"
    ms_output.parent.mkdir(parents=True, exist_ok=True)
    
    if ms_output.exists():
        print(f"  MS already exists: {ms_output}")
        return ms_output
    
    print(f"  Converting group {group_time} -> {ms_output}...")
    
    cmd = [
        sys.executable, "-m", "dsa110_contimg.conversion.strategies.hdf5_orchestrator",
        str(incoming_dir),
        str(ms_output.parent),
        group_time,
        group_time,
        "--writer", "parallel-subband",
        "--scratch-dir", str(scratch_dir),
        "--max-workers", str(max_workers),
    ]
    
    # Add tmpfs options if available
    tmpfs_path = Path("/dev/shm")
    if tmpfs_path.exists():
        cmd.extend(["--stage-to-tmpfs", "--tmpfs-path", str(tmpfs_path)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: Conversion failed:\n{result.stderr}")
        return None
    
    # Verify MS was created
    if ms_output.exists():
        print(f"  ✓ MS created: {ms_output}")
        return ms_output
    else:
        print(f"  ERROR: MS file not found after conversion")
        return None


def identify_calibrator_ms(ms_dir: Path, calibrator_name: str, transit_time: Time,
                           tolerance_minutes: float = 5.0) -> Optional[Path]:
    """Identify which MS contains the calibrator transit."""
    print(f"\n=== Phase 4: Calibrator Identification ===")
    print(f"Looking for calibrator MS near transit {transit_time.isot}...")
    
    catalog_df = load_vla_catalog()
    try:
        cal_ra, cal_dec = get_calibrator_radec(catalog_df, calibrator_name)
    except KeyError:
        print(f"ERROR: Calibrator {calibrator_name} not found in catalog")
        return None
    
    transit_mjd = transit_time.mjd
    tolerance_mjd = tolerance_minutes / (24 * 60)
    
    best_match = None
    best_diff = float('inf')
    
    for ms_path in sorted(ms_dir.glob("*.ms")):
        try:
            with table(str(ms_path), readonly=True) as tb:
                # Get time range from MS
                time_col = tb.getcol('TIME')
                if len(time_col) == 0:
                    continue
                
                mid_time = (time_col.min() + time_col.max()) / 2.0
                mid_mjd = mid_time / 86400.0 - 40587.0  # Convert to MJD
                
                # Check if MS time is near transit
                time_diff = abs(mid_mjd - transit_mjd)
                if time_diff < tolerance_mjd and time_diff < best_diff:
                    # Check if calibrator is in beam
                    # (Simplified: just check time proximity for now)
                    best_match = ms_path
                    best_diff = time_diff
        except Exception as e:
            print(f"  Warning: Could not read {ms_path}: {e}")
            continue
    
    if best_match:
        print(f"  ✓ Found calibrator MS: {best_match}")
        return best_match
    else:
        print(f"  ERROR: No MS found near transit time")
        return None


def flag_calibrator_ms(ms_path: Path) -> bool:
    """Flag calibrator MS (reset, zeros, rfi)."""
    print(f"\n=== Phase 5.1: Flagging Calibrator MS ===")
    
    modes = ["reset", "zeros", "rfi"]
    for mode in modes:
        print(f"  Flagging --mode {mode}...")
        cmd = [
            sys.executable, "-m", "dsa110_contimg.calibration.cli", "flag",
            "--ms", str(ms_path),
            "--mode", mode
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: Flagging ({mode}) failed:\n{result.stderr}")
            return False
        print(f"  ✓ {mode} flagging complete")
    
    # Check flagging summary
    cmd = [
        sys.executable, "-m", "dsa110_contimg.calibration.cli", "flag",
        "--ms", str(ms_path),
        "--mode", "summary"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    
    return True


def solve_bandpass(ms_path: Path, field: str = "0", refant: str = "103") -> Optional[Path]:
    """Solve bandpass calibration."""
    print(f"\n=== Phase 5.2: Bandpass Solve ===")
    
    ms_stem = ms_path.stem
    cal_table = ms_path.parent / f"{ms_stem}_{field}_bpcal"
    
    if cal_table.exists():
        print(f"  Bandpass table already exists: {cal_table}")
        return cal_table
    
    print(f"  Solving bandpass...")
    cmd = [
        sys.executable, "-m", "dsa110_contimg.calibration.cli", "calibrate",
        "--ms", str(ms_path),
        "--field", field,
        "--refant", refant,
        "--skip-g",  # Skip gain solve
        "--skip-k",  # Skip delay solve (default anyway)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: Bandpass solve failed:\n{result.stderr}")
        return None
    
    # Verify table was created
    if cal_table.exists():
        print(f"  ✓ Bandpass table created: {cal_table}")
        return cal_table
    else:
        print(f"  ERROR: Bandpass table not found")
        return None


def solve_gains(ms_path: Path, bp_table: Path, field: str = "0", refant: str = "103") -> Optional[Path]:
    """Solve gain calibration (using existing bandpass)."""
    print(f"\n=== Phase 5.3: Gain Solve ===")
    
    ms_stem = ms_path.stem
    cal_table = ms_path.parent / f"{ms_stem}_{field}_gpcal"
    
    if cal_table.exists():
        print(f"  Gain table already exists: {cal_table}")
        return cal_table
    
    print(f"  Solving gains...")
    cmd = [
        sys.executable, "-m", "dsa110_contimg.calibration.cli", "calibrate",
        "--ms", str(ms_path),
        "--field", field,
        "--refant", refant,
        "--skip-bp",  # Skip bandpass (use existing)
        "--skip-k",   # Skip delay solve
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: Gain solve failed:\n{result.stderr}")
        return None
    
    # Verify table was created
    if cal_table.exists():
        print(f"  ✓ Gain table created: {cal_table}")
        return cal_table
    else:
        print(f"  ERROR: Gain table not found")
        return None


def apply_calibration(target_ms: Path, bp_table: Path, gp_table: Path, field: str = "0") -> bool:
    """Apply calibration tables to target MS."""
    print(f"\n=== Phase 6: Apply Calibration ===")
    print(f"  Applying to {target_ms}...")
    
    cmd = [
        sys.executable, "-m", "dsa110_contimg.calibration.cli", "apply",
        "--ms", str(target_ms),
        "--field", field,
        "--tables", str(bp_table), str(gp_table)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: Calibration apply failed:\n{result.stderr}")
        return False
    
    # Verify CORRECTED_DATA column exists
    try:
        with table(str(target_ms), readonly=True) as tb:
            if 'CORRECTED_DATA' in tb.colnames():
                print(f"  ✓ Calibration applied (CORRECTED_DATA present)")
                return True
            else:
                print(f"  ERROR: CORRECTED_DATA column not found")
                return False
    except Exception as e:
        print(f"  ERROR: Could not verify application: {e}")
        return False


def image_ms(ms_path: Path, output_dir: Path, imsize: int = 2048, 
            cell_arcsec: float = 1.0, robust: float = 0.5) -> Optional[Path]:
    """Image a Measurement Set."""
    print(f"\n=== Phase 7: Imaging ===")
    print(f"  Imaging {ms_path}...")
    
    image_name = ms_path.stem
    image_path = output_dir / "images" / f"{image_name}.image"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    
    if image_path.exists():
        print(f"  Image already exists: {image_path}")
        return image_path
    
    cmd = [
        sys.executable, "-m", "dsa110_contimg.imaging.cli", "image",
        "--ms", str(ms_path),
        "--imagename", str(image_path.with_suffix('')),
        "--imsize", str(imsize),
        "--cell-arcsec", str(cell_arcsec),
        "--weighting", "briggs",
        "--robust", str(robust),
        "--pbcor",
        "--quality-tier", "development"  # Use development tier for speed
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: Imaging failed:\n{result.stderr}")
        return None
    
    if image_path.exists():
        print(f"  ✓ Image created: {image_path}")
        return image_path
    else:
        print(f"  ERROR: Image file not found")
        return None


def register_image_in_db(image_path: Path, ms_path: Path, products_db: Path, 
                         integration_time: str = "60min", pbcor: bool = True):
    """Register image in products database."""
    import time

    from dsa110_contimg.database.products import (ensure_products_db,
                                                  images_insert)
    
    conn = ensure_products_db(products_db)
    now = time.time()
    
    images_insert(conn, str(image_path), str(ms_path), now, integration_time, 1 if pbcor else 0)
    conn.commit()
    conn.close()
    
    print(f"  ✓ Image registered in products DB")


def main():
    parser = argparse.ArgumentParser(description="Build 60-minute mosaic")
    parser.add_argument("--calibrator", default="0834+555", help="Calibrator name")
    parser.add_argument("--date", default="2025-11-02", help="Target date (YYYY-MM-DD)")
    parser.add_argument("--incoming-dir", default="/data/incoming", help="Input HDF5 directory")
    parser.add_argument("--output-dir", default="/data/output", help="Output directory")
    parser.add_argument("--scratch-dir", default="/stage/dsa110-contimg", help="Scratch directory")
    parser.add_argument("--products-db", help="Products database path (default: state/db/products.sqlite3)")
    parser.add_argument("--window-minutes", type=int, default=30, help="Window around transit (minutes)")
    parser.add_argument("--imsize", type=int, default=2048, help="Image size (pixels)")
    parser.add_argument("--max-workers", type=int, default=4, help="Max conversion workers")
    parser.add_argument("--skip-conversion", action="store_true", help="Skip MS conversion (use existing)")
    parser.add_argument("--skip-calibration", action="store_true", help="Skip calibration (use existing)")
    
    args = parser.parse_args()
    
    incoming_dir = Path(args.incoming_dir)
    output_dir = Path(args.output_dir)
    scratch_dir = Path(args.scratch_dir)
    
    if args.products_db:
        products_db = Path(args.products_db)
    else:
        products_db = repo_root / "state" / "products.sqlite3"
    
    print("=" * 70)
    print(f"60-Minute Mosaic Generation")
    print(f"Calibrator: {args.calibrator}, Date: {args.date}")
    print("=" * 70)
    
    # Phase 1: Transit time calculation
    print("\n=== Phase 1: Transit Time Calculation ===")
    transit_time = find_transit_on_date(args.calibrator, args.date)
    if transit_time is None:
        print("ERROR: Could not find transit time")
        return 1
    
    window_minutes = args.window_minutes
    start_time = transit_time - (window_minutes * 60)
    end_time = transit_time + (window_minutes * 60)
    
    print(f"Transit: {transit_time.isot}")
    print(f"Window: {start_time.isot} to {end_time.isot}")
    
    start_str = start_time.isot.replace('T', ' ')[:19]
    end_str = end_time.isot.replace('T', ' ')[:19]
    
    # Phase 2-3: Data discovery and conversion
    if not args.skip_conversion:
        groups = discover_groups(incoming_dir, start_str, end_str)
        
        print(f"\n=== Phase 3: MS Conversion ===")
        ms_files = []
        for group_time in groups:
            ms_path = convert_group_to_ms(incoming_dir, output_dir, group_time, 
                                         scratch_dir, args.max_workers)
            if ms_path:
                ms_files.append(ms_path)
        
        if not ms_files:
            print("ERROR: No MS files created")
            return 1
    else:
        # Use existing MS files
        ms_dir = output_dir / "ms"
        ms_files = list(sorted(ms_dir.glob("*.ms")))
        print(f"\nUsing {len(ms_files)} existing MS files")
    
    # Phase 4: Calibrator identification
    cal_ms = identify_calibrator_ms(output_dir / "ms", args.calibrator, transit_time)
    if cal_ms is None:
        print("ERROR: Could not identify calibrator MS")
        return 1
    
    # Phase 5: Calibration
    if not args.skip_calibration:
        if not flag_calibrator_ms(cal_ms):
            print("ERROR: Flagging failed")
            return 1
        
        bp_table = solve_bandpass(cal_ms)
        if bp_table is None:
            print("ERROR: Bandpass solve failed")
            return 1
        
        gp_table = solve_gains(cal_ms, bp_table)
        if gp_table is None:
            print("ERROR: Gain solve failed")
            return 1
    else:
        # Use existing tables
        ms_stem = cal_ms.stem
        bp_table = cal_ms.parent / f"{ms_stem}_0_bpcal"
        gp_table = cal_ms.parent / f"{ms_stem}_0_gpcal"
        
        if not bp_table.exists() or not gp_table.exists():
            print(f"ERROR: Calibration tables not found:\n  {bp_table}\n  {gp_table}")
            return 1
        print(f"\nUsing existing calibration tables:\n  {bp_table}\n  {gp_table}")
    
    # Phase 6: Apply calibration to target MS files
    print(f"\n=== Phase 6: Apply Calibration to Target MS Files ===")
    target_ms_files = [ms for ms in ms_files if ms != cal_ms]
    
    for target_ms in target_ms_files:
        if not apply_calibration(target_ms, bp_table, gp_table):
            print(f"WARNING: Failed to apply calibration to {target_ms}")
    
    # Phase 7: Imaging
    print(f"\n=== Phase 7: Imaging ===")
    image_files = []
    for ms_file in ms_files:
        image_path = image_ms(ms_file, output_dir, imsize=args.imsize)
        if image_path:
            image_files.append(image_path)
            register_image_in_db(image_path, ms_file, products_db)
    
    if not image_files:
        print("ERROR: No images created")
        return 1
    
    # Phase 8-9: Mosaic planning and building
    print(f"\n=== Phase 8-9: Mosaic Planning and Building ===")
    
    mosaic_name = f"{args.calibrator.replace('+', '_')}_transit_{args.date}"
    since_epoch = int(start_time.unix)
    until_epoch = int(end_time.unix)
    
    # Plan mosaic
    import argparse as ap
    plan_args = ap.Namespace(
        products_db=str(products_db),
        name=mosaic_name,
        since=since_epoch,
        until=until_epoch,
        include_unpbcor=False,
        method="pbweighted"
    )
    
    print(f"Planning mosaic '{mosaic_name}'...")
    plan_result = cmd_plan(plan_args)
    if plan_result != 0:
        print(f"ERROR: Mosaic planning failed")
        return plan_result
    
    # Build mosaic
    mosaic_output = output_dir / "mosaics" / f"{mosaic_name}.image"
    mosaic_output.parent.mkdir(parents=True, exist_ok=True)
    
    build_args = ap.Namespace(
        products_db=str(products_db),
        name=mosaic_name,
        output=str(mosaic_output),
        ignore_validation=False,
        dry_run=False
    )
    
    print(f"Building mosaic '{mosaic_name}'...")
    build_result = cmd_build(build_args)
    if build_result != 0:
        print(f"ERROR: Mosaic building failed")
        return build_result
    
    print(f"\n{'=' * 70}")
    print(f"✓ SUCCESS! Mosaic created: {mosaic_output}")
    print(f"{'=' * 70}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

