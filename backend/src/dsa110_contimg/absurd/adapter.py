"""
Pipeline adapter for Absurd task execution.

This module provides the integration layer between the Absurd workflow
manager and the DSA-110 pipeline stages. It wraps existing pipeline
stages to execute as durable Absurd tasks.

Phase 2 Integration Features:
- Task dependency chaining (conversion → calibration → imaging)
- Automatic follow-up task spawning
- Housekeeping task support
- Dead letter queue integration
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dsa110_contimg.absurd.client import AbsurdClient
from dsa110_contimg.absurd.config import AbsurdConfig
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
    elif task_name == "housekeeping":
        return await execute_housekeeping(params)
    elif task_name == "create-mosaic":
        return await execute_create_mosaic(params)
    else:
        raise ValueError(
            f"Unknown task name: '{task_name}'. Supported tasks: "
            f"convert-uvh5-to-ms, calibration-solve, calibration-apply, "
            f"imaging, validation, crossmatch, photometry, catalog-setup, "
            f"organize-files, housekeeping, create-mosaic"
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
            msg = "File organized successfully"
        elif organized_paths is not None:
            num_organized = len(organized_paths)
            logger.info(f"[Absurd] {num_organized} files organized")
            msg = f"{num_organized} files organized successfully"
        else:
            logger.warning("[Absurd] No organized paths returned")
            msg = "File organization completed (no paths returned)"

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


# ============================================================================
# Task Dependency Chain Support
# ============================================================================


@dataclass
class TaskChain:
    """Defines a sequence of dependent tasks.

    When a task completes successfully, the next task in the chain
    is automatically spawned with the outputs of the previous task.
    """

    name: str
    tasks: List[str]  # Ordered list of task names
    params_transform: Dict[str, Callable[[Dict], Dict]] = field(default_factory=dict)

    def get_next_task(self, current_task: str) -> Optional[str]:
        """Get the next task in the chain after the current one."""
        try:
            idx = self.tasks.index(current_task)
            if idx < len(self.tasks) - 1:
                return self.tasks[idx + 1]
        except ValueError:
            pass
        return None

    def transform_params(self, task_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Transform task result into params for the next task."""
        if task_name in self.params_transform:
            return self.params_transform[task_name](result)

        # Default: pass outputs as inputs for next task
        return {
            "config": result.get("config"),
            "inputs": result.get("inputs", {}),
            "outputs": result.get("outputs", {}),
        }


# Pre-defined task chains for common workflows
STANDARD_PIPELINE_CHAIN = TaskChain(
    name="standard-pipeline",
    tasks=[
        "catalog-setup",
        "convert-uvh5-to-ms",
        "calibration-solve",
        "calibration-apply",
        "imaging",
        "validation",
        "crossmatch",
        "photometry",
    ],
)

QUICK_IMAGING_CHAIN = TaskChain(
    name="quick-imaging",
    tasks=[
        "convert-uvh5-to-ms",
        "calibration-apply",  # Use existing calibration
        "imaging",
    ],
)

CALIBRATOR_CHAIN = TaskChain(
    name="calibrator-processing",
    tasks=[
        "catalog-setup",
        "convert-uvh5-to-ms",
        "calibration-solve",
    ],
)

TARGET_CHAIN = TaskChain(
    name="target-processing",
    tasks=[
        "convert-uvh5-to-ms",
        "calibration-apply",
        "imaging",
        "validation",
        "photometry",
    ],
)

# Registry of available chains
TASK_CHAINS = {
    "standard-pipeline": STANDARD_PIPELINE_CHAIN,
    "quick-imaging": QUICK_IMAGING_CHAIN,
    "calibrator": CALIBRATOR_CHAIN,
    "target": TARGET_CHAIN,
}


