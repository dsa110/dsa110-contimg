#!/usr/bin/env python
"""Initialize Phase 3 database tables for transient detection and astrometric calibration.

NOTE: As of v0.9, Phase 3 tables are automatically created by ensure_products_db()
in backend/src/dsa110_contimg/database/products.py. This script is kept for:
  1. Verification of existing databases
  2. Force-recreating tables if needed
  3. Backward compatibility

The following tables are now auto-created:
- transient_candidates (extended schema with variability tracking)
- transient_alerts
- transient_lightcurves
- astrometric_solutions
- astrometric_residuals
- monitoring_sources (new in v0.9)

Usage:
    python scripts/initialize_phase3_tables.py [--db-path PATH] [--force]

Arguments:
    --db-path PATH    Path to products database (default: state/db/products.sqlite3)
    --force           Drop existing tables before recreating (dangerous!)
    --verify          Verify tables exist without creating them

Example:
    # Verify tables exist (recommended - tables are auto-created now)
    python scripts/initialize_phase3_tables.py --verify

    # Initialize with custom database path (legacy usage)
    python scripts/initialize_phase3_tables.py --db-path /data/custom.sqlite3

Exit codes:
    0: Success
    1: Error during initialization
    2: Verification failed (tables missing)
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_transient_detection_schema() -> List[str]:
    """Get SQL schema for transient detection tables.

    Returns:
        List of CREATE TABLE and CREATE INDEX SQL statements
    """
    return [
        # transient_candidates table
        """
        CREATE TABLE IF NOT EXISTS transient_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            detection_type TEXT NOT NULL,
            flux_obs_mjy REAL NOT NULL,
            flux_baseline_mjy REAL,
            flux_ratio REAL,
            significance_sigma REAL NOT NULL,
            baseline_catalog TEXT,
            detected_at REAL NOT NULL,
            mosaic_id INTEGER,
            classification TEXT,
            variability_index REAL,
            last_updated REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY (mosaic_id) REFERENCES products(id)
        )
        """,
        # transient_candidates indices
        """
        CREATE INDEX IF NOT EXISTS idx_transients_type 
            ON transient_candidates(detection_type, significance_sigma DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_transients_coords 
            ON transient_candidates(ra_deg, dec_deg)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_transients_detected 
            ON transient_candidates(detected_at DESC)
        """,
        # transient_alerts table
        """
        CREATE TABLE IF NOT EXISTS transient_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            alert_level TEXT NOT NULL,
            alert_message TEXT NOT NULL,
            created_at REAL NOT NULL,
            acknowledged BOOLEAN DEFAULT 0,
            acknowledged_at REAL,
            acknowledged_by TEXT,
            follow_up_status TEXT,
            notes TEXT,
            FOREIGN KEY (candidate_id) REFERENCES transient_candidates(id)
        )
        """,
        # transient_alerts indices
        """
        CREATE INDEX IF NOT EXISTS idx_alerts_level 
            ON transient_alerts(alert_level, created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_alerts_status 
            ON transient_alerts(acknowledged, created_at DESC)
        """,
        # transient_lightcurves table
        """
        CREATE TABLE IF NOT EXISTS transient_lightcurves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            mjd REAL NOT NULL,
            flux_mjy REAL NOT NULL,
            flux_err_mjy REAL,
            frequency_ghz REAL NOT NULL,
            mosaic_id INTEGER,
            measured_at REAL NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES transient_candidates(id),
            FOREIGN KEY (mosaic_id) REFERENCES products(id)
        )
        """,
        # transient_lightcurves indices
        """
        CREATE INDEX IF NOT EXISTS idx_lightcurves_candidate 
            ON transient_lightcurves(candidate_id, mjd)
        """,
    ]


def get_astrometric_calibration_schema() -> List[str]:
    """Get SQL schema for astrometric calibration tables.

    Returns:
        List of CREATE TABLE and CREATE INDEX SQL statements
    """
    return [
        # astrometric_solutions table
        """
        CREATE TABLE IF NOT EXISTS astrometric_solutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mosaic_id INTEGER NOT NULL,
            reference_catalog TEXT NOT NULL,
            n_matches INTEGER NOT NULL,
            ra_offset_mas REAL NOT NULL,
            dec_offset_mas REAL NOT NULL,
            ra_offset_err_mas REAL NOT NULL,
            dec_offset_err_mas REAL NOT NULL,
            rotation_deg REAL,
            scale_factor REAL,
            rms_residual_mas REAL NOT NULL,
            applied BOOLEAN DEFAULT 0,
            computed_at REAL NOT NULL,
            applied_at REAL,
            notes TEXT,
            FOREIGN KEY (mosaic_id) REFERENCES products(id)
        )
        """,
        # astrometric_solutions indices
        """
        CREATE INDEX IF NOT EXISTS idx_astrometry_mosaic 
            ON astrometric_solutions(mosaic_id, computed_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_astrometry_applied 
            ON astrometric_solutions(applied, computed_at DESC)
        """,
        # astrometric_residuals table
        """
        CREATE TABLE IF NOT EXISTS astrometric_residuals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solution_id INTEGER NOT NULL,
            source_ra_deg REAL NOT NULL,
            source_dec_deg REAL NOT NULL,
            reference_ra_deg REAL NOT NULL,
            reference_dec_deg REAL NOT NULL,
            ra_offset_mas REAL NOT NULL,
            dec_offset_mas REAL NOT NULL,
            separation_mas REAL NOT NULL,
            source_flux_mjy REAL,
            reference_flux_mjy REAL,
            measured_at REAL NOT NULL,
            FOREIGN KEY (solution_id) REFERENCES astrometric_solutions(id)
        )
        """,
        # astrometric_residuals indices
        """
        CREATE INDEX IF NOT EXISTS idx_residuals_solution 
            ON astrometric_residuals(solution_id)
        """,
    ]


def verify_tables(conn: sqlite3.Connection) -> bool:
    """Verify all Phase 3 tables exist.

    Args:
        conn: Database connection

    Returns:
        True if all tables exist, False otherwise
    """
    required_tables = [
        "transient_candidates",
        "transient_alerts",
        "transient_lightcurves",
        "astrometric_solutions",
        "astrometric_residuals",
    ]

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}

    all_exist = True
    for table in required_tables:
        if table in existing_tables:
            logger.info(f":check: Table '{table}' exists")
        else:
            logger.error(f":cross: Table '{table}' missing")
            all_exist = False

    return all_exist


def drop_tables(conn: sqlite3.Connection) -> None:
    """Drop all Phase 3 tables (dangerous!).

    Args:
        conn: Database connection
    """
    tables = [
        "transient_lightcurves",
        "transient_alerts",
        "transient_candidates",
        "astrometric_residuals",
        "astrometric_solutions",
    ]

    logger.warning("Dropping existing Phase 3 tables...")
    cursor = conn.cursor()

    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            logger.warning(f"Dropped table: {table}")
        except sqlite3.Error as e:
            logger.error(f"Failed to drop {table}: {e}")

    conn.commit()


def initialize_tables(
    db_path: Path, force: bool = False, verify_only: bool = False
) -> int:
    """Initialize Phase 3 database tables.

    Args:
        db_path: Path to database file
        force: If True, drop existing tables before creating
        verify_only: If True, only verify tables exist

    Returns:
        Exit code (0 = success, 1 = error, 2 = verification failed)
    """
    try:
        # Check database exists
        if not db_path.exists():
            logger.error(f"Database not found: {db_path}")
            logger.info("Please create the database first or specify correct path")
            return 1

        logger.info(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(str(db_path), timeout=60.0)

        # Verify mode
        if verify_only:
            logger.info("Verifying Phase 3 tables...")
            if verify_tables(conn):
                logger.info(":check: All Phase 3 tables exist")
                return 0
            else:
                logger.error(":cross: Some Phase 3 tables are missing")
                return 2

        # Drop existing tables if force
        if force:
            drop_tables(conn)

        # Create transient detection tables
        logger.info("Creating transient detection tables...")
        transient_schema = get_transient_detection_schema()

        cursor = conn.cursor()
        for sql in transient_schema:
            cursor.execute(sql)

        logger.info(":check: Created transient_candidates table with indices")
        logger.info(":check: Created transient_alerts table with indices")
        logger.info(":check: Created transient_lightcurves table with indices")

        # Create astrometric calibration tables
        logger.info("Creating astrometric calibration tables...")
        astrometry_schema = get_astrometric_calibration_schema()

        for sql in astrometry_schema:
            cursor.execute(sql)

        logger.info(":check: Created astrometric_solutions table with indices")
        logger.info(":check: Created astrometric_residuals table with indices")

        # Commit changes
        conn.commit()
        logger.info(":check: All Phase 3 tables created successfully")

        # Verify
        logger.info("Verifying table creation...")
        if verify_tables(conn):
            logger.info(":check: Verification passed")
            return 0
        else:
            logger.error(":cross: Verification failed")
            return 2

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        if "conn" in locals():
            conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize Phase 3 database tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("state/db/products.sqlite3"),
        help="Path to products database (default: state/db/products.sqlite3)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop existing tables before recreating (dangerous!)",
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify tables exist without creating them",
    )

    args = parser.parse_args()

    # Warn if force
    if args.force and not args.verify:
        logger.warning(":warning:  --force will DROP all existing Phase 3 tables!")
        logger.warning(":warning:  Press Ctrl+C to cancel, or wait 5 seconds to continue...")
        import time

        try:
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Cancelled")
            return 0

    # Initialize
    exit_code = initialize_tables(
        db_path=args.db_path, force=args.force, verify_only=args.verify
    )

    if exit_code == 0:
        if args.verify:
            logger.info(":check: Phase 3 tables verified successfully")
        else:
            logger.info(":check: Phase 3 initialization complete")
    else:
        logger.error(":cross: Phase 3 initialization failed")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
