#!/usr/bin/env python3
"""
Generate multiple MS files spanning 1 hour around a calibrator transit.

This script generates MS files for contiguous observation groups around a specific
transit time, creating a time series of MS files spanning approximately 1 hour.

Example:
    python scripts/generate_transit_hour_ms.py \
        --calibrator 0834+555 \
        --transit-time 2025-10-30T13:51:30 \
        --output-dir /scratch/dsa110-contimg/ms/0834_555_hour
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from astropy.time import Time
import astropy.units as u

from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig
from dsa110_contimg.conversion.exceptions import ConversionError
from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import find_subband_groups
from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert, _ms_time_range


def extract_group_id(file_path: str) -> str:
    """Extract group ID (timestamp) from file path."""
    base = Path(file_path).name
    return base.split('_sb')[0]


def generate_transit_hour_ms(
    calibrator_name: str,
    transit_time: Time,
    output_dir: Path,
    *,
    window_minutes: int = 30,
    max_groups: int = 10,
    config: CalibratorMSConfig,
    configure_for_imaging: bool = True,
    register_in_db: bool = True,
    stage_to_tmpfs: bool = True
) -> List[Tuple[str, Path, bool, str]]:
    """Generate MS files for groups spanning an hour around a transit.
    
    Args:
        calibrator_name: Name of calibrator (e.g., "0834+555")
        transit_time: Transit time to center on
        output_dir: Output directory for MS files
        window_minutes: Half-window in minutes around transit (default: 30 = ±30 min)
        max_groups: Maximum number of groups to process (default: 10)
        config: CalibratorMSConfig instance
        configure_for_imaging: Whether to configure MS for imaging
        register_in_db: Whether to register in products database
        stage_to_tmpfs: Whether to stage to tmpfs
        
    Returns:
        List of tuples: (group_id, ms_path, success, error_message)
    """
    results = []
    
    # Create generator
    generator = CalibratorMSGenerator.from_config(config, verbose=True)
    
    # Find all groups in window
    half_window = window_minutes
    t0 = (transit_time - half_window * u.min).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
    t1 = (transit_time + half_window * u.min).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\n{'='*80}")
    print(f"Generating MS files for {calibrator_name} transit hour")
    print(f"{'='*80}")
    print(f"Transit time: {transit_time.isot}")
    print(f"Search window: {t0} to {t1}")
    print(f"Output directory: {output_dir}")
    print(f"Maximum groups: {max_groups}")
    print()
    
    # Find groups
    groups = find_subband_groups(str(config.input_dir), t0, t1)
    
    if not groups:
        print(f"ERROR: No groups found in window")
        return results
    
    # Sort groups chronologically by timestamp
    groups_with_time = []
    for group_files in groups:
        group_id = extract_group_id(group_files[0])
        group_time = Time(group_id)
        delta_min = abs((group_time - transit_time).to(u.min).value)
        groups_with_time.append((group_time, group_id, group_files, delta_min))
    
    groups_with_time.sort(key=lambda x: x[0])  # Sort by time
    
    # Limit to max_groups closest to transit
    if len(groups_with_time) > max_groups:
        groups_with_time.sort(key=lambda x: x[3])  # Sort by delta from transit
        groups_with_time = groups_with_time[:max_groups]
        groups_with_time.sort(key=lambda x: x[0])  # Re-sort chronologically
    
    print(f"Found {len(groups_with_time)} groups to process:")
    for i, (group_time, group_id, group_files, delta_min) in enumerate(groups_with_time, 1):
        print(f"  {i:2d}. {group_id}: Δ={delta_min:.1f} min from transit, {len(group_files)} files")
    print()
    
    # Generate MS for each group
    for i, (group_time, group_id, group_files, delta_min) in enumerate(groups_with_time, 1):
        print(f"\n[{i}/{len(groups_with_time)}] Processing group {group_id}...")
        
        # Derive output path
        # Format: {calibrator}_{date}_{group_id}.ms
        cal_safe = calibrator_name.replace('+', '_').replace('-', '_')
        date_str = group_id.split('T')[0].replace('-', '')
        time_str = group_id.split('T')[1].replace(':', '')
        ms_name = f"{cal_safe}_{date_str}_{time_str}.ms"
        ms_path = output_dir / ms_name
        
        # Check if already exists
        if ms_path.exists():
            print(f"  ✓ MS already exists: {ms_path}")
            results.append((group_id, ms_path, True, "already_exists"))
            continue
        
        # Create transit info dict for database registration
        transit_info = {
            'transit_iso': transit_time.isot,
            'group_id': group_id,
            'transit_mjd': transit_time.mjd
        }
        
        try:
            # Convert group to MS
            print(f"  Converting {len(group_files)} subbands -> {ms_path}")
            start_time = time.time()
            
            generator.convert_group(
                group_files,
                ms_path,
                stage_to_tmpfs=stage_to_tmpfs
            )
            
            conversion_time = time.time() - start_time
            print(f"  ✓ Conversion completed in {conversion_time:.1f}s")
            
            # Configure for imaging
            if configure_for_imaging:
                print(f"  Configuring MS for imaging...")
                configure_ms_for_imaging(str(ms_path))
                print(f"  ✓ MS configured for imaging")
            
            # Register in database
            if register_in_db:
                print(f"  Registering in products database...")
                generator._register_ms_in_db(
                    ms_path,
                    transit_info,
                    status="converted",
                    stage="converted"
                )
                print(f"  ✓ Registered in database")
            
            results.append((group_id, ms_path, True, "success"))
            print(f"  ✓ Successfully created: {ms_path}")
            
        except ConversionError as e:
            error_msg = str(e)
            print(f"  ✗ Conversion failed: {error_msg}")
            results.append((group_id, ms_path, False, error_msg))
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"  ✗ {error_msg}")
            results.append((group_id, ms_path, False, error_msg))
    
    return results


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Generate MS files spanning 1 hour around a calibrator transit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    ap.add_argument('--calibrator', default='0834+555', 
                    help='Calibrator name (default: 0834+555)')
    ap.add_argument('--transit-time', required=True,
                    help='Transit time in ISO format (e.g., 2025-10-30T13:51:30)')
    ap.add_argument('--output-dir', required=True,
                    help='Output directory for MS files')
    ap.add_argument('--window-minutes', type=int, default=30,
                    help='Half-window in minutes around transit (default: 30 = ±30 min)')
    ap.add_argument('--max-groups', type=int, default=10,
                    help='Maximum number of groups to process (default: 10)')
    ap.add_argument('--input-dir', help='Input directory with UVH5 files (default: from env/config)')
    ap.add_argument('--products-db', help='Products database path (default: from env/config)')
    ap.add_argument('--no-configure', action='store_true',
                    help='Skip MS imaging column configuration')
    ap.add_argument('--no-register', action='store_true',
                    help='Skip database registration')
    ap.add_argument('--no-stage-tmpfs', action='store_true',
                    help='Disable tmpfs staging')
    
    args = ap.parse_args()
    
    # Parse transit time
    try:
        transit_time = Time(args.transit_time)
    except Exception as e:
        print(f"ERROR: Invalid transit time format: {e}", file=sys.stderr)
        return 1
    
    # Load configuration
    config = CalibratorMSConfig.from_env()
    
    # Override with command-line arguments
    if args.input_dir:
        config.input_dir = Path(args.input_dir)
    if args.products_db:
        config.products_db = Path(args.products_db)
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate MS files
    results = generate_transit_hour_ms(
        args.calibrator,
        transit_time,
        output_dir,
        window_minutes=args.window_minutes,
        max_groups=args.max_groups,
        config=config,
        configure_for_imaging=not args.no_configure,
        register_in_db=not args.no_register,
        stage_to_tmpfs=not args.no_stage_tmpfs
    )
    
    # Print summary
    print(f"\n{'='*80}")
    print("Summary")
    print(f"{'='*80}")
    successful = sum(1 for _, _, success, _ in results if success)
    failed = len(results) - successful
    print(f"Total groups processed: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Already existed: {sum(1 for _, _, _, msg in results if msg == 'already_exists')}")
    
    if failed > 0:
        print(f"\nFailed groups:")
        for group_id, ms_path, success, error_msg in results:
            if not success:
                print(f"  {group_id}: {error_msg}")
    
    if successful > 0:
        print(f"\nSuccessfully created MS files:")
        for group_id, ms_path, success, _ in results:
            if success:
                print(f"  {ms_path}")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

