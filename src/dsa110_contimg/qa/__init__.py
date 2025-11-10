"""
Quality assurance package for DSA-110 continuum imaging pipeline.

Provides comprehensive quality validation for MS files, calibration tables,
and image products with integrated alerting.
"""

from dsa110_contimg.qa.calibration_quality import (
    PerSPWFlaggingStats,
    analyze_per_spw_flagging,
    check_caltable_completeness,
    check_corrected_data_quality,
    check_upstream_delay_correction,
    export_per_spw_stats,
    flag_problematic_spws,
    inspect_kcal_simple,
    plot_per_spw_flagging,
    validate_caltable_quality,
    verify_kcal_delays,
)
from dsa110_contimg.qa.image_quality import quick_image_check, validate_image_quality
from dsa110_contimg.qa.ms_quality import quick_ms_check, validate_ms_quality
from dsa110_contimg.qa.pipeline_quality import (
    QualityThresholds,
    check_calibration_quality,
    check_image_quality,
    check_ms_after_conversion,
)

# Visualization framework
from dsa110_contimg.qa.visualization import (
    CasaTable,
    FITSFile,
    browse_qa_outputs,
    display_qa_summary,
    generate_fits_viewer_notebook,
    generate_ms_explorer_notebook,
    generate_qa_notebook,
    ls,
)
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization
from dsa110_contimg.qa.postage_stamps import (
    create_cutout,
    normalize_cutout,
    plot_cutout,
    show_all_cutouts,
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
    # Visualization framework
    "FITSFile",
    "CasaTable",
    "ls",
    "generate_qa_notebook",
    "generate_fits_viewer_notebook",
    "generate_ms_explorer_notebook",
    "browse_qa_outputs",
    "display_qa_summary",
    "run_ms_qa_with_visualization",
    # Postage stamps
    "create_cutout",
    "normalize_cutout",
    "plot_cutout",
    "show_all_cutouts",
]
