#!/usr/bin/env python3
"""
Generate an MS for the most recent transit of a calibrator.

This script uses the CalibratorMSGenerator service to:
1. Find the most recent transit of the specified calibrator
2. Locate the subband group files for that transit
3. Convert the group to a Measurement Set
4. Configure it for imaging and register in products database

Example:
    python scripts/generate_calibrator_ms.py \
        --name 0834+555 \
        --output-dir /scratch/dsa110-contimg/ms
    
    # Or specify explicit output path:
    python scripts/generate_calibrator_ms.py \
        --name 0834+555 \
        --output-ms /scratch/dsa110-contimg/ms/0834_555_latest.ms
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig

def main() -> int:
    ap = argparse.ArgumentParser(
        description='Generate MS for most recent calibrator transit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    ap.add_argument('--name', default='0834+555', help='Calibrator name (default: 0834+555)')
    ap.add_argument('--input-dir', help='Input directory with UVH5 files (default: from env/config)')
    ap.add_argument('--output-dir', help='Output directory for MS files (default: from env/config)')
    ap.add_argument('--output-ms', help='Explicit output MS path (overrides --output-dir and auto-naming)')
    ap.add_argument('--products-db', help='Products database path (default: from env/config)')
    ap.add_argument('--catalog', action='append', help='VLA catalog paths (can specify multiple)')
    ap.add_argument('--window-minutes', type=int, default=60, help='Search window around transit (default: 60)')
    ap.add_argument('--max-days-back', type=int, default=14, help='Maximum days to search back (default: 14)')
    ap.add_argument('--dec-tolerance-deg', type=float, default=2.0, help='Declination tolerance (default: 2.0)')
    ap.add_argument('--scratch-dir', help='Scratch directory for staging (optional)')
    ap.add_argument('--no-stage-tmpfs', action='store_true', help='Disable tmpfs staging')
    ap.add_argument('--no-configure', action='store_true', help='Skip MS imaging column configuration')
    ap.add_argument('--no-register', action='store_true', help='Skip database registration')
    ap.add_argument('--json', action='store_true', help='Output JSON result')
    ap.add_argument('--quiet', action='store_true', help='Suppress progress messages')
    
    args = ap.parse_args()
    
    # Load configuration
    config = CalibratorMSConfig.from_env()
    
    # Override with command-line arguments
    if args.input_dir:
        config.input_dir = Path(args.input_dir)
    if args.output_dir:
        config.output_dir = Path(args.output_dir)
    if args.output_ms:
        config.output_dir = Path(args.output_ms).parent
    if args.products_db:
        config.products_db = Path(args.products_db)
    if args.catalog:
        config.catalogs = [Path(c) for c in args.catalog]
    if args.scratch_dir:
        config.scratch_dir = Path(args.scratch_dir)
    
    # Create generator
    generator = CalibratorMSGenerator.from_config(config, verbose=not args.quiet)
    
    # Determine output name
    output_name = None
    if args.output_ms:
        output_name = Path(args.output_ms).name
    
    # Generate MS
    result = generator.generate_from_transit(
        args.name,
        window_minutes=args.window_minutes,
        max_days_back=args.max_days_back,
        dec_tolerance_deg=args.dec_tolerance_deg,
        auto_naming=(output_name is None),
        output_name=output_name,
        configure_for_imaging=not args.no_configure,
        register_in_db=not args.no_register,
        stage_to_tmpfs=not args.no_stage_tmpfs
    )
    
    # Output results
    if args.json:
        output = {
            "success": result.success,
            "ms_path": str(result.ms_path) if result.ms_path else None,
            "transit_info": result.transit_info,
            "group_id": result.group_id,
            "already_exists": result.already_exists,
            "error": result.error,
            "metrics": result.metrics,
            "progress_summary": result.progress_summary
        }
        print(json.dumps(output, indent=2))
    else:
        if result.success:
            print(f"\n{'='*60}")
            print(f"Success!")
            print(f"{'='*60}")
            print(f"MS Path: {result.ms_path}")
            print(f"Transit: {result.transit_info['transit_iso'] if result.transit_info else 'N/A'}")
            print(f"Group ID: {result.group_id}")
            print(f"Already Existed: {result.already_exists}")
            if result.metrics:
                print(f"\nMetrics:")
                for key, value in result.metrics.items():
                    print(f"  {key}: {value}")
        else:
            print(f"\nError: {result.error}", file=sys.stderr)
            if result.progress_summary:
                print("\nProgress Summary:", file=sys.stderr)
                for step in result.progress_summary.get('steps', []):
                    status = step['status'].upper()
                    print(f"  [{status}] {step['message']}", file=sys.stderr)
    
    return 0 if result.success else 1


if __name__ == '__main__':
    sys.exit(main())

