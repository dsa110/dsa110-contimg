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
    - Simpler queries: No fuzzy time-window clustering needed
    - Idempotent: Re-running normalizer is safe

Used by:
    - ABSURD ingestion (absurd/ingestion.py) for normalize-group task
    - Batch normalization of historical data
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Pattern for parsing subband filenames
SUBBAND_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(?P<index>\d{2})\.hdf5$"
)

# Default tolerance for grouping subbands (seconds)
DEFAULT_CLUSTER_TOLERANCE_S = 60.0


def parse_subband_info(path: Path) -> Optional[Tuple[str, int]]:
    """Extract (group_id, subband_idx) from a filename, or None if not matched.

    Args:
        path: Path to HDF5 subband file

    Returns:
        Tuple of (group_id, subband_index) or None if filename doesn't match pattern

    Example:
        >>> parse_subband_info(Path("/data/2025-10-02T00:12:00_sb05.hdf5"))
        ("2025-10-02T00:12:00", 5)
    """
    m = SUBBAND_PATTERN.search(path.name)
    if not m:
        return None
    gid = m.group("timestamp")
    try:
        sb = int(m.group("index"))
    except ValueError:
        return None
    return gid, sb


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
) -> Path:
    """Normalize a subband file during ingest.

    This is the main entry point called during streaming ingest. It handles:
    - Checking if rename is needed
    - Performing atomic rename

    Args:
        path: Path to the incoming subband file
        target_group_id: The canonical group_id (from clustering)
        source_group_id: The original group_id from the filename

    Returns:
        Path after normalization (original or renamed)
    """
    if source_group_id == target_group_id:
        return path

    new_path, _ = normalize_subband_path(path, target_group_id, dry_run=False)
    return new_path


def normalize_directory(
    directory: Path,
    cluster_tolerance_s: float = DEFAULT_CLUSTER_TOLERANCE_S,
    dry_run: bool = True,
) -> Dict[str, int]:
    """Normalize all subband files in a directory.

    Groups files by timestamp within tolerance, then renames all files in each
    group to use the earliest (sb00's) timestamp as the canonical group_id.

    Args:
        directory: Path to directory containing HDF5 files
        cluster_tolerance_s: Tolerance for clustering subbands (default: 60s)
        dry_run: If True, only report what would be done (default: True for safety)

    Returns:
        Dict with statistics:
        - files_scanned: Total HDF5 files found
        - files_renamed: Number of files renamed (or would be renamed)
        - groups_found: Number of observation groups detected
        - errors: Number of files that failed to parse/rename

    Example:
        >>> stats = normalize_directory(Path("/data/incoming"), dry_run=True)
        >>> print(f"Would rename {stats['files_renamed']} files")
    """
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    # Collect all subband files
    files_by_group: Dict[str, Dict[int, Path]] = defaultdict(dict)
    errors = 0

    for hdf5_file in directory.glob("*_sb*.hdf5"):
        info = parse_subband_info(hdf5_file)
        if info is None:
            logger.warning("Could not parse filename: %s", hdf5_file.name)
            errors += 1
            continue

        group_id, subband_idx = info
        files_by_group[group_id][subband_idx] = hdf5_file

    # Cluster groups within tolerance
    sorted_groups = sorted(files_by_group.keys())
    canonical_map: Dict[str, str] = {}  # original_group_id -> canonical_group_id

    for group_id in sorted_groups:
        # Parse timestamp
        try:
            ts = datetime.fromisoformat(group_id)
        except ValueError:
            logger.warning("Invalid timestamp format: %s", group_id)
            canonical_map[group_id] = group_id
            continue

        # Find or create canonical group
        found_canonical = False
        for existing_group in canonical_map.values():
            try:
                existing_ts = datetime.fromisoformat(existing_group)
                if abs((ts - existing_ts).total_seconds()) <= cluster_tolerance_s:
                    canonical_map[group_id] = existing_group
                    found_canonical = True
                    break
            except ValueError:
                continue

        if not found_canonical:
            canonical_map[group_id] = group_id

    # Normalize files
    files_renamed = 0
    files_scanned = 0

    for group_id, subbands in files_by_group.items():
        canonical = canonical_map.get(group_id, group_id)

        for subband_idx, path in subbands.items():
            files_scanned += 1

            if group_id != canonical:
                try:
                    _, was_renamed = normalize_subband_path(path, canonical, dry_run=dry_run)
                    if was_renamed:
                        files_renamed += 1
                except Exception as e:
                    logger.error("Failed to normalize %s: %s", path, e)
                    errors += 1

    # Count unique canonical groups
    groups_found = len(set(canonical_map.values()))

    return {
        "files_scanned": files_scanned,
        "files_renamed": files_renamed,
        "groups_found": groups_found,
        "errors": errors,
    }
