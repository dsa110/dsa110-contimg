#!/usr/bin/env python3
"""
Backfill RA, Dec, and MJD metadata in the hdf5_files table.

This script reads metadata from sb00 files (one per group) and updates
all subbands in that group with the same RA/Dec/MJD values.

Usage:
    python backfill_hdf5_metadata.py [--batch-size 100] [--dry-run]
"""

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

import h5py
import numpy as np
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u

# DSA-110 telescope location
DSA110_LON_DEG = -116.8662  # degrees East
DSA110_LAT_DEG = 37.2334  # degrees North

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def extract_metadata(hdf5_path: Path, location: EarthLocation) -> dict:
    """
    Extract RA, Dec, and MJD from an HDF5 file.

    Args:
        hdf5_path: Path to the HDF5 file (should be sb00).
        location: EarthLocation for LST calculation.

    Returns:
        Dict with keys: ra_deg, dec_deg, timestamp_mjd.

    Raises:
        Exception: If metadata cannot be read.
    """
    with h5py.File(hdf5_path, "r") as f:
        # Declination (radians)
        dec_rad = f["Header/extra_keywords/phase_center_dec"][()]
        dec_deg = float(np.degrees(dec_rad))

        # Hour Angle (radians)
        ha_rad = f["Header/extra_keywords/ha_phase_center"][()]

        # Time array (Julian Date)
        times_jd = f["Header/time_array"][:]
        mid_jd = (times_jd.min() + times_jd.max()) / 2
        mid_mjd = mid_jd - 2400000.5

        # Calculate RA from HA and LST
        # RA = LST - HA
        t = Time(mid_jd, format="jd")
        lst_rad = t.sidereal_time("apparent", longitude=location.lon).radian
        ra_rad = lst_rad - ha_rad
        ra_deg = float(np.degrees(ra_rad)) % 360.0

    return {
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "timestamp_mjd": mid_mjd,
    }


def backfill_metadata(
    db_path: Path,
    batch_size: int = 100,
    dry_run: bool = False,
) -> dict:
    """
    Backfill RA/Dec/MJD metadata for all groups missing data.

    Args:
        db_path: Path to pipeline.sqlite3 database.
        batch_size: Number of groups to process per batch.
        dry_run: If True, don't write to database.

    Returns:
        Dict with statistics: groups_processed, groups_failed, files_updated.
    """
    location = EarthLocation(lon=DSA110_LON_DEG * u.deg, lat=DSA110_LAT_DEG * u.deg)

    conn = sqlite3.connect(str(db_path), timeout=30)
    cursor = conn.cursor()

    # Count total groups needing backfill
    cursor.execute("""
        SELECT COUNT(DISTINCT group_id)
        FROM hdf5_files
        WHERE subband_num = 0 AND ra_deg IS NULL
    """)
    total_groups = cursor.fetchone()[0]

    if total_groups == 0:
        logger.info("No groups need backfilling - all metadata already present")
        conn.close()
        return {"groups_processed": 0, "groups_failed": 0, "files_updated": 0}

    logger.info(f"Found {total_groups:,} groups needing metadata backfill")
    if dry_run:
        logger.info("DRY RUN - no database changes will be made")

    stats = {
        "groups_processed": 0,
        "groups_failed": 0,
        "files_updated": 0,
    }

    start_time = time.time()
    last_report = start_time

    while True:
        # Fetch next batch of sb00 files
        cursor.execute(
            """
            SELECT group_id, path
            FROM hdf5_files
            WHERE subband_num = 0 AND ra_deg IS NULL
            LIMIT ?
        """,
            (batch_size,),
        )
        rows = cursor.fetchall()

        if not rows:
            break  # All done

        updates = []
        for group_id, fpath in rows:
            try:
                metadata = extract_metadata(Path(fpath), location)
                updates.append(
                    (
                        metadata["ra_deg"],
                        metadata["dec_deg"],
                        metadata["timestamp_mjd"],
                        group_id,
                    )
                )
                stats["groups_processed"] += 1
            except Exception as e:
                logger.warning(f"Failed to read {fpath}: {e}")
                stats["groups_failed"] += 1
                continue

        # Batch update database
        if updates and not dry_run:
            cursor.executemany(
                """
                UPDATE hdf5_files
                SET ra_deg = ?, dec_deg = ?, timestamp_mjd = ?
                WHERE group_id = ?
            """,
                updates,
            )
            stats["files_updated"] += cursor.rowcount
            conn.commit()

        # Progress reporting
        now = time.time()
        if now - last_report > 30:  # Report every 30 seconds
            elapsed = now - start_time
            rate = stats["groups_processed"] / elapsed if elapsed > 0 else 0
            remaining = total_groups - stats["groups_processed"]
            eta_min = (remaining / rate / 60) if rate > 0 else 0

            logger.info(
                f"Progress: {stats['groups_processed']:,}/{total_groups:,} groups "
                f"({stats['groups_processed']/total_groups*100:.1f}%) | "
                f"Rate: {rate:.1f} groups/s | "
                f"ETA: {eta_min:.1f} min | "
                f"Files updated: {stats['files_updated']:,}"
            )
            last_report = now

    conn.close()

    elapsed = time.time() - start_time
    logger.info(
        f"Backfill complete in {elapsed/60:.1f} minutes:\n"
        f"  Groups processed: {stats['groups_processed']:,}\n"
        f"  Groups failed: {stats['groups_failed']:,}\n"
        f"  Files updated: {stats['files_updated']:,}"
    )

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Backfill RA/Dec/MJD metadata in hdf5_files table"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("/data/dsa110-contimg/state/db/pipeline.sqlite3"),
        help="Path to pipeline database (default: /data/dsa110-contimg/state/db/pipeline.sqlite3)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of groups to process per batch (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing to database",
    )

    args = parser.parse_args()

    if not args.db_path.exists():
        logger.error(f"Database not found: {args.db_path}")
        sys.exit(1)

    try:
        stats = backfill_metadata(
            db_path=args.db_path,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        if stats["groups_failed"] > 0:
            logger.warning(
                f"{stats['groups_failed']} groups failed - check logs for details"
            )
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nBackfill interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
