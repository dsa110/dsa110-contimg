"""
PostgreSQL database adapter using asyncpg.

This adapter provides an async interface to PostgreSQL databases,
with connection pooling for concurrent access.

Note: This adapter requires the asyncpg package to be installed:
    pip install asyncpg
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None  # type: ignore

from ..backend import DatabaseAdapter, DatabaseConfig


logger = logging.getLogger(__name__)


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL database adapter using asyncpg.
    
    This adapter uses asyncpg's connection pool for efficient
    concurrent database access.
    
    Features:
    - Connection pooling with configurable min/max connections
    - SSL support
    - Automatic reconnection on connection loss
    - Dict-like row access via Record objects
    """
    
    def __init__(self, config: DatabaseConfig):
        if not ASYNCPG_AVAILABLE:
            raise ImportError(
                "asyncpg is required for PostgreSQL support. "
                "Install it with: pip install asyncpg"
            )
        super().__init__(config)
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Initialize the PostgreSQL connection pool."""
        ssl_context = "require" if self.config.pg_ssl else None
        
        self._pool = await asyncpg.create_pool(
            host=self.config.pg_host,
            port=self.config.pg_port,
            database=self.config.pg_database,
            user=self.config.pg_user,
            password=self.config.pg_password,
            min_size=self.config.pg_pool_min,
            max_size=self.config.pg_pool_max,
            ssl=ssl_context,
        )
        logger.info(
            f"PostgreSQL pool connected to {self.config.pg_host}:"
            f"{self.config.pg_port}/{self.config.pg_database}"
        )
    
    async def disconnect(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL pool closed")
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        """Acquire a connection from the pool."""
        if self._pool is None:
            await self.connect()
        
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> str:
        """Execute a query and return the status.
        
        Note: PostgreSQL uses $1, $2, etc. for parameters.
        The query should already use this format.
        """
        async with self.acquire() as conn:
            if params:
                return await conn.execute(query, *params)
            return await conn.execute(query)
    
    async def fetch_one(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> Optional[dict]:
        """Execute a query and return one row as a dict."""
        async with self.acquire() as conn:
            if params:
                row = await conn.fetchrow(query, *params)
            else:
                row = await conn.fetchrow(query)
            
            if row is None:
                return None
            return dict(row)
    
    async def fetch_all(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> list[dict]:
        """Execute a query and return all rows as dicts."""
        async with self.acquire() as conn:
            if params:
                rows = await conn.fetch(query, *params)
            else:
                rows = await conn.fetch(query)
            
            return [dict(row) for row in rows]
    
    async def fetch_val(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> Any:
        """Execute a query and return a single value."""
        async with self.acquire() as conn:
            if params:
                return await conn.fetchval(query, *params)
            return await conn.fetchval(query)
    
    @property
    def placeholder(self) -> str:
        """Return the PostgreSQL parameter placeholder format.
        
        Note: PostgreSQL uses $1, $2, etc. but this returns '$'
        as a marker. Use convert_placeholders() to convert
        SQLite-style '?' to PostgreSQL-style.
        """
        return "$"
    
    async def execute_many(
        self,
        query: str,
        params_list: list[tuple],
    ) -> None:
        """Execute a query with multiple parameter sets.
        
        Uses PostgreSQL's executemany for efficiency.
        """
        async with self.acquire() as conn:
            await conn.executemany(query, params_list)
    
    async def copy_records(
        self,
        table_name: str,
        records: list[tuple],
        columns: list[str],
    ) -> None:
        """Bulk insert records using PostgreSQL COPY.
        
        This is much faster than INSERT for large datasets.
        """
        async with self.acquire() as conn:
            await conn.copy_records_to_table(
                table_name,
                records=records,
                columns=columns,
            )


def convert_placeholders(query: str) -> str:
    """Convert SQLite-style ? placeholders to PostgreSQL $1, $2, etc.
    
    Args:
        query: SQL query with ? placeholders
        
    Returns:
        Query with $1, $2, ... placeholders
        
    Example:
        >>> convert_placeholders("SELECT * FROM t WHERE a=? AND b=?")
        "SELECT * FROM t WHERE a=$1 AND b=$2"
    """
    result = []
    param_count = 0
    i = 0
    while i < len(query):
        if query[i] == '?':
            param_count += 1
            result.append(f"${param_count}")
        else:
            result.append(query[i])
        i += 1
    return ''.join(result)
