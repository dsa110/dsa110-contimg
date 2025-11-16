"""HDF5 file indexing service for fast subband group queries.

This module provides functions to scan and index HDF5 files in the input directory,
enabling fast database queries instead of filesystem scans.
"""

import logging
import os
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from astropy.time import Time

from dsa110_contimg.database.products import ensure_products_db

logger = logging.getLogger(__name__)


def parse_hdf5_filename(filename: str) -> Optional[Tuple[str, str]]:
    """Parse HDF5 filename to extract group_id and subband_code.

    Args:
        filename: HDF5 filename (e.g., "2025-10-02T15:41:35_sb00.hdf5")

    Returns:
        Tuple of (group_id, subband_code) or None if parsing fails.
        group_id is the timestamp part (e.g., "2025-10-02T15:41:35")
        subband_code is the subband identifier (e.g., "sb00")
    """
    if not filename.endswith(".hdf5") or "_sb" not in filename:
        return None

    base = os.path.basename(filename)
    if "_sb" not in base:
        return None

    # Extract group ID (timestamp part before _sb)
    group_id = base.split("_sb")[0]

    # Extract subband code
    sb_part = base.rsplit("_sb", 1)[1].split(".")[0]
    if sb_part.startswith("sb"):
        subband_code = sb_part
    else:
        # Handle formats like "00" -> "sb00"
        subband_code = f"sb{sb_part.zfill(2)}"

    return (group_id, subband_code)


def _is_hdf5_subband_file(filename: str) -> bool:
    """Check if filename is an HDF5 subband file.

    Args:
        filename: Filename to check

    Returns:
        True if filename is an HDF5 subband file
    """
    return filename.endswith(".hdf5") and "_sb" in filename


def _scan_hdf5_files(
    input_dir: Path, max_files: Optional[int] = None
) -> Tuple[List[Tuple[str, str]], set]:
    """Scan directory for HDF5 files.

    Args:
        input_dir: Directory to scan
        max_files: Maximum number of files to scan (for testing/partial scans)

    Returns:
        Tuple of (list of (full_path, filename) tuples, set of current_paths)
    """
    hdf5_files = []
    current_paths = set()

    for root, _, files in os.walk(os.fspath(input_dir)):
        for fn in files:
            if not _is_hdf5_subband_file(fn):
                continue
            full_path = os.path.join(root, fn)
            # Normalize path to handle symlinks and relative paths
            full_path_resolved = os.path.abspath(full_path)
            hdf5_files.append((full_path_resolved, fn))
            current_paths.add(full_path_resolved)

            if max_files and len(hdf5_files) >= max_files:
                break

        if max_files and len(hdf5_files) >= max_files:
            break

    return hdf5_files, current_paths


def _parse_hdf5_metadata(full_path: str, filename: str) -> Optional[Dict[str, Any]]:
    """Parse metadata from HDF5 filename and file stats.

    Args:
        full_path: Full path to HDF5 file
        filename: Filename of HDF5 file

    Returns:
        Dictionary with metadata or None if parsing fails.
        Keys: group_id, subband_code, file_size, modified_time, timestamp_iso, timestamp_mjd
    """
    # Parse filename
    parsed = parse_hdf5_filename(filename)
    if not parsed:
        return None

    group_id, subband_code = parsed

    # Get file metadata
    try:
        stat_info = os.stat(full_path)
        file_size = stat_info.st_size
        modified_time = stat_info.st_mtime
    except OSError as e:
        logger.debug(f"Could not stat {full_path}: {e}")
        return None

    # Parse timestamp from group_id
    timestamp_iso = None
    timestamp_mjd = None
    try:
        # Try to parse as ISO format: YYYY-MM-DDTHH:MM:SS
        if "T" in group_id:
            timestamp_iso = group_id
            timestamp_mjd = Time(timestamp_iso, format="isot").mjd
    except Exception:
        pass

    return {
        "group_id": group_id,
        "subband_code": subband_code,
        "file_size": file_size,
        "modified_time": modified_time,
        "timestamp_iso": timestamp_iso,
        "timestamp_mjd": timestamp_mjd,
    }


def _is_path_under_directory(db_path: str, input_dir_path: Path) -> Tuple[bool, Optional[Path]]:
    """Check if a database path is under the input directory.

    Args:
        db_path: Path from database
        input_dir_path: Resolved input directory path

    Returns:
        Tuple of (is_under_input_dir, resolved_path)
    """
    try:
        db_path_obj = Path(db_path)

        # Check if path is under input_dir (using Path for reliable comparison)
        try:
            db_path_resolved = db_path_obj.resolve()
            # Check if db_path is under input_dir using relative_to
            try:
                db_path_resolved.relative_to(input_dir_path)
                return True, db_path_resolved
            except ValueError:
                # Path is not under input_dir
                return False, None
        except (OSError, ValueError):
            # Path resolution failed, try string comparison as fallback
            is_under = str(db_path).startswith(str(input_dir_path))
            if is_under:
                resolved = db_path_obj.resolve() if db_path_obj.exists() else None
                return True, resolved
            return False, None
    except Exception:
        return False, None


