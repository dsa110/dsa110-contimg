# backend/src/dsa110_contimg/database/__init__.py

"""
DSA-110 Continuum Imaging Pipeline Database Module.

This module provides the simplified Database class (recommended)
and helper functions for common database operations.

Recommended Usage (Simplified):
    from dsa110_contimg.database import Database
    
    db = Database()  # Uses PIPELINE_DB env var or default path
    
    # Query with dict results
    images = db.query("SELECT * FROM images WHERE type = ?", ("dirty",))
    for img in images:
        print(f"{img['path']}: {img['noise_jy']} Jy")
    
    # Insert/update
    db.execute(
        "INSERT INTO images (path, ms_path, type, created_at) VALUES (?, ?, ?, ?)",
        ("/path/to/img.fits", "/path/to/ms", "dirty", time.time())
    )
    
    # Transaction context
    with db.transaction() as conn:
        conn.execute("UPDATE images SET type = ? WHERE id = ?", ("clean", 42))

Helper Functions:
    # Jobs
    from dsa110_contimg.database import create_job, update_job_status, get_job, list_jobs
    
    # MS Index
    from dsa110_contimg.database import ms_index_upsert, images_insert, photometry_insert
    
    # Calibrators
    from dsa110_contimg.database import get_bandpass_calibrators, register_bandpass_calibrator

Configuration:
    - PIPELINE_DB: Path to unified pipeline.sqlite3 (default: /data/dsa110-contimg/state/db/pipeline.sqlite3)
    - DB_CONNECTION_TIMEOUT: Connection timeout in seconds (default: 30.0)

See Also:
    - dsa110_contimg.database.unified: Simplified Database class and helpers
"""

# =============================================================================
# Simplified Database Layer (RECOMMENDED)
# =============================================================================

from .unified import (
    # Database class
    Database,
    DEFAULT_PIPELINE_DB,
    # Path helpers
    get_pipeline_db_path,
    get_calibrators_db_path,  # Alias for get_pipeline_db_path
    # Initialization and singleton
    init_unified_db,
    get_db,
    close_db,
    ensure_pipeline_db,
    # Jobs helpers
    create_job,
    update_job_status,
    append_job_log,
    get_job,
    list_jobs,
    # MS/Products helpers
    ms_index_upsert,
    images_insert,
    photometry_insert,
    # Pointing helpers
    log_pointing,
    # Calibrator helpers
    get_bandpass_calibrators,
    register_bandpass_calibrator,
    # Calibration registry (migrated from registry.py)
    CalTableRow,
    DEFAULT_CALTABLE_ORDER,
    ensure_db,
    register_caltable_set,
    register_caltable_set_from_prefix,
    retire_caltable_set,
    list_caltable_sets,
    get_active_applylist,
    register_and_verify_caltables,
)

# =============================================================================
# State Machine for Pipeline Processing
# =============================================================================

from .state_machine import (
    # State enum and exceptions
    MSState,
    StateTransitionError,
    StateNotFoundError,
    # Data classes
    StateRecord,
    TransitionResult,
    # State machine class
    MSStateMachine,
    # Context manager for state-tracked processing
    state_transition_context,
    # Singleton access
    get_state_machine,
    close_state_machine,
)

# =============================================================================
# Legacy ORM Compatibility (DEPRECATED)
# =============================================================================

# Import legacy ORM-based session management for backwards compatibility
# These are deprecated and will be removed in a future version
import warnings

try:
    from .session import (
        get_session,
        get_readonly_session,
        get_scoped_session,
        get_session_factory,
        get_engine,
        get_db_path,
        get_db_url,
        get_raw_connection,
        init_database,
        reset_engines,
        DatabaseName,
        DEFAULT_DB_PATHS,
        DATABASE_PATHS,
    )
    
    from .models import (
        ProductsBase,
        CalRegistryBase,
        HDF5Base,
        IngestBase,
        DataRegistryBase,
        MSIndex,
        Image,
        Photometry,
        HDF5FileIndexProducts,
        StorageLocation,
        BatchJob,
        BatchJobItem,
        TransientCandidate,
        CalibratorTransit,
        DeadLetterQueue,
        MonitoringSource,
        Caltable,
        HDF5FileIndex,
        HDF5StorageLocation,
        PointingHistory,
        PointingHistoryIngest,
        DataRegistry,
        DataRelationship,
        DataTag,
        PRODUCTS_MODELS,
        CAL_REGISTRY_MODELS,
        HDF5_MODELS,
        INGEST_MODELS,
        DATA_REGISTRY_MODELS,
    )
    _LEGACY_ORM_AVAILABLE = True
