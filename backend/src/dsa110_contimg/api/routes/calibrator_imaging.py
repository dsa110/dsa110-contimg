"""
Calibrator Imaging API routes.

Provides endpoints for the calibrator imaging test workflow:
1. List bandpass calibrators for a given time
2. Find transits with HDF5 data availability
3. Generate MS from HDF5 files
4. Calibrate the MS
5. Create images
6. Run photometry
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from astropy.time import Time

from dsa110_contimg.calibration.transit import (
    previous_transits,
    upcoming_transits,
    pick_best_observation,
)
from dsa110_contimg.database.calibrators import (
    get_bandpass_calibrators,
    get_calibrators_db_path,
)
from dsa110_contimg.database.hdf5_index import query_subband_groups

from ..database import DatabasePool, get_db_pool
from ..exceptions import (
    RecordNotFoundError,
    DatabaseQueryError,
    ValidationError as APIValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calibrator-imaging", tags=["calibrator-imaging"])


# =============================================================================
# Configuration
# =============================================================================

# Database paths
HDF5_DB_PATH = os.getenv(
    "PIPELINE_HDF5_DB",
    "/data/dsa110-contimg/state/hdf5.sqlite3"
)
PRODUCTS_DB_PATH = os.getenv(
    "PIPELINE_PRODUCTS_DB",
    "/data/dsa110-contimg/state/products.sqlite3"
)
INCOMING_DIR = os.getenv(
    "PIPELINE_INCOMING_DIR",
    "/data/incoming"
)
OUTPUT_MS_DIR = os.getenv(
    "PIPELINE_OUTPUT_MS_DIR",
    "/stage/dsa110-contimg/ms"
)
OUTPUT_IMAGES_DIR = os.getenv(
    "PIPELINE_OUTPUT_IMAGES_DIR",
    "/stage/dsa110-contimg/images"
)


# =============================================================================
# Request/Response Models
# =============================================================================

class CalibratorInfo(BaseModel):
    """Information about a bandpass calibrator."""
    
    id: int
    name: str = Field(..., description="Calibrator name (e.g., '3C286')")
    ra_deg: float = Field(..., description="Right ascension in degrees")
    dec_deg: float = Field(..., description="Declination in degrees")
    flux_jy: Optional[float] = Field(None, description="Flux in Jansky")
    status: str = Field(default="active", description="Status")


class TransitInfo(BaseModel):
    """Information about a calibrator transit."""
    
    transit_time_iso: str = Field(..., description="Transit time in ISO format")
    transit_time_mjd: float = Field(..., description="Transit time in MJD")
    has_data: bool = Field(..., description="Whether HDF5 data is available")
    num_subband_groups: int = Field(default=0, description="Number of subband groups available")
    observation_ids: List[str] = Field(default_factory=list, description="Available observation IDs")


class CalibratorWithTransits(BaseModel):
    """Calibrator with transit information."""
    
    calibrator: CalibratorInfo
    transits: List[TransitInfo]


class ObservationInfo(BaseModel):
    """Information about an available observation."""
    
    observation_id: str = Field(..., description="Observation identifier (timestamp)")
    start_time_iso: str = Field(..., description="Start time in ISO format")
    mid_time_iso: str = Field(..., description="Mid-point time in ISO format")
    end_time_iso: str = Field(..., description="End time in ISO format")
    num_subbands: int = Field(..., description="Number of subbands available")
    file_paths: List[str] = Field(..., description="Paths to HDF5 files")
    delta_from_transit_min: float = Field(..., description="Distance from transit in minutes")


class MSGenerationRequest(BaseModel):
    """Request to generate an MS from HDF5 files."""
    
    calibrator_name: str = Field(..., description="Calibrator name")
    observation_id: str = Field(..., description="Observation identifier")
    output_name: Optional[str] = Field(None, description="Optional output MS name")


class MSGenerationResponse(BaseModel):
    """Response from MS generation."""
    
    job_id: str = Field(..., description="Background job ID")
    status: str = Field(..., description="Job status")
    ms_path: Optional[str] = Field(None, description="Output MS path (when complete)")


class CalibrationRequest(BaseModel):
    """Request to calibrate an MS."""
    
    ms_path: str = Field(..., description="Path to the MS")
    calibrator_name: str = Field(..., description="Calibrator name for model")


class CalibrationResponse(BaseModel):
    """Response from calibration."""
    
    job_id: str = Field(..., description="Background job ID")
    status: str = Field(..., description="Job status")
    cal_table_path: Optional[str] = Field(None, description="Output cal table path")


class ImagingRequest(BaseModel):
    """Request to create an image."""
    
    ms_path: str = Field(..., description="Path to the calibrated MS")
    imsize: int = Field(default=2048, description="Image size in pixels")
    cell: str = Field(default="2.5arcsec", description="Cell size")
    niter: int = Field(default=5000, description="Number of clean iterations")
    threshold: str = Field(default="1mJy", description="Clean threshold")


class ImagingResponse(BaseModel):
    """Response from imaging."""
    
    job_id: str = Field(..., description="Background job ID")
    status: str = Field(..., description="Job status")
    image_path: Optional[str] = Field(None, description="Output image path")


class JobStatus(str, Enum):
    """Job status enum."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobInfo(BaseModel):
    """Information about a background job."""
    
    job_id: str
    job_type: str
    status: JobStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[dict] = None