def _is_file_missing(db_path: str, db_path_resolved: Optional[Path], current_paths: set) -> bool:
    """Check if a file is missing from the filesystem.

    Args:
        db_path: Original path from database
        db_path_resolved: Resolved path (if available)
        current_paths: Set of paths that currently exist on filesystem

    Returns:
        True if file is missing, False otherwise
    """
    # First check if resolved path is in current_paths set
    if db_path_resolved:
        return db_path_resolved not in current_paths

    # If we couldn't resolve, check if file exists directly
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        return True

    # Double-check in case of path normalization issues
    return not os.path.exists(db_path)


def _mark_file_as_deleted(conn: sqlite3.Connection, db_path: str) -> None:
    """Mark a single file as not stored in the database.

    Args:
        conn: Database connection
        db_path: Path to mark as deleted
    """
    conn.execute("UPDATE hdf5_file_index SET stored = 0 WHERE path = ?", (db_path,))


def _process_deleted_file_check(
    conn: sqlite3.Connection,
    db_path: str,
    input_dir_path: Path,
    current_paths: set,
) -> bool:
    """Check if a file should be marked as deleted and mark it if so.

    Args:
        conn: Database connection
        db_path: Path from database
        input_dir_path: Resolved input directory path
        current_paths: Set of paths that currently exist on filesystem

    Returns:
        True if file was marked as deleted, False otherwise
    """
    try:
        is_under, db_path_resolved = _is_path_under_directory(db_path, input_dir_path)
        if not is_under:
            return False

        # Check if file still exists on filesystem
        if _is_file_missing(db_path, db_path_resolved, current_paths):
            _mark_file_as_deleted(conn, db_path)
            return True
        return False
    except Exception as e:
        # If path operations fail, check if file exists directly
        if not os.path.exists(db_path):
            _mark_file_as_deleted(conn, db_path)
            return True
        logger.debug(f"Could not process path {db_path}: {e}")
        return False


def _mark_deleted_files(conn: sqlite3.Connection, input_dir: Path, current_paths: set) -> int:
    """Mark files in database that no longer exist on filesystem as not stored.

    Args:
        conn: Database connection
        input_dir: Input directory path
        current_paths: Set of paths that currently exist on filesystem

    Returns:
        Number of files marked as not stored
    """
    all_db_paths = conn.execute("SELECT path FROM hdf5_file_index WHERE stored = 1").fetchall()

    deleted_count = 0
    input_dir_path = Path(input_dir).resolve()

    for (db_path,) in all_db_paths:
        if _process_deleted_file_check(conn, db_path, input_dir_path, current_paths):
            deleted_count += 1

    return deleted_count


def index_hdf5_files(
    input_dir: Path,
    products_db: Path,
    *,
    force_rescan: bool = False,
    max_files: Optional[int] = None,
) -> Dict[str, int]:
    """Scan and index HDF5 files in input directory.

    This function maintains the index as a snapshot of the current filesystem state.
    Files that are deleted from the filesystem will be marked as not stored (stored=0)
    but their metadata is preserved in the database for historical tracking.

    Args:
        input_dir: Directory containing HDF5 files
        products_db: Path to products database
        force_rescan: If True, re-index all files even if already indexed
        max_files: Maximum number of files to index (for testing/partial scans)

    Returns:
        Dictionary with statistics:
        - 'total_scanned': Total files scanned
        - 'new_indexed': New files indexed
        - 'updated': Files updated (modified time changed)
        - 'skipped': Files skipped (already indexed and unchanged)
        - 'deleted': Files marked as not stored (no longer exist on filesystem)
        - 'errors': Files that failed to index
    """
    stats = {
        "total_scanned": 0,
        "new_indexed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "deleted": 0,
    }

    if not input_dir.exists():
        logger.warning(f"Input directory does not exist: {input_dir}")
        return stats

    conn = ensure_products_db(products_db)
    indexed_at = time.time()

    logger.info(f"Scanning HDF5 files in {input_dir}...")

    # Scan directory for HDF5 files
    hdf5_files, current_paths = _scan_hdf5_files(input_dir, max_files)
    logger.info(f"Found {len(hdf5_files)} HDF5 files to process")

    # Process files in batches
    batch_size = 1000
    for i in range(0, len(hdf5_files), batch_size):
        batch = hdf5_files[i : i + batch_size]
        batch_stats = _update_database_batch(conn, batch, indexed_at, force_rescan)
        for key in stats:
            stats[key] += batch_stats[key]

        if (i + batch_size) % 10000 == 0:
            logger.info(
                f"Processed {i + batch_size}/{len(hdf5_files)} files "
                f"(new: {stats['new_indexed']}, updated: {stats['updated']}, "
                f"skipped: {stats['skipped']}, errors: {stats['errors']})"
            )

    # Mark entries for files that no longer exist on filesystem as not stored
    logger.info("Checking for files no longer on disk...")
    stats["deleted"] = _mark_deleted_files(conn, input_dir, current_paths)

    conn.commit()
    logger.info(
        f"Indexing complete: {stats['new_indexed']} new, {stats['updated']} updated, "
        f"{stats['skipped']} skipped, {stats['deleted']} marked as not stored, {stats['errors']} errors"
    )

    return stats


