"""Pydantic models used by the monitoring API."""

from __future__ import annotations

from datetime import datetime as dt
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Re-export datetime for backward compatibility in type annotations
datetime = dt


class QueueGroup(BaseModel):
    group_id: str = Field(..., description="Normalized observation timestamp")
    state: str = Field(
        ..., description="Queue state (collecting|pending|in_progress|completed|failed)"
    )
    received_at: datetime
    last_update: datetime
    subbands_present: int = Field(
        ..., description="Number of subbands ingested for this group"
    )
    expected_subbands: int = Field(...,
                                   description="Expected subbands per group")
    has_calibrator: bool | None = Field(
        None, description="True if any calibrator was matched in beam"
    )
    matches: list[CalibratorMatch] | None = Field(
        None, description="Top matched calibrators for this group"
    )


class QueueStats(BaseModel):
    total: int
    pending: int
    in_progress: int
    failed: int
    completed: int
    collecting: int


class CalibrationSet(BaseModel):
    set_name: str
    tables: List[str]
    active: int = Field(..., description="Number of active tables")
    total: int = Field(..., description="Total tables registered for the set")


class PipelineStatus(BaseModel):
    queue: QueueStats
    recent_groups: List[QueueGroup]
    calibration_sets: List[CalibrationSet]
    matched_recent: int = Field(
        0, description="Number of recent groups with calibrator matches"
    )


class ProductEntry(BaseModel):
    id: int
    path: str
    ms_path: str
    created_at: datetime
    type: str
    beam_major_arcsec: Optional[float] = None
    noise_jy: Optional[float] = None
    pbcor: bool = Field(False, description="Primary-beam corrected")


class ProductList(BaseModel):
    items: List[ProductEntry]


class ImageInfo(BaseModel):
    """Detailed image information for SkyView."""

    id: int
    path: str
    ms_path: str
    created_at: Optional[datetime] = None
    type: str = Field(...,
                      description="Image type: image, pbcor, residual, psf, pb")
    beam_major_arcsec: Optional[float] = None
    beam_minor_arcsec: Optional[float] = None
    beam_pa_deg: Optional[float] = None
    noise_jy: Optional[float] = None
    peak_flux_jy: Optional[float] = None
    pbcor: bool = Field(False, description="Primary-beam corrected")
    center_ra_deg: Optional[float] = None
    center_dec_deg: Optional[float] = None
    image_size_deg: Optional[float] = None
    pixel_size_arcsec: Optional[float] = None


class ImageList(BaseModel):
    """List of images with pagination."""

    items: List[ImageInfo]
    total: int


class CalibratorMatch(BaseModel):
    name: str
    ra_deg: float
    dec_deg: float
    sep_deg: float
    weighted_flux: float | None = None


class CalibratorMatchGroup(BaseModel):
    group_id: str
    matched: bool = Field(..., description="True if any calibrator matched")
    matches: List[CalibratorMatch]
    received_at: datetime
    last_update: datetime


class CalibratorMatchList(BaseModel):
    items: List[CalibratorMatchGroup]


class QAArtifact(BaseModel):
    group_id: str
    name: str
    path: str
    created_at: datetime | None = None


class QAList(BaseModel):
    items: List[QAArtifact]


class GroupDetail(BaseModel):
    group_id: str
    state: str
    received_at: datetime
    last_update: datetime
    subbands_present: int
    expected_subbands: int
    has_calibrator: bool | None = None
    matches: list[CalibratorMatch] | None = None
    qa: list[QAArtifact] = Field(default_factory=list)
    perf_total_time: float | None = None
    writer_type: str | None = None


class DiskInfo(BaseModel):
    """Disk usage information for a specific mount point."""

    mount_point: str = Field(...,
                             description="Mount point path (e.g., '/stage/', '/data/')")
    total: int = Field(..., description="Total disk space in bytes")
    used: int = Field(..., description="Used disk space in bytes")
    free: int = Field(..., description="Free disk space in bytes")
    percent: float = Field(..., description="Disk usage percentage")


