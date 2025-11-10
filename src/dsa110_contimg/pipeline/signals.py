"""
Signal handling for graceful pipeline shutdown.

Provides signal handlers to allow pipelines to clean up gracefully
when interrupted (SIGTERM, SIGINT).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
import signal
import sys
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """Manages graceful shutdown for pipeline execution.

    Registers signal handlers for SIGTERM and SIGINT to allow
    pipelines to clean up resources before exiting.
    """

    def __init__(self, cleanup_callback: Optional[Callable[[], None]] = None):
        """Initialize graceful shutdown handler.

        Args:
            cleanup_callback: Optional callback to execute during shutdown
        """
        self.cleanup_callback = cleanup_callback
        self.shutdown_requested = False
        self._original_handlers = {}

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.warning(f"Received {signal_name}, initiating graceful shutdown...")

        self.shutdown_requested = True

        # Execute cleanup callback if provided
        if self.cleanup_callback:
            try:
                self.cleanup_callback()
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}", exc_info=True)

        # Exit gracefully
        logger.info("Graceful shutdown complete")
        sys.exit(130 if signum == signal.SIGINT else 0)

    def register(self):
        """Register signal handlers."""
        if sys.platform == "win32":
            # Windows doesn't support SIGTERM
            signals = [signal.SIGINT]
        else:
            signals = [signal.SIGTERM, signal.SIGINT]

        for sig in signals:
            try:
                self._original_handlers[sig] = signal.signal(sig, self._signal_handler)
                logger.debug(f"Registered handler for {signal.Signals(sig).name}")
            except (ValueError, OSError) as e:
                logger.warning(
                    f"Could not register handler for {signal.Signals(sig).name}: {e}"
                )

    def unregister(self):
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            try:
                signal.signal(sig, handler)
                logger.debug(f"Restored handler for {signal.Signals(sig).name}")
            except (ValueError, OSError) as e:
                logger.warning(
                    f"Could not restore handler for {signal.Signals(sig).name}: {e}"
                )

        self._original_handlers.clear()

    def __enter__(self):
        """Enter context manager."""
        self.register()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.unregister()
        return False


@contextmanager
def graceful_shutdown(cleanup_callback: Optional[Callable[[], None]] = None):
    """Context manager for graceful shutdown handling.

    Args:
        cleanup_callback: Optional callback to execute during shutdown

    Example:
        def cleanup():
            # Cleanup resources
            pass

        with graceful_shutdown(cleanup):
            # Long-running pipeline code
            run_pipeline()
    """
    handler = GracefulShutdown(cleanup_callback)
    try:
        handler.register()
        yield handler
    finally:
        handler.unregister()