def _check_file_index_status(
    conn: sqlite3.Connection, full_path: str, modified_time: float, force_rescan: bool
) -> Optional[str]:
    """Check if file is already indexed and determine its status.

    Args:
        conn: Database connection
        full_path: Full path to file
        modified_time: File modification time
        force_rescan: If True, treat as new file

    Returns:
        Status string: 'skipped', 'updated', 'new', or None if error
    """
    if force_rescan:
        return "new"

    existing = conn.execute(
        "SELECT modified_time FROM hdf5_file_index WHERE path = ?", (full_path,)
    ).fetchone()

    if not existing:
        return "new"

    if existing[0] == modified_time:
        return "skipped"

    return "updated"


def _insert_or_update_file_entry(
    conn: sqlite3.Connection,
    full_path: str,
    filename: str,
    metadata: Dict[str, Any],
    indexed_at: float,
) -> None:
    """Insert or update file entry in database.

    Args:
        conn: Database connection
        full_path: Full path to file
        filename: Filename
        metadata: Parsed metadata dictionary
        indexed_at: Timestamp when indexing started
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO hdf5_file_index
        (path, filename, group_id, subband_code, timestamp_iso, timestamp_mjd,
         file_size_bytes, modified_time, indexed_at, stored)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            full_path,
            filename,
            metadata["group_id"],
            metadata["subband_code"],
            metadata["timestamp_iso"],
            metadata["timestamp_mjd"],
            metadata["file_size"],
            metadata["modified_time"],
            indexed_at,
        ),
    )


def _process_single_file(
    conn: sqlite3.Connection,
    full_path: str,
    filename: str,
    indexed_at: float,
    force_rescan: bool,
) -> Optional[str]:
    """Process a single file and update database.

    Args:
        conn: Database connection
        full_path: Full path to the file
        filename: Filename
        indexed_at: Timestamp when indexing started
        force_rescan: If True, re-index all files even if already indexed

    Returns:
        Status string: "new_indexed", "updated", "skipped", or None on error
    """
    metadata = _parse_hdf5_metadata(full_path, filename)
    if not metadata:
        return None

    status = _check_file_index_status(conn, full_path, metadata["modified_time"], force_rescan)
    if status == "skipped":
        return "skipped"

    _insert_or_update_file_entry(conn, full_path, filename, metadata, indexed_at)
    return status


def _update_stats_for_file(stats: Dict[str, int], status: Optional[str]) -> None:
    """Update statistics dictionary based on file processing status.

    Args:
        stats: Statistics dictionary to update
        status: Processing status ("new_indexed", "updated", "skipped", or None)
    """
    if status is None:
        stats["errors"] += 1
    elif status == "skipped":
        stats["skipped"] += 1
    elif status == "updated":
        stats["updated"] += 1
    else:  # status == "new_indexed"
        stats["new_indexed"] += 1


def _update_database_batch(
    conn: sqlite3.Connection,
    batch: List[Tuple[str, str]],
    indexed_at: float,
    force_rescan: bool,
) -> Dict[str, int]:
    """Update database with batch of files.

    Args:
        conn: Database connection
        batch: List of (full_path, filename) tuples
        indexed_at: Timestamp when indexing started
        force_rescan: If True, re-index all files even if already indexed

    Returns:
        Dictionary with statistics for this batch
    """
    stats = {
        "total_scanned": 0,
        "new_indexed": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "deleted": 0,
    }

    for full_path, filename in batch:
        stats["total_scanned"] += 1

        try:
            status = _process_single_file(conn, full_path, filename, indexed_at, force_rescan)
            _update_stats_for_file(stats, status)
        except Exception as e:
            logger.debug(f"Error indexing {full_path}: {e}")
            stats["errors"] += 1

    return stats


def query_subband_groups(
    products_db: Path,
    start_time: str,
    end_time: str,
    *,
    tolerance_s: float = 1.0,
    only_stored: bool = True,
) -> List[List[str]]:
    """Query database for complete subband groups in time range.

    Args:
        products_db: Path to products database
        start_time: Start time (ISO format: "YYYY-MM-DD HH:MM:SS")
        end_time: End time (ISO format: "YYYY-MM-DD HH:MM:SS")
        tolerance_s: Time tolerance in seconds (default: 1.0)
        only_stored: If True, only return groups where all files are still stored on disk

    Returns:
        List of complete 16-subband groups, each group is a list of file paths
        sorted by subband code.
    """
    conn = ensure_products_db(products_db)

    # Convert times to MJD
    try:
        start_mjd = Time(start_time, format="isot").mjd
        end_mjd = Time(end_time, format="isot").mjd
    except Exception:
        # Fallback to ISO format without 'T'
        start_mjd = Time(start_time.replace(" ", "T"), format="isot").mjd
        end_mjd = Time(end_time.replace(" ", "T"), format="isot").mjd

    # Query for files in time range
    # Use tolerance: convert seconds to days
    tolerance_days = tolerance_s / 86400.0

    # Build query with optional stored filter
    if only_stored:
        query = """
        SELECT group_id, subband_code, path
        FROM hdf5_file_index
        WHERE timestamp_mjd >= ? AND timestamp_mjd <= ? AND stored = 1
        ORDER BY group_id, subband_code
        """
    else:
        query = """
        SELECT group_id, subband_code, path
        FROM hdf5_file_index
        WHERE timestamp_mjd >= ? AND timestamp_mjd <= ?
        ORDER BY group_id, subband_code
        """

    # Query with timestamp_mjd for time-based clustering
    if only_stored:
        query = """
        SELECT timestamp_mjd, subband_code, path
        FROM hdf5_file_index
        WHERE timestamp_mjd >= ? AND timestamp_mjd <= ? AND stored = 1
        ORDER BY timestamp_mjd, subband_code
        """
    else:
        query = """
        SELECT timestamp_mjd, subband_code, path
        FROM hdf5_file_index
        WHERE timestamp_mjd >= ? AND timestamp_mjd <= ?
        ORDER BY timestamp_mjd, subband_code
        """

    rows = conn.execute(
        query,
        (start_mjd - tolerance_days, end_mjd + tolerance_days),
    ).fetchall()

    if not rows:
        return []

    # Cluster files by timestamp within a tolerance window (1 minute = ~0.000694 days)
    # This handles cases where filenames have slightly different timestamps
    cluster_tolerance_days = 60.0 / 86400.0  # 1 minute tolerance for clustering

    # Group files by time clusters
    # Each cluster is represented by its earliest timestamp
    time_clusters = {}  # cluster_mjd -> {subband_code: path}

    for timestamp_mjd, subband_code, path in rows:
        # Find existing cluster within tolerance, or create new one
        cluster_found = False
        for cluster_mjd in sorted(time_clusters.keys()):
            if abs(timestamp_mjd - cluster_mjd) <= cluster_tolerance_days:
                # Add to existing cluster
                time_clusters[cluster_mjd][subband_code] = path
                cluster_found = True
                break

        if not cluster_found:
            # Create new cluster
            time_clusters[timestamp_mjd] = {subband_code: path}

    # Filter to complete 16-subband groups
    expected_sb = [f"sb{idx:02d}" for idx in range(16)]
    complete_groups = []
    for cluster_mjd, sb_map in time_clusters.items():
        if set(sb_map.keys()) == set(expected_sb):
            # Sort by subband code
            group_files = [sb_map[sb] for sb in sorted(expected_sb)]
            # If only_stored is True, verify all files still exist
            if only_stored:
                all_exist = all(os.path.exists(f) for f in group_files)
                if not all_exist:
                    continue  # Skip incomplete groups
            complete_groups.append(group_files)

    return complete_groups


def get_group_count(products_db: Path, group_id: str) -> int:
    """Get count of subbands for a specific group_id.

    Args:
        products_db: Path to products database
        group_id: Group ID to query

    Returns:
        Number of subbands found for this group_id
    """
    conn = ensure_products_db(products_db)
    count = conn.execute(
        "SELECT COUNT(*) FROM hdf5_file_index WHERE group_id = ?",
        (group_id,),
    ).fetchone()[0]
    return count


def is_group_complete(products_db: Path, group_id: str) -> bool:
    """Check if a group has all 16 subbands.

    Args:
        products_db: Path to products database
        group_id: Group ID to check

    Returns:
        True if group has all 16 subbands, False otherwise
    """
    return get_group_count(products_db, group_id) == 16


__all__ = [
    "index_hdf5_files",
    "query_subband_groups",
    "get_group_count",
    "is_group_complete",
    "parse_hdf5_filename",
]
