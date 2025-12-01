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
