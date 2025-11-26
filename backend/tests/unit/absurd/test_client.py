# mypy: disable-error-code="import-not-found,import-untyped"
"""
Unit tests for AbsurdClient.

Tests client methods with mocked asyncpg pool.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest  # type: ignore[import-not-found]

from dsa110_contimg.absurd.client import AbsurdClient  # type: ignore[import-not-found]

# --- Fixtures ---


@pytest.fixture
def client():
    """Create an AbsurdClient instance."""
    return AbsurdClient("postgresql://test:test@localhost/test")


def create_mock_pool_with_connection(mock_conn):
    """Create a mock pool with proper async context manager for acquire()."""
    mock_pool = AsyncMock()
    mock_pool.close = AsyncMock()

    @asynccontextmanager
    async def mock_acquire():
        yield mock_conn

    mock_pool.acquire = mock_acquire
    return mock_pool


# --- Connection Tests ---


class TestConnection:
    """Tests for connect/close lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_creates_pool(self, client):
        """connect() should create asyncpg pool."""
        mock_pool = AsyncMock()

        async def create_pool_coro(*args, **kwargs):
            return mock_pool

        with patch(
            "dsa110_contimg.absurd.client.asyncpg.create_pool", side_effect=create_pool_coro
        ) as mock_create:
            await client.connect()

            mock_create.assert_called_once()
            assert client._pool is mock_pool

    @pytest.mark.asyncio
    async def test_connect_twice_warns(self, client, caplog):
        """connect() when already connected should warn."""
        mock_pool = AsyncMock()

        async def create_pool_coro(*args, **kwargs):
            return mock_pool

        with patch(
            "dsa110_contimg.absurd.client.asyncpg.create_pool", side_effect=create_pool_coro
        ) as mock_create:
            await client.connect()
            await client.connect()

            assert mock_create.call_count == 1
            assert "already connected" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_close_closes_pool(self, client):
        """close() should close the pool."""
        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock()
        client._pool = mock_pool

        await client.close()

        mock_pool.close.assert_called_once()
        assert client._pool is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected_noop(self, client):
        """close() when not connected should be no-op."""
        assert client._pool is None
        await client.close()  # Should not raise
        assert client._pool is None

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """async with should connect and close."""
        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock()

        async def create_pool_coro(*args, **kwargs):
            return mock_pool

        with patch(
            "dsa110_contimg.absurd.client.asyncpg.create_pool", side_effect=create_pool_coro
        ):
            async with client as c:
                assert c is client
                assert client._pool is mock_pool

            mock_pool.close.assert_called_once()


# --- spawn_task Tests ---


class TestSpawnTask:
    """Tests for spawn_task method."""

    @pytest.mark.asyncio
    async def test_spawn_task_returns_uuid(self, client):
        """spawn_task should return task UUID."""
        task_uuid = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=(task_uuid,))

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.spawn_task(
            queue_name="test-queue",
            task_name="test-task",
            params={"foo": "bar"},
            priority=5,
            timeout_sec=300,
        )

        assert result == task_uuid
        mock_conn.fetchrow.assert_called_once()
        call_args = mock_conn.fetchrow.call_args[0]
        assert "absurd.spawn_task" in call_args[0]
        assert call_args[1] == "test-queue"
        assert call_args[2] == "test-task"
        assert json.loads(call_args[3]) == {"foo": "bar"}
        assert call_args[4] == 5
        assert call_args[5] == 300

    @pytest.mark.asyncio
    async def test_spawn_task_default_priority(self, client):
        """spawn_task with default priority should be 0."""
        task_uuid = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=(task_uuid,))

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        await client.spawn_task(
            queue_name="test-queue",
            task_name="test-task",
            params={},
        )

        call_args = mock_conn.fetchrow.call_args[0]
        assert call_args[4] == 0  # priority
        assert call_args[5] is None  # timeout_sec

    @pytest.mark.asyncio
    async def test_spawn_task_not_connected_raises(self, client):
        """spawn_task when not connected should raise ValueError."""
        with pytest.raises(ValueError, match="not connected"):
            await client.spawn_task("queue", "task", {})


