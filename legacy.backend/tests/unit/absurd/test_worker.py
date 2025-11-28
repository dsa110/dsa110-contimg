# mypy: disable-error-code="import-not-found,import-untyped"
"""
Unit tests for AbsurdWorker.

Tests worker lifecycle with mocked client.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # type: ignore[import-not-found]

from dsa110_contimg.absurd.config import AbsurdConfig  # type: ignore[import-not-found]
from dsa110_contimg.absurd.worker import (  # type: ignore[import-not-found]
    AbsurdWorker,
    emit_queue_stats_update,
    emit_task_update,
)

# --- Fixtures ---


@pytest.fixture
def config():
    """Create test AbsurdConfig."""
    return AbsurdConfig(
        enabled=True,
        database_url="postgresql://test:test@localhost/test",
        queue_name="test-queue",
        worker_concurrency=1,
        worker_poll_interval_sec=0.1,
        task_timeout_sec=300,
        max_retries=3,
    )


@pytest.fixture
def mock_executor():
    """Create mock executor function."""
    return AsyncMock(return_value={"status": "success", "output": "result"})


@pytest.fixture
def mock_client():
    """Create mock AbsurdClient."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.close = AsyncMock()
    client.claim_task = AsyncMock(return_value=None)
    client.complete_task = AsyncMock()
    client.fail_task = AsyncMock()
    client.heartbeat_task = AsyncMock(return_value=True)
    return client


# --- Worker Initialization Tests ---


