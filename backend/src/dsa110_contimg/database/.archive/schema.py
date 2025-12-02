"""
Shared database schema definitions for DSA-110 Continuum Imaging Pipeline.

This module provides canonical schema definitions used by:
- Production database migrations (Alembic)
- Test fixtures (pytest)
- Schema validation utilities

By centralizing schema definitions, we ensure consistency between production
and test environments.

Usage:
    from dsa110_contimg.database.schema import (
        PRODUCTS_SCHEMA_SQL,
        CAL_REGISTRY_SCHEMA_SQL,
        create_products_tables,
        create_cal_registry_tables,
    )
"""

from typing import List, Dict, Any
import sqlite3

# =============================================================================
# PRODUCTS DATABASE SCHEMA
# =============================================================================

PRODUCTS_TABLES: Dict[str, str] = {
    "images": """
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            ms_path TEXT NOT NULL,
            created_at REAL NOT NULL,
            type TEXT NOT NULL DEFAULT 'continuum',
            beam_major_arcsec REAL,
            beam_minor_arcsec REAL,
            beam_pa_deg REAL,
            noise_jy REAL,
            dynamic_range REAL,
            pbcor INTEGER DEFAULT 0,
            format TEXT DEFAULT 'fits',
            field_name TEXT,
            center_ra_deg REAL,
            center_dec_deg REAL,
            imsize_x INTEGER,
            imsize_y INTEGER,
            cellsize_arcsec REAL,
            freq_ghz REAL,
            bandwidth_mhz REAL,
            integration_sec REAL
        )
    """,
    
    "ms_index": """
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
            ra_deg REAL,
            dec_deg REAL,
            field_name TEXT,
            pointing_ra_deg REAL,
            pointing_dec_deg REAL
        )
    """,
    
    "photometry": """
        CREATE TABLE IF NOT EXISTS photometry (
            id INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL,
            image_path TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            mjd REAL,
            flux_jy REAL,
            flux_err_jy REAL,
            peak_jyb REAL,
            peak_err_jyb REAL,
            snr REAL,
            local_rms REAL
        )
    """,
    
    "sources": """
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            name TEXT,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            catalog_match TEXT,
            source_type TEXT,
            first_detected_mjd REAL,
            last_detected_mjd REAL,
            detection_count INTEGER DEFAULT 0
        )
    """,
    
    "batch_jobs": """
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            total_items INTEGER NOT NULL DEFAULT 0,
            completed_items INTEGER DEFAULT 0,
            failed_items INTEGER DEFAULT 0,
            params TEXT
        )
    """,
    
    "batch_job_items": """
        CREATE TABLE IF NOT EXISTS batch_job_items (
            id INTEGER PRIMARY KEY,
            batch_id INTEGER NOT NULL,
            ms_path TEXT NOT NULL,
            job_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            error TEXT,
            started_at REAL,
            completed_at REAL,
            data_id TEXT,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
    """,
    
    "variability_metrics": """
        CREATE TABLE IF NOT EXISTS variability_metrics (
            id INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL UNIQUE,
            chi_squared REAL,
            eta REAL,
            v_index REAL,
            modulation_index REAL,
            is_variable INTEGER DEFAULT 0,
            updated_at REAL,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        )
    """,
    
    "ese_events": """
        CREATE TABLE IF NOT EXISTS ese_events (
            id INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL,
            start_mjd REAL,
            end_mjd REAL,
            min_flux_jy REAL,
            duration_days REAL,
            significance REAL,
            status TEXT DEFAULT 'candidate',
            notes TEXT,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        )
    """,
}

