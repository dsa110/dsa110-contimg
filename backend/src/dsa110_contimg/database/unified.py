"""
Unified database layer for DSA-110 Continuum Imaging Pipeline.

This module provides a simplified database interface as outlined in the
complexity reduction guide. It replaces the multi-database architecture
with a single unified database (pipeline.sqlite3).

Design Goals:
- Single SQLite database instead of 5+ separate databases
- Simple Database class (~65 lines) instead of 800+ lines of abstraction
- Direct SQL with sqlite3.Row for dict-like access
- Context manager for safe connection handling
- WAL mode for concurrent access

Target Schema (unified from products, cal_registry, ingest, calibrators, hdf5):
- ms_index: Measurement Set products with stage tracking
- images: Image products linked to MS
- photometry: Photometric measurements
- calibration_tables: Calibration table registry
- calibration_applied: Record of calibration applications
- calibrator_catalog: VLA and bandpass calibrators
- hdf5_files: Raw HDF5 file index
- processing_queue: Ingest/processing queue with retry logic
- calibrator_transits: Transit time calculations

Usage:
    from dsa110_contimg.database.unified import Database
    
    # Query with dict-like results
    db = Database()
    images = db.query(
        "SELECT * FROM images WHERE noise_jy < ?", 
        (0.001,)
    )
    for img in images:
        print(f"{img['path']}: {img['noise_jy']} Jy")
    
    # Write operations
    db.execute(
        "INSERT INTO images (path, ms_path, created_at, type) VALUES (?, ?, ?, ?)",
        ("/path/to/image.fits", "/path/to/ms", time.time(), "dirty")
    )
    
    # Context manager for transactions
    with db.transaction() as conn:
        conn.execute("INSERT INTO ...")
        conn.execute("UPDATE ...")
    # Auto-commits on success, rolls back on error

Migration:
    Run the migration script to consolidate existing databases:
    $ python scripts/migrate_databases.py --dry-run  # Preview
    $ python scripts/migrate_databases.py            # Execute
"""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

# Default database path
DEFAULT_PIPELINE_DB = "/data/dsa110-contimg/state/db/pipeline.sqlite3"

# Schema file path (relative to this module)
_SCHEMA_FILE = Path(__file__).parent / "schema.sql"


def _load_schema() -> str:
    """Load the unified schema from the external SQL file."""
    if _SCHEMA_FILE.exists():
        return _SCHEMA_FILE.read_text()
    else:
        raise FileNotFoundError(
            f"Schema file not found: {_SCHEMA_FILE}. "
            "This file should be distributed with the package."
        )


# Lazy-loaded schema (cached after first load)
_CACHED_SCHEMA: Optional[str] = None


def get_unified_schema() -> str:
    """Get the unified database schema SQL.
    
    The schema is loaded from schema.sql and cached for subsequent calls.
    
    Returns:
        SQL schema definition string
    """
    global _CACHED_SCHEMA
    if _CACHED_SCHEMA is None:
        _CACHED_SCHEMA = _load_schema()
    return _CACHED_SCHEMA


# Backward compatibility alias
UNIFIED_SCHEMA = property(lambda self: get_unified_schema())


