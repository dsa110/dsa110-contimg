"""
Image routes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
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
            pointing_ra_deg=img.center_ra_deg,
            pointing_dec_deg=img.center_dec_deg,
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


# =============================================================================
# Rating Endpoints
# =============================================================================


class RatingRequest(BaseModel):
    """Request to submit an image rating."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    comment: Optional[str] = Field(None, description="Optional comment")
    rater: Optional[str] = Field(None, description="Username of rater")


class RatingResponse(BaseModel):
    """Response after submitting a rating."""
    image_id: str
    rating: int
    comment: Optional[str]
    rater: Optional[str]
    rated_at: str
    new_average: Optional[float] = None


@router.post("/{image_id}/rating", response_model=RatingResponse)
async def submit_image_rating(
    image_id: str,
    request: RatingRequest,
    service: AsyncImageService = Depends(get_async_image_service),
    _auth: AuthContext = Depends(require_write_access),
):
    """
    Submit a quality rating for an image.

    Ratings help with quality assessment and filtering.

    Raises:
        RecordNotFoundError: If image is not found
    """
    from datetime import datetime
    import sqlite3
    import os
    from pathlib import Path

    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)

    rated_at = datetime.utcnow().isoformat() + "Z"

    # Store rating in database
    db_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )

    new_average = None

    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path), timeout=10.0)
            conn.row_factory = sqlite3.Row

            # Ensure ratings table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS image_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    rater TEXT,
                    rated_at TEXT NOT NULL
                )
            """)

            # Insert rating
            conn.execute(
                """
                INSERT INTO image_ratings (image_id, rating, comment, rater, rated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (image_id, request.rating, request.comment, request.rater, rated_at),
            )

            # Calculate new average
            result = conn.execute(
                "SELECT AVG(rating) as avg_rating FROM image_ratings WHERE image_id = ?",
                (image_id,),
            ).fetchone()

            if result and result["avg_rating"]:
                new_average = round(result["avg_rating"], 2)

            conn.commit()
            conn.close()
        except Exception as e:
            # Log but don't fail - rating is not critical
            pass

    return RatingResponse(
        image_id=image_id,
        rating=request.rating,
        comment=request.comment,
        rater=request.rater,
        rated_at=rated_at,
        new_average=new_average,
    )


# =============================================================================
# Image Delete Endpoint
# =============================================================================


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    delete_files: bool = Query(False, description="Also delete FITS file from disk"),
    service: AsyncImageService = Depends(get_async_image_service),
    _auth: AuthContext = Depends(require_write_access),
):
    """
    Delete an image from the database.

    By default, only removes the database record. Set delete_files=true
    to also delete the FITS file from disk.

    Raises:
        RecordNotFoundError: If image is not found
        HTTPException: If deletion fails
    """
    from pathlib import Path

    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)

    deleted_file = False

    # Delete file if requested
    if delete_files and image.path:
        try:
            file_path = Path(image.path)
            if file_path.exists():
                file_path.unlink()
                deleted_file = True

                # Also delete associated files (masks, regions, thumbnails)
                for related_file in file_path.parent.glob(f"{file_path.stem}.*"):
                    if related_file != file_path:
                        try:
                            related_file.unlink()
                        except OSError:
                            pass
        except OSError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete file: {str(e)}"
            )

    # Delete from database
    try:
        await service.delete_image(image_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete image record: {str(e)}"
        )

    return {
        "status": "deleted",
        "image_id": image_id,
        "file_deleted": deleted_file,
    }


# =============================================================================
# Quicklook/Export Endpoints
# =============================================================================


def _load_image_array(image_path):
    """Load a FITS image as a 2D numpy array and return data plus header."""
    from pathlib import Path
    import numpy as np
    from astropy.io import fits
    
    fits_path = Path(image_path)
    if not fits_path.exists():
        raise FileNotAccessibleError(image_path, "read")
    
    with fits.open(fits_path) as hdul:
        data = None
        header = None
        for hdu in hdul:
            if hdu.data is not None and len(hdu.data.shape) >= 2:
                data = hdu.data
                header = hdu.header
                break
    
    if data is None:
        raise HTTPException(status_code=422, detail="No image data found in FITS file")
    
    # Reduce extra dimensions (e.g., polarization/channel axes)
    while len(data.shape) > 2:
        data = data[0]
    
    return data, header


