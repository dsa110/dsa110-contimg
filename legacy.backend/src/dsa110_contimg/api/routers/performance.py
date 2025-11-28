"""
API endpoints for performance monitoring
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter

from dsa110_contimg.api.caching import get_cache
from dsa110_contimg.api.rate_limiting import SLOWAPI_AVAILABLE, get_limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics")
def get_performance_metrics() -> Dict[str, Any]:
    """
    Get performance metrics including cache and rate limiting statistics
    """
    metrics: Dict[str, Any] = {
        "timestamp": time.time(),
        "cache": {},
        "rate_limiting": {},
    }

    # Cache metrics
    try:
        cache = get_cache()
        cache_stats = cache.get_stats()
        metrics["cache"] = cache_stats
    except Exception as e:
        logger.warning(f"Failed to get cache stats: {e}")
        metrics["cache"] = {"error": str(e)}

    # Rate limiting metrics
    if SLOWAPI_AVAILABLE:
        try:
            limiter = get_limiter()
            if limiter:
                metrics["rate_limiting"] = {
                    "enabled": True,
                    "backend": "redis" if os.getenv("REDIS_URL") else "memory",
                }
            else:
                metrics["rate_limiting"] = {"enabled": False}
        except Exception as e:
            logger.warning(f"Failed to get rate limiter stats: {e}")
            metrics["rate_limiting"] = {"error": str(e)}
    else:
        metrics["rate_limiting"] = {"enabled": False, "reason": "slowapi not available"}

    return metrics


@router.get("/cache/stats")
def get_cache_stats() -> Dict[str, Any]:
    """Get detailed cache statistics"""
    cache = get_cache()
    return cache.get_stats()


@router.get("/rate-limiting/stats")
def get_rate_limiting_stats() -> Dict[str, Any]:
    """Get rate limiting statistics"""
    if not SLOWAPI_AVAILABLE:
        return {"enabled": False, "reason": "slowapi not available"}

    limiter = get_limiter()
    if limiter is None:
        return {"enabled": False, "reason": "limiter not initialized"}

    return {
        "enabled": True,
        "backend": "redis" if os.getenv("REDIS_URL") else "memory",
        "default_limits": "1000/hour, 100/minute",
    }


# Import os for environment variables
import os
