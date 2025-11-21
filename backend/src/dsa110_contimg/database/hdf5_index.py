"""HDF5 file indexing service for fast subband group queries.

This module provides functions to scan and index HDF5 files in the
input directory, enabling fast database queries instead of filesystem
scans.

CRITICAL: Understanding group_id vs Observation Groups
=======================================================

The `group_id` field in hdf5_file_index stores the EXACT ISO timestamp from
each file's filename (e.g., "2025-10-18T14:35:15"). However, subbands from
the SAME observation may have slightly different timestamps due to write
timing, buffering, or processing delays.

**WRONG APPROACH:**
    SELECT group_id, COUNT(*) FROM hdf5_file_index GROUP BY group_id HAVING COUNT(*) = 16;

    This groups by EXACT timestamps and will show fragmented "groups" with
    1-8 subbands each, even though the data is complete!

**CORRECT APPROACH:**
    Use query_subband_groups() or find_subband_groups() which implement
    time-windowing (±2.5 min tolerance by default) to properly group subbands
    that belong to the same observation.

**Key Points:**
- group_id is for indexing individual files, NOT for determining completeness
- Always use the pipeline's time-windowing functions (query_subband_groups)
- Never count subbands by GROUP BY group_id - results will be misleading
- The pipeline handles temporal clustering automatically
"""

import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from astropy.time import Time

