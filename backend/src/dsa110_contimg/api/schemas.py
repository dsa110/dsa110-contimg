"""
Pydantic models for API request/response schemas.

These models define the data structures used by the API endpoints
and are designed to align with frontend TypeScript types.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class CalibratorMatch(BaseModel):
    """A calibrator table match for a Measurement Set."""
    cal_table: str = Field(..., description="Path to calibration table")
    type: str = Field(..., description="Calibrator type (e.g., 'flux', 'phase', 'bandpass')")


class ImageDetailResponse(BaseModel):
    """Response model for image detail endpoint."""
    id: str = Field(..., description="Unique image identifier")
    path: str = Field(..., description="Full path to the image file")
    ms_path: Optional[str] = Field(None, description="Path to source Measurement Set")
    cal_table: Optional[str] = Field(None, description="Path to calibration table used")
    pointing_ra_deg: Optional[float] = Field(None, description="Pointing RA in degrees")
    pointing_dec_deg: Optional[float] = Field(None, description="Pointing Dec in degrees")
    qa_grade: Optional[Literal["good", "warn", "fail"]] = Field(None, description="QA assessment grade")
    qa_summary: Optional[str] = Field(None, description="Brief QA summary (e.g., 'RMS 0.35 mJy')")
    run_id: Optional[str] = Field(None, description="Pipeline run/job ID")
    created_at: Optional[datetime] = Field(None, description="Image creation timestamp")
    # Image versioning fields
    parent_id: Optional[str] = Field(None, description="ID of parent image (for re-imaged products)")
    version: int = Field(default=1, description="Image version number (1 for originals)")
    imaging_params: Optional[dict] = Field(None, description="Imaging parameters used")
    mask_path: Optional[str] = Field(None, description="Path to associated mask file")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "img-20250115-001",
                "path": "/data/images/20250115/img-001.fits",
                "ms_path": "/data/ms/20250115/obs-001.ms",
                "cal_table": "/data/cal/20250115/cal-001.tbl",
                "pointing_ra_deg": 180.0,
                "pointing_dec_deg": -30.0,
                "qa_grade": "good",
                "qa_summary": "RMS 0.35 mJy, DR 1200",
                "run_id": "job-456",
                "created_at": "2025-01-15T10:30:00Z",
                "parent_id": None,
                "version": 1,
                "imaging_params": {
                    "imsize": [5040, 5040],
                    "cell": "2.5arcsec",
                    "weighting": "briggs",
                    "robust": 0.5
                },
                "mask_path": None
            }
        }


class MSDetailResponse(BaseModel):
    """Response model for Measurement Set detail endpoint."""
    path: str = Field(..., description="Full path to the MS")
    pointing_ra_deg: Optional[float] = Field(None, description="Phase center RA in degrees")
    pointing_dec_deg: Optional[float] = Field(None, description="Phase center Dec in degrees")
    calibrator_matches: Optional[list[CalibratorMatch]] = Field(
        None, description="Matched calibration tables"
    )
    qa_grade: Optional[Literal["good", "warn", "fail"]] = Field(None, description="QA grade")
    qa_summary: Optional[str] = Field(None, description="Brief QA summary")
    run_id: Optional[str] = Field(None, description="Pipeline run/job ID")
    created_at: Optional[datetime] = Field(None, description="MS creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "path": "/data/ms/20250115/obs-001.ms",
                "pointing_ra_deg": 180.0,
                "pointing_dec_deg": -30.0,
                "calibrator_matches": [
                    {"cal_table": "/data/cal/flux.tbl", "type": "flux"},
                    {"cal_table": "/data/cal/phase.tbl", "type": "phase"}
                ],
                "qa_grade": "warn",
                "qa_summary": "High RFI in subbands 5-8",
                "run_id": "job-123",
                "created_at": "2025-01-15T08:00:00Z"
            }
        }


class ContributingImage(BaseModel):
    """An image that contributed to a source detection."""
    image_id: str = Field(..., description="Image identifier")
    path: str = Field(..., description="Image file path")
    ms_path: Optional[str] = Field(None, description="Source MS path")
    qa_grade: Optional[Literal["good", "warn", "fail"]] = Field(None, description="QA grade")
    created_at: Optional[datetime] = Field(None, description="Image creation time")


class SourceDetailResponse(BaseModel):
    """Response model for source detail endpoint."""
    id: str = Field(..., description="Unique source identifier")
    name: Optional[str] = Field(None, description="Source name (if cataloged)")
    ra_deg: float = Field(..., description="Source RA in degrees")
    dec_deg: float = Field(..., description="Source Dec in degrees")
    contributing_images: Optional[list[ContributingImage]] = Field(
        None, description="Images where this source was detected"
    )
    latest_image_id: Optional[str] = Field(None, description="Most recent contributing image ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "src-001",
                "name": "DSA-110 J1200-3000",
                "ra_deg": 180.0,
                "dec_deg": -30.0,
                "contributing_images": [
                    {
                        "image_id": "img-001",
                        "path": "/data/images/img-001.fits",
                        "qa_grade": "good",
                        "created_at": "2025-01-15T10:30:00Z"
                    }
                ],
                "latest_image_id": "img-001"
            }
        }


class ProvenanceResponse(BaseModel):
    """Response model for job provenance endpoint."""
    run_id: str = Field(..., description="Job/pipeline run ID")
    ms_path: Optional[str] = Field(None, description="Input MS path")
    cal_table: Optional[str] = Field(None, description="Calibration table used")
    pointing_ra_deg: Optional[float] = Field(None, description="Pointing RA")
    pointing_dec_deg: Optional[float] = Field(None, description="Pointing Dec")
    qa_grade: Optional[Literal["good", "warn", "fail"]] = Field(None, description="QA grade")
    qa_summary: Optional[str] = Field(None, description="QA summary")
    logs_url: Optional[str] = Field(None, description="URL to job logs")
    qa_url: Optional[str] = Field(None, description="URL to QA report")
    ms_url: Optional[str] = Field(None, description="URL to MS detail")
    image_url: Optional[str] = Field(None, description="URL to image detail")
    created_at: Optional[datetime] = Field(None, description="Job start time")


class ImageListResponse(BaseModel):
    """Response model for image list endpoint."""
    id: str = Field(..., description="Unique image identifier")
    path: str = Field(..., description="Full path to the image file")
    qa_grade: Optional[Literal["good", "warn", "fail"]] = Field(None, description="QA assessment grade")
    created_at: Optional[datetime] = Field(None, description="Image creation timestamp")
    run_id: Optional[str] = Field(None, description="Pipeline run/job ID")


class SourceListResponse(BaseModel):
    """Response model for source list endpoint."""
    id: str = Field(..., description="Unique source identifier")
    name: Optional[str] = Field(None, description="Source name")
    ra_deg: float = Field(..., description="Source RA in degrees")
    dec_deg: float = Field(..., description="Source Dec in degrees")
    num_images: int = Field(0, description="Number of contributing images")
    image_id: Optional[str] = Field(None, description="Latest contributing image ID")


class JobListResponse(BaseModel):
    """Response model for job list endpoint."""
    run_id: str = Field(..., description="Job/pipeline run ID")
    status: Literal["pending", "running", "completed", "failed"] = Field(..., description="Job status")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    finished_at: Optional[datetime] = Field(None, description="Job completion time")


# =============================================================================
# QA Response Models
# =============================================================================

class QAMetrics(BaseModel):
    """Common QA metrics for any entity."""
    noise_jy: Optional[float] = Field(None, description="RMS noise in Jy")
    dynamic_range: Optional[float] = Field(None, description="Dynamic range")
    n_sources: Optional[int] = Field(None, description="Number of detected sources")
    peak_flux_jy: Optional[float] = Field(None, description="Peak flux in Jy")


class QAReportResponse(BaseModel):
    """Response model for QA report endpoints."""
    entity_id: str = Field(..., description="ID of the entity (image, MS, job)")
    entity_type: Literal["image", "ms", "job", "source"] = Field(..., description="Type of entity")
    qa_grade: Optional[Literal["good", "warn", "fail"]] = Field(None, description="Overall QA grade")
    qa_summary: Optional[str] = Field(None, description="Brief QA summary")
    metrics: Optional[QAMetrics] = Field(None, description="Detailed QA metrics")
    warnings: list[str] = Field(default_factory=list, description="QA warnings")
    flags: list[str] = Field(default_factory=list, description="QA flags")


# =============================================================================
# Lightcurve and Variability Response Models
# =============================================================================

class LightcurvePoint(BaseModel):
    """A single point in a lightcurve."""
    mjd: float = Field(..., description="Modified Julian Date")
    flux_jy: float = Field(..., description="Flux density in Jy")
    flux_err_jy: Optional[float] = Field(None, description="Flux uncertainty in Jy")
    image_id: Optional[str] = Field(None, description="Source image ID")


class LightcurveResponse(BaseModel):
    """Response model for lightcurve endpoint."""
    source_id: str = Field(..., description="Source identifier")
    data_points: list[LightcurvePoint] = Field(default_factory=list, description="Lightcurve data")


class VariabilityResponse(BaseModel):
    """Response model for variability endpoint."""
    source_id: str = Field(..., description="Source identifier")
    source_name: Optional[str] = Field(None, description="Source name")
    n_epochs: int = Field(..., description="Number of epochs")
    mean_flux_jy: Optional[float] = Field(None, description="Mean flux in Jy")
    std_flux_jy: Optional[float] = Field(None, description="Standard deviation of flux")
    variability_index: Optional[float] = Field(None, description="Variability index (std/mean)")
    modulation_index: Optional[float] = Field(None, description="Modulation index")
    chi_squared: Optional[float] = Field(None, description="Chi-squared statistic")
    is_variable: bool = Field(False, description="Whether source is classified as variable")
    min_flux_jy: Optional[float] = Field(None, description="Minimum flux")
    max_flux_jy: Optional[float] = Field(None, description="Maximum flux")
    mjd_range: Optional[list[float]] = Field(None, description="[min_mjd, max_mjd]")


# =============================================================================
# Stats Response Models
# =============================================================================

class DashboardStats(BaseModel):
    """Response model for dashboard statistics."""
    total_images: int = Field(..., description="Total number of images")
    total_sources: int = Field(..., description="Total number of sources")
    total_jobs: int = Field(..., description="Total number of jobs")
    total_ms: int = Field(..., description="Total number of measurement sets")
    recent_images: int = Field(0, description="Images from last 24 hours")
    recent_jobs: int = Field(0, description="Jobs from last 24 hours")
    qa_good: int = Field(0, description="Images with good QA grade")
    qa_warn: int = Field(0, description="Images with warning QA grade")
    qa_fail: int = Field(0, description="Images with failed QA grade")


# =============================================================================
# MS Visualization Response Models (casangi integration)
# =============================================================================

class RasterPlotParams(BaseModel):
    """Parameters for visibility raster plot request."""
    xaxis: Literal["time", "baseline", "frequency"] = Field(
        "time", description="X-axis dimension"
    )
    yaxis: Literal["amp", "phase", "real", "imag"] = Field(
        "amp", description="Visibility component to plot"
    )
    colormap: str = Field("viridis", description="Matplotlib/Bokeh colormap name")
    width: int = Field(800, ge=200, le=2000, description="Plot width in pixels")
    height: int = Field(600, ge=200, le=2000, description="Plot height in pixels")
    spw: Optional[int] = Field(None, ge=0, description="Spectral window to plot (None=all)")
    antenna: Optional[str] = Field(None, description="Antenna selection (e.g., '0~10')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "xaxis": "time",
                "yaxis": "amp",
                "colormap": "viridis",
                "width": 800,
                "height": 600,
                "spw": 0,
                "antenna": None,
            }
        }


class AntennaInfo(BaseModel):
    """Information about a single antenna in the array."""
    id: int = Field(..., description="Antenna ID (0-indexed)")
    name: str = Field(..., description="Antenna name (e.g., 'DSA-001')")
    x_m: float = Field(..., description="East position in meters (local ENU)")
    y_m: float = Field(..., description="North position in meters (local ENU)")
    flagged_pct: float = Field(
        0.0, ge=0.0, le=100.0, 
        description="Percentage of data flagged for this antenna"
    )
    baseline_count: int = Field(0, ge=0, description="Number of baselines involving this antenna")


class AntennaLayoutResponse(BaseModel):
    """Response model for antenna layout endpoint."""
    antennas: list[AntennaInfo] = Field(..., description="List of antenna positions and stats")
    array_center_lon: float = Field(..., description="Array center longitude (degrees)")
    array_center_lat: float = Field(..., description="Array center latitude (degrees)")
    total_baselines: int = Field(..., description="Total number of baselines")
    
    class Config:
        json_schema_extra = {
            "example": {
                "antennas": [
                    {"id": 0, "name": "DSA-001", "x_m": 0.0, "y_m": 0.0, "flagged_pct": 5.2, "baseline_count": 109},
                    {"id": 1, "name": "DSA-002", "x_m": 10.5, "y_m": 0.0, "flagged_pct": 0.0, "baseline_count": 109},
                ],
                "array_center_lon": -118.2817,
                "array_center_lat": 37.2339,
                "total_baselines": 5995,
            }
        }