class SystemMetrics(BaseModel):
    ts: datetime
    cpu_percent: float | None = None
    mem_percent: float | None = None
    mem_total: int | None = None
    mem_used: int | None = None
    disk_total: int | None = None  # Deprecated: kept for backward compatibility
    disk_used: int | None = None  # Deprecated: kept for backward compatibility
    disks: List[DiskInfo] = Field(
        default_factory=list, description="Disk usage information for multiple mount points"
    )
    load_1: float | None = None
    load_5: float | None = None
    load_15: float | None = None


class MsIndexEntry(BaseModel):
    path: str
    start_mjd: float | None = None
    end_mjd: float | None = None
    mid_mjd: float | None = None
    processed_at: datetime | None = None
    status: str | None = None
    stage: str | None = None
    stage_updated_at: datetime | None = None
    cal_applied: int | None = None
    imagename: str | None = None


class MsIndexList(BaseModel):
    items: List[MsIndexEntry]


class PointingHistoryEntry(BaseModel):
    timestamp: float
    ra_deg: float
    dec_deg: float


class PointingHistoryList(BaseModel):
    items: List[PointingHistoryEntry]


class TimelineSegment(BaseModel):
    """A time segment where observation data exists on disk."""

    start_time: datetime = Field(..., description="Start time of the segment")
    end_time: datetime = Field(..., description="End time of the segment")
    file_count: int = Field(...,
                            description="Number of HDF5 files in this segment")


class ObservationTimeline(BaseModel):
    """Timeline of observations from HDF5 files on disk."""

    earliest_time: datetime | None = Field(
        None, description="Earliest observation timestamp found"
    )
    latest_time: datetime | None = Field(
        None, description="Latest observation timestamp found"
    )
    total_files: int = Field(0, description="Total number of HDF5 files found")
    unique_timestamps: int = Field(
        0, description="Number of unique observation timestamps"
    )
    segments: List[TimelineSegment] = Field(
        default_factory=list,
        description="Time segments where data exists (grouped by proximity)",
    )


# Control panel job models
class JobParams(BaseModel):
    field: Optional[str] = None
    refant: Optional[str] = None
    gaintables: Optional[List[str]] = None
    gridder: str = "wproject"
    wprojplanes: int = -1
    datacolumn: str = "corrected"
    quality_tier: str = "standard"
    skip_fits: bool = True
    use_nvss_mask: bool = True
    mask_radius_arcsec: float = 60.0


class CalibrateJobParams(BaseModel):
    """Enhanced calibration job parameters with flexible cal table selection."""

    field: Optional[str] = None
    refant: str = "103"

    # Cal table selection
    # K-cal (disabled by default for DSA-110, use --do-k to enable)
    solve_delay: bool = False
    solve_bandpass: bool = True  # BP-cal
    solve_gains: bool = True  # G-cal

    # Advanced options
    delay_solint: str = "inf"
    bandpass_solint: str = "inf"
    gain_solint: str = "inf"
    # "ap" (amp+phase), "p" (phase-only), "a" (amp-only)
    gain_calmode: str = "ap"

    # Field selection
    auto_fields: bool = True
    manual_fields: Optional[List[int]] = None

    # Catalog matching
    cal_catalog: str = "vla"
    search_radius_deg: float = 1.0
    min_pb: float = 0.5

    # Flagging
    do_flagging: bool = False

    # Existing table handling
    use_existing_tables: str = "auto"  # "auto", "manual", "none"
    existing_k_table: Optional[str] = None
    existing_bp_table: Optional[str] = None
    existing_g_table: Optional[str] = None


class Job(BaseModel):
    id: int
    type: str
    status: str
    ms_path: str
    params: JobParams
    logs: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list)
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class JobList(BaseModel):
    items: List[Job]


class JobCreateRequest(BaseModel):
    ms_path: str
    params: JobParams


