"""
Database abstraction layer for multi-backend support.

This package provides a unified async interface for database operations,
supporting both SQLite and PostgreSQL backends.

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
        backend=DatabaseBackend.POSTGRESQL,
        pg_host="localhost",
        pg_database="dsa110",
        pg_user="user",
        pg_password="password",
    )
    adapter = create_adapter(config)

Environment Variables (prefix: DSA110_DB):
    DSA110_DB_BACKEND: "sqlite" or "postgresql"
    DSA110_DB_SQLITE_PATH: Path to SQLite database
    DSA110_DB_PG_HOST: PostgreSQL host
    DSA110_DB_PG_PORT: PostgreSQL port
    DSA110_DB_PG_DATABASE: PostgreSQL database name
    DSA110_DB_PG_USER: PostgreSQL username
    DSA110_DB_PG_PASSWORD: PostgreSQL password
    DSA110_DB_PG_POOL_MIN: Min pool connections
    DSA110_DB_PG_POOL_MAX: Max pool connections
    DSA110_DB_PG_SSL: Use SSL (true/false)
"""

from .backend import (
    create_adapter,
    DatabaseAdapter,
    DatabaseBackend,
    DatabaseConfig,
)
from .query_builder import (
    QueryBuilder,
    convert_sqlite_to_postgresql,
    convert_postgresql_to_sqlite,
)
from .adapters.sync_pool import (
    SyncConnectionPool,
    SyncPoolConfig,
    get_sync_pool,
    close_all_sync_pools,
)

__all__ = [
    "create_adapter",
    "DatabaseAdapter",
    "DatabaseBackend",
    "DatabaseConfig",
    "QueryBuilder",
    "convert_sqlite_to_postgresql",
    "convert_postgresql_to_sqlite",
    # Sync pool
    "SyncConnectionPool",
    "SyncPoolConfig",
    "get_sync_pool",
    "close_all_sync_pools",
]
