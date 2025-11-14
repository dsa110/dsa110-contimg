"""
API endpoints for task queue management
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status

from dsa110_contimg.api.task_queue import (
    enqueue_task,
    get_job_status,
    get_queue_stats,
    is_task_queue_available,
)

router = APIRouter()


@router.get("/available")
def check_task_queue_available() -> Dict[str, Any]:
    """Check if task queue is available"""
    return {
        "available": is_task_queue_available(),
    }


@router.get("/queues/{queue_name}/stats")
def get_queue_statistics(queue_name: str = "default") -> Dict[str, Any]:
    """Get statistics for a task queue"""
    stats = get_queue_stats(queue_name)
    if not stats.get("available"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Task queue '{queue_name}' is not available: {stats.get('reason', 'Unknown error')}",
        )
    return stats


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> Dict[str, Any]:
    """Get job status and details"""
    job_status = get_job_status(job_id)
    if job_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )
    return job_status


@router.post("/queues/{queue_name}/enqueue")
def enqueue_job(
    queue_name: str = "default",
    function_name: Optional[str] = None,
    timeout: int = 300,
) -> Dict[str, Any]:
    """
    Enqueue a job (placeholder - actual implementation depends on use case)

    Note: This is a placeholder endpoint. Actual task enqueueing should be done
    in specific endpoints that need background processing.
    """
    if not is_task_queue_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue is not available",
        )

    return {
        "message": "Use task_queue.enqueue_task() in your endpoints to enqueue jobs",
        "queue": queue_name,
        "available": True,
    }
