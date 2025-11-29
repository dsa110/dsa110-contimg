"""
Migration Script: products.sqlite3 → calibrators.sqlite3

Migrates bandpass calibrators from products.sqlite3 to the new
calibrators.sqlite3 database.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from dsa110_contimg.database.calibrators import (
    ensure_calibrators_db,
    get_calibrators_db_path,
    register_bandpass_calibrator,
)

logger = logging.getLogger(__name__)


def check_products_db(products_db_path: Path) -> bool:
    """Check if products.sqlite3 exists and has bandpass_calibrators table.

    Args:
        products_db_path: Path to products.sqlite3

    Returns:
        True if database exists and has the table
    """
    if not products_db_path.exists():
        logger.error(f"Products database not found: {products_db_path}")
        return False

    try:
        conn = sqlite3.connect(str(products_db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bandpass_calibrators'"
        )
        exists = cursor.fetchone() is not None
        conn.close()

        if not exists:
            logger.warning(f"Table 'bandpass_calibrators' not found in {products_db_path}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error checking products database: {e}")
        return False


def extract_bandpass_calibrators(products_db_path: Path) -> List[dict]:
    """Extract bandpass calibrators from products.sqlite3.

    Args:
        products_db_path: Path to products.sqlite3

    Returns:
        List of calibrator dictionaries
    """
    conn = sqlite3.connect(str(products_db_path))
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute("SELECT * FROM bandpass_calibrators")
        calibrators = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Extracted {len(calibrators)} bandpass calibrators from products.sqlite3")
        return calibrators
    except Exception as e:
        logger.error(f"Error extracting bandpass calibrators: {e}")
        raise
    finally:
        conn.close()


def migrate_to_calibrators_db(
    calibrators: List[dict],
    calibrators_db_path: Optional[Path] = None,
    dry_run: bool = False,
) -> int:
    """Migrate calibrators to calibrators.sqlite3.

    Args:
        calibrators: List of calibrator dictionaries from products.sqlite3
        calibrators_db_path: Path to calibrators.sqlite3 (auto-resolved if None)
        dry_run: If True, don't actually write to database

    Returns:
        Number of calibrators migrated
    """
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    migrated_count = 0

    for cal in calibrators:
        calibrator_name = cal.get("calibrator_name") or cal.get("name")
        if not calibrator_name:
            logger.warning(f"Skipping calibrator with no name: {cal}")
            continue

        try:
            if not dry_run:
                register_bandpass_calibrator(
                    calibrator_name=calibrator_name,
                    ra_deg=cal.get("ra_deg") or cal.get("ra"),
                    dec_deg=cal.get("dec_deg") or cal.get("dec"),
                    dec_range_min=cal.get("dec_range_min"),
                    dec_range_max=cal.get("dec_range_max"),
                    source_catalog=cal.get("source_catalog"),
                    flux_jy=cal.get("flux_jy") or cal.get("flux"),
                    registered_by=cal.get("registered_by") or "migration",
                    status=cal.get("status", "active"),
                    notes=cal.get("notes"),
                    calibrators_db=calibrators_db_path,
                )
            migrated_count += 1
            logger.debug(f"Migrated calibrator: {calibrator_name}")
        except Exception as e:
            logger.error(f"Failed to migrate calibrator {calibrator_name}: {e}")

    return migrated_count


def verify_migration(
    products_db_path: Path,
    calibrators_db_path: Optional[Path] = None,
) -> bool:
    """Verify that migration was successful.

    Args:
        products_db_path: Path to source products.sqlite3
        calibrators_db_path: Path to target calibrators.sqlite3

    Returns:
        True if verification passes
    """
    # Extract from source
    source_calibrators = extract_bandpass_calibrators(products_db_path)
    source_names = {cal.get("calibrator_name") or cal.get("name") for cal in source_calibrators}
    source_names.discard(None)

    # Extract from target
    from dsa110_contimg.database.calibrators import get_bandpass_calibrators

    target_calibrators = get_bandpass_calibrators(calibrators_db=calibrators_db_path)
    target_names = {cal["calibrator_name"] for cal in target_calibrators}

    # Compare
    missing = source_names - target_names
    extra = target_names - source_names

    if missing:
        logger.warning(f"Missing calibrators in target: {missing}")
    if extra:
        logger.info(f"Extra calibrators in target (not in source): {extra}")

    success = len(missing) == 0
    logger.info(
        f"Verification: {len(source_names)} source, {len(target_names)} target, "
        f"{len(missing)} missing, {len(extra)} extra"
    )

    return success


def main():
    """CLI entry point for migration."""
    parser = argparse.ArgumentParser(
        description="Migrate bandpass calibrators from products.sqlite3 to calibrators.sqlite3"
    )
    parser.add_argument(
        "--products-db",
        type=Path,
        default=Path("/data/dsa110-contimg/products.sqlite3"),
        help="Path to products.sqlite3 (default: /data/dsa110-contimg/products.sqlite3)",
    )
    parser.add_argument(
        "--calibrators-db",
        type=Path,
        default=None,
        help="Path to calibrators.sqlite3 (default: auto-resolved)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - don't actually migrate",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration after completion",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Check source database
    if not check_products_db(args.products_db):
        logger.error("Source database check failed. Aborting.")
        return 1

    # Extract calibrators
    logger.info(f"Extracting bandpass calibrators from {args.products_db}")
    calibrators = extract_bandpass_calibrators(args.products_db)

    if not calibrators:
        logger.warning("No calibrators found to migrate")
        return 0

    # Migrate
    logger.info(f"Migrating {len(calibrators)} calibrators...")
    migrated_count = migrate_to_calibrators_db(
        calibrators, calibrators_db_path=args.calibrators_db, dry_run=args.dry_run
    )

    logger.info(f"Migrated {migrated_count}/{len(calibrators)} calibrators")

    # Verify
    if args.verify and not args.dry_run:
        logger.info("Verifying migration...")
        success = verify_migration(args.products_db, args.calibrators_db)
        if success:
            logger.info(":check_mark: Verification passed")
        else:
            logger.warning(":warning_sign: Verification found discrepancies")
            return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
