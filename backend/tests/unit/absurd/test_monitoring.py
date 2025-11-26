# mypy: disable-error-code="import-not-found,import-untyped"
"""
Unit tests for AbsurdMonitor.

Tests monitoring, worker tracking, timeout detection, and metrics collection.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # type: ignore[import-not-found]

from dsa110_contimg.absurd.monitoring import (  # type: ignore[import-not-found]
    AbsurdMonitor,
    PrometheusExporter,
    QueueHealth,
    TaskMetrics,
    WorkerInfo,
    WorkerMetrics,
    WorkerState,
)

# --- Fixtures ---


@pytest.fixture
def mock_client():
    """Create a mock AbsurdClient with pool."""
    client = MagicMock()
    client._pool = MagicMock()
    client.get_queue_stats = AsyncMock(
        return_value={
            "pending": 5,
            "claimed": 2,
            "completed": 100,
            "failed": 3,
            "cancelled": 1,
        }
    )
    client.list_tasks = AsyncMock(return_value=[])
    return client


@pytest.fixture
def monitor(mock_client):
    """Create an AbsurdMonitor instance with mock client."""
    return AbsurdMonitor(mock_client, "test-queue")


# --- WorkerState Tests ---


class TestWorkerState:
    """Tests for WorkerState enum."""

    def test_worker_states_exist(self):
        """All expected worker states should exist."""
        assert WorkerState.ACTIVE.value == "active"
        assert WorkerState.IDLE.value == "idle"
        assert WorkerState.STALE.value == "stale"
        assert WorkerState.CRASHED.value == "crashed"

    def test_worker_state_values_are_strings(self):
        """Worker state values should be strings."""
        for state in WorkerState:
            assert isinstance(state.value, str)


# --- WorkerInfo Tests ---


class TestWorkerInfo:
    """Tests for WorkerInfo dataclass."""

    def test_worker_info_creation(self):
        """WorkerInfo should store all fields correctly."""
        now = time.time()
        info = WorkerInfo(
            worker_id="test-worker-1",
            first_seen=now - 100,
            last_seen=now,
            task_count=5,
            current_task_id="task-123",
            state=WorkerState.ACTIVE,
            consecutive_missed_heartbeats=0,
        )

        assert info.worker_id == "test-worker-1"
        assert info.first_seen == now - 100
        assert info.last_seen == now
        assert info.task_count == 5
        assert info.current_task_id == "task-123"
        assert info.state == WorkerState.ACTIVE
        assert info.consecutive_missed_heartbeats == 0

    def test_worker_info_default_state(self):
        """WorkerInfo should default to ACTIVE state."""
        now = time.time()
        info = WorkerInfo(
            worker_id="test-worker",
            first_seen=now,
            last_seen=now,
        )

        assert info.state == WorkerState.ACTIVE
        assert info.task_count == 0
        assert info.current_task_id is None
        assert info.consecutive_missed_heartbeats == 0


# --- Monitor Initialization Tests ---


class TestMonitorInit:
    """Tests for AbsurdMonitor initialization."""

    def test_monitor_init(self, mock_client):
        """Monitor should initialize with proper defaults."""
        monitor = AbsurdMonitor(mock_client, "test-queue")

        assert monitor.client is mock_client
        assert monitor.queue_name == "test-queue"
        assert monitor.total_timed_out_count == 0
        assert monitor.total_crashed_count == 0
        assert len(monitor.worker_registry) == 0
        assert len(monitor.crashed_worker_ids) == 0

    def test_monitor_time_series_deques_initialized(self, monitor):
        """Time series deques should be initialized with proper maxlen."""
        assert isinstance(monitor.completed_1min, deque)
        assert monitor.completed_1min.maxlen == 60

        assert isinstance(monitor.timed_out_1min, deque)
        assert monitor.timed_out_1min.maxlen == 60

        assert isinstance(monitor.timed_out_5min, deque)
        assert monitor.timed_out_5min.maxlen == 300

    def test_monitor_thresholds(self, monitor):
        """Monitor should have configurable thresholds."""
        assert monitor.WORKER_STALE_THRESHOLD_SEC == 60
        assert monitor.WORKER_CRASHED_THRESHOLD_SEC == 180
        assert monitor.WORKER_ACTIVE_THRESHOLD_SEC == 10


# --- Worker Heartbeat Tests ---


class TestWorkerHeartbeat:
    """Tests for worker heartbeat recording."""

    def test_record_heartbeat_new_worker(self, monitor):
        """Recording heartbeat for new worker should register it."""
        monitor.record_worker_heartbeat("worker-1", task_count=0)

        assert "worker-1" in monitor.worker_registry
        info = monitor.worker_registry["worker-1"]
        assert info.state == WorkerState.ACTIVE
        assert info.task_count == 0

    def test_record_heartbeat_updates_last_seen(self, monitor):
        """Recording heartbeat should update last_seen time."""
        monitor.record_worker_heartbeat("worker-1")
        first_seen = monitor.worker_registry["worker-1"].last_seen

        time.sleep(0.01)  # Small delay
        monitor.record_worker_heartbeat("worker-1")
        second_seen = monitor.worker_registry["worker-1"].last_seen

        assert second_seen > first_seen

    def test_record_heartbeat_with_task_id(self, monitor):
        """Recording heartbeat with task ID should track current task."""
        monitor.record_worker_heartbeat("worker-1", current_task_id="task-abc")

        info = monitor.worker_registry["worker-1"]
        assert info.current_task_id == "task-abc"

    def test_record_heartbeat_increments_task_count(self, monitor):
        """Recording heartbeat should update task count."""
        monitor.record_worker_heartbeat("worker-1", task_count=1)
        assert monitor.worker_registry["worker-1"].task_count == 1

        monitor.record_worker_heartbeat("worker-1", task_count=5)
        assert monitor.worker_registry["worker-1"].task_count == 5

    def test_record_heartbeat_recovers_crashed_worker(self, monitor):
        """Crashed worker that sends heartbeat should recover."""
        # Register worker and mark as crashed
        monitor.record_worker_heartbeat("worker-1")
        monitor.worker_registry["worker-1"].state = WorkerState.CRASHED
        monitor.crashed_worker_ids.add("worker-1")

        # Send new heartbeat
        monitor.record_worker_heartbeat("worker-1")

        assert monitor.worker_registry["worker-1"].state == WorkerState.ACTIVE
        assert "worker-1" not in monitor.crashed_worker_ids


# --- Worker State Update Tests ---


class TestWorkerStateUpdate:
    """Tests for _update_worker_states method."""

    def test_active_worker_state(self, monitor):
        """Worker seen recently should be ACTIVE."""
        now = time.time()
        monitor.worker_registry["worker-1"] = WorkerInfo(
            worker_id="worker-1",
            first_seen=now - 100,
            last_seen=now - 5,  # 5 seconds ago
        )

        monitor._update_worker_states(now)

        assert monitor.worker_registry["worker-1"].state == WorkerState.ACTIVE

    def test_idle_worker_state(self, monitor):
        """Worker not seen very recently but within threshold should be IDLE."""
        now = time.time()
        monitor.worker_registry["worker-1"] = WorkerInfo(
            worker_id="worker-1",
            first_seen=now - 100,
            last_seen=now - 30,  # 30 seconds ago (> 10s, < 60s)
        )

        monitor._update_worker_states(now)

        assert monitor.worker_registry["worker-1"].state == WorkerState.IDLE

    def test_stale_worker_state(self, monitor):
        """Worker not seen for a while should be STALE."""
        now = time.time()
        monitor.worker_registry["worker-1"] = WorkerInfo(
            worker_id="worker-1",
            first_seen=now - 200,
            last_seen=now - 90,  # 90 seconds ago (> 60s, < 180s)
        )

        monitor._update_worker_states(now)

        assert monitor.worker_registry["worker-1"].state == WorkerState.STALE
        assert monitor.worker_registry["worker-1"].consecutive_missed_heartbeats > 0

    def test_crashed_worker_state(self, monitor):
        """Worker not seen for too long should be CRASHED."""
        now = time.time()
        monitor.worker_registry["worker-1"] = WorkerInfo(
            worker_id="worker-1",
            first_seen=now - 500,
            last_seen=now - 200,  # 200 seconds ago (> 180s)
        )

        monitor._update_worker_states(now)

        assert monitor.worker_registry["worker-1"].state == WorkerState.CRASHED
        assert "worker-1" in monitor.crashed_worker_ids
        assert monitor.total_crashed_count == 1

    def test_crashed_worker_counted_once(self, monitor):
        """Crashed worker should only be counted once."""
        now = time.time()
        monitor.worker_registry["worker-1"] = WorkerInfo(
            worker_id="worker-1",
            first_seen=now - 500,
            last_seen=now - 200,
        )

        # Call update twice
        monitor._update_worker_states(now)
        monitor._update_worker_states(now)

        assert monitor.total_crashed_count == 1  # Only counted once


# --- Task Recording Tests ---


class TestTaskRecording:
    """Tests for task completion/failure recording."""

    def test_record_task_completed(self, monitor):
        """Recording completed task should update time series."""
        monitor.record_task_completed("task-1")

        assert len(monitor.completed_1min) == 1
        assert len(monitor.completed_5min) == 1
        assert len(monitor.completed_15min) == 1

    def test_record_task_failed(self, monitor):
        """Recording failed task should update time series."""
        monitor.record_task_failed("task-1")

        assert len(monitor.failed_1min) == 1
        assert len(monitor.failed_5min) == 1

    def test_record_task_failed_with_timeout(self, monitor):
        """Recording failed task with timeout should update timeout series."""
        monitor.record_task_failed("task-1", is_timeout=True)

        assert len(monitor.failed_1min) == 1
        assert len(monitor.timed_out_1min) == 1
        assert monitor.total_timed_out_count == 1

    def test_record_task_timeout(self, monitor):
        """Recording timeout should update both failed and timed_out series."""
        monitor.record_task_timeout("task-1")

        assert len(monitor.failed_1min) == 1
        assert len(monitor.timed_out_1min) == 1
        assert monitor.total_timed_out_count == 1


# --- Timeout Query Tests ---


class TestTimeoutQuery:
    """Tests for _count_timed_out_tasks method."""

    @pytest.mark.asyncio
    async def test_count_timed_out_tasks_returns_count(self, monitor, mock_client):
        """Should return count from database query."""
        # Setup mock connection
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"count": 5})

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_client._pool.acquire = mock_acquire

        count = await monitor._count_timed_out_tasks()

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_timed_out_tasks_no_pool(self, monitor, mock_client):
        """Should return 0 if pool not connected."""
        mock_client._pool = None

        count = await monitor._count_timed_out_tasks()

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_timed_out_tasks_handles_error(self, monitor, mock_client):
        """Should return 0 on database error."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("DB error"))

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_client._pool.acquire = mock_acquire

        count = await monitor._count_timed_out_tasks()

        assert count == 0


