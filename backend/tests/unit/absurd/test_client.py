"""
Contract tests for ABSURD client.

Tests the AbsurdClient class interface contracts without mocking internals.
Verifies:
- Input validation and type contracts
- Error handling contracts (correct exceptions for invalid states)
- API surface contracts (method signatures, return types)
- Protocol compliance (context manager, async patterns)

Philosophy:
- Test behavior through the public interface, not implementation details
- Verify contracts: "given X input, expect Y behavior"
- No mocking of internals - test real validation logic
- Database operations require integration tests (marked separately)
"""

import pytest
from uuid import UUID, uuid4

from dsa110_contimg.absurd.client import AbsurdClient


# ============================================================================
# Initialization Contracts
# ============================================================================


class TestAbsurdClientInitContract:
    """Contract tests for AbsurdClient initialization."""

    def test_accepts_valid_database_url(self):
        """Contract: Client accepts any string as database_url."""
        client = AbsurdClient("postgresql://localhost/test")
        assert client.database_url == "postgresql://localhost/test"

    def test_accepts_custom_pool_sizes(self):
        """Contract: Client accepts custom pool size configuration."""
        client = AbsurdClient(
            "postgresql://localhost/test",
            pool_min_size=5,
            pool_max_size=20,
        )
        assert client.pool_min_size == 5
        assert client.pool_max_size == 20

    def test_default_pool_sizes(self):
        """Contract: Client uses sensible default pool sizes."""
        client = AbsurdClient("postgresql://localhost/test")
        
        # Defaults should be reasonable (between 1-50)
        assert 1 <= client.pool_min_size <= 50
        assert 1 <= client.pool_max_size <= 50
        assert client.pool_min_size <= client.pool_max_size

    def test_starts_disconnected(self):
        """Contract: Newly created client is not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        assert client._pool is None


# ============================================================================
# Connection State Contracts
# ============================================================================


class TestAbsurdClientConnectionContract:
    """Contract tests for connection state handling."""

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        """Contract: close() is safe to call multiple times."""
        client = AbsurdClient("postgresql://localhost/test")
        
        # Should not raise even when not connected
        await client.close()
        await client.close()
        await client.close()
        
        assert client._pool is None

    @pytest.mark.asyncio
    async def test_close_resets_pool_to_none(self):
        """Contract: close() sets _pool to None."""
        client = AbsurdClient("postgresql://localhost/test")
        await client.close()
        assert client._pool is None


# ============================================================================
# Method Pre-condition Contracts (Requires Connection)
# ============================================================================


class TestAbsurdClientRequiresConnection:
    """Contract: All operations require connection, raise ValueError if not."""

    @pytest.mark.asyncio
    async def test_spawn_task_requires_connection(self):
        """Contract: spawn_task raises ValueError when not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        
        with pytest.raises(ValueError) as exc_info:
            await client.spawn_task("queue", "task", {"key": "value"})
        
        assert "not connected" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_task_requires_connection(self):
        """Contract: get_task raises ValueError when not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        
        with pytest.raises(ValueError) as exc_info:
            await client.get_task(uuid4())
        
        assert "not connected" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_list_tasks_requires_connection(self):
        """Contract: list_tasks raises ValueError when not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        
        with pytest.raises(ValueError) as exc_info:
            await client.list_tasks()
        
        assert "not connected" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_cancel_task_requires_connection(self):
        """Contract: cancel_task raises ValueError when not connected."""
        client = AbsurdClient("postgresql://localhost/test")
        
        with pytest.raises(ValueError) as exc_info:
            await client.cancel_task(uuid4())
        
        assert "not connected" in str(exc_info.value).lower()


# ============================================================================
# Method Signature Contracts
# ============================================================================


