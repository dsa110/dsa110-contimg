#!/opt/miniforge/envs/casa6/bin/python
"""
Build the full NVSS SQLite database from the HEASARC catalog.

This creates a comprehensive database with all ~1.77M NVSS sources at:
  /data/dsa110-contimg/state/catalogs/nvss_full.sqlite3

Once built, dec strip databases can be created much faster using SQL queries
instead of re-parsing the raw text file.

Usage:
    # Build full database (skip if exists)
    python -m dsa110_contimg.catalog.build_nvss_full_cli

    # Force rebuild
    python -m dsa110_contimg.catalog.build_nvss_full_cli --force

    # Check if database exists
    python -m dsa110_contimg.catalog.build_nvss_full_cli --check
"""

from __future__ import annotations

import argparse
import sys

from dsa110_contimg.catalog.builders import (
    build_nvss_full_db,
    get_nvss_full_db_path,
    nvss_full_db_exists,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build full NVSS SQLite database from HEASARC catalog"
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if database exists",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Check if database exists and print status",
    )
    ap.add_argument(
        "--output",
        help="Output path (default: state/catalogs/nvss_full.sqlite3)",
    )

    args = ap.parse_args(argv)

    if args.check:
        db_path = get_nvss_full_db_path()
        exists = nvss_full_db_exists()
        if exists:
            import sqlite3
            with sqlite3.connect(str(db_path)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
                meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
            print(f"✓ Full NVSS database exists: {db_path}")
            print(f"  Sources: {count:,}")
            print(f"  Built: {meta.get('build_time_iso', 'unknown')}")
            return 0
        else:
            print(f"✗ Full NVSS database not found: {db_path}")
            print("  Run without --check to build it.")
            return 1

    print("Building full NVSS database...")
    print("  This may take a few minutes on first run (downloads ~93MB, parses 1.77M sources)")
    print()

    try:
        from pathlib import Path
        output_path = Path(args.output) if args.output else None
        
        db_path = build_nvss_full_db(
            output_path=output_path,
            force_rebuild=args.force,
        )
        
        # Print summary
        import sqlite3
        with sqlite3.connect(str(db_path)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        
        print()
        print(f"✓ Full NVSS database ready: {db_path}")
        print(f"  Sources: {count:,}")
        print()
        print("Dec strip databases will now be built from this database (faster).")
        return 0

    except Exception as e:
        print(f"\n✗ Error building database: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
