"""
Database configuration and connection management.

Provides async database connections with connection pooling,
and transaction context managers for safe database operations.

All database access now uses the unified pipeline.sqlite3 database.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Optional, AsyncIterator, Iterator
import aiosqlite


# Default unified database path
DEFAULT_DB_PATH = "/data/dsa110-contimg/state/db/pipeline.sqlite3"


@dataclass
class PoolConfig:
    """Configuration for the database connection pool.
    
    All paths point to the unified pipeline.sqlite3 database.
    """
    
    db_path: str = DEFAULT_DB_PATH
    timeout: float = 30.0
    
    @classmethod
    def from_env(cls) -> "PoolConfig":
        """Create config from environment variables.
        
        Uses PIPELINE_DB for the unified database path.
        """
        db_path = os.getenv("PIPELINE_DB", DEFAULT_DB_PATH)
        
        return cls(
            db_path=db_path,
            timeout=float(os.getenv("DB_CONNECTION_TIMEOUT", "30.0")),
        )


class DatabasePool:
    """
    Async database connection pool for the unified pipeline database.
    
    All database operations use the unified pipeline.sqlite3 database.
    """
    
    def __init__(self, config: Optional[PoolConfig] = None):
        self.config = config or PoolConfig.from_env()
        self._conn: Optional[aiosqlite.Connection] = None
    
    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create a connection to the unified database."""
        if self._conn is not None:
            try:
                # Test if connection is still valid
                await self._conn.execute("SELECT 1")
                return self._conn
            except (sqlite3.Error, ValueError):
                # Connection is dead, create new one
                try:
                    await self._conn.close()
                except (sqlite3.Error, ValueError):
                    pass
        
        conn = await aiosqlite.connect(
            self.config.db_path,
            timeout=self.config.timeout
        )
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        self._conn = conn
        return conn
    
    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get a connection to the unified database."""
        conn = await self._get_connection()
        yield conn
    
    async def close(self):
        """Close the connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None


