"""Database utilities with retry logic, monitoring, and connection pooling."""

from __future__ import annotations

import logging
import sqlite3
import time
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """Simple connection pool for SQLite databases.

    Maintains a pool of connections per database path to reduce connection overhead.
    Connections are reused but not shared across threads (SQLite limitation).
    """

    def __init__(self, max_connections: int = 5, timeout: float = 30.0):
        """Initialize the connection pool.

        Args:
            max_connections: Maximum connections per database path
            timeout: Connection timeout in seconds
        """
        self.max_connections = max_connections
        self.timeout = timeout
        self._pools: Dict[str, deque] = {}
        self._locks: Dict[str, Lock] = {}
        self._active_connections: Dict[str, int] = {}

    def _get_pool_key(self, db_path: Path) -> str:
        """Get a unique key for the database path."""
        return str(db_path.resolve())

    def _create_connection(self, db_path: Path) -> sqlite3.Connection:
        """Create a new database connection with optimal settings."""
        conn = sqlite3.connect(str(db_path), timeout=self.timeout)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass  # WAL may not be available on some filesystems
        # Set busy timeout
        # Note: PRAGMA doesn't support parameterized queries, but timeout_ms is a calculated value, not user input
        timeout_ms = int(self.timeout * 1000)
        conn.execute(f"PRAGMA busy_timeout={timeout_ms}")
        return conn

    @contextmanager
    def get_connection(self, db_path: Path):
        """Get a connection from the pool (context manager).

        Yields:
            sqlite3.Connection: Database connection

        Example:
            with pool.get_connection(db_path) as conn:
                cursor = conn.execute("SELECT * FROM table")
        """
        pool_key = self._get_pool_key(db_path)

        # Initialize pool for this database if needed
        if pool_key not in self._pools:
            self._pools[pool_key] = deque()
            self._locks[pool_key] = Lock()
            self._active_connections[pool_key] = 0

        lock = self._locks[pool_key]
        pool = self._pools[pool_key]

        conn = None
        try:
            with lock:
                # Try to get a connection from the pool
                if pool:
                    conn = pool.popleft()
                    # Verify connection is still valid
                    try:
                        conn.execute("SELECT 1").fetchone()
                    except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                        # Connection is invalid, create a new one
                        try:
                            conn.close()
                        except Exception:
                            pass
                        conn = None

                # Create new connection if pool is empty or connection invalid
                if conn is None:
                    if self._active_connections[pool_key] < self.max_connections:
                        conn = self._create_connection(db_path)
                        self._active_connections[pool_key] += 1
                    else:
                        # Pool exhausted, create temporary connection
                        conn = self._create_connection(db_path)

            yield conn

        finally:
            # Return connection to pool if it's from the pool
            if conn is not None:
                try:
                    # Rollback any uncommitted transactions
                    conn.rollback()
                except Exception:
                    pass

                with lock:
                    # Only return to pool if we're under the limit
                    if (
                        pool_key in self._active_connections
                        and len(pool) < self.max_connections
                        and self._active_connections[pool_key] <= self.max_connections
                    ):
                        pool.append(conn)
                    else:
                        # Close connection if pool is full or we're over limit
                        try:
                            conn.close()
                        except Exception:
                            pass
                        if pool_key in self._active_connections:
                            self._active_connections[pool_key] = max(
                                0, self._active_connections[pool_key] - 1
                            )


