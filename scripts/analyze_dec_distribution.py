#!/opt/miniforge/envs/casa6/bin/python
"""
Analyze declination distribution across HDF5 observations.

Samples HDF5 files from the database and extracts declination values
to understand the distribution of pointings and identify Dec ~55° epochs.
"""

import sqlite3
import numpy as np
from collections import defaultdict
import h5py


def extract_dec_from_hdf5(path: str) -> float | None:
    """Extract declination in degrees from HDF5 file."""
    try:
        with h5py.File(path, 'r') as f:
            if 'Header/extra_keywords/phase_center_dec' in f:
                dec_rad = f['Header/extra_keywords/phase_center_dec'][()]
                return float(np.degrees(dec_rad))
    except Exception as e:
        print(f"  Warning: Could not read {path}: {e}")
    return None


def main():
    db_path = "/data/incoming/hdf5_file_index.sqlite3"
    
    print("=" * 80)
    print("DSA-110 Declination Distribution Analysis")
    print("=" * 80)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get total counts
    cursor.execute("SELECT COUNT(*) FROM hdf5_file_index")
    total_files = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT timestamp) FROM hdf5_file_index")
    total_timestamps = cursor.fetchone()[0]
    
    print("\nDatabase statistics:")
    print(f"  Total HDF5 files: {total_files:,}")
    print(f"  Unique timestamps: {total_timestamps:,}")
    
    # Get time range
    cursor.execute("SELECT MIN(timestamp_iso), MAX(timestamp_iso) FROM hdf5_file_index")
    min_time, max_time = cursor.fetchone()
    print(f"  Time range: {min_time} to {max_time}")
    
    # Sample files for declination extraction
    # Strategy: Sample every Nth timestamp (subband 0 only) for good coverage
    sample_size = 500  # Coarse sampling
    cursor.execute(f"""
        WITH ranked AS (
            SELECT timestamp, timestamp_iso, path,
                   ROW_NUMBER() OVER (ORDER BY timestamp) as rn,
                   COUNT(*) OVER () as total
            FROM hdf5_file_index
            WHERE subband = 0
        )
        SELECT timestamp, timestamp_iso, path
        FROM ranked
        WHERE rn % (total / {sample_size}) = 0
        ORDER BY timestamp
    """)
    
    sample_files = cursor.fetchall()
    print(f"\n  Sampling {len(sample_files)} files for declination...")
    
    # Extract declinations
    dec_data = []
    failed = 0
    
    for i, (timestamp, timestamp_iso, path) in enumerate(sample_files):
        if i % 50 == 0:
            print(f"    Progress: {i}/{len(sample_files)} ({100*i/len(sample_files):.1f}%)")
        
        dec = extract_dec_from_hdf5(path)
        if dec is not None:
            dec_data.append({
                'timestamp': timestamp,
                'timestamp_iso': timestamp_iso,
                'dec_deg': dec,
                'path': path
            })
        else:
            failed += 1
    
    print(f"\n  Successfully extracted {len(dec_data)} declinations")
    print(f"  Failed to read {failed} files")
    
    if not dec_data:
        print("\nERROR: No declinations extracted!")
        return
    
    # Analyze distribution
    print("\n" + "=" * 80)
    print("Declination Distribution")
    print("=" * 80)
    
    decs = np.array([d['dec_deg'] for d in dec_data])
    
    print("\nStatistics:")
    print(f"  Min Dec:    {decs.min():.4f}°")
    print(f"  Max Dec:    {decs.max():.4f}°")
    print(f"  Mean Dec:   {decs.mean():.4f}°")
    print(f"  Median Dec: {np.median(decs):.4f}°")
    print(f"  Std Dev:    {decs.std():.4f}°")
    
    # Histogram
    print("\nHistogram (1° bins):")
    hist, bin_edges = np.histogram(decs, bins=np.arange(int(decs.min()), int(decs.max())+2, 1))
    for i, count in enumerate(hist):
        if count > 0:
            dec_center = (bin_edges[i] + bin_edges[i+1]) / 2
            bar = '#' * int(50 * count / hist.max())
            print(f"  {dec_center:5.1f}°: {bar} ({count})")
    
    # Find Dec ~55° epochs
    print("\n" + "=" * 80)
    print("Observations near Dec = 55°")
    print("=" * 80)
    
    target_dec = 55.0
    tolerance = 2.0  # ±2° tolerance
    
    near_55 = [d for d in dec_data if abs(d['dec_deg'] - target_dec) < tolerance]
    
    if near_55:
        print(f"\nFound {len(near_55)} observations within ±{tolerance}° of {target_dec}°:")
        print(f"\n{'Timestamp':<20} {'Dec (°)':<10} {'Date':<12}")
        print("-" * 50)
        
        # Group by date
        by_date = defaultdict(list)
        for obs in near_55:
            date = obs['timestamp_iso'][:10]  # YYYY-MM-DD
            by_date[date].append(obs)
        
        # Show samples from each date
        for date in sorted(by_date.keys()):
            obs_list = by_date[date]
            # Show first observation of each date
            obs = obs_list[0]
            print(f"{obs['timestamp_iso']:<20} {obs['dec_deg']:8.4f}   {date:<12}")
            if len(obs_list) > 1:
                print(f"  ... and {len(obs_list)-1} more observations on this date")
        
        print(f"\n" + "=" * 80)
        print(f"Days with Dec ~{target_dec}°:")
        print("=" * 80)
        for date in sorted(by_date.keys()):
            n_obs = len(by_date[date])
            dec_range = [o['dec_deg'] for o in by_date[date]]
            print(f"  {date}: {n_obs:3d} observations, Dec range: {min(dec_range):.3f}° - {max(dec_range):.3f}°")
    else:
        print(f"\nNo observations found within ±{tolerance}° of {target_dec}°")
        
        # Find closest
        closest_idx = np.argmin(np.abs(decs - target_dec))
        closest = dec_data[closest_idx]
        print(f"\nClosest observation:")
        print(f"  Timestamp: {closest['timestamp_iso']}")
        print(f"  Dec: {closest['dec_deg']:.4f}°")
        print(f"  Difference: {abs(closest['dec_deg'] - target_dec):.4f}°")
    
    conn.close()


if __name__ == "__main__":
    main()
