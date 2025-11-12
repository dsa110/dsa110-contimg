"""
Parallel execution utilities for QA visualization framework.

Provides executor for parallel processing of file operations,
similar to RadioPadre's executor functionality.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from .settings_manager import settings


_executor = None
_executor_ncpu_settings = None


def ncpu() -> int:
    """
    Get number of CPU cores to use.

    Returns:
        Number of CPU cores (respects max_ncpu setting)
    """
    ncpu_val = settings.gen.ncpu
    if ncpu_val < 1:
        try:
            ncpu_val = len(os.sched_getaffinity(0))
        except AttributeError:
            # Fallback for systems without sched_getaffinity
            ncpu_val = os.cpu_count() or 1

        if settings.gen.max_ncpu and settings.gen.max_ncpu < ncpu_val:
            ncpu_val = settings.gen.max_ncpu

        ncpu_val = max(ncpu_val, 1)

    return ncpu_val


def executor() -> ThreadPoolExecutor:
    """
    Get or create thread pool executor.

    Returns:
        ThreadPoolExecutor instance
    """
    global _executor, _executor_ncpu_settings

    ncpu_settings = (settings.gen.ncpu, settings.gen.max_ncpu)

    # Recreate executor if settings changed
    if _executor is not None and ncpu_settings != _executor_ncpu_settings:
        _executor.shutdown(wait=True)
        _executor = None

    if _executor is None:
        nw = ncpu()
        _executor_ncpu_settings = ncpu_settings
        _executor = ThreadPoolExecutor(max_workers=nw)

    return _executor


def shutdown_executor():
    """Shutdown the global executor."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None
