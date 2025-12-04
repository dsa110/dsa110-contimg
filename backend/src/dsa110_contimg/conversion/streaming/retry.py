"""
Retry utilities for the streaming pipeline.

This module provides production-grade retry logic with:
- Exponential backoff with jitter
- Configurable retry conditions
- Structured logging of retry attempts
"""

from __future__ import annotations

import functools
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from .exceptions import StreamingError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay_s: float = 1.0
    max_delay_s: float = 60.0
    exponential_base: float = 2.0
    jitter_factor: float = 0.1
    retryable_exceptions: Tuple[Type[Exception], ...] = (StreamingError,)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an exception should be retried.

        Args:
            exception: The exception that was raised
            attempt: Current attempt number (1-indexed)

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_attempts:
            return False

        # Check if exception is retryable type
        if not isinstance(exception, self.retryable_exceptions):
            return False

        # Check if StreamingError is marked as retryable
        if isinstance(exception, StreamingError):
            return exception.retryable

        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay before next retry attempt.

        Uses exponential backoff with jitter to prevent thundering herd.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds before next attempt
        """
        # Exponential backoff
        delay = self.initial_delay_s * (self.exponential_base ** (attempt - 1))

        # Cap at max delay
        delay = min(delay, self.max_delay_s)

        # Add jitter (±jitter_factor)
        jitter = delay * self.jitter_factor * (2 * random.random() - 1)
        delay += jitter

        return max(0, delay)


# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig()


def retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry a function on failure.

    Args:
        config: Retry configuration (uses default if not provided)
        on_retry: Optional callback called on each retry with (exception, attempt)

    Returns:
        Decorated function

    Example:
        >>> @retry(RetryConfig(max_attempts=3))
        ... def fetch_data():
        ...     return requests.get(url).json()
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not config.should_retry(e, attempt):
                        raise

                    delay = config.get_delay(attempt)
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                        attempt,
                        config.max_attempts,
                        func.__name__,
                        str(e),
                        delay,
                    )

                    if on_retry is not None:
                        try:
                            on_retry(e, attempt)
                        except Exception:
                            pass

                    time.sleep(delay)

            # Should not reach here, but satisfy type checker
            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Retry loop exited without result or exception")

        return wrapper

    return decorator


def retry_with_result(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    *args: Any,
    **kwargs: Any,
) -> Tuple[Optional[T], Optional[Exception], int]:
    """Execute a function with retry, returning result and metadata.

    Unlike the @retry decorator, this function returns success/failure
    information without raising exceptions.

    Args:
        func: Function to execute
        config: Retry configuration
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Tuple of (result, exception, attempts)
        - result is None if all attempts failed
        - exception is None if succeeded
        - attempts is the number of attempts made

    Example:
        >>> result, error, attempts = retry_with_result(
        ...     process_group,
        ...     RetryConfig(max_attempts=3),
        ...     group_id="2025-10-02T00:12:00"
        ... )
        >>> if error is not None:
        ...     logger.error("Failed after %d attempts: %s", attempts, error)
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG

    last_exception: Optional[Exception] = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            return result, None, attempt
        except Exception as e:
            last_exception = e

            if not config.should_retry(e, attempt):
                return None, e, attempt

            delay = config.get_delay(attempt)
            logger.warning(
                "Attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                attempt,
                config.max_attempts,
                func.__name__,
                str(e),
                delay,
            )
            time.sleep(delay)

    return None, last_exception, config.max_attempts


class RetryContext:
    """Context manager for retry logic with cleanup.

    Provides a more flexible retry pattern that allows custom
    cleanup between attempts.

    Example:
        >>> with RetryContext(max_attempts=3) as ctx:
        ...     while ctx.should_continue():
        ...         try:
        ...             result = process_data()
        ...             ctx.success(result)
        ...         except TransientError as e:
        ...             ctx.record_failure(e)
        ...             cleanup_partial_work()
        >>> if ctx.succeeded:
        ...     print(f"Result: {ctx.result}")
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_s: float = 1.0,
        max_delay_s: float = 60.0,
    ) -> None:
        """Initialize retry context.

        Args:
            max_attempts: Maximum number of attempts
            initial_delay_s: Initial delay between retries
            max_delay_s: Maximum delay between retries
        """
        self.config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay_s=initial_delay_s,
            max_delay_s=max_delay_s,
        )
        self._attempt = 0
        self._succeeded = False
        self._result: Any = None
        self._last_exception: Optional[Exception] = None

    def __enter__(self) -> "RetryContext":
        """Enter the context."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit the context."""
        # Don't suppress exceptions
        return False

    def should_continue(self) -> bool:
        """Check if another attempt should be made.

        Returns:
            True if should continue, False otherwise
        """
        if self._succeeded:
            return False
        if self._attempt >= self.config.max_attempts:
            return False
        return True

    def record_failure(self, exception: Exception) -> None:
        """Record a failed attempt.

        Args:
            exception: The exception that caused the failure
        """
        self._attempt += 1
        self._last_exception = exception

        if self.should_continue():
            delay = self.config.get_delay(self._attempt)
            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %.1fs",
                self._attempt,
                self.config.max_attempts,
                str(exception),
                delay,
            )
            time.sleep(delay)

    def success(self, result: Any = None) -> None:
        """Mark the operation as successful.

        Args:
            result: Optional result value
        """
        self._attempt += 1
        self._succeeded = True
        self._result = result

    @property
    def succeeded(self) -> bool:
        """Check if operation succeeded."""
        return self._succeeded

    @property
    def result(self) -> Any:
        """Get the result value."""
        return self._result

    @property
    def last_exception(self) -> Optional[Exception]:
        """Get the last exception."""
        return self._last_exception

    @property
    def attempts(self) -> int:
        """Get the number of attempts made."""
        return self._attempt
