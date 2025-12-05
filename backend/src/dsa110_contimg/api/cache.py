"""
Redis caching layer for the DSA-110 Continuum Imaging Pipeline API.

This module provides TTL-based caching for frequently accessed data.
Cache invalidation is time-based (not event-driven) since the API is
read-only and the pipeline writes directly to SQLite.

Usage:
    from .cache import cache_manager, cached

    # Decorator for route handlers
    @cached("sources:list", ttl=300)
    async def list_sources(...):
        ...

    # Manual cache operations
    cache_manager.set("key", {"data": "value"}, ttl=60)
    data = cache_manager.get("key")
    cache_manager.invalidate("sources:*")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Optional

# Import Redis exception type with fallback
try:
    from redis.exceptions import RedisError
except ImportError:
    # Define a fallback if redis is not installed
    class RedisError(Exception):
        """Placeholder for redis.exceptions.RedisError when redis is not installed."""

        pass


logger = logging.getLogger(__name__)


def _get_cache_settings():
    """Get cache settings from centralized config."""
    try:
        from dsa110_contimg.config import get_settings

        settings = get_settings()
        return {
            "redis_url": getattr(settings.api, "redis_url", "redis://localhost:6379/0"),
            "redis_enabled": getattr(settings.api, "redis_cache_enabled", True),
            "default_ttl": getattr(settings.api, "redis_default_ttl", 300),
        }
    except ImportError:
        # Fallback to environment variables if settings not available
        return {
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            "redis_enabled": os.getenv("REDIS_CACHE_ENABLED", "true").lower() == "true",
            "default_ttl": int(os.getenv("REDIS_DEFAULT_TTL", "300")),
        }


# Load settings at module level (with lazy evaluation)
_cache_settings = None


def get_cache_settings():
    global _cache_settings
    if _cache_settings is None:
        _cache_settings = _get_cache_settings()
    return _cache_settings


def _get_redis_url():
    return get_cache_settings()["redis_url"]


def _get_redis_enabled():
    return get_cache_settings()["redis_enabled"]


def _get_default_ttl():
    return get_cache_settings()["default_ttl"]


# Redis connection settings (functions for lazy evaluation)
# Use these functions instead of module-level constants
REDIS_URL = None  # Deprecated: use _get_redis_url()
REDIS_ENABLED = None  # Deprecated: use _get_redis_enabled()
DEFAULT_TTL = None  # Deprecated: use _get_default_ttl()

# TTL configuration by cache key prefix
# Shorter TTL for frequently changing data, longer for static data
CACHE_TTL_CONFIG = {
    "stats": 30,  # Summary stats - refresh every 30s
    "sources:list": 300,  # Source list - 5 minutes
    "sources:detail": 300,  # Source detail - 5 minutes
    "images:list": 300,  # Image list - 5 minutes
    "images:detail": 600,  # Image detail - 10 minutes (rarely changes)
    "cal:tables": 3600,  # Calibrator catalog - 1 hour (nearly static)
    "cal:matches": 1800,  # Cal matches - 30 minutes
    "ms:metadata": 600,  # MS metadata - 10 minutes
    "jobs:list": 60,  # Job list - 1 minute (changes during runs)
}

# Keys that should NEVER be cached
# - Lightcurves without end_date (scientists expect current data)
# - Active job status
# - Real-time logs
CACHE_BLACKLIST = [
    "lightcurve:open",  # Open-ended lightcurve queries
    "jobs:active",  # Currently running jobs
    "logs:",  # Real-time logs
]


class CacheManager:
    """
    Redis cache manager with TTL-based expiration.

    Gracefully degrades if Redis is unavailable - all operations
    become no-ops and the API falls back to direct DB queries.
    """

    _instance: Optional["CacheManager"] = None

    def __init__(self):
        self.client = None
        self.enabled = _get_redis_enabled()
        self._connect()

    def _connect(self):
        """Establish Redis connection."""
        if not self.enabled:
            logger.info("Redis caching disabled via config")
            return

        try:
            import redis
            from redis.exceptions import RedisError

            redis_url = _get_redis_url()
            self.client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            self.client.ping()
            logger.info(f"Redis cache connected: {redis_url}")
        except ImportError:
            logger.warning("redis package not installed, caching disabled")
            self.enabled = False
        except RedisError as e:
            logger.warning(f"Redis connection failed: {e}, caching disabled")
            self.enabled = False
            self.client = None

    @classmethod
    def get_instance(cls) -> "CacheManager":
        """Get singleton cache manager instance."""
        if cls._instance is None:
            cls._instance = CacheManager()
        return cls._instance

    def _is_blacklisted(self, key: str) -> bool:
        """Check if key matches blacklist patterns."""
        return any(key.startswith(pattern) for pattern in CACHE_BLACKLIST)

    def _get_ttl(self, key: str, default_ttl: int) -> int:
        """Get TTL for a key based on prefix configuration."""
        for prefix, ttl in CACHE_TTL_CONFIG.items():
            if key.startswith(prefix):
                return ttl
        return default_ttl

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Returns None if key doesn't exist, is expired, or Redis unavailable.
        """
        if not self.enabled or not self.client:
            return None

        try:
            data = self.client.get(key)
            if data:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(data)
            logger.debug(f"Cache MISS: {key}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Cache JSON decode error for {key}: {e}")
            return None
        except RedisError as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: JSON-serializable value
            ttl: Time-to-live in seconds (uses config default if not specified)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        if self._is_blacklisted(key):
            logger.debug(f"Cache SKIP (blacklisted): {key}")
            return False

        try:
            ttl = ttl or self._get_ttl(key, _get_default_ttl())
            self.client.setex(key, ttl, json.dumps(value, default=str))
            logger.debug(f"Cache SET: {key} (TTL={ttl}s)")
            return True
        except (TypeError, ValueError) as e:
            logger.warning(f"Cache serialization error for {key}: {e}")
            return False
        except RedisError as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a specific key from cache."""
        if not self.enabled or not self.client:
            return False

        try:
            self.client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except RedisError as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False

    def invalidate(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.

        Args:
            pattern: Redis glob pattern (e.g., "sources:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.client:
            return 0

        try:
            keys = list(self.client.scan_iter(match=pattern, count=100))
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Cache INVALIDATE: {pattern} ({deleted} keys)")
                return deleted
            return 0
        except RedisError as e:
            logger.warning(f"Cache invalidate error for {pattern}: {e}")
            return 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        if not self.enabled or not self.client:
            return {"enabled": False, "status": "disabled"}

        try:
            info = self.client.info("stats")
            memory = self.client.info("memory")
            keyspace = self.client.info("keyspace")

            return {
                "enabled": True,
                "status": "connected",
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
                ),
                "memory_used_bytes": memory.get("used_memory", 0),
                "memory_used_human": memory.get("used_memory_human", "0B"),
                "total_keys": sum(
                    db.get("keys", 0) for db in keyspace.values() if isinstance(db, dict)
                ),
            }
        except RedisError as e:
            return {"enabled": True, "status": "error", "error": str(e)}


# Singleton instance
cache_manager = CacheManager.get_instance()


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from prefix and arguments.

    Args:
        prefix: Key prefix (e.g., "sources:list")
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        Cache key string
    """
    parts = [prefix]

    # Add positional args
    for arg in args:
        if arg is not None:
            parts.append(str(arg))

    # Add sorted kwargs
    for key in sorted(kwargs.keys()):
        value = kwargs[key]
        if value is not None:
            parts.append(f"{key}={value}")

    key = ":".join(parts)

    # Hash if too long
    if len(key) > 200:
        hash_suffix = hashlib.md5(key.encode()).hexdigest()[:12]
        key = f"{prefix}:hash:{hash_suffix}"

    return key


