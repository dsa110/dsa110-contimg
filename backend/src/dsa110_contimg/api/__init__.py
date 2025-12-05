# backend/src/dsa110_contimg/api/__init__.py
"""
DSA-110 Continuum Imaging Pipeline API.

This package provides the REST API for the pipeline, including:
- Image detail and download endpoints
- Measurement Set metadata endpoints
- Source catalog and lightcurve endpoints
- Job provenance and logging endpoints
- Standardized error handling via exceptions module
- Database connection pooling (sync and async)
"""

from .app import app, create_app
from .database import (
    DatabasePool,
    PoolConfig,
    SyncDatabasePool,
    async_transaction,
    async_transactional_connection,
    close_db_pool,
    close_sync_db_pool,
    get_db_pool,
    get_sync_db_pool,
    transaction,
    transactional_connection,
)
from .exceptions import (
    DatabaseConnectionError,
    DSA110APIError,
    FileNotAccessibleError,
    ProcessingError,
    RecordNotFoundError,
    ValidationError,
)

__all__ = [
    # App
    "app",
    "create_app",
    # Database pools
    "DatabasePool",
    "SyncDatabasePool",
    "PoolConfig",
    "get_db_pool",
    "get_sync_db_pool",
    "close_db_pool",
    "close_sync_db_pool",
    # Transaction managers
    "transaction",
    "async_transaction",
    "transactional_connection",
    "async_transactional_connection",
    # Exception classes
    "DSA110APIError",
    "RecordNotFoundError",
    "ValidationError",
    "DatabaseConnectionError",
    "FileNotAccessibleError",
    "ProcessingError",
]