class PhotometryResult(BaseModel):
    """Photometry measurement result."""
    
    source_name: str
    ra_deg: float
    dec_deg: float
    peak_flux_jy: float
    integrated_flux_jy: float
    rms_jy: float
    snr: float


# =============================================================================
# In-memory job tracking (for demo purposes)
# In production, this would use a proper job queue like Celery
# =============================================================================

_jobs: dict[str, JobInfo] = {}


def create_job(job_type: str) -> str:
    """Create a new job and return its ID."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = JobInfo(
        job_id=job_id,
        job_type=job_type,
        status=JobStatus.PENDING,
        created_at=datetime.utcnow().isoformat(),
    )
    return job_id


def get_job(job_id: str) -> Optional[JobInfo]:
    """Get job info by ID."""
    return _jobs.get(job_id)


def update_job(job_id: str, **kwargs):
    """Update job info."""
    if job_id in _jobs:
        job = _jobs[job_id]
        for k, v in kwargs.items():
            setattr(job, k, v)


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/calibrators", response_model=List[CalibratorInfo])
async def list_calibrators(
    status: str = Query("active", description="Filter by status"),
) -> List[CalibratorInfo]:
    """
    List all bandpass calibrators.
    
    Returns calibrators from the database that can be used for
    bandpass calibration.
    """
    try:
        calibrators = get_bandpass_calibrators(status=status)
    except Exception as e:
        logger.error(f"Failed to get calibrators: {e}")
        raise DatabaseQueryError("calibrator_list", str(e))
    
    return [
        CalibratorInfo(
            id=cal.get("id", 0),
            name=cal["calibrator_name"],
            ra_deg=cal["ra_deg"],
            dec_deg=cal["dec_deg"],
            flux_jy=cal.get("flux_jy"),
            status=cal.get("status", "active"),
        )
        for cal in calibrators
    ]


@router.get("/calibrators/{calibrator_name}/transits", response_model=List[TransitInfo])
async def get_calibrator_transits(
    calibrator_name: str,
    days_back: int = Query(7, ge=1, le=30, description="Days to look back"),
    days_forward: int = Query(2, ge=0, le=14, description="Days to look forward"),
) -> List[TransitInfo]:
    """
    Get transit times for a calibrator with data availability.
    
    Returns a list of transit times, indicating which have HDF5 data
    available in the archive.
    """
    # Look up calibrator
    calibrators = get_bandpass_calibrators()
    cal = next((c for c in calibrators if c["calibrator_name"] == calibrator_name), None)
    
    if not cal:
        raise RecordNotFoundError("Calibrator", calibrator_name)
    
    ra_deg = cal["ra_deg"]
    now = Time.now()
    
    # Get previous and upcoming transits
    prev = previous_transits(ra_deg, start_time=now, n=days_back)
    upcoming = upcoming_transits(ra_deg, start_time=now, n=days_forward)
    
    all_transits = prev + upcoming
    all_transits.sort(key=lambda t: t.mjd)
    
    # Check data availability for each transit
    transit_infos = []
    
    for transit in all_transits:
        transit_iso = transit.iso
        
        # Check for HDF5 data within ±30 minutes of transit
        window_start = (transit - 30 * 60 * u.s).iso if hasattr(transit, 'iso') else str(transit)
        window_end = (transit + 30 * 60 * u.s).iso if hasattr(transit, 'iso') else str(transit)
        
        try:
            import astropy.units as u
            window_start = (transit - 30 * u.min).iso
            window_end = (transit + 30 * u.min).iso
            
            # Query HDF5 database for subband groups
            if os.path.exists(HDF5_DB_PATH):
                groups = query_subband_groups(
                    HDF5_DB_PATH,
                    window_start,
                    window_end,
                    tolerance_s=1.0,
                    cluster_tolerance_s=60.0,
                )
                has_data = len(groups) > 0
                num_groups = len(groups)
                # Extract observation IDs from file paths
                obs_ids = []
                for group in groups:
                    if group:
                        # Extract timestamp from first file in group
                        filename = os.path.basename(group[0])
                        obs_id = filename.split("_sb")[0] if "_sb" in filename else filename.replace(".hdf5", "")
                        obs_ids.append(obs_id)
            else:
                has_data = False
                num_groups = 0
                obs_ids = []
        except Exception as e:
            logger.warning(f"Failed to check HDF5 data for transit {transit_iso}: {e}")
            has_data = False
            num_groups = 0
            obs_ids = []
        
        transit_infos.append(TransitInfo(
            transit_time_iso=transit.iso,
            transit_time_mjd=transit.mjd,
            has_data=has_data,
            num_subband_groups=num_groups,
            observation_ids=obs_ids,
        ))
    
    return transit_infos


@router.get("/calibrators/{calibrator_name}/observations", response_model=List[ObservationInfo])
async def get_calibrator_observations(
    calibrator_name: str,
    transit_time_iso: str = Query(..., description="Target transit time in ISO format"),
    window_minutes: int = Query(60, ge=5, le=180, description="Search window in minutes"),
) -> List[ObservationInfo]:
    """
    Get available observations around a specific transit time.
    
    Returns detailed information about HDF5 subband groups available
    near the specified transit time.
    """
    # Look up calibrator
    calibrators = get_bandpass_calibrators()
    cal = next((c for c in calibrators if c["calibrator_name"] == calibrator_name), None)
    
    if not cal:
        raise RecordNotFoundError("Calibrator", calibrator_name)
    
    try:
        import astropy.units as u
        transit = Time(transit_time_iso)
        window_start = (transit - window_minutes * u.min).iso
        window_end = (transit + window_minutes * u.min).iso
    except Exception as e:
        raise APIValidationError(f"Invalid transit time: {e}")
    
    if not os.path.exists(HDF5_DB_PATH):
        logger.warning(f"HDF5 database not found at {HDF5_DB_PATH}")
        return []
    
    try:
        groups = query_subband_groups(
            HDF5_DB_PATH,
            window_start,
            window_end,
            tolerance_s=1.0,
            cluster_tolerance_s=60.0,
        )
    except Exception as e:
        logger.error(f"Failed to query HDF5 database: {e}")
        raise DatabaseQueryError("hdf5_query", str(e))
    
    observations = []
    for group in groups:
        if not group:
            continue
        
        # Extract observation info from file paths
        try:
            from dsa110_contimg.utils import get_uvh5_mid_mjd
            
            # Get observation ID from first file
            first_file = group[0]
            filename = os.path.basename(first_file)
            obs_id = filename.split("_sb")[0] if "_sb" in filename else filename.replace(".hdf5", "")
            
            # Estimate times from observation ID (which is typically a timestamp)
            try:
                start_time = Time(obs_id)
                # Typical observation is ~5 minutes
                mid_time = start_time + 2.5 * u.min
                end_time = start_time + 5 * u.min
            except Exception:
                # If obs_id isn't a valid timestamp, use MJD from file
                mid_mjd = get_uvh5_mid_mjd(first_file) if os.path.exists(first_file) else None
                if mid_mjd:
                    mid_time = Time(mid_mjd, format="mjd")
                    start_time = mid_time - 2.5 * u.min
                    end_time = mid_time + 2.5 * u.min
                else:
                    continue
            
            # Calculate distance from transit
            delta_min = abs((mid_time - transit).to(u.min).value)
            
            observations.append(ObservationInfo(
                observation_id=obs_id,
                start_time_iso=start_time.iso,
                mid_time_iso=mid_time.iso,
                end_time_iso=end_time.iso,
                num_subbands=len(group),
                file_paths=group,
                delta_from_transit_min=delta_min,
            ))
        except Exception as e:
            logger.warning(f"Failed to process observation group: {e}")
            continue
    
    # Sort by distance from transit
    observations.sort(key=lambda o: o.delta_from_transit_min)
    
    return observations


@router.post("/generate-ms", response_model=MSGenerationResponse)
async def generate_ms(
    request: MSGenerationRequest,
    background_tasks: BackgroundTasks,
) -> MSGenerationResponse:
    """
    Start MS generation from HDF5 files.
    
    This starts a background job to convert HDF5 subband files
    to a Measurement Set.
    """
    job_id = create_job("ms_generation")
    
    # Schedule background task
    background_tasks.add_task(
        _run_ms_generation,
        job_id,
        request.calibrator_name,
        request.observation_id,
        request.output_name,
    )
    
    return MSGenerationResponse(
        job_id=job_id,
        status="pending",
        ms_path=None,
    )


async def _run_ms_generation(
    job_id: str,
    calibrator_name: str,
    observation_id: str,
    output_name: Optional[str],
):
    """Background task to generate MS from HDF5 files."""
    update_job(job_id, status=JobStatus.RUNNING, started_at=datetime.utcnow().isoformat())
    
    try:
        # Determine output path
        if output_name:
            ms_path = os.path.join(OUTPUT_MS_DIR, f"{output_name}.ms")
        else:
            ms_path = os.path.join(OUTPUT_MS_DIR, f"{calibrator_name}_{observation_id}.ms")
        
        # In a real implementation, this would call the conversion pipeline
        # For now, we simulate the conversion
        from dsa110_contimg.conversion.cli import main as conversion_main
        
        # Find the observation files
        # This would query the HDF5 database and run the converter
        logger.info(f"Starting MS generation for {observation_id} -> {ms_path}")
        
        # Simulate processing time
        await asyncio.sleep(2)
        
        # Check if files exist in incoming directory
        # In production, would actually run conversion
        
        update_job(
            job_id,
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow().isoformat(),
            result={"ms_path": ms_path},
        )
    except Exception as e:
        logger.error(f"MS generation failed: {e}")
        update_job(
            job_id,
            status=JobStatus.FAILED,
            completed_at=datetime.utcnow().isoformat(),
            error_message=str(e),
        )


@router.post("/calibrate", response_model=CalibrationResponse)
async def calibrate_ms(
    request: CalibrationRequest,
    background_tasks: BackgroundTasks,
) -> CalibrationResponse:
    """
    Start calibration of an MS.
    
    This starts a background job to calibrate the MS using
    the specified calibrator model.
    """
    job_id = create_job("calibration")
    
    background_tasks.add_task(
        _run_calibration,
        job_id,
        request.ms_path,
        request.calibrator_name,
    )
    
    return CalibrationResponse(
        job_id=job_id,
        status="pending",
        cal_table_path=None,
    )


async def _run_calibration(
    job_id: str,
    ms_path: str,
    calibrator_name: str,
):
    """Background task to calibrate MS."""
    update_job(job_id, status=JobStatus.RUNNING, started_at=datetime.utcnow().isoformat())
    
    try:
        logger.info(f"Starting calibration for {ms_path} with {calibrator_name}")
        
        # In production, would run actual calibration
        # from dsa110_contimg.calibration import run_calibration
        
        # Simulate processing
        await asyncio.sleep(3)
        
        cal_table_path = ms_path.replace(".ms", ".bcal")
        
        update_job(
            job_id,
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow().isoformat(),
            result={"cal_table_path": cal_table_path},
        )
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        update_job(
            job_id,
            status=JobStatus.FAILED,
            completed_at=datetime.utcnow().isoformat(),
            error_message=str(e),
        )


@router.post("/image", response_model=ImagingResponse)
async def create_image(
    request: ImagingRequest,
    background_tasks: BackgroundTasks,
) -> ImagingResponse:
    """
    Start imaging of a calibrated MS.
    
    This starts a background job to create an image from
    the calibrated MS.
    """
    job_id = create_job("imaging")
    
    background_tasks.add_task(
        _run_imaging,
        job_id,
        request.ms_path,
        request.imsize,
        request.cell,
        request.niter,
        request.threshold,
    )
    
    return ImagingResponse(
        job_id=job_id,
        status="pending",
        image_path=None,
    )


async def _run_imaging(
    job_id: str,
    ms_path: str,
    imsize: int,
    cell: str,
    niter: int,
    threshold: str,
):
    """Background task to create image."""
    update_job(job_id, status=JobStatus.RUNNING, started_at=datetime.utcnow().isoformat())
    
    try:
        logger.info(f"Starting imaging for {ms_path}")
        
        # In production, would run actual imaging
        # from dsa110_contimg.imaging import run_tclean
        
        # Simulate processing
        await asyncio.sleep(5)
        
        ms_basename = os.path.basename(ms_path).replace(".ms", "")
        image_path = os.path.join(OUTPUT_IMAGES_DIR, f"{ms_basename}.image.fits")
        
        update_job(
            job_id,
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow().isoformat(),
            result={"image_path": image_path},
        )
    except Exception as e:
        logger.error(f"Imaging failed: {e}")
        update_job(
            job_id,
            status=JobStatus.FAILED,
            completed_at=datetime.utcnow().isoformat(),
            error_message=str(e),
        )


@router.get("/job/{job_id}", response_model=JobInfo)
async def get_job_status(job_id: str) -> JobInfo:
    """
    Get status of a background job.
    """
    job = get_job(job_id)
    if not job:
        raise RecordNotFoundError("Job", job_id)
    return job


@router.get("/photometry/{image_path:path}", response_model=PhotometryResult)
async def get_photometry(
    image_path: str,
    source_name: Optional[str] = Query(None, description="Source name to measure"),
    ra_deg: Optional[float] = Query(None, description="RA in degrees"),
    dec_deg: Optional[float] = Query(None, description="Dec in degrees"),
) -> PhotometryResult:
    """
    Get photometry measurements for an image.
    
    If source_name is provided, looks up coordinates from calibrator database.
    Otherwise, ra_deg and dec_deg must be provided.
    """
    if source_name:
        # Look up calibrator coordinates
        calibrators = get_bandpass_calibrators()
        cal = next((c for c in calibrators if c["calibrator_name"] == source_name), None)
        if cal:
            ra_deg = cal["ra_deg"]
            dec_deg = cal["dec_deg"]
        else:
            raise RecordNotFoundError("Calibrator", source_name)
    
    if ra_deg is None or dec_deg is None:
        raise APIValidationError("Either source_name or (ra_deg, dec_deg) must be provided")
    
    # In production, would run actual photometry
    # from dsa110_contimg.photometry import measure_flux
    
    # Return placeholder values for demo
    return PhotometryResult(
        source_name=source_name or "unknown",
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        peak_flux_jy=1.5,  # Placeholder
        integrated_flux_jy=2.0,  # Placeholder
        rms_jy=0.001,  # Placeholder
        snr=150.0,  # Placeholder
    )


# =============================================================================
# Health check
# =============================================================================

@router.get("/health")
async def health_check():
    """Check health of calibrator imaging API."""
    return {
        "status": "healthy",
        "hdf5_db_exists": os.path.exists(HDF5_DB_PATH),
        "calibrators_db_exists": os.path.exists(str(get_calibrators_db_path())),
        "incoming_dir_exists": os.path.exists(INCOMING_DIR),
        "output_ms_dir_exists": os.path.exists(OUTPUT_MS_DIR),
        "output_images_dir_exists": os.path.exists(OUTPUT_IMAGES_DIR),
    }
