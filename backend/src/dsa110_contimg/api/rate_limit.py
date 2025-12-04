"""
Rate limiting middleware for the DSA-110 API.

Uses slowapi to implement request rate limiting with Redis backend.
Provides configurable limits per endpoint and client identification.
"""

import os
from typing import Callable, Optional

from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .client_ip import get_client_ip

API_KEY_HEADER_NAME = os.getenv("DSA110_API_KEY_HEADER", "X-API-Key")


def get_client_identifier(request: Request) -> str:
    """
    Get client identifier for rate limiting.
    
    Priority:
    1. API key (when provided)
    2. Hardened client IP (honors XFF only for trusted proxies)
    """
    api_key = request.headers.get(API_KEY_HEADER_NAME)
    if api_key:
        return f"apikey:{api_key[:8]}"
    
    return get_client_ip(request)


def create_limiter(
    storage_uri: Optional[str] = None,
    default_limits: Optional[list] = None,
    key_func: Optional[Callable] = None,
) -> Limiter:
    """
    Create and configure a rate limiter.
    
    Args:
        storage_uri: Redis URI for rate limit storage.
            Defaults to DSA110_REDIS_URL or memory storage.
        default_limits: Default rate limits applied to all routes.
            Defaults to ["1000 per hour", "100 per minute"].
        key_func: Function to extract client identifier.
            Defaults to get_client_identifier.
    
    Returns:
        Configured Limiter instance.
    """
    # Get Redis URI from environment or parameter
    if storage_uri is None:
        storage_uri = os.getenv("DSA110_REDIS_URL", "memory://")
    
    # Default rate limits
    if default_limits is None:
        default_limits = [
            os.getenv("DSA110_RATE_LIMIT_HOUR", "1000 per hour"),
            os.getenv("DSA110_RATE_LIMIT_MINUTE", "100 per minute"),
        ]
    
    # Use custom key function or default
    if key_func is None:
        key_func = get_client_identifier
    
    return Limiter(
        key_func=key_func,
        default_limits=default_limits,
        storage_uri=storage_uri,
        strategy="fixed-window",  # or "moving-window"
        headers_enabled=True,  # Include rate limit headers in response
    )


# Global limiter instance
limiter = create_limiter()


# Rate limit presets for different endpoint types
class RateLimits:
    """Predefined rate limits for different endpoint types."""
    
    # High-frequency endpoints (health checks, status)
    HIGH = "1000 per minute"
    
    # Standard read endpoints
    STANDARD = "100 per minute"
    
    # Write operations (require more resources)
    WRITE = "30 per minute"
    
    # Heavy operations (image generation, etc.)
    HEAVY = "10 per minute"
    
    # Authentication operations
    AUTH = "20 per minute"
    
    # Batch operations
    BATCH = "5 per minute"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    
    Returns a JSON response with rate limit information.
    """
    from fastapi.responses import JSONResponse
    
    # Extract limit details
    limit_value = str(exc.detail) if hasattr(exc, 'detail') else "Rate limit exceeded"
    
    response = JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Too many requests. {limit_value}",
            "retry_after": getattr(exc, 'retry_after', 60),
        }
    )
    
    # Add Retry-After header
    if hasattr(exc, 'retry_after'):
        response.headers["Retry-After"] = str(exc.retry_after)
    
    return response


def get_rate_limit_info(request: Request) -> dict:
    """
    Get current rate limit status for a client.
    
    Returns dict with:
        - limit: Maximum requests allowed
        - remaining: Requests remaining
        - reset: Timestamp when limit resets
    """
    # This would need access to the limiter's storage
    # For now, return placeholder
    return {
        "limit": 1000,
        "remaining": 999,
        "reset": 0,
    }


# Bypass rate limiting for certain conditions
def should_skip_rate_limit(request: Request) -> bool:
    """
    Check if request should bypass rate limiting.
    
    Returns True to skip rate limiting for:
    - Internal/localhost requests in development
    - Requests with special bypass header (if configured)
    """
    # Check for bypass in development
    if os.getenv("DSA110_RATE_LIMIT_DISABLED", "").lower() == "true":
        return True
    
    # Check for internal requests
    client_ip = get_client_ip(request)
    if client_ip in ["127.0.0.1", "::1", "localhost"]:
        if os.getenv("DSA110_ENV", "development") == "development":
            return True
    
    return False


# Decorator shortcuts for common rate limits
def limit_standard(func):
    """Apply standard rate limit to endpoint."""
    return limiter.limit(RateLimits.STANDARD)(func)


def limit_write(func):
    """Apply write operation rate limit to endpoint."""
    return limiter.limit(RateLimits.WRITE)(func)


def limit_heavy(func):
    """Apply heavy operation rate limit to endpoint."""
    return limiter.limit(RateLimits.HEAVY)(func)
