#!/usr/bin/env python
"""
Reindex HDF5 Group IDs - Normalize existing group_id values in the database.

This script updates existing hdf5_files (or hdf5_file_index) table entries
to use normalized group_id values, fixing the issue where files from the
same observation were assigned different group_ids due to timestamps being
a few seconds apart.

The normalization rounds timestamps to 10-second boundaries, ensuring all
subbands from the same observation share the same group_id.

Usage:
    # Dry-run (see what would change without modifying DB):
    python scripts/ops/reindex_hdf5_groups.py --dry-run

    # Actually update the database:
    python scripts/ops/reindex_hdf5_groups.py

    # Specify custom DB path:
    python scripts/ops/reindex_hdf5_groups.py --db-path /path/to/pipeline.sqlite3

    # Use different tolerance (default is 10 seconds):
    python scripts/ops/reindex_hdf5_groups.py --tolerance 5
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# Add src to path for imports
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT / "src"))

from dsa110_contimg.database.storage_validator import (
    normalize_group_timestamp,
    GROUP_TIMESTAMP_TOLERANCE_SECONDS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def detect_table_name(conn: sqlite3.Connection) -> str:
    """Detect whether to use hdf5_files or hdf5_file_index table."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('hdf5_files', 'hdf5_file_index')")
    tables = [row[0] for row in cursor.fetchall()]
    
    if "hdf5_files" in tables:
        return "hdf5_files"
    elif "hdf5_file_index" in tables:
        return "hdf5_file_index"
    else:
        raise ValueError("No HDF5 index table found (expected hdf5_files or hdf5_file_index)")


