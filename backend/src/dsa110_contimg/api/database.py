"""
Database configuration and connection management.

Provides async database connections with connection pooling.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional, AsyncIterator
import aiosqlite


@dataclass
class PoolConfig:
    """Configuration for the database connection pool.
    
    Note: This is specifically for the async connection pool. For the
    comprehensive database configuration, see config.DatabaseConfig.
    """
    
    products_db_path: str = "/data/dsa110-contimg/state/products.sqlite3"
    cal_registry_db_path: str = "/data/dsa110-contimg/state/cal_registry.sqlite3"
    timeout: float = 30.0
    
    @classmethod
    def from_env(cls) -> "PoolConfig":
        """Create config from environment variables."""
        return cls(
            products_db_path=os.getenv(
                "DSA110_PRODUCTS_DB_PATH",
                "/data/dsa110-contimg/state/products.sqlite3"
            ),
            cal_registry_db_path=os.getenv(
                "DSA110_CAL_REGISTRY_DB_PATH",
                "/data/dsa110-contimg/state/cal_registry.sqlite3"
            ),
            timeout=float(os.getenv("DSA110_DB_TIMEOUT", "30.0")),
        )


class DatabasePool:
    """
    Async database connection pool.
    
    Provides connection pooling for SQLite databases with proper
    lifecycle management.
    """
    
    def __init__(self, config: Optional[PoolConfig] = None):
        self.config = config or PoolConfig.from_env()
        self._products_conn: Optional[aiosqlite.Connection] = None
        self._cal_conn: Optional[aiosqlite.Connection] = None
    
    async def _get_connection(
        self,
        db_path: str,
        existing_conn: Optional[aiosqlite.Connection]
    ) -> aiosqlite.Connection:
        """Get or create a connection to the specified database."""
        if existing_conn is not None:
            try:
                # Test if connection is still valid
                await existing_conn.execute("SELECT 1")
                return existing_conn
            except Exception:
                # Connection is dead, create new one
                try:
                    await existing_conn.close()
                except Exception:
                    pass
        
        conn = await aiosqlite.connect(
            db_path,
            timeout=self.config.timeout
        )
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        return conn
    
    @asynccontextmanager
    async def products_db(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get a connection to the products database."""
        self._products_conn = await self._get_connection(
            self.config.products_db_path,
            self._products_conn
        )
        yield self._products_conn
    
    @asynccontextmanager
    async def cal_registry_db(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get a connection to the calibration registry database."""
        self._cal_conn = await self._get_connection(
            self.config.cal_registry_db_path,
            self._cal_conn
        )
        yield self._cal_conn
    
    async def close(self):
        """Close all connections."""
        if self._products_conn:
            await self._products_conn.close()
            self._products_conn = None
        if self._cal_conn:
            await self._cal_conn.close()
            self._cal_conn = None


# Global database pool instance
_db_pool: Optional[DatabasePool] = None


def get_db_pool() -> DatabasePool:
    """Get the global database pool instance."""
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool()
    return _db_pool


async def close_db_pool():
    """Close the global database pool."""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
