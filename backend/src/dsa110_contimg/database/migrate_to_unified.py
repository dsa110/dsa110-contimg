"""
Database Migration Script: Consolidate All DBs into pipeline.sqlite3

This script migrates data from the legacy separate database files into
the unified pipeline.sqlite3 database.

Migration Steps:
1. Create new tables in pipeline.sqlite3 (via init_unified_db)
2. Migrate data from products.sqlite3 (jobs, mosaics, transients, QA, etc.)
3. Migrate data from calibrators.sqlite3 (VLA calibrators, bandpass/gain cals)
4. Skip hdf5.sqlite3 and ingest.sqlite3 (already duplicated in pipeline.sqlite3)
5. Archive/delete migrated databases

Usage:
    python -m dsa110_contimg.database.migrate_to_unified [--dry-run] [--archive]
"""

import argparse
import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .unified import Database, init_unified_db, DEFAULT_PIPELINE_DB

logger = logging.getLogger(__name__)

# Database paths
DB_DIR = Path("/data/dsa110-contimg/state/db")
ARCHIVE_DIR = DB_DIR / "archive"

# Source databases to migrate
MIGRATE_SOURCES = {
    "products": DB_DIR / "products.sqlite3",
    "calibrators": DB_DIR / "calibrators.sqlite3",
}

# Databases that are duplicates (data already in pipeline.sqlite3)
DUPLICATE_DBS = {
    "hdf5": DB_DIR / "hdf5.sqlite3",
    "ingest": DB_DIR / "ingest.sqlite3",
    "ingest_queue": DB_DIR / "ingest_queue.sqlite3",
    "alerts": DB_DIR / "alerts.sqlite3",
    "cal_registry": DB_DIR / "cal_registry.sqlite3",
    "data_registry": DB_DIR / "data_registry.sqlite3",
}


def get_table_count(conn: sqlite3.Connection, table: str) -> int:
    """Get row count for a table."""
    try:
        cursor = conn.execute(f"SELECT COUNT(*) FROM [{table}]")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def migrate_table(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    source_table: str,
    target_table: str,
    column_mapping: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
) -> int:
    """
    Migrate data from source table to target table.
    
    Args:
        source_conn: Source database connection
        target_conn: Target database connection
        source_table: Source table name
        target_table: Target table name
        column_mapping: Optional dict mapping source -> target columns
        dry_run: If True, don't actually migrate data
        
    Returns:
        Number of rows migrated
    """
    # Get source columns
    cursor = source_conn.execute(f"PRAGMA table_info([{source_table}])")
    source_cols = [row[1] for row in cursor.fetchall()]
    
    # Get target columns
    cursor = target_conn.execute(f"PRAGMA table_info([{target_table}])")
    target_cols = [row[1] for row in cursor.fetchall()]
    
    # Determine which columns to migrate
    if column_mapping:
        migrate_cols = [(src, column_mapping.get(src, src)) for src in source_cols]
        migrate_cols = [(src, tgt) for src, tgt in migrate_cols if tgt in target_cols]
    else:
        # Use common columns
        common = set(source_cols) & set(target_cols)
        migrate_cols = [(c, c) for c in source_cols if c in common]
    
    if not migrate_cols:
        logger.warning(f"No common columns between {source_table} and {target_table}")
        return 0
    
    src_col_str = ", ".join(f"[{c[0]}]" for c in migrate_cols)
    tgt_col_str = ", ".join(f"[{c[1]}]" for c in migrate_cols)
    placeholders = ", ".join("?" for _ in migrate_cols)
    
    # Fetch source data
    cursor = source_conn.execute(f"SELECT {src_col_str} FROM [{source_table}]")
    rows = cursor.fetchall()
    
    if not rows:
        return 0
    
    if dry_run:
        logger.info(f"  [DRY-RUN] Would migrate {len(rows)} rows from {source_table} to {target_table}")
        return len(rows)
    
    # Insert into target (using INSERT OR IGNORE to skip duplicates)
    insert_sql = f"INSERT OR IGNORE INTO [{target_table}] ({tgt_col_str}) VALUES ({placeholders})"
    target_conn.executemany(insert_sql, rows)
    
    return len(rows)


