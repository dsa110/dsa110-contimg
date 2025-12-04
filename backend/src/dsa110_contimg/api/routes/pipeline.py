"""
FastAPI router for pipeline control operations.

Provides REST API endpoints for:
- Listing registered pipelines
- Running pipelines (full or individual stages)
- Getting pipeline execution status
- Triggering individual stage tasks
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from dsa110_contimg.absurd import AbsurdClient
from dsa110_contimg.api.routes.absurd import get_absurd_client

from ..auth import require_write_access

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pipeline",
    tags=["pipeline"],
    dependencies=[Depends(require_write_access)],
)


# =============================================================================
# Request/Response Models
# =============================================================================


class PipelineInfo(BaseModel):
    """Information about a registered pipeline."""

    name: str = Field(..., description="Pipeline name")
    description: str = Field(default="", description="Pipeline description")
    schedule: Optional[str] = Field(None, description="Cron schedule if scheduled")
    is_scheduled: bool = Field(default=False, description="Whether pipeline runs on schedule")


class PipelineListResponse(BaseModel):
    """List of registered pipelines."""

    pipelines: List[PipelineInfo]
    total: int


class RunPipelineRequest(BaseModel):
    """Request to run a registered pipeline."""

    pipeline_name: str = Field(..., description="Name of registered pipeline to run")
    params: Dict[str, Any] = Field(default_factory=dict, description="Pipeline parameters")


class RunPipelineResponse(BaseModel):
    """Response from running a pipeline."""

    execution_id: str = Field(..., description="Pipeline execution ID")
    pipeline_name: str = Field(..., description="Pipeline name")
    status: str = Field(..., description="Initial status")
    message: str = Field(default="", description="Status message")


class FullPipelineRequest(BaseModel):
    """Request to run a full pipeline (conversion → calibration → imaging)."""

    start_time: str = Field(..., description="Start time ISO format")
    end_time: str = Field(..., description="End time ISO format")
    input_dir: str = Field(default="/data/incoming", description="Input HDF5 directory")
    output_dir: str = Field(default="/stage/dsa110-contimg/ms", description="Output MS directory")
    run_calibration: bool = Field(default=True, description="Run calibration after conversion")
    run_imaging: bool = Field(default=True, description="Run imaging after calibration")
    imaging_params: Dict[str, Any] = Field(default_factory=dict, description="Imaging parameters")


class StageTaskRequest(BaseModel):
    """Request to run an individual pipeline stage."""

    stage: str = Field(..., description="Stage name: conversion, calibration-solve, calibration-apply, imaging, validation, crossmatch, photometry")
    params: Dict[str, Any] = Field(..., description="Stage-specific parameters")
    priority: int = Field(default=0, description="Task priority")


class StageTaskResponse(BaseModel):
    """Response from spawning a stage task."""

    task_id: str = Field(..., description="ABSURD task ID")
    stage: str = Field(..., description="Stage name")
    status: str = Field(..., description="Initial status")


class ExecutionStatus(BaseModel):
    """Status of a pipeline execution."""

    execution_id: str
    pipeline_name: str
    status: str  # pending, running, completed, failed
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
    jobs: List[Dict[str, Any]]


class ExecutionListResponse(BaseModel):
    """List of pipeline executions."""

    executions: List[ExecutionStatus]
    total: int


# =============================================================================
# Pipeline Registry Endpoints
# =============================================================================


@router.get("/registered", response_model=PipelineListResponse)
async def list_registered_pipelines():
    """List all registered pipelines.

    Returns:
        List of pipeline info with names, descriptions, and schedules
    """
    from dsa110_contimg.pipeline import get_pipeline_registry

    registry = get_pipeline_registry()
    pipelines = []

    for name in registry.list_names():
        pipeline_class = registry.get(name)
        if pipeline_class:
            pipelines.append(
                PipelineInfo(
                    name=name,
                    description=pipeline_class.__doc__ or "",
                    schedule=getattr(pipeline_class, "schedule", None),
                    is_scheduled=getattr(pipeline_class, "schedule", None) is not None,
                )
            )

    return PipelineListResponse(pipelines=pipelines, total=len(pipelines))


@router.post("/run", response_model=RunPipelineResponse)
async def run_registered_pipeline(
    request: RunPipelineRequest,
    client: AbsurdClient = Depends(get_absurd_client),
):
    """Run a registered pipeline by name.

    Args:
        request: Pipeline name and parameters

    Returns:
        Execution ID and initial status
    """
    from dsa110_contimg.pipeline import get_pipeline_registry

    registry = get_pipeline_registry()

    # Validate pipeline exists
    if request.pipeline_name not in registry:
        available = ", ".join(registry.list_names()) or "(none)"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline '{request.pipeline_name}' not found. Available: {available}",
        )

    # Get database path from environment or default
    import os

    db_path = os.environ.get(
        "PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3"
    )

    # Spawn the pipeline-run task
    try:
        task_id = await client.spawn_task(
            queue_name="dsa110-pipeline",
            task_name="pipeline-run",
            params={
                "pipeline_name": request.pipeline_name,
                "database_path": db_path,
                **request.params,
            },
            priority=5,  # Higher priority for user-requested pipelines
        )

        return RunPipelineResponse(
            execution_id=str(task_id),
            pipeline_name=request.pipeline_name,
            status="pending",
            message=f"Pipeline '{request.pipeline_name}' queued for execution",
        )

    except Exception as e:
        logger.exception(f"Failed to run pipeline {request.pipeline_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue pipeline: {str(e)}",
        )


# =============================================================================
# Full Pipeline Endpoints
# =============================================================================


@router.post("/full", response_model=Dict[str, Any])
async def run_full_pipeline(
    request: FullPipelineRequest,
    client: AbsurdClient = Depends(get_absurd_client),
):
    """Run a full pipeline: conversion → calibration → imaging.

    This spawns a sequence of tasks that process observations
    in the given time range through the complete pipeline.

    Args:
        request: Time range and processing options

    Returns:
        Task IDs for each stage
    """
    task_ids = {}

    try:
        # Stage 1: Conversion
        conversion_task = await client.spawn_task(
            queue_name="dsa110-pipeline",
            task_name="convert-uvh5-to-ms",
            params={
                "inputs": {
                    "input_dir": request.input_dir,
                    "output_dir": request.output_dir,
                    "start_time": request.start_time,
                    "end_time": request.end_time,
                },
            },
            priority=5,
        )
        task_ids["conversion"] = str(conversion_task)

        # Stage 2: Calibration (if requested)
        if request.run_calibration:
            cal_task = await client.spawn_task(
                queue_name="dsa110-pipeline",
                task_name="calibration-apply",
                params={
                    "inputs": {
                        "ms_dir": request.output_dir,
                        "start_time": request.start_time,
                        "end_time": request.end_time,
                    },
                    "depends_on": str(conversion_task),
                },
                priority=4,
            )
            task_ids["calibration"] = str(cal_task)

            # Stage 3: Imaging (if requested)
            if request.run_imaging:
                imaging_task = await client.spawn_task(
                    queue_name="dsa110-pipeline",
                    task_name="imaging",
                    params={
                        "inputs": {
                            "ms_dir": request.output_dir,
                            "start_time": request.start_time,
                            "end_time": request.end_time,
                            **request.imaging_params,
                        },
                        "depends_on": str(cal_task),
                    },
                    priority=3,
                )
                task_ids["imaging"] = str(imaging_task)

        return {
            "status": "queued",
            "task_ids": task_ids,
            "time_range": {
                "start": request.start_time,
                "end": request.end_time,
            },
            "message": f"Full pipeline queued with {len(task_ids)} stages",
        }

    except Exception as e:
        logger.exception(f"Failed to queue full pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue pipeline: {str(e)}",
        )


# =============================================================================
# Individual Stage Endpoints
# =============================================================================


SUPPORTED_STAGES = [
    "convert-uvh5-to-ms",
    "calibration-solve",
    "calibration-apply",
    "imaging",
    "validation",
    "crossmatch",
    "photometry",
    "catalog-setup",
    "organize-files",
    "create-mosaic",
]


@router.get("/stages")
async def list_available_stages():
    """List available pipeline stages that can be run individually.

    Returns:
        List of stage names with descriptions
    """
    stage_info = {
        "convert-uvh5-to-ms": "Convert UVH5 files to Measurement Sets",
        "calibration-solve": "Solve for calibration solutions",
        "calibration-apply": "Apply calibration to MS",
        "imaging": "Create images from calibrated MS",
        "validation": "Validate image quality",
        "crossmatch": "Cross-match sources with catalogs",
        "photometry": "Extract photometry from images",
        "catalog-setup": "Build catalog databases for declination",
        "organize-files": "Organize output files into standard structure",
        "create-mosaic": "Create mosaic from multiple images",
    }

    return {
        "stages": [
            {"name": name, "description": stage_info.get(name, "")}
            for name in SUPPORTED_STAGES
        ],
        "total": len(SUPPORTED_STAGES),
    }


@router.post("/stage", response_model=StageTaskResponse)
async def run_stage(
    request: StageTaskRequest,
    client: AbsurdClient = Depends(get_absurd_client),
):
    """Run an individual pipeline stage as an ABSURD task.

    Args:
        request: Stage name and parameters

    Returns:
        Task ID and status
    """
    if request.stage not in SUPPORTED_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown stage '{request.stage}'. Supported: {', '.join(SUPPORTED_STAGES)}",
        )

    try:
        task_id = await client.spawn_task(
            queue_name="dsa110-pipeline",
            task_name=request.stage,
            params={"inputs": request.params},
            priority=request.priority,
        )

        return StageTaskResponse(
            task_id=str(task_id),
            stage=request.stage,
            status="pending",
        )

    except Exception as e:
        logger.exception(f"Failed to run stage {request.stage}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue stage: {str(e)}",
        )


# =============================================================================
# Stage-Specific Convenience Endpoints
# =============================================================================


@router.post("/calibrate")
async def calibrate_ms(
    ms_path: str = Query(..., description="Path to Measurement Set"),
    apply_only: bool = Query(default=True, description="Apply existing solutions (vs solve new)"),
    client: AbsurdClient = Depends(get_absurd_client),
):
    """Calibrate a specific Measurement Set.

    Args:
        ms_path: Path to the MS to calibrate
        apply_only: If True, apply existing solutions; if False, solve new ones

    Returns:
        Task ID and status
    """
    task_name = "calibration-apply" if apply_only else "calibration-solve"

    try:
        task_id = await client.spawn_task(
            queue_name="dsa110-pipeline",
            task_name=task_name,
            params={"inputs": {"ms_path": ms_path}},
            priority=5,
        )

        return {
            "task_id": str(task_id),
            "stage": task_name,
            "ms_path": ms_path,
            "status": "pending",
        }

    except Exception as e:
        logger.exception(f"Failed to calibrate {ms_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/image")
async def image_ms(
    ms_path: str = Query(..., description="Path to calibrated Measurement Set"),
    imsize: int = Query(default=5040, description="Image size in pixels"),
    cell: str = Query(default="2.5arcsec", description="Cell size"),
    niter: int = Query(default=10000, description="Number of clean iterations"),
    threshold: str = Query(default="0.5mJy", description="Clean threshold"),
    weighting: str = Query(default="briggs", description="Weighting scheme"),
    robust: float = Query(default=0.5, description="Robust parameter"),
    client: AbsurdClient = Depends(get_absurd_client),
):
    """Create an image from a calibrated Measurement Set.

    Args:
        ms_path: Path to the calibrated MS
        imsize: Image size in pixels
        cell: Cell size
        niter: Clean iterations
        threshold: Clean threshold
        weighting: Weighting scheme
        robust: Robust parameter

    Returns:
        Task ID and status
    """
    try:
        task_id = await client.spawn_task(
            queue_name="dsa110-pipeline",
            task_name="imaging",
            params={
                "inputs": {
                    "ms_path": ms_path,
                    "imsize": [imsize, imsize],
                    "cell": cell,
                    "niter": niter,
                    "threshold": threshold,
                    "weighting": weighting,
                    "robust": robust,
                }
            },
            priority=5,
        )

        return {
            "task_id": str(task_id),
            "stage": "imaging",
            "ms_path": ms_path,
            "status": "pending",
        }

    except Exception as e:
        logger.exception(f"Failed to image {ms_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Execution Status Endpoints
# =============================================================================


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    limit: int = Query(default=50, description="Max results"),
    status_filter: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List recent pipeline executions.

    Args:
        limit: Maximum number of results
        status_filter: Optional status filter (pending, running, completed, failed)

    Returns:
        List of execution statuses
    """
    import os
    import sqlite3

    db_path = os.environ.get(
        "PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3"
    )

    if not Path(db_path).exists():
        return ExecutionListResponse(executions=[], total=0)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        query = """
            SELECT execution_id, pipeline_name, status, started_at, completed_at, error
            FROM pipeline_executions
        """
        params = []

        if status_filter:
            query += " WHERE status = ?"
            params.append(status_filter)

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        executions = []
        for row in rows:
            # Get jobs for this execution
            job_cursor = conn.execute(
                """
                SELECT job_id, job_type, status, started_at, completed_at, error
                FROM pipeline_jobs
                WHERE execution_id = ?
                ORDER BY started_at
                """,
                (row["execution_id"],),
            )
            jobs = [dict(j) for j in job_cursor.fetchall()]

            executions.append(
                ExecutionStatus(
                    execution_id=row["execution_id"],
                    pipeline_name=row["pipeline_name"],
                    status=row["status"],
                    started_at=row["started_at"],
                    completed_at=row["completed_at"],
                    error=row["error"],
                    jobs=jobs,
                )
            )

        conn.close()
        return ExecutionListResponse(executions=executions, total=len(executions))

    except Exception as e:
        logger.warning(f"Failed to query executions: {e}")
        return ExecutionListResponse(executions=[], total=0)


@router.get("/executions/{execution_id}", response_model=ExecutionStatus)
async def get_execution(execution_id: str):
    """Get status of a specific pipeline execution.

    Args:
        execution_id: Execution ID

    Returns:
        Execution status with job details
    """
    import os
    import sqlite3

    db_path = os.environ.get(
        "PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3"
    )

    if not Path(db_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline database not found",
        )

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            SELECT execution_id, pipeline_name, status, started_at, completed_at, error
            FROM pipeline_executions
            WHERE execution_id = ?
            """,
            (execution_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution '{execution_id}' not found",
            )

        # Get jobs
        job_cursor = conn.execute(
            """
            SELECT job_id, job_type, status, started_at, completed_at, error
            FROM pipeline_jobs
            WHERE execution_id = ?
            ORDER BY started_at
            """,
            (execution_id,),
        )
        jobs = [dict(j) for j in job_cursor.fetchall()]

        conn.close()

        return ExecutionStatus(
            execution_id=row["execution_id"],
            pipeline_name=row["pipeline_name"],
            status=row["status"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            error=row["error"],
            jobs=jobs,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
