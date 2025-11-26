"""
Centralized configuration for QA validation thresholds and settings.

All validation thresholds should be defined here for consistency and easy adjustment.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class AstrometryConfig:
    """Configuration for astrometry validation."""

    max_offset_arcsec: float = 1.0
    max_rms_arcsec: float = 0.5
    min_match_fraction: float = 0.8
    match_radius_arcsec: float = 2.0
    use_pybdsf: bool = True
    pybdsf_rms_box: Tuple[int, int] = (40, 10)


@dataclass
class FluxScaleConfig:
    """Configuration for flux scale validation."""

    max_flux_ratio_deviation: float = 0.2  # 20% deviation allowed
    min_match_fraction: float = 0.5
    match_radius_arcsec: float = 2.0
    flux_box_size_pix: int = 5


@dataclass
class SourceCountsConfig:
    """Configuration for source counts validation."""

    min_completeness: float = 0.7
    max_false_positive_rate: float = 0.1
    min_detection_snr: float = 5.0
    use_pybdsf: bool = True
    pybdsf_rms_box: Tuple[int, int] = (40, 10)


@dataclass
class ImageQualityConfig:
    """Configuration for image quality validation."""

    max_rms_noise: float = 0.001
    min_dynamic_range: float = 100.0
    max_beam_major_arcsec: float = 10.0
    min_beam_minor_arcsec: float = 0.1


@dataclass
class CalibrationConfig:
    """Configuration for calibration validation."""

    max_delay_ns: float = 10.0
    max_gain_deviation: float = 0.1
    min_flagging_fraction: float = 0.0
    max_flagging_fraction: float = 0.5


@dataclass
class PhotometryConfig:
    """Configuration for photometry validation."""

    max_flux_error_fraction: float = 0.1  # 10% error allowed
    min_match_fraction: float = 0.8
    max_position_offset_arcsec: float = 1.0
    flux_box_size_pix: int = 5


@dataclass
class VariabilityConfig:
    """Configuration for variability/ESE validation."""

    min_chi_squared: float = 25.0  # 5-sigma threshold
    min_variability_fraction: float = 0.2  # 20% flux change
    max_false_positive_rate: float = 0.01  # 1% false positives
    min_observations: int = 10


@dataclass
class MosaicConfig:
    """Configuration for mosaic validation."""

    max_seam_flux_deviation: float = 0.1  # 10% flux difference in overlaps
    max_wcs_offset_arcsec: float = 0.1
    min_overlap_fraction: float = 0.1
    max_noise_ratio: float = 1.5  # Noise can be 1.5x different


@dataclass
class StreamingConfig:
    """Configuration for streaming validation."""

    max_time_gap_seconds: float = 60.0
    max_latency_seconds: float = 300.0  # 5 minutes
    min_throughput_mbps: float = 10.0
    max_missing_files_fraction: float = 0.01  # 1% missing files


@dataclass
class DatabaseConfig:
    """Configuration for database validation."""

    max_orphaned_records: int = 0
    max_missing_files_fraction: float = 0.0
    require_referential_integrity: bool = True


@dataclass
class FastValidationConfig:
    """Configuration for fast validation mode (<60s target).

    Aggressive sampling and optimization settings for rapid validation.
    """

    # Sampling parameters (more aggressive than standard)
    ms_sample_fraction: float = 0.01  # 1% instead of 10%
    image_sample_pixels: int = 10000  # Fixed pixel count instead of full image
    catalog_max_sources: int = 50  # Limit catalog matches
    calibration_sample_fraction: float = 0.01  # 1% for calibration checks

    # Performance settings
    skip_expensive_checks: bool = True  # Skip forced photometry, detailed catalog matching
    parallel_workers: int = 4  # Number of parallel workers
    timeout_seconds: int = 60  # Maximum time for validation

    # Tiered validation settings
    tier1_timeout_seconds: float = 10.0  # Quick checks timeout
    tier2_timeout_seconds: float = 30.0  # Standard checks timeout
    tier3_timeout_seconds: float = 60.0  # Detailed checks timeout (optional)

    # What to skip in fast mode
    skip_catalog_validation: bool = False  # Can be enabled for very fast mode
    skip_photometry_validation: bool = False
    skip_variability_validation: bool = True  # Usually skip in fast mode
    skip_mosaic_validation: bool = True  # Usually skip in fast mode

    # Caching
    use_cache: bool = True  # Enable result caching
    cache_ttl_seconds: int = 3600  # Cache TTL (1 hour)


@dataclass
class QAConfig:
    """Master configuration for all QA validation.

    Usage:
        from dsa110_contimg.qa.config import get_default_config

        config = get_default_config()
        # Override specific thresholds
        config.astrometry.max_offset_arcsec = 2.0
    """

    astrometry: AstrometryConfig = field(default_factory=AstrometryConfig)
    flux_scale: FluxScaleConfig = field(default_factory=FluxScaleConfig)
    source_counts: SourceCountsConfig = field(default_factory=SourceCountsConfig)
    image_quality: ImageQualityConfig = field(default_factory=ImageQualityConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    photometry: PhotometryConfig = field(default_factory=PhotometryConfig)
    variability: VariabilityConfig = field(default_factory=VariabilityConfig)
    mosaic: MosaicConfig = field(default_factory=MosaicConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    fast_validation: FastValidationConfig = field(default_factory=FastValidationConfig)

    # Global settings
    generate_html_report: bool = True
    generate_plots: bool = True
    verbose: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "astrometry": {
                "max_offset_arcsec": self.astrometry.max_offset_arcsec,
                "max_rms_arcsec": self.astrometry.max_rms_arcsec,
                "min_match_fraction": self.astrometry.min_match_fraction,
                "match_radius_arcsec": self.astrometry.match_radius_arcsec,
                "use_pybdsf": self.astrometry.use_pybdsf,
                "pybdsf_rms_box": self.astrometry.pybdsf_rms_box,
            },
            "flux_scale": {
                "max_flux_ratio_deviation": self.flux_scale.max_flux_ratio_deviation,
                "min_match_fraction": self.flux_scale.min_match_fraction,
                "match_radius_arcsec": self.flux_scale.match_radius_arcsec,
                "flux_box_size_pix": self.flux_scale.flux_box_size_pix,
            },
            "source_counts": {
                "min_completeness": self.source_counts.min_completeness,
                "max_false_positive_rate": self.source_counts.max_false_positive_rate,
                "min_detection_snr": self.source_counts.min_detection_snr,
                "use_pybdsf": self.source_counts.use_pybdsf,
                "pybdsf_rms_box": self.source_counts.pybdsf_rms_box,
            },
            "image_quality": {
                "max_rms_noise": self.image_quality.max_rms_noise,
                "min_dynamic_range": self.image_quality.min_dynamic_range,
                "max_beam_major_arcsec": self.image_quality.max_beam_major_arcsec,
                "min_beam_minor_arcsec": self.image_quality.min_beam_minor_arcsec,
            },
            "calibration": {
                "max_delay_ns": self.calibration.max_delay_ns,
                "max_gain_deviation": self.calibration.max_gain_deviation,
                "min_flagging_fraction": self.calibration.min_flagging_fraction,
                "max_flagging_fraction": self.calibration.max_flagging_fraction,
            },
            "photometry": {
                "max_flux_error_fraction": self.photometry.max_flux_error_fraction,
                "min_match_fraction": self.photometry.min_match_fraction,
                "max_position_offset_arcsec": self.photometry.max_position_offset_arcsec,
                "flux_box_size_pix": self.photometry.flux_box_size_pix,
            },
            "variability": {
                "min_chi_squared": self.variability.min_chi_squared,
                "min_variability_fraction": self.variability.min_variability_fraction,
                "max_false_positive_rate": self.variability.max_false_positive_rate,
                "min_observations": self.variability.min_observations,
            },
            "mosaic": {
                "max_seam_flux_deviation": self.mosaic.max_seam_flux_deviation,
                "max_wcs_offset_arcsec": self.mosaic.max_wcs_offset_arcsec,
                "min_overlap_fraction": self.mosaic.min_overlap_fraction,
                "max_noise_ratio": self.mosaic.max_noise_ratio,
            },
            "streaming": {
                "max_time_gap_seconds": self.streaming.max_time_gap_seconds,
                "max_latency_seconds": self.streaming.max_latency_seconds,
                "min_throughput_mbps": self.streaming.min_throughput_mbps,
                "max_missing_files_fraction": self.streaming.max_missing_files_fraction,
            },
            "database": {
                "max_orphaned_records": self.database.max_orphaned_records,
                "max_missing_files_fraction": self.database.max_missing_files_fraction,
                "require_referential_integrity": self.database.require_referential_integrity,
            },
            "fast_validation": {
                "ms_sample_fraction": self.fast_validation.ms_sample_fraction,
                "image_sample_pixels": self.fast_validation.image_sample_pixels,
                "catalog_max_sources": self.fast_validation.catalog_max_sources,
                "calibration_sample_fraction": self.fast_validation.calibration_sample_fraction,
                "skip_expensive_checks": self.fast_validation.skip_expensive_checks,
                "parallel_workers": self.fast_validation.parallel_workers,
                "timeout_seconds": self.fast_validation.timeout_seconds,
                "use_cache": self.fast_validation.use_cache,
            },
            "generate_html_report": self.generate_html_report,
            "generate_plots": self.generate_plots,
            "verbose": self.verbose,
        }


# Global default configuration instance
_default_config: Optional[QAConfig] = None


def get_default_config() -> QAConfig:
    """Get default QA configuration.

    Returns:
        QAConfig instance with default thresholds
    """
    global _default_config
    if _default_config is None:
        _default_config = QAConfig()
    return _default_config


def load_config_from_dict(config_dict: Dict[str, Any]) -> QAConfig:
    """Load configuration from dictionary.

    Args:
        config_dict: Dictionary with configuration values

    Returns:
        QAConfig instance
    """
    config = QAConfig()

    # Update astrometry config
    if "astrometry" in config_dict:
        astro_dict = config_dict["astrometry"]
        config.astrometry.max_offset_arcsec = astro_dict.get("max_offset_arcsec", 1.0)
        config.astrometry.max_rms_arcsec = astro_dict.get("max_rms_arcsec", 0.5)
        config.astrometry.min_match_fraction = astro_dict.get("min_match_fraction", 0.8)
        config.astrometry.match_radius_arcsec = astro_dict.get("match_radius_arcsec", 2.0)

    # Update flux scale config
    if "flux_scale" in config_dict:
        flux_dict = config_dict["flux_scale"]
        config.flux_scale.max_flux_ratio_deviation = flux_dict.get("max_flux_ratio_deviation", 0.2)
        config.flux_scale.min_match_fraction = flux_dict.get("min_match_fraction", 0.5)
        config.flux_scale.match_radius_arcsec = flux_dict.get("match_radius_arcsec", 2.0)
        config.flux_scale.flux_box_size_pix = flux_dict.get("flux_box_size_pix", 5)

    # Update other configs similarly...
    # (Abbreviated for brevity - full implementation would update all configs)

    # Global settings
    config.generate_html_report = config_dict.get("generate_html_report", True)
    config.generate_plots = config_dict.get("generate_plots", True)
    config.verbose = config_dict.get("verbose", False)

    return config
