"""
Image routes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..dependencies import get_async_image_service
from ..exceptions import (
    RecordNotFoundError,
    FileNotAccessibleError,
)
from ..schemas import ImageDetailResponse, ImageListResponse, ProvenanceResponse
from ..services.async_services import AsyncImageService

router = APIRouter(prefix="/images", tags=["images"])


@router.get("", response_model=list[ImageListResponse])
async def list_images(
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    List all images with summary info.
    
    Returns a paginated list of images with basic metadata.
    
    Raises:
        DatabaseError: If database query fails
    """
    images = await service.list_images(limit=limit, offset=offset)
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


@router.get("/{image_id}", response_model=ImageDetailResponse)
async def get_image_detail(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Get detailed information about an image.
    
    Raises:
        RecordNotFoundError: If image is not found
    """
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
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


@router.get("/{image_id}/provenance", response_model=ProvenanceResponse)
async def get_image_provenance(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Get provenance information for an image.
    
    Raises:
        RecordNotFoundError: If image is not found
    """
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
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


@router.get("/{image_id}/qa")
async def get_image_qa_detail(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Get detailed QA report for an image.
    
    Raises:
        RecordNotFoundError: If image is not found
    """
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    return service.build_qa_report(image)


@router.get("/{image_id}/fits")
async def download_image_fits(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Download the FITS file for an image.
    
    Raises:
        RecordNotFoundError: If image is not found
        FileNotAccessibleError: If FITS file is not accessible
    """
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    valid, error = service.validate_fits_file(image)
    if not valid:
        raise FileNotAccessibleError(image.path, "read")
    
    return FileResponse(
        path=image.path,
        media_type="application/fits",
        filename=service.get_fits_filename(image),
    )


# =============================================================================
# Image Versioning Endpoints
# =============================================================================


class ImageVersionInfo(BaseModel):
    """Information about an image version in the chain."""
    id: str = Field(..., description="Image identifier")
    version: int = Field(..., description="Version number")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    qa_grade: Optional[str] = Field(None, description="QA grade")
    imaging_params: Optional[dict] = Field(None, description="Imaging parameters")


class ImageVersionChainResponse(BaseModel):
    """Response containing the version chain for an image."""
    current_id: str = Field(..., description="Current image ID")
    root_id: str = Field(..., description="ID of the original (v1) image")
    chain: list[ImageVersionInfo] = Field(..., description="All versions in the chain")
    total_versions: int = Field(..., description="Total number of versions")


class ReimageRequest(BaseModel):
    """Request to re-image from an existing image."""
    imsize: list[int] = Field(default=[5040, 5040], description="Image size [width, height]")
    cell: str = Field(default="2.5arcsec", description="Cell size")
    niter: int = Field(default=10000, description="Max iterations")
    threshold: str = Field(default="0.5mJy", description="Stopping threshold")
    weighting: str = Field(default="briggs", description="Weighting scheme")
    robust: float = Field(default=0.5, description="Robust parameter")
    deconvolver: str = Field(default="mtmfs", description="Deconvolver")
    use_existing_mask: bool = Field(default=False, description="Use existing mask if available")


class ReimageResponse(BaseModel):
    """Response after starting a re-imaging job."""
    job_id: str = Field(..., description="Job ID for tracking")
    parent_image_id: str = Field(..., description="Parent image ID")
    new_version: int = Field(..., description="Version number of new image")
    status: str = Field(..., description="Job status")


@router.get("/{image_id}/versions", response_model=ImageVersionChainResponse)
async def get_image_version_chain(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Get the version chain for an image.
    
    Returns all versions of an image, from the original (v1) to all
    subsequent re-images, following the parent_id links.
    
    Raises:
        RecordNotFoundError: If image is not found
    """
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Build version chain
    chain = []
    current = image
    
    # Traverse back to root
    while current:
        chain.append(ImageVersionInfo(
            id=str(current.id),
            version=getattr(current, 'version', 1),
            created_at=datetime.fromtimestamp(current.created_at) if current.created_at else None,
            qa_grade=current.qa_grade,
            imaging_params=getattr(current, 'imaging_params', None),
        ))
        
        parent_id = getattr(current, 'parent_id', None)
        if parent_id:
            current = await service.get_image(parent_id)
        else:
            current = None
    
    # Reverse to get chronological order
    chain.reverse()
    
    return ImageVersionChainResponse(
        current_id=image_id,
        root_id=chain[0].id if chain else image_id,
        chain=chain,
        total_versions=len(chain),
    )


@router.get("/{image_id}/children", response_model=list[ImageVersionInfo])
async def get_image_children(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Get all images that were derived from this image.
    
    Returns images that have this image as their parent_id.
    
    Raises:
        RecordNotFoundError: If image is not found
    """
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Get children (images with this as parent)
    children = await service.get_image_children(image_id)
    
    return [
        ImageVersionInfo(
            id=str(child.id),
            version=getattr(child, 'version', 1),
            created_at=datetime.fromtimestamp(child.created_at) if child.created_at else None,
            qa_grade=child.qa_grade,
            imaging_params=getattr(child, 'imaging_params', None),
        )
        for child in children
    ]


@router.post("/{image_id}/reimage", response_model=ReimageResponse)
async def reimage_from_existing(
    image_id: str,
    request: ReimageRequest,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Queue a re-imaging job from an existing image.
    
    Creates a new image version using the same MS and calibration
    but with different imaging parameters.
    
    Raises:
        RecordNotFoundError: If image is not found
        HTTPException: If re-imaging is not possible (e.g., no MS)
    """
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Validate we can re-image
    if not image.ms_path:
        raise HTTPException(
            status_code=422,
            detail="Cannot re-image: no source Measurement Set recorded"
        )
    
    # Calculate new version number
    current_version = getattr(image, 'version', 1)
    new_version = current_version + 1
    
    # Build imaging params
    params = {
        "imsize": request.imsize,
        "cell": request.cell,
        "niter": request.niter,
        "threshold": request.threshold,
        "weighting": request.weighting,
        "robust": request.robust,
        "deconvolver": request.deconvolver,
    }
    
    # Add mask if requested and available
    mask_path = getattr(image, 'mask_path', None)
    if request.use_existing_mask and mask_path:
        params["mask"] = mask_path
    
    # Queue re-imaging job
    try:
        job_id = await service.queue_reimage_job(
            parent_image_id=image_id,
            ms_path=image.ms_path,
            cal_table=image.cal_table,
            params=params,
            new_version=new_version,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue re-image job: {str(e)}"
        )
    
    return ReimageResponse(
        job_id=job_id,
        parent_image_id=image_id,
        new_version=new_version,
        status="queued",
    )

