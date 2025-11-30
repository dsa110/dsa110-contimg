"""
Image routes.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from ..dependencies import get_image_service, get_image_repository
from ..errors import image_not_found, internal_error
from ..repositories import ImageRepository
from ..schemas import ImageDetailResponse, ImageListResponse, ProvenanceResponse
from ..services.image_service import ImageService

router = APIRouter(prefix="/images", tags=["images"])


@router.get("", response_model=list[ImageListResponse])
async def list_images(
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: ImageService = Depends(get_image_service),
):
    """
    List all images with summary info.
    
    Returns a paginated list of images with basic metadata.
    """
    try:
        images = service.list_images(limit=limit, offset=offset)
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


@router.get("/{image_id}", response_model=ImageDetailResponse)
async def get_image_detail(
    image_id: str,
    service: ImageService = Depends(get_image_service),
):
    """
    Get detailed information about an image.
    """
    try:
        image = service.get_image(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=image_not_found(image_id).to_dict(),
            )
        
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


@router.get("/{image_id}/provenance", response_model=ProvenanceResponse)
async def get_image_provenance(
    image_id: str,
    service: ImageService = Depends(get_image_service),
):
    """
    Get provenance information for an image.
    """
    try:
        image = service.get_image(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=image_not_found(image_id).to_dict(),
            )
        
        links = service.build_provenance_links(image)
        
        return ProvenanceResponse(
            run_id=image.run_id,
            ms_path=image.ms_path,
            cal_table=image.cal_table,
            pointing_ra_deg=image.center_ra_deg,
            pointing_dec_deg=image.center_dec_deg,
            qa_grade=image.qa_grade,
            qa_summary=image.qa_summary,
            logs_url=links["logs_url"],
            qa_url=links["qa_url"],
            ms_url=links["ms_url"],
            image_url=links["image_url"],
            created_at=datetime.fromtimestamp(image.created_at) if image.created_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve image provenance: {str(e)}").to_dict(),
        )


@router.get("/{image_id}/qa")
async def get_image_qa_detail(
    image_id: str,
    service: ImageService = Depends(get_image_service),
):
    """
    Get detailed QA report for an image.
    """
    try:
        image = service.get_image(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=image_not_found(image_id).to_dict(),
            )
        
        return service.build_qa_report(image)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve image QA: {str(e)}").to_dict(),
        )


@router.get("/{image_id}/fits")
async def download_image_fits(
    image_id: str,
    service: ImageService = Depends(get_image_service),
):
    """Download the FITS file for an image."""
    try:
        image = service.get_image(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=image_not_found(image_id).to_dict(),
            )
        
        valid, error = service.validate_fits_file(image)
        if not valid:
            raise HTTPException(
                status_code=404,
                detail=internal_error(error).to_dict(),
            )
        
        return FileResponse(
            path=image.path,
            media_type="application/fits",
            filename=service.get_fits_filename(image),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to download FITS: {str(e)}").to_dict(),
        )
