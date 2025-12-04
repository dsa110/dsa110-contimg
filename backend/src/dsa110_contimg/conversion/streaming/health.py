"""
Health check and metrics infrastructure for the streaming pipeline.

This module provides production monitoring capabilities:
- Health check endpoints for liveness/readiness probes
- Metrics collection for Prometheus
- Structured logging helpers
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Result of a health check."""

    name: str
    status: HealthStatus
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)


@dataclass
class PipelineMetrics:
    """Collected pipeline metrics."""

    # Counters
    groups_processed: int = 0
    groups_failed: int = 0
    groups_retried: int = 0

    # Gauges
    queue_pending: int = 0
    queue_in_progress: int = 0
    queue_completed: int = 0

    # Timing (in seconds)
    last_processing_time: float = 0.0
    avg_processing_time: float = 0.0
    last_group_completed_at: Optional[float] = None

    # Disk space (in GB)
    output_disk_free_gb: float = 0.0
    scratch_disk_free_gb: float = 0.0

    # Status
    worker_status: str = "unknown"
    watcher_status: str = "unknown"
    last_error: Optional[str] = None
    last_error_at: Optional[float] = None


class HealthChecker:
    """Health check manager for the streaming pipeline.

    Provides centralized health monitoring with pluggable checks
    for different components (queue, worker, watcher, disk, etc.).

    Example:
        >>> checker = HealthChecker()
        >>> checker.register_check("queue", check_queue_health)
        >>> checker.register_check("disk", check_disk_health)
        >>> result = checker.run_all()
        >>> print(result.overall_status)
    """

    def __init__(self) -> None:
        """Initialize the health checker."""
        self._checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._last_results: Dict[str, HealthCheck] = {}
        self._lock = threading.Lock()

    def register_check(
        self,
        name: str,
        check_fn: Callable[[], HealthCheck],
    ) -> None:
        """Register a health check function.

        Args:
            name: Unique name for the check
            check_fn: Callable that returns a HealthCheck result
        """
        with self._lock:
            self._checks[name] = check_fn

    def unregister_check(self, name: str) -> None:
        """Unregister a health check.

        Args:
            name: Name of check to remove
        """
        with self._lock:
            self._checks.pop(name, None)
            self._last_results.pop(name, None)

    def run_check(self, name: str) -> Optional[HealthCheck]:
        """Run a single health check.

        Args:
            name: Name of check to run

        Returns:
            HealthCheck result, or None if check not found
        """
        with self._lock:
            check_fn = self._checks.get(name)
            if check_fn is None:
                return None

        try:
            result = check_fn()
        except Exception as e:
            result = HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check raised exception: {e}",
            )

        with self._lock:
            self._last_results[name] = result

        return result

    def run_all(self) -> "AggregatedHealth":
        """Run all registered health checks.

        Returns:
            AggregatedHealth with individual results and overall status
        """
        results: Dict[str, HealthCheck] = {}

        with self._lock:
            check_names = list(self._checks.keys())

        for name in check_names:
            result = self.run_check(name)
            if result is not None:
                results[name] = result

        return AggregatedHealth(checks=results)

    def get_last_result(self, name: str) -> Optional[HealthCheck]:
        """Get cached result of a health check.

        Args:
            name: Name of check

        Returns:
            Last HealthCheck result, or None
        """
        with self._lock:
            return self._last_results.get(name)


@dataclass
class AggregatedHealth:
    """Aggregated health check results."""

    checks: Dict[str, HealthCheck] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)

    @property
    def overall_status(self) -> HealthStatus:
        """Compute overall health status from individual checks."""
        if not self.checks:
            return HealthStatus.UNKNOWN

        statuses = [c.status for c in self.checks.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN

    @property
    def is_healthy(self) -> bool:
        """Check if overall status is healthy."""
        return self.overall_status == HealthStatus.HEALTHY

    @property
    def is_ready(self) -> bool:
        """Check if pipeline is ready to process (healthy or degraded)."""
        return self.overall_status in (
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall_status": self.overall_status.value,
            "is_healthy": self.is_healthy,
            "is_ready": self.is_ready,
            "checked_at": datetime.fromtimestamp(self.checked_at).isoformat(),
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "details": check.details,
                }
                for name, check in self.checks.items()
            },
        }


