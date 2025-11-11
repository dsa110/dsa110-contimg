"""Mosaic-related API routes extracted from routes.py."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from dsa110_contimg.api.data_access import (
    fetch_mosaic_by_id,
    fetch_mosaics,
)
from dsa110_contimg.api.models import Mosaic, MosaicQueryResponse

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


@router.post("/mosaics/create")
def mosaics_create(_: Request, request_body: dict):
    return {
        "status": "not_implemented",
        "message": "Mosaic creation via API is not yet implemented. Use the mosaic CLI tools.",
        "mosaic_id": None,
    }


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
        raise HTTPException(status_code=404, detail=f"FITS file not found for mosaic {mosaic_id}: {mosaic_path}")
    return FileResponse(mosaic_path, media_type="application/fits", filename=Path(mosaic_path).name)

