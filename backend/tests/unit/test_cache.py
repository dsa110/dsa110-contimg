"""
Unit tests for cache.py - Redis caching layer.

Tests for:
- CacheManager class
- Cache key generation
- Cache decorator
- TTL configuration
- Blacklist handling
"""

import json
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from dsa110_contimg.api.cache import (
    CacheManager,
    cache_manager,
    make_cache_key,
    cached,
    cache_lightcurve_key,
    CACHE_TTL_CONFIG,
    CACHE_BLACKLIST,
    DEFAULT_TTL,
)


class TestMakeCacheKey:
    """Tests for make_cache_key function."""

    def test_prefix_only(self):
        """Test key with only prefix."""
        key = make_cache_key("sources:list")
        assert key == "sources:list"

    def test_with_positional_args(self):
        """Test key with positional arguments."""
        key = make_cache_key("sources:detail", "src-123")
        assert key == "sources:detail:src-123"

    def test_with_kwargs(self):
        """Test key with keyword arguments."""
        key = make_cache_key("sources:list", limit=100, offset=0)
        assert key == "sources:list:limit=100:offset=0"

    def test_kwargs_sorted(self):
        """Test kwargs are sorted alphabetically."""
        key = make_cache_key("test", zebra=1, apple=2, mango=3)
        assert key == "test:apple=2:mango=3:zebra=1"

    def test_none_values_excluded(self):
        """Test None values are excluded from key."""
        key = make_cache_key("test", foo=None, bar="value")
        assert key == "test:bar=value"

    def test_mixed_args_and_kwargs(self):
        """Test key with both positional and keyword args."""
        key = make_cache_key("images:detail", "img-456", format="fits")
        assert key == "images:detail:img-456:format=fits"

    def test_long_key_hashed(self):
        """Test long keys are hashed."""
        # Create a very long key
        long_value = "x" * 300
        key = make_cache_key("test", value=long_value)
        
        assert key.startswith("test:hash:")
        assert len(key) < 50  # Should be much shorter after hashing


class TestCacheLightcurveKey:
    """Tests for cache_lightcurve_key function."""

    def test_closed_range(self):
        """Test lightcurve key with explicit end date."""
        key = cache_lightcurve_key("src-123", start_mjd=60000.0, end_mjd=60100.0)
        assert key.startswith("lightcurve:")
        assert "src-123" in key
        assert "60000.0" in key
        assert "60100.0" in key

    def test_open_ended_uses_blacklist_prefix(self):
        """Test open-ended query uses blacklisted prefix."""
        key = cache_lightcurve_key("src-123", start_mjd=60000.0, end_mjd=None)
        assert key.startswith("lightcurve:open:")
        # This should match the blacklist pattern


class TestCacheManagerDisabled:
    """Tests for CacheManager when Redis is disabled."""

    @pytest.fixture
    def disabled_manager(self):
        """Create a CacheManager with caching disabled."""
        with patch.dict("os.environ", {"REDIS_CACHE_ENABLED": "false"}):
            manager = CacheManager()
            manager.enabled = False
            manager.client = None
            return manager

    def test_get_returns_none(self, disabled_manager):
        """Test get returns None when disabled."""
        result = disabled_manager.get("any:key")
        assert result is None

    def test_set_returns_false(self, disabled_manager):
        """Test set returns False when disabled."""
        result = disabled_manager.set("any:key", {"data": "value"})
        assert result is False

    def test_delete_returns_false(self, disabled_manager):
        """Test delete returns False when disabled."""
        result = disabled_manager.delete("any:key")
        assert result is False

    def test_invalidate_returns_zero(self, disabled_manager):
        """Test invalidate returns 0 when disabled."""
        result = disabled_manager.invalidate("pattern:*")
        assert result == 0

    def test_get_stats_shows_disabled(self, disabled_manager):
        """Test get_stats shows disabled status."""
        stats = disabled_manager.get_stats()
        assert stats["enabled"] is False
        assert stats["status"] == "disabled"


