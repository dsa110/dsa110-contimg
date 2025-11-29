# backend/src/dsa110_contimg/database/__init__.py

"""
DSA-110 Continuum Imaging Pipeline Database Module.

This module provides SQLAlchemy ORM models and session management for all
SQLite databases used by the pipeline.

Databases:
    - products.sqlite3: Product registry (MS, images, photometry, transients)
    - cal_registry.sqlite3: Calibration table registry
    - hdf5.sqlite3: HDF5 file index
    - ingest.sqlite3: Streaming queue management
    - data_registry.sqlite3: Data staging and publishing

Usage:
    # Query images using ORM
    from dsa110_contimg.database import get_session, Image, MSIndex
    
    with get_session("products") as session:
        images = session.query(Image).filter_by(type="dirty").all()
        for img in images:
            print(f"{img.path}: {img.noise_jy} Jy")
    
    # Add new records
    with get_session("products") as session:
        new_image = Image(
            path="/stage/dsa110-contimg/images/test.fits",
            ms_path="/stage/dsa110-contimg/ms/test.ms",
            created_at=time.time(),
            type="dirty",
        )
        session.add(new_image)
        # Commits automatically on exit
    
    # Multi-threaded access (streaming converter)
    from dsa110_contimg.database import get_scoped_session
    
    Session = get_scoped_session("products")
    
    def worker():
        session = Session()
        try:
            # do work
            session.commit()
        finally:
            Session.remove()

Configuration:
    Database paths can be overridden via environment variables:
    - PIPELINE_PRODUCTS_DB
    - PIPELINE_CAL_REGISTRY_DB
    - PIPELINE_HDF5_DB
    - PIPELINE_INGEST_DB
    - PIPELINE_DATA_REGISTRY_DB

See Also:
    - dsa110_contimg.database.models: ORM model definitions
    - dsa110_contimg.database.session: Session and engine management
    - dsa110_contimg.database.repositories: Repository pattern wrappers
"""

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
    # Session management
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