class Database:
    """
    Simple SQLite database wrapper for the unified pipeline database.
    
    This class replaces ~800 lines of abstraction with a simple, direct
    interface to SQLite. It uses sqlite3.Row for dict-like access and
    provides WAL mode for concurrent access.
    
    Thread Safety:
        The connection is created with check_same_thread=False, but
        concurrent writes should use the transaction() context manager
        to ensure proper locking.
    
    Attributes:
        db_path: Path to the SQLite database file
        timeout: Connection timeout in seconds (default: 30.0)
    """
    
    def __init__(
        self, 
        db_path: Optional[Union[str, Path]] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database. If None, reads from
                     PIPELINE_DB env var or uses default.
            timeout: Connection timeout in seconds.
        """
        if db_path is None:
            db_path = os.environ.get("PIPELINE_DB", DEFAULT_PIPELINE_DB)
        
        self.db_path = Path(db_path)
        self.timeout = timeout
        self._conn: Optional[sqlite3.Connection] = None
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create database connection with proper settings."""
        if self._conn is None:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._conn = sqlite3.connect(
                str(self.db_path),
                timeout=self.timeout,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent access
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=30000")  # 30s busy timeout
        return self._conn
    
    def query(
        self, 
        sql: str, 
        params: tuple = ()
    ) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return list of dicts.
        
        Args:
            sql: SQL query string with ? placeholders
            params: Query parameters tuple
            
        Returns:
            List of dictionaries, one per row
            
        Example:
            images = db.query(
                "SELECT * FROM images WHERE type = ?", 
                ("dirty",)
            )
        """
        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def query_one(
        self, 
        sql: str, 
        params: tuple = ()
    ) -> Optional[Dict[str, Any]]:
        """
        Execute SELECT query and return single row or None.
        
        Args:
            sql: SQL query string with ? placeholders
            params: Query parameters tuple
            
        Returns:
            Single row as dict, or None if no results
        """
        cursor = self.conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def query_val(
        self, 
        sql: str, 
        params: tuple = ()
    ) -> Any:
        """
        Execute SELECT query and return single value.
        
        Args:
            sql: SQL query string with ? placeholders
            params: Query parameters tuple
            
        Returns:
            First column of first row, or None
            
        Example:
            count = db.query_val("SELECT COUNT(*) FROM images")
        """
        cursor = self.conn.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row else None
    
    def execute(
        self, 
        sql: str, 
        params: tuple = ()
    ) -> int:
        """
        Execute INSERT/UPDATE/DELETE and return affected rows.
        
        This method auto-commits. For multi-statement transactions,
        use the transaction() context manager.
        
        Args:
            sql: SQL statement with ? placeholders
            params: Statement parameters tuple
            
        Returns:
            Number of rows affected
        """
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        return cursor.rowcount
    
    def execute_many(
        self,
        sql: str,
        params_list: List[tuple],
    ) -> int:
        """
        Execute statement for multiple parameter sets.
        
        More efficient than calling execute() in a loop.
        
        Args:
            sql: SQL statement with ? placeholders
            params_list: List of parameter tuples
            
        Returns:
            Total number of rows affected
        """
        cursor = self.conn.executemany(sql, params_list)
        self.conn.commit()
        return cursor.rowcount
    
    def execute_script(self, sql: str) -> None:
        """
        Execute multiple SQL statements (for schema creation).
        
        Args:
            sql: SQL script with multiple statements
        """
        self.conn.executescript(sql)
    
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Transaction context manager with auto-commit/rollback.
        
        Yields:
            sqlite3.Connection for executing statements
            
        Example:
            with db.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
            # Auto-committed on success, rolled back on error
        """
        try:
            self.conn.execute("BEGIN")
            yield self.conn
            self.conn.commit()
        except (sqlite3.Error, OSError, ValueError):
            self.conn.rollback()
            raise
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
    
    def __enter__(self) -> "Database":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close connection."""
        self.close()



# =============================================================================
# Schema Loading (external file)
# =============================================================================

# UNIFIED_SCHEMA is now loaded from schema.sql file
# Use get_unified_schema() to access it


def init_unified_db(db_path: Optional[Union[str, Path]] = None) -> Database:
    """
    Initialize the unified database with schema.
    
    Creates the database file and all tables if they don't exist.
    The schema is loaded from schema.sql in the same directory.
    
    Args:
        db_path: Path to database. Uses PIPELINE_DB env var or default.
        
    Returns:
        Database instance ready for use
    """
    db = Database(db_path)
    db.execute_script(get_unified_schema())
    return db



# =============================================================================
# Global Instance (singleton pattern)
# =============================================================================

_global_db: Optional[Database] = None


def get_db(db_path: Optional[Union[str, Path]] = None) -> Database:
    """
    Get or create global database instance.
    
    This provides a singleton database connection for the application.
    For multi-threaded contexts, consider creating per-thread instances.
    
    Args:
        db_path: Path to database (only used on first call)
        
    Returns:
        Shared Database instance
    """
    global _global_db
    if _global_db is None:
        _global_db = Database(db_path)
    return _global_db


def close_db() -> None:
    """Close the global database connection."""
    global _global_db
    if _global_db is not None:
        _global_db.close()
        _global_db = None


# =============================================================================
# Helper Functions (replacing legacy modules)
# =============================================================================

def ensure_pipeline_db() -> sqlite3.Connection:
    """
    Ensure the unified pipeline database exists and return a connection.
    
    This replaces ensure_products_db, ensure_ingest_db, etc.
    
    Returns:
        sqlite3.Connection to the pipeline database
    """
    db = init_unified_db()
    return db.conn


# Jobs helpers (replacing jobs.py)

def create_job(
    conn: sqlite3.Connection,
    job_type: str,
    ms_path: str,
    params: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Create a new job record.
    
    Args:
        conn: Database connection
        job_type: Type of job (e.g., 'calibration', 'imaging')
        ms_path: Path to measurement set
        params: Optional job parameters (stored as JSON)
        
    Returns:
        Job ID
    """
    import json
    import time
    params_json = json.dumps(params) if params else None
    cursor = conn.execute(
        """
        INSERT INTO jobs (type, status, ms_path, params, created_at)
        VALUES (?, 'pending', ?, ?, ?)
        """,
        (job_type, ms_path, params_json, time.time())
    )
    conn.commit()
    return cursor.lastrowid


def update_job_status(
    conn: sqlite3.Connection,
    job_id: int,
    status: str,
    **kwargs
) -> None:
    """
    Update job status and optional fields.
    
    Args:
        conn: Database connection
        job_id: Job ID to update
        status: New status ('pending', 'running', 'completed', 'failed')
        **kwargs: Additional fields to update (started_at, finished_at, logs, artifacts)
    """
    import json
    import time
    
    updates = ["status = ?"]
    values = [status]
    
    if status == "running" and "started_at" not in kwargs:
        updates.append("started_at = ?")
        values.append(time.time())
    
    if status in ("completed", "failed") and "finished_at" not in kwargs:
        updates.append("finished_at = ?")
        values.append(time.time())
    
    for key, value in kwargs.items():
        if key in ("started_at", "finished_at"):
            updates.append(f"{key} = ?")
            values.append(value)
        elif key in ("logs", "artifacts"):
            updates.append(f"{key} = ?")
            values.append(json.dumps(value) if isinstance(value, (dict, list)) else value)
    
    values.append(job_id)
    conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", values)
    conn.commit()


def append_job_log(conn: sqlite3.Connection, job_id: int, line: str) -> None:
    """
    Append a line to the job's log.
    
    Args:
        conn: Database connection
        job_id: Job ID
        line: Log line to append
    """
    cursor = conn.execute("SELECT logs FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    existing = row[0] if row and row[0] else ""
    new_logs = existing + line + "\n" if existing else line + "\n"
    conn.execute("UPDATE jobs SET logs = ? WHERE id = ?", (new_logs, job_id))
    conn.commit()


def get_job(conn: sqlite3.Connection, job_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a job by ID.
    
    Args:
        conn: Database connection
        job_id: Job ID
        
    Returns:
        Job record as dict, or None if not found
    """
    cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    if row:
        return dict(zip([d[0] for d in cursor.description], row))
    return None


def list_jobs(
    conn: sqlite3.Connection,
    limit: int = 50,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List jobs, optionally filtered by status.
    
    Args:
        conn: Database connection
        limit: Maximum number of jobs to return
        status: Optional status filter
        
    Returns:
        List of job records as dicts
    """
    if status:
        cursor = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit)
        )
    else:
        cursor = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
    return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]


# MS/Products helpers (replacing products.py)

def ms_index_upsert(
    conn: sqlite3.Connection,
    ms_path: str,
    **kwargs
) -> None:
    """
    Insert or update an MS index record.
    
    Args:
        conn: Database connection
        ms_path: Path to measurement set (primary key)
        **kwargs: Additional fields to set
    """
    import time
    
    # Check if record exists
    cursor = conn.execute("SELECT 1 FROM ms_index WHERE path = ?", (ms_path,))
    exists = cursor.fetchone() is not None
    
    if exists:
        # Update existing record
        if kwargs:
            updates = [f"{k} = ?" for k in kwargs.keys()]
            conn.execute(
                f"UPDATE ms_index SET {', '.join(updates)} WHERE path = ?",
                list(kwargs.values()) + [ms_path]
            )
    else:
        # Insert new record
        kwargs.setdefault("created_at", time.time())
        columns = ["path"] + list(kwargs.keys())
        placeholders = ", ".join("?" for _ in columns)
        conn.execute(
            f"INSERT INTO ms_index ({', '.join(columns)}) VALUES ({placeholders})",
            [ms_path] + list(kwargs.values())
        )
    conn.commit()


def images_insert(
    conn: sqlite3.Connection,
    path: str,
    ms_path: str,
    image_type: str,
    **kwargs
) -> int:
    """
    Insert an image record.
    
    Args:
        conn: Database connection
        path: Path to image file
        ms_path: Path to source measurement set
        image_type: Type of image (e.g., 'dirty', 'clean', 'residual')
        **kwargs: Additional fields
        
    Returns:
        Image ID
    """
    import time
    kwargs.setdefault("created_at", time.time())
    
    columns = ["path", "ms_path", "type"] + list(kwargs.keys())
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT OR REPLACE INTO images ({', '.join(columns)}) VALUES ({placeholders})",
        [path, ms_path, image_type] + list(kwargs.values())
    )
    conn.commit()
    return cursor.lastrowid


