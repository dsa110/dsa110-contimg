"""
Job routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..auth import require_write_access, AuthContext
from ..dependencies import get_job_service
from ..exceptions import RecordNotFoundError
from ..schemas import JobListResponse, ProvenanceResponse
from ..services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobListResponse])
async def list_jobs(
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: JobService = Depends(get_job_service),
):
    """
    List all pipeline jobs with summary info.
    """
    jobs = service.list_jobs(limit=limit, offset=offset)
    return [
        JobListResponse(
            run_id=job.run_id,
            status=service.get_job_status(job),
            started_at=job.started_at,
        )
        for job in jobs
    ]


@router.get("/{run_id}")
async def get_job_detail(
    run_id: str,
    service: JobService = Depends(get_job_service),
):
    """
    Get detailed information about a pipeline job.
    
    Raises:
        RecordNotFoundError: If job is not found
    """
    job = service.get_job(run_id)
    if not job:
        raise RecordNotFoundError("Job", run_id)
    
    links = service.build_provenance_links(job)
    
    return {
        "run_id": job.run_id,
        "status": service.get_job_status(job),
        "started_at": job.started_at,
        "finished_at": getattr(job, "finished_at", None),
        "logs_url": links["logs_url"],
        "qa_url": links["qa_url"],
        "config": getattr(job, "config", None),
    }


@router.get("/{run_id}/provenance", response_model=ProvenanceResponse)
async def get_job_provenance(
    run_id: str,
    service: JobService = Depends(get_job_service),
):
    """
    Get provenance information for a pipeline job.
    
    Raises:
        RecordNotFoundError: If job is not found
    """
    job = service.get_job(run_id)
    if not job:
        raise RecordNotFoundError("Job", run_id)
    
    links = service.build_provenance_links(job)
    
    return ProvenanceResponse(
        run_id=job.run_id,
        ms_path=job.input_ms_path,
        cal_table=job.cal_table_path,
        pointing_ra_deg=job.phase_center_ra,
        pointing_dec_deg=job.phase_center_dec,
        qa_grade=job.qa_grade,
        qa_summary=job.qa_summary,
        logs_url=links["logs_url"],
        qa_url=links["qa_url"],
        ms_url=links["ms_url"],
        image_url=links["image_url"],
        created_at=job.started_at,
    )


@router.get("/{run_id}/logs")
async def get_job_logs(
    run_id: str,
    tail: int = Query(100, description="Number of lines from end"),
    service: JobService = Depends(get_job_service),
):
    """Get logs for a pipeline job."""
    return service.read_log_tail(run_id, tail)


@router.post("/{run_id}/rerun")
async def rerun_job(
    run_id: str,
    auth: AuthContext = Depends(require_write_access),
    service: JobService = Depends(get_job_service),
):
    """
    Re-run a pipeline job.
    
    Requires authentication with write access.
    
    Raises:
        RecordNotFoundError: If original job is not found
    """
    from ..job_queue import job_queue, rerun_pipeline_job
    
    original_job = service.get_job(run_id)
    if not original_job:
        raise RecordNotFoundError("Job", run_id)
    
    job_id = job_queue.enqueue(
        rerun_pipeline_job,
        original_run_id=run_id,
        config=None,
        meta={
            "original_run_id": run_id,
            "requested_by": auth.key_id or "unknown",
            "auth_method": auth.method,
        },
    )
    
    return {
        "status": "queued",
        "job_id": job_id,
        "original_run_id": run_id,
        "message": f"Job {run_id} queued for re-run",
        "queue_connected": job_queue.is_connected,
    }

