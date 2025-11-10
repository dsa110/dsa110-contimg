"""
Quality assurance package for DSA-110 continuum imaging pipeline.

Provides comprehensive quality validation for MS files, calibration tables,
and image products with integrated alerting.
"""

from dsa110_contimg.qa.ms_quality import validate_ms_quality, quick_ms_check
from dsa110_contimg.qa.calibration_quality import (
    validate_caltable_quality,
    analyze_per_spw_flagging,
    PerSPWFlaggingStats,
    flag_problematic_spws,
    export_per_spw_stats,
    plot_per_spw_flagging,
    check_corrected_data_quality,
    check_upstream_delay_correction,
    verify_kcal_delays,
    inspect_kcal_simple,
    check_caltable_completeness,
)
from dsa110_contimg.qa.image_quality import validate_image_quality, quick_image_check
from dsa110_contimg.qa.pipeline_quality import (
    check_ms_after_conversion,
    check_calibration_quality,
    check_image_quality,
    QualityThresholds,
)

__all__ = [
    # MS quality
    "validate_ms_quality",
    "quick_ms_check",
    # Calibration quality
    "validate_caltable_quality",
    "analyze_per_spw_flagging",
    "PerSPWFlaggingStats",
    "flag_problematic_spws",
    "export_per_spw_stats",
    "plot_per_spw_flagging",
    "check_corrected_data_quality",
    "check_caltable_completeness",
    # Delay-specific QA
    "check_upstream_delay_correction",
    "verify_kcal_delays",
    "inspect_kcal_simple",
    # Image quality
    "validate_image_quality",
    "quick_image_check",
    # Catalog validation
    "catalog_validation",
    # Integrated pipeline QA
    "check_ms_after_conversion",
    "check_calibration_quality",
    "check_image_quality",
    "QualityThresholds",
]
