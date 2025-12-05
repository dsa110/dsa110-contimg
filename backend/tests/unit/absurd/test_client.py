"""
Unit tests for ABSURD client.

Tests the AbsurdClient class with mocked database connections.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from dsa110_contimg.absurd.client import AbsurdClient


class TestAbsurdClientInit:
    """Tests for AbsurdClient initialization."""

    def test_client_creation(self):
        """Test client can be created with default settings."""
        client = AbsurdClient("postgresql://localhost/test")
        
        assert client.database_url == "postgresql://localhost/test"
        assert client.pool_min_size == 2
        assert client.pool_max_size == 10
        assert client._pool is None

    def test_client_custom_pool_size(self):
        """Test client with custom pool size."""
        client = AbsurdClient(
            "postgresql://localhost/test",
            pool_min_size=5,
            pool_max_size=20,
        )
        
        assert client.pool_min_size == 5
        assert client.pool_max_size == 20


class TestAbsurdClientConnection:
    """Tests for AbsurdClient connection handling."""

    @pytest.mark.asyncio
    async def test_connect_creates_pool(self):
        """Test connect creates connection pool."""
        client = AbsurdClient("postgresql://localhost/test")
        
        mock_pool = AsyncMock()
        with patch("dsa110_contimg.absurd.client.asyncpg.create_pool", return_value=mock_pool):
            await client.connect()
            
            assert client._pool is mock_pool

    @pytest.mark.asyncio
    async def test_connect_warns_if_already_connected(self):
        """Test connect warns if already connected."""
        client = AbsurdClient("postgresql://localhost/test")
        client._pool = AsyncMock()  # Simulate already connected
        
        with patch("dsa110_contimg.absurd.client.logger.warning") as mock_warn:
            await client.connect()
            mock_warn.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_closes_pool(self):
        """Test close closes connection pool."""
        client = AbsurdClient("postgresql://localhost/test")
        mock_pool = AsyncMock()
        client._pool = mock_pool
        
        await client.close()
        
        mock_pool.close.assert_called_once()
        assert client._pool is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        """Test close is safe when not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        
        # Should not raise
        await client.close()
        assert client._pool is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        mock_pool = AsyncMock()
        
        with patch("dsa110_contimg.absurd.client.asyncpg.create_pool", return_value=mock_pool):
            async with AbsurdClient("postgresql://localhost/test") as client:
                assert client._pool is mock_pool
            
            # Pool should be closed after context
            mock_pool.close.assert_called_once()


class TestAbsurdClientSpawnTask:
    """Tests for AbsurdClient.spawn_task()."""

    @pytest.mark.asyncio
    async def test_spawn_task_not_connected(self):
        """Test spawn_task raises when not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        
        with pytest.raises(ValueError, match="not connected"):
            await client.spawn_task("queue", "task", {"key": "value"})

    @pytest.mark.asyncio
    async def test_spawn_task_success(self):
        """Test spawn_task returns task ID."""
        client = AbsurdClient("postgresql://localhost/test")
        
        task_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = [task_id]
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        client._pool = mock_pool
        
        result = await client.spawn_task("my-queue", "convert", {"group_id": "test"})
        
        assert result == task_id
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_task_with_priority(self):
        """Test spawn_task with custom priority."""
        client = AbsurdClient("postgresql://localhost/test")
        
        task_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = [task_id]
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        client._pool = mock_pool
        
        await client.spawn_task("my-queue", "urgent-task", {}, priority=10)
        
        # Verify priority was passed
        call_args = mock_conn.fetchrow.call_args[0]
        assert call_args[3] == 10  # priority argument

    @pytest.mark.asyncio
    async def test_spawn_task_with_timeout(self):
        """Test spawn_task with custom timeout."""
        client = AbsurdClient("postgresql://localhost/test")
        
        task_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = [task_id]
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        client._pool = mock_pool
        
        await client.spawn_task("my-queue", "long-task", {}, timeout_sec=7200)
        
        # Verify timeout was passed
        call_args = mock_conn.fetchrow.call_args[0]
        assert call_args[4] == 7200  # timeout_sec argument


class TestAbsurdClientGetTask:
    """Tests for AbsurdClient.get_task()."""

    @pytest.mark.asyncio
    async def test_get_task_not_connected(self):
        """Test get_task raises when not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        
        with pytest.raises(ValueError, match="not connected"):
            await client.get_task(uuid4())

    @pytest.mark.asyncio
    async def test_get_task_found(self):
        """Test get_task returns task details."""
        client = AbsurdClient("postgresql://localhost/test")
        
        task_id = uuid4()
        mock_row = {
            "id": task_id,
            "queue_name": "my-queue",
            "task_name": "convert",
            "state": "running",
            "params": '{"group_id": "test"}',
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_row
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        client._pool = mock_pool
        
        result = await client.get_task(task_id)
        
        assert result is not None
        assert result["id"] == task_id
        assert result["state"] == "running"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test get_task returns None for missing task."""
        client = AbsurdClient("postgresql://localhost/test")
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        client._pool = mock_pool
        
        result = await client.get_task(uuid4())
        
        assert result is None


class TestAbsurdClientListTasks:
    """Tests for AbsurdClient.list_tasks()."""

    @pytest.mark.asyncio
    async def test_list_tasks_not_connected(self):
        """Test list_tasks raises when not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        
        with pytest.raises(ValueError, match="not connected"):
            await client.list_tasks("my-queue")

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self):
        """Test list_tasks returns empty list when no tasks."""
        client = AbsurdClient("postgresql://localhost/test")
        
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        client._pool = mock_pool
        
        result = await client.list_tasks("my-queue")
        
        assert result == []

    @pytest.mark.asyncio
    async def test_list_tasks_with_results(self):
        """Test list_tasks returns task list."""
        client = AbsurdClient("postgresql://localhost/test")
        
        mock_rows = [
            {"id": uuid4(), "task_name": "task1", "state": "pending"},
            {"id": uuid4(), "task_name": "task2", "state": "running"},
        ]
        
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_rows
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        client._pool = mock_pool
        
        result = await client.list_tasks("my-queue")
        
        assert len(result) == 2
        assert result[0]["task_name"] == "task1"
        assert result[1]["task_name"] == "task2"


class TestAbsurdClientCancelTask:
    """Tests for AbsurdClient.cancel_task()."""

    @pytest.mark.asyncio
    async def test_cancel_task_not_connected(self):
        """Test cancel_task raises when not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        
        with pytest.raises(ValueError, match="not connected"):
            await client.cancel_task(uuid4())

    @pytest.mark.asyncio
    async def test_cancel_task_success(self):
        """Test cancel_task returns True on success."""
        client = AbsurdClient("postgresql://localhost/test")
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = True
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        client._pool = mock_pool
        
        result = await client.cancel_task(uuid4())
        
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self):
        """Test cancel_task returns False when task not found."""
        client = AbsurdClient("postgresql://localhost/test")
        
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = False
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        client._pool = mock_pool
        
        result = await client.cancel_task(uuid4())
        
        assert result is False
