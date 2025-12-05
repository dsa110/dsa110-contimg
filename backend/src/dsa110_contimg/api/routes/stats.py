"""
Statistics routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_stats_service
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
    return await service.get_dashboard_stats()
