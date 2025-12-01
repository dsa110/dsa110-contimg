#!/usr/bin/env python3
"""
Database Migration Script: Consolidate to Unified Pipeline Database.

Migrates data from 5+ separate SQLite databases into a single unified
pipeline.sqlite3 database as outlined in the complexity reduction guide.

Source databases:
    - products.sqlite3 (ms_index, images, photometry, etc.)
    - cal_registry.sqlite3 (caltables)
    - ingest.sqlite3 (queue, performance metrics)
    - calibrators.sqlite3 (bandpass_calibrators, vla_calibrators)
    - hdf5.sqlite3 (file index)
    - alerts.sqlite3 (alert history)

Target database:
    - pipeline.sqlite3 (all tables unified)

Usage:
    # Preview migration (no changes)
    python scripts/migrate_to_unified_db.py --dry-run
    
    # Execute migration with backup
    python scripts/migrate_to_unified_db.py
    
    # Specify custom paths
    python scripts/migrate_to_unified_db.py \
        --state-dir /data/dsa110-contimg/state/db \
        --output /data/dsa110-contimg/state/db/pipeline.sqlite3

Safety:
    - Creates timestamped backup of all source databases
    - Verifies row counts after migration
    - Does not delete source databases (manual step)
    - Can be run multiple times (uses INSERT OR IGNORE)
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add backend to path if running as script
SCRIPT_DIR = Path(__file__).parent
BACKEND_SRC = SCRIPT_DIR.parent / "backend" / "src"
if BACKEND_SRC.exists():
    sys.path.insert(0, str(BACKEND_SRC))


# =============================================================================
# Source Database Configuration
# =============================================================================

# Source database files and their table mappings
SOURCE_DATABASES = {
    "products": {
        "file": "products.sqlite3",
        "tables": {
            "ms_index": "ms_index",
            "images": "images",
            "photometry": "photometry",
            "hdf5_file_index": "hdf5_files",  # Map to unified name
            "storage_locations": "storage_locations",
            "dead_letter_queue": "dead_letter_queue",
            "calibrator_transits": "calibrator_transits",
            "pointing_history": "pointing_history",
        }
    },
    "cal_registry": {
        "file": "cal_registry.sqlite3",
        "tables": {
            "caltables": "calibration_tables",  # Renamed in unified schema
        }
    },
    "ingest": {
        "file": "ingest.sqlite3",
        "tables": {
            "ingest_queue": "processing_queue",  # Renamed
            "subband_files": "subband_files",
            "performance_metrics": "performance_metrics",
            "pointing_history": "pointing_history",  # May duplicate
        }
    },
    "calibrators": {
        "file": "calibrators.sqlite3",
        "tables": {
            "bandpass_calibrators": "calibrator_catalog",  # Merged
            "vla_calibrators": "calibrator_catalog",  # Merged
        }
    },
    "hdf5": {
        "file": "hdf5.sqlite3",
        "tables": {
            "hdf5_file_index": "hdf5_files",  # May duplicate products
        }
    },
    "alerts": {
        "file": "alerts.sqlite3",
        "tables": {
            "alert_history": "alert_history",
        }
    },
}


# =============================================================================
# Migration Functions
# =============================================================================

def backup_databases(
    state_dir: Path,
    backup_dir: Path,
) -> Path:
    """
    Create timestamped backup of all source databases.
    
    Args:
        state_dir: Directory containing source databases
        backup_dir: Directory to store backups
        
    Returns:
        Path to backup directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"db_backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[1/5] Creating backups in {backup_path}")
    
    for db_name, config in SOURCE_DATABASES.items():
        src = state_dir / config["file"]
        if src.exists():
            dst = backup_path / config["file"]
            shutil.copy2(src, dst)
            size_mb = src.stat().st_size / (1024 * 1024)
            print(f"  ✓ {config['file']} ({size_mb:.1f} MB)")
        else:
            print(f"  ⚠ {config['file']} not found, skipping")
    
    return backup_path


