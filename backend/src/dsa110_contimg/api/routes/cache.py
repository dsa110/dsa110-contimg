"""
Cache routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import require_write_access, AuthContext
from ..cache import cache_manager

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("")
async def get_cache_stats():
    """
    Get Redis cache statistics.
    """
    return cache_manager.get_stats()


@router.post("/invalidate/{pattern}")
async def invalidate_cache(
    pattern: str,
    auth: AuthContext = Depends(require_write_access),
):
    """
    Invalidate cache keys matching pattern.
    
    Use glob patterns like:
    - `sources:*` - All source-related cache entries
    - `images:list:*` - All image list cache entries
    - `stats` - Stats cache entry
    
    Requires authentication with write access.
    """
    deleted = cache_manager.invalidate(pattern)
    return {
        "pattern": pattern,
        "keys_deleted": deleted,
    }


@router.post("/clear")
async def clear_cache(
    auth: AuthContext = Depends(require_write_access),
):
    """
    Clear all cache entries.
    
    Requires authentication with write access.
    """
    deleted = cache_manager.invalidate("*")
    return {
        "status": "cleared",
        "keys_deleted": deleted,
    }
