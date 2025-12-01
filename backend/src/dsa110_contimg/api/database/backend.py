"""
Database backend abstraction for multi-database support.

This module provides a Protocol-based abstraction for database backends,
allowing the API to work with both SQLite and PostgreSQL.

The abstraction is designed to be minimal - it wraps the connection
and provides a consistent async interface. Query syntax differences
are handled by the query builder module.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional, Protocol, runtime_checkable


class DatabaseBackend(str, Enum):
    """Supported database backends."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@dataclass
class DatabaseConfig:
    """Database configuration supporting both SQLite and PostgreSQL.
    
    For SQLite:
        backend = "sqlite"
        sqlite_path = "/path/to/database.db"
        
    For PostgreSQL:
        backend = "postgresql"
        pg_host = "localhost"
        pg_port = 5432
        pg_database = "dsa110"
        pg_user = "user"
        pg_password = "password"
        pg_pool_size = 5
    """
    
    backend: DatabaseBackend = DatabaseBackend.SQLITE
    
    # SQLite settings
    sqlite_path: str = ""
    sqlite_timeout: float = 30.0
    
    # PostgreSQL settings
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "dsa110"
    pg_user: str = ""
    pg_password: str = ""
    pg_pool_min: int = 1
    pg_pool_max: int = 10
    pg_ssl: bool = False
    
    @classmethod
    def from_env(cls, prefix: str = "DSA110_DB") -> "DatabaseConfig":
        """Create configuration from environment variables.
        
        Environment variables (with default prefix DSA110_DB):
        - {prefix}_BACKEND: sqlite or postgresql
        - {prefix}_SQLITE_PATH: SQLite database path
        - {prefix}_PG_HOST: PostgreSQL host
        - {prefix}_PG_PORT: PostgreSQL port
        - {prefix}_PG_DATABASE: PostgreSQL database name
        - {prefix}_PG_USER: PostgreSQL username
        - {prefix}_PG_PASSWORD: PostgreSQL password
        - {prefix}_PG_POOL_MIN: Min pool connections
        - {prefix}_PG_POOL_MAX: Max pool connections
        - {prefix}_PG_SSL: Use SSL (true/false)
        """
        backend_str = os.getenv(f"{prefix}_BACKEND", "sqlite").lower()
        backend = DatabaseBackend(backend_str)
        
        return cls(
            backend=backend,
            sqlite_path=os.getenv(
                f"{prefix}_SQLITE_PATH",
                os.getenv("PIPELINE_PRODUCTS_DB", "/data/dsa110-contimg/state/products.sqlite3")
            ),
            sqlite_timeout=float(os.getenv(f"{prefix}_SQLITE_TIMEOUT", "30.0")),
            pg_host=os.getenv(f"{prefix}_PG_HOST", "localhost"),
            pg_port=int(os.getenv(f"{prefix}_PG_PORT", "5432")),
            pg_database=os.getenv(f"{prefix}_PG_DATABASE", "dsa110"),
            pg_user=os.getenv(f"{prefix}_PG_USER", ""),
            pg_password=os.getenv(f"{prefix}_PG_PASSWORD", ""),
            pg_pool_min=int(os.getenv(f"{prefix}_PG_POOL_MIN", "1")),
            pg_pool_max=int(os.getenv(f"{prefix}_PG_POOL_MAX", "10")),
            pg_ssl=os.getenv(f"{prefix}_PG_SSL", "false").lower() == "true",
        )
    
    @property
    def connection_string(self) -> str:
        """Get connection string for the configured backend."""
        if self.backend == DatabaseBackend.SQLITE:
            return f"sqlite:///{self.sqlite_path}"
        else:
            ssl_suffix = "?sslmode=require" if self.pg_ssl else ""
            return (
                f"postgresql://{self.pg_user}:{self.pg_password}@"
                f"{self.pg_host}:{self.pg_port}/{self.pg_database}{ssl_suffix}"
            )


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
    def backend(self) -> DatabaseBackend:
        """Return the backend type."""
        return self.config.backend


def create_adapter(config: Optional[DatabaseConfig] = None) -> DatabaseAdapter:
    """Factory function to create the appropriate database adapter.
    
    Args:
        config: Database configuration. If None, loads from environment.
        
    Returns:
        DatabaseAdapter instance for the configured backend.
        
    Raises:
        ValueError: If the backend is not supported.
    """
    if config is None:
        config = DatabaseConfig.from_env()
    
    if config.backend == DatabaseBackend.SQLITE:
        from .adapters.sqlite_adapter import SQLiteAdapter
        return SQLiteAdapter(config)
    elif config.backend == DatabaseBackend.POSTGRESQL:
        from .adapters.postgresql_adapter import PostgreSQLAdapter
        return PostgreSQLAdapter(config)
    else:
        raise ValueError(f"Unsupported database backend: {config.backend}")
