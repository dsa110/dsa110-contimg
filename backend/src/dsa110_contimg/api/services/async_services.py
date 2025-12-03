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


DEFAULT_MS_ROOTS = "/data/dsa110-contimg,/stage/dsa110-contimg"
DEFAULT_LOG_ROOTS = "/data/dsa110-contimg/state/logs,/data/dsa110-contimg/logs"


def _parse_root_list(env_var: str, default: str) -> list[Path]:
    """Parse a comma-separated list of filesystem roots."""
    raw = os.getenv(env_var) or default
    roots: list[Path] = []
    for item in raw.split(","):
        path_str = item.strip()
        if path_str:
            roots.append(Path(path_str).expanduser().resolve())
    return roots


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
    
    MS_ALLOWED_ROOTS = _parse_root_list("DSA110_ALLOWED_MS_ROOTS", DEFAULT_MS_ROOTS)
    
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
    
    def validate_ms_path(self, ms_path: str) -> tuple[bool, Optional[str], Optional[Path]]:
        """Validate that MS path exists and is inside allowed directories."""
        if not ms_path:
            return False, "No MS path specified", None
        
        resolved = Path(ms_path).expanduser().resolve()
        
        if not self._is_ms_path_allowed(resolved):
            return False, "MS path outside allowed directories", None
        
        if not resolved.exists():
            return False, f"MS not found: {ms_path}", None
        
        return True, None, resolved
    
    @classmethod
    def _is_ms_path_allowed(cls, path: Path) -> bool:
        """Check if a path is within the allowed MS roots."""
        return any(path.is_relative_to(root) for root in cls.MS_ALLOWED_ROOTS)


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
    
    def calculate_variability(
        self,
        source: "SourceRecord",
        epochs: List[dict]
    ) -> dict:
        """
        Calculate variability metrics for a source.
        
        Returns variability analysis including:
        - Variability index (V = std / mean)
        - Modulation index
        - Chi-squared statistics
        - Flux statistics
        """
        if not epochs or len(epochs) < 2:
            return {
                "source_id": source.id,
                "source_name": source.name,
                "n_epochs": len(epochs) if epochs else 0,
                "variability_index": None,
                "modulation_index": None,
                "chi_squared": None,
                "chi_squared_reduced": None,
                "is_variable": None,
                "flux_stats": None,
                "message": "Insufficient epochs for variability analysis (need at least 2)",
            }
        
        # Extract flux values
        fluxes = [e.get("flux_jy") for e in epochs if e.get("flux_jy") is not None]
        errors = [e.get("flux_err_jy") for e in epochs if e.get("flux_err_jy") is not None]
        
        if len(fluxes) < 2:
            return {
                "source_id": source.id,
                "source_name": source.name,
                "n_epochs": len(epochs),
                "variability_index": None,
                "message": "Insufficient flux measurements",
            }
        
        import statistics
        mean_flux = statistics.mean(fluxes)
        std_flux = statistics.stdev(fluxes)
        
        # Variability index V = std / mean
        variability_index = std_flux / mean_flux if mean_flux > 0 else None
        modulation_index = variability_index
        
        # Chi-squared test
        chi_squared = None
        chi_squared_reduced = None
        if errors and len(errors) == len(fluxes):
            chi_squared = sum(
                ((f - mean_flux) / e) ** 2
                for f, e in zip(fluxes, errors) if e > 0
            )
            dof = len(fluxes) - 1
            chi_squared_reduced = chi_squared / dof if dof > 0 else None
        
        # Simple variability classification (V > 0.1)
        is_variable = variability_index is not None and variability_index > 0.1
        
        return {
            "source_id": source.id,
            "source_name": source.name,
            "n_epochs": len(epochs),
            "variability_index": round(variability_index, 4) if variability_index else None,
            "modulation_index": round(modulation_index, 4) if modulation_index else None,
            "chi_squared": round(chi_squared, 2) if chi_squared else None,
            "chi_squared_reduced": round(chi_squared_reduced, 2) if chi_squared_reduced else None,
            "is_variable": is_variable,
            "flux_stats": {
                "mean_jy": round(mean_flux, 6),
                "std_jy": round(std_flux, 6),
                "min_jy": round(min(fluxes), 6),
                "max_jy": round(max(fluxes), 6),
            },
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
    
    LOG_PATHS = [
        "/data/dsa110-contimg/state/logs",
        "/data/dsa110-contimg/logs",
    ]
    
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
    
    def get_job_status(self, job: "JobRecord") -> str:
        """Determine job status from record."""
        if getattr(job, "queue_status", None):
            return job.queue_status
        if job.qa_grade:
            return "completed"
        return "pending"
    
    def build_provenance_links(self, job: "JobRecord") -> dict:
        """Build provenance URLs for a job."""
        return {
            "logs_url": f"/api/logs/{job.run_id}",
            "qa_url": f"/api/qa/job/{job.run_id}",
            "ms_url": (
                f"/api/ms/{quote(job.input_ms_path, safe='')}/metadata"
                if job.input_ms_path else None
            ),
            "image_url": (
                f"/api/images/{job.output_image_id}"
                if job.output_image_id else None
            ),
        }
    
    def find_log_file(self, run_id: str) -> Optional[Path]:
        """Find log file for a job, checking multiple paths."""
        for log_dir in self.LOG_PATHS:
            log_path = Path(log_dir) / f"{run_id}.log"
            if log_path.exists():
                return log_path
        return None
    
    def read_log_tail(self, run_id: str, tail: int = 100) -> dict:
        """Read the last N lines of a job's log file."""
        log_path = self.find_log_file(run_id)
        
        if not log_path:
            return {
                "run_id": run_id,
                "logs": [],
                "error": f"Log file not found for run_id: {run_id}",
            }
        
        try:
            with open(log_path) as f:
                lines = f.readlines()
                return {
                    "run_id": run_id,
                    "logs": lines[-tail:] if tail > 0 else lines,
                    "total_lines": len(lines),
                }
        except IOError as e:
            return {
                "run_id": run_id,
                "logs": [],
                "error": f"Failed to read log file: {str(e)}",
            }
    
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
