#!/usr/bin/env python3
"""
Normalize subband filenames in a directory.

This script normalizes historical subband files by renaming them to use
canonical group_ids. Files with similar timestamps (within tolerance) are
grouped together, and all files in a group are renamed to use sb00's
timestamp as the canonical group_id.

Usage:
    # Dry-run (default - shows what would be renamed)
    python -m dsa110_contimg.conversion.streaming.normalize_cli /data/incoming

    # Actually rename files
    python -m dsa110_contimg.conversion.streaming.normalize_cli /data/incoming --apply

    # Custom tolerance
    python -m dsa110_contimg.conversion.streaming.normalize_cli /data/incoming --tolerance 30

Example output:
    Scanning /data/incoming...
    Found 160 files in 10 groups
    Would rename 12 files to match canonical timestamps

    Files to rename:
      2025-01-15T12:00:01_sb05.hdf5 -> 2025-01-15T12:00:00_sb05.hdf5
      2025-01-15T12:00:02_sb11.hdf5 -> 2025-01-15T12:00:00_sb11.hdf5
      ...
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dsa110_contimg.conversion.streaming.normalize import normalize_directory


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the normalize CLI."""
    parser = argparse.ArgumentParser(
        description="Normalize subband filenames to canonical group_ids",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing subband files to normalize",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually rename files (default is dry-run)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=60.0,
        help="Clustering tolerance in seconds (default: 60)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args(argv)

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s" if not args.verbose else "%(levelname)s: %(message)s",
    )

    # Validate directory
    if not args.directory.exists():
        print(f"Error: Directory does not exist: {args.directory}", file=sys.stderr)
        return 1

    if not args.directory.is_dir():
        print(f"Error: Not a directory: {args.directory}", file=sys.stderr)
        return 1

    # Run normalization
    dry_run = not args.apply

    if dry_run:
        print(f"Scanning {args.directory} (dry-run mode)...")
    else:
        print(f"Normalizing files in {args.directory}...")

    stats = normalize_directory(
        directory=args.directory,
        cluster_tolerance_s=args.tolerance,
        dry_run=dry_run,
    )

    # Report results
    print()
    print(f"Files scanned: {stats['files_scanned']}")
    print(f"Groups found: {stats['groups_found']}")

    if dry_run:
        print(f"Files to rename: {stats['files_renamed']}")
    else:
        print(f"Files renamed: {stats['files_renamed']}")

    if stats['errors']:
        print()
        print(f"Errors ({len(stats['errors'])}):")
        for error in stats['errors'][:10]:  # Limit to first 10
            print(f"  - {error}")
        if len(stats['errors']) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more")

    if dry_run and stats['files_renamed'] > 0:
        print()
        print("Run with --apply to actually rename files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
