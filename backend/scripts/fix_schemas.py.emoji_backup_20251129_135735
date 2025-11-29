#!/usr/bin/env python3
"""
Database Schema Fix Utility for DSA-110 Continuum Imaging Pipeline.

This script diagnoses and repairs common database issues:
- Schema mismatches (missing columns)
- Locked databases (stale lock files)
- Migration failures
- Corrupted indexes

Usage:
    python fix_schemas.py                    # Check all databases
    python fix_schemas.py --fix              # Apply fixes
    python fix_schemas.py --database products --fix
    python fix_schemas.py --clear-locks      # Clear stale lock files
"""

from __future__ import annotations

import argparse
import fcntl
import logging
import os
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Default database paths
DEFAULT_DB_PATHS = {
    "products": Path("/data/dsa110-contimg/state/products.sqlite3"),
    "cal_registry": Path("/data/dsa110-contimg/state/cal_registry.sqlite3"),
    "hdf5": Path("/data/dsa110-contimg/state/hdf5_index.sqlite3"),
    "ingest": Path("/data/dsa110-contimg/state/ingest.sqlite3"),
    "data_registry": Path("/data/dsa110-contimg/state/data_registry.sqlite3"),
}

# Expected schemas for each database
EXPECTED_SCHEMAS: Dict[str, Dict[str, List[Tuple[str, str]]]] = {
    "products": {
        "ms_index": [
            ("path", "TEXT PRIMARY KEY"),
            ("start_mjd", "REAL"),
            ("end_mjd", "REAL"),
            ("mid_mjd", "REAL"),
            ("processed_at", "REAL"),
            ("status", "TEXT"),
            ("stage", "TEXT"),
            ("stage_updated_at", "REAL"),
            ("cal_applied", "INTEGER DEFAULT 0"),
            ("imagename", "TEXT"),
            ("ra_deg", "REAL"),
            ("dec_deg", "REAL"),
            ("pointing_ra_deg", "REAL"),
            ("pointing_dec_deg", "REAL"),
        ],
        "images": [
            ("id", "INTEGER PRIMARY KEY"),
            ("path", "TEXT"),
            ("ms_path", "TEXT"),
            ("created_at", "REAL"),
            ("type", "TEXT"),
        ],
        "photometry": [
            ("id", "INTEGER PRIMARY KEY"),
            ("image_path", "TEXT"),
            ("source_id", "TEXT"),
        ],
        "transient_candidates": [
            ("id", "INTEGER PRIMARY KEY"),
            ("source_name", "TEXT"),
            ("ra_deg", "REAL"),
            ("dec_deg", "REAL"),
            ("flux_obs_mjy", "REAL"),
            ("flux_baseline_mjy", "REAL"),
            ("flux_ratio", "REAL"),
            ("significance_sigma", "REAL"),
            ("detection_type", "TEXT"),
            ("baseline_catalog", "TEXT"),
            ("mosaic_id", "INTEGER"),
            ("classification", "TEXT"),
            ("variability_index", "REAL"),
            ("last_updated", "REAL"),
            ("notes", "TEXT"),
        ],
        "monitoring_sources": [
            ("id", "INTEGER PRIMARY KEY"),
            ("source_name", "TEXT"),
            ("ra_deg", "REAL"),
            ("dec_deg", "REAL"),
        ],
    },
    "cal_registry": {
        "caltables": [
            ("id", "INTEGER PRIMARY KEY"),
            ("path", "TEXT"),
            ("set_name", "TEXT"),
            ("source_ms_path", "TEXT"),
            ("solver_command", "TEXT"),
            ("solver_version", "TEXT"),
            ("solver_params", "TEXT"),
            ("quality_metrics", "TEXT"),
        ],
    },
    "ingest": {
        "ingest_queue": [
            ("group_id", "TEXT PRIMARY KEY"),
            ("state", "TEXT"),
            ("received_at", "REAL"),
            ("last_update", "REAL"),
            ("expected_subbands", "INTEGER"),
            ("retry_count", "INTEGER DEFAULT 0"),
            ("error", "TEXT"),
            ("checkpoint_path", "TEXT"),
            ("processing_stage", "TEXT DEFAULT 'collecting'"),
            ("chunk_minutes", "REAL"),
            ("has_calibrator", "INTEGER"),
            ("calibrators", "TEXT"),
        ],
        "subband_files": [
            ("id", "INTEGER PRIMARY KEY"),
            ("group_id", "TEXT"),
            ("subband", "INTEGER"),
            ("file_path", "TEXT"),
        ],
        "performance_metrics": [
            ("id", "INTEGER PRIMARY KEY"),
            ("group_id", "TEXT"),
            ("writer_type", "TEXT"),
        ],
    },
}


