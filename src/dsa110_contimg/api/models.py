"""Pydantic models used by the monitoring API."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union, Dict

from pydantic import BaseModel, Field


class QueueGroup(BaseModel):
    group_id: str = Field(..., description="Normalized observation timestamp")
    state: str = Field(..., description="Queue state (collecting|pending|in_progress|completed|failed)")
    received_at: datetime
    last_update: datetime
    subbands_present: int = Field(..., description="Number of subbands ingested for this group")
    expected_subbands: int = Field(..., description="Expected subbands per group")
    has_calibrator: bool | None = Field(None, description="True if any calibrator was matched in beam")
    matches: list[CalibratorMatch] | None = Field(None, description="Top matched calibrators for this group")


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
    matched_recent: int = Field(0, description="Number of recent groups with calibrator matches")


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


class SystemMetrics(BaseModel):
    ts: datetime
    cpu_percent: float | None = None
    mem_percent: float | None = None
    mem_total: int | None = None
    mem_used: int | None = None
    disk_total: int | None = None
    disk_used: int | None = None
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


# Control panel job models
class JobParams(BaseModel):
    field: Optional[str] = None
    refant: Optional[str] = None
    gaintables: Optional[List[str]] = None
    gridder: str = "wproject"
    wprojplanes: int = -1
    datacolumn: str = "corrected"
    quick: bool = False
    skip_fits: bool = True


class CalibrateJobParams(BaseModel):
    """Enhanced calibration job parameters with flexible cal table selection."""
    field: Optional[str] = None
    refant: str = "103"
    
    # Cal table selection
    solve_delay: bool = True  # K-cal
    solve_bandpass: bool = True  # BP-cal
    solve_gains: bool = True  # G-cal
    
    # Advanced options
    delay_solint: str = "inf"
    bandpass_solint: str = "inf"
    gain_solint: str = "inf"
    gain_calmode: str = "ap"  # "ap" (amp+phase), "p" (phase-only), "a" (amp-only)
    
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
    sort_by: str = "time_desc"  # time_asc, time_desc, name_asc, name_desc, size_asc, size_desc
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
    input_dir: str
    output_dir: str
    start_time: str
    end_time: str
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
    per_antenna: Optional[Dict[str, float]] = None  # Antenna ID -> fraction flagged
    per_field: Optional[Dict[str, float]] = None  # Field ID -> fraction flagged


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
    flagging_stats: Optional[FlaggingStats] = None  # Enhanced: flagging statistics


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
    start_time: str
    end_time: str
    input_dir: str = "/data/incoming"
    output_dir: str = "/scratch/dsa110-contimg/ms"
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

class CalibrationQA(BaseModel):
    """Quality assessment metrics for calibration."""
    ms_path: str
    job_id: int
    k_metrics: Optional[dict] = None  # SNR, flagged fraction, etc.
    bp_metrics: Optional[dict] = None
    g_metrics: Optional[dict] = None
    overall_quality: str = "unknown"  # excellent, good, marginal, poor, unknown
    flags_total: Optional[float] = None  # Fraction of flagged solutions
    timestamp: datetime = Field(default_factory=datetime.utcnow)


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
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QAMetrics(BaseModel):
    """Combined QA metrics for an MS."""
    ms_path: str
    calibration_qa: Optional[CalibrationQA] = None
    image_qa: Optional[ImageQA] = None
