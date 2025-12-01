"""
Synchronous connection pool for SQLite databases.

This module provides a thread-safe connection pool for synchronous
SQLite access, complementing the async aiosqlite adapter.

The pool manages a fixed number of connections, with automatic
reconnection on failure and WAL mode enabled for concurrent access.
"""

from __future__ import annotations

import sqlite3
import threading
import queue
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncPoolConfig:
    """Configuration for the synchronous connection pool.
    
    Attributes:
        db_path: Path to the SQLite database file
        pool_size: Number of connections to maintain in the pool
        timeout: SQLite connection timeout in seconds
        check_same_thread: Whether to check thread affinity (False for pool)
        max_wait: Maximum seconds to wait for a connection from pool
    """
    db_path: str
    pool_size: int = 5
    timeout: float = 30.0
    check_same_thread: bool = False
    max_wait: float = 10.0


class SyncConnectionPool:
    """Thread-safe synchronous connection pool for SQLite.
    
    This pool maintains a fixed number of connections that can be
    acquired and released by multiple threads. Each connection is
    configured with WAL mode for concurrent access.
    
    Usage:
        pool = SyncConnectionPool(SyncPoolConfig(db_path="/path/to/db.sqlite3"))
        pool.initialize()
        
        with pool.acquire() as conn:
            cursor = conn.execute("SELECT * FROM table")
            rows = cursor.fetchall()
        
        pool.close()
    
    Thread Safety:
        The pool is thread-safe. Connections can be safely acquired
        and released from multiple threads.
    """
    
    def __init__(self, config: SyncPoolConfig):
        self.config = config
        self._pool: queue.Queue[sqlite3.Connection] = queue.Queue(maxsize=config.pool_size)
        self._lock = threading.Lock()
        self._initialized = False
        self._closed = False
        self._connection_count = 0
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with proper configuration."""
        conn = sqlite3.connect(
            self.config.db_path,
            timeout=self.config.timeout,
            check_same_thread=self.config.check_same_thread,
        )
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode and other optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-65536")  # 64MB cache
        
        return conn
    
    def _validate_connection(self, conn: sqlite3.Connection) -> bool:
        """Check if a connection is still valid."""
        try:
            conn.execute("SELECT 1")
            return True
        except (sqlite3.Error, ValueError):
            return False
    
    def initialize(self) -> None:
        """Initialize the connection pool.
        
        Creates all connections upfront. This should be called
        before using the pool.
        """
        with self._lock:
            if self._initialized:
                return
            
            for _ in range(self.config.pool_size):
                try:
                    conn = self._create_connection()
                    self._pool.put_nowait(conn)
                    self._connection_count += 1
                except sqlite3.Error as e:
                    logger.error(f"Failed to create pool connection: {e}")
                    raise
            
            self._initialized = True
            logger.info(
                f"Sync pool initialized with {self._connection_count} connections "
                f"for {self.config.db_path}"
            )
    
    def close(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            if self._closed:
                return
            
            self._closed = True
            closed_count = 0
            
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    try:
                        conn.close()
                        closed_count += 1
                    except sqlite3.Error:
                        pass
                except queue.Empty:
                    break
            
            logger.info(f"Sync pool closed ({closed_count} connections)")
    
    @contextmanager
    def acquire(self) -> Iterator[sqlite3.Connection]:
        """Acquire a connection from the pool.
        
        The connection is automatically returned to the pool when
        the context manager exits.
        
        Yields:
            A SQLite connection from the pool
            
        Raises:
            RuntimeError: If pool is not initialized or is closed
            TimeoutError: If no connection available within max_wait
        """
        if not self._initialized:
            raise RuntimeError("Pool not initialized. Call initialize() first.")
        
        if self._closed:
            raise RuntimeError("Pool is closed.")
        
        conn: Optional[sqlite3.Connection] = None
        
        try:
            # Try to get a connection from the pool
            conn = self._pool.get(timeout=self.config.max_wait)
            
            # Validate and reconnect if needed
            if not self._validate_connection(conn):
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
                conn = self._create_connection()
            
            yield conn
            
        except queue.Empty:
            raise TimeoutError(
                f"No connection available within {self.config.max_wait}s"
            )
        finally:
            # Return connection to pool
            if conn is not None:
                try:
                    # Rollback any uncommitted transaction
                    conn.rollback()
                    self._pool.put_nowait(conn)
                except queue.Full:
                    # Pool is full, close this connection
                    try:
                        conn.close()
                    except sqlite3.Error:
                        pass
                except sqlite3.Error:
                    # Connection is dead, don't return to pool
                    try:
                        new_conn = self._create_connection()
                        self._pool.put_nowait(new_conn)
                    except (sqlite3.Error, queue.Full):
                        pass
    
    @property
    def available(self) -> int:
        """Number of available connections in the pool."""
        return self._pool.qsize()
    
    @property
    def size(self) -> int:
        """Total pool size."""
        return self.config.pool_size


# Global pool instances for each database
_pools: dict[str, SyncConnectionPool] = {}
_pools_lock = threading.Lock()


def get_sync_pool(
    db_path: str,
    pool_size: int = 5,
    timeout: float = 30.0,
) -> SyncConnectionPool:
    """Get or create a sync connection pool for a database.
    
    Pools are cached by database path and reused.
    
    Args:
        db_path: Path to the SQLite database
        pool_size: Number of connections in the pool
        timeout: SQLite connection timeout
        
    Returns:
        Initialized SyncConnectionPool
    """
    with _pools_lock:
        if db_path not in _pools:
            config = SyncPoolConfig(
                db_path=db_path,
                pool_size=pool_size,
                timeout=timeout,
            )
            pool = SyncConnectionPool(config)
            pool.initialize()
            _pools[db_path] = pool
        
        return _pools[db_path]


def close_all_sync_pools() -> None:
    """Close all sync connection pools."""
    with _pools_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()
