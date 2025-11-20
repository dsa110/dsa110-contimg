"""
Pipeline adapter for Absurd task execution.

This module provides the integration layer between the Absurd workflow
manager and the DSA-110 pipeline stages. It wraps existing pipeline
stages to execute as durable Absurd tasks.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import (
    AdaptivePhotometryStage,
    CalibrationSolveStage,
    CalibrationStage,
    CatalogSetupStage,
    ConversionStage,
    CrossMatchStage,
    ImagingStage,
    OrganizationStage,
    ValidationStage,
)

logger = logging.getLogger(__name__)


async def execute_pipeline_task(task_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a pipeline task via Absurd.

    This is the main entry point for Absurd task execution. It routes
    task_name to the appropriate executor function.

    Args:
        task_name: Task type to execute. Supported tasks:
            - "convert-uvh5-to-ms": Convert UVH5 to Measurement Set
            - "calibration-solve": Solve calibration solutions
            - "calibration-apply": Apply calibration to MS
            - "imaging": Create images from calibrated MS
        params: Task parameters specific to the task type.
            Common keys:
                - config: PipelineConfig dict or path to config file
                - inputs: Task-specific input parameters
                - priority: Task priority (optional)

    Returns:
        Task result dict with keys:
            - status: "success" or "error"
            - outputs: Stage-specific result data
            - message: Human-readable status message
            - errors: List of error messages (if status == "error")

    Raises:
        ValueError: If task_name is unknown

    Example:
        >>> result = await execute_pipeline_task(
        ...     "convert-uvh5-to-ms",
        ...     {
        ...         "config": {"paths": {...}},
        ...         "inputs": {
        ...             "input_path": "/data/obs.hdf5",
        ...             "start_time": "2025-01-01T00:00:00",
        ...             "end_time": "2025-01-01T01:00:00"
        ...         }
        ...     }
        ... )
        >>> print(result["status"])
        "success"
    """
    logger.info(f"Executing Absurd task: {task_name}")

    # Route to appropriate executor
    if task_name == "convert-uvh5-to-ms":
        return await execute_conversion(params)
    elif task_name == "calibration-solve":
        return await execute_calibration_solve(params)
    elif task_name == "calibration-apply":
        return await execute_calibration_apply(params)
    elif task_name == "imaging":
        return await execute_imaging(params)
    elif task_name == "validation":
        return await execute_validation(params)
    elif task_name == "crossmatch":
        return await execute_crossmatch(params)
    elif task_name == "photometry":
        return await execute_photometry(params)
    elif task_name == "catalog-setup":
        return await execute_catalog_setup(params)
    elif task_name == "organize-files":
        return await execute_organize_files(params)
    else:
        raise ValueError(
            f"Unknown task name: '{task_name}'. Supported tasks: "
            f"convert-uvh5-to-ms, calibration-solve, calibration-apply, "
            f"imaging, validation, crossmatch, photometry, catalog-setup, "
            f"organize-files"
        )


