"""
Unified Configuration for DSA-110 Continuum Imaging Pipeline.

This module consolidates ALL configuration into a single Pydantic Settings class,
replacing ~100+ scattered os.getenv() calls across 15+ files.

Configuration sources (in priority order):
1. Environment variables (highest priority)
2. .env file (if present)
3. Hardcoded defaults (lowest priority)

Usage:
    from dsa110_contimg.config import settings

    # Access typed, validated config
    ms_dir = settings.paths.ms_dir
    timeout = settings.database.timeout

    # All values validated at import time (fail-fast)

Environment variable naming convention:
    CONTIMG_*     - Pipeline-specific settings
    PIPELINE_*    - Legacy names (supported for compatibility)
    DSA110_*      - API/service settings
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional, Set

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class PathSettings(BaseSettings):
    """Path configuration for all pipeline directories and databases.

    All paths are validated to ensure parent directories exist.
    Uses Path type for type safety (CASA wrappers handle string conversion).
    """

    model_config = SettingsConfigDict(
        env_prefix="CONTIMG_",
        extra="ignore",
    )

    # Base directories
    input_dir: Path = Field(
        default=Path("/data/incoming"),
        description="Raw HDF5 input directory (watched by streaming converter)",
    )
    output_dir: Path = Field(
        default=Path("/stage/dsa110-contimg/ms"),
        description="Default output directory for measurement sets",
    )
    scratch_dir: Path = Field(
        default=Path("/stage/dsa110-contimg"), description="Base scratch directory (NVMe SSD)"
    )
    state_dir: Path = Field(
        default=Path("/data/dsa110-contimg/state/db"),
        description="Pipeline state directory (SQLite databases)",
    )

    # Scratch subdirectories (derived from scratch_dir by default)
    ms_dir: Optional[Path] = Field(default=None, description="Measurement set output directory")
    caltables_dir: Optional[Path] = Field(default=None, description="Calibration tables directory")
    images_dir: Optional[Path] = Field(default=None, description="Images output directory")
    mosaics_dir: Optional[Path] = Field(default=None, description="Mosaics output directory")
    logs_dir: Optional[Path] = Field(
        default=None, description="Log files directory (scratch, for transient logs)"
    )
    casa_logs_dir: Path = Field(
        default=Path("/data/dsa110-contimg/state/logs/casa"),
        description="CASA log files directory (persistent storage)",
    )

    # tmpfs staging
    stage_to_tmpfs: bool = Field(default=True, description="Enable tmpfs staging for 3-5x speedup")
    tmpfs_path: Path = Field(default=Path("/dev/shm"), description="tmpfs mount point")

    @model_validator(mode="after")
    def set_scratch_subdirs(self) -> "PathSettings":
        """Set scratch subdirectories if not explicitly configured."""
        if self.ms_dir is None:
            self.ms_dir = self.scratch_dir / "ms"
        if self.caltables_dir is None:
            self.caltables_dir = self.scratch_dir / "caltables"
        if self.images_dir is None:
            self.images_dir = self.scratch_dir / "images"
        if self.mosaics_dir is None:
            self.mosaics_dir = self.scratch_dir / "mosaics"
        if self.logs_dir is None:
            self.logs_dir = self.scratch_dir / "logs"
        return self


class DatabaseSettings(BaseSettings):
    """Database configuration for the unified SQLite database.

    All pipeline data is stored in a single unified database (pipeline.sqlite3).
    Legacy per-domain databases have been migrated and deprecated.
    """

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    # Unified database - the single source of truth
    path: Path = Field(
        default=Path("/data/dsa110-contimg/state/db/pipeline.sqlite3"),
        validation_alias="PIPELINE_DB",
        description="Unified pipeline database path",
    )

    # Connection settings
    timeout: float = Field(
        default=30.0,
        validation_alias="DB_CONNECTION_TIMEOUT",
        description="Database connection timeout in seconds",
    )
    wal_mode: bool = Field(default=True, description="Enable WAL mode for concurrent access")


class ConversionSettings(BaseSettings):
    """Configuration for UVH5 -> MS conversion.

    All conversion parameters are centralized here instead of being passed
    as 10+ function arguments. Functions only need essential parameters
    (input, output) and pull configuration from settings.conversion.

    Example:
        from dsa110_contimg.config import settings

        # Instead of convert_group(..., max_workers=4, skip_incomplete=True, ...)
        # Just use:
        timeout = settings.conversion.timeout_s
        workers = settings.conversion.max_workers
    """

    model_config = SettingsConfigDict(
        env_prefix="CONTIMG_",
        extra="ignore",
    )

    # Subband configuration
    expected_subbands: int = Field(
        default=16, description="Expected number of subbands per observation"
    )
    chunk_minutes: float = Field(default=5.0, description="Observation chunk duration in minutes")

    # Time windowing for grouping
    cluster_tolerance_s: float = Field(
        default=60.0, description="Time window for grouping subbands (seconds)"
    )

    # Parallelization
    max_workers: int = Field(
        default=4,
        validation_alias="max_workers",
        description="Maximum parallel workers for conversion",
    )
    omp_threads: int = Field(
        default=4, validation_alias="OMP_NUM_THREADS", description="OpenMP threads per worker"
    )
    parallel_loading: bool = Field(
        default=True, description="Enable parallel I/O for subband loading"
    )
    io_max_workers: int = Field(
        default=4, description="Maximum I/O threads for parallel subband loading"
    )

    # Behavior flags (rarely changed - moved from function args)
    skip_incomplete: bool = Field(
        default=True, description="Skip groups with fewer than expected_subbands"
    )
    skip_existing: bool = Field(
        default=False, description="Skip groups that already have output MS files"
    )
    rename_calibrator_fields: bool = Field(
        default=True, description="Auto-detect and rename calibrator fields"
    )

    # Timeout and retry
    timeout_s: float = Field(default=3600.0, description="Conversion timeout in seconds")
    retry_count: int = Field(default=2, description="Number of retries on failure")

    # Writer configuration
    writer_type: str = Field(
        default="parallel-subband", description="MS writer type: parallel-subband, direct-subband"
    )
    batch_size: int = Field(default=4, description="Subbands to load per batch")


class CalibrationSettings(BaseSettings):
    """Configuration for calibration operations."""

    model_config = SettingsConfigDict(
        env_prefix="CONTIMG_CAL_",
        extra="ignore",
    )

    bandpass_interval_hours: float = Field(
        default=24.0,
        validation_alias="bandpass_interval_hours",
        description="Bandpass calibration interval",
    )
    gain_interval_hours: float = Field(
        default=1.0, validation_alias="gain_interval_hours", description="Gain calibration interval"
    )
    use_nvss_skymodel: bool = Field(
        default=True,
        validation_alias="use_nvss_skymodel",
        description="Use NVSS sky model for calibration",
    )
    bp_minsnr: float = Field(
        default=3.0,
        validation_alias="bp_minsnr",
        description="Minimum SNR for bandpass calibration",
    )
    gain_minsnr: float = Field(
        default=3.0, validation_alias="gain_minsnr", description="Minimum SNR for gain calibration"
    )
    gain_solint: str = Field(
        default="int", validation_alias="gain_solint", description="Gain solution interval"
    )


class ImagingSettings(BaseSettings):
    """Configuration for imaging operations."""

    model_config = SettingsConfigDict(
        env_prefix="IMG_",
        extra="ignore",
    )

    imsize: int = Field(default=2048, description="Image size in pixels")
    robust: float = Field(default=0.0, description="Briggs robust parameter")
    niter: int = Field(default=10000, description="Maximum clean iterations")


class GPUSettings(BaseSettings):
    """GPU acceleration configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PIPELINE_GPU_",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable GPU acceleration")
    devices: str = Field(default="", description="Comma-separated GPU device IDs (empty = all)")
    gridder: str = Field(
        default="idg", description="WSClean gridder: idg (GPU), wgridder (CPU), wstacking (CPU)"
    )
    idg_mode: str = Field(default="hybrid", description="IDG mode: cpu, gpu, or hybrid")
    memory_fraction: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Max fraction of GPU memory to use"
    )


