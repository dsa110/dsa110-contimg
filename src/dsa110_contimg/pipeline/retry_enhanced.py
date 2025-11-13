"""Enhanced retry logic with tenacity integration.

Provides robust retry functionality with exponential backoff,
custom retry conditions, and comprehensive error handling.
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar, Any, Optional, List, Type

T = TypeVar('T')

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        retry_if_exception,
        RetryError
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    RetryError = Exception


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        retryable_exceptions: List of exception types to retry on
        on_retry: Callback function called on each retry
    
    Usage:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def my_function():
            # Function implementation
            pass
    """
    if TENACITY_AVAILABLE:
        # Use tenacity library
        stop = stop_after_attempt(max_attempts)
        wait = wait_exponential(
            multiplier=initial_delay,
            min=initial_delay,
            max=max_delay
        )
        
        if retryable_exceptions:
            retry_condition = retry_if_exception_type(tuple(retryable_exceptions))
        else:
            retry_condition = retry_if_exception(lambda e: True)
        
        return retry(
            stop=stop,
            wait=wait,
            retry=retry_condition,
            reraise=True
        )
    else:
        # Simple retry implementation
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args: Any, **kwargs: Any) -> T:
                last_exception: Optional[Exception] = None
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        # Check if exception is retryable
                        if retryable_exceptions and not isinstance(e, tuple(retryable_exceptions)):
                            raise
                        
                        # Check if we should retry
                        if attempt >= max_attempts:
                            raise
                        
                        # Calculate delay
                        delay = min(
                            initial_delay * (exponential_base ** (attempt - 1)),
                            max_delay
                        )
                        
                        # Call retry callback
                        if on_retry:
                            try:
                                on_retry(e, attempt)
                            except Exception:
                                pass  # Don't fail on callback error
                        
                        time.sleep(delay)
                
                # Should never reach here, but just in case
                if last_exception:
                    raise last_exception
                raise RuntimeError("Retry failed without exception")
            
            return wrapper
        
        return decorator


def retry_on_transient_error(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for transient errors (IOError, RuntimeError, ConnectionError)."""
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
        retryable_exceptions=[IOError, RuntimeError, ConnectionError, OSError]
    )


def retry_on_database_error(
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 10.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for database errors."""
    import sqlite3
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
        retryable_exceptions=[sqlite3.OperationalError, sqlite3.DatabaseError]
    )


# Pre-configured retry decorators

retry_ese_detection = retry_on_transient_error(max_attempts=3, initial_delay=2.0)
retry_calibration_solve = retry_on_transient_error(max_attempts=2, initial_delay=5.0, max_delay=300.0)
retry_photometry = retry_on_transient_error(max_attempts=3, initial_delay=1.0)
retry_database = retry_on_database_error(max_attempts=5, initial_delay=0.5)

