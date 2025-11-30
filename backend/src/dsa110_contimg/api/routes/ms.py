"""
Measurement Set routes.
"""

from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Depends

from ..dependencies import get_async_ms_service
from ..exceptions import RecordNotFoundError
from ..schemas import MSDetailResponse, ProvenanceResponse
from ..services.async_services import AsyncMSService

router = APIRouter(prefix="/ms", tags=["measurement-sets"])


@router.get("/{encoded_path:path}/metadata", response_model=MSDetailResponse)
async def get_ms_metadata(
    encoded_path: str,
    service: AsyncMSService = Depends(get_async_ms_service),
):
    """
    Get metadata for a Measurement Set.
    
    The path should be URL-encoded.
    
    Raises:
        RecordNotFoundError: If MS is not found
    """
    ms_path = unquote(encoded_path)
    
    ms_meta = await service.get_ms_metadata(ms_path)
    if not ms_meta:
        raise RecordNotFoundError("MeasurementSet", ms_path)
    
    ra, dec = service.get_pointing(ms_meta)
    
    return MSDetailResponse(
        path=ms_meta.path,
        pointing_ra_deg=ra,
        pointing_dec_deg=dec,
        calibrator_matches=ms_meta.calibrator_tables,
        qa_grade=ms_meta.qa_grade,
        qa_summary=ms_meta.qa_summary,
        run_id=ms_meta.run_id,
        created_at=ms_meta.created_at,
    )


@router.get("/{encoded_path:path}/calibrator-matches")
async def get_ms_calibrator_matches(
    encoded_path: str,
    service: AsyncMSService = Depends(get_async_ms_service),
):
    """
    Get calibrator matches for a Measurement Set.
    
    Raises:
        RecordNotFoundError: If MS is not found
    """
    ms_path = unquote(encoded_path)
    
    ms_meta = await service.get_ms_metadata(ms_path)
    if not ms_meta:
        raise RecordNotFoundError("MeasurementSet", ms_path)
    
    return {
        "ms_path": ms_path,
        "matches": ms_meta.calibrator_tables or [],
    }


@router.get("/{encoded_path:path}/provenance", response_model=ProvenanceResponse)
async def get_ms_provenance(
    encoded_path: str,
    service: AsyncMSService = Depends(get_async_ms_service),
):
    """
    Get provenance information for a Measurement Set.
    
    Raises:
        RecordNotFoundError: If MS is not found
    """
    ms_path = unquote(encoded_path)
    
    ms_meta = await service.get_ms_metadata(ms_path)
    if not ms_meta:
        raise RecordNotFoundError("MeasurementSet", ms_path)
    
    ra, dec = service.get_pointing(ms_meta)
    cal_table = service.get_primary_cal_table(ms_meta)
    links = service.build_provenance_links(ms_meta)
    
    return ProvenanceResponse(
        run_id=ms_meta.run_id,
        ms_path=ms_path,
        cal_table=cal_table,
        pointing_ra_deg=ra,
        pointing_dec_deg=dec,
        qa_grade=ms_meta.qa_grade,
        qa_summary=ms_meta.qa_summary,
        logs_url=links["logs_url"],
        qa_url=links["qa_url"],
        ms_url=links["ms_url"],
        image_url=links["image_url"],
        created_at=ms_meta.created_at,
    )