@dataclass
class DiagnosticResult:
    """Result of a database diagnostic check."""
    database: str
    table: str
    issue_type: str
    description: str
    severity: str  # "error", "warning", "info"
    fix_sql: Optional[str] = None
    fixed: bool = False


def get_db_path(db_name: str) -> Path:
    """Get database path from environment or defaults."""
    env_map = {
        "products": "PIPELINE_PRODUCTS_DB",
        "cal_registry": "PIPELINE_CAL_REGISTRY_DB",
        "hdf5": "PIPELINE_HDF5_DB",
        "ingest": "PIPELINE_INGEST_DB",
        "data_registry": "PIPELINE_DATA_REGISTRY_DB",
    }
    env_var = env_map.get(db_name)
    if env_var and os.environ.get(env_var):
        return Path(os.environ[env_var])
    return DEFAULT_DB_PATHS.get(db_name, Path(f"/data/dsa110-contimg/state/{db_name}.sqlite3"))


def check_database_locked(db_path: Path) -> Tuple[bool, Optional[str]]:
    """Check if a database is locked."""
    if not db_path.exists():
        return False, None
    
    lock_path = db_path.with_suffix(".lock")
    wal_path = db_path.with_suffix(".sqlite3-wal")
    
    # Check for explicit lock file
    if lock_path.exists():
        try:
            with open(lock_path, "r") as f:
                content = f.read().strip()
            return True, f"Lock file exists: {lock_path} (PID: {content})"
        except Exception:
            return True, f"Lock file exists: {lock_path}"
    
    # Try to open database
    try:
        conn = sqlite3.connect(str(db_path), timeout=2.0)
        conn.execute("SELECT 1")
        conn.close()
        return False, None
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            return True, f"Database is locked: {e}"
        return False, None


def check_wal_size(db_path: Path, max_mb: float = 100.0) -> Optional[DiagnosticResult]:
    """Check if WAL file is too large (indicates checkpoint issues)."""
    wal_path = db_path.with_suffix(".sqlite3-wal")
    if wal_path.exists():
        size_mb = wal_path.stat().st_size / (1024 * 1024)
        if size_mb > max_mb:
            return DiagnosticResult(
                database=db_path.name,
                table="",
                issue_type="wal_size",
                description=f"WAL file is {size_mb:.1f} MB (threshold: {max_mb} MB)",
                severity="warning",
                fix_sql="PRAGMA wal_checkpoint(TRUNCATE)",
            )
    return None


def get_table_columns(conn: sqlite3.Connection, table: str) -> Dict[str, str]:
    """Get columns and their types for a table."""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        return {row[1]: row[2] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        return {}


def check_missing_columns(
    conn: sqlite3.Connection, db_name: str, table: str, expected: List[Tuple[str, str]]
) -> List[DiagnosticResult]:
    """Check for missing columns in a table."""
    results = []
    existing = get_table_columns(conn, table)
    
    if not existing:
        # Table doesn't exist
        return [DiagnosticResult(
            database=db_name,
            table=table,
            issue_type="missing_table",
            description=f"Table '{table}' does not exist",
            severity="error",
        )]
    
    for col_name, col_def in expected:
        if col_name not in existing:
            # Extract just the type for ALTER TABLE
            col_type = col_def.split()[0] if " " in col_def else col_def
            if "PRIMARY KEY" in col_def.upper():
                continue  # Can't add PRIMARY KEY columns
            
            results.append(DiagnosticResult(
                database=db_name,
                table=table,
                issue_type="missing_column",
                description=f"Column '{col_name}' missing from table '{table}'",
                severity="warning",
                fix_sql=f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}",
            ))
    
    return results