async def execute_chained_task(
    task_name: str,
    params: Dict[str, Any],
    chain_name: Optional[str] = None,
    spawn_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Execute a task and optionally spawn the next task in a chain.

    Args:
        task_name: The task to execute
        params: Task parameters
        chain_name: Name of the task chain to follow (None = no chaining)
        spawn_callback: Async callback to spawn next task: spawn_callback(task_name, params)

    Returns:
        Task result with chain_next_task if applicable
    """
    # Execute the current task
    result = await execute_pipeline_task(task_name, params)

    # If successful and part of a chain, determine next task
    if result.get("status") == "success" and chain_name and spawn_callback:
        chain = TASK_CHAINS.get(chain_name)
        if chain:
            next_task = chain.get_next_task(task_name)
            if next_task:
                # Transform params for next task
                next_params = chain.transform_params(
                    task_name,
                    {
                        "config": params.get("config"),
                        "inputs": params.get("inputs", {}),
                        "outputs": result.get("outputs", {}),
                    },
                )
                next_params["chain_name"] = chain_name

                # Spawn next task
                try:
                    next_task_id = await spawn_callback(next_task, next_params)
                    result["chain_next_task"] = next_task
                    result["chain_next_task_id"] = next_task_id
                    logger.info(
                        f"[Absurd] Chain '{chain_name}': Spawned {next_task} "
                        f"(task_id={next_task_id})"
                    )
                except Exception as e:
                    logger.error(f"[Absurd] Failed to spawn next task in chain: {e}")
                    result["chain_spawn_error"] = str(e)

    return result


# ============================================================================
# Housekeeping Task
# ============================================================================


async def execute_housekeeping(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute housekeeping operations.

    Cleans up stale files, recovers stuck groups, and maintains system health.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict with optional:
                - max_stale_hours: Hours before considering a task stale (default: 4)
                - clean_scratch: Whether to clean scratch directories (default: True)
                - recover_stuck: Whether to recover stuck queue items (default: True)
                - prune_completed: Whether to prune old completed tasks (default: False)
                - completed_retention_days: Days to keep completed tasks (default: 7)

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with housekeeping statistics
            - message: Status message
            - errors: Error list (if failed)
    """
    logger.info("[Absurd] Starting housekeeping")

    try:
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})

        max_stale_hours = inputs.get("max_stale_hours", 4)
        clean_scratch = inputs.get("clean_scratch", True)
        recover_stuck = inputs.get("recover_stuck", True)
        prune_completed = inputs.get("prune_completed", False)
        completed_retention_days = inputs.get("completed_retention_days", 7)

        stats = {
            "scratch_dirs_cleaned": 0,
            "scratch_bytes_freed": 0,
            "stuck_groups_recovered": 0,
            "completed_tasks_pruned": 0,
            "errors": [],
        }

        # Clean scratch directories
        if clean_scratch:
            scratch_stats = await _clean_scratch_directories(config, max_stale_hours)
            stats["scratch_dirs_cleaned"] = scratch_stats.get("dirs_cleaned", 0)
            stats["scratch_bytes_freed"] = scratch_stats.get("bytes_freed", 0)

        # Recover stuck queue items
        if recover_stuck:
            recovered = await _recover_stuck_groups(config, max_stale_hours)
            stats["stuck_groups_recovered"] = recovered

        # Prune old completed tasks (if enabled)
        if prune_completed:
            try:
                pruned = await _prune_completed_tasks(config, completed_retention_days)
                stats["completed_tasks_pruned"] = pruned
            except Exception as e:
                logger.warning(f"[Housekeeping] Failed to prune completed tasks: {e}")
                stats["errors"].append(str(e))

        logger.info(
            f"[Absurd] Housekeeping complete: "
            f"{stats['scratch_dirs_cleaned']} dirs cleaned, "
            f"{stats['stuck_groups_recovered']} groups recovered"
        )

        return {
            "status": "success",
            "outputs": stats,
            "message": "Housekeeping completed successfully",
        }

    except Exception as e:
        logger.exception(f"[Absurd] Housekeeping failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def _clean_scratch_directories(
    config: PipelineConfig, max_stale_hours: float
) -> Dict[str, int]:
    """Clean up stale scratch directories."""
    stats = {"dirs_cleaned": 0, "bytes_freed": 0}

    scratch_dir = Path(os.environ.get("CONTIMG_SCRATCH_DIR", "/stage/dsa110-contimg"))
    if not scratch_dir.exists():
        return stats

    cutoff_time = time.time() - (max_stale_hours * 3600)

    # Look for stream_* temporary directories
    patterns = ["stream_*", "tmp_*", "*.staged.ms"]

    for pattern in patterns:
        for path in scratch_dir.glob(pattern):
            try:
                mtime = path.stat().st_mtime
                if mtime < cutoff_time:
                    if path.is_dir():
                        # Calculate size before deletion
                        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                        shutil.rmtree(path)
                        stats["bytes_freed"] += size
                    else:
                        stats["bytes_freed"] += path.stat().st_size
                        path.unlink()
                    stats["dirs_cleaned"] += 1
                    logger.debug(f"[Housekeeping] Cleaned stale: {path}")
            except Exception as e:
                logger.warning(f"[Housekeeping] Failed to clean {path}: {e}")

    return stats


