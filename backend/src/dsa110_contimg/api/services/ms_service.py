"""
Measurement Set service - business logic for MS operations.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from ..repositories import MSRepository, MSRecord


class MSService:
    """Business logic for measurement set operations."""
    
    def __init__(self, repository: "MSRepository"):
        self.repo = repository
    
    async def get_metadata(self, ms_path: str) -> Optional["MSRecord"]:
        """Get metadata for a measurement set."""
        return self.repo.get_metadata(ms_path)
    
    def get_pointing(self, ms: "MSRecord") -> tuple[Optional[float], Optional[float]]:
        """Get pointing coordinates, preferring explicit pointing over derived."""
        ra = ms.pointing_ra_deg or ms.ra_deg
        dec = ms.pointing_dec_deg or ms.dec_deg
        return ra, dec
    
    def get_primary_cal_table(self, ms: "MSRecord") -> Optional[str]:
        """Get the primary calibration table path."""
        if ms.calibrator_tables and len(ms.calibrator_tables) > 0:
            return ms.calibrator_tables[0].get("cal_table")
        return None
    
    def build_provenance_links(self, ms: "MSRecord") -> dict:
        """Build provenance URLs for a measurement set."""
        ms_path_encoded = quote(ms.path, safe='')
        return {
            "logs_url": f"/api/logs/{ms.run_id}" if ms.run_id else None,
            "qa_url": f"/api/qa/ms/{ms_path_encoded}",
            "ms_url": f"/api/ms/{ms_path_encoded}/metadata",
            "image_url": f"/api/images/{ms.imagename}" if ms.imagename else None,
        }