class SyncDatabasePool:
    """
    Synchronous database connection pool for the unified pipeline database.
    
    All database operations use the unified pipeline.sqlite3 database.
    
    Thread-Safety: This pool is NOT thread-safe. Each thread should
    have its own pool instance, or use thread-local storage.
    """
    
    def __init__(self, config: Optional[PoolConfig] = None):
        self.config = config or PoolConfig.from_env()
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a connection to the unified database."""
        if self._conn is not None:
            try:
                # Test if connection is still valid
                self._conn.execute("SELECT 1")
                return self._conn
            except sqlite3.Error:
                # Connection is dead, create new one
                try:
                    self._conn.close()
                except sqlite3.Error:
                    pass
        
        conn = sqlite3.connect(self.config.db_path, timeout=self.config.timeout)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        self._conn = conn
        return conn
    
    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Get a connection to the unified database."""
        conn = self._get_connection()
        yield conn
    
    def close(self):
        """Close the connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Global database pool instance
_db_pool: Optional[DatabasePool] = None
_sync_db_pool: Optional[SyncDatabasePool] = None


def get_db_pool() -> DatabasePool:
    """Get the global async database pool instance."""
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool()
    return _db_pool


def get_sync_db_pool() -> SyncDatabasePool:
    """Get the global sync database pool instance.
    
    Note: This pool is not thread-safe. In multi-threaded contexts,
    consider using thread-local storage or creating per-thread pools.
    """
    global _sync_db_pool
    if _sync_db_pool is None:
        _sync_db_pool = SyncDatabasePool()
    return _sync_db_pool


async def close_db_pool():
    """Close the global async database pool."""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None


def close_sync_db_pool():
    """Close the global sync database pool."""
    global _sync_db_pool
    if _sync_db_pool:
        _sync_db_pool.close()
        _sync_db_pool = None


def close_all_db_pools():
    """Close both sync and async database pools.
    
    Note: This function does not await the async pool closure.
    Use close_db_pool() for async contexts.
    """
    close_sync_db_pool()
    # Note: For async pool, caller should use close_db_pool() in async context


# =============================================================================
# Transaction Context Managers
# =============================================================================

@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """
    Synchronous transaction context manager.
    
    Provides automatic commit on success and rollback on failure.
    Use this to wrap multi-statement database operations.
    
    Args:
        conn: Existing sqlite3 connection
        
    Yields:
        The same connection, with transaction started
        
    Example:
        conn = sqlite3.connect(db_path)
        with transaction(conn) as txn:
            txn.execute("INSERT INTO ...")
            txn.execute("UPDATE ...")
        # Auto-committed on success, rolled back on error
    """
    try:
        # Start explicit transaction (SQLite auto-starts, but be explicit)
        conn.execute("BEGIN")
        yield conn
        conn.commit()
    except (sqlite3.Error, OSError, ValueError) as e:
        # Rollback on database errors, I/O errors, or value errors
        # Re-raise to let caller handle the exception
        conn.rollback()
        raise


@asynccontextmanager
async def async_transaction(
    conn: aiosqlite.Connection
) -> AsyncIterator[aiosqlite.Connection]:
    """
    Async transaction context manager.
    
    Provides automatic commit on success and rollback on failure.
    Use this to wrap multi-statement async database operations.
    
    Args:
        conn: Existing aiosqlite connection
        
    Yields:
        The same connection, with transaction started
        
    Example:
        async with db_pool.products_db() as conn:
            async with async_transaction(conn) as txn:
                await txn.execute("INSERT INTO ...")
                await txn.execute("UPDATE ...")
        # Auto-committed on success, rolled back on error
    """
    try:
        await conn.execute("BEGIN")
        yield conn
        await conn.commit()
    except (sqlite3.Error, OSError, ValueError) as e:
        # Rollback on database errors, I/O errors, or value errors
        await conn.rollback()
        raise


@contextmanager
def transactional_connection(
    db_path: str,
    timeout: float = 30.0,
    row_factory: bool = True
) -> Iterator[sqlite3.Connection]:
    """
    Create a new connection with automatic transaction management.
    
    Use when you need a new connection with transaction semantics.
    The connection is automatically closed after the context.
    
    Args:
        db_path: Path to SQLite database
        timeout: Connection timeout in seconds
        row_factory: Whether to use sqlite3.Row for results
        
    Yields:
        sqlite3.Connection with transaction started
        
    Example:
        with transactional_connection("/path/to/db.sqlite3") as conn:
            conn.execute("INSERT INTO ...")
            conn.execute("UPDATE ...")
        # Auto-committed and closed on success
    """
    conn = sqlite3.connect(db_path, timeout=timeout)
    if row_factory:
        conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    
    try:
        conn.execute("BEGIN")
        yield conn
        conn.commit()
    except (sqlite3.Error, OSError, ValueError) as e:
        # Rollback on database errors, I/O errors, or value errors
        conn.rollback()
        raise
    finally:
        conn.close()


@asynccontextmanager
async def async_transactional_connection(
    db_path: str,
    timeout: float = 30.0
) -> AsyncIterator[aiosqlite.Connection]:
    """
    Create a new async connection with automatic transaction management.
    
    Use when you need a new async connection with transaction semantics.
    The connection is automatically closed after the context.
    
    Args:
        db_path: Path to SQLite database
        timeout: Connection timeout in seconds
        
    Yields:
        aiosqlite.Connection with transaction started
        
    Example:
        async with async_transactional_connection("/path/to/db.sqlite3") as conn:
            await conn.execute("INSERT INTO ...")
            await conn.execute("UPDATE ...")
        # Auto-committed and closed on success
    """
    conn = await aiosqlite.connect(db_path, timeout=timeout)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    
    try:
        await conn.execute("BEGIN")
        yield conn
        await conn.commit()
    except (sqlite3.Error, OSError, ValueError) as e:
        # Rollback on database errors, I/O errors, or value errors
        await conn.rollback()
        raise
    finally:
        await conn.close()
