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
        self.stages.append(
            StageDefinition(
                name=name,
                stage=stage,
                dependencies=depends_on or [],
                retry_policy=retry_policy,
                timeout=timeout,
            )
        )
        return self

    def build(self) -> PipelineOrchestrator:
        """Build pipeline orchestrator.

        Returns:
            PipelineOrchestrator instance
        """
        return PipelineOrchestrator(self.stages)


def standard_imaging_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Standard workflow: Convert → Solve Calibration → Apply Calibration → Image.

    This workflow performs a complete end-to-end pipeline:
    1. Convert UVH5 files to Measurement Sets
    2. Solve calibration tables (delay/K, bandpass/BP, gains/G)
    3. Apply calibration solutions to the MS
    4. Image the calibrated MS

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

    builder = (
        WorkflowBuilder()
        .add_stage(
            "catalog_setup",
            stages_impl.CatalogSetupStage(config),
            retry_policy=retry_policy,
        )
        .add_stage(
            "convert",
            stages_impl.ConversionStage(config),
            depends_on=["catalog_setup"],
            retry_policy=retry_policy,
        )
        .add_stage(
            "calibrate_solve",
            stages_impl.CalibrationSolveStage(config),
            depends_on=["convert"],
            retry_policy=retry_policy,
        )
        .add_stage(
            "calibrate_apply",
            stages_impl.CalibrationStage(config),
            depends_on=["calibrate_solve"],
            retry_policy=retry_policy,
        )
        .add_stage(
            "image",
            stages_impl.ImagingStage(config),
            depends_on=["calibrate_apply"],
            retry_policy=retry_policy,
        )
    )

    # Add validation stage if enabled
    if config.validation.enabled:
        builder = builder        .add_stage(
            "validate",
            stages_impl.ValidationStage(config),
            depends_on=["image"],
            retry_policy=retry_policy,
        )

    # Add cross-match stage if enabled
    if config.crossmatch.enabled:
        builder = builder.add_stage(
            "crossmatch",
            stages_impl.CrossMatchStage(config),
            depends_on=["validate", "image"],
            retry_policy=retry_policy,
        )

    # Add adaptive photometry stage if enabled
    if config.photometry.enabled:
        builder = builder.add_stage(
            "adaptive_photometry",
            stages_impl.AdaptivePhotometryStage(config),
            depends_on=["image"],
            retry_policy=retry_policy,
        )

    return builder.build()


def quicklook_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Quicklook workflow: Convert → Image (no calibration).

    Args:
        config: Pipeline configuration

    Returns:
        PipelineOrchestrator for quicklook workflow
    """
    from dsa110_contimg.pipeline import stages_impl

    builder = (
        WorkflowBuilder()
        .add_stage("catalog_setup", stages_impl.CatalogSetupStage(config))
        .add_stage("convert", stages_impl.ConversionStage(config), depends_on=["catalog_setup"])
        .add_stage("image", stages_impl.ImagingStage(config), depends_on=["convert"])
    )

    # Add validation stage if enabled
    if config.validation.enabled:
        builder = builder        .add_stage(
            "validate",
            stages_impl.ValidationStage(config),
            depends_on=["image"],
        )

    # Add cross-match stage if enabled
    if config.crossmatch.enabled:
        builder = builder.add_stage(
            "crossmatch",
            stages_impl.CrossMatchStage(config),
            depends_on=["validate", "image"],
        )

    return builder.build()


def reprocessing_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Reprocessing workflow: Calibrate → Image (MS already exists).

    Args:
        config: Pipeline configuration

    Returns:
        PipelineOrchestrator for reprocessing workflow
    """
    from dsa110_contimg.pipeline import stages_impl

    builder = (
        WorkflowBuilder()
        .add_stage("catalog_setup", stages_impl.CatalogSetupStage(config))
        .add_stage("calibrate", stages_impl.CalibrationStage(config), depends_on=["catalog_setup"])
        .add_stage("image", stages_impl.ImagingStage(config), depends_on=["calibrate"])
    )

    # Add validation stage if enabled
    if config.validation.enabled:
        builder = builder.add_stage(
            "validate",
            stages_impl.ValidationStage(config),
            depends_on=["image"],
        )

    # Add cross-match stage if enabled
    if config.crossmatch.enabled:
        builder = builder.add_stage(
            "crossmatch",
            stages_impl.CrossMatchStage(config),
            depends_on=["validate", "image"],
        )

    return builder.build()