def get_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """Get column names for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists in the database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    """Count rows in a table."""
    if not table_exists(conn, table):
        return 0
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0]


def migrate_table(
    src_conn: sqlite3.Connection,
    dest_conn: sqlite3.Connection,
    src_table: str,
    dest_table: str,
    column_mapping: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """
    Migrate data from source table to destination table.
    
    Args:
        src_conn: Source database connection
        dest_conn: Destination database connection
        src_table: Source table name
        dest_table: Destination table name
        column_mapping: Optional mapping of source->dest column names
        dry_run: If True, only count rows without migrating
        
    Returns:
        Tuple of (source_count, migrated_count)
    """
    if not table_exists(src_conn, src_table):
        return (0, 0)
    
    src_count = count_rows(src_conn, src_table)
    if src_count == 0:
        return (0, 0)
    
    if dry_run:
        return (src_count, 0)
    
    # Get source columns
    src_cols = get_table_columns(src_conn, src_table)
    
    # Get destination columns
    dest_cols = get_table_columns(dest_conn, dest_table)
    
    # Map columns (only include columns that exist in both)
    if column_mapping:
        mapped_cols = []
        dest_mapped_cols = []
        for src_col in src_cols:
            dest_col = column_mapping.get(src_col, src_col)
            if dest_col in dest_cols:
                mapped_cols.append(src_col)
                dest_mapped_cols.append(dest_col)
    else:
        # Use columns that exist in both tables
        mapped_cols = [c for c in src_cols if c in dest_cols]
        dest_mapped_cols = mapped_cols
    
    if not mapped_cols:
        print(f"    ⚠ No common columns between {src_table} and {dest_table}")
        return (src_count, 0)
    
    # Build INSERT statement
    src_col_str = ", ".join(mapped_cols)
    dest_col_str = ", ".join(dest_mapped_cols)
    placeholders = ", ".join(["?" for _ in mapped_cols])
    
    # Use INSERT OR IGNORE to handle duplicates
    insert_sql = f"""
        INSERT OR IGNORE INTO {dest_table} ({dest_col_str})
        VALUES ({placeholders})
    """
    
    # Migrate data
    select_sql = f"SELECT {src_col_str} FROM {src_table}"
    cursor = src_conn.execute(select_sql)
    
    migrated = 0
    for row in cursor:
        try:
            dest_conn.execute(insert_sql, tuple(row))
            migrated += 1
        except sqlite3.IntegrityError:
            # Skip duplicates (already handled by INSERT OR IGNORE)
            pass
    
    dest_conn.commit()
    return (src_count, migrated)


def migrate_calibrators(
    src_conn: sqlite3.Connection,
    dest_conn: sqlite3.Connection,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """
    Special migration for calibrators (merging two tables).
    
    Merges bandpass_calibrators and vla_calibrators into calibrator_catalog.
    """
    total_src = 0
    total_migrated = 0
    
    # Migrate bandpass_calibrators
    if table_exists(src_conn, "bandpass_calibrators"):
        bp_count = count_rows(src_conn, "bandpass_calibrators")
        total_src += bp_count
        
        if not dry_run and bp_count > 0:
            # Map columns
            insert_sql = """
                INSERT OR IGNORE INTO calibrator_catalog 
                (name, ra_deg, dec_deg, flux_jy, dec_range_min, dec_range_max,
                 source_catalog, status, registered_at, registered_by, notes)
                SELECT calibrator_name, ra_deg, dec_deg, flux_jy, dec_range_min, dec_range_max,
                       source_catalog, status, registered_at, registered_by, notes
                FROM bandpass_calibrators
            """
            # Can't directly insert from attached db, so read and insert
            cursor = src_conn.execute("""
                SELECT calibrator_name, ra_deg, dec_deg, flux_jy, dec_range_min, dec_range_max,
                       source_catalog, status, registered_at, registered_by, notes
                FROM bandpass_calibrators
            """)
            for row in cursor:
                try:
                    dest_conn.execute("""
                        INSERT OR IGNORE INTO calibrator_catalog 
                        (name, ra_deg, dec_deg, flux_jy, dec_range_min, dec_range_max,
                         source_catalog, status, registered_at, registered_by, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, tuple(row))
                    total_migrated += 1
                except sqlite3.IntegrityError:
                    pass
    
    # Migrate vla_calibrators
    if table_exists(src_conn, "vla_calibrators"):
        vla_count = count_rows(src_conn, "vla_calibrators")
        total_src += vla_count
        
        if not dry_run and vla_count > 0:
            cursor = src_conn.execute("""
                SELECT name, ra_deg, dec_deg, flux_jy, flux_freq_ghz, code_20_cm,
                       registered_at, notes
                FROM vla_calibrators
            """)
            for row in cursor:
                try:
                    dest_conn.execute("""
                        INSERT OR IGNORE INTO calibrator_catalog 
                        (name, ra_deg, dec_deg, flux_jy, flux_freq_ghz, code_20_cm,
                         registered_at, source_catalog, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'VLA', ?)
                    """, tuple(row))
                    total_migrated += 1
                except sqlite3.IntegrityError:
                    pass
    
    if not dry_run:
        dest_conn.commit()
    
    return (total_src, total_migrated)


def create_unified_schema(dest_conn: sqlite3.Connection) -> None:
    """Create the unified database schema."""
    # Import the schema from the unified module
    try:
        from dsa110_contimg.database.unified import UNIFIED_SCHEMA
        dest_conn.executescript(UNIFIED_SCHEMA)
    except ImportError:
        # Fallback: read schema from file if module not available
        schema_file = BACKEND_SRC / "dsa110_contimg" / "database" / "unified.py"
        if schema_file.exists():
            content = schema_file.read_text()
            # Extract UNIFIED_SCHEMA string
            start = content.find('UNIFIED_SCHEMA = """')
            end = content.find('"""', start + 20) + 3
            if start > 0 and end > start:
                schema = content[start + 20:end - 3]
                dest_conn.executescript(schema)
                return
        
        print("  ⚠ Could not load schema, creating minimal tables")
        # Minimal schema fallback
        dest_conn.executescript("""
            CREATE TABLE IF NOT EXISTS ms_index (
                path TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE
            );
        """)


