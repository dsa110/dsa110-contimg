"""
Source routes.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_async_source_service, get_async_image_repository
from ..exceptions import RecordNotFoundError, ValidationError
from ..async_repositories import AsyncImageRepository
from ..schemas import SourceDetailResponse, SourceListResponse, ContributingImage
from ..services.async_services import AsyncSourceService

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceListResponse])
async def list_sources(
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: AsyncSourceService = Depends(get_async_source_service),
):
    """
    List all sources with summary info.
    """
    sources = await service.list_sources(limit=limit, offset=offset)
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


@router.get("/{source_id}", response_model=SourceDetailResponse)
async def get_source_detail(
    source_id: str,
    service: AsyncSourceService = Depends(get_async_source_service),
):
    """
    Get detailed information about an astronomical source.
    
    Raises:
        RecordNotFoundError: If source is not found
    """
    source = await service.get_source(source_id)
    if not source:
        raise RecordNotFoundError("Source", source_id)
    
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


@router.get("/{source_id}/lightcurve")
async def get_source_lightcurve(
    source_id: str,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    service: AsyncSourceService = Depends(get_async_source_service),
):
    """Get lightcurve data for a source."""
    from astropy.time import Time
    
    # Convert ISO dates to MJD if provided
    start_mjd = None
    end_mjd = None
    if start_date:
        try:
            start_mjd = Time(start_date).mjd
        except Exception as e:
            raise ValidationError(f"Invalid start_date format: {start_date}. Use ISO format (YYYY-MM-DD).") from e
    if end_date:
        try:
            end_mjd = Time(end_date).mjd
        except Exception as e:
            raise ValidationError(f"Invalid end_date format: {end_date}. Use ISO format (YYYY-MM-DD).") from e
    
    decoded_source_id = unquote(source_id)
    data_points = await service.get_lightcurve(decoded_source_id, start_mjd, end_mjd)
    
    return {
        "source_id": decoded_source_id,
        "data_points": data_points,
    }


@router.get("/{source_id}/variability")
async def get_source_variability(
    source_id: str,
    service: AsyncSourceService = Depends(get_async_source_service),
):
    """
    Get variability analysis for a source.
    
    Raises:
        RecordNotFoundError: If source is not found
    """
    source = await service.get_source(source_id)
    if not source:
        raise RecordNotFoundError("Source", source_id)
    
    # Get lightcurve data
    epochs = await service.get_lightcurve(source_id)
    
    return service.calculate_variability(source, epochs)


@router.get("/{source_id}/qa")
async def get_source_qa(
    source_id: str,
    service: AsyncSourceService = Depends(get_async_source_service),
    image_repo: AsyncImageRepository = Depends(get_async_image_repository),
):
    """
    Get QA report for a source.
    
    Raises:
        RecordNotFoundError: If source is not found
    """
    source = await service.get_source(source_id)
    if not source:
        raise RecordNotFoundError("Source", source_id)
    
    # Get associated images for QA summary
    images = []
    if hasattr(image_repo, 'get_for_source'):
        images = image_repo.get_for_source(source_id)
    
    qa_grades = [
        img.qa_grade for img in images 
        if hasattr(img, 'qa_grade') and img.qa_grade
    ]
    
    return {
        "source_id": source_id,
        "source_name": source.name,
        "n_images": len(images) if images else 0,
        "qa_grades": qa_grades,
        "overall_grade": max(qa_grades) if qa_grades else None,
        "flags": [],
        "metrics": {
            "ra_deg": source.ra_deg,
            "dec_deg": source.dec_deg,
        },
    }

