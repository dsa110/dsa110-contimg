#!/usr/bin/env python3
"""
Simple 0834+555 Lightcurve Generator

Creates a lightcurve from multiple 0834+555 transits using the DSA-110 pipeline.
This is a simplified version that finds available transit data and processes it
step-by-step.

Usage:
    conda activate casa6
    python scripts/lightcurve_0834_simple.py --num-transits 10
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.time import Time

from dsa110_contimg.calibration.transit import upcoming_transits
from dsa110_contimg.database.hdf5_index import query_subband_groups


def find_transits_with_data(
    ra_deg: float,
    data_start: datetime,
    data_end: datetime,
    num_transits: int = 10,
    window_minutes: float = 10.0,
) -> list:
    """Find transits that have available HDF5 data.
    
    Args:
        ra_deg: RA of calibrator in degrees
        data_start: Start of data availability window
        data_end: End of data availability window
        num_transits: Maximum number of transits to find
        window_minutes: Search window around transit (±minutes)
    
    Returns:
        List of (transit_time, subband_groups) tuples
    """
    print(f"Searching for transits between {data_start} and {data_end}...")
    
    # Calculate expected number of transits (one per sidereal day ≈ 23h 56m)
    delta_days = (data_end - data_start).days + 1
    # Request slightly more than expected to ensure we cover the full range
    n_transits = int(delta_days * 1.05)
    
    # Compute transits
    start_time = Time(data_start)
    transits = upcoming_transits(ra_deg, start_time=start_time, n=n_transits)
    
    # Filter to data range
    valid_transits = [t for t in transits if data_start <= t.datetime <= data_end]
    print(f"Found {len(valid_transits)} transits in date range ({delta_days} days)")
    
    # Check for data
    matches = []
    db_path = "/data/incoming/hdf5_file_index.sqlite3"
    
    for t in valid_transits:
        window_start = (t.datetime - timedelta(minutes=window_minutes)).isoformat()
        window_end = (t.datetime + timedelta(minutes=window_minutes)).isoformat()
        
        groups = query_subband_groups(
            db_path=db_path,
            start_time=window_start,
            end_time=window_end,
            cluster_tolerance_s=60.0,
        )
        
        complete = [g for g in groups if len(g) == 16]
        
        if complete:
            # Pick the first group (they're all within the window)
            best_group = complete[0]
            matches.append((t, best_group))
            print(f"  ✓ {t.iso}: found {len(complete)} groups")
            
            if len(matches) >= num_transits:
                break
    
    print(f"\nFound {len(matches)} transits with complete 16-subband data")
    return matches


def convert_transits(transit_data: list, output_dir: Path) -> list:
    """Convert HDF5 subband groups to MS files.
    
    Args:
        transit_data: List of (transit_time, subband_group) tuples
        output_dir: Output directory for MS files
    
    Returns:
        List of MS file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ms_files = []
    
    print(f"\nConverting {len(transit_data)} transits to MS...")
    
    for i, (transit_time, subband_group) in enumerate(transit_data, 1):
        # subband_group is already a list of file paths
        file_paths = subband_group
        
        # Generate MS name
        timestamp = transit_time.datetime.strftime("%Y-%m-%dT%H-%M-%S")
        ms_name = f"0834_transit_{i:02d}_{timestamp}.ms"
        ms_path = output_dir / ms_name
        
        if ms_path.exists():
            print(f"  {i}/{len(transit_data)}: {ms_name} already exists, skipping")
            ms_files.append(ms_path)
            continue
        
        print(f"  {i}/{len(transit_data)}: Converting {ms_name}...")
        
        # Convert using the direct MS writer
        from dsa110_contimg.conversion.direct_subband import write_ms_from_subbands
        
        try:
            write_ms_from_subbands(
                file_list=file_paths,
                ms_path=str(ms_path),
                scratch_dir="/dev/shm",
            )
            ms_files.append(ms_path)
            print(f"    ✓ Conversion complete: {ms_path}")
        except Exception as e:
            print(f"    ✗ Conversion failed: {e}")
            continue
    
    return ms_files


def main():
    parser = argparse.ArgumentParser(
        description="Generate 0834+555 lightcurve from DSA-110 observations"
    )
    parser.add_argument(
        "--num-transits",
        type=int,
        default=10,
        help="Number of transits to process (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/stage/dsa110-contimg/0834_lightcurve"),
        help="Output directory for MS files and plots",
    )
    parser.add_argument(
        "--window-minutes",
        type=float,
        default=10.0,
        help="Search window around transit time (default: ±10 min)",
    )
    
    args = parser.parse_args()
    
    # 0834+555 coordinates
    ra_deg = 128.7287  # 08h34m54.9s
    dec_deg = 55.5725  # +55d34m21.1s
    
    # Data availability window (from HDF5 file index)
    data_start = datetime(2025, 10, 2)
    data_end = datetime(2025, 11, 18, 23, 59, 59)
    
    print("=" * 60)
    print("0834+555 Lightcurve Generator")
    print("=" * 60)
    print(f"Calibrator: 0834+555 (RA={ra_deg:.4f}°, Dec={dec_deg:.4f}°)")
    print(f"Num transits: {args.num_transits}")
    print(f"Output dir: {args.output_dir}")
    print(f"Search window: ±{args.window_minutes} min")
    print()
    
    # Step 1: Find transits with data
    transit_data = find_transits_with_data(
        ra_deg=ra_deg,
        data_start=data_start,
        data_end=data_end,
        num_transits=args.num_transits,
        window_minutes=args.window_minutes,
    )
    
    if not transit_data:
        print("ERROR: No transits found with available data!")
        sys.exit(1)
    
    # Step 2: Convert to MS
    ms_files = convert_transits(transit_data, args.output_dir)
    
    if not ms_files:
        print("ERROR: No MS files were created!")
        sys.exit(1)
    
    print(f"\n{'=' * 60}")
    print(f"SUCCESS: Created {len(ms_files)} MS files")
    print(f"{'=' * 60}")
    print("\nNext steps:")
    print("1. Calibrate each MS:")
    print("   python -m dsa110_contimg.calibration.cli \\")
    print(f"     --ms {args.output_dir}/*.ms \\")
    print("     --field 0 --fast")
    print("\n2. Image each MS:")
    print("   python -m dsa110_contimg.imaging.cli \\")
    print(f"     --ms {args.output_dir}/*.ms \\")
    print("     --quality-tier development")
    print("\n3. Perform photometry and create lightcurve")
    print("   (Manual step - see make_lightcurve_0834.md)")
    
    # Save transit metadata
    metadata_file = args.output_dir / "transit_metadata.json"
    metadata = [
        {
            "transit_time": t.iso,
            "transit_mjd": t.mjd,
            "ms_file": str(ms_files[i]) if i < len(ms_files) else None,
        }
        for i, (t, _) in enumerate(transit_data)
    ]
    
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nMetadata saved to: {metadata_file}")


if __name__ == "__main__":
    main()