# --- get_task Tests ---


class TestGetTask:
    """Tests for get_task method."""

    @pytest.mark.asyncio
    async def test_get_task_found(self, client):
        """get_task should return task dict when found."""
        from datetime import datetime

        task_id = uuid4()
        created = datetime(2025, 1, 15, 12, 0, 0)
        mock_row = {
            "task_id": task_id,
            "queue_name": "test-queue",
            "task_name": "test-task",
            "params": '{"key": "value"}',
            "priority": 3,
            "status": "pending",
            "created_at": created,
            "claimed_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "retry_count": 0,
        }
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.get_task(task_id)

        assert result is not None
        assert result["task_id"] == str(task_id)
        assert result["queue_name"] == "test-queue"
        assert result["task_name"] == "test-task"
        assert result["params"] == {"key": "value"}
        assert result["priority"] == 3
        assert result["status"] == "pending"
        assert result["created_at"] == created.isoformat()
        assert result["claimed_at"] is None
        assert result["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client):
        """get_task should return None when not found."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.get_task(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_task_not_connected_raises(self, client):
        """get_task when not connected should raise ValueError."""
        with pytest.raises(ValueError, match="not connected"):
            await client.get_task(uuid4())


# --- list_tasks Tests ---


class TestListTasks:
    """Tests for list_tasks method."""

    @pytest.mark.asyncio
    async def test_list_tasks_returns_list(self, client):
        """list_tasks should return list of task dicts."""
        from datetime import datetime

        task_id = uuid4()
        created = datetime(2025, 1, 15, 12, 0, 0)
        mock_rows = [
            {
                "task_id": task_id,
                "queue_name": "test-queue",
                "task_name": "test-task",
                "params": '{"k": "v"}',
                "priority": 0,
                "status": "pending",
                "created_at": created,
                "claimed_at": None,
                "completed_at": None,
                "retry_count": 0,
            }
        ]
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.list_tasks()

        assert len(result) == 1
        assert result[0]["task_id"] == str(task_id)
        assert result[0]["params"] == {"k": "v"}

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, client):
        """list_tasks should filter by queue_name and status."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        await client.list_tasks(queue_name="my-queue", status="pending", limit=50)

        call_args = mock_conn.fetch.call_args[0]
        # Verify the query was called with filter parameters
        assert mock_conn.fetch.called

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, client):
        """list_tasks with no tasks should return empty list."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.list_tasks()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_tasks_not_connected_raises(self, client):
        """list_tasks when not connected should raise ValueError."""
        with pytest.raises(ValueError, match="not connected"):
            await client.list_tasks()


# --- cancel_task Tests ---


class TestCancelTask:
    """Tests for cancel_task method."""

    @pytest.mark.asyncio
    async def test_cancel_task_success(self, client):
        """cancel_task should return True when task cancelled."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.cancel_task(uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, client):
        """cancel_task should return False when task not found."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.cancel_task(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_task_not_connected_raises(self, client):
        """cancel_task when not connected should raise ValueError."""
        with pytest.raises(ValueError, match="not connected"):
            await client.cancel_task(uuid4())


# --- get_queue_stats Tests ---


class TestGetQueueStats:
    """Tests for get_queue_stats method."""

    @pytest.mark.asyncio
    async def test_get_queue_stats_returns_dict(self, client):
        """get_queue_stats should return dict with status counts."""
        mock_rows = [
            {"status": "pending", "count": 10},
            {"status": "claimed", "count": 2},
            {"status": "completed", "count": 100},
        ]
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.get_queue_stats("test-queue")

        assert result["pending"] == 10
        assert result["claimed"] == 2
        assert result["completed"] == 100
        assert result["failed"] == 0  # default
        assert result["cancelled"] == 0  # default

    @pytest.mark.asyncio
    async def test_get_queue_stats_empty_queue(self, client):
        """get_queue_stats on empty queue should return zeros."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.get_queue_stats("empty-queue")

        assert result["pending"] == 0
        assert result["claimed"] == 0
        assert result["completed"] == 0
        assert result["failed"] == 0
        assert result["cancelled"] == 0

    @pytest.mark.asyncio
    async def test_get_queue_stats_not_connected_raises(self, client):
        """get_queue_stats when not connected should raise ValueError."""
        with pytest.raises(ValueError, match="not connected"):
            await client.get_queue_stats("queue")


