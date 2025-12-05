"""
Subband filename normalization utilities.

This module provides functions for normalizing subband filenames to ensure
all subbands in a group share the same canonical timestamp. This eliminates
the need for fuzzy time-based clustering in queries.

The Problem:
    The correlator writes subband files with slightly different timestamps:
    - 2025-01-15T12:00:00_sb00.hdf5
    - 2025-01-15T12:00:01_sb01.hdf5  (1 second later)
    - 2025-01-15T12:00:00_sb02.hdf5
    - 2025-01-15T12:00:02_sb03.hdf5  (2 seconds later)

The Solution:
    When a subband arrives, if it clusters with an existing group, rename the
    file to use the canonical group_id:
    - 2025-01-15T12:00:00_sb00.hdf5  (first arrival = canonical)
    - 2025-01-15T12:00:00_sb01.hdf5  (renamed from T12:00:01)
    - 2025-01-15T12:00:00_sb02.hdf5  (already matches)
    - 2025-01-15T12:00:00_sb03.hdf5  (renamed from T12:00:02)

Benefits:
    - Exact matching: GROUP BY group_id just works
    - Self-documenting: Filesystem shows true group membership
    - Simpler SubbandGroup: files list guaranteed to have same timestamp
    - Idempotent: Re-running normalizer is safe
"""

from __future__ import annotations

import logging
from collections import defaultdict
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .queue import parse_subband_info

logger = logging.getLogger(__name__)


def build_subband_filename(group_id: str, subband_idx: int) -> str:
    """Build a canonical subband filename from group_id and index.

    Args:
        group_id: Canonical timestamp (YYYY-MM-DDTHH:MM:SS)
        subband_idx: Subband index (0-15)

    Returns:
        Filename string like "2025-01-15T12:00:00_sb05.hdf5"

    Example:
        >>> build_subband_filename("2025-01-15T12:00:00", 5)
        "2025-01-15T12:00:00_sb05.hdf5"
    """
    return f"{group_id}_sb{subband_idx:02d}.hdf5"


def normalize_subband_path(
    path: Path,
    canonical_group_id: str,
    dry_run: bool = False,
) -> Tuple[Path, bool]:
    """Rename a subband file to use the canonical group_id.

    If the file already has the correct name, no action is taken.

    Args:
        path: Current path to the subband file
        canonical_group_id: The canonical group_id to use (YYYY-MM-DDTHH:MM:SS)
        dry_run: If True, don't actually rename, just return what would happen

    Returns:
        Tuple of (new_path, was_renamed):
        - new_path: Path after normalization (may be same as input if no rename needed)
        - was_renamed: True if file was (or would be) renamed

    Raises:
        FileNotFoundError: If the source file doesn't exist
        ValueError: If the path doesn't match subband filename pattern
        OSError: If rename fails (e.g., permission denied, target exists)

    Example:
        >>> path = Path("/data/2025-01-15T12:00:01_sb05.hdf5")
        >>> new_path, renamed = normalize_subband_path(path, "2025-01-15T12:00:00")
        >>> print(new_path)
        /data/2025-01-15T12:00:00_sb05.hdf5
        >>> print(renamed)
        True
    """
    # Parse current filename
    info = parse_subband_info(path)
    if info is None:
        raise ValueError(f"Path does not match subband pattern: {path}")

    current_group_id, subband_idx = info

    # Check if already normalized
    if current_group_id == canonical_group_id:
        logger.debug("File already normalized: %s", path.name)
        return path, False

    # Build new filename
    new_name = build_subband_filename(canonical_group_id, subband_idx)
    new_path = path.parent / new_name

    # Check source exists
    if not path.exists():
        raise FileNotFoundError(f"Source file does not exist: {path}")

    # Check target doesn't already exist (shouldn't happen in normal operation)
    if new_path.exists() and not path.samefile(new_path):
        raise OSError(f"Target file already exists: {new_path}")

    if dry_run:
        logger.info("Would rename: %s -> %s", path.name, new_name)
        return new_path, True

    # Perform atomic rename
    # Note: Path.rename() is atomic on POSIX filesystems
    try:
        path.rename(new_path)
        logger.info("Normalized: %s -> %s", path.name, new_name)
        return new_path, True
    except OSError as err:
        logger.error("Failed to rename %s -> %s: %s", path.name, new_name, err)
        raise


def normalize_subband_on_ingest(
    path: Path,
    target_group_id: str,
    source_group_id: str,
    lock_manager: Optional[object] = None,
) -> Path:
    """Normalize a subband file during ingest, with optional FUSE lock coordination.

    This is the main entry point called during streaming ingest. It handles:
    - Checking if rename is needed
    - Coordinating with FUSE lock manager if present
    - Performing atomic rename

    Args:
        path: Path to the incoming subband file
        target_group_id: The canonical group_id (from clustering)
        source_group_id: The original group_id from the filename
        lock_manager: Optional FUSE lock manager for coordination

    Returns:
        Path to the file after normalization (may be unchanged if no rename needed)

    Note:
        If rename fails, the original path is returned and an error is logged.
        This ensures ingest continues even if normalization fails.
    """
    # No rename needed if group IDs match
    if target_group_id == source_group_id:
        return path

    lock_context = _get_lock_context(lock_manager, path)

    try:
        with lock_context:
            new_path, _ = normalize_subband_path(path, target_group_id)
            return new_path
    except Exception as err:
        logger.error(
            "Failed to normalize %s to group %s: %s",
            path.name, target_group_id, err
        )
        # Return original path - ingest should continue
        return path


