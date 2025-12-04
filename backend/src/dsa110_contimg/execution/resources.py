"""
Resource management for execution.

This module provides resource limit enforcement for both in-process
and subprocess execution modes.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.
"""

from __future__ import annotations

import logging
import os
import resource
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    """Snapshot of current resource usage.

    Attributes:
        memory_mb: Current RSS memory in MB
        cpu_user_s: User CPU time in seconds
        cpu_system_s: System CPU time in seconds
        max_rss_mb: Maximum RSS seen
    """

    memory_mb: float = 0.0
    cpu_user_s: float = 0.0
    cpu_system_s: float = 0.0
    max_rss_mb: float = 0.0

    @classmethod
    def current(cls) -> "ResourceSnapshot":
        """Get current resource usage snapshot."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return cls(
            memory_mb=usage.ru_maxrss / 1024,  # Convert KB to MB on Linux
            cpu_user_s=usage.ru_utime,
            cpu_system_s=usage.ru_stime,
            max_rss_mb=usage.ru_maxrss / 1024,
        )


class ResourceManager:
    """Manages resource limits for execution.

    This class provides a unified interface for setting resource limits
    that works consistently across in-process and subprocess modes.

    For subprocess mode:
        - Sets hard limits via resource.setrlimit()
        - Optionally uses cgroups for stronger isolation

    For in-process mode:
        - Sets soft limits and monitors usage
        - Enforces thread pool and OMP/MKL thread limits
        - Cannot enforce hard memory limits (relies on monitoring)
    """

    def __init__(
        self,
        memory_mb: Optional[int] = None,
        cpu_seconds: Optional[int] = None,
        omp_threads: int = 4,
        mkl_threads: int = 4,
        max_workers: int = 4,
    ):
        """Initialize resource manager.

        Args:
            memory_mb: Maximum memory in MB (None = unlimited)
            cpu_seconds: Maximum CPU time in seconds (None = unlimited)
            omp_threads: Number of OpenMP threads
            mkl_threads: Number of MKL threads
            max_workers: Maximum thread pool workers
        """
        self.memory_mb = memory_mb
        self.cpu_seconds = cpu_seconds
        self.omp_threads = omp_threads
        self.mkl_threads = mkl_threads
        self.max_workers = max_workers

        self._initial_snapshot: Optional[ResourceSnapshot] = None
        self._env_backup: Dict[str, Optional[str]] = {}

    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for thread limits.

        Returns:
            Dictionary of environment variables to set
        """
        return {
            "OMP_NUM_THREADS": str(self.omp_threads),
            "MKL_NUM_THREADS": str(self.mkl_threads),
            "OPENBLAS_NUM_THREADS": str(self.omp_threads),
            "NUMEXPR_NUM_THREADS": str(self.omp_threads),
            "HDF5_USE_FILE_LOCKING": "FALSE",
        }

    def apply_subprocess_limits(self) -> None:
        """Apply resource limits for subprocess execution.

        This sets hard limits using resource.setrlimit() which
        will cause the process to be killed if exceeded.

        Should be called early in the subprocess (e.g., in preexec_fn).
        """
        try:
            # Memory limit (address space)
            if self.memory_mb is not None:
                limit_bytes = self.memory_mb * 1024 * 1024
                # Set both soft and hard limits
                resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
                logger.debug(f"Set RLIMIT_AS to {self.memory_mb} MB")

            # CPU time limit
            if self.cpu_seconds is not None:
                resource.setrlimit(
                    resource.RLIMIT_CPU, (self.cpu_seconds, self.cpu_seconds)
                )
                logger.debug(f"Set RLIMIT_CPU to {self.cpu_seconds} seconds")

        except (ValueError, OSError) as e:
            logger.warning(f"Failed to set resource limits: {e}")

    def apply_inprocess_limits(self) -> None:
        """Apply resource limits for in-process execution.

        For in-process execution, we can only set soft limits:
        - Thread pool limits
        - Environment variables for OMP/MKL
        - Monitor usage and warn (but cannot hard-kill)
        """
        # Set thread-related environment variables
        env_vars = self.get_env_vars()
        for key, value in env_vars.items():
            self._env_backup[key] = os.environ.get(key)
            os.environ[key] = value

        # Take initial snapshot for monitoring
        self._initial_snapshot = ResourceSnapshot.current()

        logger.debug(
            f"Applied in-process limits: OMP={self.omp_threads}, "
            f"MKL={self.mkl_threads}, workers={self.max_workers}"
        )

    def restore_environment(self) -> None:
        """Restore original environment variables."""
        for key, original_value in self._env_backup.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        self._env_backup.clear()

    def check_limits(self) -> Optional[str]:
        """Check if resource limits have been exceeded.

        For in-process mode, this monitors current usage against
        configured limits.

        Returns:
            Error message if limits exceeded, None otherwise
        """
        if self.memory_mb is None:
            return None

        current = ResourceSnapshot.current()
        if current.max_rss_mb > self.memory_mb:
            return (
                f"Memory limit exceeded: {current.max_rss_mb:.1f} MB > "
                f"{self.memory_mb} MB limit"
            )

        return None

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current resource usage statistics.

        Returns:
            Dictionary of resource usage metrics
        """
        current = ResourceSnapshot.current()
        stats = {
            "memory_mb": round(current.memory_mb, 1),
            "max_rss_mb": round(current.max_rss_mb, 1),
            "cpu_user_s": round(current.cpu_user_s, 2),
            "cpu_system_s": round(current.cpu_system_s, 2),
        }

        if self._initial_snapshot:
            stats["memory_delta_mb"] = round(
                current.max_rss_mb - self._initial_snapshot.max_rss_mb, 1
            )
            stats["cpu_delta_s"] = round(
                (current.cpu_user_s + current.cpu_system_s)
                - (self._initial_snapshot.cpu_user_s + self._initial_snapshot.cpu_system_s),
                2,
            )

        return stats


@contextmanager
def resource_limits(
    memory_mb: Optional[int] = None,
    omp_threads: int = 4,
    max_workers: int = 4,
    mode: str = "inprocess",
) -> Generator[ResourceManager, None, None]:
    """Context manager for applying resource limits.

    Example:
        with resource_limits(memory_mb=8000, omp_threads=4) as rm:
            # Execute conversion
            ...
            stats = rm.get_usage_stats()

    Args:
        memory_mb: Maximum memory in MB
        omp_threads: Number of OpenMP threads
        max_workers: Maximum thread pool workers
        mode: "inprocess" or "subprocess"

    Yields:
        ResourceManager instance
    """
    manager = ResourceManager(
        memory_mb=memory_mb,
        omp_threads=omp_threads,
        mkl_threads=omp_threads,
        max_workers=max_workers,
    )

    try:
        if mode == "subprocess":
            manager.apply_subprocess_limits()
        else:
            manager.apply_inprocess_limits()

        yield manager

    finally:
        if mode == "inprocess":
            manager.restore_environment()


def get_recommended_limits(available_memory_gb: float = 32.0) -> Dict[str, Any]:
    """Get recommended resource limits based on available resources.

    Args:
        available_memory_gb: Total available memory in GB

    Returns:
        Dictionary of recommended limit values
    """
    # Reserve ~25% for OS and other processes
    usable_memory_mb = int(available_memory_gb * 1024 * 0.75)

    # Get CPU count
    cpu_count = os.cpu_count() or 4

    # Recommend leaving some cores free
    recommended_threads = max(1, cpu_count - 2)

    return {
        "memory_mb": usable_memory_mb,
        "omp_threads": min(recommended_threads, 8),
        "mkl_threads": min(recommended_threads, 8),
        "max_workers": min(recommended_threads, 8),
        "cpu_seconds": None,  # Usually don't want to limit CPU time
    }
