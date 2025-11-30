"""
Measurement Set routes.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import unquote, quote

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_ms_service
from ..errors import ms_not_found, internal_error
from ..schemas import MSDetailResponse, ProvenanceResponse
from ..services.ms_service import MSService

router = APIRouter(prefix="/ms", tags=["measurement-sets"])


@router.get("/{encoded_path:path}/metadata", response_model=MSDetailResponse)
async def get_ms_metadata(
    encoded_path: str,
    service: MSService = Depends(get_ms_service),
):
    """
    Get metadata for a Measurement Set.
    
    The path should be URL-encoded.
    """
    ms_path = unquote(encoded_path)
    
    try:
        ms_meta = service.get_metadata(ms_path)
        if not ms_meta:
            raise HTTPException(
                status_code=404,
                detail=ms_not_found(ms_path).to_dict(),
            )
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve MS metadata: {str(e)}").to_dict(),
        )


@router.get("/{encoded_path:path}/calibrator-matches")
async def get_ms_calibrator_matches(
    encoded_path: str,
    service: MSService = Depends(get_ms_service),
):
    """Get calibrator matches for a Measurement Set."""
    ms_path = unquote(encoded_path)
    
    try:
        ms_meta = service.get_metadata(ms_path)
        if not ms_meta:
            raise HTTPException(
                status_code=404,
                detail=ms_not_found(ms_path).to_dict(),
            )
        
        return {
            "ms_path": ms_path,
            "matches": ms_meta.calibrator_tables or [],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve calibrator matches: {str(e)}").to_dict(),
        )


@router.get("/{encoded_path:path}/provenance", response_model=ProvenanceResponse)
async def get_ms_provenance(
    encoded_path: str,
    service: MSService = Depends(get_ms_service),
):
    """
    Get provenance information for a Measurement Set.
    """
    ms_path = unquote(encoded_path)
    
    try:
        ms_meta = service.get_metadata(ms_path)
        if not ms_meta:
            raise HTTPException(
                status_code=404,
                detail=ms_not_found(ms_path).to_dict(),
            )
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve MS provenance: {str(e)}").to_dict(),
        )