def get_distinct_group_ids(conn: sqlite3.Connection, table_name: str) -> list[tuple[str, int]]:
    """
    Get all distinct group_ids and their file counts.
    
    Returns:
        List of (group_id, file_count) tuples.
    """
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT group_id, COUNT(*) as file_count
        FROM {table_name}
        GROUP BY group_id
        ORDER BY group_id
    """)
    return cursor.fetchall()


def compute_normalization_plan(
    group_ids: list[tuple[str, int]],
    tolerance_seconds: int,
) -> dict:
    """
    Compute which group_ids need to be updated and what they'll become.
    
    Returns:
        Dictionary with:
        - updates: list of (old_group_id, new_group_id) tuples that need changes
        - unchanged: count of group_ids that don't need changes
        - merges: dict mapping new_group_id -> list of old_group_ids that merge into it
    """
    updates = []
    unchanged_count = 0
    merges = defaultdict(list)
    
    for group_id, _file_count in group_ids:
        try:
            normalized = normalize_group_timestamp(group_id, tolerance_seconds)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to normalize group_id '{group_id}': {e}")
            continue
        
        if normalized != group_id:
            updates.append((group_id, normalized))
            merges[normalized].append(group_id)
        else:
            unchanged_count += 1
    
    return {
        "updates": updates,
        "unchanged": unchanged_count,
        "merges": dict(merges),
    }


def apply_updates(
    conn: sqlite3.Connection,
    table_name: str,
    updates: list[tuple[str, str]],
    batch_size: int = 500,
    dry_run: bool = True,
) -> dict:
    """
    Apply group_id updates to the database.
    
    Args:
        conn: Database connection.
        table_name: Table to update.
        updates: List of (old_group_id, new_group_id) tuples.
        batch_size: Number of updates per commit.
        dry_run: If True, don't actually modify database.
    
    Returns:
        Dictionary with results.
    """
    results = {
        "dry_run": dry_run,
        "total_updates": len(updates),
        "applied": 0,
        "rows_affected": 0,
        "errors": [],
    }
    
    if dry_run:
        logger.info(f"[DRY-RUN] Would update {len(updates)} group_ids")
        results["applied"] = len(updates)
        return results
    
    cursor = conn.cursor()
    
    for i, (old_gid, new_gid) in enumerate(updates):
        try:
            cursor.execute(
                f"UPDATE {table_name} SET group_id = ? WHERE group_id = ?",
                (new_gid, old_gid)
            )
            results["rows_affected"] += cursor.rowcount
            results["applied"] += 1
            
            # Commit in batches
            if (i + 1) % batch_size == 0:
                conn.commit()
                logger.info(f"Committed batch {(i + 1) // batch_size}: {i + 1}/{len(updates)} updates")
                
        except sqlite3.Error as e:
            results["errors"].append(f"Failed to update '{old_gid}' -> '{new_gid}': {e}")
            logger.error(f"Update error: {e}")
    
    # Final commit
    conn.commit()
    logger.info(f"Applied {results['applied']} updates affecting {results['rows_affected']} rows")
    
    return results


def verify_normalization(conn: sqlite3.Connection, table_name: str, tolerance_seconds: int) -> dict:
    """
    Verify that all group_ids are now normalized.
    
    Returns:
        Dictionary with verification results.
    """
    group_ids = get_distinct_group_ids(conn, table_name)
    
    non_normalized = []
    for group_id, file_count in group_ids:
        try:
            normalized = normalize_group_timestamp(group_id, tolerance_seconds)
            if normalized != group_id:
                non_normalized.append((group_id, normalized, file_count))
        except (ValueError, TypeError):
            non_normalized.append((group_id, "PARSE_ERROR", file_count))
    
    return {
        "total_groups": len(group_ids),
        "non_normalized_count": len(non_normalized),
        "non_normalized_samples": non_normalized[:10],
        "is_fully_normalized": len(non_normalized) == 0,
    }


def print_merge_preview(merges: dict, limit: int = 20) -> None:
    """Print a preview of which groups will be merged."""
    multi_merges = {k: v for k, v in merges.items() if len(v) > 1}
    
    if not multi_merges:
        logger.info("No groups will be merged (all updates are 1:1 renames)")
        return
    
    logger.info(f"\n=== Groups that will be MERGED ({len(multi_merges)} merges) ===")
    
    for i, (new_gid, old_gids) in enumerate(sorted(multi_merges.items())[:limit]):
        logger.info(f"  {new_gid} <- {old_gids}")
    
    if len(multi_merges) > limit:
        logger.info(f"  ... and {len(multi_merges) - limit} more merges")


def main():
    parser = argparse.ArgumentParser(
        description="Reindex HDF5 group_ids with normalized timestamps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="/data/dsa110-contimg/state/db/pipeline.sqlite3",
        help="Path to SQLite database (default: %(default)s)",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=GROUP_TIMESTAMP_TOLERANCE_SECONDS,
        help=f"Timestamp tolerance in seconds (default: {GROUP_TIMESTAMP_TOLERANCE_SECONDS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without modifying database",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify current state, don't update",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check DB exists
    if not os.path.exists(args.db_path):
        logger.error(f"Database not found: {args.db_path}")
        sys.exit(1)
    
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Tolerance: {args.tolerance} seconds")
    
    # Connect to database
    conn = sqlite3.connect(args.db_path, timeout=60)
    
    try:
        # Detect table name
        table_name = detect_table_name(conn)
        logger.info(f"Using table: {table_name}")
        
        # Get current group_ids
        logger.info("Fetching current group_ids...")
        group_ids = get_distinct_group_ids(conn, table_name)
        logger.info(f"Found {len(group_ids)} distinct group_ids")
        
        # Compute normalization plan
        logger.info("Computing normalization plan...")
        plan = compute_normalization_plan(group_ids, args.tolerance)
        
        logger.info(f"\n=== Normalization Plan ===")
        logger.info(f"  Group IDs to update: {len(plan['updates'])}")
        logger.info(f"  Group IDs unchanged: {plan['unchanged']}")
        logger.info(f"  Merge destinations:  {len(plan['merges'])}")
        
        # Show merge preview
        print_merge_preview(plan["merges"])
        
        if args.verify_only:
            # Just verify and exit
            verification = verify_normalization(conn, table_name, args.tolerance)
            logger.info(f"\n=== Verification ===")
            logger.info(f"  Total groups: {verification['total_groups']}")
            logger.info(f"  Non-normalized: {verification['non_normalized_count']}")
            logger.info(f"  Fully normalized: {verification['is_fully_normalized']}")
            if verification['non_normalized_samples']:
                logger.info("  Sample non-normalized:")
                for old, new, count in verification['non_normalized_samples']:
                    logger.info(f"    {old} -> {new} ({count} files)")
            sys.exit(0 if verification['is_fully_normalized'] else 1)
        
        if not plan["updates"]:
            logger.info("No updates needed - all group_ids are already normalized!")
            sys.exit(0)
        
        # Show sample updates
        logger.info("\n=== Sample Updates ===")
        for old_gid, new_gid in plan["updates"][:10]:
            logger.info(f"  {old_gid} -> {new_gid}")
        if len(plan["updates"]) > 10:
            logger.info(f"  ... and {len(plan['updates']) - 10} more")
        
        # Apply updates
        if args.dry_run:
            logger.info("\n[DRY-RUN MODE] - No changes will be made")
        else:
            logger.info("\n=== Applying Updates ===")
        
        results = apply_updates(
            conn, table_name, plan["updates"],
            dry_run=args.dry_run
        )
        
        logger.info(f"\n=== Results ===")
        logger.info(f"  Dry run: {results['dry_run']}")
        logger.info(f"  Updates applied: {results['applied']}")
        logger.info(f"  Rows affected: {results['rows_affected']}")
        if results["errors"]:
            logger.warning(f"  Errors: {len(results['errors'])}")
            for err in results["errors"][:5]:
                logger.warning(f"    {err}")
        
        # Post-update verification (if not dry-run)
        if not args.dry_run:
            logger.info("\n=== Post-Update Verification ===")
            verification = verify_normalization(conn, table_name, args.tolerance)
            logger.info(f"  Total groups: {verification['total_groups']}")
            logger.info(f"  Non-normalized: {verification['non_normalized_count']}")
            logger.info(f"  Fully normalized: {verification['is_fully_normalized']}")
            
            if not verification['is_fully_normalized']:
                logger.warning("Some group_ids are still not normalized!")
                sys.exit(1)
        
        logger.info("\nDone!")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
