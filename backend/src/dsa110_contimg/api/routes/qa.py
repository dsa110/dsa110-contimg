"""
QA routes.
"""

from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Depends

from ..dependencies import (
    get_image_service,
    get_ms_service,
    get_job_service,
    get_qa_service,
)
from ..exceptions import RecordNotFoundError
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
    """
    Get QA report for an image.
    
    Raises:
        RecordNotFoundError: If image is not found
    """
    image = image_service.get_image(image_id)
    if not image:
        raise RecordNotFoundError("Image", image_id)
    
    return qa_service.build_image_qa(image)


@router.get("/ms/{encoded_path:path}")
async def get_ms_qa(
    encoded_path: str,
    ms_service: MSService = Depends(get_ms_service),
    qa_service: QAService = Depends(get_qa_service),
):
    """
    Get QA report for a Measurement Set.
    
    Raises:
        RecordNotFoundError: If MS is not found
    """
    ms_path = unquote(encoded_path)
    
    ms_meta = ms_service.get_metadata(ms_path)
    if not ms_meta:
        raise RecordNotFoundError("MeasurementSet", ms_path)
    
    return qa_service.build_ms_qa(ms_meta)


@router.get("/job/{run_id}")
async def get_job_qa(
    run_id: str,
    job_service: JobService = Depends(get_job_service),
    qa_service: QAService = Depends(get_qa_service),
):
    """
    Get QA summary for a pipeline job.
    
    Raises:
        RecordNotFoundError: If job is not found
    """
    job = job_service.get_job(run_id)
    if not job:
        raise RecordNotFoundError("Job", run_id)
    
    return qa_service.build_job_qa(job)