class MSListEntry(BaseModel):
    path: str
    mid_mjd: Optional[float] = None
    status: Optional[str] = None
    cal_applied: Optional[int] = None
    # Enhanced status fields
    has_calibrator: bool = False
    calibrator_name: Optional[str] = None
    calibrator_quality: Optional[str] = None  # excellent, good, marginal, poor
    is_calibrated: bool = False
    is_imaged: bool = False
    calibration_quality: Optional[str] = None
    image_quality: Optional[str] = None
    size_gb: Optional[float] = None
    start_time: Optional[str] = None


class MSList(BaseModel):
    items: List[MSListEntry]
    total: int = 0
    filtered: int = 0


class MSListFilters(BaseModel):
    """Filters for MS list query."""

    search: Optional[str] = None  # Search in path or calibrator name
    has_calibrator: Optional[bool] = None
    is_calibrated: Optional[bool] = None
    is_imaged: Optional[bool] = None
    calibrator_quality: Optional[str] = None  # excellent, good, marginal, poor
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD
    # time_asc, time_desc, name_asc, name_desc, size_asc, size_desc
    sort_by: str = "time_desc"
    limit: int = 100
    offset: int = 0


# UVH5 file discovery models
class UVH5FileEntry(BaseModel):
    path: str
    timestamp: Optional[str] = None
    subband: Optional[str] = None
    size_mb: Optional[float] = None


class UVH5FileList(BaseModel):
    items: List[UVH5FileEntry]


# Conversion job models
class ConversionJobParams(BaseModel):
    """Parameters for UVH5 → MS conversion job.

    Production processing always uses 16 subbands and should use 'parallel-subband' writer.
    The 'pyuvdata' writer is available for testing scenarios with ≤2 subbands only.
    """

    input_dir: str
    output_dir: str
    start_time: str
    end_time: str
    # 'parallel-subband' (production), 'pyuvdata' (testing only), or 'auto'
    writer: str = "auto"
    stage_to_tmpfs: bool = True
    max_workers: int = 4


class ConversionJobCreateRequest(BaseModel):
    params: ConversionJobParams


# Calibration table models
class CalTableInfo(BaseModel):
    path: str
    filename: str
    table_type: str  # K, BP, G, etc.
    size_mb: float
    modified_time: datetime


class CalTableList(BaseModel):
    items: List[CalTableInfo]


# Existing cal table discovery for an MS
class ExistingCalTable(BaseModel):
    path: str
    filename: str
    size_mb: float
    modified_time: datetime
    age_hours: float


class ExistingCalTables(BaseModel):
    ms_path: str
    k_tables: List[ExistingCalTable] = []
    bp_tables: List[ExistingCalTable] = []
    g_tables: List[ExistingCalTable] = []
    has_k: bool = False
    has_bp: bool = False
    has_g: bool = False


class CalTableCompatibility(BaseModel):
    """Compatibility check result for a calibration table."""

    is_compatible: bool
    caltable_path: str
    ms_path: str
    issues: List[str] = []
    warnings: List[str] = []
    ms_antennas: List[int] = []
    caltable_antennas: List[int] = []
    ms_freq_min_ghz: Optional[float] = None
    ms_freq_max_ghz: Optional[float] = None
    caltable_freq_min_ghz: Optional[float] = None
    caltable_freq_max_ghz: Optional[float] = None


# MS metadata models
class FieldInfo(BaseModel):
    """Field information with coordinates."""

    field_id: int
    name: str
    ra_deg: float
    dec_deg: float


class AntennaInfo(BaseModel):
    """Antenna information."""

    antenna_id: int
    name: str


class FlaggingStats(BaseModel):
    """Flagging statistics for an MS."""

    total_fraction: float  # Overall fraction flagged
    # Antenna ID -> fraction flagged
    per_antenna: Optional[Dict[str, float]] = None
    # Field ID -> fraction flagged
    per_field: Optional[Dict[str, float]] = None


class MSMetadata(BaseModel):
    path: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_sec: Optional[float] = None
    num_fields: Optional[int] = None
    field_names: Optional[List[str]] = None
    fields: Optional[List[FieldInfo]] = None  # Enhanced: includes RA/Dec
    freq_min_ghz: Optional[float] = None
    freq_max_ghz: Optional[float] = None
    num_channels: Optional[int] = None
    num_antennas: Optional[int] = None
    antennas: Optional[List[AntennaInfo]] = None  # Enhanced: antenna list
    data_columns: List[str] = []
    size_gb: Optional[float] = None
    calibrated: bool = False
    # Enhanced: flagging statistics
    flagging_stats: Optional[FlaggingStats] = None