class TestCacheManagerWithMock:
    """Tests for CacheManager with mocked Redis client."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = MagicMock()
        mock.ping.return_value = True
        mock.get.return_value = None
        mock.setex.return_value = True
        mock.delete.return_value = 1
        mock.scan_iter.return_value = iter([])
        return mock

    @pytest.fixture
    def manager_with_mock(self, mock_redis):
        """Create a CacheManager with mocked Redis."""
        manager = CacheManager.__new__(CacheManager)
        manager.enabled = True
        manager.client = mock_redis
        return manager

    def test_get_cache_hit(self, manager_with_mock, mock_redis):
        """Test cache hit returns deserialized data."""
        cached_data = {"name": "test", "value": 123}
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = manager_with_mock.get("test:key")
        
        assert result == cached_data
        mock_redis.get.assert_called_once_with("test:key")

    def test_get_cache_miss(self, manager_with_mock, mock_redis):
        """Test cache miss returns None."""
        mock_redis.get.return_value = None
        
        result = manager_with_mock.get("test:key")
        
        assert result is None

    def test_get_json_decode_error(self, manager_with_mock, mock_redis):
        """Test invalid JSON returns None."""
        mock_redis.get.return_value = "not valid json"
        
        result = manager_with_mock.get("test:key")
        
        assert result is None

    def test_set_success(self, manager_with_mock, mock_redis):
        """Test successful cache set."""
        result = manager_with_mock.set("test:key", {"data": "value"}, ttl=60)
        
        assert result is True
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == "test:key"
        assert args[1] == 60

    def test_set_uses_config_ttl(self, manager_with_mock, mock_redis):
        """Test set uses TTL from config for known prefixes."""
        # stats prefix has 30s TTL in config
        manager_with_mock.set("stats", {"count": 100})
        
        args = mock_redis.setex.call_args[0]
        assert args[1] == CACHE_TTL_CONFIG["stats"]

    def test_set_blacklisted_key(self, manager_with_mock, mock_redis):
        """Test blacklisted keys are not cached."""
        result = manager_with_mock.set("lightcurve:open:src-123", {"data": []})
        
        assert result is False
        mock_redis.setex.assert_not_called()

    def test_delete_calls_redis(self, manager_with_mock, mock_redis):
        """Test delete calls Redis."""
        result = manager_with_mock.delete("test:key")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("test:key")

    def test_invalidate_with_matches(self, manager_with_mock, mock_redis):
        """Test invalidate with matching keys."""
        mock_redis.scan_iter.return_value = iter(["test:1", "test:2", "test:3"])
        mock_redis.delete.return_value = 3
        
        result = manager_with_mock.invalidate("test:*")
        
        assert result == 3

    def test_invalidate_no_matches(self, manager_with_mock, mock_redis):
        """Test invalidate with no matching keys."""
        mock_redis.scan_iter.return_value = iter([])
        
        result = manager_with_mock.invalidate("nonexistent:*")
        
        assert result == 0

    def test_get_stats_success(self, manager_with_mock, mock_redis):
        """Test get_stats returns formatted stats."""
        mock_redis.info.side_effect = [
            {"keyspace_hits": 100, "keyspace_misses": 10},  # stats
            {"used_memory": 1024, "used_memory_human": "1K"},  # memory
            {"db0": {"keys": 50}},  # keyspace
        ]
        
        stats = manager_with_mock.get_stats()
        
        assert stats["enabled"] is True
        assert stats["status"] == "connected"
        assert stats["hits"] == 100
        assert stats["misses"] == 10
        assert stats["total_keys"] == 50


class TestCacheManagerBlacklist:
    """Tests for cache blacklist functionality."""

    def test_blacklist_contains_open_lightcurves(self):
        """Test blacklist includes open-ended lightcurve queries."""
        assert any("lightcurve:open" in pattern for pattern in CACHE_BLACKLIST)

    def test_blacklist_contains_active_jobs(self):
        """Test blacklist includes active jobs."""
        assert any("jobs:active" in pattern for pattern in CACHE_BLACKLIST)

    def test_blacklist_contains_logs(self):
        """Test blacklist includes real-time logs."""
        assert any("logs:" in pattern for pattern in CACHE_BLACKLIST)


class TestCacheTTLConfig:
    """Tests for cache TTL configuration."""

    def test_stats_short_ttl(self):
        """Test stats have short TTL."""
        assert CACHE_TTL_CONFIG["stats"] <= 60

    def test_calibrator_long_ttl(self):
        """Test calibrator tables have long TTL."""
        assert CACHE_TTL_CONFIG["cal:tables"] >= 3600

    def test_job_list_reasonable_ttl(self):
        """Test job list has reasonable TTL for changing data."""
        assert CACHE_TTL_CONFIG["jobs:list"] <= 120


class TestCachedDecorator:
    """Tests for @cached decorator."""

    @pytest.mark.asyncio
    async def test_decorator_returns_cached_value(self):
        """Test decorator returns cached value on hit."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.get.return_value = {"cached": True}
        mock_manager.set.return_value = True
        
        with patch("dsa110_contimg.api.cache.cache_manager", mock_manager):
            @cached("test:prefix")
            async def test_func(arg1: str) -> dict:
                return {"fresh": True, "arg": arg1}
            
            result = await test_func(arg1="value")
            
            assert result == {"cached": True}
            mock_manager.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_calls_function_on_miss(self):
        """Test decorator calls function on cache miss."""
        mock_manager = MagicMock()
        mock_manager.get.return_value = None  # Cache miss
        mock_manager.set.return_value = True
        
        call_count = 0
        
        with patch("dsa110_contimg.api.cache.cache_manager", mock_manager):
            @cached("test:prefix")
            async def test_func() -> dict:
                nonlocal call_count
                call_count += 1
                return {"fresh": True}
            
            result = await test_func()
            
            assert result == {"fresh": True}
            assert call_count == 1
            mock_manager.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_caches_dict_result(self):
        """Test decorator caches dict results."""
        mock_manager = MagicMock()
        mock_manager.get.return_value = None
        mock_manager.set.return_value = True
        
        with patch("dsa110_contimg.api.cache.cache_manager", mock_manager):
            @cached("test:prefix", ttl=120)
            async def test_func() -> dict:
                return {"data": "value"}
            
            await test_func()
            
            mock_manager.set.assert_called_once()
            call_args = mock_manager.set.call_args
            assert call_args[0][1] == {"data": "value"}
            assert call_args[0][2] == 120

    @pytest.mark.asyncio
    async def test_decorator_caches_list_result(self):
        """Test decorator caches list results."""
        mock_manager = MagicMock()
        mock_manager.get.return_value = None
        mock_manager.set.return_value = True
        
        with patch("dsa110_contimg.api.cache.cache_manager", mock_manager):
            @cached("test:prefix")
            async def test_func() -> list:
                return [1, 2, 3]
            
            await test_func()
            
            mock_manager.set.assert_called_once()
            call_args = mock_manager.set.call_args
            assert call_args[0][1] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_decorator_with_custom_key_builder(self):
        """Test decorator with custom key builder."""
        mock_manager = MagicMock()
        mock_manager.get.return_value = None
        mock_manager.set.return_value = True
        
        def custom_builder(*args, **kwargs):
            return f"custom:{kwargs.get('id', 'default')}"
        
        with patch("dsa110_contimg.api.cache.cache_manager", mock_manager):
            @cached("test", key_builder=custom_builder)
            async def test_func(id: str) -> dict:
                return {"id": id}
            
            await test_func(id="123")
            
            mock_manager.get.assert_called_once_with("custom:123")


