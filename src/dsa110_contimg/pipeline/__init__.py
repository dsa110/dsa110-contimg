"""
Pipeline orchestration framework for DSA-110 continuum imaging.

This package provides a declarative, type-safe pipeline orchestration system
that replaces manual workflow chaining with automatic dependency resolution,
structured error handling, and resource management.

Key Components:
- PipelineContext: Immutable context passed between stages
- PipelineStage: Base class for all pipeline stages
- PipelineOrchestrator: Executes stages respecting dependencies
- StateRepository: Abstraction for state persistence
- ResourceManager: Automatic resource cleanup
- PipelineConfig: Unified configuration system
"""

from dsa110_contimg.pipeline.adapter import LegacyWorkflowAdapter
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.observability import PipelineObserver, StageMetrics
from dsa110_contimg.pipeline.orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStatus,
    StageDefinition,
)
from dsa110_contimg.pipeline.resilience import RetryPolicy, RetryStrategy
from dsa110_contimg.pipeline.resources import ResourceManager
from dsa110_contimg.pipeline.stages import PipelineStage, StageStatus
from dsa110_contimg.pipeline.state import (
    JobState,
    SQLiteStateRepository,
    StateRepository,
)
from dsa110_contimg.pipeline.workflows import (
    WorkflowBuilder,
    quicklook_workflow,
    reprocessing_workflow,
    standard_imaging_workflow,
)


# Import stages_impl lazily to avoid circular dependencies
def __getattr__(name: str):
    """Lazy import for stage implementations."""
    if name in (
        "ConversionStage",
        "CalibrationSolveStage",
        "CalibrationStage",
        "ImagingStage",
        "OrganizationStage",
    ):
        from dsa110_contimg.pipeline.stages_impl import (
            CalibrationSolveStage,
            CalibrationStage,
            ConversionStage,
            ImagingStage,
            OrganizationStage,
        )

        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PipelineContext",
    "PipelineStage",
    "StageStatus",
    "StateRepository",
    "SQLiteStateRepository",
    "JobState",
    "ResourceManager",
    "PipelineConfig",
    "PipelineOrchestrator",
    "StageDefinition",
    "PipelineResult",
    "PipelineStatus",
    "WorkflowBuilder",
    "standard_imaging_workflow",
    "quicklook_workflow",
    "reprocessing_workflow",
    "PipelineObserver",
    "StageMetrics",
    "LegacyWorkflowAdapter",
    "RetryPolicy",
    "RetryStrategy",
]