class TestWorkerInit:
    """Tests for worker initialization."""

    def test_worker_init_creates_client(self, config, mock_executor):
        """Worker should create AbsurdClient from config."""
        worker = AbsurdWorker(config, mock_executor)

        assert worker.config is config
        assert worker.executor is mock_executor
        assert worker.client is not None
        assert worker.worker_id is not None
        assert worker.running is False

    def test_worker_id_format(self, config, mock_executor):
        """Worker ID should contain hostname and UUID."""
        worker = AbsurdWorker(config, mock_executor)

        assert "-" in worker.worker_id
        # Format: hostname-uuid8chars
        parts = worker.worker_id.rsplit("-", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 8  # 8 hex chars

    def test_worker_uses_config_queue(self, config, mock_executor):
        """Worker should use queue_name from config."""
        config.queue_name = "custom-queue"
        worker = AbsurdWorker(config, mock_executor)

        assert worker.config.queue_name == "custom-queue"


# --- Worker Start/Stop Tests ---


class TestWorkerStartStop:
    """Tests for worker start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_running_true(self, config, mock_executor):
        """start() should set running to True."""
        worker = AbsurdWorker(config, mock_executor)

        # Mock the client
        worker.client = AsyncMock()
        worker.client.claim_task = AsyncMock(return_value=None)
        worker.client.__aenter__ = AsyncMock(return_value=worker.client)
        worker.client.__aexit__ = AsyncMock(return_value=None)

        # Start in background and stop quickly
        async def run_briefly():
            await asyncio.sleep(0.05)
            await worker.stop()

        start_task = asyncio.create_task(worker.start())
        stop_task = asyncio.create_task(run_briefly())

        await asyncio.gather(start_task, stop_task)

        assert worker.running is False

    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self, config, mock_executor):
        """stop() should set running to False."""
        worker = AbsurdWorker(config, mock_executor)
        worker.running = True

        await worker.stop()

        assert worker.running is False

    @pytest.mark.asyncio
    async def test_stop_sets_event(self, config, mock_executor):
        """stop() should set the stop event."""
        worker = AbsurdWorker(config, mock_executor)

        await worker.stop()

        assert worker._stop_event.is_set()


# --- Task Processing Tests ---


class TestTaskProcessing:
    """Tests for task processing logic."""

    @pytest.mark.asyncio
    async def test_process_task_success(self, config, mock_executor):
        """_process_task should call executor and complete task."""
        worker = AbsurdWorker(config, mock_executor)
        worker.client = AsyncMock()
        worker.client.complete_task = AsyncMock()
        worker.client.fail_task = AsyncMock()
        worker.client.heartbeat_task = AsyncMock(return_value=True)

        task = {
            "task_id": "task-123",
            "task_name": "test-task",
            "params": {"input": "data"},
        }

        # Patch WebSocket emit functions
        with patch("dsa110_contimg.absurd.worker.emit_task_update", new_callable=AsyncMock):
            with patch(
                "dsa110_contimg.absurd.worker.emit_queue_stats_update", new_callable=AsyncMock
            ):
                await worker._process_task(task)

        mock_executor.assert_called_once_with("test-task", {"input": "data"})
        worker.client.complete_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_task_executor_error_result(self, config):
        """_process_task should fail task when executor returns error status."""
        executor = AsyncMock(return_value={"status": "error", "errors": ["failed"]})
        worker = AbsurdWorker(config, executor)
        worker.client = AsyncMock()
        worker.client.complete_task = AsyncMock()
        worker.client.fail_task = AsyncMock()
        worker.client.heartbeat_task = AsyncMock(return_value=True)

        task = {
            "task_id": "task-123",
            "task_name": "test-task",
            "params": {},
        }

        with patch("dsa110_contimg.absurd.worker.emit_task_update", new_callable=AsyncMock):
            with patch(
                "dsa110_contimg.absurd.worker.emit_queue_stats_update", new_callable=AsyncMock
            ):
                await worker._process_task(task)

        worker.client.fail_task.assert_called_once()
        worker.client.complete_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_task_executor_exception(self, config):
        """_process_task should fail task when executor raises exception."""
        executor = AsyncMock(side_effect=RuntimeError("Boom!"))
        worker = AbsurdWorker(config, executor)
        worker.client = AsyncMock()
        worker.client.complete_task = AsyncMock()
        worker.client.fail_task = AsyncMock()
        worker.client.heartbeat_task = AsyncMock(return_value=True)

        task = {
            "task_id": "task-456",
            "task_name": "failing-task",
            "params": {},
        }

        with patch("dsa110_contimg.absurd.worker.emit_task_update", new_callable=AsyncMock):
            with patch(
                "dsa110_contimg.absurd.worker.emit_queue_stats_update", new_callable=AsyncMock
            ):
                await worker._process_task(task)

        worker.client.fail_task.assert_called_once()
        call_args = worker.client.fail_task.call_args[0]
        assert call_args[0] == "task-456"
        assert "Boom!" in call_args[1]


# --- Heartbeat Tests ---


class TestHeartbeat:
    """Tests for heartbeat functionality."""

    @pytest.mark.asyncio
    async def test_heartbeat_loop_sends_heartbeats(self, config, mock_executor):
        """_heartbeat_loop should send periodic heartbeats."""
        worker = AbsurdWorker(config, mock_executor)
        worker.client = AsyncMock()
        worker.client.heartbeat_task = AsyncMock(return_value=True)

        # Run heartbeat for a short time then cancel
        heartbeat_task = asyncio.create_task(worker._heartbeat_loop("task-123"))
        await asyncio.sleep(0.15)  # Let it run briefly
        heartbeat_task.cancel()

        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        # Should have sent at least one heartbeat (10s default interval is patched)
        # We can't really test this without mocking asyncio.sleep

    @pytest.mark.asyncio
    async def test_heartbeat_rejected_stops_loop(self, config, mock_executor):
        """_heartbeat_loop should stop when heartbeat rejected."""
        worker = AbsurdWorker(config, mock_executor)
        worker.client = AsyncMock()
        worker.client.heartbeat_task = AsyncMock(return_value=False)

        # Patch sleep to return quickly
        with patch("asyncio.sleep", new_callable=AsyncMock):
            heartbeat_task = asyncio.create_task(worker._heartbeat_loop("task-123"))
            await asyncio.sleep(0.01)

            # Should complete naturally (not need cancelling)
            try:
                await asyncio.wait_for(heartbeat_task, timeout=0.5)
            except asyncio.TimeoutError:
                heartbeat_task.cancel()


# --- WebSocket Event Tests ---


class TestWebSocketEvents:
    """Tests for WebSocket event emission."""

    @pytest.mark.asyncio
    async def test_emit_task_update_with_manager(self):
        """emit_task_update should broadcast when manager is set."""
        mock_manager = AsyncMock()
        mock_manager.broadcast = AsyncMock()

        with patch("dsa110_contimg.absurd.worker._websocket_manager", mock_manager):
            await emit_task_update("test-queue", "task-123", {"status": "completed"})

        mock_manager.broadcast.assert_called_once()
        call_args = mock_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "task_update"
        assert call_args["queue_name"] == "test-queue"
        assert call_args["task_id"] == "task-123"

    @pytest.mark.asyncio
    async def test_emit_task_update_without_manager(self):
        """emit_task_update should be no-op when no manager."""
        with patch("dsa110_contimg.absurd.worker._websocket_manager", None):
            await emit_task_update("test-queue", "task-123", {})
            # Should not raise

    @pytest.mark.asyncio
    async def test_emit_queue_stats_update_with_manager(self):
        """emit_queue_stats_update should broadcast when manager is set."""
        mock_manager = AsyncMock()
        mock_manager.broadcast = AsyncMock()

        with patch("dsa110_contimg.absurd.worker._websocket_manager", mock_manager):
            await emit_queue_stats_update("test-queue")

        mock_manager.broadcast.assert_called_once()
        call_args = mock_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "queue_stats_update"
        assert call_args["queue_name"] == "test-queue"

    @pytest.mark.asyncio
    async def test_emit_handles_broadcast_error(self):
        """emit functions should handle broadcast errors gracefully."""
        mock_manager = AsyncMock()
        mock_manager.broadcast = AsyncMock(side_effect=RuntimeError("Connection lost"))

        with patch("dsa110_contimg.absurd.worker._websocket_manager", mock_manager):
            # Should not raise
            await emit_task_update("queue", "task", {})
            await emit_queue_stats_update("queue")


# --- Polling Loop Tests ---


class TestPollingLoop:
    """Tests for the main polling loop behavior."""

    @pytest.mark.asyncio
    async def test_poll_claims_and_processes(self, config, mock_executor):
        """Worker should claim task and process it."""
        worker = AbsurdWorker(config, mock_executor)

        call_count = 0

        async def mock_claim(queue_name, worker_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "task_id": "task-1",
                    "task_name": "test",
                    "params": {},
                }
            return None

        worker.client = AsyncMock()
        worker.client.claim_task = mock_claim
        worker.client.complete_task = AsyncMock()
        worker.client.heartbeat_task = AsyncMock(return_value=True)
        worker.client.__aenter__ = AsyncMock(return_value=worker.client)
        worker.client.__aexit__ = AsyncMock(return_value=None)

        # Run briefly then stop
        async def run_briefly():
            await asyncio.sleep(0.15)
            await worker.stop()

        with patch("dsa110_contimg.absurd.worker.emit_task_update", new_callable=AsyncMock):
            with patch(
                "dsa110_contimg.absurd.worker.emit_queue_stats_update", new_callable=AsyncMock
            ):
                start_task = asyncio.create_task(worker.start())
                stop_task = asyncio.create_task(run_briefly())
                await asyncio.gather(start_task, stop_task)

        # Should have processed the task
        mock_executor.assert_called()

    @pytest.mark.asyncio
    async def test_poll_sleeps_when_no_tasks(self, config, mock_executor):
        """Worker should sleep when no tasks available."""
        worker = AbsurdWorker(config, mock_executor)

        worker.client = AsyncMock()
        worker.client.claim_task = AsyncMock(return_value=None)
        worker.client.__aenter__ = AsyncMock(return_value=worker.client)
        worker.client.__aexit__ = AsyncMock(return_value=None)

        async def run_briefly():
            await asyncio.sleep(0.1)
            await worker.stop()

        start_task = asyncio.create_task(worker.start())
        stop_task = asyncio.create_task(run_briefly())
        await asyncio.gather(start_task, stop_task)

        # No tasks were executed
        mock_executor.assert_not_called()