# --- claim_task Tests ---


class TestClaimTask:
    """Tests for claim_task method."""

    @pytest.mark.asyncio
    async def test_claim_task_found(self, client):
        """claim_task should return task dict when found."""
        task_id = uuid4()
        mock_row = {
            "task_id": task_id,
            "queue_name": "test-queue",
            "task_name": "test-task",
            "params": '{"input": "data"}',
            "priority": 5,
            "status": "claimed",
            "attempt": 1,
        }
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.claim_task("test-queue", "worker-1")

        assert result is not None
        assert result["task_id"] == str(task_id)
        assert result["queue_name"] == "test-queue"
        assert result["task_name"] == "test-task"
        assert result["params"] == {"input": "data"}
        assert result["priority"] == 5
        assert result["status"] == "claimed"
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_claim_task_empty_queue(self, client):
        """claim_task on empty queue should return None."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.claim_task("empty-queue", "worker-1")

        assert result is None

    @pytest.mark.asyncio
    async def test_claim_task_not_connected_raises(self, client):
        """claim_task when not connected should raise ValueError."""
        with pytest.raises(ValueError, match="not connected"):
            await client.claim_task("queue", "worker")


# --- complete_task Tests ---


class TestCompleteTask:
    """Tests for complete_task method."""

    @pytest.mark.asyncio
    async def test_complete_task_returns_none(self, client):
        """complete_task should return None (void operation)."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.complete_task("task-123", {"output": "data"})

        assert result is None
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "absurd.complete_task" in call_args[0]
        assert call_args[1] == "task-123"
        assert json.loads(call_args[2]) == {"output": "data"}

    @pytest.mark.asyncio
    async def test_complete_task_not_connected_raises(self, client):
        """complete_task when not connected should raise ValueError."""
        with pytest.raises(ValueError, match="not connected"):
            await client.complete_task("task-123", {})


# --- fail_task Tests ---


class TestFailTask:
    """Tests for fail_task method."""

    @pytest.mark.asyncio
    async def test_fail_task_returns_none(self, client):
        """fail_task should return None (void operation)."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.fail_task("task-123", "Something went wrong")

        assert result is None
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "absurd.fail_task" in call_args[0]
        assert call_args[1] == "task-123"
        assert call_args[2] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_fail_task_not_connected_raises(self, client):
        """fail_task when not connected should raise ValueError."""
        with pytest.raises(ValueError, match="not connected"):
            await client.fail_task("task-123", "error")


# --- heartbeat_task Tests ---


class TestHeartbeatTask:
    """Tests for heartbeat_task method."""

    @pytest.mark.asyncio
    async def test_heartbeat_task_success(self, client):
        """heartbeat_task should return True when accepted."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=True)

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.heartbeat_task("task-123")

        assert result is True
        mock_conn.fetchval.assert_called_once()
        call_args = mock_conn.fetchval.call_args[0]
        assert "absurd.heartbeat_task" in call_args[0]

    @pytest.mark.asyncio
    async def test_heartbeat_task_rejected(self, client):
        """heartbeat_task should return False when rejected."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=False)

        mock_pool = create_mock_pool_with_connection(mock_conn)
        client._pool = mock_pool

        result = await client.heartbeat_task("task-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_heartbeat_task_not_connected_raises(self, client):
        """heartbeat_task when not connected should raise ValueError."""
        with pytest.raises(ValueError, match="not connected"):
            await client.heartbeat_task("task-123")