# --- Collect Worker Metrics Tests ---


class TestCollectWorkerMetrics:
    """Tests for collect_worker_metrics method."""

    @pytest.mark.asyncio
    async def test_collect_worker_metrics_empty(self, monitor):
        """Should return zeros when no workers registered."""
        metrics = await monitor.collect_worker_metrics()

        assert metrics.total_workers == 0
        assert metrics.active_workers == 0
        assert metrics.idle_workers == 0
        assert metrics.crashed_workers == 0

    @pytest.mark.asyncio
    async def test_collect_worker_metrics_with_workers(self, monitor):
        """Should count workers by state."""
        now = time.time()

        # Active worker (seen just now)
        monitor.worker_registry["worker-1"] = WorkerInfo(
            worker_id="worker-1", first_seen=now - 100, last_seen=now - 2
        )

        # Idle worker (seen 30 seconds ago)
        monitor.worker_registry["worker-2"] = WorkerInfo(
            worker_id="worker-2", first_seen=now - 100, last_seen=now - 30
        )

        metrics = await monitor.collect_worker_metrics()

        assert metrics.total_workers == 2
        assert metrics.active_workers == 1
        assert metrics.idle_workers == 1

    @pytest.mark.asyncio
    async def test_collect_worker_metrics_includes_task_counts(self, monitor):
        """Should include task counts per worker."""
        now = time.time()
        monitor.worker_registry["worker-1"] = WorkerInfo(
            worker_id="worker-1",
            first_seen=now - 100,
            last_seen=now - 2,
            task_count=10,
        )

        metrics = await monitor.collect_worker_metrics()

        assert metrics.tasks_per_worker["worker-1"] == 10
        assert metrics.avg_tasks_per_worker == 10.0

    @pytest.mark.asyncio
    async def test_collect_worker_metrics_includes_states(self, monitor):
        """Should include worker states in metrics."""
        now = time.time()
        monitor.worker_registry["worker-1"] = WorkerInfo(
            worker_id="worker-1",
            first_seen=now - 100,
            last_seen=now - 2,
            state=WorkerState.ACTIVE,
        )

        metrics = await monitor.collect_worker_metrics()

        assert metrics.worker_states is not None
        assert metrics.worker_states["worker-1"] == "active"


