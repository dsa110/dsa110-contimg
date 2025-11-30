"""
Logs routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_async_job_service
from ..services.async_services import AsyncJobService

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/{run_id}")
async def get_logs(
    run_id: str,
    tail: int = Query(100, description="Number of lines from end"),
    service: AsyncJobService = Depends(get_async_job_service),
):
    """Get logs for a pipeline job."""
    return service.read_log_tail(run_id, tail)