# MS Calibrator match models
class MSCalibratorMatch(BaseModel):
    """Calibrator match for a specific MS."""

    name: str
    ra_deg: float
    dec_deg: float
    flux_jy: float
    sep_deg: float
    pb_response: float
    weighted_flux: float
    quality: str  # "excellent", "good", "marginal", "poor"
    recommended_fields: Optional[List[int]] = None


class MSCalibratorMatchList(BaseModel):
    """List of calibrator matches for an MS."""

    ms_path: str
    pointing_dec: float
    mid_mjd: Optional[float] = None
    matches: List[MSCalibratorMatch]
    has_calibrator: bool = False


# Workflow models
class WorkflowParams(BaseModel):
    """Parameters for full workflow job (convert → calibrate → image).

    Production processing always uses 16 subbands and should use 'parallel-subband' writer.
    The 'pyuvdata' writer is available for testing scenarios with ≤2 subbands only.
    """

    start_time: str
    end_time: str
    input_dir: str = "/data/incoming"
    output_dir: str = "/stage/dsa110-contimg/ms"
    # 'parallel-subband' (production), 'pyuvdata' (testing only), or 'auto'
    writer: str = "auto"
    stage_to_tmpfs: bool = True
    max_workers: int = 4
    field: Optional[str] = None
    refant: Optional[str] = "103"
    gridder: str = "wproject"
    wprojplanes: int = -1


class WorkflowJobCreateRequest(BaseModel):
    params: WorkflowParams


# ============================================================================
# Batch Job Models
# ============================================================================


class BatchJobStatus(BaseModel):
    """Status of a single job within a batch."""

    ms_path: str
    job_id: Optional[int] = None
    status: str = "pending"  # pending, running, done, failed, cancelled
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class BatchJob(BaseModel):
    """A batch job that processes multiple MS files."""

    id: int
    type: str  # batch_calibrate, batch_apply, batch_image
    created_at: datetime
    status: str  # pending, running, done, failed, cancelled
    total_items: int
    completed_items: int = 0
    failed_items: int = 0
    params: dict  # Shared parameters for all items
    items: List[BatchJobStatus]


class BatchJobList(BaseModel):
    items: List[BatchJob]


class BatchCalibrateParams(BaseModel):
    """Parameters for batch calibration."""

    ms_paths: List[str]
    params: CalibrateJobParams


class BatchApplyParams(BaseModel):
    """Parameters for batch apply."""

    ms_paths: List[str]
    params: JobParams


class BatchImageParams(BaseModel):
    """Parameters for batch imaging."""

    ms_paths: List[str]
    params: JobParams


class BatchJobCreateRequest(BaseModel):
    """Request to create a batch job."""

    job_type: str  # calibrate, apply, image
    params: Union[BatchCalibrateParams, BatchApplyParams, BatchImageParams]


# ============================================================================
# Quality Assessment Models
# ============================================================================


class PerSPWStats(BaseModel):
    """Per-spectral-window flagging statistics."""

    spw_id: int
    total_solutions: int
    flagged_solutions: int
    fraction_flagged: float
    n_channels: int
    channels_with_high_flagging: int
    avg_flagged_per_channel: float
    max_flagged_in_channel: int
    is_problematic: bool


class CalibrationQA(BaseModel):
    """Quality assessment metrics for calibration."""

    ms_path: str
    job_id: int
    k_metrics: Optional[dict] = None  # SNR, flagged fraction, etc.
    bp_metrics: Optional[dict] = None
    g_metrics: Optional[dict] = None
    overall_quality: str = "unknown"  # excellent, good, marginal, poor, unknown
    flags_total: Optional[float] = None  # Fraction of flagged solutions
    # Per-SPW flagging statistics
    per_spw_stats: Optional[List[PerSPWStats]] = None
    timestamp: datetime = Field(default_factory=dt.utcnow)


