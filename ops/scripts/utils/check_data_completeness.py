#!/opt/miniforge/envs/casa6/bin/python
"""
Check data completeness using the correct time-windowing approach.

This script demonstrates the CORRECT way to check for complete subband groups.
DO NOT use GROUP BY group_id on hdf5_file_index - it will give misleading results!
"""

import argparse
import sys
from pathlib import Path

from dsa110_contimg.database.hdf5_index import query_subband_groups


def main():
    parser = argparse.ArgumentParser(
        description="Check for complete subband groups in time range",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check October 18, 2025
  %(prog)s --start "2025-10-18 00:00:00" --end "2025-10-18 23:59:59"
  
  # Check with custom tolerance
  %(prog)s --start "2025-10-18 14:00:00" --end "2025-10-18 15:00:00" \\
           --tolerance 180.0

CRITICAL: This uses time-windowing to group subbands, not exact timestamp matching!
""",
    )
    parser.add_argument(
        "--hdf5-db",
        default="/data/dsa110-contimg/state/hdf5.sqlite3",
        help="Path to HDF5 database (default: %(default)s)",
    )
    parser.add_argument(
        "--start",
        required=True,
        help='Start time (ISO format: "YYYY-MM-DD HH:MM:SS")',
    )
    parser.add_argument(
        "--end",
        required=True,
        help='End time (ISO format: "YYYY-MM-DD HH:MM:SS")',
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=150.0,
        help="Clustering tolerance in seconds (default: 150.0 = 2.5 min)",
    )
    parser.add_argument(
        "--min-subbands",
        type=int,
        default=12,
        help="Minimum subbands for 'complete' group (default: 12)",
    )
    parser.add_argument(
        "--show-incomplete",
        action="store_true",
        help="Also show incomplete groups",
    )

    args = parser.parse_args()

    # Query using time-windowing
    print(f"Querying {args.start} to {args.end}")
    print(f"Clustering tolerance: {args.tolerance}s ({args.tolerance/60:.1f} min)")
    print()

    groups = query_subband_groups(
        Path(args.hdf5_db),
        args.start,
        args.end,
        cluster_tolerance_s=args.tolerance,
    )

    if not groups:
        print("No groups found in time range")
        return 1

    # Categorize groups
    complete = [g for g in groups if g.num_subbands >= args.min_subbands]
    incomplete = [g for g in groups if g.num_subbands < args.min_subbands]

    print(f"Found {len(groups)} total groups:")
    print(f"  Complete (≥{args.min_subbands} subbands): {len(complete)}")
    print(f"  Incomplete (<{args.min_subbands} subbands): {len(incomplete)}")
    print()

    # Show complete groups
    if complete:
        print("Complete groups:")
        for g in complete:
            missing = 16 - g.num_subbands
            missing_str = f" (missing {missing})" if missing > 0 else ""
            print(f"  {g.representative_time}: {g.num_subbands} subbands{missing_str}")
        print()

    # Show incomplete groups if requested
    if args.show_incomplete and incomplete:
        print("Incomplete groups:")
        for g in incomplete:
            print(f"  {g.representative_time}: {g.num_subbands} subbands")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
