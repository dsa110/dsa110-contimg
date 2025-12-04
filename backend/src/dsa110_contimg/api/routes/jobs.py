"""
Job routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..auth import require_write_access, AuthContext
from ..dependencies import get_async_job_service
from ..exceptions import RecordNotFoundError
from ..schemas import JobListResponse, ProvenanceResponse
from ..services.async_services import AsyncJobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


class BulkJobActionRequest(BaseModel):
    """Request model for bulk job actions."""
    run_ids: list[str] = Field(default_factory=list, alias="runIds")
    
    class Config:
        allow_population_by_field_name = True


@router.get("", response_model=list[JobListResponse])
async def list_jobs(
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: AsyncJobService = Depends(get_async_job_service),
):
    """
    List all pipeline jobs with summary info.
    """
    jobs = await service.list_jobs(limit=limit, offset=offset)
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
    service: AsyncJobService = Depends(get_async_job_service),
):
    """
    Get detailed information about a pipeline job.
    
    Raises:
        RecordNotFoundError: If job is not found
    """
    job = await service.get_job(run_id)
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
    service: AsyncJobService = Depends(get_async_job_service),
):
    """
    Get provenance information for a pipeline job.
    
    Raises:
        RecordNotFoundError: If job is not found
    """
    job = await service.get_job(run_id)
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
    service: AsyncJobService = Depends(get_async_job_service),
):
    """Get logs for a pipeline job."""
    return service.read_log_tail(run_id, tail)


def _jobs_to_csv(rows: list[dict]) -> str:
    """Serialize job summaries to CSV."""
    import csv
    import io
    
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["run_id", "status", "started_at", "finished_at", "input_ms", "output_image_id"])
    for row in rows:
        writer.writerow([
            row.get("run_id"),
            row.get("status"),
            row.get("started_at"),
            row.get("finished_at"),
            row.get("input_ms"),
            row.get("output_image_id") or "",
        ])
    buffer.seek(0)
    return buffer.getvalue()


@router.get("/export")
async def export_jobs(
    ids: str = Query(..., description="Comma-separated run IDs"),
    service: AsyncJobService = Depends(get_async_job_service),
):
    """Export selected jobs as CSV."""
    run_ids = [run_id for run_id in ids.split(",") if run_id]
    if not run_ids:
        raise HTTPException(status_code=400, detail="No run IDs provided")
    
    rows = []
    for run_id in run_ids:
        job = await service.get_job(run_id)
        if not job:
            continue
        rows.append({
            "run_id": job.run_id,
            "status": service.get_job_status(job),
            "started_at": getattr(job, "started_at", None),
            "finished_at": getattr(job, "finished_at", None),
            "input_ms": getattr(job, "input_ms_path", None),
            "output_image_id": getattr(job, "output_image_id", None),
        })
    
    if not rows:
        raise RecordNotFoundError("Job", ids)
    
    csv_data = _jobs_to_csv(rows)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="jobs.csv"'},
    )


@router.post("/bulk-rerun")
async def bulk_rerun_jobs(
    request: BulkJobActionRequest,
    auth: AuthContext = Depends(require_write_access),
    service: AsyncJobService = Depends(get_async_job_service),
):
    """Queue reruns for multiple jobs."""
    if not request.run_ids:
        raise HTTPException(status_code=400, detail="No run IDs provided")
    
    from ..job_queue import job_queue, rerun_pipeline_job
    
    enqueued = []
    not_found = []
    for run_id in request.run_ids:
        job = await service.get_job(run_id)
        if not job:
            not_found.append(run_id)
            continue
        
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
        enqueued.append({"run_id": run_id, "job_id": job_id})
    
    return {
        "status": "queued",
        "enqueued": enqueued,
        "not_found": not_found,
        "queue_connected": job_queue.is_connected,
    }


@router.post("/bulk-cancel")
async def bulk_cancel_jobs(
    request: BulkJobActionRequest,
    _auth: AuthContext = Depends(require_write_access),
):
    """Cancel queued jobs by run ID (best effort)."""
    if not request.run_ids:
        raise HTTPException(status_code=400, detail="No run IDs provided")
    
    from ..job_queue import job_queue
    
    canceled = []
    not_found = []
    for run_id in request.run_ids:
        if job_queue.cancel(run_id):
            canceled.append(run_id)
        else:
            not_found.append(run_id)
    
    return {"status": "ok", "canceled": canceled, "not_found": not_found}


@router.post("/{run_id}/rerun")
async def rerun_job(
    run_id: str,
    auth: AuthContext = Depends(require_write_access),
    service: AsyncJobService = Depends(get_async_job_service),
):
    """
    Re-run a pipeline job.
    
    Requires authentication with write access.
    
    Raises:
        RecordNotFoundError: If original job is not found
    """
    from ..job_queue import job_queue, rerun_pipeline_job
    
    original_job = await service.get_job(run_id)
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