from dsa110_contimg.database.hdf5_db import ensure_hdf5_db

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

    For sb00 files (first subband in group), also extracts:
    - Sky coordinates (RA/Dec in degrees)
    - Observation date and time

    Args:
        full_path: Full path to HDF5 file
        filename: Filename of HDF5 file

    Returns:
        Dictionary with metadata or None if parsing fails.
        Keys: group_id, subband_code, file_size, modified_time, timestamp_iso, timestamp_mjd
              ra_deg, dec_deg, obs_date, obs_time (only for sb00 files)
    """
    # Parse filename
    parsed = parse_hdf5_filename(filename)
    if not parsed:
        return None

    group_id, subband_code = parsed

    # Extract subband number from subband_code (e.g., "sb00" -> 0, "sb15" -> 15)
    subband_num = None
    try:
        if subband_code.startswith("sb"):
            subband_num = int(subband_code[2:])
    except (ValueError, IndexError):
        logger.debug(f"Could not parse subband number from {subband_code}")

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

    metadata = {
        "group_id": group_id,
        "subband_code": subband_code,
        "subband_num": subband_num,
        "file_size": file_size,
        "modified_time": modified_time,
        "timestamp_iso": timestamp_iso,
        "timestamp_mjd": timestamp_mjd,
        "ra_deg": None,
        "dec_deg": None,
        "obs_date": None,
        "obs_time": None,
    }

    # Extract sky coordinates and time only for sb00 files
    if subband_code == "sb00":
        try:
            from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                _peek_uvh5_phase_and_midtime,
            )

            # Extract RA, Dec, and mid_time from HDF5 file
            pt_ra, pt_dec, mid_mjd = _peek_uvh5_phase_and_midtime(full_path)

            # Convert to degrees (check for non-zero/non-None)
            # Note: Can't use "if pt_ra" because Quantity truthiness is ambiguous
            if pt_ra is not None and pt_ra.value != 0:
                metadata["ra_deg"] = pt_ra.to("deg").value
            if pt_dec is not None and pt_dec.value != 0:
                metadata["dec_deg"] = pt_dec.to("deg").value

            # Extract date and time from timestamp
            if timestamp_iso:
                try:
                    t = Time(timestamp_iso, format="isot")
                    metadata["obs_date"] = t.to_value("iso", subfmt="date")
                    metadata["obs_time"] = t.to_value("iso", subfmt="date_hm")
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"Could not extract sky coordinates from {full_path}: {e}")

    return metadata


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
    hdf5_db: Path,
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
        hdf5_db: Path to HDF5 database
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

    conn = ensure_hdf5_db(hdf5_db)
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
    conn: sqlite3.Connection,
    full_path: str,
    modified_time: float,
    force_rescan: bool,
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
        "SELECT modified_time FROM hdf5_file_index WHERE path = ?",
        (full_path,),
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
        (path, filename, group_id, subband_code, subband_num,
         timestamp_iso, timestamp_mjd, file_size_bytes, modified_time,
         indexed_at, stored, ra_deg, dec_deg, obs_date, obs_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        """,
        (
            full_path,
            filename,
            metadata["group_id"],
            metadata["subband_code"],
            metadata["subband_num"],
            metadata["timestamp_iso"],
            metadata["timestamp_mjd"],
            metadata["file_size"],
            metadata["modified_time"],
            indexed_at,
            metadata["ra_deg"],
            metadata["dec_deg"],
            metadata["obs_date"],
            metadata["obs_time"],
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


@dataclass
class SubbandGroupInfo:
    """Metadata for a subband group, tracking completeness and missing subbands.

    Attributes:
        files: List of 16 file paths (None for missing subbands), ordered sb00-sb15
        is_complete: True if all 16 subbands are present, False if 12-15 (semi-complete)
        present_count: Number of present subbands (12-16)
        missing_subbands: Set of missing subband indices (0-15)
        missing_subband_codes: Set of missing subband codes (e.g., {"sb03", "sb07"})
    """

    files: List[Optional[str]]
    is_complete: bool
    present_count: int
    missing_subbands: Set[int]
    missing_subband_codes: Set[str]

    def __post_init__(self):
        """Validate and compute derived fields."""
        if len(self.files) != 16:
            raise ValueError(f"Group must have exactly 16 slots, got {len(self.files)}")
        # Recompute to ensure consistency
        present = [i for i, f in enumerate(self.files) if f is not None]
        missing = set(range(16)) - set(present)
        self.present_count = len(present)
        self.missing_subbands = missing
        self.missing_subband_codes = {f"sb{i:02d}" for i in missing}
        self.is_complete = len(missing) == 0

    @classmethod
    def from_file_list(cls, files: List[Optional[str]]) -> "SubbandGroupInfo":
        """Create SubbandGroupInfo from a list of files (may contain None).

        Args:
            files: List of 16 file paths (None for missing subbands)

        Returns:
            SubbandGroupInfo instance
        """
        if len(files) != 16:
            raise ValueError(f"Group must have exactly 16 slots, got {len(files)}")
        present = [i for i, f in enumerate(files) if f is not None]
        missing = set(range(16)) - set(present)
        return cls(
            files=files,
            is_complete=len(missing) == 0,
            present_count=len(present),
            missing_subbands=missing,
            missing_subband_codes={f"sb{i:02d}" for i in missing},
        )

    def needs_synthetic_subbands(self) -> bool:
        """Check if synthetic subbands are needed.

        Returns:
            True if group is semi-complete (12-15 subbands), False if complete
        """
        return not self.is_complete and self.present_count >= 12


def query_subband_groups(
    hdf5_db: Path,
    start_time: str,
    end_time: str,
    *,
    tolerance_s: float = 60.0,
    cluster_tolerance_s: float = 60.0,
    only_stored: bool = True,
) -> List[SubbandGroupInfo]:
    """Query database for subband groups in time range.

    This is the database-specific grouping function. For a higher-level function
    that includes filesystem fallback, see `find_subband_groups()` in
    `dsa110_contimg.conversion.strategies.hdf5_orchestrator`.

    NOTE: This function and `find_subband_groups()` are NOT redundant:
    - `query_subband_groups()`: Database-only query (this function)
    - `find_subband_groups()`: High-level wrapper that calls `query_subband_groups()`
      first, then falls back to filesystem scan if database query fails

    Args:
        hdf5_db: Path to HDF5 database
        start_time: Start time (ISO format: "YYYY-MM-DD HH:MM:SS")
        end_time: End time (ISO format: "YYYY-MM-DD HH:MM:SS")
        tolerance_s: Time tolerance in seconds for query window expansion (default: 60.0)
        cluster_tolerance_s: Time tolerance in seconds for clustering files into groups (default: 60.0)
        only_stored: If True, only return groups where all files are still stored on disk

    Returns:
        List of SubbandGroupInfo objects for groups with 12-16 subbands.
        Each group tracks which subbands are missing and whether synthetic
        subbands need to be created.
    """
    conn = ensure_hdf5_db(hdf5_db)

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

    # CRITICAL: Use the correct proximity-based grouping algorithm from hdf5_orchestrator.py
    # This algorithm is proven to work correctly in production.
    #
    # Algorithm:
    # 1. Sort files by timestamp
    # 2. For each file, find all files within cluster_tolerance_s
    # 3. Build subband map and check if complete (16 subbands)
    # 4. Mark used files to avoid duplicate groups

    # Convert to numpy arrays for efficient proximity search
    times_sec = np.array([mjd * 86400.0 for mjd, _, _ in rows])  # MJD to seconds
    subband_codes = np.array([sb for _, sb, _ in rows])
    paths = np.array([path for _, _, path in rows])

    expected_sb = set([f"sb{idx:02d}" for idx in range(16)])
    group_infos = []
    used = np.zeros(len(times_sec), dtype=bool)

    for i in range(len(times_sec)):
        if used[i]:
            continue

        # Find all files within tolerance of this file
        close_indices = np.where(np.abs(times_sec - times_sec[i]) <= cluster_tolerance_s)[0]
        group_indices = [idx for idx in close_indices if not used[idx]]

        # Build subband map for this potential group
        subband_map = {}
        for idx in group_indices:
            sb_code = subband_codes[idx]
            if sb_code in subband_map:
                logger.debug(f"Duplicate subband {sb_code}, using latest file")
            subband_map[sb_code] = paths[idx]

        # NEW PROTOCOL: Accept groups with 12-16 subbands (missing 4 or fewer)
        # Missing subbands will be filled with zero-padded synthetic subbands
        present_sb = set(subband_map.keys())

        if len(present_sb) >= 12 and len(present_sb) <= 16:
            # Sort by subband code (sb00 to sb15), using None for missing subbands
            group_files = []
            for idx in range(16):
                sb_code = f"sb{idx:02d}"
                if sb_code in subband_map:
                    group_files.append(subband_map[sb_code])
                else:
                    group_files.append(None)  # Placeholder for missing subband

            # If only_stored is True, verify all existing files still exist
            if only_stored:
                existing_files = [f for f in group_files if f is not None]
                all_exist = all(os.path.exists(f) for f in existing_files)
                if not all_exist:
                    # Don't mark as used - allow partial groups to be tried again
                    continue

            # Create SubbandGroupInfo with metadata about missing subbands
            group_info = SubbandGroupInfo.from_file_list(group_files)
            group_infos.append(group_info)

            # Mark all files in this group as used
            for idx in group_indices:
                used[idx] = True

    return group_infos


def get_group_count(hdf5_db: Path, group_id: str) -> int:
    """Get number of subbands for a specific group_id.

    WARNING: This counts files with EXACT timestamp matching. If you're checking
    data completeness, use query_subband_groups() instead, which uses time-windowing
    to properly group subbands from the same observation.

    Args:
        hdf5_db: Path to HDF5 database
        group_id: Group ID to check

    Returns:
        Number of subbands found for this group_id
    """
    conn = ensure_hdf5_db(hdf5_db)
    count = conn.execute(
        "SELECT COUNT(*) FROM hdf5_file_index WHERE group_id = ?",
        (group_id,),
    ).fetchone()[0]

    # Print warning if group appears incomplete
    if count < 16 and count > 0:
        msg = (
            f"\n⚠️  WARNING: Group {group_id} has {count}/16 subbands\n"
            f"    This counts EXACT timestamp matches only!\n"
            f"    For proper completeness checking, use query_subband_groups()\n"
            f"    with time-windowing (±2.5 min tolerance).\n"
            f"    Subbands from the same observation may have slightly different timestamps.\n"
        )
        print(msg, flush=True)
        logger.warning(msg)

    return count


def is_group_complete(hdf5_db: Path, group_id: str) -> bool:
    """Check if a group has all 16 subbands.

    WARNING: This checks for EXACT timestamp matching. If you're checking data
    completeness for conversion, use query_subband_groups() instead, which uses
    time-windowing to properly group subbands from the same observation.

    Args:
        hdf5_db: Path to HDF5 database
        group_id: Group ID to check

    Returns:
        True if group has all 16 subbands (exact timestamp match), False otherwise
    """
    count = get_group_count(hdf5_db, group_id)

    if count < 16:
        msg = (
            f"\nℹ️  Group {group_id}: {count}/16 subbands with exact timestamp match\n"
            f"   💡 Reminder: Use query_subband_groups() with time-windowing\n"
            f"      for proper completeness checking (±2.5 min tolerance)\n"
        )
        print(msg, flush=True)
        logger.info(msg)

    return count == 16


__all__ = [
    "index_hdf5_files",
    "query_subband_groups",
    "get_group_count",
    "is_group_complete",
    "parse_hdf5_filename",
    "SubbandGroupInfo",
]
