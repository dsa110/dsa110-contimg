"""
Caching utilities for API responses
Supports Redis for distributed caching with in-memory fallback
"""

from __future__ import annotations

import json
import logging
import os
import time
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Try to import Redis, fall back to in-memory cache if not available
try:
    import redis
    from redis.exceptions import ConnectionError as RedisConnectionError

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache fallback")

# In-memory cache fallback
_memory_cache: dict[str, tuple[float, Any]] = {}


class CacheBackend:
    """Unified cache interface supporting Redis and in-memory fallback"""

    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 300):
        """
        Initialize cache backend

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            default_ttl: Default TTL in seconds for cached items
        """
        self.default_ttl = default_ttl
        self.redis_client: Optional[Any] = None
        self.use_redis = False

        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                self.use_redis = True
                logger.info(f"Connected to Redis cache at {redis_url}")
            except (RedisConnectionError, Exception) as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory cache.")
                self.redis_client = None
                self.use_redis = False

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
                return None
        else:
            # In-memory cache
            if key in _memory_cache:
                expiry, value = _memory_cache[key]
                if time.time() < expiry:
                    return value
                else:
                    del _memory_cache[key]
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        ttl = ttl or self.default_ttl

        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
                return False
        else:
            # In-memory cache
            expiry = time.time() + ttl
            _memory_cache[key] = (expiry, value)
            # Clean up expired entries periodically
            if len(_memory_cache) > 10000:
                self._cleanup_memory_cache()
            return True

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
                return False
        else:
            # In-memory cache
            _memory_cache.pop(key, None)
            return True

    def clear(self) -> bool:
        """Clear all cache"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.flushdb()
                return True
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
                return False
        else:
            # In-memory cache
            _memory_cache.clear()
            return True

    def _cleanup_memory_cache(self) -> None:
        """Remove expired entries from in-memory cache"""
        current_time = time.time()
        expired_keys = [key for key, (expiry, _) in _memory_cache.items() if current_time >= expiry]
        for key in expired_keys:
            del _memory_cache[key]

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        if self.use_redis and self.redis_client:
            try:
                info = self.redis_client.info("stats")
                return {
                    "backend": "redis",
                    "keys": self.redis_client.dbsize(),
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0),
                }
            except Exception as e:
                logger.warning(f"Redis stats error: {e}")
                return {"backend": "redis", "error": str(e)}
        else:
            return {
                "backend": "memory",
                "keys": len(_memory_cache),
                "hits": 0,  # Not tracked for in-memory
                "misses": 0,
            }


# Global cache instance (initialized in app startup)
_cache_backend: Optional[CacheBackend] = None


def get_cache() -> CacheBackend:
    """Get global cache backend instance"""
    global _cache_backend
    if _cache_backend is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _cache_backend = CacheBackend(redis_url=redis_url)
    return _cache_backend


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache = get_cache()
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache = get_cache()
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result

        # Return appropriate wrapper based on whether function is async
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
