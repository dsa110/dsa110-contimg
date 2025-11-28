"""
Monitoring and metrics collection for Absurd workflow manager.

Provides real-time metrics, health checks, and observability.

Features:
- Task metrics with timeout tracking
- Worker heartbeat registry with crash detection
- Prometheus metrics export
- Health checks and alerting
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

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
    timed_out_workers: int = 0  # Workers that stopped heartbeating

    tasks_per_worker: Optional[Dict[str, int]] = None
    avg_tasks_per_worker: float = 0.0

    worker_uptime_sec: Optional[Dict[str, float]] = None
    avg_worker_uptime_sec: float = 0.0

    # Worker state tracking
    worker_states: Optional[Dict[str, str]] = None  # worker_id -> state (active/idle/crashed)
    last_heartbeat_times: Optional[Dict[str, float]] = None  # worker_id -> timestamp


class WorkerState(Enum):
    """Worker lifecycle states."""

    ACTIVE = "active"  # Recently seen processing tasks
    IDLE = "idle"  # Recently seen but not processing
    STALE = "stale"  # Not seen recently, may be crashed
    CRASHED = "crashed"  # Confirmed crashed (missing heartbeats)


@dataclass
class WorkerInfo:
    """Information about a registered worker."""

    worker_id: str
    first_seen: float
    last_seen: float
    task_count: int = 0
    current_task_id: Optional[str] = None
    state: WorkerState = WorkerState.ACTIVE
    consecutive_missed_heartbeats: int = 0


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

    # Configuration constants
    WORKER_STALE_THRESHOLD_SEC = 60  # Worker considered stale after this time without heartbeat
    WORKER_CRASHED_THRESHOLD_SEC = 180  # Worker considered crashed after this time
    WORKER_ACTIVE_THRESHOLD_SEC = 10  # Worker considered active if seen within this time
    MAX_CONSECUTIVE_MISSED_HEARTBEATS = 5  # Crash detection threshold

    def __init__(self, client: AbsurdClient, queue_name: str):
        self.client = client
        self.queue_name = queue_name

        # Time-series data for task completion tracking
        self.completed_1min: deque[float] = deque(maxlen=60)  # timestamps
        self.completed_5min: deque[float] = deque(maxlen=300)
        self.completed_15min: deque[float] = deque(maxlen=900)

        self.failed_1min: deque[float] = deque(maxlen=60)
        self.failed_5min: deque[float] = deque(maxlen=300)
        self.failed_15min: deque[float] = deque(maxlen=900)

        # Timeout tracking - store timestamps of timed out tasks
        self.timed_out_1min: deque[float] = deque(maxlen=60)
        self.timed_out_5min: deque[float] = deque(maxlen=300)
        self.timed_out_15min: deque[float] = deque(maxlen=900)
        self.total_timed_out_count: int = 0

        # Task timing data
        self.wait_times: deque[float] = deque(maxlen=1000)
        self.execution_times: deque[float] = deque(maxlen=1000)

        # Worker tracking - using structured WorkerInfo objects
        self.worker_registry: Dict[str, WorkerInfo] = {}
        self.crashed_worker_ids: Set[str] = set()  # Track confirmed crashes
        self.total_crashed_count: int = 0

        # Legacy compatibility (keeping these for backward compatibility)
        self.worker_last_seen: Dict[str, float] = {}
        self.worker_task_counts: Dict[str, int] = defaultdict(int)
        self.worker_start_times: Dict[str, float] = {}

        # Health check cache
        self._last_health_check: Optional[QueueHealth] = None
        self._last_health_check_time: float = 0
        self._health_check_cache_sec: float = 10

        # Last known timed_out count from database (for incremental tracking)
        self._last_known_timed_out_from_db: int = 0

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

        # Calculate total from individual counts
        total_tasks = (
            stats["completed"]
            + stats["failed"]
            + stats["cancelled"]
            + stats["pending"]
            + stats["claimed"]
        )

        # Track timeouts: Query for tasks that were marked as timed out
        # Timeouts are tracked when a task exceeds its timeout_sec while in 'claimed' status
        # and gets failed with a timeout error message
        timed_out_count = await self._count_timed_out_tasks()

        # Track new timeouts for time-series data
        new_timeouts = timed_out_count - self._last_known_timed_out_from_db
        if new_timeouts > 0:
            now = time.time()
            for _ in range(new_timeouts):
                self.timed_out_1min.append(now)
                self.timed_out_5min.append(now)
                self.timed_out_15min.append(now)
            self.total_timed_out_count += new_timeouts
            self._last_known_timed_out_from_db = timed_out_count

        metrics = TaskMetrics(
            total_spawned=total_tasks,
            total_claimed=stats["claimed"],  # Currently claimed tasks
            total_completed=stats["completed"],
            total_failed=stats["failed"],
            total_cancelled=stats["cancelled"],
            total_timed_out=timed_out_count,  # Now properly tracked from database
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
        """Collect worker pool metrics with proper heartbeat and crash tracking."""
        now = time.time()

        # Update worker states based on last seen times
        self._update_worker_states(now)

        # Count workers by state
        active_count = 0
        idle_count = 0
        stale_count = 0
        crashed_count = 0

        worker_states_dict: Dict[str, str] = {}
        last_heartbeat_dict: Dict[str, float] = {}

        for worker_id, worker_info in self.worker_registry.items():
            worker_states_dict[worker_id] = worker_info.state.value
            last_heartbeat_dict[worker_id] = worker_info.last_seen

            if worker_info.state == WorkerState.ACTIVE:
                active_count += 1
            elif worker_info.state == WorkerState.IDLE:
                idle_count += 1
            elif worker_info.state == WorkerState.STALE:
                stale_count += 1
            elif worker_info.state == WorkerState.CRASHED:
                crashed_count += 1

        # Also count workers in crashed_worker_ids that may have been removed from registry
        crashed_count += len(self.crashed_worker_ids - set(self.worker_registry.keys()))

        total_workers = len(self.worker_registry)

        # Calculate task counts per worker
        tasks_per_worker = {wid: info.task_count for wid, info in self.worker_registry.items()}
        avg_tasks = sum(tasks_per_worker.values()) / total_workers if total_workers > 0 else 0.0

        # Calculate uptime per worker
        worker_uptimes = {
            wid: now - info.first_seen
            for wid, info in self.worker_registry.items()
            if info.state != WorkerState.CRASHED
        }
        avg_uptime = sum(worker_uptimes.values()) / len(worker_uptimes) if worker_uptimes else 0.0

        return WorkerMetrics(
            total_workers=total_workers,
            active_workers=active_count,
            idle_workers=idle_count,
            crashed_workers=crashed_count + self.total_crashed_count,
            timed_out_workers=stale_count,
            tasks_per_worker=tasks_per_worker,
            avg_tasks_per_worker=avg_tasks,
            worker_uptime_sec=worker_uptimes,
            avg_worker_uptime_sec=avg_uptime,
            worker_states=worker_states_dict,
            last_heartbeat_times=last_heartbeat_dict,
        )

    def _update_worker_states(self, now: float) -> None:
        """Update worker states based on heartbeat timing.

        State transitions:
        - ACTIVE: Last seen < WORKER_ACTIVE_THRESHOLD_SEC ago
        - IDLE: Last seen < WORKER_STALE_THRESHOLD_SEC ago (but not active)
        - STALE: Last seen < WORKER_CRASHED_THRESHOLD_SEC ago (warning state)
        - CRASHED: Last seen > WORKER_CRASHED_THRESHOLD_SEC ago OR
                   missed > MAX_CONSECUTIVE_MISSED_HEARTBEATS
        """
        workers_to_mark_crashed: List[str] = []

        for worker_id, info in self.worker_registry.items():
            time_since_seen = now - info.last_seen

            if time_since_seen < self.WORKER_ACTIVE_THRESHOLD_SEC:
                # Worker is active (recently seen)
                info.state = WorkerState.ACTIVE
                info.consecutive_missed_heartbeats = 0
            elif time_since_seen < self.WORKER_STALE_THRESHOLD_SEC:
                # Worker is idle (seen recently but not very recently)
                info.state = WorkerState.IDLE
                info.consecutive_missed_heartbeats = 0
            elif time_since_seen < self.WORKER_CRASHED_THRESHOLD_SEC:
                # Worker is stale (not seen for a while)
                info.state = WorkerState.STALE
                # Increment missed heartbeats based on expected heartbeat interval (10s)
                expected_heartbeats = int(time_since_seen / 10)
                info.consecutive_missed_heartbeats = expected_heartbeats
            else:
                # Worker has likely crashed
                info.state = WorkerState.CRASHED
                workers_to_mark_crashed.append(worker_id)

        # Mark crashed workers
        for worker_id in workers_to_mark_crashed:
            if worker_id not in self.crashed_worker_ids:
                self.crashed_worker_ids.add(worker_id)
                self.total_crashed_count += 1
                logger.warning(
                    f"Worker {worker_id} marked as crashed "
                    f"(no heartbeat for {self.WORKER_CRASHED_THRESHOLD_SEC}s)"
                )

    def register_worker_heartbeat(self, worker_id: str, task_id: Optional[str] = None) -> None:
        """Register a heartbeat from a worker.

        This method should be called periodically by workers to indicate
        they are alive. If processing a task, include the task_id.

        Args:
            worker_id: Unique worker identifier
            task_id: Optional current task ID being processed
        """
        now = time.time()

        if worker_id in self.worker_registry:
            # Update existing worker
            info = self.worker_registry[worker_id]
            info.last_seen = now
            info.current_task_id = task_id
            info.consecutive_missed_heartbeats = 0

            # Update state based on whether processing a task
            if task_id:
                info.state = WorkerState.ACTIVE
            else:
                info.state = WorkerState.IDLE

            # Remove from crashed set if it was there
            self.crashed_worker_ids.discard(worker_id)
        else:
            # Register new worker
            self.worker_registry[worker_id] = WorkerInfo(
                worker_id=worker_id,
                first_seen=now,
                last_seen=now,
                task_count=0,
                current_task_id=task_id,
                state=WorkerState.ACTIVE if task_id else WorkerState.IDLE,
            )
            logger.info(f"New worker registered: {worker_id}")

        # Update legacy tracking for compatibility
        self.worker_last_seen[worker_id] = now
        if worker_id not in self.worker_start_times:
            self.worker_start_times[worker_id] = now

    def record_task_completion(self, worker_id: str) -> None:
        """Record that a worker completed a task.

        This should be called when a worker finishes processing a task
        to update task count statistics.

        Args:
            worker_id: Worker that completed the task
        """
        if worker_id in self.worker_registry:
            self.worker_registry[worker_id].task_count += 1
            self.worker_registry[worker_id].current_task_id = None
            self.worker_registry[worker_id].state = WorkerState.IDLE

        # Update legacy tracking
        self.worker_task_counts[worker_id] += 1

    async def _count_timed_out_tasks(self) -> int:
        """Count tasks that failed due to timeout.

        Timed-out tasks are identified by:
        1. status = 'failed'
        2. error message contains 'timeout' (case-insensitive)

        OR

        Tasks that exceeded their timeout_sec while claimed but never completed:
        - status = 'claimed'
        - (NOW - claimed_at) > timeout_sec

        Returns:
            Count of timed-out tasks
        """
        if self.client._pool is None:
            logger.warning("Client not connected, cannot count timed-out tasks")
            return 0

        try:
            async with self.client._pool.acquire() as conn:
                # Count failed tasks with timeout-related errors
                row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as count
                    FROM absurd.tasks
                    WHERE queue_name = $1
                      AND status = 'failed'
                      AND (error ILIKE '%timeout%' OR error ILIKE '%timed out%')
                    """,
                    self.queue_name,
                )
                return row["count"] if row else 0
        except Exception as e:
            logger.error(f"Error counting timed-out tasks: {e}")
            return 0

    async def _get_stale_claimed_tasks(self, threshold_sec: float = 3600) -> List[Dict[str, Any]]:
        """Get tasks that have been claimed but not completed for longer than threshold.

        These are potential timeout candidates or stuck tasks.

        Args:
            threshold_sec: Time in seconds after which a claimed task is considered stale

        Returns:
            List of stale task details
        """
        if self.client._pool is None:
            return []

        try:
            async with self.client._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT task_id, task_name, worker_id, claimed_at, timeout_sec,
                           EXTRACT(EPOCH FROM (NOW() - claimed_at)) as claimed_duration_sec
                    FROM absurd.tasks
                    WHERE queue_name = $1
                      AND status = 'claimed'
                      AND claimed_at < NOW() - INTERVAL '1 second' * $2
                    ORDER BY claimed_at ASC
                    """,
                    self.queue_name,
                    threshold_sec,
                )
                return [
                    {
                        "task_id": str(row["task_id"]),
                        "task_name": row["task_name"],
                        "worker_id": row["worker_id"],
                        "claimed_at": row["claimed_at"].isoformat() if row["claimed_at"] else None,
                        "timeout_sec": row["timeout_sec"],
                        "claimed_duration_sec": row["claimed_duration_sec"],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting stale claimed tasks: {e}")
            return []

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

    def record_task_failed(self, task_id: str, is_timeout: bool = False):
        """Record task failure for metrics.

        Args:
            task_id: The task that failed
            is_timeout: Whether the failure was due to timeout
        """
        now = time.time()
        self.failed_1min.append(now)
        self.failed_5min.append(now)
        self.failed_15min.append(now)

        if is_timeout:
            self.timed_out_1min.append(now)
            self.timed_out_5min.append(now)
            self.timed_out_15min.append(now)
            self.total_timed_out_count += 1

    def record_task_timeout(self, task_id: str):
        """Record a task timeout explicitly.

        This is called when a task times out (separate from general failures).

        Args:
            task_id: The task that timed out
        """
        now = time.time()
        self.timed_out_1min.append(now)
        self.timed_out_5min.append(now)
        self.timed_out_15min.append(now)
        self.total_timed_out_count += 1
        # Also record as a failure
        self.failed_1min.append(now)
        self.failed_5min.append(now)
        self.failed_15min.append(now)
        logger.warning(f"Task {task_id} timed out")

    def record_worker_heartbeat(
        self, worker_id: str, task_count: int = 0, current_task_id: Optional[str] = None
    ):
        """Record worker heartbeat with structured tracking.

        Args:
            worker_id: Unique identifier for the worker
            task_count: Total tasks processed by this worker
            current_task_id: ID of task currently being processed (if any)
        """
        now = time.time()

        # Update structured worker registry
        if worker_id in self.worker_registry:
            info = self.worker_registry[worker_id]
            info.last_seen = now
            info.task_count = task_count
            info.current_task_id = current_task_id
            # If worker was crashed but is now responding, recover it
            if info.state == WorkerState.CRASHED:
                info.state = WorkerState.ACTIVE
                info.consecutive_missed_heartbeats = 0
                self.crashed_worker_ids.discard(worker_id)
                logger.info(f"Worker {worker_id} recovered from crashed state")
            else:
                info.state = WorkerState.ACTIVE
                info.consecutive_missed_heartbeats = 0
        else:
            # New worker
            self.worker_registry[worker_id] = WorkerInfo(
                worker_id=worker_id,
                first_seen=now,
                last_seen=now,
                task_count=task_count,
                current_task_id=current_task_id,
                state=WorkerState.ACTIVE,
            )
            logger.info(f"New worker registered: {worker_id}")

        # Also update legacy tracking for backward compatibility
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


class PrometheusExporter:
    """Export Absurd metrics to Prometheus."""

    def __init__(self, monitor: AbsurdMonitor, prefix: str = "absurd"):
        self.monitor = monitor
        self.prefix = prefix
        self._metrics: Dict[str, Any] = {}

    def _metric_name(self, name: str) -> str:
        """Generate Prometheus metric name."""
        return f"{self.prefix}_{name}"

    async def collect_prometheus_metrics(self) -> Dict[str, float]:
        """Collect all metrics in Prometheus format."""
        task_metrics = await self.monitor.collect_metrics()
        worker_metrics = await self.monitor.collect_worker_metrics()
        health = await self.monitor.check_health()

        metrics = {}

        # Task counters
        metrics[self._metric_name("tasks_spawned_total")] = task_metrics.total_spawned
        metrics[self._metric_name("tasks_completed_total")] = task_metrics.total_completed
        metrics[self._metric_name("tasks_failed_total")] = task_metrics.total_failed
        metrics[self._metric_name("tasks_cancelled_total")] = task_metrics.total_cancelled
        metrics[self._metric_name("tasks_timed_out_total")] = task_metrics.total_timed_out

        # Task gauges
        metrics[self._metric_name("tasks_pending")] = task_metrics.current_pending
        metrics[self._metric_name("tasks_claimed")] = task_metrics.current_claimed
        metrics[self._metric_name("queue_depth")] = (
            task_metrics.current_pending + task_metrics.current_claimed
        )

        # Task timing histograms (percentiles)
        metrics[self._metric_name("task_wait_time_seconds_p50")] = task_metrics.p50_wait_time_sec
        metrics[self._metric_name("task_wait_time_seconds_p95")] = task_metrics.p95_wait_time_sec
        metrics[self._metric_name("task_wait_time_seconds_p99")] = task_metrics.p99_wait_time_sec
        metrics[self._metric_name("task_execution_time_seconds_p50")] = (
            task_metrics.p50_execution_time_sec
        )
        metrics[self._metric_name("task_execution_time_seconds_p95")] = (
            task_metrics.p95_execution_time_sec
        )
        metrics[self._metric_name("task_execution_time_seconds_p99")] = (
            task_metrics.p99_execution_time_sec
        )

        # Throughput gauges
        metrics[self._metric_name("throughput_1min_tasks_per_second")] = (
            task_metrics.throughput_1min
        )
        metrics[self._metric_name("throughput_5min_tasks_per_second")] = (
            task_metrics.throughput_5min
        )
        metrics[self._metric_name("throughput_15min_tasks_per_second")] = (
            task_metrics.throughput_15min
        )

        # Success/error rates
        metrics[self._metric_name("success_rate_1min")] = task_metrics.success_rate_1min
        metrics[self._metric_name("success_rate_5min")] = task_metrics.success_rate_5min
        metrics[self._metric_name("success_rate_15min")] = task_metrics.success_rate_15min
        metrics[self._metric_name("error_rate_1min_tasks_per_second")] = (
            task_metrics.error_rate_1min
        )
        metrics[self._metric_name("error_rate_5min_tasks_per_second")] = (
            task_metrics.error_rate_5min
        )
        metrics[self._metric_name("error_rate_15min_tasks_per_second")] = (
            task_metrics.error_rate_15min
        )

        # Worker metrics
        metrics[self._metric_name("workers_total")] = worker_metrics.total_workers
        metrics[self._metric_name("workers_active")] = worker_metrics.active_workers
        metrics[self._metric_name("workers_idle")] = worker_metrics.idle_workers
        metrics[self._metric_name("workers_crashed_total")] = worker_metrics.crashed_workers
        metrics[self._metric_name("workers_timed_out")] = worker_metrics.timed_out_workers
        metrics[self._metric_name("worker_avg_tasks")] = worker_metrics.avg_tasks_per_worker
        metrics[self._metric_name("worker_avg_uptime_seconds")] = (
            worker_metrics.avg_worker_uptime_sec
        )

        # Health metrics
        metrics[self._metric_name("database_available")] = 1 if health.database_available else 0
        metrics[self._metric_name("database_latency_milliseconds")] = (
            health.database_latency_ms if health.database_latency_ms >= 0 else 0
        )
        metrics[self._metric_name("worker_pool_healthy")] = 1 if health.worker_pool_healthy else 0
        metrics[self._metric_name("age_oldest_pending_seconds")] = health.age_oldest_pending_sec
        metrics[self._metric_name("last_task_completed_seconds_ago")] = (
            health.last_task_completed_sec_ago if health.last_task_completed_sec_ago >= 0 else 0
        )

        # Health status as enum (0=healthy, 1=degraded, 2=critical, 3=down)
        status_map = {"healthy": 0, "degraded": 1, "critical": 2, "down": 3}
        metrics[self._metric_name("health_status")] = status_map.get(health.status, 3)
        metrics[self._metric_name("alert_count")] = len(health.alerts)
        metrics[self._metric_name("warning_count")] = len(health.warnings)

        return metrics

    def format_prometheus_text(self, metrics: Dict[str, float]) -> str:
        """Format metrics as Prometheus text exposition format."""
        lines = []

        # Add comments for metric types
        counter_suffixes = ["_total", "_count"]
        gauge_suffixes = ["", "_seconds", "_milliseconds", "_bytes", "_ratio"]

        for name, value in sorted(metrics.items()):
            # Determine metric type
            if any(name.endswith(suffix) for suffix in counter_suffixes):
                metric_type = "counter"
            elif "_p50" in name or "_p95" in name or "_p99" in name:
                metric_type = "summary"
            else:
                metric_type = "gauge"

            lines.append(f"# TYPE {name} {metric_type}")
            lines.append(f"{name} {value}")

        return "\n".join(lines) + "\n"

    async def export_to_file(self, output_path: str):
        """Export metrics to file for node_exporter textfile collector."""
        metrics = await self.collect_prometheus_metrics()
        text = self.format_prometheus_text(metrics)

        with open(output_path, "w") as f:
            f.write(text)

        logger.debug(f"Exported {len(metrics)} metrics to {output_path}")

    async def export_loop(self, output_path: str, interval_sec: float = 15):
        """Continuous export loop for textfile collector."""
        while True:
            try:
                await self.export_to_file(output_path)
            except Exception as e:
                logger.error(f"Prometheus export error: {e}", exc_info=True)

            await asyncio.sleep(interval_sec)
