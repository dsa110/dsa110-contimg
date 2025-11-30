"""
FastAPI routes for the DSA-110 Continuum Imaging Pipeline API.

This module defines the REST API endpoints for images, measurement sets,
sources, and job provenance. All endpoints use standardized error responses.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse

from .auth import require_write_access, AuthContext
from .errors import (
    ErrorEnvelope,
    image_not_found,
    ms_not_found,
    source_not_found,
    internal_error,
    db_unavailable,
)
from .schemas import (
    ImageDetailResponse,
    ImageListResponse,
    MSDetailResponse,
    SourceDetailResponse,
    SourceListResponse,
    ProvenanceResponse,
    ContributingImage,
    JobListResponse,
)
from .repositories import (
    ImageRepository,
    MSRepository,
    SourceRepository,
    JobRepository,
)
from .cache import cache_manager, cached, make_cache_key, cache_lightcurve_key

# Create routers for different resource types
images_router = APIRouter(prefix="/images", tags=["images"])
ms_router = APIRouter(prefix="/ms", tags=["measurement-sets"])
sources_router = APIRouter(prefix="/sources", tags=["sources"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])
queue_router = APIRouter(prefix="/queue", tags=["queue"])
qa_router = APIRouter(prefix="/qa", tags=["qa"])
cal_router = APIRouter(prefix="/cal", tags=["calibration"])
logs_router = APIRouter(prefix="/logs", tags=["logs"])
stats_router = APIRouter(prefix="/stats", tags=["statistics"])
cache_router = APIRouter(prefix="/cache", tags=["cache"])

# Initialize repositories
image_repo = ImageRepository()
ms_repo = MSRepository()
source_repo = SourceRepository()
job_repo = JobRepository()


def error_response(error: ErrorEnvelope) -> JSONResponse:
    """Convert an ErrorEnvelope to a JSONResponse."""
    return JSONResponse(
        status_code=error.http_status,
        content=error.to_dict(),
    )


# =============================================================================
# Image Endpoints
# =============================================================================


@images_router.get("", response_model=list[ImageListResponse])
async def list_images(
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all images with summary info.
    
    Returns a paginated list of images with basic metadata.
    """
    try:
        images = image_repo.list_all(limit=limit, offset=offset)
        return [
            ImageListResponse(
                id=str(img.id),
                path=img.path,
                qa_grade=img.qa_grade,
                created_at=datetime.fromtimestamp(img.created_at) if img.created_at else None,
                run_id=img.run_id,
            )
            for img in images
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to list images: {str(e)}").to_dict(),
        )



@images_router.get("/{image_id}", response_model=ImageDetailResponse)
async def get_image_detail(image_id: str):
    """
    Get detailed information about an image.
    
    Returns image metadata including path, source MS, calibration info,
    pointing coordinates, QA assessment, and provenance.
    """
    try:
        image = image_repo.get_by_id(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=image_not_found(image_id).to_dict(),
            )
        
        # Convert to response model
        return ImageDetailResponse(
            id=str(image.id),
            path=image.path,
            ms_path=image.ms_path,
            cal_table=image.cal_table,
            pointing_ra_deg=image.center_ra_deg,
            pointing_dec_deg=image.center_dec_deg,
            qa_grade=image.qa_grade,
            qa_summary=image.qa_summary,
            run_id=image.run_id,
            created_at=datetime.fromtimestamp(image.created_at) if image.created_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve image: {str(e)}").to_dict(),
        )




@images_router.get("/{image_id}/provenance", response_model=ProvenanceResponse)
async def get_image_provenance(image_id: str):
    """
    Get provenance information for an image.
    
    Returns the pipeline context including input MS, calibration,
    and links to related resources.
    """
    try:
        image = image_repo.get_by_id(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=image_not_found(image_id).to_dict(),
            )
        
        return ProvenanceResponse(
            run_id=image.run_id,
            ms_path=image.ms_path,
            cal_table=image.cal_table,
            pointing_ra_deg=image.center_ra_deg,
            pointing_dec_deg=image.center_dec_deg,
            qa_grade=image.qa_grade,
            qa_summary=image.qa_summary,
            logs_url=f"/api/logs/{image.run_id}" if image.run_id else None,
            qa_url=f"/api/qa/image/{image_id}",
            ms_url=f"/api/ms/{quote(image.ms_path, safe='')}/metadata" if image.ms_path else None,
            image_url=f"/api/images/{image_id}",
            created_at=datetime.fromtimestamp(image.created_at) if image.created_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve image provenance: {str(e)}").to_dict(),
        )

