#!/opt/miniforge/envs/casa6/bin/python
"""
Build MS files for a 60-minute window centered on VLA calibrator 0834+555 transit on 2025-11-02.

This script uses the same codebase and parameters as the streaming pipeline to ensure
stress testing with production code paths.

Usage:
    PYTHONPATH=/data/dsa110-contimg/src python scripts/build_0834_transit_ms.py
"""

import os
import subprocess
import sys
from pathlib import Path

import astropy.units as u
from astropy.time import Time

# Add src to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from dsa110_contimg.calibration.catalogs import (get_calibrator_radec,
                                                 load_vla_catalog)
from dsa110_contimg.calibration.schedule import previous_transits


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
    """Main function to build MS files using streaming pipeline codebase."""
    calibrator_name = "0834+555"
    target_date = "2025-11-02"
    
    print(f"Building MS files for 60-minute window around {calibrator_name} transit on {target_date}")
    print("=" * 70)
    print("Using streaming pipeline codebase (orchestrator with --writer auto)")
    print("=" * 70)
    
    # Step 1: Find transit time
    print("\nStep 1: Finding transit time...")
    transit_time = find_transit_on_date(calibrator_name, target_date)
    
    if transit_time is None:
        print("ERROR: Could not find transit time. Exiting.")
        return 1
    
    # Step 2: Calculate 60-minute window (±30 minutes)
    window_minutes = 30
    start_time = transit_time - (window_minutes * u.min)  # 30 minutes before
    end_time = transit_time + (window_minutes * u.min)     # 30 minutes after
    
    # Format as strings for CLI (YYYY-MM-DD HH:MM:SS)
    start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\nStep 2: Calculated 60-minute window:")
    print(f"  Transit: {transit_time.isot}")
    print(f"  Window: {start_time_str} to {end_time_str}")
    
    # Step 3: Get directories from environment or use defaults
    input_dir = os.getenv("CONTIMG_INPUT_DIR", "/data/incoming")
    output_dir = os.getenv("CONTIMG_OUTPUT_DIR", "/data/ms")
    scratch_dir = os.getenv("CONTIMG_SCRATCH_DIR", "/data/scratch")
    
    # Create directories if they don't exist
    for dir_path in [input_dir, output_dir, scratch_dir]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print(f"\nStep 3: Directory configuration:")
    print(f"  Input (HDF5): {input_dir}")
    print(f"  Output (MS): {output_dir}")
    print(f"  Scratch: {scratch_dir}")
    
    # Verify input directory exists and has files
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"ERROR: Input directory does not exist: {input_dir}")
        return 1
    
    hdf5_files = list(input_path.glob("*_sb??.hdf5"))
    if not hdf5_files:
        print(f"WARNING: No HDF5 files found in {input_dir}")
        print("Continuing anyway - orchestrator will search for files in time window...")
    else:
        print(f"Found {len(hdf5_files)} HDF5 files in input directory")
    
    # Step 4: Build command matching streaming pipeline exactly
    print(f"\nStep 4: Running orchestrator (same as streaming pipeline)...")
    print(f"Command: python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator")
    print(f"  --writer auto (selects parallel-subband for 16 subbands)")
    print(f"  --stage-to-tmpfs (if available)")
    
    # Build command - matching streaming pipeline exactly
    cmd = [
        sys.executable,
        "-m",
        "dsa110_contimg.conversion.strategies.hdf5_orchestrator",
        input_dir,
        output_dir,
        start_time_str,
        end_time_str,
        "--writer",
        "auto",  # Streaming pipeline uses "auto" which selects appropriate writer
        "--scratch-dir",
        scratch_dir,
        "--max-workers",
        "4",  # Default from streaming pipeline
    ]
    
    # Add tmpfs staging if available (matches streaming pipeline)
    tmpfs_path = os.getenv("CONTIMG_TMPFS_PATH", "/dev/shm")
    if Path(tmpfs_path).exists():
        cmd.append("--stage-to-tmpfs")
        cmd.extend(["--tmpfs-path", tmpfs_path])
        print(f"  Using tmpfs staging: {tmpfs_path}")
    else:
        print(f"  Tmpfs not available at {tmpfs_path}, using scratch directory only")
    
    # Set environment variables matching streaming pipeline
    env = os.environ.copy()
    env.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    env.setdefault("OMP_NUM_THREADS", os.getenv("OMP_NUM_THREADS", "4"))
    env.setdefault("MKL_NUM_THREADS", os.getenv("MKL_NUM_THREADS", "4"))
    
    # Set PYTHONPATH if not already set
    if "PYTHONPATH" not in env:
        env["PYTHONPATH"] = str(repo_root / "src")
    
    print(f"\nExecuting conversion...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run the orchestrator
    try:
        ret = subprocess.call(cmd, env=env)
        if ret != 0:
            print(f"\nERROR: Orchestrator failed with exit code {ret}")
            return ret
        
        print(f"\n✓ Conversion completed successfully!")
        print(f"\nMS files should be in: {output_dir}")
        
        # List generated MS files
        output_path = Path(output_dir)
        ms_files = list(output_path.glob("*.ms"))
        if ms_files:
            print(f"\nGenerated {len(ms_files)} MS file(s):")
            for ms_file in sorted(ms_files):
                print(f"  - {ms_file}")
        else:
            print(f"\nNo MS files found in {output_dir}")
            print("This may be normal if no complete groups were found in the time window.")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nConversion interrupted by user")
        return 130
    except Exception as e:
        print(f"\nERROR: Exception during conversion: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

