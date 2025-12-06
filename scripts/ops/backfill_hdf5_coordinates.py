#!/opt/miniforge/envs/casa6/bin/python
"""
Backfill missing ra_deg, dec_deg, and timestamp_mjd in pipeline.sqlite3::hdf5_files.

This script reads HDF5 file headers directly using h5py (fast path) and
updates the database with extracted coordinates and timestamps.

Usage:
    python scripts/ops/backfill_hdf5_coordinates.py [--batch-size 1000] [--dry-run]
"""

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

import h5py
import numpy as np
from astropy.time import Time

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DB_PATH = "/data/dsa110-contimg/state/db/pipeline.sqlite3"


def extract_metadata_fast(file_path: str) -> dict:
    """Extract coordinates and timestamp from HDF5 file (fast path).
    
    Returns:
        Dict with ra_deg, dec_deg, timestamp_mjd (or None if extraction fails)
    """
    result = {"ra_deg": None, "dec_deg": None, "timestamp_mjd": None}
    
    try:
        with h5py.File(file_path, "r") as f:
            # Extract declination
            if "Header/extra_keywords/phase_center_dec" in f:
                dec_rad = float(f["Header/extra_keywords/phase_center_dec"][()])
                result["dec_deg"] = float(np.degrees(dec_rad))
            
            # Extract RA (if stored)
            if "Header/extra_keywords/phase_center_ra" in f:
                ra_rad = float(f["Header/extra_keywords/phase_center_ra"][()])
                result["ra_deg"] = float(np.degrees(ra_rad))
            
            # Extract timestamp
            if "Header/time_array" in f:
                times = f["Header/time_array"][:]
                mid_jd = (times.min() + times.max()) / 2
                result["timestamp_mjd"] = mid_jd - 2400000.5
    
    except Exception as e:
        logger.debug(f"Failed to read {file_path}: {e}")
    
    return result


def backfill_from_timestamp_iso(conn: sqlite3.Connection, batch_size: int = 10000) -> int:
    """Quick backfill: Convert timestamp_iso to timestamp_mjd (no file I/O).
    
    This is extremely fast since it only requires string parsing.
    """
    cursor = conn.cursor()
    
    # Get files with timestamp_iso but missing timestamp_mjd
    cursor.execute("""
        SELECT path, timestamp_iso 
        FROM hdf5_files 
        WHERE timestamp_iso IS NOT NULL 
          AND timestamp_mjd IS NULL
        LIMIT ?
    """, (batch_size,))
    
    rows = cursor.fetchall()
    if not rows:
        return 0
    
    logger.info(f"Converting {len(rows)} timestamp_iso values to MJD...")
    
    updates = []
    for path, timestamp_iso in rows:
        try:
            t = Time(timestamp_iso, format="isot", scale="utc")
            updates.append((t.mjd, path))
        except Exception as e:
            logger.warning(f"Failed to parse timestamp {timestamp_iso}: {e}")
    
    cursor.executemany(
        "UPDATE hdf5_files SET timestamp_mjd = ? WHERE path = ?",
        updates
    )
    conn.commit()
    
    return len(updates)


