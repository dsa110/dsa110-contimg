# This file initializes the calibration module.

# Catalog registry (unified catalog query interface)
from dsa110_contimg.calibration.catalog_registry import (
    CATALOG_REGISTRY,
    CatalogConfig,
    CatalogName,
    list_available_catalogs,
    query_catalog,
    query_multiple_catalogs,
)

# Adaptive flagging
from dsa110_contimg.calibration.flagging_adaptive import (
    AdaptiveFlaggingResult,
    CalibrationFailure,
    FlaggingStrategy,
    flag_rfi_adaptive,
    flag_rfi_with_gpu_fallback,
)

# Pipeline jobs and orchestration
from dsa110_contimg.calibration.jobs import (
    CalibrationApplyJob,
    CalibrationJobConfig,
    CalibrationSolveJob,
    CalibrationValidateJob,
)
from dsa110_contimg.calibration.pipeline import (
    CalibrationPipeline,
    CalibrationPipelineConfig,
    CalibrationResult,
    CalibrationStatus,
    StreamingCalibrationPipeline,
    run_calibration_pipeline,
)

# QA module
from dsa110_contimg.calibration.qa import (
    CalibrationMetrics,
    CalibrationQAResult,
    CalibrationQAStore,
    QAIssue,
    QAThresholds,
    assess_calibration_quality,
    compute_calibration_metrics,
    get_qa_store,
)

# Self-calibration
from dsa110_contimg.calibration.selfcal import (
    SelfCalConfig,
    SelfCalIterationResult,
    SelfCalMode,
    SelfCalResult,
    SelfCalStatus,
    selfcal_iteration,
    selfcal_ms,
)
from dsa110_contimg.calibration.transit import (
    next_transit_time,
    observation_overlaps_transit,
    pick_best_observation,
    previous_transits,
    upcoming_transits,
)

__all__ = [
    # Transit utilities
    "next_transit_time",
    "previous_transits",
    "upcoming_transits",
    "observation_overlaps_transit",
    "pick_best_observation",
    # Pipeline jobs
    "CalibrationApplyJob",
    "CalibrationJobConfig",
    "CalibrationSolveJob",
    "CalibrationValidateJob",
    # Pipelines
    "CalibrationPipeline",
    "CalibrationPipelineConfig",
    "CalibrationResult",
    "CalibrationStatus",
    "StreamingCalibrationPipeline",
    "run_calibration_pipeline",
    # QA
    "CalibrationMetrics",
    "CalibrationQAResult",
    "CalibrationQAStore",
    "QAIssue",
    "QAThresholds",
    "assess_calibration_quality",
    "compute_calibration_metrics",
    "get_qa_store",
    # Adaptive flagging
    "CalibrationFailure",
    "flag_rfi_adaptive",
    "flag_rfi_with_gpu_fallback",
    "FlaggingStrategy",
    "AdaptiveFlaggingResult",
    # Self-calibration
    "SelfCalMode",
    "SelfCalStatus",
    "SelfCalConfig",
    "SelfCalIterationResult",
    "SelfCalResult",
    "selfcal_iteration",
    "selfcal_ms",
    # Catalog registry
    "CatalogName",
    "CatalogConfig",
    "CATALOG_REGISTRY",
    "query_catalog",
    "query_multiple_catalogs",
    "list_available_catalogs",
]
