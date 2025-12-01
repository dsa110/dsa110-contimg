"""
Database adapters for multi-backend support.

This package provides database adapters for:
- SQLite (via aiosqlite)
- PostgreSQL (via asyncpg)
"""

from .sqlite_adapter import SQLiteAdapter

# PostgreSQL adapter is optional - only import if available
try:
    from .postgresql_adapter import PostgreSQLAdapter
    __all__ = ["SQLiteAdapter", "PostgreSQLAdapter"]
except ImportError:
    __all__ = ["SQLiteAdapter"]
