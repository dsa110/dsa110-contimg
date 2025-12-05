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
    
    try:
        # If we have a lock manager, acquire write lock for the rename
        if lock_manager is not None:
            # Use write lock since we're modifying the file path
            # This coordinates with any readers (like the validator)
            try:
                lock_context = lock_manager.write_lock(str(path), timeout=5.0)
            except Exception as lock_err:
                logger.warning(
                    f"Could not acquire lock for normalization of {path.name}: {lock_err}"
                )
                # Continue without lock - rename should still be atomic
                from contextlib import nullcontext
                lock_context = nullcontext()
        else:
            from contextlib import nullcontext
            lock_context = nullcontext()
        
        with lock_context:
            new_path, was_renamed = normalize_subband_path(path, target_group_id)
            return new_path
            
    except Exception as e:
        logger.error(
            f"Failed to normalize {path.name} to group {target_group_id}: {e}"
        )
        # Return original path - ingest should continue
        return path


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
    from datetime import datetime
    from collections import defaultdict
    
    stats = {
        "files_scanned": 0,
        "files_renamed": 0,
        "groups_found": 0,
        "errors": [],
    }
    
    # Find all subband files
    files_by_timestamp: dict[datetime, list[tuple[Path, str, int]]] = defaultdict(list)
    
    for path in directory.glob("*_sb??.hdf5"):
        stats["files_scanned"] += 1
        info = parse_subband_info(path)
        if info is None:
            stats["errors"].append(f"Could not parse: {path.name}")
            continue
        
        group_id, subband_idx = info
        try:
            dt = datetime.strptime(group_id, "%Y-%m-%dT%H:%M:%S")
            files_by_timestamp[dt].append((path, group_id, subband_idx))
        except ValueError as e:
            stats["errors"].append(f"Invalid timestamp in {path.name}: {e}")
    
    # Cluster by timestamp
    sorted_times = sorted(files_by_timestamp.keys())
    clusters: list[list[datetime]] = []
    
    for dt in sorted_times:
        # Check if this timestamp belongs to the last cluster
        if clusters and (dt - clusters[-1][-1]).total_seconds() <= cluster_tolerance_s:
            clusters[-1].append(dt)
        else:
            clusters.append([dt])
    
    stats["groups_found"] = len(clusters)
    
    # Normalize each cluster
    for cluster in clusters:
        # Canonical group_id is the earliest timestamp in cluster
        canonical_dt = min(cluster)
        canonical_group_id = canonical_dt.strftime("%Y-%m-%dT%H:%M:%S")
        
        for dt in cluster:
            for path, current_group_id, subband_idx in files_by_timestamp[dt]:
                if current_group_id != canonical_group_id:
                    try:
                        _, was_renamed = normalize_subband_path(
                            path, canonical_group_id, dry_run=dry_run
                        )
                        if was_renamed:
                            stats["files_renamed"] += 1
                    except Exception as e:
                        stats["errors"].append(f"Failed to rename {path.name}: {e}")
    
    return stats