except ImportError:
    _LEGACY_ORM_AVAILABLE = False

# =============================================================================
# Legacy Compatibility Wrappers
# =============================================================================

import os
import sqlite3
from pathlib import Path
from typing import Optional, Union


def ensure_products_db(path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """
    Legacy wrapper: ensure products database exists and return connection.
    
    For new code, use `ensure_pipeline_db()` which uses PIPELINE_DB env var.
    
    Args:
        path: Optional database path. If None, uses PIPELINE_DB or default.
        
    Returns:
        sqlite3.Connection to the pipeline database
    """
    if path is not None:
        # Legacy behavior: ignore the path and use the unified database
        # This maintains backwards compatibility while consolidating DBs
        import warnings
        warnings.warn(
            "ensure_products_db(path) is deprecated. "
            "Use ensure_pipeline_db() which uses PIPELINE_DB env var.",
            DeprecationWarning,
            stacklevel=2
        )
    return ensure_pipeline_db()


def ensure_ingest_db(path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """
    Legacy wrapper: ensure ingest database exists and return connection.
    
    For new code, use `ensure_pipeline_db()` which uses PIPELINE_DB env var.
    
    Args:
        path: Optional database path. If None, uses PIPELINE_DB or default.
        
    Returns:
        sqlite3.Connection to the pipeline database
    """
    if path is not None:
        import warnings
        warnings.warn(
            "ensure_ingest_db(path) is deprecated. "
            "Use ensure_pipeline_db() which uses PIPELINE_DB env var.",
            DeprecationWarning,
            stacklevel=2
        )
    return ensure_pipeline_db()


# Legacy HDF5 functions (keep for backward compatibility)
from .hdf5_index import (
    index_hdf5_files,
    query_hdf5_file,
    get_hdf5_metadata,
)

__all__ = [
    # Simplified Database Layer (RECOMMENDED)
    "Database",
    "DEFAULT_PIPELINE_DB",
    "init_unified_db",
    "get_db",
    "close_db",
    "ensure_pipeline_db",
    # Jobs helpers
    "create_job",
    "update_job_status",
    "append_job_log",
    "get_job",
    "list_jobs",
    # MS/Products helpers
    "ms_index_upsert",
    "images_insert",
    "photometry_insert",
    # Pointing helpers
    "log_pointing",
    # Calibrator helpers
    "get_bandpass_calibrators",
    "register_bandpass_calibrator",
    # Legacy aliases
    "ensure_products_db",
    "ensure_ingest_db",
    # Legacy HDF5 functions
    "index_hdf5_files",
    "query_hdf5_file",
    "get_hdf5_metadata",
]

# Add legacy ORM exports to __all__ if available
if _LEGACY_ORM_AVAILABLE:
    __all__.extend([
        # Legacy Session management
        "get_session",
        "get_readonly_session",
        "get_scoped_session",
        "get_session_factory",
        "get_engine",
        "get_db_path",
        "get_db_url",
        "get_raw_connection",
        "init_database",
        "reset_engines",
        "DatabaseName",
        "DEFAULT_DB_PATHS",
        "DATABASE_PATHS",
        # ORM Base classes
        "ProductsBase",
        "CalRegistryBase",
        "HDF5Base",
        "IngestBase",
        "DataRegistryBase",
        # ORM Models
        "MSIndex",
        "Image",
        "Photometry",
        "HDF5FileIndexProducts",
        "StorageLocation",
        "BatchJob",
        "BatchJobItem",
        "TransientCandidate",
        "CalibratorTransit",
        "DeadLetterQueue",
        "MonitoringSource",
        "Caltable",
        "HDF5FileIndex",
        "HDF5StorageLocation",
        "PointingHistory",
        "PointingHistoryIngest",
        "DataRegistry",
        "DataRelationship",
        "DataTag",
        # Model collections
        "PRODUCTS_MODELS",
        "CAL_REGISTRY_MODELS",
        "HDF5_MODELS",
        "INGEST_MODELS",
        "DATA_REGISTRY_MODELS",
    ])
