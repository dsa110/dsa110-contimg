#!/usr/bin/env python3
"""
Build a 60-minute mosaic centered on VLA calibrator 0834+555 transit.

This script:
1. Uses list_available_transits() to find transits with data on disk
2. Finds the most recent transit before a target date (default: 2025-10-29)
3. Calculates a 60-minute window (±30 minutes around transit)
4. Plans a mosaic from tiles in that window
5. Builds the mosaic

Usage:
    PYTHONPATH=/data/dsa110-contimg/src python scripts/build_0834_transit_mosaic.py [--before-date YYYY-MM-DD]
"""

import argparse
from dsa110_contimg.mosaic.cli import cmd_plan, cmd_build
from dsa110_contimg.conversion.config import CalibratorMSConfig
from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
import sys
import os
from pathlib import Path
from astropy.time import Time
from datetime import datetime

# Add src to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))


def find_transit_with_data_before_date(calibrator_name: str, target_date: str, max_days_back: int = 60):
    """Find the most recent transit before target_date that has data on disk.

    Args:
        calibrator_name: Calibrator name (e.g., "0834+555")
        target_date: Target date in ISO format (e.g., "2025-10-29")
        max_days_back: Maximum days to search back

    Returns:
        Transit info dict with 'transit_iso' key, or None
    """
    # Initialize service
    config = CalibratorMSConfig.from_env()
    service = CalibratorMSGenerator.from_config(config, verbose=True)

    # Get all available transits with data
    print(
        f"\nSearching for available {calibrator_name} transits with data (max {max_days_back} days back)...")
    transits = service.list_available_transits(
        calibrator_name, max_days_back=max_days_back)

    if not transits:
        print(f"ERROR: No transits found with data for {calibrator_name}")
        return None

    print(f"\nFound {len(transits)} transits with data:")
    for i, transit in enumerate(transits[:10], 1):  # Show first 10
        transit_date = transit['transit_iso'].split('T')[0]
        print(
            f"  {i}. {transit['transit_iso']} ({transit_date}) - {len(transit.get('files', []))} files")

    # Find transit before target date
    target_dt = datetime.fromisoformat(target_date)

    print(f"\nLooking for transit before {target_date}...")
    for transit in transits:
        transit_iso = transit['transit_iso']
        transit_dt = datetime.fromisoformat(transit_iso.split('T')[0])

        if transit_dt < target_dt:
            print(f"\n✓ Found transit before {target_date}: {transit_iso}")
            print(f"  Group ID: {transit['group_id']}")
            print(f"  Files: {len(transit.get('files', []))} subband files")
            print(f"  Has MS: {transit.get('has_ms', False)}")
            return transit

    print(f"\nERROR: No transit found before {target_date}")
    print(f"Available transits:")
    for transit in transits[:5]:
        print(f"  - {transit['transit_iso']}")
    return None


def main():
    """Main function to build 60-minute mosaic."""
    parser = argparse.ArgumentParser(
        description="Build 60-minute mosaic for 0834+555 transit")
    parser.add_argument("--before-date", default="2025-10-29",
                        help="Find transit before this date (YYYY-MM-DD)")
    parser.add_argument("--max-days-back", type=int, default=60,
                        help="Maximum days to search back")

    args = parser.parse_args()

    calibrator_name = "0834+555"
    target_date = args.before_date

    print(
        f"Building 60-minute mosaic for {calibrator_name} transit before {target_date}")
    print("=" * 70)

    # Step 1: Find transit with data
    print("\nStep 1: Finding transit with data on disk...")
    transit_info = find_transit_with_data_before_date(
        calibrator_name, target_date, args.max_days_back)

    if transit_info is None:
        print("ERROR: Could not find suitable transit. Exiting.")
        return 1

    # Extract transit time
    transit_iso = transit_info['transit_iso']
    transit_time = Time(transit_iso)

    # Create mosaic name from transit date
    transit_date = transit_iso.split('T')[0]
    mosaic_name = f"0834_transit_{transit_date}"

    # Step 2: Calculate 60-minute window (±30 minutes)
    window_minutes = 30
    start_time = transit_time - (window_minutes * 60)  # 30 minutes before
    end_time = transit_time + (window_minutes * 60)     # 30 minutes after

    print(f"\nStep 2: Calculated 60-minute window:")
    print(f"  Transit: {transit_time.isot}")
    print(f"  Window: {start_time.isot} to {end_time.isot}")

    # Convert to Unix timestamps for mosaic CLI
    since_epoch = int(start_time.unix)
    until_epoch = int(end_time.unix)

    # Step 3: Plan mosaic
    print(f"\nStep 3: Planning mosaic '{mosaic_name}'...")

    # Get products DB path from environment or default
    products_db = os.getenv("PIPELINE_PRODUCTS_DB", str(
        repo_root / "state" / "products.sqlite3"))

    if not Path(products_db).exists():
        print(f"ERROR: Products DB not found at {products_db}")
        print("Please set PIPELINE_PRODUCTS_DB environment variable or ensure state/products.sqlite3 exists")
        return 1

    # Create plan args
    plan_args = argparse.Namespace(
        products_db=products_db,
        name=mosaic_name,
        since=since_epoch,
        until=until_epoch,
        include_unpbcor=False,
        method="pbweighted"
    )

    plan_result = cmd_plan(plan_args)
    if plan_result != 0:
        print(f"ERROR: Mosaic planning failed (exit code {plan_result})")
        return plan_result

    # Step 4: Build mosaic
    print(f"\nStep 4: Building mosaic...")

    # Determine output path (use /stage/dsa110-contimg/ as staging area)
    output_dir = Path(os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg"))
    mosaic_dir = output_dir / "mosaics"
    mosaic_dir.mkdir(parents=True, exist_ok=True)
    output_path = mosaic_dir / f"{mosaic_name}.image"

    # Create build args
    build_args = argparse.Namespace(
        products_db=products_db,
        name=mosaic_name,
        output=str(output_path),
        ignore_validation=False,
        dry_run=False
    )

    build_result = cmd_build(build_args)
    if build_result != 0:
        print(f"ERROR: Mosaic building failed (exit code {build_result})")
        return build_result

    print(f"\n{'=' * 70}")
    print(f"✓ SUCCESS! Mosaic created at: {output_path}")
    print(f"{'=' * 70}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
