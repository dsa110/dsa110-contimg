# This file initializes the calibration module.

from dsa110_contimg.calibration.transit import (
    next_transit_time,
    previous_transits,
    upcoming_transits,
    observation_overlaps_transit,
    pick_best_observation,
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

# Adaptive flagging
from dsa110_contimg.calibration.flagging_adaptive import (
    CalibrationFailure,
    flag_rfi_adaptive,
    flag_rfi_with_gpu_fallback,
    FlaggingStrategy,
    AdaptiveFlaggingResult,
)

# Self-calibration
from dsa110_contimg.calibration.selfcal import (
    SelfCalMode,
    SelfCalStatus,
    SelfCalConfig,
    SelfCalIterationResult,
    SelfCalResult,
    selfcal_iteration,
    selfcal_ms,
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
]