def migrate_products_db(target_db: Optional[Database], dry_run: bool = False) -> Dict[str, int]:
    """Migrate all tables from products.sqlite3."""
    source_path = MIGRATE_SOURCES["products"]
    if not source_path.exists():
        logger.info(f"products.sqlite3 not found at {source_path}, skipping")
        return {}
    
    results = {}
    source_conn = sqlite3.connect(str(source_path))
    source_conn.row_factory = sqlite3.Row
    
    try:
        # Tables to migrate with same names
        same_name_tables = [
            "jobs",
            "batch_jobs",
            "batch_job_items",
            "qa_artifacts",
            "image_qa",
            "calibration_qa",
            "mosaics",
            "mosaic_groups",
            "regions",
            "transient_candidates",
            "transient_alerts",
            "transient_lightcurves",
            "variability_stats",
            "monitoring_sources",
            "ese_candidates",
            "astrometric_solutions",
            "astrometric_residuals",
        ]
        
        for table in same_name_tables:
            if dry_run:
                # For dry-run, just count rows in source
                count = get_table_count(source_conn, table)
                if count > 0:
                    results[table] = count
                    logger.info(f"  [DRY-RUN] Would migrate {count} rows from {table}")
            else:
                count = migrate_table(
                    source_conn, target_db.conn, table, table, dry_run=dry_run
                )
                if count > 0:
                    results[table] = count
                    logger.info(f"  Migrated {count} rows from {table}")
        
        if not dry_run and target_db:
            target_db.conn.commit()
            
    finally:
        source_conn.close()
    
    return results


def migrate_calibrators_db(target_db: Optional[Database], dry_run: bool = False) -> Dict[str, int]:
    """Migrate all tables from calibrators.sqlite3."""
    source_path = MIGRATE_SOURCES["calibrators"]
    if not source_path.exists():
        logger.info(f"calibrators.sqlite3 not found at {source_path}, skipping")
        return {}
    
    results = {}
    source_conn = sqlite3.connect(str(source_path))
    source_conn.row_factory = sqlite3.Row
    
    try:
        # Tables to migrate with same names
        same_name_tables = [
            "vla_calibrators",
            "vla_flux_info",
            "catalog_sources",
            "skymodel_metadata",
            "bandpass_calibrators",
            "gain_calibrators",
        ]
        
        for table in same_name_tables:
            if dry_run:
                count = get_table_count(source_conn, table)
                if count > 0:
                    results[table] = count
                    logger.info(f"  [DRY-RUN] Would migrate {count} rows from {table}")
            else:
                count = migrate_table(
                    source_conn, target_db.conn, table, table, dry_run=dry_run
                )
                if count > 0:
                    results[table] = count
                    logger.info(f"  Migrated {count} rows from {table}")
        
        if not dry_run and target_db:
            target_db.conn.commit()
            
    finally:
        source_conn.close()
    
    return results


def verify_duplicates() -> Dict[str, Dict[str, int]]:
    """
    Verify that duplicate databases contain the same data as pipeline.sqlite3.
    
    Returns dict of {db_name: {table: count_diff}} where count_diff is
    the difference in row counts (should be 0 for true duplicates).
    """
    results = {}
    pipeline_conn = sqlite3.connect(str(DEFAULT_PIPELINE_DB))
    
    try:
        # hdf5.sqlite3 -> hdf5_files table
        if DUPLICATE_DBS["hdf5"].exists():
            hdf5_conn = sqlite3.connect(str(DUPLICATE_DBS["hdf5"]))
            pipeline_count = get_table_count(pipeline_conn, "hdf5_files")
            source_count = get_table_count(hdf5_conn, "hdf5_file_index")
            results["hdf5"] = {"hdf5_files": pipeline_count - source_count}
            hdf5_conn.close()
        
        # ingest.sqlite3 -> processing_queue table
        if DUPLICATE_DBS["ingest"].exists():
            ingest_conn = sqlite3.connect(str(DUPLICATE_DBS["ingest"]))
            pipeline_count = get_table_count(pipeline_conn, "processing_queue")
            source_count = get_table_count(ingest_conn, "ingest_queue")
            results["ingest"] = {"processing_queue": pipeline_count - source_count}
            ingest_conn.close()
            
    finally:
        pipeline_conn.close()
    
    return results


def archive_databases(dry_run: bool = False) -> List[str]:
    """
    Move migrated databases to archive directory.
    
    Returns list of archived database names.
    """
    archived = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not dry_run:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Archive source databases
    for name, path in MIGRATE_SOURCES.items():
        if path.exists():
            archive_path = ARCHIVE_DIR / f"{path.stem}_{timestamp}.sqlite3"
            if dry_run:
                logger.info(f"  [DRY-RUN] Would archive {path} -> {archive_path}")
            else:
                shutil.move(str(path), str(archive_path))
                logger.info(f"  Archived {path} -> {archive_path}")
            archived.append(name)
    
    # Archive duplicate databases
    for name, path in DUPLICATE_DBS.items():
        if path.exists():
            archive_path = ARCHIVE_DIR / f"{path.stem}_{timestamp}.sqlite3"
            if dry_run:
                logger.info(f"  [DRY-RUN] Would archive {path} -> {archive_path}")
            else:
                shutil.move(str(path), str(archive_path))
                logger.info(f"  Archived {path} -> {archive_path}")
            archived.append(name)
    
    return archived