@images_router.get("/{image_id}/fits")
async def download_image_fits(image_id: str):
    """Download the FITS file for an image."""
    try:
        image = image_repo.get_by_id(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=image_not_found(image_id).to_dict(),
            )
        
        # Check if file exists
        if not os.path.exists(image.path):
            raise HTTPException(
                status_code=404,
                detail=internal_error(f"FITS file not found on disk: {image.path}").to_dict(),
            )
        
        # Return the file
        return FileResponse(
            path=image.path,
            media_type="application/fits",
            filename=Path(image.path).name,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to download FITS: {str(e)}").to_dict(),
        )


# =============================================================================
# Measurement Set Endpoints
# =============================================================================

@ms_router.get("/{encoded_path:path}/metadata", response_model=MSDetailResponse)
async def get_ms_metadata(encoded_path: str):
    """
    Get metadata for a Measurement Set.
    
    The path should be URL-encoded. Returns pointing info, calibrator matches,
    QA assessment, and related provenance.
    """
    ms_path = unquote(encoded_path)
    
    try:
        ms_meta = ms_repo.get_metadata(ms_path)
        if not ms_meta:
            raise HTTPException(
                status_code=404,
                detail=ms_not_found(ms_path).to_dict(),
            )
        
        return MSDetailResponse(
            path=ms_meta.path,
            pointing_ra_deg=ms_meta.pointing_ra_deg or ms_meta.ra_deg,
            pointing_dec_deg=ms_meta.pointing_dec_deg or ms_meta.dec_deg,
            calibrator_matches=ms_meta.calibrator_tables,
            qa_grade=ms_meta.qa_grade,
            qa_summary=ms_meta.qa_summary,
            run_id=ms_meta.run_id,
            created_at=ms_meta.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve MS metadata: {str(e)}").to_dict(),
        )


@ms_router.get("/{encoded_path:path}/calibrator-matches")
async def get_ms_calibrator_matches(encoded_path: str):
    """Get calibrator matches for a Measurement Set."""
    ms_path = unquote(encoded_path)
    
    try:
        ms_meta = ms_repo.get_metadata(ms_path)
        if not ms_meta:
            raise HTTPException(
                status_code=404,
                detail=ms_not_found(ms_path).to_dict(),
            )
        
        return {
            "ms_path": ms_path,
            "matches": ms_meta.calibrator_tables or [],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve calibrator matches: {str(e)}").to_dict(),
        )


@ms_router.get("/{encoded_path:path}/provenance", response_model=ProvenanceResponse)
async def get_ms_provenance(encoded_path: str):
    """
    Get provenance information for a Measurement Set.
    
    Returns all relevant context for the MS including calibration,
    pointing, QA, and links to related resources.
    """
    ms_path = unquote(encoded_path)
    
    try:
        ms_meta = ms_repo.get_metadata(ms_path)
        if not ms_meta:
            raise HTTPException(
                status_code=404,
                detail=ms_not_found(ms_path).to_dict(),
            )
        
        # Get the first calibration table if available
        cal_table = None
        if ms_meta.calibrator_tables:
            cal_table = ms_meta.calibrator_tables[0].get("cal_table")
        
        return ProvenanceResponse(
            run_id=ms_meta.run_id,
            ms_path=ms_path,
            cal_table=cal_table,
            pointing_ra_deg=ms_meta.pointing_ra_deg or ms_meta.ra_deg,
            pointing_dec_deg=ms_meta.pointing_dec_deg or ms_meta.dec_deg,
            qa_grade=ms_meta.qa_grade,
            qa_summary=ms_meta.qa_summary,
            logs_url=f"/api/logs/{ms_meta.run_id}" if ms_meta.run_id else None,
            qa_url=f"/api/qa/ms/{quote(ms_path, safe='')}",
            ms_url=f"/api/ms/{quote(ms_path, safe='')}/metadata",
            image_url=f"/api/images/{ms_meta.imagename}" if ms_meta.imagename else None,
            created_at=ms_meta.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve MS provenance: {str(e)}").to_dict(),
        )


# =============================================================================
# Source Endpoints
# =============================================================================


