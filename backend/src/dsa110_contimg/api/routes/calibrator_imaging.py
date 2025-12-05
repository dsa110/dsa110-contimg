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
from datetime import datetime
from enum import Enum
from typing import List, Optional

from astropy.time import Time
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from dsa110_contimg.calibration.transit import (
    previous_transits,
    upcoming_transits,
)
from dsa110_contimg.database import (
    get_bandpass_calibrators,
    get_calibrators_db_path,
)
from dsa110_contimg.database.hdf5_index import query_subband_groups

from ..config import get_config
from ..exceptions import (
    DatabaseQueryError,
    RecordNotFoundError,
)
from ..exceptions import (
    ValidationError as APIValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calibrator-imaging", tags=["calibrator-imaging"])


# =============================================================================
# Configuration - use centralized config with env var overrides
# =============================================================================


def get_hdf5_db_path() -> str:
    """Get HDF5 database path from config."""
    config = get_config()
    return str(config.database.hdf5_path)


def get_products_db_path() -> str:
    """Get products database path from config."""
    config = get_config()
    return str(config.database.products_path)


def get_calibrators_db_path_from_config() -> str:
    """Get calibrators database path from config."""
    config = get_config()
    return str(config.database.calibrators_path)


def get_incoming_dir() -> str:
    """Get incoming HDF5 directory."""
    return os.getenv("PIPELINE_INCOMING_DIR", "/data/incoming")


def get_output_ms_dir() -> str:
    """Get output MS directory."""
    return os.getenv("PIPELINE_OUTPUT_MS_DIR", "/stage/dsa110-contimg/ms")


def get_output_images_dir() -> str:
    """Get output images directory."""
    return os.getenv("PIPELINE_OUTPUT_IMAGES_DIR", "/stage/dsa110-contimg/images")


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
    observation_ids: List[str] = Field(
        default_factory=list, description="Available observation IDs"
    )


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
        transit_iso = transit.isot  # Use T separator format for database queries

        try:
            import astropy.units as u

            window_start = (transit - 30 * u.min).isot
            window_end = (transit + 30 * u.min).isot

            # Query HDF5 database for subband groups
            hdf5_db = get_hdf5_db_path()
            if os.path.exists(hdf5_db):
                groups = query_subband_groups(
                    hdf5_db,
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
                        obs_id = (
                            filename.split("_sb")[0]
                            if "_sb" in filename
                            else filename.replace(".hdf5", "")
                        )
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

        transit_infos.append(
            TransitInfo(
                transit_time_iso=transit.isot,  # Use T separator for consistency
                transit_time_mjd=transit.mjd,
                has_data=has_data,
                num_subband_groups=num_groups,
                observation_ids=obs_ids,
            )
        )

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
        window_start = (transit - window_minutes * u.min).isot  # Use T separator for DB queries
        window_end = (transit + window_minutes * u.min).isot
    except Exception as e:
        raise APIValidationError(f"Invalid transit time: {e}")

    hdf5_db = get_hdf5_db_path()
    if not os.path.exists(hdf5_db):
        logger.warning(f"HDF5 database not found at {hdf5_db}")
        return []

    try:
        groups = query_subband_groups(
            hdf5_db,
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
            obs_id = (
                filename.split("_sb")[0] if "_sb" in filename else filename.replace(".hdf5", "")
            )

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

            observations.append(
                ObservationInfo(
                    observation_id=obs_id,
                    start_time_iso=start_time.isot,
                    mid_time_iso=mid_time.isot,
                    end_time_iso=end_time.isot,
                    num_subbands=len(group),
                    file_paths=group,
                    delta_from_transit_min=delta_min,
                )
            )
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
        output_ms_dir = get_output_ms_dir()
        if output_name:
            ms_path = os.path.join(output_ms_dir, f"{output_name}.ms")
        else:
            ms_path = os.path.join(output_ms_dir, f"{calibrator_name}_{observation_id}.ms")

        # In a real implementation, this would use the execution module
        # For now, we simulate the conversion
        # Import deferred to avoid import-time side effects
        from dsa110_contimg.execution import InProcessExecutor  # noqa: F401

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
        output_images_dir = get_output_images_dir()
        image_path = os.path.join(output_images_dir, f"{ms_basename}.image.fits")

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
    """Check health of calibrator imaging API with configuration details."""
    hdf5_db = get_hdf5_db_path()
    products_db = get_products_db_path()
    calibrators_db = str(get_calibrators_db_path())
    incoming_dir = get_incoming_dir()
    output_ms_dir = get_output_ms_dir()
    output_images_dir = get_output_images_dir()

    # Check each path
    hdf5_exists = os.path.exists(hdf5_db)
    products_exists = os.path.exists(products_db)
    calibrators_exists = os.path.exists(calibrators_db)
    incoming_exists = os.path.exists(incoming_dir)
    ms_dir_exists = os.path.exists(output_ms_dir)
    images_dir_exists = os.path.exists(output_images_dir)

    # Count HDF5 files in incoming
    hdf5_file_count = 0
    if incoming_exists:
        try:
            hdf5_file_count = len([f for f in os.listdir(incoming_dir) if f.endswith(".hdf5")])
        except Exception:
            pass

    # Count MS files in output
    ms_file_count = 0
    if ms_dir_exists:
        try:
            ms_file_count = len([f for f in os.listdir(output_ms_dir) if f.endswith(".ms")])
        except Exception:
            pass

    all_ok = all(
        [hdf5_exists, calibrators_exists, incoming_exists, ms_dir_exists, images_dir_exists]
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "configuration": {
            "hdf5_db": {
                "path": hdf5_db,
                "exists": hdf5_exists,
            },
            "products_db": {
                "path": products_db,
                "exists": products_exists,
            },
            "calibrators_db": {
                "path": calibrators_db,
                "exists": calibrators_exists,
            },
            "incoming_dir": {
                "path": incoming_dir,
                "exists": incoming_exists,
                "hdf5_file_count": hdf5_file_count if incoming_exists else None,
            },
            "output_ms_dir": {
                "path": output_ms_dir,
                "exists": ms_dir_exists,
                "ms_file_count": ms_file_count if ms_dir_exists else None,
            },
            "output_images_dir": {
                "path": output_images_dir,
                "exists": images_dir_exists,
            },
        },
        # Legacy flat fields for backward compatibility
        "hdf5_db_exists": hdf5_exists,
        "calibrators_db_exists": calibrators_exists,
        "incoming_dir_exists": incoming_exists,
        "output_ms_dir_exists": ms_dir_exists,
        "output_images_dir_exists": images_dir_exists,
    }


@router.get("/data-coverage")
async def get_data_coverage():
    """
    Get the time range of indexed HDF5 data.

    Returns the earliest and latest timestamps in the HDF5 index,
    allowing the frontend to query the appropriate time range
    instead of using hardcoded defaults.
    """
    hdf5_db = get_hdf5_db_path()

    if not os.path.exists(hdf5_db):
        raise HTTPException(status_code=503, detail="HDF5 database not available")

    try:
        conn = sqlite3.connect(hdf5_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                MIN(timestamp_iso) as earliest_iso,
                MAX(timestamp_iso) as latest_iso,
                MIN(timestamp_mjd) as earliest_mjd,
                MAX(timestamp_mjd) as latest_mjd,
                COUNT(*) as total_files,
                COUNT(DISTINCT group_id) as total_groups
            FROM hdf5_files
        """)
        row = cursor.fetchone()
        conn.close()

        if not row or not row["earliest_iso"]:
            return {"has_data": False, "message": "No HDF5 files indexed"}

        # Calculate days from now
        from datetime import datetime

        latest = datetime.fromisoformat(row["latest_iso"])
        earliest = datetime.fromisoformat(row["earliest_iso"])
        now = datetime.utcnow()

        days_since_latest = (now - latest).days
        total_days_span = (latest - earliest).days

        return {
            "has_data": True,
            "earliest_time_iso": row["earliest_iso"],
            "latest_time_iso": row["latest_iso"],
            "earliest_mjd": row["earliest_mjd"],
            "latest_mjd": row["latest_mjd"],
            "total_files": row["total_files"],
            "total_groups": row["total_groups"],
            "days_since_latest": days_since_latest,
            "total_days_span": total_days_span,
            "recommended_days_back": max(days_since_latest + 7, 14),
        }
    except Exception as e:
        logger.exception("Failed to query data coverage")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/health/storage")
async def storage_health_check():
    """
    Validate HDF5 database synchronization with filesystem.

    This is a more expensive check that compares the database
    index with actual files on disk.
    """
    from dsa110_contimg.database.storage_validator import (
        get_storage_metrics,
        validate_hdf5_storage,
    )

    hdf5_db = get_hdf5_db_path()
    incoming_dir = get_incoming_dir()

    if not os.path.exists(hdf5_db):
        return {
            "status": "error",
            "message": "HDF5 database not found",
            "db_path": hdf5_db,
        }

    if not os.path.exists(incoming_dir):
        return {
            "status": "error",
            "message": "Incoming directory not found",
            "dir_path": incoming_dir,
        }

    # Get quick metrics first
    metrics = get_storage_metrics(hdf5_db, incoming_dir)

    # Determine if full validation is needed based on count mismatch
    if not metrics["count_matches"]:
        # Run full validation to get details
        validation = validate_hdf5_storage(hdf5_db, incoming_dir)
        return {
            "status": "out_of_sync",
            "message": "Database and filesystem are not synchronized",
            "quick_metrics": metrics,
            "validation": validation.to_dict(),
        }

    return {
        "status": "synchronized",
        "message": "Database matches filesystem",
        "metrics": metrics,
    }


@router.post("/health/storage/reconcile")
async def reconcile_storage_endpoint(
    mark_removed: bool = Query(default=True, description="Mark stale records as removed"),
    dry_run: bool = Query(default=True, description="Dry run (no database changes)"),
):
    """
    Reconcile database with filesystem - mark stale records as removed.

    Stale records are database entries for files that no longer exist on disk.
    This endpoint marks them with stored=0 instead of deleting them.

    Args:
        mark_removed: If True, mark stale records as stored=0
        dry_run: If True, only report what would change (default: True for safety)

    Returns:
        Reconciliation results including counts of stale records found/marked.
    """
    from dsa110_contimg.database.storage_validator import reconcile_storage

    hdf5_db = get_hdf5_db_path()
    incoming_dir = get_incoming_dir()

    if not os.path.exists(hdf5_db):
        return {
            "status": "error",
            "message": "HDF5 database not found",
            "db_path": hdf5_db,
        }

    result = reconcile_storage(
        hdf5_db,
        incoming_dir,
        mark_removed=mark_removed,
        dry_run=dry_run,
    )

    return {
        "status": "success" if not result.get("errors") else "partial",
        "message": f"{'Would mark' if dry_run else 'Marked'} {result.get('stale_records_marked', 0)} stale records",
        **result,
    }


@router.post("/health/storage/index-orphaned")
async def index_orphaned_files_endpoint(
    dry_run: bool = Query(default=True, description="Dry run (no database changes)"),
):
    """
    Index orphaned files - files on disk but not in database.

    Parses HDF5 filenames to extract metadata (timestamp, subband, group_id)
    and inserts records into the hdf5_files table.

    Args:
        dry_run: If True, only report what would be indexed (default: True for safety)

    Returns:
        Indexing results including counts of files parsed and indexed.
    """
    from dsa110_contimg.database.storage_validator import index_orphaned_files

    hdf5_db = get_hdf5_db_path()
    incoming_dir = get_incoming_dir()

    if not os.path.exists(hdf5_db):
        return {
            "status": "error",
            "message": "HDF5 database not found",
            "db_path": hdf5_db,
        }

    result = index_orphaned_files(
        hdf5_db,
        incoming_dir,
        dry_run=dry_run,
    )

    status = "success"
    if result.get("errors"):
        status = "partial"
    if result.get("parse_failed", 0) > result.get("parsed_ok", 0):
        status = "warning"  # Many files couldn't be parsed

    return {
        "status": status,
        "message": f"{'Would index' if dry_run else 'Indexed'} {result.get('indexed', 0)} of {result.get('total_orphaned', 0)} orphaned files",
        **result,
    }


@router.post("/health/storage/full-reconcile")
async def full_reconciliation_endpoint(
    mark_removed: bool = Query(default=True, description="Mark stale records as removed"),
    index_orphaned: bool = Query(default=True, description="Index orphaned files"),
    dry_run: bool = Query(default=True, description="Dry run (no database changes)"),
):
    """
    Perform full database reconciliation with filesystem.

    This combines both operations:
    1. Mark stale records (in DB but not on disk) as removed
    2. Index orphaned files (on disk but not in DB)

    Args:
        mark_removed: If True, mark stale records as stored=0
        index_orphaned: If True, index orphaned files
        dry_run: If True, only report what would change (default: True for safety)

    Returns:
        Full reconciliation results with pre/post sync percentages.
    """
    from dsa110_contimg.database.storage_validator import full_reconciliation

    hdf5_db = get_hdf5_db_path()
    incoming_dir = get_incoming_dir()

    if not os.path.exists(hdf5_db):
        return {
            "status": "error",
            "message": "HDF5 database not found",
            "db_path": hdf5_db,
        }

    result = full_reconciliation(
        hdf5_db,
        incoming_dir,
        mark_removed=mark_removed,
        index_orphaned=index_orphaned,
        dry_run=dry_run,
    )

    errors = result.get("reconciliation", {}).get("errors", []) + result.get("indexing", {}).get(
        "errors", []
    )

    return {
        "status": "success" if not errors else "partial",
        "message": f"Reconciliation {'would bring' if dry_run else 'brought'} sync from {result.get('pre_sync_percentage', 0):.1f}% to {result.get('post_sync_percentage', 0):.1f}%",
        **result,
    }


@router.get("/health/services")
async def services_health_check():
    """
    Check health of dependent services (Docker containers, systemd services).
    """
    from dsa110_contimg.monitoring.service_health import (
        DEFAULT_DOCKER_CONTAINERS,
        DEFAULT_HTTP_ENDPOINTS,
        DEFAULT_SYSTEMD_SERVICES,
        check_system_health,
    )

    report = await check_system_health(
        docker_containers=DEFAULT_DOCKER_CONTAINERS,
        systemd_services=DEFAULT_SYSTEMD_SERVICES,
        http_endpoints=DEFAULT_HTTP_ENDPOINTS,
    )

    return report.to_dict()


# =============================================================================
# Prometheus Metrics Endpoint
# =============================================================================


@router.get("/metrics")
async def prometheus_metrics():
    """
    Export metrics in Prometheus text format.

    Returns metrics for:
    - Storage synchronization (files on disk vs indexed in database)
    - Docker container status
    - Systemd service status

    This endpoint can be scraped by Prometheus at regular intervals.
    """
    from fastapi.responses import PlainTextResponse

    from dsa110_contimg.monitoring.prometheus_metrics import collect_all_metrics

    hdf5_db = get_hdf5_db_path()
    incoming_dir = get_incoming_dir()

    metrics_text = await collect_all_metrics(hdf5_db, incoming_dir)

    return PlainTextResponse(content=metrics_text, media_type="text/plain; charset=utf-8")


# =============================================================================
# Alerts Endpoints
# =============================================================================

# Shared alert manager instance
_alert_manager = None


def get_alert_manager():
    """Get or create the alert manager singleton."""
    global _alert_manager
    if _alert_manager is None:
        from dsa110_contimg.monitoring.alerting import (
            AlertManager,
            create_default_alert_rules,
        )

        # Get paths from config
        hdf5_db = get_hdf5_db_path()
        incoming_dir = get_incoming_dir()
        alert_db = os.path.join(os.path.dirname(hdf5_db), "alerts.sqlite3")

        # Get notification URLs from env
        slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        generic_webhook = os.getenv("ALERT_WEBHOOK_URL")

        _alert_manager = AlertManager(
            db_path=alert_db,
            webhook_url=generic_webhook,
            slack_webhook=slack_webhook,
        )

        # Register default rules
        rules = create_default_alert_rules(hdf5_db, incoming_dir)
        for rule in rules:
            _alert_manager.register_rule(rule)

    return _alert_manager


@router.get("/alerts/active")
async def get_active_alerts():
    """
    Get currently active (firing) alerts.
    """
    manager = get_alert_manager()

    # Evaluate rules to update state
    new_alerts = manager.evaluate_rules()

    # Send notifications for any new alerts
    if new_alerts:
        await manager.send_notifications(new_alerts)

    active = manager.get_active_alerts()
    return {
        "active_alerts": [a.to_dict() for a in active],
        "count": len(active),
    }


@router.get("/alerts/history")
async def get_alert_history(
    limit: int = Query(
        default=100, ge=1, le=1000, description="Maximum number of alerts to return"
    ),
    rule_name: Optional[str] = Query(default=None, description="Filter by rule name"),
):
    """
    Get alert history from the database.
    """
    manager = get_alert_manager()
    history = manager.get_alert_history(limit=limit, rule_name=rule_name)
    return {
        "alerts": history,
        "count": len(history),
    }


@router.post("/alerts/evaluate")
async def evaluate_alerts():
    """
    Manually trigger alert rule evaluation.

    This is useful for testing or forcing an immediate check.
    Returns any new or changed alerts.
    """
    manager = get_alert_manager()

    # Evaluate all rules
    alerts = manager.evaluate_rules()

    # Send notifications
    if alerts:
        await manager.send_notifications(alerts)

    return {
        "evaluated": True,
        "new_or_changed_alerts": [a.to_dict() for a in alerts],
        "total_active": len(manager.get_active_alerts()),
    }


# =============================================================================
# Precomputation and Pointing Tracker Endpoints
# =============================================================================


@router.get("/pointing/status")
async def get_pointing_status():
    """
    Get current pointing tracker status.

    Returns:
        - Current telescope declination
        - Recent pointing changes
        - Cached transit predictions
        - Pending catalog builds
    """
    try:
        from dsa110_contimg.pipeline.precompute import get_pointing_tracker

        tracker = get_pointing_tracker()
        return tracker.get_status()
    except ImportError:
        return {
            "error": "Precompute module not available",
            "current_dec_deg": None,
        }


@router.get("/pointing/transits")
async def get_upcoming_transits_for_dec(
    dec_deg: Optional[float] = Query(
        default=None, description="Target declination (default: current pointing)"
    ),
    hours_ahead: float = Query(default=24.0, ge=1.0, le=168.0, description="Hours ahead to search"),
):
    """
    Get upcoming calibrator transits for a declination.

    This uses the precomputation cache if available.
    """
    try:
        from dsa110_contimg.pipeline.precompute import get_pointing_tracker

        tracker = get_pointing_tracker()

        # Get cached transits
        transits = tracker.get_cached_transits(dec_deg)

        return {
            "target_dec_deg": dec_deg or tracker.current_dec,
            "transits": [t.to_dict() for t in transits],
            "count": len(transits),
        }
    except ImportError:
        # Fallback to standard transit calculation
        from dsa110_contimg.pointing.monitor import get_all_upcoming_transits

        transits = get_all_upcoming_transits(hours_ahead=hours_ahead)
        return {
            "target_dec_deg": dec_deg,
            "transits": [t.to_dict() for t in transits],
            "count": len(transits),
        }


@router.get("/pointing/best-calibrator")
async def get_best_calibrator_for_dec(
    dec_deg: Optional[float] = Query(
        default=None, description="Target declination (default: current pointing)"
    ),
):
    """
    Get the best calibrator for the given or current declination.

    Returns the calibrator with the closest declination and soonest transit.
    """
    try:
        from dsa110_contimg.pipeline.precompute import get_pointing_tracker

        tracker = get_pointing_tracker()

        calibrator = tracker.get_best_calibrator(dec_deg)

        if calibrator is None:
            return {
                "target_dec_deg": dec_deg or tracker.current_dec,
                "calibrator": None,
                "message": "No suitable calibrator found",
            }

        return {
            "target_dec_deg": dec_deg or tracker.current_dec,
            "calibrator": calibrator.to_dict(),
        }
    except ImportError:
        return {
            "error": "Precompute module not available",
            "calibrator": None,
        }


@router.post("/pointing/precompute-transits")
async def precompute_all_transits_endpoint(
    hours_ahead: float = Query(
        default=48.0, ge=1.0, le=168.0, description="Hours ahead to precompute"
    ),
):
    """
    Precompute all calibrator transits for the next N hours.

    This warms the transit cache for faster lookup.
    """
    try:
        from dsa110_contimg.pipeline.precompute import precompute_all_transits

        predictions = await precompute_all_transits(hours_ahead=hours_ahead)

        total = sum(len(v) for v in predictions.values())
        return {
            "precomputed": True,
            "hours_ahead": hours_ahead,
            "calibrator_count": len(predictions),
            "total_transits": total,
            "by_calibrator": {k: len(v) for k, v in predictions.items()},
        }
    except ImportError:
        return {
            "error": "Precompute module not available",
            "precomputed": False,
        }


@router.post("/pointing/ensure-catalogs")
async def ensure_catalogs_for_dec_endpoint(
    dec_deg: float = Query(..., description="Target declination"),
    catalog_types: Optional[str] = Query(
        default=None, description="Comma-separated catalog types (default: nvss,first,vlass)"
    ),
    wait: bool = Query(default=False, description="Wait for builds to complete (can be slow)"),
):
    """
    Ensure catalog databases exist for a declination.

    Triggers background builds for missing catalogs.

    Args:
        dec_deg: Target declination
        catalog_types: Comma-separated list (e.g., "nvss,first")
        wait: If True, wait for builds (may take several minutes)
    """
    try:
        from dsa110_contimg.pipeline.precompute import ensure_catalogs_for_dec

        types = None
        if catalog_types:
            types = [t.strip() for t in catalog_types.split(",")]

        results = ensure_catalogs_for_dec(
            dec_deg=dec_deg,
            catalog_types=types,
            wait=wait,
        )

        return {
            "dec_deg": dec_deg,
            "catalogs": {k: str(v) if v else None for k, v in results.items()},
            "waited": wait,
        }
    except ImportError:
        return {
            "error": "Precompute module not available",
            "catalogs": {},
        }
