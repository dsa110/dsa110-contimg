"""
Error Recovery Module for DSA-110 Pipeline.

Provides:
- Exponential backoff retry logic
- Checkpoint-based resume for failed jobs
- Dead letter queue for persistent failures
- Alert integration for critical failures

Usage:
    from dsa110_contimg.pipeline.error_recovery import (
        RetryPolicy, ErrorRecoveryManager, DeadLetterQueue
    )

    # Configure retry policy
    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=60.0)

    # Use recovery manager
    recovery = ErrorRecoveryManager(policy)
    await recovery.execute_with_retry(my_function, "ms_path", ...)

    # Or use decorator
    @with_retry(max_retries=3)
    async def process_ms(ms_path: str) -> None:
        ...
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import random
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generator,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Retry Policy Configuration
# =============================================================================


class BackoffStrategy(str, Enum):
    """Backoff strategy for retries."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"
    FIBONACCI = "fibonacci"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay cap in seconds
        backoff_strategy: How to increase delay between retries
        backoff_factor: Multiplier for exponential/linear backoff
        jitter: Add random jitter (0.0-1.0) to prevent thundering herd
        retryable_exceptions: Exception types that trigger retry
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_factor: float = 2.0
    jitter: float = 0.1
    retryable_exceptions: tuple = (Exception,)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (0-indexed).

        Args:
            attempt: Current attempt number (0 = first retry)

        Returns:
            Delay in seconds with optional jitter
        """
        if self.backoff_strategy == BackoffStrategy.CONSTANT:
            delay = self.base_delay
        elif self.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay * (1 + attempt * self.backoff_factor)
        elif self.backoff_strategy == BackoffStrategy.FIBONACCI:
            delay = self.base_delay * _fibonacci(attempt + 2)
        else:  # EXPONENTIAL (default)
            delay = self.base_delay * (self.backoff_factor**attempt)

        # Apply cap
        delay = min(delay, self.max_delay)

        # Apply jitter
        if self.jitter > 0:
            jitter_range = delay * self.jitter
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay)  # Ensure positive delay

        return delay


def _fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number for backoff."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


# Default policies for different scenarios
QUICK_RETRY_POLICY = RetryPolicy(max_retries=2, base_delay=0.5, max_delay=5.0)

STANDARD_RETRY_POLICY = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=60.0)

AGGRESSIVE_RETRY_POLICY = RetryPolicy(max_retries=5, base_delay=2.0, max_delay=300.0)


# =============================================================================
# Retry Result and Attempt Tracking
# =============================================================================


class RetryOutcome(str, Enum):
    """Outcome of a retry attempt."""

    SUCCESS = "success"
    RETRY = "retry"
    EXHAUSTED = "exhausted"
    NON_RETRYABLE = "non_retryable"


@dataclass
class RetryAttempt:
    """Record of a single retry attempt."""

    attempt_number: int
    started_at: float
    ended_at: float
    success: bool
    error: Optional[str] = None
    error_type: Optional[str] = None
    delay_before: float = 0.0

    @property
    def duration(self) -> float:
        """Duration of the attempt in seconds."""
        return self.ended_at - self.started_at


@dataclass
class RetryResult(Generic[T]):
    """Result of retry execution.

    Attributes:
        success: Whether execution ultimately succeeded
        result: Return value if successful
        attempts: List of all attempts made
        final_error: Final error if failed
        total_duration: Total time spent including delays
    """

    success: bool
    result: Optional[T] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    final_error: Optional[str] = None
    final_error_type: Optional[str] = None
    total_duration: float = 0.0

    @property
    def attempt_count(self) -> int:
        """Number of attempts made."""
        return len(self.attempts)

    @property
    def outcome(self) -> RetryOutcome:
        """Overall outcome of the retry execution."""
        if self.success:
            return RetryOutcome.SUCCESS
        if self.final_error_type and "non_retryable" in self.final_error_type.lower():
            return RetryOutcome.NON_RETRYABLE
        return RetryOutcome.EXHAUSTED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "outcome": self.outcome.value,
            "attempt_count": self.attempt_count,
            "total_duration_s": self.total_duration,
            "final_error": self.final_error,
            "final_error_type": self.final_error_type,
            "attempts": [
                {
                    "attempt": a.attempt_number,
                    "duration_s": a.duration,
                    "success": a.success,
                    "error": a.error,
                }
                for a in self.attempts
            ],
        }


# =============================================================================
# Error Recovery Manager
# =============================================================================


class ErrorRecoveryManager:
    """Manages error recovery with retries and checkpoints.

    Provides centralized retry logic with:
    - Configurable retry policies
    - Checkpoint-based resume
    - Alert integration for failures
    - Metrics collection
    """

    def __init__(
        self,
        policy: Optional[RetryPolicy] = None,
        alert_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        metrics_callback: Optional[Callable[[str, RetryResult], None]] = None,
    ):
        """Initialize recovery manager.

        Args:
            policy: Default retry policy
            alert_callback: Async callback for alerts (severity, title, message)
            metrics_callback: Callback for metrics (operation_name, result)
        """
        self.default_policy = policy or STANDARD_RETRY_POLICY
        self.alert_callback = alert_callback
        self.metrics_callback = metrics_callback

    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        policy: Optional[RetryPolicy] = None,
        operation_name: Optional[str] = None,
        checkpoint_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> RetryResult[T]:
        """Execute async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            policy: Override retry policy
            operation_name: Name for logging/metrics
            checkpoint_data: Checkpoint data for resume
            **kwargs: Keyword arguments for func

        Returns:
            RetryResult with outcome and all attempts
        """
        policy = policy or self.default_policy
        op_name = operation_name or func.__name__
        attempts: List[RetryAttempt] = []
        start_time = time.time()

        # Inject checkpoint data if function accepts it
        if checkpoint_data and "checkpoint" in func.__code__.co_varnames:
            kwargs["checkpoint"] = checkpoint_data

        for attempt_num in range(policy.max_retries + 1):
            delay = 0.0 if attempt_num == 0 else policy.calculate_delay(attempt_num - 1)

            if delay > 0:
                logger.debug(
                    "Retry %d/%d for %s, waiting %.1fs",
                    attempt_num,
                    policy.max_retries,
                    op_name,
                    delay,
                )
                await asyncio.sleep(delay)

            attempt_start = time.time()
            try:
                result = await func(*args, **kwargs)
                attempt_end = time.time()

                attempts.append(
                    RetryAttempt(
                        attempt_number=attempt_num + 1,
                        started_at=attempt_start,
                        ended_at=attempt_end,
                        success=True,
                        delay_before=delay,
                    )
                )

                retry_result = RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_duration=time.time() - start_time,
                )

                if self.metrics_callback:
                    self.metrics_callback(op_name, retry_result)

                return retry_result

            except policy.retryable_exceptions as e:
                attempt_end = time.time()
                error_type = type(e).__name__
                error_msg = str(e)

                attempts.append(
                    RetryAttempt(
                        attempt_number=attempt_num + 1,
                        started_at=attempt_start,
                        ended_at=attempt_end,
                        success=False,
                        error=error_msg,
                        error_type=error_type,
                        delay_before=delay,
                    )
                )

                logger.warning(
                    "Attempt %d/%d failed for %s: %s",
                    attempt_num + 1,
                    policy.max_retries + 1,
                    op_name,
                    error_msg,
                )

            except Exception as e:
                # Non-retryable exception
                attempt_end = time.time()
                error_type = type(e).__name__
                error_msg = str(e)

                attempts.append(
                    RetryAttempt(
                        attempt_number=attempt_num + 1,
                        started_at=attempt_start,
                        ended_at=attempt_end,
                        success=False,
                        error=error_msg,
                        error_type=f"non_retryable_{error_type}",
                        delay_before=delay,
                    )
                )

                logger.error("Non-retryable error for %s: %s", op_name, error_msg)
                break

        # All retries exhausted
        final_attempt = attempts[-1] if attempts else None
        retry_result = RetryResult(
            success=False,
            attempts=attempts,
            final_error=final_attempt.error if final_attempt else None,
            final_error_type=final_attempt.error_type if final_attempt else None,
            total_duration=time.time() - start_time,
        )

        if self.metrics_callback:
            self.metrics_callback(op_name, retry_result)

        # Send alert for exhausted retries
        if self.alert_callback:
            await self._send_failure_alert(op_name, retry_result)

        return retry_result

    async def _send_failure_alert(
        self, operation_name: str, result: RetryResult
    ) -> None:
        """Send alert for failed operation."""
        if not self.alert_callback:
            return

        severity = "critical" if result.attempt_count >= 3 else "warning"
        title = f"Pipeline operation failed: {operation_name}"
        message = (
            f"Operation '{operation_name}' failed after {result.attempt_count} attempts.\n"
            f"Final error: {result.final_error}\n"
            f"Total duration: {result.total_duration:.1f}s"
        )

        try:
            await self.alert_callback(severity, title, message)
        except Exception as e:
            logger.error("Failed to send alert: %s", e)


def execute_with_retry_sync(
    func: Callable[..., T],
    *args,
    policy: Optional[RetryPolicy] = None,
    operation_name: Optional[str] = None,
    **kwargs,
) -> RetryResult[T]:
    """Execute synchronous function with retry logic.

    Args:
        func: Sync function to execute
        *args: Positional arguments for func
        policy: Override retry policy
        operation_name: Name for logging
        **kwargs: Keyword arguments for func

    Returns:
        RetryResult with outcome and all attempts
    """
    policy = policy or STANDARD_RETRY_POLICY
    op_name = operation_name or func.__name__
    attempts: List[RetryAttempt] = []
    start_time = time.time()

    for attempt_num in range(policy.max_retries + 1):
        delay = 0.0 if attempt_num == 0 else policy.calculate_delay(attempt_num - 1)

        if delay > 0:
            logger.debug(
                "Retry %d/%d for %s, waiting %.1fs",
                attempt_num,
                policy.max_retries,
                op_name,
                delay,
            )
            time.sleep(delay)

        attempt_start = time.time()
        try:
            result = func(*args, **kwargs)
            attempt_end = time.time()

            attempts.append(
                RetryAttempt(
                    attempt_number=attempt_num + 1,
                    started_at=attempt_start,
                    ended_at=attempt_end,
                    success=True,
                    delay_before=delay,
                )
            )

            return RetryResult(
                success=True,
                result=result,
                attempts=attempts,
                total_duration=time.time() - start_time,
            )

        except policy.retryable_exceptions as e:
            attempt_end = time.time()

            attempts.append(
                RetryAttempt(
                    attempt_number=attempt_num + 1,
                    started_at=attempt_start,
                    ended_at=attempt_end,
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__,
                    delay_before=delay,
                )
            )

            logger.warning(
                "Attempt %d/%d failed for %s: %s",
                attempt_num + 1,
                policy.max_retries + 1,
                op_name,
                e,
            )

        except Exception as e:
            attempt_end = time.time()

            attempts.append(
                RetryAttempt(
                    attempt_number=attempt_num + 1,
                    started_at=attempt_start,
                    ended_at=attempt_end,
                    success=False,
                    error=str(e),
                    error_type=f"non_retryable_{type(e).__name__}",
                    delay_before=delay,
                )
            )
            break

    final_attempt = attempts[-1] if attempts else None
    return RetryResult(
        success=False,
        attempts=attempts,
        final_error=final_attempt.error if final_attempt else None,
        final_error_type=final_attempt.error_type if final_attempt else None,
        total_duration=time.time() - start_time,
    )


# =============================================================================
# Retry Decorator
# =============================================================================


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator to add retry logic to async functions.

    Args:
        max_retries: Maximum retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay cap
        backoff_strategy: Backoff calculation strategy
        retryable_exceptions: Exceptions that trigger retry

    Returns:
        Decorated function with retry behavior
    """
    policy = RetryPolicy(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=backoff_strategy,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            manager = ErrorRecoveryManager(policy)
            result = await manager.execute_with_retry(func, *args, **kwargs)
            if result.success:
                return result.result
            raise RuntimeError(
                f"All {result.attempt_count} attempts failed: {result.final_error}"
            )

        return wrapper

    return decorator


def with_retry_sync(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator to add retry logic to sync functions.

    Args:
        max_retries: Maximum retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay cap
        backoff_strategy: Backoff calculation strategy
        retryable_exceptions: Exceptions that trigger retry

    Returns:
        Decorated function with retry behavior
    """
    policy = RetryPolicy(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=backoff_strategy,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            result = execute_with_retry_sync(func, *args, policy=policy, **kwargs)
            if result.success:
                return result.result
            raise RuntimeError(
                f"All {result.attempt_count} attempts failed: {result.final_error}"
            )

        return wrapper

    return decorator


# =============================================================================
# Dead Letter Queue
# =============================================================================


class DeadLetterReason(str, Enum):
    """Reason for sending to dead letter queue."""

    RETRIES_EXHAUSTED = "retries_exhausted"
    NON_RETRYABLE_ERROR = "non_retryable_error"
    MANUAL_REJECTION = "manual_rejection"
    TIMEOUT = "timeout"
    INVALID_DATA = "invalid_data"


@dataclass
class DeadLetterEntry:
    """Entry in the dead letter queue."""

    id: int
    ms_path: str
    reason: DeadLetterReason
    error_message: str
    error_type: str
    attempt_count: int
    last_attempt_at: float
    created_at: float
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "ms_path": self.ms_path,
            "reason": self.reason.value,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "attempt_count": self.attempt_count,
            "last_attempt_at": datetime.fromtimestamp(self.last_attempt_at).isoformat(),
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "checkpoint_data": self.checkpoint_data,
            "metadata": self.metadata,
        }


class DeadLetterQueue:
    """Dead letter queue for persistent failures.

    Stores failed jobs that have exhausted retries for later
    investigation and manual reprocessing.

    Attributes:
        db_path: Path to SQLite database
        alert_callback: Callback for DLQ alerts
    """

    SCHEMA = """
        CREATE TABLE IF NOT EXISTS dead_letter_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ms_path TEXT NOT NULL,
            reason TEXT NOT NULL,
            error_message TEXT,
            error_type TEXT,
            attempt_count INTEGER DEFAULT 0,
            last_attempt_at REAL,
            checkpoint_data TEXT,
            metadata TEXT,
            created_at REAL NOT NULL,
            resolved_at REAL,
            resolved_by TEXT,
            resolution_notes TEXT,
            UNIQUE(ms_path, created_at)
        )
    """

    INDEX_PATH = """
        CREATE INDEX IF NOT EXISTS idx_dlq_ms_path
        ON dead_letter_queue(ms_path)
    """

    INDEX_REASON = """
        CREATE INDEX IF NOT EXISTS idx_dlq_reason
        ON dead_letter_queue(reason)
    """

    INDEX_CREATED = """
        CREATE INDEX IF NOT EXISTS idx_dlq_created
        ON dead_letter_queue(created_at)
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        alert_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ):
        """Initialize dead letter queue.

        Args:
            db_path: Path to SQLite database. If None, uses pipeline.sqlite3.
            alert_callback: Async callback for alerts (severity, title, message)
        """
        from ..database.session import get_db_path

        self.db_path = db_path or get_db_path("pipeline")
        self.alert_callback = alert_callback
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create database schema if not exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute(self.SCHEMA)
            conn.execute(self.INDEX_PATH)
            conn.execute(self.INDEX_REASON)
            conn.execute(self.INDEX_CREATED)
            conn.commit()

        logger.debug("Dead letter queue schema initialized at %s", self.db_path)

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with WAL mode."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            yield conn
        finally:
            conn.close()

    async def add(
        self,
        ms_path: str,
        reason: DeadLetterReason,
        error_message: str,
        error_type: str = "Unknown",
        attempt_count: int = 0,
        checkpoint_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add entry to dead letter queue.

        Args:
            ms_path: Path to failed MS
            reason: Why it was dead-lettered
            error_message: Error message
            error_type: Type of error
            attempt_count: Number of attempts made
            checkpoint_data: Checkpoint for potential resume
            metadata: Additional metadata

        Returns:
            ID of created entry
        """
        now = time.time()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO dead_letter_queue
                    (ms_path, reason, error_message, error_type, attempt_count,
                     last_attempt_at, checkpoint_data, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ms_path,
                    reason.value,
                    error_message,
                    error_type,
                    attempt_count,
                    now,
                    json.dumps(checkpoint_data or {}),
                    json.dumps(metadata or {}),
                    now,
                ),
            )
            conn.commit()
            entry_id = cursor.lastrowid

        logger.warning(
            "Added to DLQ: %s (reason=%s, id=%d)", ms_path, reason.value, entry_id
        )

        # Send alert
        if self.alert_callback:
            await self._send_dlq_alert(ms_path, reason, error_message)

        return entry_id

    async def _send_dlq_alert(
        self, ms_path: str, reason: DeadLetterReason, error_message: str
    ) -> None:
        """Send alert for new DLQ entry."""
        if not self.alert_callback:
            return

        try:
            await self.alert_callback(
                "critical",
                f"Job sent to Dead Letter Queue: {Path(ms_path).name}",
                f"MS: {ms_path}\nReason: {reason.value}\nError: {error_message}",
            )
        except Exception as e:
            logger.error("Failed to send DLQ alert: %s", e)

    def get_unresolved(
        self, reason: Optional[DeadLetterReason] = None, limit: int = 100
    ) -> List[DeadLetterEntry]:
        """Get unresolved entries from DLQ.

        Args:
            reason: Filter by reason
            limit: Maximum entries to return

        Returns:
            List of unresolved entries
        """
        with self._get_connection() as conn:
            if reason:
                rows = conn.execute(
                    """
                    SELECT id, ms_path, reason, error_message, error_type,
                           attempt_count, last_attempt_at, checkpoint_data,
                           metadata, created_at
                    FROM dead_letter_queue
                    WHERE resolved_at IS NULL AND reason = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (reason.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, ms_path, reason, error_message, error_type,
                           attempt_count, last_attempt_at, checkpoint_data,
                           metadata, created_at
                    FROM dead_letter_queue
                    WHERE resolved_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [self._row_to_entry(row) for row in rows]

    def _row_to_entry(self, row: tuple) -> DeadLetterEntry:
        """Convert database row to DeadLetterEntry."""
        return DeadLetterEntry(
            id=row[0],
            ms_path=row[1],
            reason=DeadLetterReason(row[2]),
            error_message=row[3],
            error_type=row[4],
            attempt_count=row[5] or 0,
            last_attempt_at=row[6] or 0.0,
            checkpoint_data=json.loads(row[7]) if row[7] else {},
            metadata=json.loads(row[8]) if row[8] else {},
            created_at=row[9],
        )

    def resolve(
        self,
        entry_id: int,
        resolved_by: str = "system",
        resolution_notes: str = "",
    ) -> bool:
        """Mark DLQ entry as resolved.

        Args:
            entry_id: ID of entry to resolve
            resolved_by: Who resolved it
            resolution_notes: Notes about resolution

        Returns:
            True if entry was resolved
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE dead_letter_queue
                SET resolved_at = ?, resolved_by = ?, resolution_notes = ?
                WHERE id = ? AND resolved_at IS NULL
                """,
                (time.time(), resolved_by, resolution_notes, entry_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics.

        Returns:
            Dictionary with count by reason and resolution status
        """
        with self._get_connection() as conn:
            # Unresolved by reason
            unresolved = conn.execute(
                """
                SELECT reason, COUNT(*) as count
                FROM dead_letter_queue
                WHERE resolved_at IS NULL
                GROUP BY reason
                """
            ).fetchall()

            # Total resolved
            resolved_count = conn.execute(
                "SELECT COUNT(*) FROM dead_letter_queue WHERE resolved_at IS NOT NULL"
            ).fetchone()[0]

            # Total unresolved
            unresolved_count = conn.execute(
                "SELECT COUNT(*) FROM dead_letter_queue WHERE resolved_at IS NULL"
            ).fetchone()[0]

        return {
            "unresolved_count": unresolved_count,
            "resolved_count": resolved_count,
            "by_reason": {row[0]: row[1] for row in unresolved},
        }

    def requeue(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """Get entry data for reprocessing.

        Args:
            entry_id: ID of entry to requeue

        Returns:
            Entry data with ms_path and checkpoint_data, or None
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT ms_path, checkpoint_data, metadata
                FROM dead_letter_queue
                WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()

        if not row:
            return None

        return {
            "ms_path": row[0],
            "checkpoint_data": json.loads(row[1]) if row[1] else {},
            "metadata": json.loads(row[2]) if row[2] else {},
        }


# =============================================================================
# Checkpoint Manager
# =============================================================================


@dataclass
class Checkpoint:
    """Processing checkpoint for resume capability.

    Attributes:
        ms_path: Path to MS being processed
        stage: Current processing stage
        progress: Progress within stage (0.0-1.0)
        data: Stage-specific checkpoint data
        created_at: When checkpoint was created
    """

    ms_path: str
    stage: str
    progress: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ms_path": self.ms_path,
            "stage": self.stage,
            "progress": self.progress,
            "data": self.data,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Checkpoint:
        """Create from dictionary."""
        return cls(
            ms_path=data["ms_path"],
            stage=data["stage"],
            progress=data.get("progress", 0.0),
            data=data.get("data", {}),
            created_at=data.get("created_at", time.time()),
        )


class CheckpointManager:
    """Manages checkpoints for resumable processing.

    Checkpoints allow long-running jobs to resume from
    the last known good state after a failure.
    """

    def __init__(self, state_machine=None):
        """Initialize checkpoint manager.

        Args:
            state_machine: MSStateMachine instance for persistence
        """
        self._state_machine = state_machine

    def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to state machine.

        Args:
            checkpoint: Checkpoint to save
        """
        if not self._state_machine:
            logger.debug("No state machine - checkpoint not persisted")
            return

        try:
            self._state_machine.save_checkpoint(
                checkpoint.ms_path, checkpoint.to_dict()
            )
            logger.debug(
                "Saved checkpoint for %s at stage %s (%.0f%%)",
                checkpoint.ms_path,
                checkpoint.stage,
                checkpoint.progress * 100,
            )
        except Exception as e:
            logger.error("Failed to save checkpoint: %s", e)

    def load(self, ms_path: str) -> Optional[Checkpoint]:
        """Load checkpoint for MS path.

        Args:
            ms_path: Path to MS

        Returns:
            Checkpoint if exists, None otherwise
        """
        if not self._state_machine:
            return None

        try:
            record = self._state_machine.get_state_record(ms_path)
            if record and record.checkpoint_data:
                return Checkpoint.from_dict(record.checkpoint_data)
        except Exception as e:
            logger.debug("No checkpoint found for %s: %s", ms_path, e)

        return None

    def clear(self, ms_path: str) -> None:
        """Clear checkpoint for MS path.

        Args:
            ms_path: Path to MS
        """
        if not self._state_machine:
            return

        try:
            self._state_machine.save_checkpoint(ms_path, {})
            logger.debug("Cleared checkpoint for %s", ms_path)
        except Exception as e:
            logger.error("Failed to clear checkpoint: %s", e)

    @contextmanager
    def checkpoint_context(
        self, ms_path: str, stage: str
    ) -> Generator[Checkpoint, None, None]:
        """Context manager for checkpoint tracking.

        Automatically saves checkpoint on exit and clears on success.

        Args:
            ms_path: Path to MS
            stage: Processing stage name

        Yields:
            Checkpoint object to update progress/data
        """
        checkpoint = self.load(ms_path) or Checkpoint(ms_path=ms_path, stage=stage)
        checkpoint.stage = stage
        checkpoint.created_at = time.time()

        try:
            yield checkpoint
            # Success - clear checkpoint
            self.clear(ms_path)
        except Exception:
            # Failure - save checkpoint
            self.save(checkpoint)
            raise


# =============================================================================
# Alert Integration
# =============================================================================


async def create_alert_callback(
    webhook_url: Optional[str] = None,
    slack_webhook: Optional[str] = None,
) -> Callable[[str, str, str], Awaitable[None]]:
    """Create an alert callback for error recovery.

    This callback sends alerts via the monitoring tasks system.

    Args:
        webhook_url: Optional webhook URL for alerts
        slack_webhook: Optional Slack webhook URL

    Returns:
        Async callback function for sending alerts
    """
    from ..monitoring.tasks import _execute_send_alert

    async def alert_callback(severity: str, title: str, message: str) -> None:
        """Send alert via monitoring system."""
        params = {
            "severity": severity,
            "title": title,
            "message": message,
            "channels": [],
        }

        if webhook_url:
            params["channels"].append("webhook")
            params["webhook_url"] = webhook_url

        if slack_webhook:
            params["channels"].append("slack")
            params["slack_webhook"] = slack_webhook

        if params["channels"]:
            await _execute_send_alert(params)

    return alert_callback


def create_metrics_callback() -> Callable[[str, RetryResult], None]:
    """Create a metrics callback for error recovery.

    Records retry metrics to the pipeline metrics collector.

    Returns:
        Callback function for recording metrics
    """
    from ..monitoring.pipeline_metrics import get_metrics_collector

    def metrics_callback(operation_name: str, result: RetryResult) -> None:
        """Record retry metrics."""
        collector = get_metrics_collector()

        # Log retry statistics
        if result.attempt_count > 1:
            logger.info(
                "Retry stats for %s: attempts=%d, success=%s, duration=%.1fs",
                operation_name,
                result.attempt_count,
                result.success,
                result.total_duration,
            )

    return metrics_callback


class IntegratedErrorRecovery:
    """Error recovery with integrated alerting and metrics.

    Convenience class that sets up ErrorRecoveryManager with
    alert and metrics callbacks pre-configured.
    """

    def __init__(
        self,
        policy: Optional[RetryPolicy] = None,
        webhook_url: Optional[str] = None,
        slack_webhook: Optional[str] = None,
        enable_metrics: bool = True,
    ):
        """Initialize integrated error recovery.

        Args:
            policy: Retry policy (default: STANDARD_RETRY_POLICY)
            webhook_url: Webhook URL for failure alerts
            slack_webhook: Slack webhook for failure alerts
            enable_metrics: Whether to record retry metrics
        """
        self.policy = policy or STANDARD_RETRY_POLICY
        self.webhook_url = webhook_url
        self.slack_webhook = slack_webhook
        self.enable_metrics = enable_metrics
        self._manager: Optional[ErrorRecoveryManager] = None

    async def get_manager(self) -> ErrorRecoveryManager:
        """Get or create the error recovery manager.

        Returns:
            Configured ErrorRecoveryManager
        """
        if self._manager is None:
            alert_callback = None
            if self.webhook_url or self.slack_webhook:
                alert_callback = await create_alert_callback(
                    self.webhook_url, self.slack_webhook
                )

            metrics_callback = create_metrics_callback() if self.enable_metrics else None

            self._manager = ErrorRecoveryManager(
                policy=self.policy,
                alert_callback=alert_callback,
                metrics_callback=metrics_callback,
            )

        return self._manager

    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        operation_name: Optional[str] = None,
        **kwargs,
    ) -> RetryResult[T]:
        """Execute function with retry and integrated monitoring.

        Args:
            func: Async function to execute
            *args: Function arguments
            operation_name: Name for logging/metrics
            **kwargs: Function keyword arguments

        Returns:
            RetryResult with outcome
        """
        manager = await self.get_manager()
        return await manager.execute_with_retry(
            func, *args, operation_name=operation_name, **kwargs
        )


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Retry Policy
    "BackoffStrategy",
    "RetryPolicy",
    "QUICK_RETRY_POLICY",
    "STANDARD_RETRY_POLICY",
    "AGGRESSIVE_RETRY_POLICY",
    # Retry Results
    "RetryOutcome",
    "RetryAttempt",
    "RetryResult",
    # Recovery Manager
    "ErrorRecoveryManager",
    "execute_with_retry_sync",
    # Decorators
    "with_retry",
    "with_retry_sync",
    # Dead Letter Queue
    "DeadLetterReason",
    "DeadLetterEntry",
    "DeadLetterQueue",
    # Checkpoints
    "Checkpoint",
    "CheckpointManager",
    # Alert Integration
    "create_alert_callback",
    "create_metrics_callback",
    "IntegratedErrorRecovery",
]
