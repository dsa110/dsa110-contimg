"""Caching layer for pipeline components.

Provides in-memory caching with TTL support and optional Redis backend.
Uses functools.lru_cache for simple cases, supports Redis for distributed caching.
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

T = TypeVar("T")

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache."""
        ...

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        ...

    @abstractmethod
    def list_keys(self, pattern: Optional[str] = None, limit: int = 100) -> List[str]:
        """List cache keys, optionally filtered by pattern."""
        ...


class InMemoryCache(CacheBackend):
    """In-memory cache with TTL support."""

    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._sets: int = 0
        self._deletes: int = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            self._misses += 1
            return None

        value, expiry = self._cache[key]
        if expiry > 0 and time.time() > expiry:
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        expiry = time.time() + ttl if ttl else 0
        self._cache[key] = (value, expiry)
        self._sets += 1

    def delete(self, key: str) -> None:
        """Delete value from cache."""
        if key in self._cache:
            self._cache.pop(key, None)
            self._deletes += 1

    def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        # Count active (non-expired) keys
        now = time.time()
        active_keys = sum(1 for _, expiry in self._cache.values() if expiry == 0 or expiry > now)

        return {
            "backend_type": "InMemoryCache",
            "total_keys": len(self._cache),
            "active_keys": active_keys,
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "deletes": self._deletes,
            "hit_rate": round(hit_rate, 2),
            "miss_rate": round(100 - hit_rate, 2) if total_requests > 0 else 0.0,
            "total_requests": total_requests,
        }

    def list_keys(self, pattern: Optional[str] = None, limit: int = 100) -> List[str]:
        """List cache keys, optionally filtered by pattern."""
        keys = list(self._cache.keys())

        if pattern:
            import fnmatch

            keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]

        return keys[:limit]


class RedisCache(CacheBackend):
    """Redis cache backend."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """Initialize Redis cache."""
        if not REDIS_AVAILABLE:
            raise ImportError("redis package not available")
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = self.client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        if ttl:
            self.client.setex(key, int(ttl), value)
        else:
            self.client.set(key, value)

    def delete(self, key: str) -> None:
        """Delete value from cache."""
        self.client.delete(key)

    def clear(self) -> None:
        """Clear all cache."""
        self.client.flushdb()

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        info = self.client.info("stats")
        self.client.info("keyspace")

        # Count keys
        total_keys = self.client.dbsize()

        # Get hit/miss from Redis INFO stats
        keyspace_hits = info.get("keyspace_hits", 0)
        keyspace_misses = info.get("keyspace_misses", 0)
        total_requests = keyspace_hits + keyspace_misses
        hit_rate = (keyspace_hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "backend_type": "RedisCache",
            "total_keys": total_keys,
            "active_keys": total_keys,  # Redis doesn't track expired separately
            "hits": keyspace_hits,
            "misses": keyspace_misses,
            "sets": info.get("total_commands_processed", 0),  # Approximate
            "deletes": 0,  # Redis doesn't track this separately
            "hit_rate": round(hit_rate, 2),
            "miss_rate": round(100 - hit_rate, 2) if total_requests > 0 else 0.0,
            "total_requests": total_requests,
        }

    def list_keys(self, pattern: Optional[str] = None, limit: int = 100) -> List[str]:
        """List cache keys, optionally filtered by pattern."""
        if pattern:
            keys = list(self.client.scan_iter(match=pattern, count=limit))
        else:
            keys = list(self.client.scan_iter(count=limit))

        return keys[:limit]


# Global cache instance
_cache_backend: Optional[CacheBackend] = None


def get_cache_backend() -> CacheBackend:
    """Get cache backend instance."""
    global _cache_backend

    if _cache_backend is None:
        # Try Redis first, fall back to in-memory
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))

        if REDIS_AVAILABLE:
            try:
                _cache_backend = RedisCache(host=redis_host, port=redis_port)
                return _cache_backend
            except Exception:
                pass  # Fall back to in-memory

        _cache_backend = InMemoryCache()

    return _cache_backend


def cached_with_ttl(ttl_seconds: float = 3600.0, key_prefix: str = ""):
    """Decorator for caching function results with TTL.

    Args:
        ttl_seconds: Time to live in seconds
        key_prefix: Prefix for cache keys

    Usage:
        @cached_with_ttl(ttl_seconds=3600)
        def expensive_function(arg1, arg2):
            # Expensive computation
            return result
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache = get_cache_backend()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.append(str(hash(args)))
            if kwargs:
                key_parts.append(str(hash(tuple(sorted(kwargs.items())))))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl_seconds)
            return result

        # Add cache management methods
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_delete = lambda *a, **kw: cache.delete(
            ":".join(
                [
                    key_prefix,
                    func.__name__,
                    str(hash(a)),
                    str(hash(tuple(sorted(kw.items())))),
                ]
            )
        )

        return wrapper

    return decorator


# Pre-configured cache decorators

cache_variability_stats = cached_with_ttl(ttl_seconds=3600.0, key_prefix="variability_stats")
cache_reference_sources = cached_with_ttl(ttl_seconds=1800.0, key_prefix="reference_sources")
cache_calibration_tables = cached_with_ttl(ttl_seconds=7200.0, key_prefix="calibration_tables")
cache_catalog_queries = cached_with_ttl(ttl_seconds=3600.0, key_prefix="catalog")


# Convenience functions for common caching patterns


def cache_variability_stats_for_source(source_id: str, stats: dict, ttl: float = 3600.0):
    """Cache variability stats for a source."""
    cache = get_cache_backend()
    cache.set(f"variability_stats:{source_id}", stats, ttl=ttl)


def get_cached_variability_stats(source_id: str) -> Optional[dict]:
    """Get cached variability stats for a source."""
    cache = get_cache_backend()
    return cache.get(f"variability_stats:{source_id}")


def cache_reference_sources_for_field(
    ra_deg: float, dec_deg: float, sources: list, ttl: float = 1800.0
):
    """Cache reference sources for a field."""
    cache = get_cache_backend()
    key = f"reference_sources:{ra_deg:.6f}:{dec_deg:.6f}"
    cache.set(key, sources, ttl=ttl)


def get_cached_reference_sources(ra_deg: float, dec_deg: float) -> Optional[list]:
    """Get cached reference sources for a field."""
    cache = get_cache_backend()
    key = f"reference_sources:{ra_deg:.6f}:{dec_deg:.6f}"
    return cache.get(key)