def _get_lock_context(lock_manager: Optional[object], path: Path):
    """Get appropriate lock context for file operations.

    Args:
        lock_manager: Optional FUSE lock manager
        path: File path for locking

    Returns:
        Context manager (write lock if manager present, nullcontext otherwise)
    """
    if lock_manager is None:
        return nullcontext()

    try:
        return lock_manager.write_lock(str(path), timeout=5.0)
    except Exception as lock_err:
        logger.warning(
            "Could not acquire lock for normalization of %s: %s",
            path.name, lock_err
        )
        return nullcontext()


def _scan_subband_files(directory: Path) -> tuple[dict, list[str]]:
    """Scan directory for subband files and group by timestamp.

    Args:
        directory: Directory to scan

    Returns:
        Tuple of (files_by_timestamp dict, list of error messages)
    """
    files_by_timestamp: dict[datetime, list[tuple[Path, str, int]]] = defaultdict(list)
    errors: list[str] = []

    for path in directory.glob("*_sb??.hdf5"):
        info = parse_subband_info(path)
        if info is None:
            errors.append(f"Could not parse: {path.name}")
            continue

        group_id, subband_idx = info
        try:
            timestamp = datetime.strptime(group_id, "%Y-%m-%dT%H:%M:%S")
            files_by_timestamp[timestamp].append((path, group_id, subband_idx))
        except ValueError as parse_err:
            errors.append(f"Invalid timestamp in {path.name}: {parse_err}")

    return files_by_timestamp, errors


def _cluster_timestamps(
    timestamps: list[datetime],
    tolerance_s: float,
) -> list[list[datetime]]:
    """Cluster timestamps that are within tolerance of each other.

    Args:
        timestamps: Sorted list of timestamps
        tolerance_s: Maximum seconds between timestamps in same cluster

    Returns:
        List of clusters (each cluster is a list of timestamps)
    """
    clusters: list[list[datetime]] = []

    for timestamp in timestamps:
        if clusters and (timestamp - clusters[-1][-1]).total_seconds() <= tolerance_s:
            clusters[-1].append(timestamp)
        else:
            clusters.append([timestamp])

    return clusters


def _normalize_cluster(
    cluster: list[datetime],
    files_by_timestamp: dict,
    dry_run: bool,
) -> tuple[int, list[str]]:
    """Normalize all files in a cluster to use the canonical timestamp.

    Args:
        cluster: List of timestamps in this cluster
        files_by_timestamp: Mapping of timestamp to file info
        dry_run: If True, don't actually rename

    Returns:
        Tuple of (files_renamed count, list of error messages)
    """
    renamed = 0
    errors: list[str] = []

    canonical_dt = min(cluster)
    canonical_group_id = canonical_dt.strftime("%Y-%m-%dT%H:%M:%S")

    for timestamp in cluster:
        for path, current_group_id, _ in files_by_timestamp[timestamp]:
            if current_group_id != canonical_group_id:
                try:
                    _, was_renamed = normalize_subband_path(
                        path, canonical_group_id, dry_run=dry_run
                    )
                    if was_renamed:
                        renamed += 1
                except OSError as rename_err:
                    errors.append(f"Failed to rename {path.name}: {rename_err}")

    return renamed, errors


def normalize_directory(
    directory: Path,
    cluster_tolerance_s: float = 60.0,
    dry_run: bool = True,
) -> dict:
    """Normalize all subband files in a directory.

    This is a batch operation for normalizing historical files. It:
    1. Scans for all *_sb??.hdf5 files
    2. Groups them by timestamp (using clustering tolerance)
    3. Renames files to use the canonical group_id (earliest in cluster)

    Args:
        directory: Directory containing subband files
        cluster_tolerance_s: Tolerance for clustering (default: 60s)
        dry_run: If True, only report what would be done (default: True for safety)

    Returns:
        Dictionary with statistics:
        - files_scanned: Total files found
        - files_renamed: Files that were (or would be) renamed
        - groups_found: Number of distinct groups after normalization
        - errors: List of error messages

    Example:
        >>> stats = normalize_directory(Path("/data/incoming"), dry_run=True)
        >>> print(f"Would rename {stats['files_renamed']} of {stats['files_scanned']} files")
    """
    # Scan directory
    files_by_timestamp, scan_errors = _scan_subband_files(directory)
    files_scanned = sum(len(files) for files in files_by_timestamp.values())
    files_scanned += len(scan_errors)  # Include unparseable files in count

    # Cluster timestamps
    sorted_times = sorted(files_by_timestamp.keys())
    clusters = _cluster_timestamps(sorted_times, cluster_tolerance_s)

    # Normalize each cluster
    files_renamed = 0
    rename_errors: list[str] = []

    for cluster in clusters:
        renamed, errors = _normalize_cluster(cluster, files_by_timestamp, dry_run)
        files_renamed += renamed
        rename_errors.extend(errors)

    return {
        "files_scanned": files_scanned,
        "files_renamed": files_renamed,
        "groups_found": len(clusters),
        "errors": scan_errors + rename_errors,
    }