async def execute_conversion(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute UVH5 to MS conversion.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict with:
                - input_path: Path to UVH5 file
                - start_time: Start time (ISO format)
                - end_time: End time (ISO format)

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with ms_path, ms_groups, etc.
            - message: Status message
            - errors: Error list (if failed)

    Example:
        >>> result = await execute_conversion({
        ...     "config": config_dict,
        ...     "inputs": {
        ...         "input_path": "/data/obs.hdf5",
        ...         "start_time": "2025-01-01T00:00:00",
        ...         "end_time": "2025-01-01T01:00:00"
        ...     }
        ... })
    """
    logger.info("[Absurd] Starting UVH5 → MS conversion")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})

        # Validate required inputs
        required = ["input_path", "start_time", "end_time"]
        missing = [k for k in required if k not in inputs]
        if missing:
            return {
                "status": "error",
                "message": f"Missing required inputs: {missing}",
                "errors": [f"Missing: {m}" for m in missing],
            }

        # Create pipeline context
        context = PipelineContext(config=config, inputs=inputs)

        # Initialize stage
        stage = ConversionStage(config)

        # Validate prerequisites
        is_valid, error = stage.validate(context)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Validation failed: {error}",
                "errors": [error],
            }

        # Execute in thread pool (CASA requires blocking I/O)
        logger.info("[Absurd] Executing conversion stage...")
        result_context = await asyncio.to_thread(stage.execute, context)

        ms_path = result_context.outputs.get("ms_path")
        logger.info(f"[Absurd] Conversion complete: {ms_path}")

        return {
            "status": "success",
            "outputs": result_context.outputs,
            "message": "Conversion completed successfully",
        }

    except Exception as e:
        logger.exception(f"[Absurd] Conversion failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_calibration_solve(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute calibration solution solving.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict with:
                - ms_path: Path to MS (or in outputs from previous stage)

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with calibration_tables (K, BP, G, etc.)
            - message: Status message
            - errors: Error list (if failed)

    Example:
        >>> result = await execute_calibration_solve({
        ...     "config": config_dict,
        ...     "inputs": {},
        ...     "outputs": {"ms_path": "/data/obs.ms"}
        ... })
    """
    logger.info("[Absurd] Starting calibration solve")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})
        outputs = params.get("outputs", {})

        # MS path can be in inputs or outputs
        ms_path = inputs.get("ms_path") or outputs.get("ms_path")
        if not ms_path:
            return {
                "status": "error",
                "message": "Missing required input: ms_path",
                "errors": ["ms_path not found in inputs or outputs"],
            }

        # Create pipeline context with ms_path in outputs
        context = PipelineContext(config=config, inputs=inputs, outputs={"ms_path": ms_path})

        # Initialize stage
        stage = CalibrationSolveStage(config)

        # Validate prerequisites
        is_valid, error = stage.validate(context)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Validation failed: {error}",
                "errors": [error],
            }

        # Execute in thread pool (CASA requires blocking I/O)
        logger.info(f"[Absurd] Solving calibration for: {ms_path}")
        result_context = await asyncio.to_thread(stage.execute, context)

        cal_tables = result_context.outputs.get("calibration_tables", {})
        table_names = list(cal_tables.keys())
        logger.info(f"[Absurd] Calibration solve complete. " f"Generated tables: {table_names}")

        msg = f"Calibration solved successfully ({len(cal_tables)} tables)"
        return {
            "status": "success",
            "outputs": result_context.outputs,
            "message": msg,
        }

    except Exception as e:
        logger.exception(f"[Absurd] Calibration solve failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_calibration_apply(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute calibration application to MS.

        Args:
            params: Must contain:
                - config: PipelineConfig dict or path
                - inputs: Dict (optional)
                             - outputs: Dict with:
                     - ms_path: Path to MS
                     - calibration_tables: Cal table paths dict

        Returns:
            Result dict with:
                - status: "success" or "error"
                - outputs: Dict with ms_path (calibrated)
                - message: Status message
                - errors: Error list (if failed)

        Example:
            >>> result = await execute_calibration_apply({
            ...     "config": config_dict,
            ...     "outputs": {
            ...         "ms_path": "/data/obs.ms",
    ...         "calibration_tables": {"K": "/cal/K.cal"}
            ...     }
            ... })
    """
    logger.info("[Absurd] Starting calibration apply")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})
        outputs = params.get("outputs", {})

        # Validate required outputs
        ms_path = outputs.get("ms_path")
        cal_tables = outputs.get("calibration_tables")

        if not ms_path:
            return {
                "status": "error",
                "message": "Missing required output: ms_path",
                "errors": ["ms_path not found in outputs"],
            }

        if not cal_tables:
            return {
                "status": "error",
                "message": "Missing required output: calibration_tables",
                "errors": ["calibration_tables not found in outputs"],
            }

        # Create pipeline context
        context = PipelineContext(
            config=config,
            inputs=inputs,
            outputs={"ms_path": ms_path, "calibration_tables": cal_tables},
        )

        # Initialize stage
        stage = CalibrationStage(config)

        # Validate prerequisites
        is_valid, error = stage.validate(context)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Validation failed: {error}",
                "errors": [error],
            }

        # Execute in thread pool (CASA requires blocking I/O)
        table_names = list(cal_tables.keys())
        logger.info(f"[Absurd] Applying calibration to: {ms_path} " f"(tables: {table_names})")
        result_context = await asyncio.to_thread(stage.execute, context)

        logger.info(f"[Absurd] Calibration applied successfully to: {ms_path}")

        return {
            "status": "success",
            "outputs": result_context.outputs,
            "message": "Calibration applied successfully",
        }

    except Exception as e:
        logger.exception(f"[Absurd] Calibration apply failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_imaging(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute imaging from calibrated MS.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict (optional)
            - outputs: Dict with:
                - ms_path: Path to calibrated MS

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with image_path, image_metadata, etc.
            - message: Status message
            - errors: Error list (if failed)

    Example:
        >>> result = await execute_imaging({
        ...     "config": config_dict,
        ...     "outputs": {"ms_path": "/data/calibrated.ms"}
        ... })
    """
    logger.info("[Absurd] Starting imaging")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})
        outputs = params.get("outputs", {})

        # MS path must be in outputs
        ms_path = outputs.get("ms_path")
        if not ms_path:
            return {
                "status": "error",
                "message": "Missing required output: ms_path",
                "errors": ["ms_path not found in outputs"],
            }

        # Create pipeline context
        context = PipelineContext(config=config, inputs=inputs, outputs={"ms_path": ms_path})

        # Initialize stage
        stage = ImagingStage(config)

        # Validate prerequisites
        is_valid, error = stage.validate(context)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Validation failed: {error}",
                "errors": [error],
            }

        # Execute in thread pool (CASA requires blocking I/O)
        logger.info(f"[Absurd] Creating image from: {ms_path}")
        result_context = await asyncio.to_thread(stage.execute, context)

        image_path = result_context.outputs.get("image_path")
        logger.info(f"[Absurd] Imaging complete: {image_path}")

        return {
            "status": "success",
            "outputs": result_context.outputs,
            "message": "Imaging completed successfully",
        }

    except Exception as e:
        logger.exception(f"[Absurd] Imaging failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_validation(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute image validation.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict (optional)
            - outputs: Dict with:
                - image_path: Path to FITS image

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with validation_results
            - message: Status message
            - errors: Error list (if failed)

    Example:
        >>> result = await execute_validation({
        ...     "config": config_dict,
        ...     "outputs": {"image_path": "/data/image.fits"}
        ... })
    """
    logger.info("[Absurd] Starting image validation")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})
        outputs = params.get("outputs", {})

        # image_path must be in outputs
        image_path = outputs.get("image_path")
        if not image_path:
            return {
                "status": "error",
                "message": "Missing required output: image_path",
                "errors": ["image_path not found in outputs"],
            }

        # Create pipeline context
        context = PipelineContext(config=config, inputs=inputs, outputs={"image_path": image_path})

        # Initialize stage
        stage = ValidationStage(config)

        # Validate prerequisites
        is_valid, error = stage.validate(context)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Validation failed: {error}",
                "errors": [error],
            }

        # Execute in thread pool
        logger.info(f"[Absurd] Validating image: {image_path}")
        result_context = await asyncio.to_thread(stage.execute, context)

        validation_results = result_context.outputs.get("validation_results", {})
        val_status = validation_results.get("status", "unknown")
        logger.info(f"[Absurd] Validation complete: {image_path} " f"(status: {val_status})")

        msg = f"Validation completed with status: {val_status}"
        return {
            "status": "success",
            "outputs": result_context.outputs,
            "message": msg,
        }

    except Exception as e:
        logger.exception(f"[Absurd] Validation failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_crossmatch(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute source cross-matching.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict (optional)
            - outputs: Dict with:
                - image_path: Path to image (OR)
                - detected_sources: DataFrame of detected sources

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with crossmatch_results
            - message: Status message
            - errors: Error list (if failed)

    Example:
        >>> result = await execute_crossmatch({
        ...     "config": config_dict,
        ...     "outputs": {"image_path": "/data/image.fits"}
        ... })
    """
    logger.info("[Absurd] Starting source cross-matching")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})
        outputs = params.get("outputs", {})

        # Either image_path or detected_sources must be present
        image_path = outputs.get("image_path")
        detected_sources = outputs.get("detected_sources")

        if not image_path and detected_sources is None:
            return {
                "status": "error",
                "message": ("Missing required output: " "image_path or detected_sources"),
                "errors": ["Neither image_path nor detected_sources " "found in outputs"],
            }

        # Create pipeline context
        context_outputs = {}
        if image_path:
            context_outputs["image_path"] = image_path
        if detected_sources is not None:
            context_outputs["detected_sources"] = detected_sources

        context = PipelineContext(config=config, inputs=inputs, outputs=context_outputs)

        # Initialize stage
        stage = CrossMatchStage(config)

        # Validate prerequisites
        is_valid, error = stage.validate(context)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Validation failed: {error}",
                "errors": [error],
            }

        # Execute in thread pool
        source_info = (
            f"image_path={image_path}"
            if image_path
            else f"detected_sources ({len(detected_sources)} sources)"
        )
        logger.info(f"[Absurd] Cross-matching: {source_info}")
        result_context = await asyncio.to_thread(stage.execute, context)

        crossmatch_results = result_context.outputs.get("crossmatch_results", {})
        num_matches = len(crossmatch_results.get("matches", []))
        logger.info(f"[Absurd] Cross-match complete: {num_matches} matches found")

        msg = f"Cross-matching completed: {num_matches} matches"
        return {
            "status": "success",
            "outputs": result_context.outputs,
            "message": msg,
        }

    except Exception as e:
        logger.exception(f"[Absurd] Cross-match failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_photometry(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute adaptive binning photometry.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict (optional)
            - outputs: Dict with:
                - ms_path: Path to calibrated MS
                - image_path: Path to image (optional)

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with photometry_results (DataFrame)
            - message: Status message
            - errors: Error list (if failed)

    Example:
        >>> result = await execute_photometry({
        ...     "config": config_dict,
        ...     "outputs": {
        ...         "ms_path": "/data/calibrated.ms",
        ...         "image_path": "/data/image.fits"
        ...     }
        ... })
    """
    logger.info("[Absurd] Starting adaptive photometry")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})
        outputs = params.get("outputs", {})

        # ms_path must be in outputs
        ms_path = outputs.get("ms_path")
        if not ms_path:
            return {
                "status": "error",
                "message": "Missing required output: ms_path",
                "errors": ["ms_path not found in outputs"],
            }

        # image_path is optional
        image_path = outputs.get("image_path")

        # Create pipeline context
        context_outputs = {"ms_path": ms_path}
        if image_path:
            context_outputs["image_path"] = image_path

        context = PipelineContext(config=config, inputs=inputs, outputs=context_outputs)

        # Initialize stage
        stage = AdaptivePhotometryStage(config)

        # Validate prerequisites
        is_valid, error = stage.validate(context)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Validation failed: {error}",
                "errors": [error],
            }

        # Execute in thread pool
        logger.info(f"[Absurd] Running photometry on: {ms_path}")
        if image_path:
            logger.info(f"[Absurd] Using image for source detection: {image_path}")
        result_context = await asyncio.to_thread(stage.execute, context)

        photometry_results = result_context.outputs.get("photometry_results")
        num_sources = len(photometry_results) if photometry_results is not None else 0
        logger.info(f"[Absurd] Photometry complete: {num_sources} sources measured")

        msg = f"Photometry completed: {num_sources} sources"
        return {
            "status": "success",
            "outputs": result_context.outputs,
            "message": msg,
        }

    except Exception as e:
        logger.exception(f"[Absurd] Photometry failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_catalog_setup(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute catalog setup for observation declination.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict with:
                - input_path: Path to HDF5 observation file
            - outputs: Dict (optional)

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with catalog_setup_status
            - message: Status message
            - errors: Error list (if failed)

    Example:
        >>> result = await execute_catalog_setup({
        ...     "config": config_dict,
        ...     "inputs": {"input_path": "/data/observation.hdf5"}
        ... })
    """
    logger.info("[Absurd] Starting catalog setup")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})
        outputs = params.get("outputs", {})

        # input_path must be in inputs
        input_path = inputs.get("input_path")
        if not input_path:
            return {
                "status": "error",
                "message": "Missing required input: input_path",
                "errors": ["input_path not found in inputs"],
            }

        # Create pipeline context
        context = PipelineContext(config=config, inputs={"input_path": input_path}, outputs=outputs)

        # Initialize stage
        stage = CatalogSetupStage(config)

        # Validate prerequisites
        is_valid, error = stage.validate(context)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Validation failed: {error}",
                "errors": [error],
            }

        # Execute in thread pool
        logger.info(f"[Absurd] Setting up catalogs for: {input_path}")
        result_context = await asyncio.to_thread(stage.execute, context)

        catalog_status = result_context.outputs.get("catalog_setup_status", "unknown")
        logger.info(f"[Absurd] Catalog setup complete: {catalog_status}")

        msg = f"Catalog setup completed with status: {catalog_status}"
        return {
            "status": "success",
            "outputs": result_context.outputs,
            "message": msg,
        }

    except Exception as e:
        logger.exception(f"[Absurd] Catalog setup failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_organize_files(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute file organization for MS files.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict (optional)
            - outputs: Dict with:
                - ms_path: Path to MS file (OR)
                - ms_paths: List of MS file paths

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with organized ms_path/ms_paths
            - message: Status message
            - errors: Error list (if failed)

    Example:
        >>> result = await execute_organize_files({
        ...     "config": config_dict,
        ...     "outputs": {"ms_path": "/data/raw/obs.ms"}
        ... })
    """
    logger.info("[Absurd] Starting file organization")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})
        outputs = params.get("outputs", {})

        # Either ms_path or ms_paths must be in outputs
        ms_path = outputs.get("ms_path")
        ms_paths = outputs.get("ms_paths")

        if not ms_path and not ms_paths:
            return {
                "status": "error",
                "message": "Missing required output: ms_path or ms_paths",
                "errors": ["Neither ms_path nor ms_paths found in outputs"],
            }

        # Create pipeline context
        context_outputs = {}
        if ms_path:
            context_outputs["ms_path"] = ms_path
        if ms_paths:
            context_outputs["ms_paths"] = ms_paths

        context = PipelineContext(config=config, inputs=inputs, outputs=context_outputs)

        # Initialize stage
        stage = OrganizationStage(config)

        # Validate prerequisites
        is_valid, error = stage.validate(context)
        if not is_valid:
            return {
                "status": "error",
                "message": f"Validation failed: {error}",
                "errors": [error],
            }

        # Execute in thread pool
        if ms_path:
            logger.info(f"[Absurd] Organizing file: {ms_path}")
        else:
            logger.info(f"[Absurd] Organizing {len(ms_paths)} files")
        result_context = await asyncio.to_thread(stage.execute, context)

        # Get organized paths
        organized_path = result_context.outputs.get("ms_path")
        organized_paths = result_context.outputs.get("ms_paths")

        if organized_path:
            logger.info(f"[Absurd] File organized: {organized_path}")
            msg = f"File organized successfully"
        else:
            logger.info(f"[Absurd] {len(organized_paths)} files organized")
            msg = f"{len(organized_paths)} files organized successfully"

        return {
            "status": "success",
            "outputs": result_context.outputs,
            "message": msg,
        }

    except Exception as e:
        logger.exception(f"[Absurd] File organization failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


# ============================================================================
# Helper Functions
# ============================================================================


def _load_config(config_param: Any) -> PipelineConfig:
    """Load PipelineConfig from various formats.

    Args:
        config_param: Can be:
            - PipelineConfig instance (returned as-is)
            - Dict (converted to PipelineConfig)
            - str/Path (loaded from YAML file)
            - None (loads default config)

    Returns:
        PipelineConfig instance

    Raises:
        ValueError: If config cannot be loaded
    """
    if isinstance(config_param, PipelineConfig):
        return config_param

    if isinstance(config_param, dict):
        return PipelineConfig(**config_param)

    if isinstance(config_param, (str, Path)):
        return PipelineConfig.from_yaml(config_param)

    if config_param is None:
        # Load default config from environment
        config = PipelineConfig.from_env()
        # Enable Phase 3 features
        config.transient_detection.enabled = True
        config.astrometric_calibration.enabled = True
        return config

    raise ValueError(f"Invalid config parameter type: {type(config_param)}")