async def _recover_stuck_groups(config: PipelineConfig, max_stale_hours: float) -> int:
    """Recover stuck queue groups back to pending state."""
    import sqlite3

    # Unified database path (Phase 2 consolidation)
    queue_db = Path(os.environ.get("PIPELINE_DB", "state/db/pipeline.sqlite3"))
    if not queue_db.exists():
        return 0

    recovered = 0
    cutoff_time = time.time() - (max_stale_hours * 3600)

    try:
        conn = sqlite3.connect(str(queue_db), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")

        # Find stuck in_progress groups
        cursor = conn.execute(
            """
            SELECT group_id FROM ingest_queue
            WHERE state = 'in_progress' AND last_update < ?
            """,
            (cutoff_time,),
        )
        stuck_groups = [row[0] for row in cursor.fetchall()]

        # Reset them to pending
        for group_id in stuck_groups:
            conn.execute(
                """
                UPDATE ingest_queue
                SET state = 'pending', 
                    last_update = ?,
                    error = 'Recovered by housekeeping (was stuck)'
                WHERE group_id = ?
                """,
                (time.time(), group_id),
            )
            recovered += 1
            logger.info(f"[Housekeeping] Recovered stuck group: {group_id}")

        conn.commit()
        conn.close()

    except Exception as e:
        logger.warning(f"[Housekeeping] Failed to recover stuck groups: {e}")

    return recovered


async def _prune_completed_tasks(config: PipelineConfig, retention_days: int) -> int:
    """Prune old completed tasks from Absurd queue."""
    absurd_cfg = AbsurdConfig.from_env()
    if not absurd_cfg.enabled:
        logger.info("[Housekeeping] Absurd disabled, skipping task prune")
        return 0

    client = AbsurdClient(absurd_cfg.database_url)
    async with client:
        return await client.prune_tasks(
            retention_days=retention_days,
            queue_name=absurd_cfg.queue_name,
            statuses=["completed", "failed", "cancelled"],
        )


async def execute_create_mosaic(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute mosaic creation from a group of images.

    This task combines multiple drift-scan images into a single mosaic
    using primary beam weighting for optimal sensitivity.

    Args:
        params: Must contain:
            - config: PipelineConfig dict or path
            - inputs: Dict with:
                - group_id: Group identifier for the observation
                - image_paths: Optional list of image paths (auto-discovered if not provided)
                - output_dir: Optional output directory for mosaic
                - center_ra_deg: Optional RA center override (degrees)
                - span_minutes: Optional time span (default: 50 minutes for 10 images)
                - enable_photometry: Whether to run photometry after mosaic (default: True)
                - photometry_config: Optional photometry configuration dict

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs: Dict with:
                - mosaic_path: Path to output mosaic FITS file
                - mosaic_metadata: Mosaic statistics and metrics
                - photometry_results: Photometry results if enabled
                - num_tiles: Number of images combined
            - message: Status message
            - errors: Error list (if failed)

    Example:
        >>> result = await execute_create_mosaic({
        ...     "config": config_dict,
        ...     "inputs": {
        ...         "group_id": "2025-06-01_12:00:00",
        ...         "enable_photometry": True
        ...     }
        ... })
    """
    logger.info("[Absurd] Starting mosaic creation")

    try:
        # Load configuration
        config = _load_config(params.get("config"))
        inputs = params.get("inputs", {})

        group_id = inputs.get("group_id")
        image_paths = inputs.get("image_paths")
        output_dir = inputs.get("output_dir")
        center_ra_deg = inputs.get("center_ra_deg")
        span_minutes = inputs.get("span_minutes", 50)
        enable_photometry = inputs.get("enable_photometry", True)
        photometry_config = inputs.get("photometry_config")

        if not group_id and not image_paths:
            return {
                "status": "error",
                "message": "Missing required input: group_id or image_paths",
                "errors": ["Either group_id or image_paths must be provided"],
            }

        # Import mosaic modules here to avoid circular imports
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        # Create orchestrator with configuration from environment
        products_db_path = config.paths.products_db if config.paths else None
        hdf5_db_path = config.paths.hdf5_db if config.paths else None

        orchestrator = MosaicOrchestrator(
            products_db_path=products_db_path,
            hdf5_db_path=hdf5_db_path,
            enable_photometry=enable_photometry,
            photometry_config=photometry_config,
        )

        # Execute mosaic creation in thread pool (involves heavy I/O)
        logger.info(f"[Absurd] Creating mosaic for group: {group_id}")

        if group_id:
            # Use orchestrator's group-based mosaic creation
            mosaic_result = await asyncio.to_thread(
                _create_mosaic_from_group,
                orchestrator,
                group_id,
                center_ra_deg,
                span_minutes,
            )
        else:
            # Use explicit image paths
            mosaic_result = await asyncio.to_thread(
                _create_mosaic_from_images,
                orchestrator,
                image_paths,
                output_dir,
            )

        if mosaic_result.get("error"):
            return {
                "status": "error",
                "message": mosaic_result["error"],
                "errors": [mosaic_result["error"]],
            }

        mosaic_path = mosaic_result.get("mosaic_path")
        logger.info(f"[Absurd] Mosaic creation complete: {mosaic_path}")

        return {
            "status": "success",
            "outputs": mosaic_result,
            "message": f"Mosaic created successfully: {mosaic_path}",
        }

    except Exception as e:
        logger.exception(f"[Absurd] Mosaic creation failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


def _create_mosaic_from_group(
    orchestrator: Any,
    group_id: str,
    center_ra_deg: Optional[float] = None,
    span_minutes: float = 50,
) -> Dict[str, Any]:
    """Helper to create mosaic from a group ID.

    Args:
        orchestrator: MosaicOrchestrator instance
        group_id: Group identifier
        center_ra_deg: Optional RA center override
        span_minutes: Time span in minutes

    Returns:
        Result dict with mosaic_path, metadata, etc.
    """
    try:
        # Check if orchestrator has a method for this
        if hasattr(orchestrator, "create_mosaic_for_group"):
            result = orchestrator.create_mosaic_for_group(
                group_id=group_id,
                center_ra_deg=center_ra_deg,
            )
            return {
                "mosaic_path": result.get("mosaic_path"),
                "mosaic_metadata": result.get("metadata", {}),
                "photometry_results": result.get("photometry"),
                "num_tiles": result.get("num_tiles", 0),
            }

        # Fallback: Use MosaicOrchestrator's process method
        # The orchestrator has all the required configuration
        if hasattr(orchestrator, "process_observation"):
            try:
                result = orchestrator.process_observation(
                    center_ra_deg=center_ra_deg,
                    group_id=group_id,
                )
                if result:
                    return {
                        "mosaic_path": result.get("mosaic_path"),
                        "mosaic_metadata": result.get("metadata", {}),
                        "photometry_results": result.get("photometry"),
                        "num_tiles": result.get("num_tiles", 0),
                    }
            except Exception as process_error:
                logger.warning(f"Orchestrator process failed: {process_error}")

        # Final fallback: Log error with context
        return {
            "error": f"Orchestrator does not support group-based mosaic creation for group {group_id}"
        }

    except Exception as e:
        logger.exception(f"Error creating mosaic for group {group_id}: {e}")
        return {"error": str(e)}


def _create_mosaic_from_images(
    orchestrator: Any,
    image_paths: List[str],
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to create mosaic from explicit image paths.

    Args:
        orchestrator: MosaicOrchestrator instance
        image_paths: List of image file paths
        output_dir: Optional output directory

    Returns:
        Result dict with mosaic_path, metadata, etc.
    """
    try:
        # Validate paths
        valid_paths = []
        for path in image_paths:
            p = Path(path)
            if p.exists():
                valid_paths.append(str(p))
            else:
                logger.warning(f"Image path not found: {path}")

        if len(valid_paths) < 2:
            return {"error": f"Need at least 2 valid images, found {len(valid_paths)}"}

        # Determine output path
        if output_dir:
            out_dir = Path(output_dir)
        else:
            out_dir = Path(valid_paths[0]).parent / "mosaics"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Generate output name from first image
        first_name = Path(valid_paths[0]).stem
        mosaic_name = f"mosaic_{first_name}_n{len(valid_paths)}.fits"
        mosaic_path = out_dir / mosaic_name

        # Try to use CASA linearmosaic via casatasks
        try:
            from casatasks import linearmosaic  # type: ignore[import-not-found]

            # Run linearmosaic with proper FITS output
            linearmosaic(
                images=valid_paths,
                outfile=str(mosaic_path).replace(".fits", ".image"),
                imageweights=[1.0] * len(valid_paths),
            )

            # Convert to FITS if needed
            if mosaic_path.suffix == ".fits":
                from casatasks import exportfits  # type: ignore[import-not-found]

                exportfits(
                    imagename=str(mosaic_path).replace(".fits", ".image"),
                    fitsimage=str(mosaic_path),
                    overwrite=True,
                )

            return {
                "mosaic_path": str(mosaic_path),
                "mosaic_metadata": {"method": "linearmosaic", "num_tiles": len(valid_paths)},
                "photometry_results": None,
                "num_tiles": len(valid_paths),
            }
        except ImportError:
            logger.warning("casatasks not available for mosaic creation")
            return {"error": "CASA tools not available for mosaic creation"}

    except Exception as e:
        logger.exception(f"Error creating mosaic from images: {e}")
        return {"error": str(e)}


# ============================================================================
# Streaming Converter Bridge
# ============================================================================


class AbsurdStreamingBridge:
    """Bridge between streaming converter and Absurd task queue.

    Instead of processing groups locally, this bridge submits discovered
    subband groups to Absurd for durable, distributed processing.
    """

    def __init__(
        self,
        absurd_client: Any,  # AbsurdClient
        queue_name: str = "dsa110-pipeline",
        chain_name: str = "standard-pipeline",
    ):
        self.client = absurd_client
        self.queue_name = queue_name
        self.chain_name = chain_name
        self._submitted_groups: set = set()

    async def submit_group(
        self,
        group_id: str,
        file_paths: List[str],
        config_dict: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        is_calibrator: bool = False,
    ) -> Optional[str]:
        """Submit a subband group for processing via Absurd.

        Args:
            group_id: The group identifier (timestamp)
            file_paths: List of subband file paths
            config_dict: Pipeline configuration override
            priority: Task priority (higher = more urgent)
            is_calibrator: Whether this is a calibrator observation

        Returns:
            Task ID if submitted, None if already submitted
        """
        # Deduplicate
        if group_id in self._submitted_groups:
            logger.debug(f"[Bridge] Group {group_id} already submitted, skipping")
            return None

        # Build task params with properly typed inputs dict
        inputs_dict: Dict[str, Any] = {
            "input_path": str(Path(file_paths[0]).parent),
            "file_list": file_paths,
            "group_id": group_id,
        }

        # Extract time range from group_id
        try:
            from astropy.time import Time  # type: ignore[import-not-found]

            t = Time(group_id)
            # Assume 5-minute observation window
            if u is not None:
                inputs_dict["start_time"] = (t - 30 * u.second).isot
                inputs_dict["end_time"] = (t + 5 * u.minute).isot
            else:
                inputs_dict["start_time"] = group_id
                inputs_dict["end_time"] = group_id
        except (ValueError, TypeError):
            # Fallback: use group_id as timestamp
            inputs_dict["start_time"] = group_id
            inputs_dict["end_time"] = group_id

        params: Dict[str, Any] = {
            "config": config_dict,
            "inputs": inputs_dict,
            "chain_name": "calibrator" if is_calibrator else self.chain_name,
        }

        # Spawn task
        try:
            task_id = await self.client.spawn_task(
                queue_name=self.queue_name,
                task_name="convert-uvh5-to-ms",
                params=params,
                priority=priority,
            )

            self._submitted_groups.add(group_id)
            logger.info(
                f"[Bridge] Submitted group {group_id} as task {task_id} "
                f"(chain: {params['chain_name']})"
            )

            return str(task_id)

        except Exception as e:
            logger.error(f"[Bridge] Failed to submit group {group_id}: {e}")
            return None

    async def get_group_status(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a submitted group.

        Returns the task status if found, None otherwise.
        """
        # Search for tasks with this group_id
        try:
            tasks = await self.client.list_tasks(
                queue_name=self.queue_name,
                limit=100,
            )

            for task in tasks:
                if task.get("params", {}).get("inputs", {}).get("group_id") == group_id:
                    return {
                        "task_id": task["task_id"],
                        "status": task["status"],
                        "created_at": task.get("created_at"),
                        "completed_at": task.get("completed_at"),
                        "error": task.get("error"),
                    }

        except Exception as e:
            logger.warning(f"[Bridge] Failed to get status for {group_id}: {e}")

        return None

    def clear_submitted_cache(self):
        """Clear the submitted groups cache (useful for testing)."""
        self._submitted_groups.clear()


# Add astropy units import at module level for bridge
try:
    import astropy.units as u  # type: ignore[import-not-found]
except ImportError:
    u = None
