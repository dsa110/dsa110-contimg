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
from ..auth import require_write_access, AuthContext

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
    _auth: AuthContext = Depends(require_write_access),
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


# =============================================================================
# Mask Management Endpoints
# =============================================================================


class MaskCreateRequest(BaseModel):
    """Request to create a mask for an image."""
    format: str = Field(default="ds9", description="Region format (ds9, crtf)")
    regions: str = Field(..., description="Region file content")


class MaskResponse(BaseModel):
    """Response after saving a mask."""
    id: str = Field(..., description="Mask identifier")
    path: str = Field(..., description="Path to saved mask file")
    format: str = Field(..., description="Region format")
    region_count: int = Field(..., description="Number of regions in mask")
    created_at: str = Field(..., description="Creation timestamp")


class MaskListResponse(BaseModel):
    """Response listing masks for an image."""
    masks: list[MaskResponse] = Field(..., description="List of masks")
    total: int = Field(..., description="Total number of masks")


@router.post("/{image_id}/masks", response_model=MaskResponse)
async def save_mask(
    image_id: str,
    request: MaskCreateRequest,
    service: AsyncImageService = Depends(get_async_image_service),
    _auth: AuthContext = Depends(require_write_access),
):
    """
    Save a DS9/CRTF region mask for an image.
    
    The mask is saved alongside the image and can be used for re-imaging.
    
    Raises:
        RecordNotFoundError: If image is not found
        HTTPException: If mask cannot be saved
    """
    from pathlib import Path
    from datetime import datetime
    import uuid
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Determine mask file path
    image_path = Path(image.path)
    mask_id = str(uuid.uuid4())[:8]
    
    # Determine extension based on format
    ext = ".reg" if request.format == "ds9" else ".crtf"
    mask_filename = f"{image_path.stem}.mask.{mask_id}{ext}"
    mask_path = image_path.parent / mask_filename
    
    try:
        # Write mask file
        mask_path.write_text(request.regions)
        
        # Count regions (simple line count for DS9 format)
        region_count = sum(
            1 for line in request.regions.split("\n")
            if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("global")
        )
        
        # Update image record with mask path (if service supports it)
        try:
            await service.update_image_mask(image_id, str(mask_path))
        except AttributeError:
            # Service may not have mask update support yet
            pass
        
        return MaskResponse(
            id=mask_id,
            path=str(mask_path),
            format=request.format,
            region_count=region_count,
            created_at=datetime.now().isoformat(),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save mask: {str(e)}"
        )


