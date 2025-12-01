"""
Database adapters for SQLite.

This package provides the SQLite adapter (via aiosqlite).
PostgreSQL support was removed in the complexity reduction refactor.
"""

from .sqlite_adapter import SQLiteAdapter

__all__ = ["SQLiteAdapter"]
