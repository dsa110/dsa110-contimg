"""
Async service layer - business logic for async operations.

This module provides async versions of all services, using async repositories
for non-blocking database operations.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from ..async_repositories import (
        AsyncImageRepository,
        AsyncMSRepository,
        AsyncSourceRepository,
        AsyncJobRepository,
    )
    from ..repositories import ImageRecord, MSRecord, SourceRecord, JobRecord


class AsyncImageService:
    """Async business logic for image operations."""
    
    def __init__(self, repository: "AsyncImageRepository"):
        self.repo = repository
    
    async def get_image(self, image_id: str) -> Optional["ImageRecord"]:
        """Get image by ID."""
        return await self.repo.get_by_id(image_id)
    
    async def list_images(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["ImageRecord"]:
        """List images with pagination."""
        return await self.repo.list_all(limit=limit, offset=offset)
    
    async def count_images(self) -> int:
        """Get total count of images."""
        return await self.repo.count()
    
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
            "flags": image.qa_flags or [],
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


class AsyncMSService:
    """Async business logic for Measurement Set operations."""
    
    def __init__(self, repository: "AsyncMSRepository"):
        self.repo = repository
    
    async def get_ms_metadata(self, ms_path: str) -> Optional["MSRecord"]:
        """Get MS metadata by path."""
        return await self.repo.get_metadata(ms_path)
    
    async def list_ms(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["MSRecord"]:
        """List MS records with pagination."""
        return await self.repo.list_all(limit=limit, offset=offset)
    
    def build_ms_summary(self, ms: "MSRecord") -> dict:
        """Build summary information for an MS."""
        return {
            "path": ms.path,
            "stage": ms.stage,
            "status": ms.status,
            "qa_grade": ms.qa_grade,
            "calibrated": bool(ms.cal_applied),
            "has_image": bool(ms.imagename),
            "coordinates": {
                "ra_deg": ms.ra_deg or ms.pointing_ra_deg,
                "dec_deg": ms.dec_deg or ms.pointing_dec_deg,
            },
            "time_range": {
                "start_mjd": ms.start_mjd,
                "end_mjd": ms.end_mjd,
                "mid_mjd": ms.mid_mjd,
            },
        }
    
    def validate_ms_path(self, ms_path: str) -> tuple[bool, Optional[str]]:
        """Validate that MS path exists."""
        if not ms_path:
            return False, "No MS path specified"
        
        if not os.path.exists(ms_path):
            return False, f"MS not found: {ms_path}"
        
        return True, None


class AsyncSourceService:
    """Async business logic for source catalog operations."""
    
    def __init__(self, repository: "AsyncSourceRepository"):
        self.repo = repository
    
    async def get_source(self, source_id: str) -> Optional["SourceRecord"]:
        """Get source by ID."""
        return await self.repo.get_by_id(source_id)
    
    async def list_sources(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["SourceRecord"]:
        """List sources with pagination."""
        return await self.repo.list_all(limit=limit, offset=offset)
    
    async def get_lightcurve(
        self,
        source_id: str,
        start_mjd: Optional[float] = None,
        end_mjd: Optional[float] = None
    ) -> List[dict]:
        """Get lightcurve data for a source."""
        return await self.repo.get_lightcurve(source_id, start_mjd, end_mjd)
    
    def build_source_summary(self, source: "SourceRecord") -> dict:
        """Build summary information for a source."""
        return {
            "id": source.id,
            "name": source.name,
            "coordinates": {
                "ra_deg": source.ra_deg,
                "dec_deg": source.dec_deg,
            },
            "n_observations": len(source.contributing_images or []),
            "latest_image_id": source.latest_image_id,
        }
    
    def calculate_variability_metrics(self, lightcurve: List[dict]) -> dict:
        """Calculate variability metrics from lightcurve data."""
        if not lightcurve:
            return {}
        
        fluxes = [point["flux_jy"] for point in lightcurve if point.get("flux_jy")]
        if not fluxes:
            return {}
        
        import statistics
        
        mean_flux = statistics.mean(fluxes)
        std_flux = statistics.stdev(fluxes) if len(fluxes) > 1 else 0.0
        
        return {
            "mean_flux_jy": mean_flux,
            "std_flux_jy": std_flux,
            "variability_index": std_flux / mean_flux if mean_flux > 0 else 0.0,
            "n_measurements": len(fluxes),
            "flux_range": {
                "min": min(fluxes),
                "max": max(fluxes),
            },
        }


class AsyncJobService:
    """Async business logic for pipeline job operations."""
    
    def __init__(self, repository: "AsyncJobRepository"):
        self.repo = repository
    
    async def get_job(self, run_id: str) -> Optional["JobRecord"]:
        """Get job by run ID."""
        return await self.repo.get_by_run_id(run_id)
    
    async def list_jobs(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["JobRecord"]:
        """List jobs with pagination."""
        return await self.repo.list_all(limit=limit, offset=offset)
    
    def build_job_summary(self, job: "JobRecord") -> dict:
        """Build summary information for a job."""
        return {
            "run_id": job.run_id,
            "status": job.queue_status or "unknown",
            "qa_grade": job.qa_grade,
            "input_ms": job.input_ms_path,
            "output_image_id": job.output_image_id,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "phase_center": {
                "ra_deg": job.phase_center_ra,
                "dec_deg": job.phase_center_dec,
            },
        }
    
    def estimate_completion_time(self, job: "JobRecord") -> Optional[datetime]:
        """Estimate job completion time based on status and history."""
        # Placeholder - would need historical data to implement properly
        if job.queue_status in ["completed", "failed"]:
            return job.started_at
        return None