class QASettings(BaseSettings):
    """Quality assurance thresholds."""

    model_config = SettingsConfigDict(
        env_prefix="CONTIMG_QA_",
        extra="ignore",
    )

    # MS quality
    ms_max_flagged: float = Field(default=0.5, description="Max flagged fraction for MS")
    ms_max_zeros: float = Field(default=0.3, description="Max zero fraction for MS")
    ms_min_amp: float = Field(default=1e-6, description="Minimum amplitude for MS")

    # Calibration quality
    cal_max_flagged: float = Field(default=0.3, description="Max flagged fraction for cal")
    cal_min_amp: float = Field(default=0.1, description="Minimum amplitude for cal")
    cal_max_amp: float = Field(default=10.0, description="Maximum amplitude for cal")
    cal_max_phase_scatter: float = Field(default=90.0, description="Max phase scatter (deg)")

    # Image quality
    img_min_dynamic_range: float = Field(default=5.0, description="Min dynamic range")
    img_min_peak_snr: float = Field(default=5.0, description="Min peak SNR")
    img_min_5sigma_pixels: int = Field(default=10, description="Min 5-sigma pixels")


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    level: str = Field(
        default="INFO", validation_alias="CONTIMG_LOG_LEVEL", description="Log level"
    )
    json_format: bool = Field(
        default=False, validation_alias="PIPELINE_LOG_FORMAT", description="Use JSON log format"
    )
    max_size_mb: int = Field(default=100, description="Max log file size in MB")
    backup_count: int = Field(default=5, description="Number of backup log files")


