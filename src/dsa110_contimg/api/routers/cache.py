"""API endpoints for cache monitoring and management."""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional

from dsa110_contimg.pipeline.caching import get_cache_backend

router = APIRouter()


@router.get("/stats")
def get_cache_statistics():
    """Get cache statistics."""
    cache = get_cache_backend()
    stats = cache.get_statistics()
    return stats


@router.get("/keys")
def list_cache_keys(
    pattern: Optional[str] = Query(None, description="Filter keys by pattern (supports wildcards)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of keys to return"),
):
    """List cache keys."""
    cache = get_cache_backend()
    keys = cache.list_keys(pattern=pattern, limit=limit)
    
    # Get additional info for each key
    keys_with_info = []
    for key in keys:
        value = cache.get(key)
        keys_with_info.append({
            "key": key,
            "exists": value is not None,
            "has_value": value is not None,
        })
    
    return {
        "keys": keys_with_info,
        "total": len(keys_with_info),
    }


@router.get("/keys/{key:path}")
def get_cache_key(key: str):
    """Get details for a specific cache key."""
    cache = get_cache_backend()
    value = cache.get(key)
    
    if value is None:
        raise HTTPException(status_code=404, detail=f"Cache key '{key}' not found")
    
    return {
        "key": key,
        "value": value,
        "value_type": type(value).__name__,
        "value_size": len(str(value)) if value else 0,
    }


@router.delete("/keys/{key:path}")
def delete_cache_key(key: str):
    """Delete a specific cache key."""
    cache = get_cache_backend()
    value = cache.get(key)
    
    if value is None:
        raise HTTPException(status_code=404, detail=f"Cache key '{key}' not found")
    
    cache.delete(key)
    return {"message": f"Cache key '{key}' deleted successfully"}


@router.delete("/clear")
def clear_cache():
    """Clear all cache."""
    cache = get_cache_backend()
    cache.clear()
    return {"message": "Cache cleared successfully"}


@router.get("/performance")
def get_cache_performance():
    """Get cache performance metrics."""
    cache = get_cache_backend()
    stats = cache.get_statistics()
    
    return {
        "hit_rate": stats.get("hit_rate", 0.0),
        "miss_rate": stats.get("miss_rate", 0.0),
        "total_requests": stats.get("total_requests", 0),
        "hits": stats.get("hits", 0),
        "misses": stats.get("misses", 0),
        "backend_type": stats.get("backend_type", "Unknown"),
    }