def _prepare_display_array(data, scale: str = "linear"):
    """Normalize image data to 0-1 and apply optional scaling."""
    import numpy as np
    
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        raise HTTPException(status_code=422, detail="Image contains no finite pixels")
    
    vmin, vmax = np.percentile(finite, [1, 99.5])
    if vmax <= vmin:
        vmax = vmin + 1e-6
    
    scaled = np.clip((data - vmin) / (vmax - vmin), 0, 1)
    scale = (scale or "linear").lower()
    
    if scale == "log":
        scaled = np.log1p(scaled * 1000) / np.log(1001)
    elif scale == "sqrt":
        scaled = np.sqrt(scaled)
    elif scale in ("squared", "square"):
        scaled = np.square(scaled)
    elif scale == "asinh":
        scaled = np.arcsinh(scaled) / np.arcsinh(1)
    
    return np.clip(scaled, 0, 1)


def _render_image_bytes(data, colormap: str = "gray", scale: str = "linear", fmt: str = "png", quality: int | None = None):
    """Render a numpy array to an image byte buffer."""
    import io
    from matplotlib import cm
    from PIL import Image
    
    prepared = _prepare_display_array(data, scale)
    cmap = cm.get_cmap(colormap or "gray")
    rgba = cmap(prepared, bytes=True)
    
    img = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    
    save_kwargs = {"format": fmt.upper()}
    if quality and fmt.lower() in {"jpg", "jpeg", "webp"}:
        save_kwargs["quality"] = max(1, min(quality, 100))
    
    img.save(buf, **save_kwargs)
    buf.seek(0)
    return buf


def _ensure_thumbnail(image_path, thumbnail_path, size: int = 256):
    """Generate a thumbnail PNG if one does not already exist."""
    from pathlib import Path
    
    thumb_path = Path(thumbnail_path)
    if thumb_path.exists():
        return thumb_path
    
    # Try CASA-based thumbnail generation first (best effort)
    try:
        from ..batch.thumbnails import generate_image_thumbnail
        generated = generate_image_thumbnail(str(image_path), str(thumbnail_path), size=size)
        if generated:
            return Path(generated)
    except Exception:
        pass
    
    # Fallback: render quicklook from FITS data
    data, _ = _load_image_array(image_path)
    buf = _render_image_bytes(data, fmt="png")
    
    from PIL import Image
    img = Image.open(buf)
    img.thumbnail((size, size))
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(thumb_path, format="PNG")
    return thumb_path


@router.get("/{image_id}/thumbnail")
async def get_image_thumbnail(
    image_id: str,
    size: int = Query(256, ge=32, le=2048, description="Max thumbnail dimension"),
    service: AsyncImageService = Depends(get_async_image_service),
):
    """Return a PNG thumbnail for quick previews."""
    from pathlib import Path
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    fits_path = Path(image.path)
    if not fits_path.exists():
        raise FileNotAccessibleError(image.path, "read")
    
    thumb_path = fits_path.with_suffix(".thumb.png")
    try:
        generated = _ensure_thumbnail(fits_path, thumb_path, size=size)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate thumbnail: {e}")
    
    return FileResponse(
        path=generated,
        media_type="image/png",
        filename=f"{fits_path.stem}.thumb.png",
    )


@router.get("/{image_id}/png")
async def export_image_png(
    image_id: str,
    colormap: str = Query("gray", description="Matplotlib colormap name"),
    scale: str = Query("linear", description="Intensity scale (linear, log, sqrt, asinh)"),
    quality: int = Query(90, ge=1, le=100, description="Quality hint for lossy formats"),
    service: AsyncImageService = Depends(get_async_image_service),
):
    """Render a FITS image to a PNG quicklook."""
    from pathlib import Path
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    fits_path = Path(image.path)
    if not fits_path.exists():
        raise FileNotAccessibleError(image.path, "read")
    
    try:
        data, _ = _load_image_array(fits_path)
        buf = _render_image_bytes(data, colormap=colormap, scale=scale, fmt="png", quality=quality)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render PNG: {e}")
    
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{fits_path.stem}.png"'},
    )


