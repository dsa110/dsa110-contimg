"""
Storage Validator - Ensures HDF5 database matches filesystem reality.

This module provides utilities to:
1. Detect files on disk not in database (orphaned files)
2. Detect files in database not on disk (stale records)
3. Reconcile database with filesystem
4. Provide integrity metrics for monitoring
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class StorageValidationResult:
    """Result of a storage validation check."""
    
    # Counts
    files_on_disk: int = 0
    files_in_db_stored: int = 0  # stored=1
    files_in_db_removed: int = 0  # stored=0
    files_in_db_total: int = 0
    
    # Discrepancies
    on_disk_not_in_db: List[str] = field(default_factory=list)
    in_db_not_on_disk: List[str] = field(default_factory=list)
    
    # Status
    is_synchronized: bool = False
    validation_time_sec: float = 0.0
    validated_at: str = ""
    
    @property
    def orphaned_file_count(self) -> int:
        """Files on disk but not in database."""
        return len(self.on_disk_not_in_db)
    
    @property
    def stale_record_count(self) -> int:
        """Database records for files that no longer exist."""
        return len(self.in_db_not_on_disk)
    
    @property
    def sync_percentage(self) -> float:
        """Percentage of files that are correctly synchronized."""
        total = self.files_on_disk + self.stale_record_count
        if total == 0:
            return 100.0
        synced = self.files_on_disk - self.orphaned_file_count
        return (synced / total) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "files_on_disk": self.files_on_disk,
            "files_in_db_stored": self.files_in_db_stored,
            "files_in_db_removed": self.files_in_db_removed,
            "files_in_db_total": self.files_in_db_total,
            "orphaned_file_count": self.orphaned_file_count,
            "stale_record_count": self.stale_record_count,
            "is_synchronized": self.is_synchronized,
            "sync_percentage": round(self.sync_percentage, 2),
            "validation_time_sec": round(self.validation_time_sec, 3),
            "validated_at": self.validated_at,
            # Include sample of discrepancies (limit for API response size)
            "sample_orphaned_files": self.on_disk_not_in_db[:10],
            "sample_stale_records": self.in_db_not_on_disk[:10],
        }


def validate_hdf5_storage(
    db_path: str,
    storage_dir: str,
    full_check: bool = False,
    max_discrepancies: int = 1000,
) -> StorageValidationResult:
    """
    Validate that HDF5 database matches filesystem.
    
    Args:
        db_path: Path to HDF5 index SQLite database.
        storage_dir: Directory containing HDF5 files.
        full_check: If True, collect all discrepancies. If False, stop at max.
        max_discrepancies: Maximum discrepancies to collect (for performance).
    
    Returns:
        StorageValidationResult with validation details.
    """
    from datetime import datetime
    
    start_time = time.time()
    result = StorageValidationResult()
    result.validated_at = datetime.utcnow().isoformat() + "Z"
    
    # Get files on disk
    disk_files: Set[str] = set()
    try:
        for entry in os.scandir(storage_dir):
            if entry.is_file() and entry.name.endswith('.hdf5'):
                disk_files.add(entry.path)
    except OSError as e:
        logger.error(f"Failed to scan storage directory: {e}")
        result.validation_time_sec = time.time() - start_time
        return result
    
    result.files_on_disk = len(disk_files)
    
    # Get files from database
    db_files_stored: Set[str] = set()
    db_files_removed: Set[str] = set()
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        # Count totals
        cursor.execute("SELECT COUNT(*) FROM hdf5_file_index WHERE stored=1")
        result.files_in_db_stored = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM hdf5_file_index WHERE stored=0")
        result.files_in_db_removed = cursor.fetchone()[0]
        
        result.files_in_db_total = result.files_in_db_stored + result.files_in_db_removed
        
        # Get paths for comparison
        cursor.execute("SELECT path, stored FROM hdf5_file_index")
        for path, stored in cursor.fetchall():
            if stored == 1:
                db_files_stored.add(path)
            else:
                db_files_removed.add(path)
        
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Failed to query database: {e}")
        result.validation_time_sec = time.time() - start_time
        return result
    
    # Find discrepancies
    # Files on disk but not in DB (or marked as removed)
    for path in disk_files:
        if path not in db_files_stored:
            result.on_disk_not_in_db.append(path)
            if not full_check and len(result.on_disk_not_in_db) >= max_discrepancies:
                break
    
    # Files in DB (marked stored) but not on disk
    for path in db_files_stored:
        if path not in disk_files:
            result.in_db_not_on_disk.append(path)
            if not full_check and len(result.in_db_not_on_disk) >= max_discrepancies:
                break
    
    result.is_synchronized = (
        len(result.on_disk_not_in_db) == 0 and
        len(result.in_db_not_on_disk) == 0
    )
    
    result.validation_time_sec = time.time() - start_time
    
    logger.info(
        f"Storage validation complete: {result.files_on_disk} on disk, "
        f"{result.files_in_db_stored} in DB, "
        f"{result.orphaned_file_count} orphaned, "
        f"{result.stale_record_count} stale"
    )
    
    return result


def reconcile_storage(
    db_path: str,
    storage_dir: str,
    mark_removed: bool = True,
    dry_run: bool = True,
) -> dict:
    """
    Reconcile database with filesystem.
    
    Args:
        db_path: Path to HDF5 index SQLite database.
        storage_dir: Directory containing HDF5 files.
        mark_removed: If True, mark missing files as stored=0.
        dry_run: If True, don't actually modify database.
    
    Returns:
        Dictionary with reconciliation results.
    """
    validation = validate_hdf5_storage(db_path, storage_dir, full_check=True)
    
    results = {
        "dry_run": dry_run,
        "stale_records_to_mark": len(validation.in_db_not_on_disk),
        "stale_records_marked": 0,
        "orphaned_files_found": len(validation.on_disk_not_in_db),
        "errors": [],
    }
    
    if not mark_removed or dry_run:
        return results
    
    # Mark stale records as removed
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        for path in validation.in_db_not_on_disk:
            try:
                cursor.execute(
                    "UPDATE hdf5_file_index SET stored=0 WHERE path=?",
                    (path,)
                )
                results["stale_records_marked"] += 1
            except sqlite3.Error as e:
                results["errors"].append(f"Failed to update {path}: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Marked {results['stale_records_marked']} stale records as removed")
        
    except sqlite3.Error as e:
        results["errors"].append(f"Database error: {e}")
    
    return results


def get_storage_metrics(db_path: str, storage_dir: str) -> dict:
    """
    Get quick storage metrics without full validation.
    
    This is faster than full validation - just compares counts.
    
    Args:
        db_path: Path to HDF5 index SQLite database.
        storage_dir: Directory containing HDF5 files.
    
    Returns:
        Dictionary with storage metrics.
    """
    metrics = {
        "files_on_disk": 0,
        "files_in_db_stored": 0,
        "files_in_db_total": 0,
        "count_matches": False,
        "checked_at": "",
    }
    
    from datetime import datetime
    metrics["checked_at"] = datetime.utcnow().isoformat() + "Z"
    
    # Count files on disk (fast)
    try:
        metrics["files_on_disk"] = sum(
            1 for entry in os.scandir(storage_dir)
            if entry.is_file() and entry.name.endswith('.hdf5')
        )
    except OSError:
        pass
    
    # Count in database
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM hdf5_file_index WHERE stored=1")
        metrics["files_in_db_stored"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM hdf5_file_index")
        metrics["files_in_db_total"] = cursor.fetchone()[0]
        conn.close()
    except sqlite3.Error:
        pass
    
    metrics["count_matches"] = (
        metrics["files_on_disk"] == metrics["files_in_db_stored"]
    )
    
    return metrics


# Regex pattern for parsing HDF5 filenames
# Format: 2025-01-15T12:30:00_sb00.hdf5
import re
from datetime import datetime

_HDF5_FILENAME_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(?P<subband>\d{2})\.hdf5$"
)

# Tolerance for grouping files into the same observation (in seconds).
# Files written within this window are considered part of the same observation.
GROUP_TIMESTAMP_TOLERANCE_SECONDS = 10


def normalize_group_timestamp(timestamp_iso: str, tolerance_seconds: int = GROUP_TIMESTAMP_TOLERANCE_SECONDS) -> str:
    """
    Normalize a timestamp to a canonical group timestamp.
    
    This rounds the timestamp down to the nearest tolerance_seconds boundary,
    ensuring that files written within the tolerance window get the same group_id.
    
    For example, with tolerance_seconds=10:
    - '2025-01-15T12:30:01' -> '2025-01-15T12:30:00'
    - '2025-01-15T12:30:09' -> '2025-01-15T12:30:00'
    - '2025-01-15T12:30:10' -> '2025-01-15T12:30:10'
    - '2025-01-15T12:30:15' -> '2025-01-15T12:30:10'
    
    Args:
        timestamp_iso: ISO format timestamp like '2025-01-15T12:30:05'
        tolerance_seconds: Time window for grouping (default: 10 seconds)
    
    Returns:
        Normalized ISO timestamp string.
    """
    dt = datetime.fromisoformat(timestamp_iso)
    # Floor to nearest tolerance_seconds boundary
    seconds_since_midnight = dt.hour * 3600 + dt.minute * 60 + dt.second
    floored_seconds = (seconds_since_midnight // tolerance_seconds) * tolerance_seconds
    normalized_dt = dt.replace(
        hour=floored_seconds // 3600,
        minute=(floored_seconds % 3600) // 60,
        second=floored_seconds % 60,
        microsecond=0
    )
    return normalized_dt.strftime("%Y-%m-%dT%H:%M:%S")


def parse_hdf5_filename(filename: str) -> Optional[dict]:
    """
    Parse HDF5 filename to extract metadata.
    
    Args:
        filename: Filename like '2025-01-15T12:30:00_sb00.hdf5'
    
    Returns:
        Dictionary with parsed metadata or None if parsing fails.
        Keys: timestamp_iso, group_id, subband_code, subband_num, obs_date, obs_time
        
    Note:
        group_id is normalized to a canonical timestamp (rounded to nearest 10s)
        to ensure all subbands from the same observation get the same group_id,
        even if they were written a few seconds apart.
    """
    match = _HDF5_FILENAME_PATTERN.search(filename)
    if not match:
        return None
    
    timestamp_iso = match.group("timestamp")
    subband_str = match.group("subband")
    
    try:
        subband_num = int(subband_str)
    except ValueError:
        return None
    
    # Parse date and time components
    obs_date = timestamp_iso.split("T")[0]  # YYYY-MM-DD
    obs_time = timestamp_iso.split("T")[1]  # HH:MM:SS
    
    # Normalize group_id to canonical timestamp (handles files written seconds apart)
    group_id = normalize_group_timestamp(timestamp_iso)
    
    return {
        "timestamp_iso": timestamp_iso,
        "group_id": group_id,  # Normalized to canonical timestamp
        "subband_code": f"sb{subband_str}",
        "subband_num": subband_num,
        "obs_date": obs_date,
        "obs_time": obs_time,
    }


def iso_to_mjd(timestamp_iso: str) -> float:
    """
    Convert ISO timestamp to MJD using astropy.
    
    Args:
        timestamp_iso: ISO format timestamp like '2025-01-15T12:30:00'
    
    Returns:
        MJD (Modified Julian Date) as float.
    """
    from astropy.time import Time
    t = Time(timestamp_iso, format="isot", scale="utc")
    return t.mjd


def index_orphaned_files(
    db_path: str,
    storage_dir: str,
    orphaned_files: Optional[List[str]] = None,
    batch_size: int = 1000,
    dry_run: bool = True,
) -> dict:
    """
    Index orphaned files (files on disk not in database) into the HDF5 index.
    
    This function parses HDF5 filenames to extract metadata and inserts
    records into the hdf5_file_index table.
    
    Args:
        db_path: Path to HDF5 index SQLite database.
        storage_dir: Directory containing HDF5 files.
        orphaned_files: Optional list of orphaned file paths. If None,
            will run validate_hdf5_storage() to find them.
        batch_size: Number of files to insert per transaction.
        dry_run: If True, don't actually modify database.
    
    Returns:
        Dictionary with indexing results:
        - total_orphaned: Number of orphaned files found
        - parsed_ok: Number of files with valid filename format
        - parse_failed: Number of files that couldn't be parsed
        - indexed: Number of files successfully indexed
        - errors: List of error messages
        - sample_parse_failures: Sample of files that couldn't be parsed
    """
    results = {
        "dry_run": dry_run,
        "total_orphaned": 0,
        "parsed_ok": 0,
        "parse_failed": 0,
        "indexed": 0,
        "errors": [],
        "sample_parse_failures": [],
    }
    
    # Get orphaned files if not provided
    if orphaned_files is None:
        validation = validate_hdf5_storage(db_path, storage_dir, full_check=True)
        orphaned_files = validation.on_disk_not_in_db
    
    results["total_orphaned"] = len(orphaned_files)
    
    if not orphaned_files:
        logger.info("No orphaned files to index")
        return results
    
    # Parse all files and collect valid records
    records_to_insert = []
    
    for file_path in orphaned_files:
        filename = os.path.basename(file_path)
        parsed = parse_hdf5_filename(filename)
        
        if parsed is None:
            results["parse_failed"] += 1
            if len(results["sample_parse_failures"]) < 10:
                results["sample_parse_failures"].append(filename)
            continue
        
        results["parsed_ok"] += 1
        
        # Get file stats
        try:
            stat = os.stat(file_path)
            file_size = stat.st_size
            modified_time = stat.st_mtime
        except OSError as e:
            results["errors"].append(f"Failed to stat {file_path}: {e}")
            continue
        
        # Convert timestamp to MJD
        try:
            timestamp_mjd = iso_to_mjd(parsed["timestamp_iso"])
        except Exception as e:
            results["errors"].append(f"Failed to convert timestamp for {filename}: {e}")
            continue
        
        # Build record tuple for insertion
        record = (
            file_path,                    # path
            filename,                     # filename
            parsed["group_id"],           # group_id
            parsed["subband_code"],       # subband_code
            parsed["subband_num"],        # subband_num
            parsed["timestamp_iso"],      # timestamp_iso
            timestamp_mjd,                # timestamp_mjd
            file_size,                    # file_size_bytes
            modified_time,                # modified_time
            time.time(),                  # indexed_at
            1,                            # stored
            None,                         # ra_deg (unknown)
            None,                         # dec_deg (unknown)
            parsed["obs_date"],           # obs_date
            parsed["obs_time"],           # obs_time
        )
        records_to_insert.append(record)
    
    logger.info(
        f"Parsed {results['parsed_ok']} files successfully, "
        f"{results['parse_failed']} failed to parse"
    )
    
    if dry_run:
        results["indexed"] = len(records_to_insert)
        logger.info(f"Dry run: would index {results['indexed']} files")
        return results
    
    # Insert records in batches
    try:
        conn = sqlite3.connect(db_path, timeout=60)
        cursor = conn.cursor()
        
        insert_sql = """
            INSERT OR REPLACE INTO hdf5_file_index 
            (path, filename, group_id, subband_code, subband_num, 
             timestamp_iso, timestamp_mjd, file_size_bytes, modified_time,
             indexed_at, stored, ra_deg, dec_deg, obs_date, obs_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for i in range(0, len(records_to_insert), batch_size):
            batch = records_to_insert[i:i + batch_size]
            try:
                cursor.executemany(insert_sql, batch)
                conn.commit()
                results["indexed"] += len(batch)
                logger.info(f"Indexed batch {i // batch_size + 1}: {len(batch)} files")
            except sqlite3.Error as e:
                results["errors"].append(f"Batch insert error at {i}: {e}")
                conn.rollback()
        
        conn.close()
        
        logger.info(f"Successfully indexed {results['indexed']} files")
        
    except sqlite3.Error as e:
        results["errors"].append(f"Database error: {e}")
    
    return results


def full_reconciliation(
    db_path: str,
    storage_dir: str,
    mark_removed: bool = True,
    index_orphaned: bool = True,
    dry_run: bool = True,
) -> dict:
    """
    Perform full database reconciliation with filesystem.
    
    This combines both:
    1. Marking stale records (in DB but not on disk) as removed
    2. Indexing orphaned files (on disk but not in DB)
    
    Args:
        db_path: Path to HDF5 index SQLite database.
        storage_dir: Directory containing HDF5 files.
        mark_removed: If True, mark missing files as stored=0.
        index_orphaned: If True, index orphaned files.
        dry_run: If True, don't actually modify database.
    
    Returns:
        Dictionary with full reconciliation results.
    """
    results = {
        "dry_run": dry_run,
        "reconciliation": {},
        "indexing": {},
        "pre_sync_percentage": 0.0,
        "post_sync_percentage": 0.0,
    }
    
    # Get pre-reconciliation metrics
    pre_validation = validate_hdf5_storage(db_path, storage_dir, full_check=True)
    results["pre_sync_percentage"] = pre_validation.sync_percentage
    
    # Step 1: Mark stale records
    reconcile_result = reconcile_storage(
        db_path, storage_dir, mark_removed=mark_removed, dry_run=dry_run
    )
    results["reconciliation"] = reconcile_result
    
    # Step 2: Index orphaned files
    if index_orphaned:
        index_result = index_orphaned_files(
            db_path, storage_dir,
            orphaned_files=pre_validation.on_disk_not_in_db,
            dry_run=dry_run
        )
        results["indexing"] = index_result
    
    # Get post-reconciliation metrics (if not dry run)
    if not dry_run:
        post_validation = validate_hdf5_storage(db_path, storage_dir, full_check=False)
        results["post_sync_percentage"] = post_validation.sync_percentage
    else:
        # Estimate post-sync percentage
        total_on_disk = pre_validation.files_on_disk
        indexed_ok = results.get("indexing", {}).get("indexed", 0)
        stale_marked = reconcile_result.get("stale_records_to_mark", 0)
        
        # After reconciliation:
        # - Stale records removed from "stored" count
        # - Orphaned files indexed and added to "stored" count
        new_stored = pre_validation.files_in_db_stored - stale_marked + indexed_ok
        if total_on_disk > 0:
            results["post_sync_percentage"] = round((new_stored / total_on_disk) * 100, 2)
    
    return results
