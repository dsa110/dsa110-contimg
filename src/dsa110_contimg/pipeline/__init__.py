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

from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import PipelineStage, StageStatus
from dsa110_contimg.pipeline.state import (
    StateRepository,
    SQLiteStateRepository,
    JobState,
)
from dsa110_contimg.pipeline.resources import ResourceManager
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.orchestrator import (
    PipelineOrchestrator,
    StageDefinition,
    PipelineResult,
)
from dsa110_contimg.pipeline.workflows import (
    WorkflowBuilder,
    standard_imaging_workflow,
    quicklook_workflow,
    reprocessing_workflow,
)

# Import stages_impl lazily to avoid circular dependencies
def __getattr__(name: str):
    """Lazy import for stage implementations."""
    if name in ("ConversionStage", "CalibrationStage", "ImagingStage"):
        from dsa110_contimg.pipeline.stages_impl import (
            ConversionStage,
            CalibrationStage,
            ImagingStage,
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
    "WorkflowBuilder",
    "standard_imaging_workflow",
    "quicklook_workflow",
    "reprocessing_workflow",
]