@router.get("/{image_id}/cutout")
async def get_image_cutout(
    image_id: str,
    ra: float = Query(..., description="Center RA in degrees"),
    dec: float = Query(..., description="Center Dec in degrees"),
    width: float = Query(60.0, description="Cutout width"),
    height: float = Query(60.0, description="Cutout height"),
    unit: str = Query("arcsec", description="Units for width/height (arcsec, arcmin, pixel)"),
    format: str = Query("fits", description="Output format (fits, png, jpg, webp)"),
    colormap: str = Query("gray", description="Colormap for image formats"),
    scale: str = Query("linear", description="Intensity scale for image formats"),
    quality: int = Query(90, ge=1, le=100, description="Quality for JPG/WEBP"),
    service: AsyncImageService = Depends(get_async_image_service),
):
    """Extract a cutout around the requested sky position."""
    from pathlib import Path
    import tempfile
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astropy.nddata import Cutout2D
    from astropy.wcs import WCS
    from astropy.io import fits
    
    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    fits_path = Path(image.path)
    if not fits_path.exists():
        raise FileNotAccessibleError(image.path, "read")
    
    data, header = _load_image_array(fits_path)
    wcs = WCS(header) if header is not None else None
    if wcs is None or not wcs.has_celestial:
        raise HTTPException(status_code=422, detail="Image does not contain WCS information for cutouts")
    
    center = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
    unit_lower = unit.lower()
    if unit_lower == "pixel":
        size = (int(height), int(width))
    elif unit_lower in {"arcsec", "arcmin"}:
        q_unit = u.arcsec if unit_lower == "arcsec" else u.arcmin
        size = (height * q_unit, width * q_unit)
    else:
        raise HTTPException(status_code=400, detail="Invalid unit for cutout")
    
    try:
        cutout = Cutout2D(data, position=center, size=size, wcs=wcs, mode="trim")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to create cutout: {e}")
    
    fmt = format.lower()
    if fmt == "fits":
        with tempfile.NamedTemporaryFile(suffix=".fits", delete=False) as tmp:
            hdu = fits.PrimaryHDU(data=cutout.data, header=cutout.wcs.to_header())
            hdu.writeto(tmp.name, overwrite=True)
            return FileResponse(
                path=tmp.name,
                media_type="application/fits",
                filename=f"{fits_path.stem}_cutout.fits",
            )
    
    media_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    if fmt not in media_map:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    
    buf = _render_image_bytes(cutout.data, colormap=colormap, scale=scale, fmt=fmt, quality=quality)
    return StreamingResponse(
        buf,
        media_type=media_map[fmt],
        headers={"Content-Disposition": f'inline; filename="{fits_path.stem}_cutout.{fmt}"'},
    )


# =============================================================================
# Bulk Download Endpoint
# =============================================================================


class BulkDownloadRequest(BaseModel):
    """Request for bulk download."""
    image_ids: list[str] = Field(..., description="List of image IDs to download")
    format: str = Field(default="zip", description="Archive format (zip, tar)")


async def _build_bulk_archive(
    image_ids: list[str],
    archive_format: str,
    service: AsyncImageService,
):
    """Create a ZIP/TAR archive for the requested images."""
    from pathlib import Path
    import tempfile
    import zipfile
    import tarfile
    
    valid_paths = []
    for image_id in image_ids:
        image = await service.get_image(image_id)
        if image and image.path:
            path = Path(image.path)
            if path.exists():
                valid_paths.append((image_id, path))
    
    if not valid_paths:
        raise HTTPException(
            status_code=404,
            detail="No valid images found for download"
        )
    
    try:
        if archive_format == "tar":
            with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
                archive_path = tmp.name
            
            with tarfile.open(archive_path, "w:gz") as tar:
                for _, path in valid_paths:
                    tar.add(path, arcname=path.name)
            
            media_type = "application/gzip"
            filename = "images.tar.gz"
        else:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                archive_path = tmp.name
            
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for _, path in valid_paths:
                    zf.write(path, arcname=path.name)
            
            media_type = "application/zip"
            filename = "images.zip"
        
        return FileResponse(
            path=archive_path,
            media_type=media_type,
            filename=filename,
            background=None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create archive: {str(e)}"
        )