PRODUCTS_INDEXES: List[str] = [
    "CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path)",
    "CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_images_type ON images(type)",
    "CREATE INDEX IF NOT EXISTS idx_ms_index_stage ON ms_index(stage)",
    "CREATE INDEX IF NOT EXISTS idx_ms_index_mid_mjd ON ms_index(mid_mjd)",
    "CREATE INDEX IF NOT EXISTS idx_ms_index_status ON ms_index(status)",
    "CREATE INDEX IF NOT EXISTS idx_photometry_source_id ON photometry(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_photometry_mjd ON photometry(mjd)",
    "CREATE INDEX IF NOT EXISTS idx_photometry_image_path ON photometry(image_path)",
    "CREATE INDEX IF NOT EXISTS idx_sources_coords ON sources(ra_deg, dec_deg)",
    "CREATE INDEX IF NOT EXISTS idx_batch_job_items_batch_id ON batch_job_items(batch_id)",
    "CREATE INDEX IF NOT EXISTS idx_batch_job_items_status ON batch_job_items(status)",
    "CREATE INDEX IF NOT EXISTS idx_variability_source ON variability_metrics(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_ese_source ON ese_events(source_id)",
]


# =============================================================================
# CALIBRATION REGISTRY SCHEMA
# =============================================================================

CAL_REGISTRY_TABLES: Dict[str, str] = {
    "caltables": """
        CREATE TABLE IF NOT EXISTS caltables (
            path TEXT PRIMARY KEY,
            table_type TEXT NOT NULL,
            set_name TEXT,
            cal_field TEXT,
            refant TEXT,
            created_at REAL,
            source_ms_path TEXT,
            status TEXT DEFAULT 'active',
            notes TEXT,
            order_index INTEGER DEFAULT 0
        )
    """,
}

CAL_REGISTRY_INDEXES: List[str] = [
    "CREATE INDEX IF NOT EXISTS idx_caltables_type ON caltables(table_type)",
    "CREATE INDEX IF NOT EXISTS idx_caltables_set ON caltables(set_name)",
    "CREATE INDEX IF NOT EXISTS idx_caltables_source_ms ON caltables(source_ms_path)",
]


# =============================================================================
# SCHEMA CREATION FUNCTIONS
# =============================================================================

def create_products_tables(conn: sqlite3.Connection) -> None:
    """
    Create all products database tables and indexes.
    
    Args:
        conn: SQLite connection to products database
    """
    cursor = conn.cursor()
    
    # Create tables
    for table_name, create_sql in PRODUCTS_TABLES.items():
        cursor.execute(create_sql)
    
    # Create indexes
    for index_sql in PRODUCTS_INDEXES:
        cursor.execute(index_sql)
    
    conn.commit()


def create_cal_registry_tables(conn: sqlite3.Connection) -> None:
    """
    Create all calibration registry tables and indexes.
    
    Args:
        conn: SQLite connection to cal registry database
    """
    cursor = conn.cursor()
    
    # Create tables
    for table_name, create_sql in CAL_REGISTRY_TABLES.items():
        cursor.execute(create_sql)
    
    # Create indexes
    for index_sql in CAL_REGISTRY_INDEXES:
        cursor.execute(index_sql)
    
    conn.commit()


def get_products_schema_sql() -> str:
    """Get complete products schema as a single SQL string."""
    statements = list(PRODUCTS_TABLES.values()) + PRODUCTS_INDEXES
    return ";\n".join(statements) + ";"


def get_cal_registry_schema_sql() -> str:
    """Get complete cal registry schema as a single SQL string."""
    statements = list(CAL_REGISTRY_TABLES.values()) + CAL_REGISTRY_INDEXES
    return ";\n".join(statements) + ";"


def validate_products_schema(conn: sqlite3.Connection) -> List[str]:
    """
    Validate that all required products tables exist.
    
    Args:
        conn: SQLite connection to validate
        
    Returns:
        List of missing table names (empty if all present)
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {row[0] for row in cursor.fetchall()}
    
    required = set(PRODUCTS_TABLES.keys())
    missing = required - existing
    
    return sorted(missing)


def validate_cal_registry_schema(conn: sqlite3.Connection) -> List[str]:
    """
    Validate that all required cal registry tables exist.
    
    Args:
        conn: SQLite connection to validate
        
    Returns:
        List of missing table names (empty if all present)
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {row[0] for row in cursor.fetchall()}
    
    required = set(CAL_REGISTRY_TABLES.keys())
    missing = required - existing
    
    return sorted(missing)
