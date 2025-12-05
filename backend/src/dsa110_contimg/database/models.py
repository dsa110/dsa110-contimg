"""
SQLAlchemy ORM models for DSA-110 Continuum Imaging Pipeline database.

This module defines ORM models for the unified pipeline database (pipeline.sqlite3).
All domains are consolidated into a single database with logical table groups:

- Products domain: MS registry (ms_index), images, photometry, transients
- Calibration domain: Calibration table registry (caltables)
- HDF5 domain: HDF5 file index (hdf5_file_index)
- Queue domain: Streaming queue management (processing_queue, performance_metrics)
- Data registry domain: Data staging and publishing (data_registry)

Historical note: These domains were previously in separate .sqlite3 files
but have been unified for simpler queries, atomic transactions, and easier ops.

Usage:
    from dsa110_contimg.database.models import (
        MSIndex, Image, Photometry, Caltable,
        HDF5FileIndex, DataRegistry
    )
    from dsa110_contimg.database.session import get_session

    with get_session("pipeline") as session:
        images = session.query(Image).filter_by(type="dirty").all()

Note:
    All databases use WAL mode for concurrent access with 30s timeout.
    Use scoped_session for multi-threaded contexts (e.g., streaming converter).
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

# Create separate base classes for each database to avoid table conflicts
ProductsBase = declarative_base()
CalRegistryBase = declarative_base()
HDF5Base = declarative_base()
IngestBase = declarative_base()
DataRegistryBase = declarative_base()


# =============================================================================
# Products Domain Models (ms_index, images, photometry tables)
# =============================================================================


class MSIndex(ProductsBase):
    """
    Measurement Set index tracking processing state and metadata.

    This table tracks all MS files in the pipeline, their processing stage,
    and associated metadata like pointing coordinates and field names.
    """

    __tablename__ = "ms_index"

    path = Column(String, primary_key=True, doc="Full path to the MS file")
    start_mjd = Column(Float, doc="Start time of observation in MJD")
    end_mjd = Column(Float, doc="End time of observation in MJD")
    mid_mjd = Column(Float, doc="Mid-point time of observation in MJD")
    processed_at = Column(Float, doc="Unix timestamp when MS was processed")
    status = Column(String, doc="Processing status (e.g., 'pending', 'completed', 'failed')")
    stage = Column(String, doc="Pipeline stage (e.g., 'converted', 'calibrated', 'imaged')")
    stage_updated_at = Column(Float, doc="Unix timestamp of last stage update")
    cal_applied = Column(Integer, default=0, doc="Whether calibration has been applied (0/1)")
    imagename = Column(String, doc="Associated image name/path")
    ra_deg = Column(Float, doc="Right Ascension in degrees")
    dec_deg = Column(Float, doc="Declination in degrees")
    field_name = Column(String, doc="CASA field name")
    pointing_ra_deg = Column(Float, doc="Pointing RA in degrees")
    pointing_dec_deg = Column(Float, doc="Pointing Dec in degrees")

    # Note: relationship to Image removed - no FK constraint in actual database
    # Use manual queries to join if needed

    __table_args__ = (
        Index("idx_ms_index_stage_path", "stage", "path"),
        Index("idx_ms_index_status", "status"),
    )

    def __repr__(self):
        return f"<MSIndex(path='{self.path}', stage='{self.stage}')>"


class Image(ProductsBase):
    """
    Image metadata and quality metrics.

    Stores information about generated FITS images including beam properties,
    noise measurements, and coordinate information.

    Note: ms_path references ms_index.path but the database does not enforce
    a foreign key constraint for backward compatibility with existing data.
    """

    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False, doc="Full path to image file")
    # No FK constraint - matches actual database schema for backward compatibility
    ms_path = Column(String, nullable=False, doc="Source MS path (references ms_index.path)")
    created_at = Column(Float, nullable=False, doc="Unix timestamp when image was created")
    type = Column(String, nullable=False, doc="Image type (e.g., 'dirty', 'clean', 'residual')")
    beam_major_arcsec = Column(Float, doc="Beam major axis in arcseconds")
    beam_minor_arcsec = Column(Float, doc="Beam minor axis in arcseconds")
    beam_pa_deg = Column(Float, doc="Beam position angle in degrees")
    noise_jy = Column(Float, doc="RMS noise level in Jy/beam")
    pbcor = Column(Integer, default=0, doc="Primary beam corrected (0/1)")
    format = Column(String, default="fits", doc="Image format (fits, casa)")
    dynamic_range = Column(Float, doc="Peak/RMS dynamic range")
    field_name = Column(String, doc="CASA field name")
    center_ra_deg = Column(Float, doc="Image center RA in degrees")
    center_dec_deg = Column(Float, doc="Image center Dec in degrees")
    imsize_x = Column(Integer, doc="Image size in X pixels")
    imsize_y = Column(Integer, doc="Image size in Y pixels")
    cellsize_arcsec = Column(Float, doc="Pixel size in arcseconds")
    freq_ghz = Column(Float, doc="Center frequency in GHz")
    bandwidth_mhz = Column(Float, doc="Bandwidth in MHz")
    integration_sec = Column(Float, doc="Total integration time in seconds")

    # Relationships - note: ms_path is just a string column without FK constraint
    # Use primaryjoin to define the relationship explicitly
    # Note: relationship removed for backward compatibility with existing data
    # that may have images without corresponding MS records

    __table_args__ = (Index("idx_images_ms_path", "ms_path"),)

    def __repr__(self):
        return f"<Image(id={self.id}, path='{self.path}', type='{self.type}')>"


class Photometry(ProductsBase):
    """
    Source photometry measurements from images.

    Records flux measurements for detected sources, supporting lightcurve
    analysis and variability studies.

    Note: image_path references images.path but the database does not enforce
    a foreign key constraint for backward compatibility with existing data.
    """

    __tablename__ = "photometry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, doc="Unique source identifier")
    # No FK constraint - matches actual database schema for backward compatibility
    image_path = Column(String, nullable=False, doc="Image path (references images.path)")
    ra_deg = Column(Float, nullable=False, doc="Source RA in degrees")
    dec_deg = Column(Float, nullable=False, doc="Source Dec in degrees")
    nvss_flux_mjy = Column(Float, doc="NVSS catalog flux in mJy")
    peak_jyb = Column(Float, nullable=False, doc="Peak flux in Jy/beam")
    peak_err_jyb = Column(Float, doc="Peak flux error in Jy/beam")
    measured_at = Column(Float, nullable=False, doc="Measurement Unix timestamp")
    snr = Column(Float, doc="Signal-to-noise ratio")
    mjd = Column(Float, doc="Observation MJD")
    flux_jy = Column(Float, doc="Integrated flux in Jy")
    flux_err_jy = Column(Float, doc="Integrated flux error in Jy")
    normalized_flux_jy = Column(Float, doc="Normalized flux in Jy")
    normalized_flux_err_jy = Column(Float, doc="Normalized flux error in Jy")
    mosaic_path = Column(String, doc="Associated mosaic path")
    sep_from_center_deg = Column(Float, doc="Separation from image center in degrees")
    flags = Column(Integer, default=0, doc="Quality flags bitmask")

    # Note: No relationship defined here - image_path is just a string column
    # matching images.path. Use manual queries to join if needed.

    __table_args__ = (
        Index("idx_photometry_image", "image_path"),
        Index("idx_photometry_source_id", "source_id"),
    )

    def __repr__(self):
        return f"<Photometry(id={self.id}, source_id='{self.source_id}', peak={self.peak_jyb})>"


class HDF5FileIndexProducts(ProductsBase):
    """
    HDF5 file index in products domain.

    Tracks raw UVH5 subband files for quick lookup and grouping.
    Used by the streaming converter to find complete observation groups.
    """

    __tablename__ = "hdf5_file_index"

    path = Column(String, primary_key=True, doc="Full path to HDF5 file")
    filename = Column(String, nullable=False, doc="Filename without directory")
    group_id = Column(String, nullable=False, doc="Observation group identifier")
    subband_code = Column(String, nullable=False, doc="Subband code (e.g., 'sb00')")
    timestamp_iso = Column(String, doc="ISO timestamp string")
    timestamp_mjd = Column(Float, doc="Timestamp in MJD")
    file_size_bytes = Column(Integer, doc="File size in bytes")
    modified_time = Column(Float, doc="File modification time")
    indexed_at = Column(Float, nullable=False, doc="When file was indexed")
    stored = Column(Integer, default=1, doc="Whether file is on disk (0/1)")

    __table_args__ = (
        Index("idx_hdf5_group_id", "group_id"),
        Index("idx_hdf5_timestamp_mjd", "timestamp_mjd"),
        Index("idx_hdf5_group_subband", "group_id", "subband_code"),
        Index("idx_hdf5_stored", "stored"),
    )


class StorageLocation(ProductsBase):
    """
    Registered storage locations for data files.
    """

    __tablename__ = "storage_locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_type = Column(
        String, nullable=False, doc="Location type (e.g., 'incoming', 'staging')"
    )
    base_path = Column(String, nullable=False, doc="Base path for this location")
    description = Column(String, doc="Human-readable description")
    registered_at = Column(Float, nullable=False, doc="Registration timestamp")
    status = Column(String, default="active", doc="Status (active/inactive)")
    notes = Column(String, doc="Additional notes")

    __table_args__ = (
        UniqueConstraint("location_type", "base_path"),
        Index("idx_storage_locations_type", "location_type", "status"),
    )


class BatchJob(ProductsBase):
    """
    Batch processing job tracking.
    """

    __tablename__ = "batch_jobs"

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False, doc="Job type (e.g., 'imaging', 'calibration')")
    created_at = Column(Float, nullable=False, doc="Job creation timestamp")
    status = Column(String, nullable=False, doc="Job status")
    total_items = Column(Integer, nullable=False, doc="Total items to process")
    completed_items = Column(Integer, default=0, doc="Completed items count")
    failed_items = Column(Integer, default=0, doc="Failed items count")
    params = Column(Text, doc="Job parameters as JSON")

    # Relationships
    items = relationship("BatchJobItem", back_populates="batch_job")


class BatchJobItem(ProductsBase):
    """
    Individual items within a batch job.
    """

    __tablename__ = "batch_job_items"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("batch_jobs.id"), nullable=False)
    ms_path = Column(String, nullable=False, doc="MS path for this item")
    job_id = Column(Integer, doc="External job ID if applicable")
    status = Column(String, nullable=False, doc="Item status")
    error = Column(Text, doc="Error message if failed")
    started_at = Column(Float, doc="Processing start time")

    # Relationships
    batch_job = relationship("BatchJob", back_populates="items")


class TransientCandidate(ProductsBase):
    """
    Transient source candidate tracking.
    """

    __tablename__ = "transient_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, doc="Associated source ID")
    ra_deg = Column(Float, nullable=False, doc="RA in degrees")
    dec_deg = Column(Float, nullable=False, doc="Dec in degrees")
    detection_type = Column(String, nullable=False, doc="Detection type")
    significance_sigma = Column(Float, doc="Detection significance in sigma")
    detected_at = Column(Float, doc="Detection timestamp")
    priority = Column(String, default="normal", doc="Priority level")
    n_detections = Column(Integer, default=0, doc="Number of detections")
    mean_flux_jy = Column(Float, doc="Mean flux in Jy")
    std_flux_jy = Column(Float, doc="Flux standard deviation")
    eta = Column(Float, doc="Variability index eta")
    v_index = Column(Float, doc="Variability index V")
    chi_squared = Column(Float, doc="Chi-squared statistic")
    is_variable = Column(Integer, default=0, doc="Variable source flag")
    ese_candidate = Column(Integer, default=0, doc="Extreme scattering event candidate")
    first_detected_at = Column(Float, doc="First detection timestamp")
    last_detected_at = Column(Float, doc="Last detection timestamp")
    last_updated = Column(Float, doc="Last update timestamp")
    notes = Column(Text, doc="Additional notes")

    __table_args__ = (
        Index("idx_transients_type", "detection_type", "significance_sigma"),
        Index("idx_transients_coords", "ra_deg", "dec_deg"),
        Index("idx_transients_detected", "detected_at"),
    )


class CalibratorTransit(ProductsBase):
    """
    Calibrator transit times and data availability.
    """

    __tablename__ = "calibrator_transits"

    calibrator_name = Column(String, primary_key=True, doc="Calibrator name")
    transit_mjd = Column(Float, primary_key=True, doc="Transit time in MJD")
    transit_iso = Column(String, nullable=False, doc="Transit time ISO string")
    has_data = Column(Integer, nullable=False, default=0, doc="Data available flag")
    group_id = Column(String, doc="Associated HDF5 group ID")
    group_mid_iso = Column(String, doc="Group mid-time ISO")
    delta_minutes = Column(Float, doc="Time offset from transit in minutes")
    pb_response = Column(Float, doc="Primary beam response")
    dec_match = Column(Integer, nullable=False, default=0, doc="Declination match flag")
    calculated_at = Column(Float, nullable=False, doc="Calculation timestamp")
    updated_at = Column(Float, nullable=False, doc="Last update timestamp")

    __table_args__ = (
        Index("idx_calibrator_transits_calibrator", "calibrator_name", "updated_at"),
        Index("idx_calibrator_transits_has_data", "calibrator_name", "has_data", "transit_mjd"),
        Index("idx_calibrator_transits_mjd", "transit_mjd"),
    )


class DeadLetterQueue(ProductsBase):
    """
    Dead letter queue for failed operations requiring manual intervention.
    """

    __tablename__ = "dead_letter_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    component = Column(String, nullable=False, doc="Component that failed")
    operation = Column(String, nullable=False, doc="Failed operation")
    error_type = Column(String, nullable=False, doc="Error type/category")
    error_message = Column(Text, doc="Error message")
    context_json = Column(Text, doc="Context as JSON")
    created_at = Column(Float, nullable=False, doc="Error timestamp")
    retry_count = Column(Integer, default=0, doc="Retry attempts")
    status = Column(String, default="pending", doc="Status (pending/resolved)")
    resolved_at = Column(Float, doc="Resolution timestamp")
    resolution_note = Column(Text, doc="Resolution notes")


class MonitoringSource(ProductsBase):
    """
    Sources being monitored for variability.
    """

    __tablename__ = "monitoring_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, unique=True, nullable=False, doc="Unique source ID")
    ra_deg = Column(Float, nullable=False, doc="RA in degrees")
    dec_deg = Column(Float, nullable=False, doc="Dec in degrees")
    n_detections = Column(Integer, default=0, doc="Number of detections")
    mean_flux_jy = Column(Float, doc="Mean flux")
    std_flux_jy = Column(Float, doc="Flux std dev")
    eta = Column(Float, doc="Eta variability index")
    v_index = Column(Float, doc="V variability index")
    is_variable = Column(Integer, default=0, doc="Variable flag")
    ese_candidate = Column(Integer, default=0, doc="ESE candidate flag")
    first_detected_at = Column(Float, doc="First detection")
    last_detected_at = Column(Float, doc="Last detection")

    __table_args__ = (
        Index("idx_monitoring_coords", "ra_deg", "dec_deg"),
        Index("idx_monitoring_variable", "is_variable", "eta"),
        Index("idx_monitoring_ese", "ese_candidate"),
    )


# =============================================================================
# Calibration Domain Models (caltables table)
# =============================================================================


class Caltable(CalRegistryBase):
    """
    Calibration table metadata and validity windows.

    Tracks all calibration tables produced by the pipeline, their types,
    and the time ranges over which they are valid.
    """

    __tablename__ = "caltables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    set_name = Column(String, nullable=False, doc="Calibration set name")
    path = Column(String, unique=True, nullable=False, doc="Full path to cal table")
    table_type = Column(String, nullable=False, doc="Table type (e.g., 'bandpass', 'gain')")
    order_index = Column(Integer, nullable=False, doc="Application order")
    cal_field = Column(String, doc="Calibrator field name")
    refant = Column(String, doc="Reference antenna")
    created_at = Column(Float, nullable=False, doc="Creation timestamp")
    valid_start_mjd = Column(Float, doc="Validity start MJD")
    valid_end_mjd = Column(Float, doc="Validity end MJD")
    status = Column(String, nullable=False, doc="Status (active/deprecated)")
    notes = Column(Text, doc="Additional notes")
    source_ms_path = Column(String, doc="Source MS used to derive this table")
    solver_command = Column(String, doc="CASA solver command used")
    solver_version = Column(String, doc="CASA version")
    solver_params = Column(Text, doc="Solver parameters as JSON")
    quality_metrics = Column(Text, doc="Quality metrics as JSON")

    __table_args__ = (
        Index("idx_caltables_source", "source_ms_path"),
        Index("idx_caltables_set", "set_name"),
        Index("idx_caltables_valid", "valid_start_mjd", "valid_end_mjd"),
    )

    def __repr__(self):
        return f"<Caltable(id={self.id}, path='{self.path}', type='{self.table_type}')>"

    def is_valid_at(self, mjd: float) -> bool:
        """Check if this calibration table is valid at a given MJD."""
        if self.valid_start_mjd is not None and mjd < self.valid_start_mjd:
            return False
        if self.valid_end_mjd is not None and mjd > self.valid_end_mjd:
            return False
        return True


# =============================================================================
# HDF5 Domain Models (hdf5_file_index table)
# =============================================================================


class HDF5FileIndex(HDF5Base):
    """
    HDF5 file index for fast subband group queries.

    This is the primary index for UVH5 files, supporting fast lookup
    by timestamp, group ID, and subband number.
    """

    __tablename__ = "hdf5_file_index"

    path = Column(String, primary_key=True, doc="Full path to HDF5 file")
    filename = Column(String, nullable=False, doc="Filename only")
    group_id = Column(String, nullable=False, doc="Observation group ID")
    subband_code = Column(String, nullable=False, doc="Subband code (e.g., 'sb00')")
    subband_num = Column(Integer, doc="Subband number (0-15)")
    timestamp_iso = Column(String, nullable=False, doc="ISO timestamp")
    timestamp_mjd = Column(Float, nullable=False, doc="MJD timestamp")
    file_size_bytes = Column(Integer, doc="File size in bytes")
    modified_time = Column(Float, doc="File modification time")
    indexed_at = Column(Float, doc="Index creation time")
    stored = Column(Integer, default=1, doc="File exists on disk")
    ra_deg = Column(Float, doc="RA in degrees")
    dec_deg = Column(Float, doc="Dec in degrees")
    obs_date = Column(String, doc="Observation date (YYYY-MM-DD)")
    obs_time = Column(String, doc="Observation time (HH:MM:SS)")

    __table_args__ = (
        Index("idx_hdf5_group_id", "group_id"),
        Index("idx_hdf5_timestamp_mjd", "timestamp_mjd"),
        Index("idx_hdf5_group_subband", "group_id", "subband_code"),
        Index("idx_hdf5_stored", "stored"),
        Index("idx_hdf5_ra_dec", "ra_deg", "dec_deg"),
        Index("idx_hdf5_obs_date", "obs_date"),
        Index("idx_hdf5_subband_num", "subband_num"),
        Index("idx_hdf5_group_subband_num", "group_id", "subband_num"),
    )

    def __repr__(self):
        return f"<HDF5FileIndex(path='{self.path}', group_id='{self.group_id}', sb={self.subband_num})>"


class HDF5StorageLocation(HDF5Base):
    """
    Storage location registry for HDF5 files.
    """

    __tablename__ = "storage_locations"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, doc="Location name")
    path = Column(String, nullable=False, doc="Base path")
    description = Column(String, doc="Description")


class PointingHistory(HDF5Base):
    """
    Telescope pointing history tracking.
    """

    __tablename__ = "pointing_history"

    timestamp = Column(Float, primary_key=True, doc="Unix timestamp")
    ra_deg = Column(Float, doc="RA in degrees")
    dec_deg = Column(Float, doc="Dec in degrees")

    __table_args__ = (Index("idx_pointing_timestamp", "timestamp"),)


# =============================================================================
# Ingest Queue Domain Models (ABSURD PostgreSQL)
# =============================================================================


class PointingHistoryIngest(IngestBase):
    """
    Pointing history in ingest database.
    """

    __tablename__ = "pointing_history"

    timestamp = Column(Float, primary_key=True, doc="Unix timestamp")
    ra_deg = Column(Float, doc="RA in degrees")
    dec_deg = Column(Float, doc="Dec in degrees")

    __table_args__ = (Index("idx_pointing_timestamp", "timestamp"),)


# Note: Ingestion queue is now managed by ABSURD PostgreSQL tables:
#   - absurd.ingestion_groups: Group state tracking
#   - absurd.ingestion_subbands: Subband file records
# See absurd/ingestion_db.py for schema.


# =============================================================================
# Data Registry Domain Models (data_registry table)
# =============================================================================


class DataRegistry(DataRegistryBase):
    """
    Data product staging and publishing registry.

    Tracks data products through staging, validation, and publishing workflow.
    """

    __tablename__ = "data_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_type = Column(String, nullable=False, doc="Data type (e.g., 'ms', 'image')")
    data_id = Column(String, unique=True, nullable=False, doc="Unique data ID")
    base_path = Column(String, nullable=False, doc="Base path")
    status = Column(String, nullable=False, default="staging", doc="Status")
    stage_path = Column(String, nullable=False, doc="Staging path")
    published_path = Column(String, doc="Published path")
    created_at = Column(Float, nullable=False, doc="Creation time")
    staged_at = Column(Float, nullable=False, doc="Staging time")
    published_at = Column(Float, doc="Publication time")
    publish_mode = Column(String, doc="Publish mode (copy/move)")
    metadata_json = Column(Text, doc="Metadata as JSON")
    qa_status = Column(String, doc="QA status")
    validation_status = Column(String, doc="Validation status")
    finalization_status = Column(String, default="pending", doc="Finalization status")
    auto_publish_enabled = Column(Integer, default=1, doc="Auto-publish enabled")
    publish_attempts = Column(Integer, default=0, doc="Publish attempt count")
    publish_error = Column(Text, doc="Last publish error")
    photometry_status = Column(String, doc="Photometry status")
    photometry_job_id = Column(String, doc="Photometry job ID")

    # Relationships
    tags = relationship("DataTag", back_populates="data_entry")

    __table_args__ = (
        UniqueConstraint("data_type", "data_id"),
        Index("idx_data_registry_type_status", "data_type", "status"),
        Index("idx_data_registry_status", "status"),
        Index("idx_data_registry_published_at", "published_at"),
        Index("idx_data_registry_finalization", "finalization_status"),
    )

    def __repr__(self):
        return f"<DataRegistry(id={self.id}, data_id='{self.data_id}', status='{self.status}')>"


class DataRelationship(DataRegistryBase):
    """
    Relationships between data products (e.g., MS -> Image).
    """

    __tablename__ = "data_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_data_id = Column(String, ForeignKey("data_registry.data_id"), nullable=False)
    child_data_id = Column(String, ForeignKey("data_registry.data_id"), nullable=False)
    relationship_type = Column(String, nullable=False, doc="Relationship type")

    __table_args__ = (
        UniqueConstraint("parent_data_id", "child_data_id", "relationship_type"),
        Index("idx_data_relationships_parent", "parent_data_id"),
        Index("idx_data_relationships_child", "child_data_id"),
    )


class DataTag(DataRegistryBase):
    """
    Tags associated with data products.
    """

    __tablename__ = "data_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_id = Column(String, ForeignKey("data_registry.data_id"), nullable=False)
    tag = Column(String, nullable=False, doc="Tag value")

    # Relationships
    data_entry = relationship("DataRegistry", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("data_id", "tag"),
        Index("idx_data_tags_data_id", "data_id"),
    )


# =============================================================================
# Utility functions for model introspection
# =============================================================================


def get_all_models_for_base(base) -> list:
    """Get all model classes registered with a declarative base."""
    return [mapper.class_ for mapper in base.registry.mappers]


# Model registry for easy access
PRODUCTS_MODELS = [
    MSIndex,
    Image,
    Photometry,
    HDF5FileIndexProducts,
    StorageLocation,
    BatchJob,
    BatchJobItem,
    TransientCandidate,
    CalibratorTransit,
    DeadLetterQueue,
    MonitoringSource,
]

CAL_REGISTRY_MODELS = [Caltable]

HDF5_MODELS = [HDF5FileIndex, HDF5StorageLocation, PointingHistory]

INGEST_MODELS = [PointingHistoryIngest]

DATA_REGISTRY_MODELS = [DataRegistry, DataRelationship, DataTag]