# --- Collect Task Metrics Tests ---


class TestCollectTaskMetrics:
    """Tests for collect_metrics method."""

    @pytest.mark.asyncio
    async def test_collect_metrics_basic(self, monitor, mock_client):
        """Should collect basic metrics from queue stats."""
        # Setup mock for timeout query
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"count": 2})

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_client._pool.acquire = mock_acquire

        metrics = await monitor.collect_metrics()

        assert metrics.total_completed == 100
        assert metrics.total_failed == 3
        assert metrics.current_pending == 5
        assert metrics.current_claimed == 2
        assert metrics.total_timed_out == 2

    @pytest.mark.asyncio
    async def test_collect_metrics_includes_rates(self, monitor, mock_client):
        """Should calculate throughput and success rates."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"count": 0})

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_client._pool.acquire = mock_acquire

        # Record some completions
        for _ in range(5):
            monitor.record_task_completed("task")

        metrics = await monitor.collect_metrics()

        assert metrics.throughput_1min > 0
        assert metrics.success_rate_1min == 1.0  # No failures


# --- Prometheus Exporter Tests ---


class TestPrometheusExporter:
    """Tests for PrometheusExporter."""

    def test_metric_name_prefix(self, monitor):
        """Metric names should have correct prefix."""
        exporter = PrometheusExporter(monitor, prefix="test")

        assert exporter._metric_name("tasks_total") == "test_tasks_total"

    @pytest.mark.asyncio
    async def test_collect_prometheus_metrics(self, monitor, mock_client):
        """Should collect all metrics in dict format."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"count": 0})

        @asynccontextmanager
        async def mock_acquire():
            yield mock_conn

        mock_client._pool.acquire = mock_acquire

        exporter = PrometheusExporter(monitor)
        metrics = await exporter.collect_prometheus_metrics()

        # Check key metrics exist
        assert "absurd_tasks_completed_total" in metrics
        assert "absurd_tasks_failed_total" in metrics
        assert "absurd_tasks_timed_out_total" in metrics
        assert "absurd_workers_total" in metrics
        assert "absurd_workers_crashed_total" in metrics

    def test_format_prometheus_text(self, monitor):
        """Should format metrics as Prometheus text."""
        exporter = PrometheusExporter(monitor)

        metrics = {
            "absurd_tasks_total": 100,
            "absurd_workers_active": 3,
        }

        text = exporter.format_prometheus_text(metrics)

        assert "# TYPE absurd_tasks_total" in text
        assert "absurd_tasks_total 100" in text
        assert "# TYPE absurd_workers_active" in text
        assert "absurd_workers_active 3" in text


