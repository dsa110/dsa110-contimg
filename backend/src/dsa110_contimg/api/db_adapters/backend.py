"""
Database backend abstraction for SQLite.

This module provides a Protocol-based abstraction for database backends.
The abstraction is designed to be minimal - it wraps the connection
and provides a consistent async interface.

Note: PostgreSQL support was removed in the complexity reduction refactor.
The pipeline exclusively uses SQLite for data storage. ABSURD workflow
manager uses its own PostgreSQL database separately.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional, Protocol, runtime_checkable


@dataclass
class DatabaseConfig:
    """Database configuration for SQLite.
    
    Example:
        sqlite_path = "/path/to/database.db"
    """
    
    # SQLite settings
    sqlite_path: str = ""
    sqlite_timeout: float = 30.0
    
    @classmethod
    def from_env(cls, prefix: str = "DSA110_DB") -> "DatabaseConfig":
        """Create configuration from environment variables.
        
        Environment variables (with default prefix DSA110_DB):
        - {prefix}_SQLITE_PATH: SQLite database path
        - {prefix}_SQLITE_TIMEOUT: Connection timeout (default: 30.0)
        """
        return cls(
            sqlite_path=os.getenv(
                f"{prefix}_SQLITE_PATH",
                os.getenv("PIPELINE_PRODUCTS_DB", "/data/dsa110-contimg/state/db/products.sqlite3")
            ),
            sqlite_timeout=float(os.getenv(f"{prefix}_SQLITE_TIMEOUT", "30.0")),
        )
    
    @property
    def connection_string(self) -> str:
        """Get connection string for SQLite."""
        return f"sqlite:///{self.sqlite_path}"


@runtime_checkable
class AsyncConnection(Protocol):
    """Protocol for async database connections.
    
    This provides a common interface that both aiosqlite and asyncpg
    connections can satisfy.
    """
    
    async def execute(self, query: str, *args: Any) -> Any:
        """Execute a query."""
        ...
    
    async def fetchone(self) -> Optional[Any]:
        """Fetch one row from the last query."""
        ...
    
    async def fetchall(self) -> list[Any]:
        """Fetch all rows from the last query."""
        ...
    
    async def close(self) -> None:
        """Close the connection."""
        ...


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters.
    
    Each adapter provides a consistent async interface for database
    operations, hiding backend-specific differences.
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
    
    @abstractmethod
    async def connect(self) -> None:
        """Initialize the connection pool."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close all connections."""
        pass
    
    @abstractmethod
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Any]:
        """Acquire a connection from the pool."""
        yield  # type: ignore
    
    @abstractmethod
    async def execute(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> Any:
        """Execute a query and return the result."""
        pass
    
    @abstractmethod
    async def fetch_one(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> Optional[dict]:
        """Execute a query and return one row as a dict."""
        pass
    
    @abstractmethod
    async def fetch_all(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> list[dict]:
        """Execute a query and return all rows as dicts."""
        pass
    
    @abstractmethod
    async def fetch_val(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> Any:
        """Execute a query and return a single value."""
        pass
    
    @property
    @abstractmethod
    def placeholder(self) -> str:
        """Return the parameter placeholder for this backend.
        
        SQLite uses '?', PostgreSQL uses '$1', '$2', etc.
        """
        pass
    
    @property
    def backend(self) -> str:
        """Return the backend type (always 'sqlite')."""
        return "sqlite"


def create_adapter(config: Optional[DatabaseConfig] = None) -> DatabaseAdapter:
    """Factory function to create the SQLite database adapter.
    
    Args:
        config: Database configuration. If None, loads from environment.
        
    Returns:
        SQLiteAdapter instance.
    """
    if config is None:
        config = DatabaseConfig.from_env()
    
    from .adapters.sqlite_adapter import SQLiteAdapter
    return SQLiteAdapter(config)
