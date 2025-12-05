"""
Database abstraction layer for SQLite.

This package provides a unified async interface for database operations
using SQLite.

Note: PostgreSQL support was removed in the complexity reduction refactor.
The pipeline exclusively uses SQLite for data storage. ABSURD workflow
manager uses its own PostgreSQL database separately.

Basic Usage:
    from dsa110_contimg.api.db_adapters import create_adapter, DatabaseConfig

    # Create adapter from environment variables
    adapter = create_adapter()
    await adapter.connect()

    # Execute queries
    rows = await adapter.fetch_all("SELECT * FROM products")

    # Clean up
    await adapter.disconnect()

With explicit configuration:
    config = DatabaseConfig(
        sqlite_path="/path/to/database.db",
    )
    adapter = create_adapter(config)

Environment Variables (prefix: DSA110_DB):
    DSA110_DB_SQLITE_PATH: Path to SQLite database
    DSA110_DB_SQLITE_TIMEOUT: Connection timeout (default: 30.0)
"""

from .backend import (
    DatabaseAdapter,
    DatabaseConfig,
    create_adapter,
)
from .query_builder import QueryBuilder

__all__ = [
    "create_adapter",
    "DatabaseAdapter",
    "DatabaseConfig",
    "QueryBuilder",
]