class ImageQA(BaseModel):
    """Quality assessment metrics for images."""

    ms_path: str
    job_id: int
    image_path: str
    rms_noise: Optional[float] = None  # Jy/beam
    peak_flux: Optional[float] = None  # Jy/beam
    dynamic_range: Optional[float] = None
    beam_major: Optional[float] = None  # arcsec
    beam_minor: Optional[float] = None  # arcsec
    beam_pa: Optional[float] = None  # degrees
    num_sources: Optional[int] = None
    thumbnail_path: Optional[str] = None
    overall_quality: str = "unknown"  # excellent, good, marginal, poor, unknown
    timestamp: datetime = Field(default_factory=dt.utcnow)


class QAMetrics(BaseModel):
    """Combined QA metrics for an MS."""

    ms_path: str
    calibration_qa: Optional[CalibrationQA] = None
    image_qa: Optional[ImageQA] = None


# Enhanced dashboard feature models


class ESECandidate(BaseModel):
    """ESE (Extreme Scattering Event) candidate source."""

    id: Optional[int] = None
    source_id: str
    ra_deg: float
    dec_deg: float
    first_detection_at: str  # ISO format datetime
    last_detection_at: str  # ISO format datetime
    max_sigma_dev: float
    current_flux_jy: float
    baseline_flux_jy: float
    status: str = Field(..., description="active, investigated, dismissed")
    notes: Optional[str] = None


class ESECandidatesResponse(BaseModel):
    """Response for ESE candidates endpoint."""

    candidates: List[ESECandidate]
    total: int


class Mosaic(BaseModel):
    """Mosaic image metadata."""

    id: Optional[int] = None
    name: str
    path: str
    start_mjd: float
    end_mjd: float
    start_time: str  # ISO format datetime
    end_time: str  # ISO format datetime
    created_at: str  # ISO format datetime
    status: str = Field(...,
                        description="pending, in_progress, completed, failed")
    image_count: Optional[int] = None
    noise_jy: Optional[float] = None
    source_count: Optional[int] = None
    thumbnail_path: Optional[str] = None


class MosaicQueryResponse(BaseModel):
    """Response for mosaic query endpoint."""

    mosaics: List[Mosaic]
    total: int


class SourceFluxPoint(BaseModel):
    """Single flux measurement point."""

    mjd: float
    time: str  # ISO format datetime
    flux_jy: float
    flux_err_jy: Optional[float] = None
    image_id: Optional[str] = None


class SourceTimeseries(BaseModel):
    """Source flux timeseries with variability statistics."""

    source_id: str
    ra_deg: float
    dec_deg: float
    catalog: str = "NVSS"
    flux_points: List[SourceFluxPoint]
    mean_flux_jy: float
    std_flux_jy: float
    chi_sq_nu: float
    is_variable: bool


class SourceSearchResponse(BaseModel):
    """Response for source search endpoint."""

    sources: List[SourceTimeseries]
    total: int


class VariabilityMetrics(BaseModel):
    """Variability metrics for a source."""
    source_id: str
    v: float = Field(..., description="Coefficient of variation (std/mean)")
    eta: float = Field(..., description="Weighted variance metric (η)")
    vs_mean: Optional[float] = Field(
        None, description="Mean two-epoch t-statistic")
    m_mean: Optional[float] = Field(None, description="Mean modulation index")
    n_epochs: int = Field(..., description="Number of epochs")


class LightCurveData(BaseModel):
    """Light curve data for a source."""
    source_id: str
    ra_deg: float
    dec_deg: float
    flux_points: List[SourceFluxPoint]
    normalized_flux_points: Optional[List[SourceFluxPoint]] = None


class PostageStampInfo(BaseModel):
    """Postage stamp image information."""
    image_path: str
    mjd: float
    cutout_path: Optional[str] = None
    error: Optional[str] = None


class PostageStampsResponse(BaseModel):
    """Response for postage stamps endpoint."""
    source_id: str
    ra_deg: float
    dec_deg: float
    stamps: List[PostageStampInfo]
    total: int