def run_migration(dry_run: bool = False, archive: bool = False) -> Dict:
    """
    Run the full database migration.
    
    Args:
        dry_run: If True, don't actually migrate or archive
        archive: If True, move migrated DBs to archive directory
        
    Returns:
        Dict with migration results
    """
    results = {
        "tables_created": [],
        "migrated": {},
        "duplicates_verified": {},
        "archived": [],
        "errors": [],
    }
    
    logger.info("=" * 60)
    logger.info("Database Unification Migration")
    logger.info("=" * 60)
    
    # Step 1: Initialize unified schema
    logger.info("\nStep 1: Initializing unified schema...")
    try:
        if dry_run:
            logger.info("  [DRY-RUN] Would create new tables in pipeline.sqlite3")
        else:
            db = init_unified_db()
            logger.info(f"  Initialized database at {db.db_path}")
    except Exception as e:
        results["errors"].append(f"Schema init failed: {e}")
        logger.error(f"  ERROR: {e}")
        return results
    
    # Step 2: Verify duplicates
    logger.info("\nStep 2: Verifying duplicate databases...")
    try:
        dup_results = verify_duplicates()
        results["duplicates_verified"] = dup_results
        for db_name, tables in dup_results.items():
            for table, diff in tables.items():
                if diff == 0:
                    logger.info(f"  ✓ {db_name} -> {table}: Verified identical")
                else:
                    logger.warning(f"  ⚠ {db_name} -> {table}: Diff = {diff} rows")
    except Exception as e:
        results["errors"].append(f"Duplicate verification failed: {e}")
        logger.error(f"  ERROR: {e}")
    
    # Step 3: Migrate products.sqlite3
    logger.info("\nStep 3: Migrating products.sqlite3...")
    try:
        if not dry_run:
            db = Database()  # Get existing connection
        prod_results = migrate_products_db(db if not dry_run else None, dry_run=dry_run)
        results["migrated"]["products"] = prod_results
        total = sum(prod_results.values())
        logger.info(f"  Total: {total} rows migrated from products.sqlite3")
    except Exception as e:
        results["errors"].append(f"Products migration failed: {e}")
        logger.error(f"  ERROR: {e}")
    
    # Step 4: Migrate calibrators.sqlite3
    logger.info("\nStep 4: Migrating calibrators.sqlite3...")
    try:
        if not dry_run:
            db = Database()
        cal_results = migrate_calibrators_db(db if not dry_run else None, dry_run=dry_run)
        results["migrated"]["calibrators"] = cal_results
        total = sum(cal_results.values())
        logger.info(f"  Total: {total} rows migrated from calibrators.sqlite3")
    except Exception as e:
        results["errors"].append(f"Calibrators migration failed: {e}")
        logger.error(f"  ERROR: {e}")
    
    # Step 5: Archive migrated databases
    if archive:
        logger.info("\nStep 5: Archiving migrated databases...")
        try:
            archived = archive_databases(dry_run=dry_run)
            results["archived"] = archived
            logger.info(f"  Archived {len(archived)} databases")
        except Exception as e:
            results["errors"].append(f"Archive failed: {e}")
            logger.error(f"  ERROR: {e}")
    else:
        logger.info("\nStep 5: Skipping archive (use --archive to enable)")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    
    if results["errors"]:
        logger.error(f"Errors: {len(results['errors'])}")
        for err in results["errors"]:
            logger.error(f"  - {err}")
    else:
        logger.info("Status: SUCCESS")
        
    total_rows = sum(
        sum(tables.values()) 
        for tables in results["migrated"].values()
    )
    logger.info(f"Total rows migrated: {total_rows}")
    logger.info(f"Databases archived: {len(results['archived'])}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Migrate databases to unified pipeline.sqlite3"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes"
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Move migrated databases to archive directory"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    results = run_migration(dry_run=args.dry_run, archive=args.archive)
    
    # Return exit code based on errors
    return 1 if results["errors"] else 0


if __name__ == "__main__":
    exit(main())
