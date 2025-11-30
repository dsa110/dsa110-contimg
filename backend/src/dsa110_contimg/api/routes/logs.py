"""
Logs routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_job_service
from ..services.job_service import JobService

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/{run_id}")
async def get_logs(
    run_id: str,
    tail: int = Query(100, description="Number of lines from end"),
    service: JobService = Depends(get_job_service),
):
    """Get logs for a pipeline job."""
    return service.read_log_tail(run_id, tail)