@router.get("/{image_id}/masks", response_model=MaskListResponse)
async def list_masks(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    List all masks for an image.
    
    Raises:
        RecordNotFoundError: If image is not found
    """
    from pathlib import Path
    from datetime import datetime
    import os
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Find mask files in same directory
    image_path = Path(image.path)
    mask_pattern = f"{image_path.stem}.mask.*"
    
    masks = []
    for mask_file in image_path.parent.glob(mask_pattern):
        if mask_file.suffix in (".reg", ".crtf"):
            content = mask_file.read_text()
            region_count = sum(
                1 for line in content.split("\n")
                if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("global")
            )
            
            masks.append(MaskResponse(
                id=mask_file.stem.split(".")[-1],  # Extract ID from filename
                path=str(mask_file),
                format="ds9" if mask_file.suffix == ".reg" else "crtf",
                region_count=region_count,
                created_at=datetime.fromtimestamp(os.path.getmtime(mask_file)).isoformat(),
            ))
    
    return MaskListResponse(masks=masks, total=len(masks))


@router.delete("/{image_id}/masks/{mask_id}")
async def delete_mask(
    image_id: str,
    mask_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
    _auth: AuthContext = Depends(require_write_access),
):
    """
    Delete a mask file.
    
    Raises:
        RecordNotFoundError: If image or mask is not found
    """
    from pathlib import Path
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Find mask file
    image_path = Path(image.path)
    mask_pattern = f"{image_path.stem}.mask.{mask_id}.*"
    
    deleted = False
    for mask_file in image_path.parent.glob(mask_pattern):
        mask_file.unlink()
        deleted = True
    
    if not deleted:
        raise RecordNotFoundError("Mask", mask_id)
    
    return {"status": "deleted", "mask_id": mask_id}


# =============================================================================
# Region Management Endpoints (General-purpose regions, not just masks)
# =============================================================================


class RegionCreateRequest(BaseModel):
    """Request to save regions for an image."""
    format: str = Field(default="ds9", description="Region format (ds9, crtf, json)")
    regions: str = Field(..., description="Region file content")
    name: Optional[str] = Field(None, description="Optional name for the region file")
    purpose: str = Field(
        default="analysis",
        description="Purpose: analysis, source, exclude, calibrator"
    )


class RegionResponse(BaseModel):
    """Response after saving regions."""
    id: str = Field(..., description="Region file identifier")
    path: str = Field(..., description="Path to saved region file")
    format: str = Field(..., description="Region format")
    purpose: str = Field(..., description="Region purpose")
    region_count: int = Field(..., description="Number of regions")
    created_at: str = Field(..., description="Creation timestamp")


class RegionListResponse(BaseModel):
    """Response listing regions for an image."""
    regions: list[RegionResponse] = Field(..., description="List of region files")
    total: int = Field(..., description="Total number of region files")


@router.post("/{image_id}/regions", response_model=RegionResponse)
async def save_regions(
    image_id: str,
    request: RegionCreateRequest,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Save DS9/CRTF regions for an image.
    
    Regions can be used for source identification, exclusion zones,
    or any other purpose requiring spatial annotations.
    
    Raises:
        RecordNotFoundError: If image is not found
        HTTPException: If regions cannot be saved
    """
    from pathlib import Path
    from datetime import datetime
    import uuid
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Determine region file path
    image_path = Path(image.path)
    region_id = str(uuid.uuid4())[:8]
    
    # Build filename with purpose prefix
    purpose_prefix = request.purpose if request.purpose else "regions"
    name_part = f".{request.name}" if request.name else ""
    
    # Determine extension based on format
    if request.format == "json":
        ext = ".json"
    elif request.format == "crtf":
        ext = ".crtf"
    else:
        ext = ".reg"
    
    region_filename = f"{image_path.stem}.{purpose_prefix}{name_part}.{region_id}{ext}"
    region_path = image_path.parent / region_filename
    
    try:
        # Write region file
        region_path.write_text(request.regions)
        
        # Count regions
        if request.format == "json":
            import json
            try:
                data = json.loads(request.regions)
                region_count = len(data) if isinstance(data, list) else 1
            except json.JSONDecodeError:
                region_count = 0
        else:
            region_count = sum(
                1 for line in request.regions.split("\n")
                if line.strip() 
                and not line.strip().startswith("#") 
                and not line.strip().startswith("global")
                and not line.strip().startswith("image")
            )
        
        return RegionResponse(
            id=region_id,
            path=str(region_path),
            format=request.format,
            purpose=request.purpose,
            region_count=region_count,
            created_at=datetime.now().isoformat(),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save regions: {str(e)}"
        )


@router.get("/{image_id}/regions", response_model=RegionListResponse)
async def list_regions(
    image_id: str,
    purpose: Optional[str] = Query(None, description="Filter by purpose"),
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    List all region files for an image.
    
    Raises:
        RecordNotFoundError: If image is not found
    """
    from pathlib import Path
    from datetime import datetime
    import os
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Find region files in same directory (excluding masks)
    image_path = Path(image.path)
    
    regions = []
    for region_file in image_path.parent.glob(f"{image_path.stem}.*"):
        # Skip non-region files and mask files
        if region_file.suffix not in (".reg", ".crtf", ".json"):
            continue
        if ".mask." in region_file.name:
            continue
        
        # Parse filename to extract metadata
        parts = region_file.stem.split(".")
        if len(parts) < 2:
            continue
        
        file_purpose = parts[1] if len(parts) > 1 else "unknown"
        file_id = parts[-1] if len(parts) > 2 else parts[-1]
        
        # Filter by purpose if specified
        if purpose and file_purpose != purpose:
            continue
        
        content = region_file.read_text()
        
        # Count regions
        if region_file.suffix == ".json":
            import json
            try:
                data = json.loads(content)
                region_count = len(data) if isinstance(data, list) else 1
            except json.JSONDecodeError:
                region_count = 0
        else:
            region_count = sum(
                1 for line in content.split("\n")
                if line.strip() 
                and not line.strip().startswith("#") 
                and not line.strip().startswith("global")
                and not line.strip().startswith("image")
            )
        
        regions.append(RegionResponse(
            id=file_id,
            path=str(region_file),
            format="json" if region_file.suffix == ".json" else ("crtf" if region_file.suffix == ".crtf" else "ds9"),
            purpose=file_purpose,
            region_count=region_count,
            created_at=datetime.fromtimestamp(os.path.getmtime(region_file)).isoformat(),
        ))
    
    return RegionListResponse(regions=regions, total=len(regions))


@router.get("/{image_id}/regions/{region_id}")
async def get_region_content(
    image_id: str,
    region_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Get the content of a region file.
    
    Raises:
        RecordNotFoundError: If image or region is not found
    """
    from pathlib import Path
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Find region file
    image_path = Path(image.path)
    
    for region_file in image_path.parent.glob(f"{image_path.stem}.*.{region_id}.*"):
        if region_file.suffix in (".reg", ".crtf", ".json"):
            content = region_file.read_text()
            return {
                "id": region_id,
                "path": str(region_file),
                "content": content,
                "format": "json" if region_file.suffix == ".json" else ("crtf" if region_file.suffix == ".crtf" else "ds9"),
            }
    
    raise RecordNotFoundError("Region", region_id)


@router.delete("/{image_id}/regions/{region_id}")
async def delete_region(
    image_id: str,
    region_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Delete a region file.
    
    Raises:
        RecordNotFoundError: If image or region is not found
    """
    from pathlib import Path
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    # Find and delete region file
    image_path = Path(image.path)
    
    deleted = False
    for region_file in image_path.parent.glob(f"{image_path.stem}.*.{region_id}.*"):
        if region_file.suffix in (".reg", ".crtf", ".json") and ".mask." not in region_file.name:
            region_file.unlink()
            deleted = True
    
    if not deleted:
        raise RecordNotFoundError("Region", region_id)
    
    return {"status": "deleted", "region_id": region_id}