def check_indexes(conn: sqlite3.Connection, db_name: str) -> List[DiagnosticResult]:
    """Check for missing or corrupt indexes."""
    results = []
    
    # Check integrity
    try:
        cursor = conn.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        if result != "ok":
            results.append(DiagnosticResult(
                database=db_name,
                table="",
                issue_type="integrity",
                description=f"Database integrity check failed: {result}",
                severity="error",
            ))
    except sqlite3.OperationalError as e:
        results.append(DiagnosticResult(
            database=db_name,
            table="",
            issue_type="integrity",
            description=f"Could not check integrity: {e}",
            severity="error",
        ))
    
    return results


def diagnose_database(db_name: str) -> List[DiagnosticResult]:
    """Run all diagnostics on a database."""
    results = []
    db_path = get_db_path(db_name)
    
    logger.info(f"Checking database: {db_name} ({db_path})")
    
    # Check if file exists
    if not db_path.exists():
        results.append(DiagnosticResult(
            database=db_name,
            table="",
            issue_type="missing_database",
            description=f"Database file does not exist: {db_path}",
            severity="info",
        ))
        return results
    
    # Check for locks
    is_locked, lock_msg = check_database_locked(db_path)
    if is_locked:
        results.append(DiagnosticResult(
            database=db_name,
            table="",
            issue_type="locked",
            description=lock_msg,
            severity="error",
        ))
        return results  # Can't proceed if locked
    
    # Check WAL size
    wal_result = check_wal_size(db_path)
    if wal_result:
        results.append(wal_result)
    
    # Open and check schema
    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.execute("PRAGMA busy_timeout=30000")
        
        # Check integrity
        results.extend(check_indexes(conn, db_name))
        
        # Check expected tables/columns
        if db_name in EXPECTED_SCHEMAS:
            for table, columns in EXPECTED_SCHEMAS[db_name].items():
                results.extend(check_missing_columns(conn, db_name, table, columns))
        
        conn.close()
    except sqlite3.OperationalError as e:
        results.append(DiagnosticResult(
            database=db_name,
            table="",
            issue_type="connection_error",
            description=f"Could not connect to database: {e}",
            severity="error",
        ))
    
    return results


def apply_fix(db_path: Path, fix_sql: str) -> bool:
    """Apply a SQL fix to a database."""
    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute(fix_sql)
        conn.commit()
        conn.close()
        return True
    except sqlite3.OperationalError as e:
        logger.error(f"Failed to apply fix: {e}")
        return False


def clear_stale_locks(db_names: Optional[List[str]] = None) -> int:
    """Clear stale lock files for databases."""
    if db_names is None:
        db_names = list(DEFAULT_DB_PATHS.keys())
    
    cleared = 0
    for db_name in db_names:
        db_path = get_db_path(db_name)
        lock_path = db_path.with_suffix(".lock")
        
        if lock_path.exists():
            try:
                # Check if the PID in the lock file is still running
                with open(lock_path, "r") as f:
                    content = f.read().strip()
                
                if content.isdigit():
                    pid = int(content)
                    try:
                        os.kill(pid, 0)  # Check if process exists
                        logger.warning(f"Lock file {lock_path} held by running process {pid}")
                        continue
                    except OSError:
                        pass  # Process doesn't exist
                
                # Safe to remove
                lock_path.unlink()
                logger.info(f"Removed stale lock file: {lock_path}")
                cleared += 1
            except Exception as e:
                logger.error(f"Failed to clear lock {lock_path}: {e}")
    
    return cleared


