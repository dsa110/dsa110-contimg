"""
QA routes.
"""

from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import (
    get_image_service,
    get_ms_service,
    get_job_service,
    get_qa_service,
)
from ..errors import image_not_found, ms_not_found, internal_error
from ..services.image_service import ImageService
from ..services.ms_service import MSService
from ..services.job_service import JobService
from ..services.qa_service import QAService

router = APIRouter(prefix="/qa", tags=["qa"])


@router.get("/image/{image_id}")
async def get_image_qa(
    image_id: str,
    image_service: ImageService = Depends(get_image_service),
    qa_service: QAService = Depends(get_qa_service),
):
    """Get QA report for an image."""
    try:
        image = image_service.get_image(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=image_not_found(image_id).to_dict(),
            )
        
        return qa_service.build_image_qa(image)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve image QA: {str(e)}").to_dict(),
        )


@router.get("/ms/{encoded_path:path}")
async def get_ms_qa(
    encoded_path: str,
    ms_service: MSService = Depends(get_ms_service),
    qa_service: QAService = Depends(get_qa_service),
):
    """Get QA report for a Measurement Set."""
    ms_path = unquote(encoded_path)
    
    try:
        ms_meta = ms_service.get_metadata(ms_path)
        if not ms_meta:
            raise HTTPException(
                status_code=404,
                detail=ms_not_found(ms_path).to_dict(),
            )
        
        return qa_service.build_ms_qa(ms_meta)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve MS QA: {str(e)}").to_dict(),
        )


@router.get("/job/{run_id}")
async def get_job_qa(
    run_id: str,
    job_service: JobService = Depends(get_job_service),
    qa_service: QAService = Depends(get_qa_service),
):
    """Get QA summary for a pipeline job."""
    try:
        job = job_service.get_job(run_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=internal_error(f"Job {run_id} not found").to_dict(),
            )
        
        return qa_service.build_job_qa(job)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve job QA: {str(e)}").to_dict(),
        )
