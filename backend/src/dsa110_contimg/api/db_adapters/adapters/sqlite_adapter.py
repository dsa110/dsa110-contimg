"""
SQLite database adapter using aiosqlite.

This adapter provides an async interface to SQLite databases,
maintaining compatibility with the existing codebase while
providing a consistent interface with PostgreSQL.
"""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import aiosqlite

from ..backend import DatabaseAdapter, DatabaseConfig


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter using aiosqlite.
    
    This adapter wraps aiosqlite to provide a consistent interface
    that matches the PostgreSQL adapter.
    """
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Initialize the SQLite connection.
        
        SQLite doesn't have a connection pool, so we maintain
        a single connection with WAL mode enabled.
        """
        self._connection = await aiosqlite.connect(
            self.config.sqlite_path,
            timeout=self.config.sqlite_timeout,
        )
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
    
    async def disconnect(self) -> None:
        """Close the SQLite connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[aiosqlite.Connection]:
        """Acquire the connection.
        
        SQLite uses a single connection, so this just returns it.
        The connection is tested and reconnected if needed.
        """
        if self._connection is None:
            await self.connect()
        
        # Test connection is still valid
        try:
            await self._connection.execute("SELECT 1")
        except (sqlite3.Error, ValueError):
            await self.connect()
        
        yield self._connection
    
    async def execute(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> aiosqlite.Cursor:
        """Execute a query and return the cursor."""
        async with self.acquire() as conn:
            if params:
                return await conn.execute(query, params)
            return await conn.execute(query)
    
    async def fetch_one(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> Optional[dict]:
        """Execute a query and return one row as a dict."""
        cursor = await self.execute(query, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    async def fetch_all(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> list[dict]:
        """Execute a query and return all rows as dicts."""
        cursor = await self.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def fetch_val(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> Any:
        """Execute a query and return a single value."""
        cursor = await self.execute(query, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return row[0]
    
    @property
    def placeholder(self) -> str:
        """Return the SQLite parameter placeholder."""
        return "?"
    
    async def execute_many(
        self,
        query: str,
        params_list: list[tuple],
    ) -> None:
        """Execute a query with multiple parameter sets."""
        async with self.acquire() as conn:
            await conn.executemany(query, params_list)
            await conn.commit()
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._connection:
            await self._connection.commit()
    
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._connection:
            await self._connection.rollback()