class TestCacheManagerSingleton:
    """Tests for CacheManager singleton pattern."""

    def test_get_instance_returns_same_object(self):
        """Test get_instance returns singleton."""
        with patch.object(CacheManager, "_instance", None):
            instance1 = CacheManager.get_instance()
            instance2 = CacheManager.get_instance()
            assert instance1 is instance2


class TestCacheManagerErrorHandling:
    """Tests for CacheManager error handling."""

    @pytest.fixture
    def manager_with_failing_redis(self):
        """Create manager with Redis that raises errors."""
        from redis.exceptions import RedisError
        
        mock = MagicMock()
        mock.get.side_effect = RedisError("Connection lost")
        mock.setex.side_effect = RedisError("Connection lost")
        mock.delete.side_effect = RedisError("Connection lost")
        mock.scan_iter.side_effect = RedisError("Connection lost")
        mock.info.side_effect = RedisError("Connection lost")
        
        manager = CacheManager.__new__(CacheManager)
        manager.enabled = True
        manager.client = mock
        return manager

    def test_get_handles_redis_error(self, manager_with_failing_redis):
        """Test get handles Redis errors gracefully."""
        result = manager_with_failing_redis.get("test:key")
        assert result is None

    def test_set_handles_redis_error(self, manager_with_failing_redis):
        """Test set handles Redis errors gracefully."""
        result = manager_with_failing_redis.set("test:key", {"data": "value"})
        assert result is False

    def test_delete_handles_redis_error(self, manager_with_failing_redis):
        """Test delete handles Redis errors gracefully."""
        result = manager_with_failing_redis.delete("test:key")
        assert result is False

    def test_invalidate_handles_redis_error(self, manager_with_failing_redis):
        """Test invalidate handles Redis errors gracefully."""
        result = manager_with_failing_redis.invalidate("test:*")
        assert result == 0

    def test_get_stats_handles_redis_error(self, manager_with_failing_redis):
        """Test get_stats handles Redis errors gracefully."""
        stats = manager_with_failing_redis.get_stats()
        assert stats["enabled"] is True
        assert stats["status"] == "error"
        assert "error" in stats
