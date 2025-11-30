"""
Batch job creation and management utilities.

This module provides functions for creating and updating batch jobs
in the database, supporting various job types:
- Standard batch processing
- Conversion jobs
- Publish jobs
- Photometry jobs
- ESE detection jobs
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Database Schema Management
# =============================================================================

def ensure_batch_tables(conn: sqlite3.Connection) -> None:
    """Ensure batch job tables exist in the database.
    
    Creates the batch_jobs and batch_job_items tables if they don't exist.
    This should be called before any batch operations to ensure schema exists.
    
    Args:
        conn: SQLite database connection
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            total_items INTEGER NOT NULL,
            completed_items INTEGER DEFAULT 0,
            failed_items INTEGER DEFAULT 0,
            params TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_job_items (
            id INTEGER PRIMARY KEY,
            batch_id INTEGER NOT NULL,
            ms_path TEXT NOT NULL,
            job_id INTEGER,
            status TEXT NOT NULL,
            error TEXT,
            started_at REAL,
            completed_at REAL,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
        """
    )
    conn.commit()


def ensure_data_id_column(conn: sqlite3.Connection) -> None:
    """Ensure data_id column exists in batch_job_items table.
    
    This handles migration for older databases that don't have
    the data_id column.
    
    Args:
        conn: SQLite database connection
    """
    try:
        conn.execute("SELECT data_id FROM batch_job_items LIMIT 1")
    except sqlite3.OperationalError:
        try:
            conn.execute("ALTER TABLE batch_job_items ADD COLUMN data_id TEXT DEFAULT NULL")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column may already exist from concurrent creation


# =============================================================================
# Validation Helpers
# =============================================================================

def _validate_job_type(job_type: str) -> None:
    """Validate job_type parameter."""
    if not isinstance(job_type, str) or not job_type.strip():
        raise ValueError("job_type must be a non-empty string")


def _validate_string_list(items: List[str], name: str) -> None:
    """Validate a list of strings."""
    if not isinstance(items, list):
        raise ValueError(f"{name} must be a list")
    if not all(isinstance(p, str) and p.strip() for p in items):
        raise ValueError(f"All {name} must be non-empty strings")


def _validate_params(params: Dict[str, Any]) -> None:
    """Validate params dictionary."""
    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")


# =============================================================================
# Batch Job Creation
# =============================================================================

def create_batch_job(
    conn: sqlite3.Connection,
    job_type: str,
    ms_paths: List[str],
    params: Dict[str, Any],
) -> int:
    """Create a batch job in the database.
    
    Args:
        conn: SQLite database connection
        job_type: Type of batch job (e.g., "batch_calibration", "batch_image")
        ms_paths: List of measurement set paths to process
        params: Job parameters dictionary
        
    Returns:
        Batch job ID
        
    Raises:
        ValueError: If parameters are invalid
    """
    # Input validation
    _validate_job_type(job_type)
    _validate_string_list(ms_paths, "ms_paths")
    _validate_params(params)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            datetime.utcnow().timestamp(),
            "pending",
            len(ms_paths),
            0,
            0,
            str(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Insert batch items
    for ms_path in ms_paths:
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, ms_path, "pending"),
        )

    conn.commit()
    return batch_id


def create_batch_conversion_job(
    conn: sqlite3.Connection,
    job_type: str,
    time_windows: List[Dict[str, str]],
    params: Dict[str, Any],
) -> int:
    """Create a batch conversion job in the database.

    Args:
        conn: Database connection
        job_type: Job type (e.g., "batch_convert")
        time_windows: List of time window dicts with "start_time" and "end_time"
        params: Shared parameters for all conversion jobs

    Returns:
        Batch job ID
        
    Raises:
        ValueError: If parameters are invalid
    """
    # Input validation
    _validate_job_type(job_type)
    if not isinstance(time_windows, list):
        raise ValueError("time_windows must be a list")
    if not all(
        isinstance(tw, dict)
        and "start_time" in tw
        and "end_time" in tw
        and isinstance(tw["start_time"], str)
        and isinstance(tw["end_time"], str)
        for tw in time_windows
    ):
        raise ValueError("All time_windows must be dicts with 'start_time' and 'end_time' strings")
    _validate_params(params)

    # Ensure tables exist
    ensure_batch_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            datetime.utcnow().timestamp(),
            "pending",
            len(time_windows),
            0,
            0,
            str(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Insert batch items using time window identifiers
    for tw in time_windows:
        time_window_id = f"time_window_{tw['start_time']}_{tw['end_time']}"
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, time_window_id, "pending"),
        )

    conn.commit()
    return batch_id


def create_batch_publish_job(
    conn: sqlite3.Connection,
    job_type: str,
    data_ids: List[str],
    params: Dict[str, Any],
) -> int:
    """Create a batch publish job in the database.

    Args:
        conn: Database connection
        job_type: Job type (e.g., "batch_publish")
        data_ids: List of data instance IDs to publish
        params: Shared parameters for all publish jobs (e.g., products_base)

    Returns:
        Batch job ID
        
    Raises:
        ValueError: If parameters are invalid
    """
    _validate_job_type(job_type)
    _validate_string_list(data_ids, "data_ids")
    _validate_params(params)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            datetime.utcnow().timestamp(),
            "pending",
            len(data_ids),
            0,
            0,
            str(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Insert batch items using data_ids
    for data_id in data_ids:
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, data_id, "pending"),
        )

    conn.commit()
    return batch_id


def create_batch_photometry_job(
    conn: sqlite3.Connection,
    job_type: str,
    fits_paths: List[str],
    coordinates: List[dict],
    params: Dict[str, Any],
    data_id: Optional[str] = None,
) -> int:
    """Create a batch photometry job in the database.

    Args:
        conn: Database connection
        job_type: Job type (e.g., "batch_photometry")
        fits_paths: List of FITS image paths to process
        coordinates: List of coordinate dicts with ra_deg and dec_deg
        params: Shared parameters for all photometry jobs
        data_id: Optional data ID to link photometry job to data registry

    Returns:
        Batch job ID
        
    Raises:
        ValueError: If parameters are invalid
    """
    # Ensure tables exist
    ensure_batch_tables(conn)
    ensure_data_id_column(conn)

    # Input validation
    _validate_job_type(job_type)
    _validate_string_list(fits_paths, "fits_paths")
    if not isinstance(coordinates, list):
        raise ValueError("coordinates must be a list")
    _validate_params(params)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            datetime.utcnow().timestamp(),
            "pending",
            len(fits_paths) * len(coordinates),
            0,
            0,
            json.dumps(params) if isinstance(params, dict) else str(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Insert batch items (one per image-coordinate pair)
    for fits_path in fits_paths:
        for coord in coordinates:
            item_id = f"{fits_path}:{coord['ra_deg']}:{coord['dec_deg']}"
            cursor.execute(
                """
                INSERT INTO batch_job_items (batch_id, ms_path, status, data_id)
                VALUES (?, ?, ?, ?)
                """,
                (batch_id, item_id, "pending", data_id),
            )

    conn.commit()
    return batch_id


def create_batch_ese_detect_job(
    conn: sqlite3.Connection,
    job_type: str,
    params: Dict[str, Any],
) -> int:
    """Create a batch ESE detection job in the database.

    Args:
        conn: Database connection
        job_type: Job type (e.g., "batch_ese-detect")
        params: ESE detection parameters (min_sigma, recompute, source_ids)

    Returns:
        Batch job ID
        
    Raises:
        ValueError: If parameters are invalid
    """
    # Ensure tables exist
    ensure_batch_tables(conn)

    # Input validation
    _validate_job_type(job_type)
    _validate_params(params)

    source_ids = params.get("source_ids")
    if source_ids is not None:
        if not isinstance(source_ids, list):
            raise ValueError("source_ids must be a list")
        if not all(isinstance(sid, str) and sid.strip() for sid in source_ids):
            raise ValueError("All source_ids must be non-empty strings")
        total_items = len(source_ids)
    else:
        # Will process all sources (single item)
        total_items = 1

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO batch_jobs (type, created_at, status, total_items, completed_items, failed_items, params)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_type,
            time.time(),
            "pending",
            total_items,
            0,
            0,
            json.dumps(params),
        ),
    )
    batch_id = cursor.lastrowid

    # Create batch job items
    if source_ids:
        for source_id in source_ids:
            cursor.execute(
                """
                INSERT INTO batch_job_items (batch_id, ms_path, status)
                VALUES (?, ?, ?)
                """,
                (batch_id, source_id, "pending"),
            )
    else:
        # Single item for "all sources"
        cursor.execute(
            """
            INSERT INTO batch_job_items (batch_id, ms_path, status)
            VALUES (?, ?, ?)
            """,
            (batch_id, "all_sources", "pending"),
        )

    conn.commit()
    return batch_id


# =============================================================================
# Batch Item Updates
# =============================================================================

def update_batch_item(
    conn: sqlite3.Connection,
    batch_id: int,
    ms_path: str,
    job_id: Optional[int],
    status: str,
    error: Optional[str] = None,
) -> None:
    """Update a batch job item status.
    
    Args:
        conn: Database connection
        batch_id: Batch job ID
        ms_path: Path or identifier for the item
        job_id: Individual job ID (if created)
        status: New status (pending, running, done, failed, cancelled)
        error: Error message (if failed)
        
    Raises:
        ValueError: If parameters are invalid
    """
    # Input validation
    if not isinstance(batch_id, int) or batch_id < 1:
        raise ValueError("batch_id must be a positive integer")
    if not isinstance(ms_path, str) or not ms_path.strip():
        raise ValueError("ms_path must be a non-empty string")
    if status not in ("pending", "running", "done", "failed", "cancelled"):
        raise ValueError(f"Invalid status: {status}")
    if job_id is not None and (not isinstance(job_id, int) or job_id < 1):
        raise ValueError("job_id must be None or a positive integer")

    cursor = conn.cursor()
    timestamp = datetime.utcnow().timestamp()

    if status == "running":
        cursor.execute(
            """
            UPDATE batch_job_items
            SET job_id = ?, status = ?, started_at = ?
            WHERE batch_id = ? AND ms_path = ?
            """,
            (job_id, status, timestamp, batch_id, ms_path),
        )
    elif status in ("done", "failed", "cancelled"):
        cursor.execute(
            """
            UPDATE batch_job_items
            SET status = ?, completed_at = ?, error = ?
            WHERE batch_id = ? AND ms_path = ?
            """,
            (status, timestamp, error, batch_id, ms_path),
        )

    # Update batch job counts
    cursor.execute(
        """
        SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ? AND status = 'done'
        """,
        (batch_id,),
    )
    completed = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ? AND status = 'failed'
        """,
        (batch_id,),
    )
    failed = cursor.fetchone()[0]

    # Determine overall batch status
    cursor.execute(
        """
        SELECT COUNT(*) FROM batch_job_items WHERE batch_id = ? AND status IN ('pending', 'running')
        """,
        (batch_id,),
    )
    remaining = cursor.fetchone()[0]

    if remaining == 0:
        batch_status = "done" if failed == 0 else "failed"
    else:
        batch_status = "running"

    cursor.execute(
        """
        UPDATE batch_jobs
        SET completed_items = ?, failed_items = ?, status = ?
        WHERE id = ?
        """,
        (completed, failed, batch_status, batch_id),
    )

    conn.commit()


def update_batch_conversion_item(
    conn: sqlite3.Connection,
    batch_id: int,
    time_window_id: str,
    job_id: Optional[int],
    status: str,
    error: Optional[str] = None,
) -> None:
    """Update a batch conversion job item status.

    This is an alias for update_batch_item with a time window identifier.

    Args:
        conn: Database connection
        batch_id: Batch job ID
        time_window_id: Time window identifier (format: "time_window_{start}_{end}")
        job_id: Individual job ID (if created)
        status: Status (pending, running, done, failed, cancelled)
        error: Error message (if failed)
    """
    update_batch_item(conn, batch_id, time_window_id, job_id, status, error)