def photometry_insert(
    conn: sqlite3.Connection,
    image_path: str,
    source_id: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    **kwargs
) -> int:
    """
    Insert a photometry measurement.
    
    Args:
        conn: Database connection
        image_path: Path to source image
        source_id: Source identifier
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        flux_jy: Flux in Jansky
        **kwargs: Additional fields (flux_err_jy, peak_flux_jy, rms_jy, etc.)
        
    Returns:
        Photometry record ID
    """
    import time
    kwargs.setdefault("measured_at", time.time())
    
    columns = ["image_path", "source_id", "ra_deg", "dec_deg", "flux_jy"] + list(kwargs.keys())
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT INTO photometry ({', '.join(columns)}) VALUES ({placeholders})",
        [image_path, source_id, ra_deg, dec_deg, flux_jy] + list(kwargs.values())
    )
    conn.commit()
    return cursor.lastrowid


# Calibrator helpers (replacing calibrators.py)

def get_bandpass_calibrators(
    conn: sqlite3.Connection,
    dec_range: Optional[tuple] = None,
    status: str = "active"
) -> List[Dict[str, Any]]:
    """
    Get bandpass calibrators, optionally filtered by declination range.
    
    Args:
        conn: Database connection
        dec_range: Optional (min_dec, max_dec) tuple to filter by declination
        status: Status filter (default: 'active')
        
    Returns:
        List of calibrator records as dicts
    """
    if dec_range:
        cursor = conn.execute(
            """
            SELECT * FROM bandpass_calibrators 
            WHERE status = ? AND dec_range_min <= ? AND dec_range_max >= ?
            ORDER BY dec_deg
            """,
            (status, dec_range[1], dec_range[0])
        )
    else:
        cursor = conn.execute(
            "SELECT * FROM bandpass_calibrators WHERE status = ? ORDER BY dec_deg",
            (status,)
        )
    return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]


