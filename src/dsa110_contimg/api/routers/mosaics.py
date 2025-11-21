"""Mosaic-related API routes extracted from routes.py."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse

from dsa110_contimg.api.data_access import (
    fetch_mosaic_by_id,
    fetch_mosaics,
)
from dsa110_contimg.api.models import (
    Mosaic,
    MosaicCreateRequest,
    MosaicCreateResponse,
    MosaicQueryResponse,
)

router = APIRouter()


@router.post("/mosaics/query", response_model=MosaicQueryResponse)
def mosaics_query(request: Request, request_body: dict):
    cfg = request.app.state.cfg
    start_time = request_body.get("start_time", "")
    end_time = request_body.get("end_time", "")
    if not start_time or not end_time:
        return MosaicQueryResponse(mosaics=[], total=0)
    mosaics_data = fetch_mosaics(cfg.products_db, start_time, end_time)
    mosaics = [Mosaic(**m) for m in mosaics_data]
    return MosaicQueryResponse(mosaics=mosaics, total=len(mosaics))


@router.post("/mosaics/create", response_model=MosaicCreateResponse)
def mosaics_create(
    request: Request,
    request_body: MosaicCreateRequest,
    background_tasks: BackgroundTasks,
) -> MosaicCreateResponse:
    """Create a mosaic via API.

    Supports two modes:
    1. Calibrator-centered: Provide calibrator_name
    2. Time-window: Provide start_time and end_time
    """
    import os

    from dsa110_contimg.api.job_runner import run_mosaic_create_job
    from dsa110_contimg.database.jobs import create_job, get_job
    from dsa110_contimg.database.products import ensure_products_db

    db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
    conn = ensure_products_db(db_path)

    # Validate request
    if not request_body.calibrator_name and not (request_body.start_time and request_body.end_time):
        raise HTTPException(
            status_code=400,
            detail="Either calibrator_name or (start_time and end_time) must be provided",
        )

    try:
        # Prepare job parameters
        job_params = {
            "calibrator_name": request_body.calibrator_name,
            "start_time": request_body.start_time,
            "end_time": request_body.end_time,
            "timespan_minutes": request_body.timespan_minutes,
            "wait_for_published": request_body.wait_for_published,
        }

        # Create placeholder ms_path for job creation
        # Use first MS path from group if available, otherwise use placeholder
        placeholder_ms_path = (
            f"mosaic_{request_body.calibrator_name or request_body.start_time}"
            if request_body.calibrator_name or request_body.start_time
            else "mosaic_unknown"
        )

        # Create job
        job_id = create_job(conn, "mosaic", placeholder_ms_path, job_params)
        conn.commit()

        # Start job in background
        background_tasks.add_task(run_mosaic_create_job, job_id, job_params, db_path)

        # Get initial job state
        jd = get_job(conn, job_id)
        group_id = (
            jd.get("params", {}).get("group_id") if isinstance(jd.get("params"), dict) else None
        )

        return MosaicCreateResponse(
            job_id=job_id,
            group_id=group_id,
            status=jd["status"],
            message="Mosaic creation job started",
        )
    finally:
        conn.close()


@router.get("/mosaics/{mosaic_id}", response_model=Mosaic)
def get_mosaic(request: Request, mosaic_id: int):
    cfg = request.app.state.cfg
    mosaic_data = fetch_mosaic_by_id(cfg.products_db, mosaic_id)
    if not mosaic_data:
        raise HTTPException(status_code=404, detail=f"Mosaic {mosaic_id} not found")
    return Mosaic(**mosaic_data)


@router.get("/mosaics/{mosaic_id}/fits")
def get_mosaic_fits(request: Request, mosaic_id: int):
    cfg = request.app.state.cfg
    mosaic_data = fetch_mosaic_by_id(cfg.products_db, mosaic_id)
    if not mosaic_data:
        raise HTTPException(status_code=404, detail=f"Mosaic {mosaic_id} not found")
    mosaic_path = mosaic_data["path"]
    if not Path(mosaic_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"FITS file not found for mosaic {mosaic_id}: {mosaic_path}",
        )
    return FileResponse(mosaic_path, media_type="application/fits", filename=Path(mosaic_path).name)