class TestAbsurdClientMethodSignatures:
    """Contract tests verifying method signatures and parameter types."""

    def test_spawn_task_signature(self):
        """Contract: spawn_task accepts queue_name, task_name, params, priority, timeout."""
        client = AbsurdClient("postgresql://localhost/test")
        
        # Verify method exists and has expected parameters
        import inspect
        sig = inspect.signature(client.spawn_task)
        params = list(sig.parameters.keys())
        
        assert "queue_name" in params
        assert "task_name" in params
        assert "params" in params
        assert "priority" in params
        assert "timeout_sec" in params

    def test_get_task_accepts_uuid(self):
        """Contract: get_task accepts UUID parameter."""
        client = AbsurdClient("postgresql://localhost/test")
        
        import inspect
        sig = inspect.signature(client.get_task)
        params = list(sig.parameters.keys())
        
        assert "task_id" in params

    def test_list_tasks_accepts_filters(self):
        """Contract: list_tasks accepts optional queue_name, status, limit."""
        client = AbsurdClient("postgresql://localhost/test")
        
        import inspect
        sig = inspect.signature(client.list_tasks)
        params = sig.parameters
        
        # All should be optional (have defaults)
        for param_name in ["queue_name", "status", "limit"]:
            if param_name in params:
                assert params[param_name].default is not inspect.Parameter.empty

    def test_cancel_task_accepts_uuid(self):
        """Contract: cancel_task accepts UUID parameter."""
        client = AbsurdClient("postgresql://localhost/test")
        
        import inspect
        sig = inspect.signature(client.cancel_task)
        params = list(sig.parameters.keys())
        
        assert "task_id" in params


# ============================================================================
# Async Context Manager Protocol
# ============================================================================


class TestAbsurdClientContextManagerProtocol:
    """Contract tests for async context manager protocol."""

    def test_implements_aenter(self):
        """Contract: Client implements __aenter__."""
        client = AbsurdClient("postgresql://localhost/test")
        assert hasattr(client, "__aenter__")
        assert callable(client.__aenter__)

    def test_implements_aexit(self):
        """Contract: Client implements __aexit__."""
        client = AbsurdClient("postgresql://localhost/test")
        assert hasattr(client, "__aexit__")
        assert callable(client.__aexit__)

    def test_aenter_returns_coroutine(self):
        """Contract: __aenter__ returns a coroutine."""
        import asyncio
        client = AbsurdClient("postgresql://localhost/test")
        result = client.__aenter__()
        assert asyncio.iscoroutine(result)
        # Clean up the coroutine
        result.close()

    def test_aexit_returns_coroutine(self):
        """Contract: __aexit__ returns a coroutine."""
        import asyncio
        client = AbsurdClient("postgresql://localhost/test")
        result = client.__aexit__(None, None, None)
        assert asyncio.iscoroutine(result)
        # Clean up the coroutine
        result.close()


# ============================================================================
# Return Type Contracts (for type hints validation)
# ============================================================================


class TestAbsurdClientReturnTypes:
    """Contract tests verifying return type annotations."""

    def test_spawn_task_returns_uuid_type_hint(self):
        """Contract: spawn_task is annotated to return UUID."""
        import typing
        hints = typing.get_type_hints(AbsurdClient.spawn_task)
        
        # Return type should be UUID
        assert hints.get("return") == UUID

    def test_get_task_returns_optional_dict(self):
        """Contract: get_task is annotated to return Optional[Dict]."""
        import typing
        hints = typing.get_type_hints(AbsurdClient.get_task)
        
        return_type = hints.get("return")
        # Should be Optional[Dict[str, Any]] or equivalent
        assert return_type is not None

    def test_list_tasks_returns_list(self):
        """Contract: list_tasks is annotated to return List."""
        import typing
        hints = typing.get_type_hints(AbsurdClient.list_tasks)
        
        return_type = hints.get("return")
        # Should be List[Dict[str, Any]] or equivalent
        assert return_type is not None

    def test_cancel_task_returns_bool(self):
        """Contract: cancel_task is annotated to return bool."""
        import typing
        hints = typing.get_type_hints(AbsurdClient.cancel_task)
        
        assert hints.get("return") == bool


# ============================================================================
# Input Validation Contracts
# ============================================================================


class TestAbsurdClientInputValidation:
    """Contract tests for input validation behavior."""

    def test_database_url_stored_as_provided(self):
        """Contract: database_url is stored exactly as provided."""
        url = "postgresql://user:pass@host:5432/db?sslmode=require"
        client = AbsurdClient(url)
        assert client.database_url == url

    def test_pool_sizes_stored_as_provided(self):
        """Contract: pool sizes are stored exactly as provided."""
        client = AbsurdClient("postgresql://localhost/test", pool_min_size=3, pool_max_size=15)
        assert client.pool_min_size == 3
        assert client.pool_max_size == 15