def check_disk_space(paths: Optional[List[Path]] = None) -> List[DiagnosticResult]:
    """Check disk space for database directories."""
    results = []
    
    if paths is None:
        paths = [Path("/data/dsa110-contimg/state")]
    
    for path in paths:
        if not path.exists():
            continue
        
        try:
            usage = shutil.disk_usage(path)
            free_gb = usage.free / (1024 ** 3)
            percent_used = (usage.used / usage.total) * 100
            
            if free_gb < 1.0:
                results.append(DiagnosticResult(
                    database="",
                    table="",
                    issue_type="disk_space",
                    description=f"Critical: Only {free_gb:.2f} GB free on {path}",
                    severity="error",
                ))
            elif free_gb < 5.0:
                results.append(DiagnosticResult(
                    database="",
                    table="",
                    issue_type="disk_space",
                    description=f"Warning: Only {free_gb:.2f} GB free on {path} ({percent_used:.1f}% used)",
                    severity="warning",
                ))
            else:
                results.append(DiagnosticResult(
                    database="",
                    table="",
                    issue_type="disk_space",
                    description=f"Disk space OK: {free_gb:.2f} GB free on {path}",
                    severity="info",
                ))
        except OSError as e:
            results.append(DiagnosticResult(
                database="",
                table="",
                issue_type="disk_space",
                description=f"Could not check disk space for {path}: {e}",
                severity="warning",
            ))
    
    return results


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database schema fix utility for DSA-110 pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--database", "-d",
        choices=list(DEFAULT_DB_PATHS.keys()) + ["all"],
        default="all",
        help="Database to check (default: all)",
    )
    parser.add_argument(
        "--fix", "-f",
        action="store_true",
        help="Apply fixes for detected issues",
    )
    parser.add_argument(
        "--clear-locks",
        action="store_true",
        help="Clear stale lock files",
    )
    parser.add_argument(
        "--check-disk",
        action="store_true",
        help="Check disk space",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args(argv)
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Clear locks if requested
    if args.clear_locks:
        db_names = None if args.database == "all" else [args.database]
        cleared = clear_stale_locks(db_names)
        logger.info(f"Cleared {cleared} stale lock files")
    
    # Determine databases to check
    if args.database == "all":
        db_names = list(DEFAULT_DB_PATHS.keys())
    else:
        db_names = [args.database]
    
    # Run diagnostics
    all_results: List[DiagnosticResult] = []
    
    # Check disk space first
    if args.check_disk:
        all_results.extend(check_disk_space())
    
    for db_name in db_names:
        results = diagnose_database(db_name)
        all_results.extend(results)
    
    # Report results
    errors = [r for r in all_results if r.severity == "error"]
    warnings = [r for r in all_results if r.severity == "warning"]
    infos = [r for r in all_results if r.severity == "info"]
    
    print("\n" + "=" * 60)
    print("DATABASE DIAGNOSTIC REPORT")
    print("=" * 60)
    
    if errors:
        print(f"\n:red_circle: ERRORS ({len(errors)}):")
        for r in errors:
            print(f"  - [{r.database or 'system'}] {r.issue_type}: {r.description}")
    
    if warnings:
        print(f"\n:yellow_circle: WARNINGS ({len(warnings)}):")
        for r in warnings:
            print(f"  - [{r.database}] {r.issue_type}: {r.description}")
            if r.fix_sql:
                print(f"    Fix: {r.fix_sql}")
    
    if infos and args.verbose:
        print(f"\n:green_circle: INFO ({len(infos)}):")
        for r in infos:
            print(f"  - {r.description}")
    
    # Apply fixes if requested
    if args.fix:
        fixable = [r for r in all_results if r.fix_sql and r.severity in ("warning", "error")]
        if fixable:
            print(f"\n:e-mail_symbol: Applying {len(fixable)} fixes...")
            for r in fixable:
                db_path = get_db_path(r.database)
                logger.info(f"Applying: {r.fix_sql}")
                if apply_fix(db_path, r.fix_sql):
                    r.fixed = True
                    print(f"  :check: Fixed: {r.description}")
                else:
                    print(f"  :cross: Failed: {r.description}")
            
            fixed_count = sum(1 for r in fixable if r.fixed)
            print(f"\nFixed {fixed_count}/{len(fixable)} issues")
        else:
            print("\nNo fixable issues found")
    
    # Summary
    print("\n" + "-" * 60)
    if errors:
        print(f":cross: {len(errors)} errors require manual intervention")
        return 1
    elif warnings:
        print(f":warning:  {len(warnings)} warnings detected" + (" (use --fix to repair)" if not args.fix else ""))
        return 0
    else:
        print(":check: All databases healthy")
        return 0


if __name__ == "__main__":
    sys.exit(main())
