"""
FastAPI routes for the DSA-110 Continuum Imaging Pipeline API.

This module defines the REST API endpoints for images, measurement sets,
sources, and job provenance. All endpoints use standardized error responses.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from .errors import (
    ErrorEnvelope,
    image_not_found,
    ms_not_found,
    source_not_found,
    internal_error,
)
from .schemas import (
    ImageDetailResponse,
    MSDetailResponse,
    SourceDetailResponse,
    ProvenanceResponse,
)

# Create routers for different resource types
images_router = APIRouter(prefix="/images", tags=["images"])
ms_router = APIRouter(prefix="/ms", tags=["measurement-sets"])
sources_router = APIRouter(prefix="/sources", tags=["sources"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])


def error_response(error: ErrorEnvelope) -> JSONResponse:
    """Convert an ErrorEnvelope to a JSONResponse."""
    return JSONResponse(
        status_code=error.http_status,
        content=error.to_dict(),
    )


# =============================================================================
# Image Endpoints
# =============================================================================

@images_router.get("/{image_id}", response_model=ImageDetailResponse)
async def get_image_detail(image_id: str):
    """
    Get detailed information about an image.
    
    Returns image metadata including path, source MS, calibration info,
    pointing coordinates, QA assessment, and provenance.
    """
    # TODO: Replace with actual database lookup
    # This is a stub implementation for development
    
    # Simulate not found
    if image_id.startswith("notfound"):
        raise HTTPException(
            status_code=404,
            detail=image_not_found(image_id).to_dict(),
        )
    
    # Return stub data
    return ImageDetailResponse(
        id=image_id,
        path=f"/data/images/{image_id}.fits",
        ms_path="/data/ms/example.ms",
        cal_table="/data/cal/example.tbl",
        pointing_ra_deg=180.0,
        pointing_dec_deg=-30.0,
        qa_grade="good",
        qa_summary="RMS 0.35 mJy, DR 1200",
        run_id=f"job-{image_id[:8]}",
        created_at="2025-01-15T10:30:00Z",
    )


@images_router.get("/{image_id}/fits")
async def download_image_fits(image_id: str):
    """Download the FITS file for an image."""
    # TODO: Implement actual file streaming
    raise HTTPException(
        status_code=501,
        detail=internal_error("FITS download not yet implemented").to_dict(),
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
    
    # Simulate not found
    if "notfound" in ms_path:
        raise HTTPException(
            status_code=404,
            detail=ms_not_found(ms_path).to_dict(),
        )
    
    # Return stub data
    return MSDetailResponse(
        path=ms_path,
        pointing_ra_deg=180.0,
        pointing_dec_deg=-30.0,
        calibrator_matches=[
            {"cal_table": "/data/cal/flux.tbl", "type": "flux"},
            {"cal_table": "/data/cal/phase.tbl", "type": "phase"},
        ],
        qa_grade="good",
        qa_summary="Clean data",
        run_id="job-ms-001",
        created_at="2025-01-15T08:00:00Z",
    )


@ms_router.get("/{encoded_path:path}/calibrator-matches")
async def get_ms_calibrator_matches(encoded_path: str):
    """Get calibrator matches for a Measurement Set."""
    ms_path = unquote(encoded_path)
    
    # TODO: Implement actual calibrator lookup
    return {
        "ms_path": ms_path,
        "matches": [
            {"cal_table": "/data/cal/flux.tbl", "type": "flux"},
            {"cal_table": "/data/cal/phase.tbl", "type": "phase"},
        ],
    }


# =============================================================================
# Source Endpoints
# =============================================================================

@sources_router.get("/{source_id}", response_model=SourceDetailResponse)
async def get_source_detail(source_id: str):
    """
    Get detailed information about an astronomical source.
    
    Returns source coordinates, contributing images, and detection history.
    """
    # Simulate not found
    if source_id.startswith("notfound"):
        raise HTTPException(
            status_code=404,
            detail=source_not_found(source_id).to_dict(),
        )
    
    # Return stub data
    return SourceDetailResponse(
        id=source_id,
        name=f"DSA-110 J{source_id}",
        ra_deg=180.0,
        dec_deg=-30.0,
        contributing_images=[
            {
                "image_id": "img-001",
                "path": "/data/images/img-001.fits",
                "ms_path": "/data/ms/obs-001.ms",
                "qa_grade": "good",
                "created_at": "2025-01-15T10:30:00Z",
            },
            {
                "image_id": "img-002",
                "path": "/data/images/img-002.fits",
                "ms_path": "/data/ms/obs-002.ms",
                "qa_grade": "warn",
                "created_at": "2025-01-16T10:30:00Z",
            },
        ],
        latest_image_id="img-002",
    )


@sources_router.get("/{source_id}/lightcurve")
async def get_source_lightcurve(
    source_id: str,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
):
    """Get lightcurve data for a source."""
    # TODO: Implement actual lightcurve retrieval
    return {
        "source_id": source_id,
        "data_points": [],
        "message": "Lightcurve endpoint stub",
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

@jobs_router.get("/{run_id}/provenance", response_model=ProvenanceResponse)
async def get_job_provenance(run_id: str):
    """
    Get provenance information for a pipeline job.
    
    Returns all relevant context for the job including input data,
    calibration, pointing, QA, and links to related resources.
    """
    # TODO: Implement actual job lookup
    return ProvenanceResponse(
        run_id=run_id,
        ms_path="/data/ms/example.ms",
        cal_table="/data/cal/example.tbl",
        pointing_ra_deg=180.0,
        pointing_dec_deg=-30.0,
        qa_grade="good",
        qa_summary="RMS 0.35 mJy",
        logs_url=f"/logs/{run_id}",
        qa_url=f"/qa/job/{run_id}",
        ms_url="/ms/%2Fdata%2Fms%2Fexample.ms",
        image_url="/images/img-001",
        created_at="2025-01-15T10:00:00Z",
    )


@jobs_router.get("/{run_id}/logs")
async def get_job_logs(
    run_id: str,
    tail: int = Query(100, description="Number of lines from end"),
):
    """Get logs for a pipeline job."""
    # TODO: Implement actual log retrieval
    return {
        "run_id": run_id,
        "logs": [],
        "message": "Logs endpoint stub",
    }