@sources_router.get("", response_model=list[SourceListResponse])
async def list_sources(
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all sources with summary info.
    
    Returns a paginated list of sources with basic metadata.
    """
    try:
        sources = source_repo.list_all(limit=limit, offset=offset)
        return [
            SourceListResponse(
                id=src.id,
                name=src.name,
                ra_deg=src.ra_deg,
                dec_deg=src.dec_deg,
                num_images=len(src.contributing_images) if src.contributing_images else 0,
                image_id=src.latest_image_id,
            )
            for src in sources
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to list sources: {str(e)}").to_dict(),
        )



@sources_router.get("/{source_id}", response_model=SourceDetailResponse)
async def get_source_detail(source_id: str):
    """
    Get detailed information about an astronomical source.
    
    Returns source coordinates, contributing images, and detection history.
    """
    try:
        source = source_repo.get_by_id(source_id)
        if not source:
            raise HTTPException(
                status_code=404,
                detail=source_not_found(source_id).to_dict(),
            )
        
        # Convert contributing images to ContributingImage objects
        contributing_images = []
        if source.contributing_images:
            for img_dict in source.contributing_images:
                contributing_images.append(ContributingImage(**img_dict))
        
        return SourceDetailResponse(
            id=source.id,
            name=source.name,
            ra_deg=source.ra_deg,
            dec_deg=source.dec_deg,
            contributing_images=contributing_images,
            latest_image_id=source.latest_image_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve source: {str(e)}").to_dict(),
        )


@sources_router.get("/{source_id}/lightcurve")
async def get_source_lightcurve(
    source_id: str,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
):
    """Get lightcurve data for a source."""
    from astropy.time import Time
    from .repositories import SourceRepository
    
    # Convert ISO dates to MJD if provided
    start_mjd = None
    end_mjd = None
    if start_date:
        try:
            start_mjd = Time(start_date).mjd
        except Exception:
            pass
    if end_date:
        try:
            end_mjd = Time(end_date).mjd
        except Exception:
            pass
    
    source_repo = SourceRepository()
    decoded_source_id = unquote(source_id)
    data_points = source_repo.get_lightcurve(decoded_source_id, start_mjd, end_mjd)
    
    return {
        "source_id": decoded_source_id,
        "data_points": data_points,
    }


@sources_router.get("/{source_id}/variability")
async def get_source_variability(source_id: str):
    """Get variability analysis for a source."""
    # TODO: Implement variability analysis
    return {
        "source_id": source_id,
        "variability_index": None,
        "message": "Variability endpoint stub",
    }


# =============================================================================
# Job/Provenance Endpoints
# =============================================================================


@jobs_router.get("", response_model=list[JobListResponse])
async def list_jobs(
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all pipeline jobs with summary info.
    
    Returns a paginated list of jobs with basic metadata.
    """
    try:
        jobs = job_repo.list_all(limit=limit, offset=offset)
        return [
            JobListResponse(
                run_id=job.run_id,
                status="completed" if job.qa_grade else "pending",
                started_at=job.started_at,
            )
            for job in jobs
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to list jobs: {str(e)}").to_dict(),
        )



@jobs_router.get("/{run_id}")
async def get_job_detail(run_id: str):
    """
    Get detailed information about a pipeline job.
    
    Returns job status, timing, and related resource links.
    """
    try:
        job = job_repo.get_by_run_id(run_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=internal_error(f"Job {run_id} not found").to_dict(),
            )
        
        return {
            "run_id": job.run_id,
            "status": "completed" if job.qa_grade else "pending",
            "started_at": job.started_at,
            "finished_at": getattr(job, "finished_at", None),
            "logs_url": f"/api/logs/{run_id}",
            "qa_url": f"/api/qa/job/{run_id}",
            "config": getattr(job, "config", None),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve job: {str(e)}").to_dict(),
        )



@jobs_router.get("/{run_id}/provenance", response_model=ProvenanceResponse)
async def get_job_provenance(run_id: str):
    """
    Get provenance information for a pipeline job.
    
    Returns all relevant context for the job including input data,
    calibration, pointing, QA, and links to related resources.
    """
    try:
        job = job_repo.get_by_run_id(run_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=internal_error(f"Job {run_id} not found").to_dict(),
            )
        
        return ProvenanceResponse(
            run_id=job.run_id,
            ms_path=job.input_ms_path,
            cal_table=job.cal_table_path,
            pointing_ra_deg=job.phase_center_ra,
            pointing_dec_deg=job.phase_center_dec,
            qa_grade=job.qa_grade,
            qa_summary=job.qa_summary,
            logs_url=f"/api/logs/{run_id}",
            qa_url=f"/api/qa/job/{run_id}",
            ms_url=f"/api/ms/{quote(job.input_ms_path, safe='')}/metadata" if job.input_ms_path else None,
            image_url=f"/api/images/{job.output_image_id}" if job.output_image_id else None,
            created_at=job.started_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve job provenance: {str(e)}").to_dict(),
        )


@jobs_router.get("/{run_id}/logs")
async def get_job_logs(
    run_id: str,
    tail: int = Query(100, description="Number of lines from end"),
):
    """Get logs for a pipeline job."""
    log_path = Path(f"/data/dsa110-contimg/state/logs/{run_id}.log")
    
    # Try alternative log paths
    if not log_path.exists():
        log_path = Path(f"/data/dsa110-contimg/logs/{run_id}.log")


@jobs_router.post("/{run_id}/rerun")
async def rerun_job(
    run_id: str,
    auth: AuthContext = Depends(require_write_access),
):
    """
    Re-run a pipeline job.
    
    Creates a new job based on the configuration of the specified job.
    The job is queued for background execution via Redis Queue.
    Returns the job ID for status tracking.
    
    Requires authentication with write access.
    """
    from .job_queue import job_queue, rerun_pipeline_job
    
    try:
        # Get original job
        original_job = job_repo.get_by_run_id(run_id)
        if not original_job:
            raise HTTPException(
                status_code=404,
                detail=internal_error(f"Job {run_id} not found").to_dict(),
            )
        
        # Enqueue the rerun job
        job_id = job_queue.enqueue(
            rerun_pipeline_job,
            original_run_id=run_id,
            config=None,  # Could accept config overrides from request body
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to rerun job: {str(e)}").to_dict(),
        )
    
    if not log_path.exists():
        return {
            "run_id": run_id,
            "logs": [],
            "error": f"Log file not found: {log_path}",
        }
    
    try:
        with open(log_path) as f:
            lines = f.readlines()
            return {
                "run_id": run_id,
                "logs": lines[-tail:] if tail > 0 else lines,
                "total_lines": len(lines),
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to read log file: {str(e)}").to_dict(),
        )


# =============================================================================
# Logs Endpoints (alternative path)
# =============================================================================

@logs_router.get("/{run_id}")
async def get_logs(
    run_id: str,
    tail: int = Query(100, description="Number of lines from end"),
):
    """Get logs for a pipeline job (alternative endpoint)."""
    return await get_job_logs(run_id, tail)


# =============================================================================
# QA Endpoints
# =============================================================================

@qa_router.get("/image/{image_id}")
async def get_image_qa(image_id: str):
    """Get QA report for an image."""
    try:
        image = image_repo.get_by_id(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=image_not_found(image_id).to_dict(),
            )
        
        # Check for QA data in database
        # TODO: Implement detailed QA retrieval from image_qa table
        return {
            "image_id": image_id,
            "qa_grade": image.qa_grade,
            "qa_summary": image.qa_summary,
            "metrics": {
                "rms_noise": image.noise_jy,
                "dynamic_range": image.dynamic_range,
                "beam_major_arcsec": image.beam_major_arcsec,
                "beam_minor_arcsec": image.beam_minor_arcsec,
                "beam_pa_deg": image.beam_pa_deg,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve image QA: {str(e)}").to_dict(),
        )


@qa_router.get("/ms/{encoded_path:path}")
async def get_ms_qa(encoded_path: str):
    """Get QA report for a Measurement Set."""
    ms_path = unquote(encoded_path)
    
    try:
        ms_meta = ms_repo.get_metadata(ms_path)
        if not ms_meta:
            raise HTTPException(
                status_code=404,
                detail=ms_not_found(ms_path).to_dict(),
            )
        
        # TODO: Implement detailed QA retrieval from calibration_qa table
        return {
            "ms_path": ms_path,
            "qa_grade": ms_meta.qa_grade,
            "qa_summary": ms_meta.qa_summary,
            "stage": ms_meta.stage,
            "status": ms_meta.status,
            "cal_applied": bool(ms_meta.cal_applied),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve MS QA: {str(e)}").to_dict(),
        )


@qa_router.get("/job/{run_id}")
async def get_job_qa(run_id: str):
    """Get QA summary for a pipeline job."""
    try:
        job = job_repo.get_by_run_id(run_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=internal_error(f"Job {run_id} not found").to_dict(),
            )
        
        return {
            "run_id": run_id,
            "qa_grade": job.qa_grade,
            "qa_summary": job.qa_summary,
            "ms_path": job.input_ms_path,
            "cal_table": job.cal_table_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve job QA: {str(e)}").to_dict(),
        )


# =============================================================================
# Calibration Endpoints
# =============================================================================

@cal_router.get("/{encoded_path:path}")
async def get_cal_table_detail(encoded_path: str):
    """Get calibration table details."""
    cal_path = unquote(encoded_path)
    
    try:
        # Check if cal_registry database exists
        cal_db_path = "/data/dsa110-contimg/state/cal_registry.sqlite3"
        if not os.path.exists(cal_db_path):
            raise HTTPException(
                status_code=503,
                detail=db_unavailable("cal_registry").to_dict(),
            )
        
        # Query cal_registry
        from .repositories import safe_row_get
        import sqlite3
        conn = sqlite3.connect(cal_db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM caltables WHERE path = ?",
            (cal_path,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=internal_error(f"Calibration table not found: {cal_path}").to_dict(),
            )
        
        return {
            "path": row["path"],
            "table_type": row["table_type"],
            "set_name": safe_row_get(row, "set_name"),
            "cal_field": safe_row_get(row, "cal_field"),
            "refant": safe_row_get(row, "refant"),
            "created_at": datetime.fromtimestamp(row["created_at"]) if safe_row_get(row, "created_at") else None,
            "source_ms_path": safe_row_get(row, "source_ms_path"),
            "status": safe_row_get(row, "status"),
            "notes": safe_row_get(row, "notes"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve cal table: {str(e)}").to_dict(),
        )


# =============================================================================
# Statistics Endpoints
# =============================================================================


@stats_router.get("")
async def get_stats():
    """
    Get summary statistics for the pipeline.
    
    Returns counts and status summaries in a single efficient query,
    reducing the need for multiple API calls from the dashboard.
    """
    import sqlite3
    from .repositories import get_db_connection, DEFAULT_DB_PATH, CAL_REGISTRY_DB_PATH
    
    try:
        conn = get_db_connection(DEFAULT_DB_PATH)
        
        # Get all counts in one query
        stats = {}
        
        # MS counts by stage
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN stage = 'imaged' THEN 1 ELSE 0 END) as imaged,
                SUM(CASE WHEN stage = 'calibrated' THEN 1 ELSE 0 END) as calibrated,
                SUM(CASE WHEN stage = 'ingested' THEN 1 ELSE 0 END) as ingested,
                SUM(CASE WHEN stage IS NULL OR stage = '' THEN 1 ELSE 0 END) as pending
            FROM ms_index
        """)
        row = cursor.fetchone()
        stats["ms"] = {
            "total": row["total"] or 0,
            "by_stage": {
                "imaged": row["imaged"] or 0,
                "calibrated": row["calibrated"] or 0,
                "ingested": row["ingested"] or 0,
                "pending": row["pending"] or 0,
            }
        }
        
        # Image count
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM images")
        stats["images"] = {"total": cursor.fetchone()["cnt"] or 0}
        
        # Photometry and source counts
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_photometry,
                COUNT(DISTINCT source_id) as unique_sources
            FROM photometry
        """)
        row = cursor.fetchone()
        stats["photometry"] = {"total": row["total_photometry"] or 0}
        stats["sources"] = {"total": row["unique_sources"] or 0}
        
        # Job counts by status
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                SUM(CASE WHEN status = 'pending' OR status IS NULL THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM batch_jobs
        """)
        row = cursor.fetchone()
        stats["jobs"] = {
            "total": row["total"] or 0,
            "by_status": {
                "completed": row["completed"] or 0,
                "running": row["running"] or 0,
                "pending": row["pending"] or 0,
                "failed": row["failed"] or 0,
            }
        }
        
        # Recent activity (last 10 images)
        cursor = conn.execute("""
            SELECT path, created_at, type 
            FROM images 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        stats["recent_images"] = [
            {
                "path": row["path"],
                "created_at": datetime.fromtimestamp(row["created_at"]).isoformat() if row["created_at"] else None,
                "type": row["type"],
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        # Cal table count (separate database)
        try:
            if os.path.exists(CAL_REGISTRY_DB_PATH):
                cal_conn = get_db_connection(CAL_REGISTRY_DB_PATH)
                cursor = cal_conn.execute("SELECT COUNT(*) as cnt FROM caltables")
                stats["cal_tables"] = {"total": cursor.fetchone()["cnt"] or 0}
                cal_conn.close()
            else:
                stats["cal_tables"] = {"total": 0}
        except Exception:
            stats["cal_tables"] = {"total": 0}
        
        # Add database timestamp for cache validation
        stats["_meta"] = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "cache_hint_seconds": 30,  # Suggest client-side caching
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve stats: {str(e)}").to_dict(),
        )


# =============================================================================
# Queue Management Endpoints
# =============================================================================


@queue_router.get("")
async def get_queue_stats():
    """
    Get job queue statistics.
    
    Returns information about the queue including connection status,
    job counts by status, and queue configuration.
    """
    from .job_queue import job_queue
    return job_queue.get_queue_stats()


@queue_router.get("/jobs")
async def list_queued_jobs(
    status: Optional[str] = Query(None, description="Filter by status: queued, started, finished, failed"),
    limit: int = Query(50, le=200, description="Maximum number of jobs to return"),
):
    """
    List jobs in the queue.
    
    Returns jobs optionally filtered by status.
    """
    from .job_queue import job_queue, JobStatus
    
    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Invalid status: {status}. Valid values: queued, started, finished, failed"},
            )
    
    jobs = job_queue.list_jobs(status=status_filter, limit=limit)
    return [job.to_dict() for job in jobs]


@queue_router.get("/jobs/{job_id}")
async def get_queued_job(job_id: str):
    """
    Get status and details of a specific queued job.
    """
    from .job_queue import job_queue
    
    job_info = job_queue.get_job(job_id)
    if not job_info:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Job {job_id} not found"},
        )
    
    return job_info.to_dict()


@queue_router.post("/jobs/{job_id}/cancel")
async def cancel_queued_job(
    job_id: str,
    auth: AuthContext = Depends(require_write_access),
):
    """
    Cancel a queued job.
    
    Requires authentication with write access.
    """
    from .job_queue import job_queue
    
    success = job_queue.cancel(job_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Job {job_id} not found or could not be canceled"},
        )
    
    return {"status": "canceled", "job_id": job_id}


# =============================================================================
# Cache Management Endpoints
# =============================================================================


@cache_router.get("")
async def get_cache_stats():
    """
    Get Redis cache statistics.
    
    Returns cache hit/miss rates, memory usage, and connection status.
    """
    return cache_manager.get_stats()


@cache_router.post("/invalidate/{pattern}")
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


@cache_router.post("/clear")
async def clear_cache(
    auth: AuthContext = Depends(require_write_access),
):
    """
    Clear all cache entries.
    
    Use with caution - will temporarily increase database load.
    Requires authentication with write access.
    """
    deleted = cache_manager.invalidate("*")
    return {
        "status": "cleared",
        "keys_deleted": deleted,
    }


# =============================================================================
# Service Status Endpoints
# =============================================================================

services_router = APIRouter(prefix="/services", tags=["services"])


@services_router.get("/status")
async def get_services_status():
    """
    Get health status of all monitored services.
    
    Performs server-side health checks for all dependent services,
    bypassing browser CORS/CSP restrictions. Returns accurate status
    for HTTP services (Vite, Grafana, FastAPI, MkDocs, Prometheus)
    and non-HTTP services (Redis).
    
    This endpoint is designed to be called by the frontend's
    ServiceStatusPanel component.
    """
    from .services import check_all_services
    
    results = await check_all_services()
    
    running_count = sum(1 for r in results if r.status.value == "running")
    
    return {
        "services": [r.to_dict() for r in results],
        "summary": {
            "total": len(results),
            "running": running_count,
            "stopped": len(results) - running_count,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@services_router.get("/status/{port}")
async def get_service_status_by_port(port: int):
    """
    Get health status of a specific service by port number.
    
    Args:
        port: Port number of the service to check
    """
    from .services import MONITORED_SERVICES, check_service
    
    service = next((s for s in MONITORED_SERVICES if s.port == port), None)
    if not service:
        raise HTTPException(
            status_code=404,
            detail={"error": f"No monitored service on port {port}"},
        )
    
    result = await check_service(service)
    return result.to_dict()
