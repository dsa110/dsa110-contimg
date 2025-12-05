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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

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


def get_pipeline_db_path() -> Path:
    """Get the path to the unified pipeline database.

    Returns:
        Path to the pipeline.sqlite3 database.
        
    Note:
        Checks PIPELINE_DB environment variable first,
        then falls back to default path.
    """
    env_path = os.environ.get("PIPELINE_DB")
    if env_path:
        return Path(env_path)
    return Path(DEFAULT_PIPELINE_DB)


# Backward compatibility alias
get_calibrators_db_path = get_pipeline_db_path


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


# Backward compatibility: UNIFIED_SCHEMA loaded lazily from schema.sql
# Use get_unified_schema() for the recommended API


def __getattr__(name: str) -> str:
    """Module-level __getattr__ for lazy loading UNIFIED_SCHEMA."""
    if name == "UNIFIED_SCHEMA":
        return get_unified_schema()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    Also runs pending migrations for schema updates.
    
    Args:
        db_path: Path to database. Uses PIPELINE_DB env var or default.
        
    Returns:
        Database instance ready for use
    """
    db = Database(db_path)
    db.execute_script(get_unified_schema())
    # Run any pending migrations
    _run_migrations(db)
    return db


def _run_migrations(db: Database) -> None:
    """Run schema migrations for existing databases.
    
    This handles adding new columns to existing tables.
    Uses PRAGMA table_info to check if columns exist before adding.
    
    Args:
        db: Database instance
    """
    migrations = [
        # Add effective_noise_jy to mosaics table
        ("mosaics", "effective_noise_jy", "ALTER TABLE mosaics ADD COLUMN effective_noise_jy REAL"),
    ]
    
    for table, column, sql in migrations:
        # Check if column exists
        cursor = db.conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if column not in columns:
            try:
                db.conn.execute(sql)
                db.conn.commit()
                logger.info(f"Migration: added column {column} to table {table}")
            except sqlite3.OperationalError as e:
                # Column might already exist in some edge cases
                if "duplicate column" not in str(e).lower():
                    logger.warning(f"Migration failed for {table}.{column}: {e}")



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
    validate_image: bool = True,
    **kwargs
) -> int:
    """
    Insert a photometry measurement.
    
    Args:
        conn: Database connection
        image_path: Path to source image (must exist in images table if validate_image=True)
        source_id: Source identifier
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        flux_jy: Flux in Jansky
        validate_image: If True, verify image_path exists in images table (default: True)
        **kwargs: Additional fields (flux_err_jy, peak_flux_jy, rms_jy, etc.)
        
    Returns:
        Photometry record ID
        
    Raises:
        ValueError: If validate_image=True and image_path not found in images table
    """
    import time
    
    # Validate image exists in images table for proper foreign key relationship
    if validate_image:
        cursor = conn.execute(
            "SELECT id FROM images WHERE path = ?",
            (image_path,)
        )
        if cursor.fetchone() is None:
            raise ValueError(
                f"Image path '{image_path}' not found in images table. "
                "Register the image first with register_image() or set validate_image=False."
            )
    
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


# =============================================================================
# Calibration Registry Functions (migrated from registry.py)
# =============================================================================

# Default calibration table apply order
DEFAULT_CALTABLE_ORDER = [
    ("K", 10),    # delays
    ("BA", 20),   # bandpass amplitude
    ("BP", 30),   # bandpass phase
    ("GA", 40),   # gain amplitude
    ("GP", 50),   # gain phase
    ("2G", 60),   # short-timescale ap gains (optional)
    ("FLUX", 70), # fluxscale table (optional)
]


@dataclass
class CalTableRow:
    """Calibration table row for registration."""
    set_name: str
    path: str
    table_type: str
    order_index: int
    cal_field: Optional[str]
    refant: Optional[str]
    valid_start_mjd: Optional[float]
    valid_end_mjd: Optional[float]
    status: str = "active"
    notes: Optional[str] = None
    source_ms_path: Optional[str] = None
    solver_command: Optional[str] = None
    solver_version: Optional[str] = None
    solver_params: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None


def ensure_db(path: Path) -> sqlite3.Connection:
    """Ensure calibration database exists with current schema.
    
    This function creates the caltables table if it doesn't exist and
    handles schema migrations for backwards compatibility.
    
    Args:
        path: Path to database file
        
    Returns:
        sqlite3.Connection to the database
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))

    # Create table with current schema
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS caltables (
            id INTEGER PRIMARY KEY,
            set_name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            table_type TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            cal_field TEXT,
            refant TEXT,
            created_at REAL NOT NULL,
            valid_start_mjd REAL,
            valid_end_mjd REAL,
            status TEXT NOT NULL,
            notes TEXT,
            source_ms_path TEXT,
            solver_command TEXT,
            solver_version TEXT,
            solver_params TEXT,
            quality_metrics TEXT
        )
        """
    )

    # Migrate existing databases by adding new columns if they don't exist
    _migrate_caltables_schema(conn)

    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_caltables_set ON caltables(set_name)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_caltables_valid "
        "ON caltables(valid_start_mjd, valid_end_mjd)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_caltables_source ON caltables(source_ms_path)")
    conn.commit()
    return conn


def _migrate_caltables_schema(conn: sqlite3.Connection) -> None:
    """Migrate existing database schema to add provenance columns."""
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(caltables)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add missing provenance columns
    new_columns = [
        ("source_ms_path", "TEXT"),
        ("solver_command", "TEXT"),
        ("solver_version", "TEXT"),
        ("solver_params", "TEXT"),
        ("quality_metrics", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                conn.execute(f"ALTER TABLE caltables ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError as e:
                # Column might already exist from concurrent migration
                if "duplicate column" not in str(e).lower():
                    raise

    conn.commit()


def _detect_type_from_filename(path: Path) -> Optional[str]:
    """Detect calibration table type from filename suffix."""
    name = path.name.lower()
    if name.endswith("_kcal"):
        return "K"
    if name.endswith("_2kcal"):
        return "K"
    if name.endswith("_bacal"):
        return "BA"
    if name.endswith("_bpcal"):
        return "BP"
    if name.endswith("_gacal"):
        return "GA"
    if name.endswith("_gpcal"):
        return "GP"
    if name.endswith("_2gcal"):
        return "2G"
    if name.endswith("_flux.cal") or name.endswith("_fluxcal"):
        return "FLUX"
    return None


def register_caltable_set(
    db_path: Path,
    set_name: str,
    rows: "Sequence[CalTableRow]",
    *,
    upsert: bool = True,
) -> None:
    """Register a set of calibration tables.
    
    Args:
        db_path: Path to calibration registry database
        set_name: Logical name for this calibration set
        rows: Sequence of CalTableRow objects to register
        upsert: If True, replace existing entries; if False, ignore duplicates
    """
    import json
    
    conn = ensure_db(db_path)
    now = time.time()
    with conn:
        for r in rows:
            solver_params_json = json.dumps(r.solver_params) if r.solver_params else None
            quality_metrics_json = json.dumps(r.quality_metrics) if r.quality_metrics else None

            if upsert:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO caltables(
                        set_name, path, table_type, order_index, cal_field, refant,
                        created_at, valid_start_mjd, valid_end_mjd, status, notes,
                        source_ms_path, solver_command, solver_version, solver_params,
                        quality_metrics
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        r.set_name, os.fspath(r.path), r.table_type, int(r.order_index),
                        r.cal_field, r.refant, now, r.valid_start_mjd, r.valid_end_mjd,
                        r.status, r.notes, r.source_ms_path, r.solver_command,
                        r.solver_version, solver_params_json, quality_metrics_json,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO caltables(
                        set_name, path, table_type, order_index, cal_field, refant,
                        created_at, valid_start_mjd, valid_end_mjd, status, notes,
                        source_ms_path, solver_command, solver_version, solver_params,
                        quality_metrics
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        r.set_name, os.fspath(r.path), r.table_type, int(r.order_index),
                        r.cal_field, r.refant, now, r.valid_start_mjd, r.valid_end_mjd,
                        r.status, r.notes, r.source_ms_path, r.solver_command,
                        r.solver_version, solver_params_json, quality_metrics_json,
                    ),
                )


def register_caltable_set_from_prefix(
    db_path: Path,
    set_name: str,
    prefix: Path,
    *,
    cal_field: Optional[str],
    refant: Optional[str],
    valid_start_mjd: Optional[float],
    valid_end_mjd: Optional[float],
    status: str = "active",
    quality_metrics: Optional[Dict[str, Any]] = None,
) -> List[CalTableRow]:
    """Register calibration tables found with a common prefix.

    Example: prefix="/data/ms/calpass_J1234+5678" will find files named
    calpass_J1234+5678_kcal, _bacal, _bpcal, _gacal, _gpcal, etc.
    
    Args:
        db_path: Path to calibration registry database
        set_name: Logical name for this calibration set
        prefix: Filesystem prefix for calibration tables
        cal_field: Field used for calibration solve
        refant: Reference antenna used
        valid_start_mjd: Start of validity window (MJD)
        valid_end_mjd: End of validity window (MJD)
        status: Status for registered tables (default: "active")
        quality_metrics: Optional QA metrics dict (Issue #5)
        
    Returns:
        List of CalTableRow objects that were registered
    """
    parent = prefix.parent
    base = prefix.name
    found: List[Tuple[str, Path]] = []
    for p in parent.glob(base + "*"):
        if not p.is_dir():
            continue
        t = _detect_type_from_filename(p)
        if t is None:
            continue
        found.append((t, p))

    # Determine apply order using DEFAULT_CALTABLE_ORDER
    order_map = {t: oi for t, oi in DEFAULT_CALTABLE_ORDER}
    rows: List[CalTableRow] = []
    extras: List[Tuple[str, Path]] = []
    
    for t, p in found:
        if t in order_map:
            oi = order_map[t]
        else:
            extras.append((t, p))
            continue
        rows.append(
            CalTableRow(
                set_name=set_name,
                path=str(p),
                table_type=t,
                order_index=oi,
                cal_field=cal_field,
                refant=refant,
                valid_start_mjd=valid_start_mjd,
                valid_end_mjd=valid_end_mjd,
                status=status,
                notes=None,
                quality_metrics=quality_metrics,
            )
        )

    # Append extras at the end in alpha order
    start_idx = max([oi for _, oi in DEFAULT_CALTABLE_ORDER] + [60]) + 10
    for i, (t, p) in enumerate(sorted(extras)):
        rows.append(
            CalTableRow(
                set_name=set_name,
                path=str(p),
                table_type=t,
                order_index=start_idx + 10 * i,
                cal_field=cal_field,
                refant=refant,
                valid_start_mjd=valid_start_mjd,
                valid_end_mjd=valid_end_mjd,
                status=status,
                notes=None,
                quality_metrics=quality_metrics,
            )
        )

    if rows:
        register_caltable_set(db_path, set_name, rows, upsert=True)
    return rows


def retire_caltable_set(db_path: Path, set_name: str, *, reason: Optional[str] = None) -> None:
    """Retire a calibration set (mark as inactive).
    
    Args:
        db_path: Path to calibration registry database
        set_name: Name of set to retire
        reason: Optional reason for retirement (appended to notes)
    """
    conn = ensure_db(db_path)
    with conn:
        conn.execute(
            "UPDATE caltables SET status = 'retired', "
            "notes = COALESCE(notes,'') || ? WHERE set_name = ?",
            (f" Retired: {reason or ''}", set_name),
        )


def list_caltable_sets(db_path: Path) -> List[tuple]:
    """List all calibration sets with summary info.
    
    Args:
        db_path: Path to calibration registry database
        
    Returns:
        List of (set_name, total_count, active_count, min_order) tuples
    """
    conn = ensure_db(db_path)
    cur = conn.execute(
        """
        SELECT set_name,
               COUNT(*) AS nrows,
               SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS n_active,
               MIN(order_index) AS min_order
          FROM caltables
      GROUP BY set_name
      ORDER BY MAX(created_at) DESC
        """
    )
    return [(r[0], r[1], r[2], r[3]) for r in cur.fetchall()]


def get_active_applylist(
    db_path: Path, 
    mjd: float, 
    set_name: Optional[str] = None,
    *,
    bidirectional: bool = True,
    validity_hours: float = 12.0,
) -> List[str]:
    """Return ordered list of active calibration tables applicable to MJD.

    When set_name is provided, restrict to that group; otherwise choose among
    active sets whose validity window includes mjd. If multiple sets match,
    pick the most recently created set.
    
    ISSUE #1 FIX: With bidirectional=True (default), also searches for
    calibrations AFTER the target MJD, not just before. This prevents
    the "calibration validity gap" where pre-calibrator observations
    have no valid calibration.

    Args:
        db_path: Path to calibration registry database
        mjd: Modified Julian Date to find applicable tables for
        set_name: Optional specific set name to query
        bidirectional: If True, search ±validity_hours (fixes Issue #1)
        validity_hours: Maximum time offset for calibration validity (default: 12h)
        
    Returns:
        Ordered list of calibration table paths (by apply order)
    """
    import logging
    logger = logging.getLogger(__name__)

    conn = ensure_db(db_path)
    
    if set_name:
        rows = conn.execute(
            """
            SELECT path FROM caltables
             WHERE set_name = ? AND status = 'active'
             ORDER BY order_index ASC
            """,
            (set_name,),
        ).fetchall()
        return [r[0] for r in rows]

    # Select all sets that cover mjd (exact match first)
    all_matching_sets = conn.execute(
        """
        SELECT DISTINCT set_name, MAX(created_at) AS t
          FROM caltables
         WHERE status = 'active'
           AND (valid_start_mjd IS NULL OR valid_start_mjd <= ?)
           AND (valid_end_mjd   IS NULL OR valid_end_mjd   >= ?)
      GROUP BY set_name
      ORDER BY t DESC
        """,
        (mjd, mjd),
    ).fetchall()

    # ISSUE #1 FIX: If no exact match and bidirectional enabled,
    # search for nearest calibration within ±validity_hours
    if not all_matching_sets and bidirectional:
        validity_days = validity_hours / 24.0
        search_min = mjd - validity_days
        search_max = mjd + validity_days
        
        # Find nearest calibration set (before OR after target)
        nearby_sets = conn.execute(
            """
            SELECT DISTINCT set_name,
                   (valid_start_mjd + COALESCE(valid_end_mjd, valid_start_mjd)) / 2.0 AS mid_mjd,
                   ABS((valid_start_mjd + COALESCE(valid_end_mjd, valid_start_mjd)) / 2.0 - ?) AS distance,
                   MAX(created_at) AS newest
            FROM caltables
            WHERE status = 'active'
              AND valid_start_mjd IS NOT NULL
              AND (
                  -- Set's midpoint is within search range
                  ((valid_start_mjd + COALESCE(valid_end_mjd, valid_start_mjd)) / 2.0 BETWEEN ? AND ?)
              )
            GROUP BY set_name
            ORDER BY distance ASC, newest DESC
            LIMIT 1
            """,
            (mjd, search_min, search_max),
        ).fetchall()
        
        if nearby_sets:
            chosen_set = nearby_sets[0][0]
            distance_days = nearby_sets[0][2]
            distance_hours = distance_days * 24.0
            
            # Determine if calibration is before or after target
            mid_mjd = nearby_sets[0][1]
            direction = "before" if mid_mjd < mjd else "after"
            
            logger.info(
                f"BIDIRECTIONAL SEARCH: No exact calibration match at MJD {mjd:.6f}. "
                f"Using nearest set '{chosen_set}' ({distance_hours:.1f}h {direction} target)."
            )
            
            if distance_hours > validity_hours / 2:
                logger.warning(
                    f"Calibration '{chosen_set}' is {distance_hours:.1f}h from target "
                    f"(recommended max: {validity_hours / 2:.1f}h). "
                    f"Data quality may be degraded."
                )
            
            out = conn.execute(
                "SELECT path FROM caltables WHERE set_name = ? AND status='active' ORDER BY order_index ASC",
                (chosen_set,),
            ).fetchall()
            return [r[0] for r in out]

    if not all_matching_sets:
        return []

    # If multiple sets match, check compatibility and warn
    if len(all_matching_sets) > 1:
        set_metadata = {}
        for set_name_row, _ in all_matching_sets:
            rows = conn.execute(
                """
                SELECT DISTINCT cal_field, refant
                  FROM caltables
                 WHERE set_name = ? AND status = 'active'
                 LIMIT 1
                """,
                (set_name_row,),
            ).fetchone()
            if rows:
                set_metadata[set_name_row] = {"cal_field": rows[0], "refant": rows[1]}

        set_names = [s[0] for s in all_matching_sets]
        newest_set = set_names[0]
        newest_metadata = set_metadata.get(newest_set, {})

        for other_set in set_names[1:]:
            other_metadata = set_metadata.get(other_set, {})
            if (newest_metadata.get("refant") and other_metadata.get("refant") and
                newest_metadata["refant"] != other_metadata["refant"]):
                logger.warning(
                    f"Overlapping calibration sets have different reference antennas: "
                    f"'{newest_set}' uses refant={newest_metadata['refant']}, "
                    f"'{other_set}' uses refant={other_metadata['refant']}. "
                    f"Selecting newest set '{newest_set}'."
                )
            if (newest_metadata.get("cal_field") and other_metadata.get("cal_field") and
                newest_metadata["cal_field"] != other_metadata["cal_field"]):
                logger.warning(
                    f"Overlapping calibration sets have different calibration fields: "
                    f"'{newest_set}' uses field={newest_metadata['cal_field']}, "
                    f"'{other_set}' uses field={other_metadata['cal_field']}. "
                    f"Selecting newest set '{newest_set}'."
                )

    # Select winner set by created_at (most recent)
    chosen = all_matching_sets[0][0]
    out = conn.execute(
        "SELECT path FROM caltables WHERE set_name = ? AND status='active' ORDER BY order_index ASC",
        (chosen,),
    ).fetchall()
    return [r[0] for r in out]


def register_and_verify_caltables(
    registry_db: Path,
    set_name: str,
    table_prefix: Path,
    *,
    cal_field: Optional[str],
    refant: Optional[str],
    valid_start_mjd: Optional[float],
    valid_end_mjd: Optional[float],
    mid_mjd: Optional[float] = None,
    status: str = "active",
    verify_discoverable: bool = True,
) -> List[str]:
    """Register calibration tables and verify they are discoverable.

    This is a robust wrapper around register_caltable_set_from_prefix that:
    1. Registers tables (idempotent via upsert)
    2. Verifies tables are discoverable after registration
    3. Returns list of registered table paths

    Args:
        registry_db: Path to calibration registry database
        set_name: Logical calibration set name
        table_prefix: Filesystem prefix for calibration tables
        cal_field: Field used for calibration solve
        refant: Reference antenna used
        valid_start_mjd: Start of validity window (MJD)
        valid_end_mjd: End of validity window (MJD)
        mid_mjd: Optional MJD midpoint for verification
        status: Status for registered tables (default: "active")
        verify_discoverable: Whether to verify tables are discoverable

    Returns:
        List of registered calibration table paths (ordered by apply order)

    Raises:
        RuntimeError: If registration fails or tables are not discoverable
        ValueError: If no tables found with prefix
    """
    import logging
    logger = logging.getLogger(__name__)

    # Ensure registry DB exists
    ensure_db(registry_db)

    # Register tables
    try:
        registered_rows = register_caltable_set_from_prefix(
            registry_db, set_name, table_prefix,
            cal_field=cal_field, refant=refant,
            valid_start_mjd=valid_start_mjd, valid_end_mjd=valid_end_mjd,
            status=status,
        )
    except Exception as e:
        error_msg = f"Failed to register calibration tables with prefix {table_prefix}: {e}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e

    if not registered_rows:
        error_msg = f"No calibration tables found with prefix {table_prefix}."
        logger.error(error_msg)
        raise ValueError(error_msg)

    registered_paths = [row.path for row in registered_rows]
    logger.info("Registered %d calibration tables in set '%s'", len(registered_paths), set_name)

    # Verify tables are discoverable if requested
    if verify_discoverable:
        try:
            if mid_mjd is None:
                if valid_start_mjd is not None and valid_end_mjd is not None:
                    mid_mjd = (valid_start_mjd + valid_end_mjd) / 2.0
                else:
                    from astropy.time import Time
                    mid_mjd = Time.now().mjd
                    logger.warning("Using current time (%.6f) for verification", mid_mjd)

            discovered = get_active_applylist(registry_db, mid_mjd, set_name=set_name)

            if not discovered:
                error_msg = (
                    f"Registered tables not discoverable: get_active_applylist "
                    f"returned empty for set '{set_name}' at MJD {mid_mjd:.6f}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            discovered_set = set(discovered)
            registered_set = set(registered_paths)
            missing = registered_set - discovered_set
            if missing:
                error_msg = f"Some registered tables are not discoverable: {missing}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            missing_files = [p for p in discovered if not Path(p).exists()]
            if missing_files:
                error_msg = f"Discovered tables do not exist on filesystem: {missing_files}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            logger.info("Verified %d calibration tables are discoverable", len(discovered))

        except Exception as e:
            try:
                retire_caltable_set(registry_db, set_name, reason=f"Verification failed: {e}")
                logger.warning("Retired set '%s' due to verification failure", set_name)
            except Exception as rollback_error:
                logger.error(f"Failed to rollback: {rollback_error}", exc_info=True)
            
            error_msg = f"Calibration tables registered but not discoverable: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    return registered_paths