class ExternalCatalogMatch(BaseModel):
    """External catalog match result."""
    catalog: str = Field(..., description="Catalog name (simbad, ned, gaia)")
    matched: bool = Field(..., description="Whether a match was found")
    main_id: Optional[str] = Field(None, description="Primary identifier")
    object_type: Optional[str] = Field(
        None, description="Object type/classification")
    separation_arcsec: Optional[float] = Field(
        None, description="Separation from query position")
    redshift: Optional[float] = Field(None, description="Redshift (NED)")
    parallax: Optional[float] = Field(
        None, description="Parallax in mas (Gaia)")
    distance: Optional[float] = Field(
        None, description="Distance in pc (Gaia)")
    pmra: Optional[float] = Field(
        None, description="Proper motion RA (mas/yr, Gaia)")
    pmdec: Optional[float] = Field(
        None, description="Proper motion Dec (mas/yr, Gaia)")
    phot_g_mean_mag: Optional[float] = Field(
        None, description="G-band magnitude (Gaia)")
    error: Optional[str] = Field(
        None, description="Error message if query failed")


class ExternalCatalogsResponse(BaseModel):
    """Response for external catalogs endpoint."""
    source_id: str
    ra_deg: float
    dec_deg: float
    matches: Dict[str, ExternalCatalogMatch]
    query_time_sec: Optional[float] = Field(
        None, description="Total query time")


class AlertHistory(BaseModel):
    """Alert history entry."""

    id: int
    source_id: str
    alert_type: str = Field(
        ..., description="ese_candidate, calibrator_missing, system_error"
    )
    severity: str = Field(..., description="info, warning, critical")
    message: str
    triggered_at: str  # ISO format datetime
    resolved_at: Optional[str] = None  # ISO format datetime


# Source Detail Models
class Detection(BaseModel):
    """Single detection/measurement for a source."""
    id: Optional[int] = None
    name: Optional[str] = None
    image_id: Optional[int] = None
    image_path: Optional[str] = None
    ra: float = Field(..., description="Right ascension in degrees")
    dec: float = Field(..., description="Declination in degrees")
    flux_peak: float = Field(..., description="Peak flux in mJy/beam")
    flux_peak_err: Optional[float] = Field(
        None, description="Peak flux error in mJy/beam")
    flux_int: Optional[float] = Field(
        None, description="Integrated flux in mJy")
    flux_int_err: Optional[float] = Field(
        None, description="Integrated flux error in mJy")
    snr: Optional[float] = Field(None, description="Signal-to-noise ratio")
    forced: bool = Field(
        False, description="Whether this is a forced measurement")
    frequency: Optional[float] = Field(None, description="Frequency in MHz")
    mjd: Optional[float] = Field(None, description="Modified Julian Date")
    measured_at: Optional[datetime] = None


class DetectionList(BaseModel):
    """Paginated list of detections."""
    items: List[Detection]
    total: int
    page: int = 1
    page_size: int = 25


class SourceDetail(BaseModel):
    """Detailed source information."""
    id: str = Field(..., description="Source ID")
    name: Optional[str] = None
    ra_deg: float = Field(..., description="Right ascension in degrees")
    dec_deg: float = Field(..., description="Declination in degrees")
    catalog: str = Field("NVSS", description="Catalog name")
    n_meas: int = Field(0, description="Number of measurements")
    n_meas_forced: int = Field(0, description="Number of forced measurements")
    mean_flux_jy: Optional[float] = Field(None, description="Mean flux in Jy")
    std_flux_jy: Optional[float] = Field(
        None, description="Standard deviation of flux in Jy")
    max_snr: Optional[float] = Field(None, description="Maximum SNR")
    is_variable: bool = Field(False, description="Whether source is variable")
    ese_probability: Optional[float] = Field(
        None, description="ESE candidate probability")
    new_source: bool = Field(False, description="Whether this is a new source")
    variability_metrics: Optional[VariabilityMetrics] = None