def register_bandpass_calibrator(
    conn: sqlite3.Connection,
    name: str,
    ra_deg: float,
    dec_deg: float,
    **kwargs
) -> int:
    """
    Register a bandpass calibrator.
    
    Args:
        conn: Database connection
        name: Calibrator name
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        **kwargs: Additional fields (dec_range_min, dec_range_max, flux_jy, etc.)
        
    Returns:
        Calibrator ID
    """
    import time
    kwargs.setdefault("registered_at", time.time())
    
    columns = ["calibrator_name", "ra_deg", "dec_deg"] + list(kwargs.keys())
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT OR REPLACE INTO bandpass_calibrators ({', '.join(columns)}) VALUES ({placeholders})",
        [name, ra_deg, dec_deg] + list(kwargs.values())
    )
    conn.commit()
    return cursor.lastrowid


# Pointing helpers

def log_pointing(
    conn: sqlite3.Connection,
    timestamp_mjd: float,
    ra_deg: float,
    dec_deg: float,
) -> None:
    """
    Log pointing to pointing_history table.

    Args:
        conn: Database connection
        timestamp_mjd: Observation timestamp (MJD)
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO pointing_history (timestamp, ra_deg, dec_deg)
        VALUES (?, ?, ?)
        """,
        (timestamp_mjd, ra_deg, dec_deg),
    )
    conn.commit()
