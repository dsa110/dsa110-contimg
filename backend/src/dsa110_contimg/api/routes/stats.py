"""
Statistics routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_stats_service
from ..errors import internal_error
from ..services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("")
async def get_stats(
    service: StatsService = Depends(get_stats_service),
):
    """
    Get summary statistics for the pipeline.
    
    Returns counts and status summaries in a single efficient query.
    """
    try:
        return await service.get_dashboard_stats()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve stats: {str(e)}").to_dict(),
        )
