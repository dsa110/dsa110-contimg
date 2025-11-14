#!/usr/bin/env python3
"""
Find available 0834+555 transits before a target date and build a 60-minute mosaic.

This script:
1. Lists all available transits for 0834+555 with data on disk
2. Finds the most recent transit before the target date (default: 2025-10-29)
3. Runs the complete 60-minute mosaic pipeline test

Usage:
    PYTHONPATH=/data/dsa110-contimg/src python scripts/find_and_build_0834_transit_mosaic.py [--before-date YYYY-MM-DD]
"""

import sys
import os
from pathlib import Path
from astropy.time import Time
from datetime import datetime

# Add src to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig
from dsa110_contimg.mosaic.cli import cmd_plan, cmd_build
import argparse


def find_transit_before_date(calibrator_name: str, target_date: str, max_days_back: int = 60):
    """Find the most recent transit before target_date that has data on disk.
    
    Args:
        calibrator_name: Calibrator name (e.g., "0834+555")
        target_date: Target date in ISO format (e.g., "2025-10-29")
        max_days_back: Maximum days to search back
        
    Returns:
        Transit info dict or None
    """
    # Initialize service
    config = CalibratorMSConfig.from_env()
    service = CalibratorMSGenerator.from_config(config, verbose=True)
    
    # Get all available transits
    print(f"\nSearching for available {calibrator_name} transits (max {max_days_back} days back)...")
    transits = service.list_available_transits(calibrator_name, max_days_back=max_days_back)
    
    if not transits:
        print(f"ERROR: No transits found with data for {calibrator_name}")
        return None
    
    print(f"\nFound {len(transits)} transits with data:")
    for i, transit in enumerate(transits[:10], 1):  # Show first 10
        transit_date = transit['transit_iso'].split('T')[0]
        print(f"  {i}. {transit['transit_iso']} ({transit_date}) - {len(transit.get('files', []))} files")
    
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
    """Main function to find transit and build 60-minute mosaic."""
    parser = argparse.ArgumentParser(description="Find transit and build 60-minute mosaic")
    parser.add_argument("--before-date", default="2025-10-29", 
                       help="Find transit before this date (YYYY-MM-DD)")
    parser.add_argument("--max-days-back", type=int, default=60,
                       help="Maximum days to search back")
    parser.add_argument("--calibrator", default="0834+555",
                       help="Calibrator name")
    
    args = parser.parse_args()
    
    calibrator_name = args.calibrator
    target_date = args.before_date
    
    print("=" * 70)
    print(f"Finding 0834+555 Transit Before {target_date} and Building 60-Minute Mosaic")
    print("=" * 70)
    
    # Step 1: Find transit with data
    print("\nStep 1: Finding available transit with data...")
    transit_info = find_transit_before_date(calibrator_name, target_date, args.max_days_back)
    
    if transit_info is None:
        print("ERROR: Could not find suitable transit. Exiting.")
        return 1
    
    # Extract transit time
    transit_iso = transit_info['transit_iso']
    transit_time = Time(transit_iso)
    
    # Step 2: Calculate 60-minute window (±30 minutes)
    window_minutes = 30
    start_time = transit_time - (window_minutes * 60)
    end_time = transit_time + (window_minutes * 60)
    
    print(f"\nStep 2: Calculated 60-minute window:")
    print(f"  Transit: {transit_time.isot}")
    print(f"  Window: {start_time.isot} to {end_time.isot}")
    
    # Convert to Unix timestamps for mosaic CLI
    since_epoch = int(start_time.unix)
    until_epoch = int(end_time.unix)
    
    # Get products DB path
    products_db = Path(os.getenv("PIPELINE_PRODUCTS_DB", str(repo_root / "state" / "products.sqlite3")))
    
    if not products_db.exists():
        print(f"ERROR: Products DB not found at {products_db}")
        print("Please set PIPELINE_PRODUCTS_DB environment variable or ensure state/products.sqlite3 exists")
        return 1
    
    # Create mosaic name from transit date
    transit_date = transit_iso.split('T')[0]
    mosaic_name = f"0834_transit_{transit_date}"
    
    # Step 3: Plan mosaic
    print(f"\nStep 3: Planning mosaic '{mosaic_name}'...")
    
    plan_args = argparse.Namespace(
        products_db=str(products_db),
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
    
    build_args = argparse.Namespace(
        products_db=str(products_db),
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

