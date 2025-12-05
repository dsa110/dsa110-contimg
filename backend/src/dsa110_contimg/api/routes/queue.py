"""
Queue routes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import AuthContext, require_write_access

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("")
async def get_queue_stats():
    """
    Get job queue statistics.
    """
    from ..job_queue import job_queue

    return job_queue.get_queue_stats()


@router.get("/jobs")
async def list_queued_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=200, description="Maximum number of jobs"),
):
    """
    List jobs in the queue.
    """
    from ..job_queue import JobStatus, job_queue

    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Invalid status: {status}. "
                    f"Valid values: queued, started, finished, failed"
                },
            )

    jobs = job_queue.list_jobs(status=status_filter, limit=limit)
    return [job.to_dict() for job in jobs]


@router.get("/jobs/{job_id}")
async def get_queued_job(job_id: str):
    """
    Get status and details of a specific queued job.
    """
    from ..job_queue import job_queue

    job_info = job_queue.get_job(job_id)
    if not job_info:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Job {job_id} not found"},
        )

    return job_info.to_dict()


@router.post("/jobs/{job_id}/cancel")
async def cancel_queued_job(
    job_id: str,
    auth: AuthContext = Depends(require_write_access),
):
    """
    Cancel a queued job.

    Requires authentication with write access.
    """
    from ..job_queue import job_queue

    success = job_queue.cancel(job_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Job {job_id} not found or could not be canceled"},
        )

    return {"status": "canceled", "job_id": job_id}
