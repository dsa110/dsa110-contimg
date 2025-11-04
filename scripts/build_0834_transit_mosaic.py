#!/usr/bin/env python3
"""
Build a 60-minute mosaic centered on VLA calibrator 0834+555 transit on 2025-11-02.

This script:
1. Finds the transit time for 0834+555 on 2025-11-02
2. Calculates a 60-minute window (±30 minutes around transit)
3. Plans a mosaic from tiles in that window
4. Builds the mosaic

Usage:
    PYTHONPATH=/data/dsa110-contimg/src python scripts/build_0834_transit_mosaic.py
"""

import sys
from pathlib import Path
from astropy.time import Time

# Add src to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from dsa110_contimg.calibration.catalogs import load_vla_catalog, get_calibrator_radec
from dsa110_contimg.calibration.schedule import previous_transits
from dsa110_contimg.mosaic.cli import cmd_plan, cmd_build
import argparse


def find_transit_on_date(calibrator_name: str, target_date: str, n: int = 10):
    """Find the transit time for a calibrator on a specific date.
    
    Args:
        calibrator_name: Calibrator name (e.g., "0834+555")
        target_date: Target date in ISO format (e.g., "2025-11-02")
        n: Number of previous transits to search
        
    Returns:
        Transit Time object for the specified date, or None if not found
    """
    # Load catalog
    catalog_df = load_vla_catalog()
    
    # Get RA/Dec
    try:
        ra_deg, dec_deg = get_calibrator_radec(catalog_df, calibrator_name)
        print(f"Found calibrator {calibrator_name}: RA={ra_deg:.4f}°, Dec={dec_deg:.4f}°")
    except KeyError as e:
        print(f"Error: {e}")
        return None
    
    # Calculate transits. Start from end of target date to find transits on that day
    # previous_transits finds the next transit after start_time, then steps backwards
    # So starting from 2025-11-02 23:59:59 will find transits on 2025-11-02
    search_start = Time(f"{target_date} 23:59:59")
    transits = previous_transits(ra_deg=ra_deg, start_time=search_start, n=n)
    
    # Find transit on target date
    for transit in transits:
        transit_date = transit.datetime.date().isoformat()
        if transit_date == target_date:
            print(f"Found transit on {target_date}: {transit.isot}")
            return transit
    
    # If no exact match, find closest transit on or before target date
    for transit in transits:
        transit_date = transit.datetime.date().isoformat()
        if transit_date <= target_date:
            print(f"Using closest transit before {target_date}: {transit.isot} ({transit_date})")
            return transit
    
    print(f"Warning: No transit found for {calibrator_name} on or before {target_date}")
    print(f"Available transits:")
    for i, transit in enumerate(transits, 1):
        print(f"  {i}. {transit.isot} ({transit.datetime.date().isoformat()})")
    return None


def main():
    """Main function to build 60-minute mosaic."""
    calibrator_name = "0834+555"
    target_date = "2025-11-02"
    mosaic_name = f"0834_transit_{target_date}"
    
    print(f"Building 60-minute mosaic for {calibrator_name} transit on {target_date}")
    print("=" * 60)
    
    # Step 1: Find transit time
    print("\nStep 1: Finding transit time...")
    transit_time = find_transit_on_date(calibrator_name, target_date)
    
    if transit_time is None:
        print("ERROR: Could not find transit time. Exiting.")
        return 1
    
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
    import os
    products_db = os.getenv("PIPELINE_PRODUCTS_DB", str(repo_root / "state" / "products.sqlite3"))
    
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
    
    # Determine output path
    output_dir = Path(os.getenv("CONTIMG_OUTPUT_DIR", str(repo_root / "state" / "mosaics")))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{mosaic_name}.image"
    
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
    
    print(f"\n✓ Success! Mosaic created at: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