class DatabasePerformanceMonitor:
    """Monitor database operation performance."""

    def __init__(self, max_history: int = 1000):
        """Initialize the performance monitor.

        Args:
            max_history: Maximum number of operations to track
        """
        self.operation_times: deque = deque(maxlen=max_history)
        self.error_count = 0
        self.total_operations = 0
        self.lock = Lock()

    def record_operation(
        self,
        operation_name: str,
        duration: float,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """Record a database operation.

        Args:
            operation_name: Name of the operation
            duration: Duration in seconds
            success: Whether the operation succeeded
            error: Error message if operation failed
        """
        with self.lock:
            self.total_operations += 1
            if not success:
                self.error_count += 1

            self.operation_times.append(
                {
                    "operation": operation_name,
                    "duration": duration,
                    "success": success,
                    "error": error,
                    "timestamp": time.time(),
                }
            )

    def get_stats(self) -> Dict:
        """Get performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        with self.lock:
            if not self.operation_times:
                return {
                    "total_operations": self.total_operations,
                    "error_count": self.error_count,
                    "error_rate": 0.0,
                    "avg_duration": 0.0,
                    "min_duration": 0.0,
                    "max_duration": 0.0,
                    "p50_duration": 0.0,
                    "p95_duration": 0.0,
                    "p99_duration": 0.0,
                }

            durations = [op["duration"] for op in self.operation_times if op["success"]]
            sorted_durations = sorted(durations) if durations else []

            return {
                "total_operations": self.total_operations,
                "error_count": self.error_count,
                "error_rate": (
                    self.error_count / self.total_operations if self.total_operations > 0 else 0.0
                ),
                "avg_duration": (
                    sum(sorted_durations) / len(sorted_durations) if sorted_durations else 0.0
                ),
                "min_duration": min(sorted_durations) if sorted_durations else 0.0,
                "max_duration": max(sorted_durations) if sorted_durations else 0.0,
                "p50_duration": (
                    sorted_durations[len(sorted_durations) // 2] if sorted_durations else 0.0
                ),
                "p95_duration": (
                    sorted_durations[int(len(sorted_durations) * 0.95)] if sorted_durations else 0.0
                ),
                "p99_duration": (
                    sorted_durations[int(len(sorted_durations) * 0.99)] if sorted_durations else 0.0
                ),
            }


# Global instances
_connection_pool: Optional[DatabaseConnectionPool] = None
_performance_monitor: Optional[DatabasePerformanceMonitor] = None


def get_connection_pool() -> DatabaseConnectionPool:
    """Get the global connection pool instance."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = DatabaseConnectionPool(max_connections=5, timeout=30.0)
    return _connection_pool


def get_performance_monitor() -> DatabasePerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = DatabasePerformanceMonitor(max_history=1000)
    return _performance_monitor


def retry_db_operation(
    func,
    max_retries: int = 3,
    initial_delay: float = 0.1,
    operation_name: str = "database_operation",
):
    """Retry a database operation with exponential backoff and monitoring.

    Args:
        func: Function to retry (should be a callable that returns a value)
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (doubles with each retry)
        operation_name: Name of the operation for monitoring

    Returns:
        Result of the function call

    Raises:
        Last exception if all retries fail
    """
    monitor = get_performance_monitor()
    start_time = time.time()
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            result = func()
            duration = time.time() - start_time
            monitor.record_operation(operation_name, duration, success=True)
            return result
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            last_exception = e
            error_msg = str(e).lower()
            # Check if it's a locking error
            if "locked" in error_msg or "database is locked" in error_msg:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Database locked, retrying {operation_name} "
                        f"(attempt {attempt + 1}/{max_retries}) after {delay}s"
                    )
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
            # For other database errors, record and re-raise immediately
            duration = time.time() - start_time
            monitor.record_operation(operation_name, duration, success=False, error=str(e))
            raise
        except Exception as e:
            # For non-database errors, record and re-raise immediately
            duration = time.time() - start_time
            monitor.record_operation(operation_name, duration, success=False, error=str(e))
            raise

    # If we exhausted retries, record failure and raise
    duration = time.time() - start_time
    monitor.record_operation(
        operation_name,
        duration,
        success=False,
        error=f"Exhausted {max_retries} retries: {last_exception}",
    )
    raise last_exception


@contextmanager
def db_operation(
    db_path: Path,
    operation_name: str = "database_operation",
    use_pool: bool = True,
    retry: bool = False,
):
    """Context manager for database operations with optional retry and monitoring.

    Args:
        db_path: Path to the database file
        operation_name: Name of the operation for monitoring
        use_pool: Whether to use connection pooling
        retry: Whether to retry on locking errors (use retry_db_operation wrapper instead)

    Yields:
        sqlite3.Connection: Database connection

    Example:
        with db_operation(db_path, "fetch_data") as conn:
            cursor = conn.execute("SELECT * FROM table")
    """
    monitor = get_performance_monitor()
    start_time = time.time()

    if use_pool:
        pool = get_connection_pool()
        conn_context = pool.get_connection(db_path)
    else:
        # Fallback to direct connection
        from contextlib import closing

        from dsa110_contimg.api.data_access import _connect

        conn_context = closing(_connect(db_path))

    try:
        with conn_context as conn:
            yield conn
        duration = time.time() - start_time
        monitor.record_operation(operation_name, duration, success=True)
    except Exception as e:
        duration = time.time() - start_time
        monitor.record_operation(operation_name, duration, success=False, error=str(e))
        raise