@router.get("/bulk-download")
async def bulk_download_images_get(
    ids: str = Query(..., description="Comma-separated image IDs"),
    format: str = Query("zip", description="Archive format (zip, tar)"),
    service: AsyncImageService = Depends(get_async_image_service),
):
    """Download multiple images via query parameters."""
    image_ids = [part for part in ids.split(",") if part]
    if not image_ids:
        raise HTTPException(status_code=400, detail="No image IDs provided")
    
    return await _build_bulk_archive(image_ids, format, service)


@router.post("/bulk-download")
async def bulk_download_images(
    request: BulkDownloadRequest,
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Download multiple images as an archive.

    Returns a ZIP or TAR file containing the requested FITS images.

    Raises:
        HTTPException: If no valid images found or archive creation fails
    """
    return await _build_bulk_archive(request.image_ids, request.format, service)


# =============================================================================
# Animation Endpoint
# =============================================================================


@router.get("/{image_id}/animation")
async def get_image_animation(
    image_id: str,
    frames: int = Query(10, ge=2, le=50, description="Number of frames"),
    fps: int = Query(2, ge=1, le=10, description="Frames per second"),
    service: AsyncImageService = Depends(get_async_image_service),
):
    """
    Generate an animated GIF showing different stretches/scales of the image.

    This is useful for visualizing faint features at different intensity levels.

    Raises:
        RecordNotFoundError: If image is not found
        HTTPException: If animation generation fails
    """
    from pathlib import Path
    import tempfile

    image = await service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)

    fits_path = Path(image.path)
    if not fits_path.exists():
        raise FileNotAccessibleError(image.path, "read")

    try:
        # Try to generate animation using astropy/matplotlib
        import numpy as np
        from astropy.io import fits
        from astropy.visualization import (
            AsinhStretch, LinearStretch, LogStretch,
            MinMaxInterval, ZScaleInterval, ImageNormalize
        )
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import imageio

        # Read FITS data
        with fits.open(fits_path) as hdul:
            # Find image data
            data = None
            for hdu in hdul:
                if hdu.data is not None and len(hdu.data.shape) >= 2:
                    data = hdu.data
                    break

            if data is None:
                raise HTTPException(
                    status_code=422,
                    detail="No image data found in FITS file"
                )

            # Handle 3D+ data by taking first slice
            while len(data.shape) > 2:
                data = data[0]

        # Generate frames with different stretches
        frames_list = []
        stretches = [
            ("linear", LinearStretch()),
            ("asinh_0.1", AsinhStretch(0.1)),
            ("asinh_0.5", AsinhStretch(0.5)),
            ("asinh_1", AsinhStretch(1)),
            ("asinh_2", AsinhStretch(2)),
            ("log", LogStretch()),
        ]

        interval = ZScaleInterval()

        for name, stretch in stretches[:frames]:
            fig, ax = plt.subplots(figsize=(6, 6))
            norm = ImageNormalize(data, interval=interval, stretch=stretch)
            ax.imshow(data, origin='lower', cmap='gray', norm=norm)
            ax.set_title(f"Stretch: {name}")
            ax.axis('off')

            # Save to buffer
            fig.canvas.draw()
            frame = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            frame = frame.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            frames_list.append(frame)
            plt.close(fig)

        # Create GIF
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
            gif_path = tmp.name

        imageio.mimsave(gif_path, frames_list, fps=fps, loop=0)

        return FileResponse(
            path=gif_path,
            media_type="image/gif",
            filename=f"{fits_path.stem}_animation.gif",
        )

    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"Animation generation requires additional packages: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate animation: {str(e)}"
        )
