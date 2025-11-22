"""
Monitoring and metrics collection for Absurd workflow manager.

Provides real-time metrics, health checks, and observability.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from dsa110_contimg.absurd import AbsurdClient

logger = logging.getLogger(__name__)


@dataclass
class TaskMetrics:
    """Metrics for task execution."""

    total_spawned: int = 0
    total_claimed: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    total_timed_out: int = 0

    current_pending: int = 0
    current_claimed: int = 0

    avg_wait_time_sec: float = 0.0
    avg_execution_time_sec: float = 0.0

    p50_wait_time_sec: float = 0.0
    p95_wait_time_sec: float = 0.0
    p99_wait_time_sec: float = 0.0

    p50_execution_time_sec: float = 0.0
    p95_execution_time_sec: float = 0.0
    p99_execution_time_sec: float = 0.0

    throughput_1min: float = 0.0  # tasks/sec
    throughput_5min: float = 0.0
    throughput_15min: float = 0.0

    success_rate_1min: float = 1.0
    success_rate_5min: float = 1.0
    success_rate_15min: float = 1.0

    error_rate_1min: float = 0.0
    error_rate_5min: float = 0.0
    error_rate_15min: float = 0.0


@dataclass
class WorkerMetrics:
    """Metrics for worker pool."""

    total_workers: int = 0
    active_workers: int = 0
    idle_workers: int = 0
    crashed_workers: int = 0

    tasks_per_worker: Dict[str, int] = None
    avg_tasks_per_worker: float = 0.0

    worker_uptime_sec: Dict[str, float] = None
    avg_worker_uptime_sec: float = 0.0


@dataclass
class QueueHealth:
    """Queue health status."""

    status: str  # "healthy", "degraded", "critical", "down"
    message: str

    queue_depth: int
    age_oldest_pending_sec: float

    database_available: bool
    database_latency_ms: float

    worker_pool_healthy: bool
    worker_pool_message: str

    last_task_completed_sec_ago: float

    alerts: List[str]
    warnings: List[str]


class AbsurdMonitor:
    """Monitor for Absurd workflow manager."""

    def __init__(self, client: AbsurdClient, queue_name: str):
        self.client = client
        self.queue_name = queue_name

        # Time-series data
        self.completed_1min = deque(maxlen=60)  # timestamps
        self.completed_5min = deque(maxlen=300)
        self.completed_15min = deque(maxlen=900)

        self.failed_1min = deque(maxlen=60)
        self.failed_5min = deque(maxlen=300)
        self.failed_15min = deque(maxlen=900)

        # Task timing data
        self.wait_times = deque(maxlen=1000)
        self.execution_times = deque(maxlen=1000)

        # Worker tracking
        self.worker_last_seen: Dict[str, float] = {}
        self.worker_task_counts: Dict[str, int] = defaultdict(int)
        self.worker_start_times: Dict[str, float] = {}

        # Health check cache
        self._last_health_check: Optional[QueueHealth] = None
        self._last_health_check_time: float = 0
        self._health_check_cache_sec: float = 10

    async def collect_metrics(self) -> TaskMetrics:
        """Collect current task metrics."""
        # Get queue stats
        stats = await self.client.get_queue_stats(self.queue_name)

        # Get recent tasks for timing analysis
        recent_tasks = await self.client.list_tasks(queue_name=self.queue_name, limit=100)

        # Calculate wait times and execution times
        wait_times = []
        execution_times = []

        for task in recent_tasks:
            if task["claimed_at"] and task["created_at"]:
                wait_time = (
                    datetime.fromisoformat(task["claimed_at"]).timestamp()
                    - datetime.fromisoformat(task["created_at"]).timestamp()
                )
                wait_times.append(wait_time)

            if task["completed_at"] and task["claimed_at"]:
                execution_time = (
                    datetime.fromisoformat(task["completed_at"]).timestamp()
                    - datetime.fromisoformat(task["claimed_at"]).timestamp()
                )
                execution_times.append(execution_time)

        # Update time series
        now = time.time()
        if wait_times:
            self.wait_times.extend(wait_times)
        if execution_times:
            self.execution_times.extend(execution_times)

        # Calculate throughput
        cutoff_1min = now - 60
        cutoff_5min = now - 300
        cutoff_15min = now - 900

        completed_1min = sum(1 for ts in self.completed_1min if ts > cutoff_1min)
        completed_5min = sum(1 for ts in self.completed_5min if ts > cutoff_5min)
        completed_15min = sum(1 for ts in self.completed_15min if ts > cutoff_15min)

        failed_1min = sum(1 for ts in self.failed_1min if ts > cutoff_1min)
        failed_5min = sum(1 for ts in self.failed_5min if ts > cutoff_5min)
        failed_15min = sum(1 for ts in self.failed_15min if ts > cutoff_15min)

        # Calculate rates
        throughput_1min = completed_1min / 60
        throughput_5min = completed_5min / 300
        throughput_15min = completed_15min / 900

        success_rate_1min = (
            completed_1min / (completed_1min + failed_1min)
            if (completed_1min + failed_1min) > 0
            else 1.0
        )
        success_rate_5min = (
            completed_5min / (completed_5min + failed_5min)
            if (completed_5min + failed_5min) > 0
            else 1.0
        )
        success_rate_15min = (
            completed_15min / (completed_15min + failed_15min)
            if (completed_15min + failed_15min) > 0
            else 1.0
        )

        error_rate_1min = failed_1min / 60
        error_rate_5min = failed_5min / 300
        error_rate_15min = failed_15min / 900

        # Calculate percentiles
        def percentile(data, p):
            if not data:
                return 0.0
            sorted_data = sorted(data)
            index = int(len(sorted_data) * p / 100)
            return sorted_data[index]

        metrics = TaskMetrics(
            total_spawned=stats["total"],
            total_completed=stats["completed"],
            total_failed=stats["failed"],
            total_cancelled=stats["cancelled"],
            current_pending=stats["pending"],
            current_claimed=stats["claimed"],
            avg_wait_time_sec=sum(wait_times) / len(wait_times) if wait_times else 0,
            avg_execution_time_sec=(
                sum(execution_times) / len(execution_times) if execution_times else 0
            ),
            p50_wait_time_sec=percentile(wait_times, 50),
            p95_wait_time_sec=percentile(wait_times, 95),
            p99_wait_time_sec=percentile(wait_times, 99),
            p50_execution_time_sec=percentile(execution_times, 50),
            p95_execution_time_sec=percentile(execution_times, 95),
            p99_execution_time_sec=percentile(execution_times, 99),
            throughput_1min=throughput_1min,
            throughput_5min=throughput_5min,
            throughput_15min=throughput_15min,
            success_rate_1min=success_rate_1min,
            success_rate_5min=success_rate_5min,
            success_rate_15min=success_rate_15min,
            error_rate_1min=error_rate_1min,
            error_rate_5min=error_rate_5min,
            error_rate_15min=error_rate_15min,
        )

        return metrics

    async def collect_worker_metrics(self) -> WorkerMetrics:
        """Collect worker pool metrics."""
        # TODO: Implement worker tracking via heartbeats or registry
        # For now, return basic metrics

        now = time.time()

        # Prune stale workers (not seen in 60 seconds)
        stale_workers = [
            worker_id
            for worker_id, last_seen in self.worker_last_seen.items()
            if now - last_seen > 60
        ]
        for worker_id in stale_workers:
            del self.worker_last_seen[worker_id]
            if worker_id in self.worker_task_counts:
                del self.worker_task_counts[worker_id]
            if worker_id in self.worker_start_times:
                del self.worker_start_times[worker_id]

        total_workers = len(self.worker_last_seen)
        active_workers = sum(
            1 for last_seen in self.worker_last_seen.values() if now - last_seen < 10
        )
        idle_workers = total_workers - active_workers

        avg_tasks_per_worker = (
            sum(self.worker_task_counts.values()) / total_workers if total_workers > 0 else 0
        )

        worker_uptimes = {
            worker_id: now - start_time for worker_id, start_time in self.worker_start_times.items()
        }

        avg_uptime = sum(worker_uptimes.values()) / len(worker_uptimes) if worker_uptimes else 0

        return WorkerMetrics(
            total_workers=total_workers,
            active_workers=active_workers,
            idle_workers=idle_workers,
            crashed_workers=0,  # TODO: Track crashes
            tasks_per_worker=dict(self.worker_task_counts),
            avg_tasks_per_worker=avg_tasks_per_worker,
            worker_uptime_sec=worker_uptimes,
            avg_worker_uptime_sec=avg_uptime,
        )

    async def check_health(self) -> QueueHealth:
        """Perform comprehensive health check."""
        # Check cache
        now = time.time()
        if (
            self._last_health_check
            and now - self._last_health_check_time < self._health_check_cache_sec
        ):
            return self._last_health_check

        alerts = []
        warnings = []

        # Check database connectivity
        db_start = time.time()
        try:
            stats = await self.client.get_queue_stats(self.queue_name)
            database_available = True
            database_latency_ms = (time.time() - db_start) * 1000
        except Exception as e:
            database_available = False
            database_latency_ms = -1
            alerts.append(f"Database unavailable: {e}")

        if not database_available:
            health = QueueHealth(
                status="down",
                message="Database connection failed",
                queue_depth=0,
                age_oldest_pending_sec=0,
                database_available=False,
                database_latency_ms=database_latency_ms,
                worker_pool_healthy=False,
                worker_pool_message="Cannot determine (database down)",
                last_task_completed_sec_ago=-1,
                alerts=alerts,
                warnings=warnings,
            )
            self._last_health_check = health
            self._last_health_check_time = now
            return health

        # Check queue depth
        queue_depth = stats["pending"] + stats["claimed"]

        if queue_depth > 1000:
            alerts.append(f"Queue depth critical: {queue_depth} tasks")
        elif queue_depth > 500:
            warnings.append(f"Queue depth high: {queue_depth} tasks")

        # Check oldest pending task
        pending_tasks = await self.client.list_tasks(
            queue_name=self.queue_name, status="pending", limit=1
        )

        age_oldest_pending_sec = 0
        if pending_tasks:
            oldest = pending_tasks[0]
            created_at = datetime.fromisoformat(oldest["created_at"]).timestamp()
            age_oldest_pending_sec = now - created_at

            if age_oldest_pending_sec > 3600:  # 1 hour
                alerts.append(f"Task pending for {age_oldest_pending_sec/3600:.1f} hours")
            elif age_oldest_pending_sec > 600:  # 10 minutes
                warnings.append(f"Task pending for {age_oldest_pending_sec/60:.1f} minutes")

        # Check last completed task
        completed_tasks = await self.client.list_tasks(
            queue_name=self.queue_name, status="completed", limit=1
        )

        last_task_completed_sec_ago = -1
        if completed_tasks:
            last = completed_tasks[0]
            completed_at = datetime.fromisoformat(last["completed_at"]).timestamp()
            last_task_completed_sec_ago = now - completed_at

            if queue_depth > 0 and last_task_completed_sec_ago > 300:  # 5 minutes
                alerts.append(f"No tasks completed in {last_task_completed_sec_ago/60:.1f} minutes")

        # Check worker pool
        worker_metrics = await self.collect_worker_metrics()

        worker_pool_healthy = True
        worker_pool_message = f"{worker_metrics.active_workers} active workers"

        if worker_metrics.total_workers == 0:
            worker_pool_healthy = False
            worker_pool_message = "No workers registered"
            alerts.append("No workers available")
        elif worker_metrics.active_workers == 0 and queue_depth > 0:
            worker_pool_healthy = False
            worker_pool_message = "No active workers (tasks pending)"
            alerts.append("No active workers but tasks are pending")
        elif worker_metrics.active_workers < worker_metrics.total_workers * 0.5:
            warnings.append(
                f"Only {worker_metrics.active_workers}/{worker_metrics.total_workers} workers active"
            )

        # Check database latency
        if database_latency_ms > 1000:
            alerts.append(f"Database latency high: {database_latency_ms:.0f}ms")
        elif database_latency_ms > 500:
            warnings.append(f"Database latency elevated: {database_latency_ms:.0f}ms")

        # Determine overall status
        if alerts:
            status = "critical"
            message = "; ".join(alerts)
        elif warnings:
            status = "degraded"
            message = "; ".join(warnings)
        else:
            status = "healthy"
            message = "All systems operational"

        health = QueueHealth(
            status=status,
            message=message,
            queue_depth=queue_depth,
            age_oldest_pending_sec=age_oldest_pending_sec,
            database_available=database_available,
            database_latency_ms=database_latency_ms,
            worker_pool_healthy=worker_pool_healthy,
            worker_pool_message=worker_pool_message,
            last_task_completed_sec_ago=last_task_completed_sec_ago,
            alerts=alerts,
            warnings=warnings,
        )

        self._last_health_check = health
        self._last_health_check_time = now

        return health

    def record_task_completed(self, task_id: str):
        """Record task completion for metrics."""
        now = time.time()
        self.completed_1min.append(now)
        self.completed_5min.append(now)
        self.completed_15min.append(now)

    def record_task_failed(self, task_id: str):
        """Record task failure for metrics."""
        now = time.time()
        self.failed_1min.append(now)
        self.failed_5min.append(now)
        self.failed_15min.append(now)

    def record_worker_heartbeat(self, worker_id: str, task_count: int = 0):
        """Record worker heartbeat."""
        now = time.time()
        self.worker_last_seen[worker_id] = now

        if worker_id not in self.worker_start_times:
            self.worker_start_times[worker_id] = now

        if task_count > 0:
            self.worker_task_counts[worker_id] = task_count

    async def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report."""
        task_metrics = await self.collect_metrics()
        worker_metrics = await self.collect_worker_metrics()
        health = await self.check_health()

        return {
            "timestamp": datetime.now().isoformat(),
            "queue_name": self.queue_name,
            "health": asdict(health),
            "task_metrics": asdict(task_metrics),
            "worker_metrics": asdict(worker_metrics),
        }


async def monitor_loop(client: AbsurdClient, queue_name: str, interval_sec: float = 30):
    """Continuous monitoring loop."""
    monitor = AbsurdMonitor(client, queue_name)

    while True:
        try:
            report = await monitor.generate_report()

            # Log key metrics
            logger.info(
                f"Queue Health: {report['health']['status']} - {report['health']['message']}"
            )
            logger.info(f"Throughput: {report['task_metrics']['throughput_1min']:.2f} tasks/sec")
            logger.info(f"Queue Depth: {report['health']['queue_depth']} tasks")
            logger.info(
                f"Workers: {report['worker_metrics']['active_workers']}/{report['worker_metrics']['total_workers']} active"
            )

            # Alert on critical issues
            if report["health"]["alerts"]:
                for alert in report["health"]["alerts"]:
                    logger.error(f"ALERT: {alert}")

            # Warn on degraded performance
            if report["health"]["warnings"]:
                for warning in report["health"]["warnings"]:
                    logger.warning(f"WARNING: {warning}")

        except Exception as e:
            logger.error(f"Monitoring error: {e}", exc_info=True)

        await asyncio.sleep(interval_sec)
