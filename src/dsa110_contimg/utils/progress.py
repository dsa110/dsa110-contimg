"""
Progress indicators for CLI operations using tqdm.

This module provides progress bar utilities that integrate with the CLI helpers
and respect the --disable-progress and --quiet flags.

Following expert recommendations: Use tqdm library (industry standard) instead
of custom solutions.
"""

from contextlib import contextmanager
from typing import Optional, Iterator, Any
import sys


try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Fallback: create a no-op tqdm-like object
    class tqdm:  # type: ignore
        def __init__(self, *args, **kwargs):
            self.total = kwargs.get('total', 0)
            self.n = 0
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def update(self, n=1):
            self.n += n
        
        def __iter__(self):
            return iter([])


def get_progress_bar(iterable: Optional[Any] = None,
                     total: Optional[int] = None,
                     desc: str = "Processing",
                     disable: bool = False,
                     mininterval: float = 0.1) -> Iterator:
    """
    Get a progress bar using tqdm, with automatic disable if stdout is not a TTY.
    
    Args:
        iterable: Iterable to wrap (optional)
        total: Total number of items (if iterable doesn't have __len__)
        desc: Description for the progress bar
        disable: Force disable progress bar
        mininterval: Minimum time (seconds) between updates
    
    Returns:
        tqdm progress bar iterator
    
    Example:
        for item in get_progress_bar(items, desc="Processing files"):
            process(item)
    """
    if not TQDM_AVAILABLE:
        # Fallback: return iterable as-is
        if iterable is not None:
            return iter(iterable)
        return iter(range(total or 0))
    
    # Auto-disable if not TTY (useful for scripts/automation)
    if not sys.stdout.isatty():
        disable = True
    
    return tqdm(
        iterable=iterable,
        total=total,
        desc=desc,
        disable=disable,
        mininterval=mininterval,
        file=sys.stderr,  # Use stderr so it doesn't interfere with stdout
    )


def progress_context(total: Optional[int] = None,
                    desc: str = "Processing",
                    disable: bool = False,
                    mininterval: float = 0.1):
    """
    Context manager for progress bars.
    
    Args:
        total: Total number of items to process
        desc: Description for the progress bar
        disable: Force disable progress bar
        mininterval: Minimum time (seconds) between updates
    
    Returns:
        Context manager that yields a progress bar
    
    Example:
        with progress_context(total=100, desc="Processing") as pbar:
            for i in range(100):
                process_item(i)
                pbar.update(1)
    """
    if not TQDM_AVAILABLE:
        # Fallback: create dummy context manager
        class DummyProgress:
            def update(self, n=1):
                pass
        
        @contextmanager
        def dummy_context():
            yield DummyProgress()
        
        return dummy_context()
    
    # Auto-disable if not TTY
    if not sys.stdout.isatty():
        disable = True
    
    return tqdm(
        total=total,
        desc=desc,
        disable=disable,
        mininterval=mininterval,
        file=sys.stderr,
    )


def should_disable_progress(args=None, env_var: Optional[str] = None) -> bool:
    """
    Determine if progress should be disabled based on args or environment.
    
    Args:
        args: Parsed arguments object (optional, checks disable_progress/quiet flags)
        env_var: Environment variable name to check (optional)
    
    Returns:
        True if progress should be disabled, False otherwise
    """
    # Check environment variable
    if env_var:
        import os
        if os.getenv(env_var, "").lower() in ("1", "true", "yes"):
            return True
    
    # Check args
    if args:
        if getattr(args, 'disable_progress', False) or getattr(args, 'quiet', False):
            return True
    
    # Check if stdout is not a TTY
    if not sys.stdout.isatty():
        return True
    
    return False

