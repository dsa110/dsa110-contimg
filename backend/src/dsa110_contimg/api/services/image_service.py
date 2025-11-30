"""
Image service - business logic for image operations.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from ..repositories import ImageRepository, ImageRecord


class ImageService:
    """Business logic for image operations."""
    
    def __init__(self, repository: "ImageRepository"):
        self.repo = repository
    
    def get_image(self, image_id: str) -> Optional["ImageRecord"]:
        """Get image by ID."""
        return self.repo.get_by_id(image_id)
    
    def list_images(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["ImageRecord"]:
        """List images with pagination."""
        return self.repo.list_all(limit=limit, offset=offset)
    
    def build_provenance_links(self, image: "ImageRecord") -> dict:
        """Build provenance URLs for an image."""
        return {
            "logs_url": f"/api/logs/{image.run_id}" if image.run_id else None,
            "qa_url": f"/api/qa/image/{image.id}",
            "ms_url": (
                f"/api/ms/{quote(image.ms_path, safe='')}/metadata"
                if image.ms_path else None
            ),
            "image_url": f"/api/images/{image.id}",
        }
    
    def build_qa_report(self, image: "ImageRecord") -> dict:
        """Build comprehensive QA report for an image."""
        warnings = []
        
        # Add warnings based on metrics
        if image.noise_jy and image.noise_jy > 0.01:  # 10 mJy
            warnings.append("High noise level detected")
        if image.dynamic_range and image.dynamic_range < 100:
            warnings.append("Low dynamic range")
        
        return {
            "image_id": str(image.id),
            "qa_grade": image.qa_grade,
            "qa_summary": image.qa_summary,
            "quality_metrics": {
                "noise_rms_jy": image.noise_jy,
                "dynamic_range": image.dynamic_range,
                "theoretical_noise_jy": getattr(image, 'theoretical_noise_jy', None),
            },
            "beam": {
                "major_arcsec": image.beam_major_arcsec,
                "minor_arcsec": image.beam_minor_arcsec,
                "pa_deg": image.beam_pa_deg,
            },
            "source_stats": {
                "n_sources": getattr(image, 'n_sources', None),
                "peak_flux_jy": getattr(image, 'peak_flux_jy', None),
            },
            "flags": [],
            "warnings": warnings,
        }
    
    def validate_fits_file(self, image: "ImageRecord") -> tuple[bool, Optional[str]]:
        """Validate that FITS file exists and is readable."""
        if not image.path:
            return False, "No path specified for image"
        
        if not os.path.exists(image.path):
            return False, f"FITS file not found: {image.path}"
        
        return True, None
    
    def get_fits_filename(self, image: "ImageRecord") -> str:
        """Get the filename for FITS download."""
        return Path(image.path).name if image.path else f"image_{image.id}.fits"
