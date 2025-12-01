# backend/src/dsa110_contimg/database/__init__.py

"""
DSA-110 Continuum Imaging Pipeline Database Module.

This module provides both the simplified Database class (recommended)
and the legacy SQLAlchemy ORM models for backwards compatibility.

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

Legacy Usage (ORM - for existing code):
    from dsa110_contimg.database import get_session, Image, MSIndex
    
    with get_session("products") as session:
        images = session.query(Image).filter_by(type="dirty").all()

Configuration:
    - PIPELINE_DB: Path to unified pipeline.sqlite3 (default: /data/dsa110-contimg/state/db/pipeline.sqlite3)
    - DB_CONNECTION_TIMEOUT: Connection timeout in seconds (default: 30.0)

See Also:
    - dsa110_contimg.database.unified: Simplified Database class
    - dsa110_contimg.database.models: ORM model definitions (legacy)
"""

# =============================================================================
# Simplified Database Layer (RECOMMENDED)
# =============================================================================

from .unified import Database, DEFAULT_PIPELINE_DB

# =============================================================================
# Legacy ORM-based Session Management
# =============================================================================

# Session management
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
    DATABASE_PATHS,  # Alias for Alembic migrations
)

# ORM Models - Products database
from .models import (
    # Base classes
    ProductsBase,
    CalRegistryBase,
    HDF5Base,
    IngestBase,
    DataRegistryBase,
    # Products models
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
    # Cal registry models
    Caltable,
    # HDF5 models
    HDF5FileIndex,
    HDF5StorageLocation,
    PointingHistory,
    # Ingest models
    PointingHistoryIngest,
    # Data registry models
    DataRegistry,
    DataRelationship,
    DataTag,
    # Model collections
    PRODUCTS_MODELS,
    CAL_REGISTRY_MODELS,
    HDF5_MODELS,
    INGEST_MODELS,
    DATA_REGISTRY_MODELS,
)

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
    # Base classes
    "ProductsBase",
    "CalRegistryBase",
    "HDF5Base",
    "IngestBase",
    "DataRegistryBase",
    # Products models
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
    # Cal registry models
    "Caltable",
    # HDF5 models
    "HDF5FileIndex",
    "HDF5StorageLocation",
    "PointingHistory",
    # Ingest models
    "PointingHistoryIngest",
    # Data registry models
    "DataRegistry",
    "DataRelationship",
    "DataTag",
    # Model collections
    "PRODUCTS_MODELS",
    "CAL_REGISTRY_MODELS",
    "HDF5_MODELS",
    "INGEST_MODELS",
    "DATA_REGISTRY_MODELS",
    # Legacy functions
    "index_hdf5_files",
    "query_hdf5_file",
    "get_hdf5_metadata",
]