# Image Detail Models
class Measurement(BaseModel):
    """Single measurement/detection in an image."""
    id: Optional[int] = None
    name: Optional[str] = None
    source_id: Optional[str] = None
    ra: float = Field(..., description="Right ascension in degrees")
    dec: float = Field(..., description="Declination in degrees")
    flux_peak: float = Field(..., description="Peak flux in mJy/beam")
    flux_peak_err: Optional[float] = Field(
        None, description="Peak flux error in mJy/beam")
    flux_int: Optional[float] = Field(
        None, description="Integrated flux in mJy")
    flux_int_err: Optional[float] = Field(
        None, description="Integrated flux error in mJy")
    snr: Optional[float] = Field(None, description="Signal-to-noise ratio")
    forced: bool = Field(
        False, description="Whether this is a forced measurement")
    frequency: Optional[float] = Field(None, description="Frequency in MHz")
    compactness: Optional[float] = Field(
        None, description="Source compactness")
    has_siblings: bool = Field(
        False, description="Whether source has siblings")


class MeasurementList(BaseModel):
    """Paginated list of measurements."""
    items: List[Measurement]
    total: int
    page: int = 1
    page_size: int = 25


class ImageDetail(BaseModel):
    """Detailed image information."""
    id: int
    name: Optional[str] = None
    path: str
    ms_path: Optional[str] = None
    ra: Optional[float] = Field(None, description="Right ascension in degrees")
    dec: Optional[float] = Field(None, description="Declination in degrees")
    ra_hms: Optional[str] = None
    dec_dms: Optional[str] = None
    l: Optional[float] = Field(
        None, description="Galactic longitude in degrees")
    b: Optional[float] = Field(
        None, description="Galactic latitude in degrees")
    beam_bmaj: Optional[float] = Field(
        None, description="Beam major axis in degrees")
    beam_bmin: Optional[float] = Field(
        None, description="Beam minor axis in degrees")
    beam_bpa: Optional[float] = Field(
        None, description="Beam position angle in degrees")
    rms_median: Optional[float] = Field(None, description="Median RMS in mJy")
    rms_min: Optional[float] = Field(None, description="Minimum RMS in mJy")
    rms_max: Optional[float] = Field(None, description="Maximum RMS in mJy")
    frequency: Optional[float] = Field(None, description="Frequency in MHz")
    bandwidth: Optional[float] = Field(None, description="Bandwidth in MHz")
    datetime: Optional[dt] = None  # Use dt alias to avoid shadowing
    created_at: Optional[dt] = None  # Use dt alias to avoid shadowing
    n_meas: int = Field(0, description="Number of measurements")
    n_runs: int = Field(0, description="Number of runs")
    type: str = Field(..., description="Image type")
    pbcor: bool = Field(False, description="Primary-beam corrected")


# Streaming Service Models
class StreamingConfigRequest(BaseModel):
    """Request model for streaming service configuration."""

    input_dir: str
    output_dir: str
    queue_db: Optional[str] = None
    registry_db: Optional[str] = None
    scratch_dir: Optional[str] = None
    expected_subbands: int = 16
    chunk_duration: float = 5.0  # minutes
    log_level: str = "INFO"
    use_subprocess: bool = True
    monitoring: bool = True
    monitor_interval: float = 60.0
    poll_interval: float = 5.0
    worker_poll_interval: float = 5.0
    max_workers: int = 4
    stage_to_tmpfs: bool = False
    tmpfs_path: str = "/dev/shm"


class StreamingStatusResponse(BaseModel):
    """Response model for streaming service status."""

    running: bool
    pid: Optional[int] = None
    started_at: Optional[str] = None  # ISO format
    uptime_seconds: Optional[float] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    last_heartbeat: Optional[str] = None  # ISO format
    config: Optional[dict] = None
    error: Optional[str] = None


class StreamingHealthResponse(BaseModel):
    """Response model for streaming service health check."""

    healthy: bool
    running: bool
    uptime_seconds: Optional[float] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    error: Optional[str] = None


class StreamingControlResponse(BaseModel):
    """Response model for streaming service control operations."""

    success: bool
    message: str
    pid: Optional[int] = None
