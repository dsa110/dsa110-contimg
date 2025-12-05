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

# =============================================================================
# Legacy ORM Compatibility (DEPRECATED)
# =============================================================================
# Import legacy ORM-based session management for backwards compatibility
# These are deprecated and will be removed in a future version
import warnings

# =============================================================================
# State Machine for Pipeline Processing
# =============================================================================
from .state_machine import (
    # State enum and exceptions
    MSState,
    # State machine class
    MSStateMachine,
    StateNotFoundError,
    # Data classes
    StateRecord,
    StateTransitionError,
    TransitionResult,
    close_state_machine,
    # Singleton access
    get_state_machine,
    # Context manager for state-tracked processing
    state_transition_context,
)
from .unified import (
    DEFAULT_CALTABLE_ORDER,
    DEFAULT_PIPELINE_DB,
    # Calibration registry (migrated from registry.py)
    CalTableRow,
    # Database class
    Database,
    append_job_log,
    close_db,
    # Jobs helpers
    create_job,
    ensure_db,
    ensure_pipeline_db,
    get_active_applylist,
    # Calibrator helpers
    get_bandpass_calibrators,
    get_calibrators_db_path,  # Alias for get_pipeline_db_path
    get_db,
    get_job,
    # Path helpers
    get_pipeline_db_path,
    images_insert,
    # Initialization and singleton
    init_unified_db,
    list_caltable_sets,
    list_jobs,
    # Pointing helpers
    log_pointing,
    # MS/Products helpers
    ms_index_upsert,
    photometry_insert,
    register_and_verify_caltables,
    register_bandpass_calibrator,
    register_caltable_set,
    register_caltable_set_from_prefix,
    retire_caltable_set,
    update_job_status,
)

try:
    from .models import (
        CAL_REGISTRY_MODELS,
        DATA_REGISTRY_MODELS,
        HDF5_MODELS,
        INGEST_MODELS,
        PRODUCTS_MODELS,
        BatchJob,
        BatchJobItem,
        CalibratorTransit,
        CalRegistryBase,
        Caltable,
        DataRegistry,
        DataRegistryBase,
        DataRelationship,
        DataTag,
        DeadLetterQueue,
        HDF5Base,
        HDF5FileIndex,
        HDF5FileIndexProducts,
        HDF5StorageLocation,
        Image,
        IngestBase,
        MonitoringSource,
        MSIndex,
        Photometry,
        PointingHistory,
        PointingHistoryIngest,
        ProductsBase,
        StorageLocation,
        TransientCandidate,
    )
    from .session import (
        DATABASE_PATHS,
        DEFAULT_DB_PATHS,
        DatabaseName,
        get_db_path,
        get_db_url,
        get_engine,
        get_raw_connection,
        get_readonly_session,
        get_scoped_session,
        get_session,
        get_session_factory,
        init_database,
        reset_engines,
    )

    _LEGACY_ORM_AVAILABLE = True
except ImportError:
    _LEGACY_ORM_AVAILABLE = False

# Legacy HDF5 functions (keep for backward compatibility)
from .hdf5_index import (
    get_hdf5_metadata,
    index_hdf5_files,
    query_hdf5_file,
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
    # Legacy HDF5 functions
    "index_hdf5_files",
    "query_hdf5_file",
    "get_hdf5_metadata",
]

# Add legacy ORM exports to __all__ if available
if _LEGACY_ORM_AVAILABLE:
    __all__.extend(
        [
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
        ]
    )
