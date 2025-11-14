"""
Rate limiting middleware for FastAPI
Uses slowapi for rate limiting with Redis backend support
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Try to import slowapi
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    logger.warning("slowapi not available, rate limiting disabled")

# Global limiter instance
_limiter: Optional[Any] = None


def get_limiter() -> Optional[Any]:
    """Get or create rate limiter instance"""
    global _limiter

    if not SLOWAPI_AVAILABLE:
        return None

    if _limiter is None:
        # Try to use Redis for distributed rate limiting, fall back to memory
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                from slowapi import Limiter

                _limiter = Limiter(
                    key_func=get_remote_address,
                    storage_uri=redis_url,
                    default_limits=["1000/hour", "100/minute"],
                )
                logger.info(f"Rate limiter initialized with Redis: {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis rate limiter: {e}")
                # Fall back to memory-based limiter
                _limiter = Limiter(
                    key_func=get_remote_address,
                    default_limits=["1000/hour", "100/minute"],
                )
                logger.info("Rate limiter initialized with in-memory storage")
        else:
            # Memory-based limiter
            _limiter = Limiter(
                key_func=get_remote_address,
                default_limits=["1000/hour", "100/minute"],
            )
            logger.info("Rate limiter initialized with in-memory storage (no Redis)")

    return _limiter


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors"""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": exc.retry_after,
        },
        headers={"Retry-After": str(exc.retry_after)},
    )


def setup_rate_limiting(app: Any) -> None:
    """
    Setup rate limiting middleware for FastAPI app

    Args:
        app: FastAPI application instance
    """
    if not SLOWAPI_AVAILABLE:
        logger.warning("Rate limiting not available (slowapi not installed)")
        return

    limiter = get_limiter()
    if limiter is None:
        return

    # Add rate limiting middleware
    try:
        from slowapi.middleware import SlowAPIMiddleware

        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
        logger.info("Rate limiting middleware configured")
    except ImportError:
        logger.warning("SlowAPIMiddleware not available, rate limiting partially disabled")
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# Rate limit decorators for common use cases
def rate_limit_light():
    """Light rate limit: 1000/hour, 100/minute"""
    limiter = get_limiter()
    if limiter:
        return limiter.limit("1000/hour, 100/minute")
    return lambda f: f  # No-op if limiter not available


def rate_limit_medium():
    """Medium rate limit: 500/hour, 50/minute"""
    limiter = get_limiter()
    if limiter:
        return limiter.limit("500/hour, 50/minute")
    return lambda f: f


def rate_limit_heavy():
    """Heavy rate limit: 100/hour, 10/minute"""
    limiter = get_limiter()
    if limiter:
        return limiter.limit("100/hour, 10/minute")
    return lambda f: f


def rate_limit_custom(limits: str):
    """Custom rate limit"""
    limiter = get_limiter()
    if limiter:
        return limiter.limit(limits)
    return lambda f: f