def cached(
    prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
):
    """
    Decorator for caching async route handler responses.

    Args:
        prefix: Cache key prefix
        ttl: Time-to-live in seconds (uses config default if not specified)
        key_builder: Custom function to build cache key from args/kwargs

    Example:
        @cached("sources:list", ttl=300)
        async def list_sources(limit: int = 100, offset: int = 0):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = make_cache_key(prefix, **kwargs)

            # Try cache first
            cached_data = cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data

            # Call actual function
            result = await func(*args, **kwargs)

            # Cache the result if it's JSON-serializable
            if isinstance(result, (dict, list)):
                cache_manager.set(cache_key, result, ttl)
            elif hasattr(result, "model_dump"):
                # Pydantic model
                cache_manager.set(cache_key, result.model_dump(), ttl)
            elif hasattr(result, "dict"):
                # Pydantic v1 model
                cache_manager.set(cache_key, result.dict(), ttl)

            return result

        return wrapper

    return decorator


def cache_lightcurve_key(source_id: str, start_mjd: float = None, end_mjd: float = None) -> str:
    """
    Build cache key for lightcurve queries.

    Only caches queries with explicit end_date to ensure scientists
    always get current data for open-ended queries.
    """
    if end_mjd is None:
        # Open-ended query - use blacklisted prefix to prevent caching
        return f"lightcurve:open:{source_id}"

    return make_cache_key("lightcurve", source_id, start=start_mjd, end=end_mjd)
