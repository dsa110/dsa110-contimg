"""
Retry decorator with exponential backoff for pipeline operations.

Provides automatic retry logic for transient failures in calibration,
imaging, and subprocess operations.
"""

from __future__ import annotations

import functools
import logging
import random
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Exception Types
# ============================================================================


class CalibrationError(Exception):
    """Raised when calibration fails."""

    pass


class ImagingError(Exception):
    """Raised when imaging fails."""

    pass


class ConversionError(Exception):
    """Raised when MS conversion fails."""

    pass


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, original_error: Exception, attempts: int):
        self.original_error = original_error
        self.attempts = attempts
        super().__init__(f"Retry exhausted after {attempts} attempts: {original_error}")


# Default exceptions to retry
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    CalibrationError,
    ImagingError,
    ConversionError,
    OSError,
    IOError,
    TimeoutError,
)


# ============================================================================
# Backoff Strategies
# ============================================================================


def exponential_backoff(
    attempt: int,
    base: float = 30.0,
    max_delay: float = 300.0,
    jitter: bool = True,
) -> float:
    """
    Calculate exponential backoff delay.

    Args:
        attempt: Current attempt number (0-indexed)
        base: Base delay in seconds
        max_delay: Maximum delay cap
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Delay in seconds
    """
    delay = min(base * (2**attempt), max_delay)

    if jitter:
        # Add ±25% jitter
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def linear_backoff(
    attempt: int,
    base: float = 30.0,
    max_delay: float = 300.0,
    jitter: bool = True,
) -> float:
    """
    Calculate linear backoff delay.

    Args:
        attempt: Current attempt number (0-indexed)
        base: Base delay in seconds
        max_delay: Maximum delay cap
        jitter: Add random jitter

    Returns:
        Delay in seconds
    """
    delay = min(base * (attempt + 1), max_delay)

    if jitter:
        jitter_range = delay * 0.1
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def constant_backoff(
    attempt: int,
    base: float = 30.0,
    max_delay: float = 300.0,
    jitter: bool = True,
) -> float:
    """Constant delay between retries."""
    delay = base

    if jitter:
        jitter_range = delay * 0.1
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


# ============================================================================
# Retry Decorator
# ============================================================================


def retry(
    max_attempts: int = 3,
    backoff: Callable[[int], float] = None,
    retry_on: Union[Type[Exception], Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    reraise: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        backoff: Backoff function (default: exponential with base=30, max=300)
        retry_on: Exception types to retry (default: RETRYABLE_EXCEPTIONS)
        on_retry: Callback called on each retry with (exception, attempt)
        reraise: If True, raise RetryExhaustedError; else return None

    Returns:
        Decorated function

    Example:
        @retry(max_attempts=3, retry_on=(CalibrationError, ImagingError))
        def calibrate_ms(ms_path: Path) -> bool:
            # May raise CalibrationError on transient failure
            ...

        @retry(backoff=lambda a: exponential_backoff(a, base=10, max_delay=120))
        def quick_operation():
            ...
    """
    if backoff is None:
        backoff = lambda a: exponential_backoff(a, base=30.0, max_delay=300.0)

    if retry_on is None:
        retry_on = RETRYABLE_EXCEPTIONS
    elif not isinstance(retry_on, tuple):
        retry_on = (retry_on,)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except retry_on as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        delay = backoff(attempt)

                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__}: "
                            f"{type(e).__name__}: {e}. Waiting {delay:.1f}s..."
                        )

                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: "
                            f"{type(e).__name__}: {e}"
                        )

            if reraise and last_exception:
                raise RetryExhaustedError(last_exception, max_attempts)

            return None  # type: ignore

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    backoff: Callable[[int], float] = None,
    retry_on: Union[Type[Exception], Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    reraise: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Async version of retry decorator.

    Same parameters as retry().
    """
    import asyncio

    if backoff is None:
        backoff = lambda a: exponential_backoff(a, base=30.0, max_delay=300.0)

    if retry_on is None:
        retry_on = RETRYABLE_EXCEPTIONS
    elif not isinstance(retry_on, tuple):
        retry_on = (retry_on,)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except retry_on as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        delay = backoff(attempt)

                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__}: "
                            f"{type(e).__name__}: {e}. Waiting {delay:.1f}s..."
                        )

                        if on_retry:
                            on_retry(e, attempt)

                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: "
                            f"{type(e).__name__}: {e}"
                        )

            if reraise and last_exception:
                raise RetryExhaustedError(last_exception, max_attempts)

            return None  # type: ignore

        return wrapper

    return decorator


# ============================================================================
# Convenience Functions
# ============================================================================


def retry_calibration(func: Callable[..., T]) -> Callable[..., T]:
    """
    Preset retry decorator for calibration operations.

    - 3 attempts
    - Exponential backoff: 30s, 60s, 120s (max 5 min)
    - Retries: CalibrationError, OSError, TimeoutError
    """
    return retry(
        max_attempts=3,
        backoff=lambda a: exponential_backoff(a, base=30.0, max_delay=300.0),
        retry_on=(CalibrationError, OSError, TimeoutError),
    )(func)


def retry_imaging(func: Callable[..., T]) -> Callable[..., T]:
    """
    Preset retry decorator for imaging operations.

    - 3 attempts
    - Exponential backoff: 60s, 120s, 240s (max 5 min)
    - Retries: ImagingError, OSError, TimeoutError
    """
    return retry(
        max_attempts=3,
        backoff=lambda a: exponential_backoff(a, base=60.0, max_delay=300.0),
        retry_on=(ImagingError, OSError, TimeoutError),
    )(func)


def retry_conversion(func: Callable[..., T]) -> Callable[..., T]:
    """
    Preset retry decorator for MS conversion operations.

    - 3 attempts
    - Exponential backoff: 15s, 30s, 60s (max 2 min)
    - Retries: ConversionError, OSError, IOError
    """
    return retry(
        max_attempts=3,
        backoff=lambda a: exponential_backoff(a, base=15.0, max_delay=120.0),
        retry_on=(ConversionError, OSError, IOError),
    )(func)


# ============================================================================
# Subprocess Retry Helpers
# ============================================================================


import subprocess


class SubprocessRetryError(Exception):
    """Raised when subprocess fails after retries."""

    pass


def run_with_retry(
    cmd: list,
    max_attempts: int = 3,
    backoff_base: float = 30.0,
    check: bool = True,
    **subprocess_kwargs,
) -> subprocess.CompletedProcess:
    """
    Run subprocess with retry logic.

    Args:
        cmd: Command and arguments
        max_attempts: Maximum attempts
        backoff_base: Base delay for exponential backoff
        check: Raise on non-zero exit (default True)
        **subprocess_kwargs: Additional args for subprocess.run

    Returns:
        CompletedProcess result

    Raises:
        SubprocessRetryError: If all attempts fail
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            result = subprocess.run(cmd, check=check, **subprocess_kwargs)
            return result

        except subprocess.CalledProcessError as e:
            last_error = e

            if attempt < max_attempts - 1:
                delay = exponential_backoff(attempt, base=backoff_base)
                logger.warning(
                    f"Subprocess retry {attempt + 1}/{max_attempts}: "
                    f"exit code {e.returncode}. Waiting {delay:.1f}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"Subprocess failed after {max_attempts} attempts: {cmd}")

    raise SubprocessRetryError(
        f"Command failed after {max_attempts} attempts: {cmd}"
    ) from last_error