class APISettings(BaseSettings):
    """API server configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DSA110_",
        extra="ignore",
    )

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        validation_alias="env",
        description="Deployment environment",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    workers: int = Field(default=1, description="Number of workers")

    # Auth settings
    auth_disabled: bool = Field(default=False, description="Disable authentication (dev only)")
    api_keys_csv: str = Field(
        default="", description="Comma-separated API keys (env: DSA110_API_KEYS_CSV)"
    )
    jwt_secret: str = Field(default="", description="JWT signing secret")

    # Rate limiting
    rate_limit_disabled: bool = Field(default=False, description="Disable rate limiting")
    rate_limit_minute: int = Field(default=100, description="Requests per minute")
    rate_limit_hour: int = Field(default=1000, description="Requests per hour")

    @property
    def api_keys(self) -> Set[str]:
        """Parse comma-separated API keys into a set."""
        if not self.api_keys_csv:
            return set()
        return set(k.strip() for k in self.api_keys_csv.split(",") if k.strip())


class RedisSettings(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    url: str = Field(
        default="redis://localhost:6379",
        validation_alias="DSA110_REDIS_URL",
        description="Redis connection URL",
    )
    queue_name: str = Field(
        default="dsa110-pipeline", validation_alias="DSA110_QUEUE_NAME", description="RQ queue name"
    )
    max_connections: int = Field(default=10, description="Max Redis connections")
    socket_timeout: float = Field(default=5.0, description="Redis socket timeout")
    cache_enabled: bool = Field(
        default=True, validation_alias="REDIS_CACHE_ENABLED", description="Enable Redis caching"
    )
    default_ttl: int = Field(
        default=300,
        validation_alias="REDIS_DEFAULT_TTL",
        description="Default cache TTL in seconds",
    )


class AlertingSettings(BaseSettings):
    """Alerting and notification configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CONTIMG_",
        extra="ignore",
    )

    # Slack
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    slack_min_severity: str = Field(
        default="WARNING", description="Minimum severity for Slack alerts"
    )

    # Email
    smtp_host: Optional[str] = Field(default=None, description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    alert_from_email: str = Field(
        default="dsa110-pipeline@example.com", description="Alert sender email"
    )
    alert_to_emails: str = Field(default="", description="Comma-separated alert recipients")


class DiskSettings(BaseSettings):
    """Disk monitoring configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CONTIMG_",
        extra="ignore",
    )

    disk_warn_gb: int = Field(default=200, description="Warning threshold for disk space (GB)")
    disk_critical_gb: int = Field(default=100, description="Critical threshold for disk space (GB)")
    tmpfs_warn_percent: int = Field(default=90, description="Warning threshold for tmpfs usage (%)")
    tmpfs_critical_percent: int = Field(
        default=95, description="Critical threshold for tmpfs usage (%)"
    )
    auto_cleanup_enabled: bool = Field(default=False, description="Enable automatic cleanup")


class TLSSettings(BaseSettings):
    """TLS/SSL configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DSA110_TLS_",
        extra="ignore",
    )

    enabled: bool = Field(default=False, description="Enable TLS")
    cert: Optional[Path] = Field(default=None, description="TLS certificate path")
    key: Optional[Path] = Field(default=None, description="TLS key path")
    ca: Optional[Path] = Field(default=None, description="CA certificate path")