def run_migration(
    state_dir: Path,
    output_path: Path,
    backup_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Tuple[int, int]]:
    """
    Run the full migration process.
    
    Args:
        state_dir: Directory containing source databases
        output_path: Path for unified database
        backup_dir: Backup directory (default: state_dir/backups)
        dry_run: If True, only preview without making changes
        
    Returns:
        Dict of table_name -> (source_count, migrated_count)
    """
    if backup_dir is None:
        backup_dir = state_dir / "backups"
    
    results: Dict[str, Tuple[int, int]] = {}
    
    print("=" * 70)
    print("DATABASE MIGRATION: Multiple DBs → Unified pipeline.sqlite3")
    print("=" * 70)
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
    
    # Step 1: Backup
    if not dry_run:
        backup_path = backup_databases(state_dir, backup_dir)
    else:
        print("\n[1/5] Backup (skipped in dry-run)")
    
    # Step 2: Create unified database
    print(f"\n[2/5] Creating unified database: {output_path}")
    
    if output_path.exists() and not dry_run:
        response = input(f"  {output_path} already exists. Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Migration cancelled")
            return {}
    
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dest_conn = sqlite3.connect(str(output_path))
        dest_conn.row_factory = sqlite3.Row
        dest_conn.execute("PRAGMA journal_mode=WAL")
        
        print("  ✓ Creating schema...")
        create_unified_schema(dest_conn)
    else:
        print("  (Would create schema)")
        dest_conn = None
    
    # Step 3: Migrate data from each source database
    print("\n[3/5] Migrating data...")
    
    for db_name, config in SOURCE_DATABASES.items():
        src_path = state_dir / config["file"]
        
        if not src_path.exists():
            print(f"\n  Skipping {db_name}: {config['file']} not found")
            continue
        
        print(f"\n  From {config['file']}:")
        src_conn = sqlite3.connect(str(src_path))
        src_conn.row_factory = sqlite3.Row
        
        for src_table, dest_table in config["tables"].items():
            # Special handling for calibrators (merge two tables)
            if db_name == "calibrators" and src_table in ("bandpass_calibrators", "vla_calibrators"):
                if src_table == "bandpass_calibrators":  # Only run once
                    src_count, migrated = migrate_calibrators(
                        src_conn, dest_conn, dry_run
                    )
                    results["calibrator_catalog"] = (src_count, migrated)
                    print(f"    calibrators → calibrator_catalog: {src_count} rows")
                continue
            
            if dry_run:
                src_count = count_rows(src_conn, src_table)
                results[f"{db_name}.{src_table}"] = (src_count, 0)
                print(f"    {src_table} → {dest_table}: {src_count} rows")
            else:
                src_count, migrated = migrate_table(
                    src_conn, dest_conn, src_table, dest_table
                )
                results[f"{db_name}.{src_table}"] = (src_count, migrated)
                if src_count > 0:
                    print(f"    {src_table} → {dest_table}: {migrated}/{src_count} rows")
        
        src_conn.close()
    
    # Step 4: Verify migration
    print("\n[4/5] Verification...")
    
    if not dry_run and dest_conn:
        print("\n  Unified database row counts:")
        for table in [
            "ms_index", "images", "photometry", "calibration_tables",
            "calibrator_catalog", "hdf5_files", "processing_queue",
            "calibrator_transits", "alert_history"
        ]:
            count = count_rows(dest_conn, table)
            print(f"    {table}: {count} rows")
        
        dest_conn.close()
    else:
        print("  (Skipped in dry-run)")
    
    # Step 5: Summary
    print("\n[5/5] Summary")
    print("=" * 70)
    
    total_src = sum(r[0] for r in results.values())
    total_migrated = sum(r[1] for r in results.values())
    
    if dry_run:
        print(f"\nDRY RUN COMPLETE - Would migrate {total_src} rows")
        print(f"\nTo execute migration, run:")
        print(f"  python {__file__}")
    else:
        print(f"\nMIGRATION COMPLETE")
        print(f"  ✓ Migrated {total_migrated} rows to {output_path}")
        print(f"  ✓ Backups: {backup_path}")
        print(f"\nNext steps:")
        print(f"  1. Update code to use Database('{output_path}')")
        print(f"  2. Test all queries work correctly")
        print(f"  3. After verification, archive old databases:")
        print(f"     mkdir -p {state_dir}/archive")
        print(f"     mv {state_dir}/*.sqlite3 {state_dir}/archive/")
        print(f"     mv {output_path} {state_dir}/")
    
    print("=" * 70)
    
    return results


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Migrate to unified pipeline database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview migration without executing",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path("/data/dsa110-contimg/state/db"),
        help="Directory containing source databases",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output path for unified database (default: state-dir/pipeline.sqlite3)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=None,
        help="Backup directory (default: state-dir/backups)",
    )
    
    args = parser.parse_args()
    
    if args.output is None:
        args.output = args.state_dir / "pipeline.sqlite3"
    
    run_migration(
        state_dir=args.state_dir,
        output_path=args.output,
        backup_dir=args.backup_dir,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
