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
# Unified Schema Definition
# =============================================================================

UNIFIED_SCHEMA = """
-- =============================================================================
-- DSA-110 Continuum Imaging Pipeline: Unified Database Schema
-- =============================================================================
-- 
-- All pipeline data is stored in a single unified database (pipeline.sqlite3)
-- for simpler operations, atomic transactions, and cross-domain queries.
--
-- Table Domains:
--   - Products: ms_index, images, photometry, transients
--   - Calibration: calibration_tables, calibrator_transits
--   - HDF5: hdf5_files, pointing_history
--   - Queue: processing_queue, performance_metrics
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Products Domain
-- ---------------------------------------------------------------------------

-- Measurement Set index with processing stage tracking
CREATE TABLE IF NOT EXISTS ms_index (
    path TEXT PRIMARY KEY,
    start_mjd REAL,
    end_mjd REAL,
    mid_mjd REAL,
    processed_at REAL,
    status TEXT,
    stage TEXT,
    stage_updated_at REAL,
    cal_applied INTEGER DEFAULT 0,
    imagename TEXT,
    field_name TEXT,
    pointing_ra_deg REAL,
    pointing_dec_deg REAL,
    ra_deg REAL,
    dec_deg REAL,
    group_id TEXT,
    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_ms_index_mid_mjd ON ms_index(mid_mjd);
CREATE INDEX IF NOT EXISTS idx_ms_index_status ON ms_index(status);
CREATE INDEX IF NOT EXISTS idx_ms_index_stage ON ms_index(stage);
CREATE INDEX IF NOT EXISTS idx_ms_index_group_id ON ms_index(group_id);

-- Image products linked to MS
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    ms_path TEXT NOT NULL,
    created_at REAL NOT NULL,
    type TEXT NOT NULL,
    format TEXT DEFAULT 'fits',
    beam_major_arcsec REAL,
    beam_minor_arcsec REAL,
    beam_pa_deg REAL,
    noise_jy REAL,
    dynamic_range REAL,
    pbcor INTEGER DEFAULT 0,
    field_name TEXT,
    center_ra_deg REAL,
    center_dec_deg REAL,
    imsize_x INTEGER,
    imsize_y INTEGER,
    cellsize_arcsec REAL,
    freq_ghz REAL,
    bandwidth_mhz REAL,
    integration_sec REAL,
    FOREIGN KEY (ms_path) REFERENCES ms_index(path)
);

CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path);
CREATE INDEX IF NOT EXISTS idx_images_type ON images(type);
CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at);

-- Photometric measurements
CREATE TABLE IF NOT EXISTS photometry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL,
    source_id TEXT NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_jy REAL NOT NULL,
    flux_err_jy REAL,
    peak_flux_jy REAL,
    rms_jy REAL,
    snr REAL,
    major_arcsec REAL,
    minor_arcsec REAL,
    pa_deg REAL,
    measured_at REAL NOT NULL,
    quality_flag TEXT,
    FOREIGN KEY (image_path) REFERENCES images(path)
);

CREATE INDEX IF NOT EXISTS idx_photometry_image ON photometry(image_path);
CREATE INDEX IF NOT EXISTS idx_photometry_source ON photometry(source_id);
CREATE INDEX IF NOT EXISTS idx_photometry_coords ON photometry(ra_deg, dec_deg);

-- ---------------------------------------------------------------------------
-- Calibration Domain
-- ---------------------------------------------------------------------------

-- Calibration table registry
CREATE TABLE IF NOT EXISTS calibration_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    set_name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    table_type TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    cal_field TEXT,
    refant TEXT,
    created_at REAL NOT NULL,
    valid_start_mjd REAL,
    valid_end_mjd REAL,
    status TEXT NOT NULL DEFAULT 'active',
    source_ms_path TEXT,
    solver_command TEXT,
    solver_version TEXT,
    solver_params TEXT,
    quality_metrics TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_caltables_set ON calibration_tables(set_name);
CREATE INDEX IF NOT EXISTS idx_caltables_valid ON calibration_tables(valid_start_mjd, valid_end_mjd);
CREATE INDEX IF NOT EXISTS idx_caltables_status ON calibration_tables(status);

-- Record of calibration applications
CREATE TABLE IF NOT EXISTS calibration_applied (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ms_path TEXT NOT NULL,
    caltable_path TEXT NOT NULL,
    applied_at REAL NOT NULL,
    quality REAL,
    success INTEGER DEFAULT 1,
    error_message TEXT,
    FOREIGN KEY (ms_path) REFERENCES ms_index(path),
    FOREIGN KEY (caltable_path) REFERENCES calibration_tables(path)
);

CREATE INDEX IF NOT EXISTS idx_cal_applied_ms ON calibration_applied(ms_path);

-- ---------------------------------------------------------------------------
-- Calibrator Catalog (from calibrators.sqlite3)
-- ---------------------------------------------------------------------------

-- Known bandpass calibrators
CREATE TABLE IF NOT EXISTS calibrator_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_jy REAL,
    flux_freq_ghz REAL,
    dec_range_min REAL,
    dec_range_max REAL,
    source_catalog TEXT,
    status TEXT DEFAULT 'active',
    registered_at REAL NOT NULL,
    registered_by TEXT,
    code_20_cm TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_calibrators_name ON calibrator_catalog(name);
CREATE INDEX IF NOT EXISTS idx_calibrators_dec ON calibrator_catalog(dec_deg);
CREATE INDEX IF NOT EXISTS idx_calibrators_status ON calibrator_catalog(status);

-- Calibrator transit calculations
CREATE TABLE IF NOT EXISTS calibrator_transits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calibrator_name TEXT NOT NULL,
    transit_mjd REAL NOT NULL,
    transit_iso TEXT NOT NULL,
    has_data INTEGER NOT NULL DEFAULT 0,
    group_id TEXT,
    group_mid_iso TEXT,
    delta_minutes REAL,
    pb_response REAL,
    dec_match INTEGER NOT NULL DEFAULT 0,
    calculated_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(calibrator_name, transit_mjd)
);

CREATE INDEX IF NOT EXISTS idx_transits_calibrator ON calibrator_transits(calibrator_name);
CREATE INDEX IF NOT EXISTS idx_transits_mjd ON calibrator_transits(transit_mjd DESC);
CREATE INDEX IF NOT EXISTS idx_transits_has_data ON calibrator_transits(has_data);

-- ---------------------------------------------------------------------------
-- HDF5 Domain
-- ---------------------------------------------------------------------------

-- Raw HDF5 file tracking
CREATE TABLE IF NOT EXISTS hdf5_files (
    path TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    group_id TEXT NOT NULL,
    subband_code TEXT NOT NULL,
    subband_num INTEGER,
    timestamp_iso TEXT,
    timestamp_mjd REAL,
    file_size_bytes INTEGER,
    modified_time REAL,
    indexed_at REAL NOT NULL,
    stored INTEGER DEFAULT 1,
    ra_deg REAL,
    dec_deg REAL,
    obs_date TEXT,
    obs_time TEXT
);

CREATE INDEX IF NOT EXISTS idx_hdf5_group ON hdf5_files(group_id);
CREATE INDEX IF NOT EXISTS idx_hdf5_timestamp ON hdf5_files(timestamp_mjd);
CREATE INDEX IF NOT EXISTS idx_hdf5_stored ON hdf5_files(stored);
CREATE INDEX IF NOT EXISTS idx_hdf5_coords ON hdf5_files(ra_deg, dec_deg);

-- Pointing history (from both hdf5 and ingest)
CREATE TABLE IF NOT EXISTS pointing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_mjd REAL NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    source TEXT,
    recorded_at REAL NOT NULL,
    UNIQUE(timestamp_mjd, source)
);

CREATE INDEX IF NOT EXISTS idx_pointing_time ON pointing_history(timestamp_mjd);

-- ---------------------------------------------------------------------------
-- Queue Domain
-- ---------------------------------------------------------------------------

-- Ingest/processing queue with state machine
CREATE TABLE IF NOT EXISTS processing_queue (
    group_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,  -- collecting, pending, in_progress, completed, failed
    received_at REAL NOT NULL,
    last_update REAL NOT NULL,
    expected_subbands INTEGER,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    error_message TEXT,
    checkpoint_path TEXT,
    processing_stage TEXT DEFAULT 'collecting',
    chunk_minutes REAL,
    has_calibrator INTEGER DEFAULT NULL,
    calibrators TEXT
);

CREATE INDEX IF NOT EXISTS idx_queue_state ON processing_queue(state);
CREATE INDEX IF NOT EXISTS idx_queue_received ON processing_queue(received_at);

-- Subband files for each group
CREATE TABLE IF NOT EXISTS subband_files (
    group_id TEXT NOT NULL,
    subband_idx INTEGER NOT NULL,
    path TEXT NOT NULL UNIQUE,
    PRIMARY KEY (group_id, subband_idx),
    FOREIGN KEY (group_id) REFERENCES processing_queue(group_id)
);

-- Performance metrics for processed groups
CREATE TABLE IF NOT EXISTS performance_metrics (
    group_id TEXT PRIMARY KEY,
    load_time REAL,
    phase_time REAL,
    write_time REAL,
    total_time REAL,
    writer_type TEXT,
    recorded_at REAL NOT NULL,
    FOREIGN KEY (group_id) REFERENCES processing_queue(group_id)
);

-- Dead letter queue for failed items
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_table TEXT NOT NULL,
    original_id TEXT NOT NULL,
    error_message TEXT,
    payload TEXT,
    failed_at REAL NOT NULL,
    retry_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_dlq_table ON dead_letter_queue(original_table);

-- ---------------------------------------------------------------------------
-- Storage Locations (moved from products)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS storage_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    location_type TEXT NOT NULL,  -- 'ms', 'image', 'caltable', 'hdf5'
    size_bytes INTEGER,
    created_at REAL NOT NULL,
    last_checked REAL,
    status TEXT DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_storage_type ON storage_locations(location_type);
CREATE INDEX IF NOT EXISTS idx_storage_status ON storage_locations(status);

-- ---------------------------------------------------------------------------
-- Alert History (from alerts.sqlite3)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    triggered_at REAL NOT NULL,
    resolved_at REAL,
    acknowledged_by TEXT,
    acknowledged_at REAL
);

CREATE INDEX IF NOT EXISTS idx_alerts_name ON alert_history(alert_name);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alert_history(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON alert_history(triggered_at);
"""


def init_unified_db(db_path: Optional[Union[str, Path]] = None) -> Database:
    """
    Initialize the unified database with schema.
    
    Creates the database file and all tables if they don't exist.
    
    Args:
        db_path: Path to database. Uses PIPELINE_DB env var or default.
        
    Returns:
        Database instance ready for use
    """
    db = Database(db_path)
    db.execute_script(UNIFIED_SCHEMA)
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