class MetricsCollector:
    """Metrics collection for the streaming pipeline.

    Collects and exposes metrics for monitoring systems.
    Thread-safe for concurrent updates.

    Example:
        >>> collector = MetricsCollector()
        >>> collector.increment_processed()
        >>> collector.record_processing_time(15.5)
        >>> metrics = collector.get_metrics()
    """

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self._metrics = PipelineMetrics()
        self._lock = threading.Lock()
        self._processing_times: List[float] = []
        self._max_history = 100

    def increment_processed(self) -> None:
        """Increment the count of successfully processed groups."""
        with self._lock:
            self._metrics.groups_processed += 1
            self._metrics.last_group_completed_at = time.time()

    def increment_failed(self) -> None:
        """Increment the count of failed groups."""
        with self._lock:
            self._metrics.groups_failed += 1

    def increment_retried(self) -> None:
        """Increment the count of retried groups."""
        with self._lock:
            self._metrics.groups_retried += 1

    def record_processing_time(self, seconds: float) -> None:
        """Record processing time for a group.

        Args:
            seconds: Processing time in seconds
        """
        with self._lock:
            self._metrics.last_processing_time = seconds
            self._processing_times.append(seconds)

            # Keep only recent history
            if len(self._processing_times) > self._max_history:
                self._processing_times = self._processing_times[-self._max_history:]

            # Update average
            if self._processing_times:
                self._metrics.avg_processing_time = sum(self._processing_times) / len(
                    self._processing_times
                )

    def update_queue_counts(
        self,
        pending: int = 0,
        in_progress: int = 0,
        completed: int = 0,
    ) -> None:
        """Update queue count metrics.

        Args:
            pending: Number of pending groups
            in_progress: Number of groups being processed
            completed: Number of completed groups
        """
        with self._lock:
            self._metrics.queue_pending = pending
            self._metrics.queue_in_progress = in_progress
            self._metrics.queue_completed = completed

    def update_disk_space(
        self,
        output_free_gb: float,
        scratch_free_gb: float,
    ) -> None:
        """Update disk space metrics.

        Args:
            output_free_gb: Free space in output directory (GB)
            scratch_free_gb: Free space in scratch directory (GB)
        """
        with self._lock:
            self._metrics.output_disk_free_gb = output_free_gb
            self._metrics.scratch_disk_free_gb = scratch_free_gb

    def set_worker_status(self, status: str) -> None:
        """Set worker status.

        Args:
            status: Worker status string (running, stopped, error)
        """
        with self._lock:
            self._metrics.worker_status = status

    def set_watcher_status(self, status: str) -> None:
        """Set watcher status.

        Args:
            status: Watcher status string (running, stopped, error)
        """
        with self._lock:
            self._metrics.watcher_status = status

    def record_error(self, error: str) -> None:
        """Record an error.

        Args:
            error: Error message
        """
        with self._lock:
            self._metrics.last_error = error
            self._metrics.last_error_at = time.time()

    def get_metrics(self) -> PipelineMetrics:
        """Get current metrics snapshot.

        Returns:
            Copy of current metrics
        """
        with self._lock:
            # Return a copy to prevent external modification
            return PipelineMetrics(
                groups_processed=self._metrics.groups_processed,
                groups_failed=self._metrics.groups_failed,
                groups_retried=self._metrics.groups_retried,
                queue_pending=self._metrics.queue_pending,
                queue_in_progress=self._metrics.queue_in_progress,
                queue_completed=self._metrics.queue_completed,
                last_processing_time=self._metrics.last_processing_time,
                avg_processing_time=self._metrics.avg_processing_time,
                last_group_completed_at=self._metrics.last_group_completed_at,
                output_disk_free_gb=self._metrics.output_disk_free_gb,
                scratch_disk_free_gb=self._metrics.scratch_disk_free_gb,
                worker_status=self._metrics.worker_status,
                watcher_status=self._metrics.watcher_status,
                last_error=self._metrics.last_error,
                last_error_at=self._metrics.last_error_at,
            )

    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format.

        Returns:
            Prometheus-compatible metrics string
        """
        metrics = self.get_metrics()
        lines = [
            "# HELP dsa110_streaming_groups_processed_total Total groups processed",
            "# TYPE dsa110_streaming_groups_processed_total counter",
            f"dsa110_streaming_groups_processed_total {metrics.groups_processed}",
            "",
            "# HELP dsa110_streaming_groups_failed_total Total groups failed",
            "# TYPE dsa110_streaming_groups_failed_total counter",
            f"dsa110_streaming_groups_failed_total {metrics.groups_failed}",
            "",
            "# HELP dsa110_streaming_queue_pending Number of pending groups",
            "# TYPE dsa110_streaming_queue_pending gauge",
            f"dsa110_streaming_queue_pending {metrics.queue_pending}",
            "",
            "# HELP dsa110_streaming_processing_time_seconds Last processing time",
            "# TYPE dsa110_streaming_processing_time_seconds gauge",
            f"dsa110_streaming_processing_time_seconds {metrics.last_processing_time:.3f}",
            "",
            "# HELP dsa110_streaming_disk_free_gb Free disk space in GB",
            "# TYPE dsa110_streaming_disk_free_gb gauge",
            f'dsa110_streaming_disk_free_gb{{path="output"}} {metrics.output_disk_free_gb:.2f}',
            f'dsa110_streaming_disk_free_gb{{path="scratch"}} {metrics.scratch_disk_free_gb:.2f}',
        ]
        return "\n".join(lines)


def get_disk_free_gb(path: Path) -> float:
    """Get free disk space in gigabytes.

    Args:
        path: Path to check

    Returns:
        Free space in GB
    """
    import shutil

    try:
        total, used, free = shutil.disk_usage(path)
        return free / (1024**3)
    except OSError:
        return 0.0


# Global instances for singleton pattern
_health_checker: Optional[HealthChecker] = None
_metrics_collector: Optional[MetricsCollector] = None
_instance_lock = threading.Lock()


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance.

    Returns:
        Singleton HealthChecker
    """
    global _health_checker
    with _instance_lock:
        if _health_checker is None:
            _health_checker = HealthChecker()
        return _health_checker


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        Singleton MetricsCollector
    """
    global _metrics_collector
    with _instance_lock:
        if _metrics_collector is None:
            _metrics_collector = MetricsCollector()
        return _metrics_collector