def backfill_coordinates(
    conn: sqlite3.Connection,
    batch_size: int = 100,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Backfill ra_deg and dec_deg by reading one subband per group.
    
    Strategy: Read sb00 (or first available subband) for each group,
    then apply those coordinates to all 16 subbands in that group.
    This reduces I/O by 16x.
    
    Returns:
        Tuple of (updated_count, error_count)
    """
    cursor = conn.cursor()
    
    # Get groups missing coordinates (query sb00 as representative)
    cursor.execute("""
        SELECT DISTINCT group_id 
        FROM hdf5_files 
        WHERE ra_deg IS NULL OR dec_deg IS NULL
        LIMIT ?
    """, (batch_size,))
    
    groups = [row[0] for row in cursor.fetchall()]
    if not groups:
        return 0, 0
    
    logger.info(f"Processing batch of {len(groups)} groups (up to {len(groups) * 16} files)...")
    
    updated = 0
    errors = 0
    group_updates = []
    
    start_time = time.time()
    
    for i, group_id in enumerate(groups):
        # Get representative file (prefer sb00, fallback to any available)
        cursor.execute("""
            SELECT path FROM hdf5_files
            WHERE group_id = ?
              AND path IS NOT NULL
            ORDER BY subband_num ASC
            LIMIT 1
        """, (group_id,))
        
        row = cursor.fetchone()
        if not row:
            logger.debug(f"No files found for group {group_id}")
            errors += 1
            continue
        
        rep_path = row[0]
        
        if not Path(rep_path).exists():
            logger.debug(f"Representative file not found: {rep_path}")
            errors += 1
            continue
        
        # Extract metadata from representative file
        metadata = extract_metadata_fast(rep_path)
        
        if metadata["ra_deg"] is not None or metadata["dec_deg"] is not None:
            group_updates.append((
                metadata["ra_deg"],
                metadata["dec_deg"],
                metadata["timestamp_mjd"],
                group_id
            ))
            updated += 1
        else:
            errors += 1
        
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            logger.info(f"  Progress: {i+1}/{len(groups)} groups ({rate:.1f} groups/sec)")
    
    if group_updates and not dry_run:
        # Apply coordinates to ALL subbands in each group
        cursor.executemany("""
            UPDATE hdf5_files 
            SET ra_deg = ?, 
                dec_deg = ?, 
                timestamp_mjd = COALESCE(?, timestamp_mjd)
            WHERE group_id = ?
        """, group_updates)
        conn.commit()
        
        # Count actual files updated
        cursor.execute("""
            SELECT COUNT(*) FROM hdf5_files 
            WHERE group_id IN ({})
        """.format(','.join('?' * len(groups))), groups)
        files_updated = cursor.fetchone()[0]
    else:
        files_updated = updated * 16  # Estimate
    
    elapsed = time.time() - start_time
    if elapsed > 0:
        rate = len(groups) / elapsed
        logger.info(f"Batch complete: {updated} groups (~{files_updated} files), {errors} errors ({rate:.1f} groups/sec)")
    
    return files_updated, errors


def main():
    parser = argparse.ArgumentParser(
        description="Backfill missing HDF5 metadata in pipeline.sqlite3"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of groups to process per batch (default: 500, ~8000 files)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to database",
    )
    parser.add_argument(
        "--skip-timestamp-conversion",
        action="store_true",
        help="Skip fast timestamp_iso → timestamp_mjd conversion",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        help="Maximum number of batches to process (for testing)",
    )
    
    args = parser.parse_args()
    
    if not Path(DB_PATH).exists():
        logger.error(f"Database not found: {DB_PATH}")
        return 1
    
    logger.info("=" * 80)
    logger.info("HDF5 Metadata Backfill")
    logger.info("=" * 80)
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("")
    
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    try:
        # Step 1: Fast timestamp conversion (no file I/O)
        if not args.skip_timestamp_conversion:
            logger.info("Step 1: Converting timestamp_iso to timestamp_mjd...")
            total_converted = 0
            while True:
                converted = backfill_from_timestamp_iso(conn, batch_size=10000)
                total_converted += converted
                if converted == 0:
                    break
                logger.info(f"  Converted {total_converted} timestamps so far...")
            
            logger.info(f"✓ Timestamp conversion complete: {total_converted} records")
            logger.info("")
        
        # Step 2: Extract coordinates from HDF5 files
        logger.info("Step 2: Extracting coordinates from HDF5 files...")
        logger.info("  Strategy: Read one subband per group (16x faster)")
        
        # Get total count
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT group_id) FROM hdf5_files 
            WHERE ra_deg IS NULL OR dec_deg IS NULL
        """)
        total_groups = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM hdf5_files 
            WHERE ra_deg IS NULL OR dec_deg IS NULL
        """)
        total_files = cursor.fetchone()[0]
        
        logger.info(f"Groups missing coordinates: {total_groups:,} (~{total_files:,} files)")
        
        if total_groups == 0:
            logger.info("✓ All files already have coordinates!")
            return 0
        
        logger.info("")
        
        total_updated = 0
        total_errors = 0
        batch_num = 0
        
        while True:
            batch_num += 1
            logger.info(f"Batch {batch_num}:")
            
            updated, errors = backfill_coordinates(
                conn,
                batch_size=args.batch_size,
                dry_run=args.dry_run
            )
            
            total_updated += updated
            total_errors += errors
            
            if updated == 0 and errors == 0:
                break
            
            if args.max_batches and batch_num >= args.max_batches:
                logger.info(f"Reached max batches ({args.max_batches}), stopping.")
                break
            
            logger.info("")
        
        logger.info("=" * 80)
        logger.info("Backfill Complete")
        logger.info("=" * 80)
        logger.info(f"Total updated: {total_updated:,}")
        logger.info(f"Total errors: {total_errors:,}")
        
        if args.dry_run:
            logger.info("\n(DRY RUN - no changes were written)")
        
        return 0 if total_errors == 0 else 1
    
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