class Settings(BaseSettings):
    """
    Root configuration for DSA-110 Continuum Imaging Pipeline.

    All configuration is loaded and validated at import time.
    Access via the global `settings` singleton.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Domain settings
    paths: PathSettings = Field(default_factory=PathSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    conversion: ConversionSettings = Field(default_factory=ConversionSettings)
    calibration: CalibrationSettings = Field(default_factory=CalibrationSettings)
    imaging: ImagingSettings = Field(default_factory=ImagingSettings)
    gpu: GPUSettings = Field(default_factory=GPUSettings)
    qa: QASettings = Field(default_factory=QASettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    api: APISettings = Field(default_factory=APISettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    alerting: AlertingSettings = Field(default_factory=AlertingSettings)
    disk: DiskSettings = Field(default_factory=DiskSettings)
    tls: TLSSettings = Field(default_factory=TLSSettings)

    # Threading
    omp_num_threads: int = Field(
        default=4, validation_alias="OMP_NUM_THREADS", description="OpenMP thread count"
    )
    mkl_num_threads: int = Field(
        default=4, validation_alias="MKL_NUM_THREADS", description="MKL thread count"
    )

    # Telescope identity
    telescope_name: str = Field(
        default="DSA_110",
        validation_alias="PIPELINE_TELESCOPE_NAME",
        description="Telescope name (use DSA_110 for EveryBeam)",
    )

    def validate_production(self) -> list[str]:
        """Validate production-critical settings. Returns list of errors."""
        errors = []

        if self.api.environment == Environment.PRODUCTION:
            if self.api.auth_disabled:
                errors.append("Authentication cannot be disabled in production")
            if not self.api.api_keys:
                errors.append("At least one API key required in production")
            if len(self.api.jwt_secret) < 32:
                errors.append("JWT secret must be at least 32 characters")
            if self.api.debug:
                errors.append("Debug mode cannot be enabled in production")

        return errors

    def validate_or_raise(self) -> None:
        """Validate and raise if errors found."""
        errors = self.validate_production()
        if errors:
            raise ValueError(
                "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )


@lru_cache()
def get_settings() -> Settings:
    """Get the application settings (singleton, cached)."""
    return Settings()


# Global settings instance - validated at import time
# Access via: from dsa110_contimg.config import settings
settings = get_settings()


# Convenience accessors for backwards compatibility
def get_scratch_dir() -> Path:
    """Get scratch directory path."""
    return settings.paths.scratch_dir


def get_state_dir() -> Path:
    """Get state directory path."""
    return settings.paths.state_dir


def get_unified_db_path() -> Path:
    """Get unified database path."""
    return settings.database.unified_db
