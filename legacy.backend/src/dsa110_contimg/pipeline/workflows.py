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

    # Add mosaic stage if enabled
    if config.mosaic.enabled:
        builder = builder.add_stage(
            "mosaic",
            stages_impl.MosaicStage(config),
            depends_on=["image"],
            retry_policy=retry_policy,
        )

    # Add validation stage if enabled
    if config.validation.enabled:
        depends_on = ["mosaic"] if config.mosaic.enabled else ["image"]
        builder = builder.add_stage(
            "validate",
            stages_impl.ValidationStage(config),
            depends_on=depends_on,
            retry_policy=retry_policy,
        )

    # Add cross-match stage if enabled
    if config.crossmatch.enabled:
        depends_on = ["validate"] if config.validation.enabled else ["image"]
        if config.mosaic.enabled:
            depends_on = ["validate", "mosaic"] if config.validation.enabled else ["mosaic"]
        builder = builder.add_stage(
            "crossmatch",
            stages_impl.CrossMatchStage(config),
            depends_on=depends_on,
            retry_policy=retry_policy,
        )

    # Add adaptive photometry stage if enabled
    if config.photometry.enabled:
        depends_on = ["mosaic"] if config.mosaic.enabled else ["image"]
        builder = builder.add_stage(
            "adaptive_photometry",
            stages_impl.AdaptivePhotometryStage(config),
            depends_on=depends_on,
            retry_policy=retry_policy,
        )

    # Add light curve stage if enabled (requires photometry)
    if config.light_curve.enabled and config.photometry.enabled:
        depends_on = ["adaptive_photometry"]
        if config.mosaic.enabled:
            depends_on.append("mosaic")
        builder = builder.add_stage(
            "light_curve",
            stages_impl.LightCurveStage(config),
            depends_on=depends_on,
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
        .add_stage(
            "calibrate",
            stages_impl.CalibrationStage(config),
            depends_on=["catalog_setup"],
        )
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


def streaming_workflow(config: PipelineConfig) -> PipelineOrchestrator:
    """Complete streaming end-to-end workflow.

    Full chain: CatalogSetup → Conversion → CalibrationSolve → CalibrationApply
                → Imaging → Mosaic → AdaptivePhotometry → LightCurve → TransientDetection

    This workflow implements the complete data path from HDF5 ingestion through
    light curve generation as described in the project goals. Stages are
    conditionally included based on configuration flags.

    Args:
        config: Pipeline configuration

    Returns:
        PipelineOrchestrator for complete streaming workflow

    Example:
        >>> config = PipelineConfig(
        ...     mosaic=MosaicConfig(enabled=True),
        ...     photometry=PhotometryConfig(enabled=True),
        ...     light_curve=LightCurveConfig(enabled=True),
        ...     transient_detection=TransientDetectionConfig(enabled=True),
        ... )
        >>> workflow = streaming_workflow(config)
        >>> result = await workflow.execute(context)
    """
    from dsa110_contimg.pipeline import stages_impl

    # Default retry policy for transient failures
    retry_policy = RetryPolicy(
        max_attempts=3,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        initial_delay=5.0,
        max_delay=60.0,
    )

    # Core pipeline stages (always included)
    builder = (
        WorkflowBuilder()
        .add_stage(
            "catalog_setup",
            stages_impl.CatalogSetupStage(config),
            retry_policy=retry_policy,
            timeout=300.0,  # 5 minutes
        )
        .add_stage(
            "conversion",
            stages_impl.ConversionStage(config),
            depends_on=["catalog_setup"],
            retry_policy=retry_policy,
            timeout=1800.0,  # 30 minutes for large files
        )
        .add_stage(
            "calibration_solve",
            stages_impl.CalibrationSolveStage(config),
            depends_on=["conversion"],
            retry_policy=retry_policy,
            timeout=900.0,  # 15 minutes
        )
        .add_stage(
            "calibration_apply",
            stages_impl.CalibrationStage(config),
            depends_on=["calibration_solve"],
            retry_policy=retry_policy,
            timeout=600.0,  # 10 minutes
        )
        .add_stage(
            "imaging",
            stages_impl.ImagingStage(config),
            depends_on=["calibration_apply"],
            retry_policy=retry_policy,
            timeout=1800.0,  # 30 minutes
        )
    )

    # Track dependencies for downstream stages
    last_image_stage = "imaging"

    # Mosaic stage (optional, requires multiple images)
    if config.mosaic.enabled:
        builder = builder.add_stage(
            "mosaic",
            stages_impl.MosaicStage(config),
            depends_on=[last_image_stage],
            retry_policy=retry_policy,
            timeout=3600.0,  # 1 hour for large mosaics
        )
        last_image_stage = "mosaic"

    # Validation stage (optional)
    if config.validation.enabled:
        builder = builder.add_stage(
            "validation",
            stages_impl.ValidationStage(config),
            depends_on=[last_image_stage],
            retry_policy=retry_policy,
            timeout=300.0,
        )

    # Cross-match stage (optional)
    if config.crossmatch.enabled:
        crossmatch_deps = [last_image_stage]
        if config.validation.enabled:
            crossmatch_deps.append("validation")
        builder = builder.add_stage(
            "crossmatch",
            stages_impl.CrossMatchStage(config),
            depends_on=crossmatch_deps,
            retry_policy=retry_policy,
            timeout=600.0,
        )

    # Adaptive photometry stage (optional)
    if config.photometry.enabled:
        builder = builder.add_stage(
            "adaptive_photometry",
            stages_impl.AdaptivePhotometryStage(config),
            depends_on=[last_image_stage],
            retry_policy=retry_policy,
            timeout=1200.0,  # 20 minutes
        )

    # Light curve stage (requires photometry)
    if config.light_curve.enabled and config.photometry.enabled:
        light_curve_deps = ["adaptive_photometry"]
        if config.mosaic.enabled:
            light_curve_deps.append("mosaic")
        builder = builder.add_stage(
            "light_curve",
            stages_impl.LightCurveStage(config),
            depends_on=light_curve_deps,
            retry_policy=retry_policy,
            timeout=600.0,
        )

    # Transient detection stage (optional, requires photometry or light curves)
    if config.transient_detection.enabled:
        transient_deps = []
        if config.light_curve.enabled and config.photometry.enabled:
            transient_deps.append("light_curve")
        elif config.photometry.enabled:
            transient_deps.append("adaptive_photometry")
        else:
            transient_deps.append(last_image_stage)

        builder = builder.add_stage(
            "transient_detection",
            stages_impl.TransientDetectionStage(config),
            depends_on=transient_deps,
            retry_policy=retry_policy,
            timeout=300.0,
        )

    return builder.build()
