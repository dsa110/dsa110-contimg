"""
Timeout handling for pipeline stage execution.

Provides timeout mechanisms to prevent stages from hanging indefinitely.
"""

from __future__ import annotations

import logging
import signal
import threading
import time
from contextlib import contextmanager
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when a stage execution exceeds its timeout."""
    pass


class _TimeoutHandler:
    """Internal timeout handler using signal-based timeout."""
    
    def __init__(self, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        self.timed_out = False
        self._original_handler = None
    
    def _timeout_handler(self, signum, frame):
        """Signal handler for timeout."""
        self.timed_out = True
        raise TimeoutError(f"Stage execution exceeded timeout of {self.timeout_seconds}s")
    
    def __enter__(self):
        """Enter timeout context."""
        if self.timeout_seconds <= 0:
            return self
        
        # Only use signal-based timeout on main thread (signal handlers are per-process)
        if threading.current_thread() is threading.main_thread():
            self._original_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(int(self.timeout_seconds))
        else:
            # For non-main threads, use threading-based timeout
            logger.warning(
                "Timeout requested on non-main thread. "
                "Signal-based timeout not available, using threading timeout."
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit timeout context."""
        if self.timeout_seconds <= 0:
            return False
        
        # Cancel alarm
        if threading.current_thread() is threading.main_thread():
            signal.alarm(0)
            if self._original_handler:
                signal.signal(signal.SIGALRM, self._original_handler)
        
        # If timeout occurred, don't suppress the exception
        if exc_type is TimeoutError:
            return False
        
        return False


@contextmanager
def stage_timeout(timeout_seconds: Optional[float], stage_name: str = "unknown"):
    """Context manager for stage execution timeout.
    
    Uses signal-based timeout on main thread, threading-based timeout otherwise.
    
    Args:
        timeout_seconds: Timeout in seconds (None = no timeout)
        stage_name: Name of stage for logging
        
    Yields:
        None
        
    Raises:
        TimeoutError: If execution exceeds timeout
        
    Example:
        with stage_timeout(3600.0, "conversion"):
            # Stage execution code
            perform_long_operation()
    """
    if timeout_seconds is None or timeout_seconds <= 0:
        yield
        return
    
    logger.debug(f"Setting timeout of {timeout_seconds}s for stage '{stage_name}'")
    
    # For main thread, use signal-based timeout
    if threading.current_thread() is threading.main_thread():
        try:
            with _TimeoutHandler(timeout_seconds):
                yield
        except TimeoutError as e:
            logger.error(f"Stage '{stage_name}' timed out after {timeout_seconds}s")
            raise
    else:
        # For non-main threads, use threading Timer
        timeout_occurred = threading.Event()
        
        def timeout_callback():
            timeout_occurred.set()
            logger.error(f"Stage '{stage_name}' timed out after {timeout_seconds}s")
        
        timer = threading.Timer(timeout_seconds, timeout_callback)
        timer.start()
        
        try:
            yield
            timer.cancel()
            if timeout_occurred.is_set():
                raise TimeoutError(f"Stage execution exceeded timeout of {timeout_seconds}s")
        except Exception:
            timer.cancel()
            raise


def with_timeout(timeout_seconds: Optional[float], stage_name: str = "unknown"):
    """Decorator for adding timeout to stage execution.
    
    Args:
        timeout_seconds: Timeout in seconds (None = no timeout)
        stage_name: Name of stage for logging
        
    Example:
        @with_timeout(3600.0, "conversion")
        def execute(self, context):
            # Stage execution
            pass
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            with stage_timeout(timeout_seconds, stage_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