# --- Health Check Tests ---


class TestHealthCheck:
    """Tests for check_health method."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, monitor, mock_client):
        """Should return healthy status when all checks pass."""
        mock_client.get_queue_stats = AsyncMock(
            return_value={
                "pending": 5,
                "claimed": 2,
                "completed": 100,
                "failed": 0,
                "cancelled": 0,
            }
        )
        mock_client.list_tasks = AsyncMock(return_value=[])

        # Register a worker so we don't get "no workers" alert
        monitor.record_worker_heartbeat("worker-1")

        health = await monitor.check_health()

        assert health.status == "healthy"
        assert health.database_available is True
        assert len(health.alerts) == 0

    @pytest.mark.asyncio
    async def test_health_check_database_down(self, monitor, mock_client):
        """Should return down status when database unavailable."""
        mock_client.get_queue_stats = AsyncMock(side_effect=Exception("Connection failed"))

        health = await monitor.check_health()

        assert health.status == "down"
        assert health.database_available is False
        assert len(health.alerts) > 0

    @pytest.mark.asyncio
    async def test_health_check_caching(self, monitor, mock_client):
        """Should cache health check results."""
        mock_client.list_tasks = AsyncMock(return_value=[])

        # First call
        health1 = await monitor.check_health()

        # Second call should use cache
        health2 = await monitor.check_health()

        # get_queue_stats should only be called once due to caching
        assert mock_client.get_queue_stats.call_count == 1
        assert health1.status == health2.status


# --- Integration-style Tests ---


class TestMonitorIntegration:
    """Integration-style tests for monitor workflow."""

    @pytest.mark.asyncio
    async def test_full_worker_lifecycle(self, monitor):
        """Test complete worker lifecycle: register -> active -> stale -> crashed."""
        # Worker registers
        monitor.record_worker_heartbeat("worker-1", task_count=0)
        assert monitor.worker_registry["worker-1"].state == WorkerState.ACTIVE

        # Worker becomes idle (simulate time passing)
        monitor.worker_registry["worker-1"].last_seen = time.time() - 30
        monitor._update_worker_states(time.time())
        assert monitor.worker_registry["worker-1"].state == WorkerState.IDLE

        # Worker becomes stale
        monitor.worker_registry["worker-1"].last_seen = time.time() - 90
        monitor._update_worker_states(time.time())
        assert monitor.worker_registry["worker-1"].state == WorkerState.STALE

        # Worker crashes
        monitor.worker_registry["worker-1"].last_seen = time.time() - 200
        monitor._update_worker_states(time.time())
        assert monitor.worker_registry["worker-1"].state == WorkerState.CRASHED
        assert monitor.total_crashed_count == 1

        # Worker recovers
        monitor.record_worker_heartbeat("worker-1", task_count=1)
        assert monitor.worker_registry["worker-1"].state == WorkerState.ACTIVE
        assert "worker-1" not in monitor.crashed_worker_ids

    @pytest.mark.asyncio
    async def test_multiple_workers_different_states(self, monitor):
        """Test monitoring multiple workers in different states."""
        now = time.time()

        # Add workers in different states
        monitor.worker_registry["active-1"] = WorkerInfo(
            worker_id="active-1", first_seen=now - 100, last_seen=now - 2
        )
        monitor.worker_registry["idle-1"] = WorkerInfo(
            worker_id="idle-1", first_seen=now - 100, last_seen=now - 30
        )
        monitor.worker_registry["stale-1"] = WorkerInfo(
            worker_id="stale-1", first_seen=now - 100, last_seen=now - 90
        )
        monitor.worker_registry["crashed-1"] = WorkerInfo(
            worker_id="crashed-1", first_seen=now - 300, last_seen=now - 200
        )

        metrics = await monitor.collect_worker_metrics()

        assert metrics.total_workers == 4
        assert metrics.active_workers == 1
        assert metrics.idle_workers == 1
        # stale-1 goes to timed_out_workers, crashed-1 goes to crashed_workers
        assert metrics.crashed_workers >= 1
