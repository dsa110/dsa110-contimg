"""
Workflow composition and reusable workflow definitions.

Provides builders and standard workflows for common pipeline patterns.
"""

from __future__ import annotations

from typing import List, Optional

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.orchestrator import PipelineOrchestrator, StageDefinition
from dsa110_contimg.pipeline.resilience import RetryPolicy, RetryStrategy
from dsa110_contimg.pipeline.stages import PipelineStage


class WorkflowBuilder:
    """Builder for creating reusable workflows.
    
    Example:
        workflow = (WorkflowBuilder()
            .add_stage("convert", ConversionStage())
            .add_stage("calibrate", CalibrationStage(), depends_on=["convert"])
            .add_stage("image", ImagingStage(), depends_on=["calibrate"])
            .build())
    """
    
    def __init__(self):
        """Initialize workflow builder."""
        self.stages: List[StageDefinition] = []
    
    def add_stage(
        self,
        name: str,
        stage: PipelineStage,
        depends_on: Optional[List[str]] = None,
        retry_policy: Optional[RetryPolicy] = None,
        timeout: Optional[float] = None,
    ) -> WorkflowBuilder:
        """Add stage to workflow.
        
        Args:
            name: Stage name
            stage: Pipeline stage instance
            depends_on: List of prerequisite stage names
            retry_policy: Optional retry policy
            timeout: Optional timeout in seconds
            
        Returns:
            Self for method chaining
        """
        self.stages.append(StageDefinition(
            name=name,
            stage=stage,
            dependencies=depends_on or [],
            retry_policy=retry_policy,
            timeout=timeout,
        ))
        return self
    
    def build(self) -> PipelineOrchestrator:
        """Build pipeline orchestrator.
        
        Returns:
            PipelineOrchestrator instance
        """
        return PipelineOrchestrator(self.stages)


def standard_imaging_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Standard workflow: Convert → Calibrate → Image.
    
    Args:
        config: Pipeline configuration
        
    Returns:
        PipelineOrchestrator for standard imaging workflow
    """
    # Lazy import to avoid circular dependencies
    from dsa110_contimg.pipeline import stages_impl
    
    # Default retry policy for transient failures
    retry_policy = RetryPolicy(
        max_attempts=2,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        initial_delay=5.0,
        max_delay=30.0,
    )
    
    return (WorkflowBuilder()
        .add_stage(
            "convert",
            stages_impl.ConversionStage(config),
            retry_policy=retry_policy,
        )
        .add_stage(
            "calibrate",
            stages_impl.CalibrationStage(config),
            depends_on=["convert"],
            retry_policy=retry_policy,
        )
        .add_stage(
            "image",
            stages_impl.ImagingStage(config),
            depends_on=["calibrate"],
            retry_policy=retry_policy,
        )
        .build())


def quicklook_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Quicklook workflow: Convert → Image (no calibration).
    
    Args:
        config: Pipeline configuration
        
    Returns:
        PipelineOrchestrator for quicklook workflow
    """
    from dsa110_contimg.pipeline import stages_impl
    
    return (WorkflowBuilder()
        .add_stage("convert", stages_impl.ConversionStage(config))
        .add_stage("image", stages_impl.ImagingStage(config), depends_on=["convert"])
        .build())


def reprocessing_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Reprocessing workflow: Calibrate → Image (MS already exists).
    
    Args:
        config: Pipeline configuration
        
    Returns:
        PipelineOrchestrator for reprocessing workflow
    """
    from dsa110_contimg.pipeline import stages_impl
    
    return (WorkflowBuilder()
        .add_stage("calibrate", stages_impl.CalibrationStage(config))
        .add_stage("image", stages_impl.ImagingStage(config), depends_on=["calibrate"])
        .build())

