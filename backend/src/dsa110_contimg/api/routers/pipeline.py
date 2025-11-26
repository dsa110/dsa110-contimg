"""Pipeline monitoring and execution status API endpoints."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from dsa110_contimg.pipeline.state import SQLiteStateRepository, StateRepository

logger = logging.getLogger(__name__)

router = APIRouter()


# Workflow Status Models
class WorkflowStageStatus(BaseModel):
    """Status of a single pipeline stage."""

    name: str = Field(..., description="Stage name (e.g., 'ingest', 'conversion')")
    display_name: str = Field(..., description="Human-readable stage name")
    pending: int = Field(0, description="Items waiting to be processed")
    processing: int = Field(0, description="Items currently being processed")
    completed_today: int = Field(0, description="Items completed in the last 24 hours")
    failed_today: int = Field(0, description="Items failed in the last 24 hours")


class WorkflowStatusResponse(BaseModel):
    """Unified workflow status across all pipeline stages."""

    stages: List[WorkflowStageStatus] = Field(
        ..., description="Status of each pipeline stage"
    )
    bottleneck: Optional[str] = Field(
        None, description="Stage with highest backlog (bottleneck)"
    )
    estimated_completion: Optional[str] = Field(
        None, description="ETA for clearing current backlog (ISO format)"
    )
    total_pending: int = Field(0, description="Total items pending across all stages")
    total_completed_today: int = Field(0, description="Total completed today")
    total_failed_today: int = Field(0, description="Total failed today")
    overall_health: str = Field(
        "healthy", description="Overall health: 'healthy', 'degraded', or 'stalled'"
    )
    updated_at: str = Field(..., description="Timestamp of this status (ISO format)")


# Response Models
class StageStatusResponse(BaseModel):
    """Stage status response."""

    name: str
    status: str
    duration_seconds: Optional[float] = None
    attempt: int = 1
    error_message: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class PipelineExecutionResponse(BaseModel):
    """Pipeline execution response."""

    id: int
    job_type: str
    status: str
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    duration_seconds: Optional[float] = None
    stages: List[StageStatusResponse] = []
    error_message: Optional[str] = None
    retry_count: int = 0


class StageMetricsResponse(BaseModel):
    """Stage metrics response."""

    stage_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration_seconds: float
    min_duration_seconds: float
    max_duration_seconds: float
    average_memory_mb: Optional[float] = None
    average_cpu_percent: Optional[float] = None


class DependencyGraphResponse(BaseModel):
    """Dependency graph response."""

    nodes: List[Dict[str, Any]] = Field(..., description="List of stage nodes")
    edges: List[Dict[str, Any]] = Field(..., description="List of dependency edges")


def get_state_repository(request: Request) -> StateRepository:
    """Get state repository from request app state."""
    cfg = request.app.state.cfg
    return SQLiteStateRepository(cfg.products_db)


@router.get("/executions", response_model=List[PipelineExecutionResponse])
def list_pipeline_executions(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List pipeline executions with optional filtering."""
    repo = get_state_repository(request)
    jobs = repo.list_jobs(status=status, job_type=job_type, limit=limit + offset)

    # Apply offset
    jobs = jobs[offset:]

    executions = []
    for job in jobs:
        # Extract stage information from context if available
        stages = []
        if isinstance(job.context, dict):
            stage_results = job.context.get("stage_results", {})
            for stage_name, stage_data in stage_results.items():
                if isinstance(stage_data, dict):
                    stages.append(
                        StageStatusResponse(
                            name=stage_name,
                            status=stage_data.get("status", "unknown"),
                            duration_seconds=stage_data.get("duration_seconds"),
                            attempt=stage_data.get("attempt", 1),
                            error_message=stage_data.get("error_message"),
                            started_at=stage_data.get("started_at"),
                            completed_at=stage_data.get("completed_at"),
                        )
                    )

        duration = None
        if job.finished_at and job.started_at:
            duration = job.finished_at - job.started_at
        elif job.started_at:
            # Still running, calculate partial duration
            import time

            duration = time.time() - job.started_at

        executions.append(
            PipelineExecutionResponse(
                id=job.id,
                job_type=job.type,
                status=job.status,
                created_at=job.created_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
                duration_seconds=duration,
                stages=stages,
                error_message=job.error_message,
                retry_count=job.retry_count,
            )
        )

    return executions


@router.get("/executions/active", response_model=List[PipelineExecutionResponse])
def get_active_executions(
    request: Request,
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
):
    """Get currently active pipeline executions."""
    repo = get_state_repository(request)
    jobs = repo.list_jobs(status="running", limit=limit)

    executions = []
    for job in jobs:
        # Extract stage information from context if available
        stages = []
        if isinstance(job.context, dict):
            stage_results = job.context.get("stage_results", {})
            for stage_name, stage_data in stage_results.items():
                if isinstance(stage_data, dict):
                    stages.append(
                        StageStatusResponse(
                            name=stage_name,
                            status=stage_data.get("status", "unknown"),
                            duration_seconds=stage_data.get("duration_seconds"),
                            attempt=stage_data.get("attempt", 1),
                            error_message=stage_data.get("error_message"),
                            started_at=stage_data.get("started_at"),
                            completed_at=stage_data.get("completed_at"),
                        )
                    )

        duration = None
        if job.finished_at and job.started_at:
            duration = job.finished_at - job.started_at
        elif job.started_at:
            # Still running, calculate partial duration
            import time

            duration = time.time() - job.started_at

        executions.append(
            PipelineExecutionResponse(
                id=job.id,
                job_type=job.type,
                status=job.status,
                created_at=job.created_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
                duration_seconds=duration,
                stages=stages,
                error_message=job.error_message,
                retry_count=job.retry_count,
            )
        )

    return executions


@router.get("/executions/{execution_id}", response_model=PipelineExecutionResponse)
def get_pipeline_execution(request: Request, execution_id: int):
    """Get detailed information about a specific pipeline execution."""
    repo = get_state_repository(request)
    job = repo.get_job(execution_id)

    if not job:
        raise HTTPException(status_code=404, detail="Pipeline execution not found")

    # Extract stage information from context
    stages = []
    if isinstance(job.context, dict):
        stage_results = job.context.get("stage_results", {})
        for stage_name, stage_data in stage_results.items():
            if isinstance(stage_data, dict):
                stages.append(
                    StageStatusResponse(
                        name=stage_name,
                        status=stage_data.get("status", "unknown"),
                        duration_seconds=stage_data.get("duration_seconds"),
                        attempt=stage_data.get("attempt", 1),
                        error_message=stage_data.get("error_message"),
                        started_at=stage_data.get("started_at"),
                        completed_at=stage_data.get("completed_at"),
                    )
                )

    duration = None
    if job.finished_at and job.started_at:
        duration = job.finished_at - job.started_at
    elif job.started_at:
        import time

        duration = time.time() - job.started_at

    return PipelineExecutionResponse(
        id=job.id,
        job_type=job.type,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        duration_seconds=duration,
        stages=stages,
        error_message=job.error_message,
        retry_count=job.retry_count,
    )


@router.get("/executions/{execution_id}/stages", response_model=List[StageStatusResponse])
def get_execution_stages(request: Request, execution_id: int):
    """Get stage details for a specific pipeline execution."""
    execution = get_pipeline_execution(request, execution_id)
    return execution.stages


@router.get("/stages/metrics", response_model=List[StageMetricsResponse])
def get_stage_metrics(
    request: Request,
    stage_name: Optional[str] = Query(None, description="Filter by stage name"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get aggregated metrics for pipeline stages."""
    repo = get_state_repository(request)

    # Get all completed jobs
    all_jobs = repo.list_jobs(limit=10000)  # Get a large sample

    # Aggregate metrics by stage
    stage_metrics: Dict[str, List[Dict[str, Any]]] = {}

    for job in all_jobs:
        if not isinstance(job.context, dict):
            continue

        stage_results = job.context.get("stage_results", {})
        if not isinstance(stage_results, dict):
            continue

        for stage_name, stage_data in stage_results.items():
            if stage_name and isinstance(stage_data, dict):
                if stage_name not in stage_metrics:
                    stage_metrics[stage_name] = []

                stage_metrics[stage_name].append(
                    {
                        "status": stage_data.get("status", "unknown"),
                        "duration": stage_data.get("duration_seconds"),
                        "memory": stage_data.get("memory_peak_mb"),
                        "cpu": stage_data.get("cpu_time_seconds"),
                    }
                )

    # Calculate aggregated metrics
    results = []
    for name, metrics_list in stage_metrics.items():
        if stage_name and name != stage_name:
            continue

        if not metrics_list:
            continue

        durations = [m["duration"] for m in metrics_list if m.get("duration") is not None]
        successful = sum(1 for m in metrics_list if m.get("status") == "completed")
        failed = sum(1 for m in metrics_list if m.get("status") == "failed")

        if not durations:
            continue

        results.append(
            StageMetricsResponse(
                stage_name=name,
                total_executions=len(metrics_list),
                successful_executions=successful,
                failed_executions=failed,
                average_duration_seconds=sum(durations) / len(durations),
                min_duration_seconds=min(durations),
                max_duration_seconds=max(durations),
                average_memory_mb=(
                    sum(m["memory"] for m in metrics_list if m.get("memory"))
                    / len([m for m in metrics_list if m.get("memory")])
                    if any(m.get("memory") for m in metrics_list)
                    else None
                ),
                average_cpu_percent=None,  # CPU percent not stored in current format
            )
        )

    # Sort by stage name
    results.sort(key=lambda x: x.stage_name)

    return results[:limit]


@router.get("/stages/{stage_name}/metrics", response_model=StageMetricsResponse)
def get_stage_metrics_by_name(request: Request, stage_name: str):
    """Get metrics for a specific stage."""
    metrics = get_stage_metrics(request, stage_name=stage_name, limit=1)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No metrics found for stage: {stage_name}")
    return metrics[0]


@router.get("/dependency-graph", response_model=DependencyGraphResponse)
def get_dependency_graph(request: Request):
    """Get pipeline dependency graph."""
    # Try to get dependency graph from orchestrator if available
    # For now, return a static graph based on known stages
    # In a real implementation, this would come from the active orchestrator

    # Known pipeline stages and their dependencies
    stages = {
        "catalog_setup": [],
        "conversion": ["catalog_setup"],
        "calibration_solve": ["conversion"],
        "calibration": ["calibration_solve"],
        "imaging": ["calibration"],
        "organization": ["imaging"],
        "validation": ["organization"],
        "cross_match": ["validation"],
        "adaptive_photometry": ["cross_match"],
    }

    nodes = []
    edges = []

    for stage_name, deps in stages.items():
        nodes.append(
            {
                "id": stage_name,
                "label": stage_name.replace("_", " ").title(),
                "type": "stage",
            }
        )

        for dep in deps:
            edges.append({"from": dep, "to": stage_name, "type": "depends_on"})

    return DependencyGraphResponse(nodes=nodes, edges=edges)


@router.get("/metrics/summary")
def get_metrics_summary(request: Request):
    """Get summary of key pipeline metrics."""
    repo = get_state_repository(request)

    # Get recent jobs
    recent_jobs = repo.list_jobs(limit=1000)

    total_jobs = len(recent_jobs)
    running_jobs = sum(1 for j in recent_jobs if j.status == "running")
    completed_jobs = sum(1 for j in recent_jobs if j.status == "completed")
    failed_jobs = sum(1 for j in recent_jobs if j.status == "failed")

    # Calculate average duration
    durations = []
    for job in recent_jobs:
        if job.finished_at and job.started_at:
            durations.append(job.finished_at - job.started_at)

    avg_duration = sum(durations) / len(durations) if durations else 0

    return {
        "total_jobs": total_jobs,
        "running_jobs": running_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "success_rate": (completed_jobs / total_jobs if total_jobs > 0 else 0),
        "average_duration_seconds": avg_duration,
        "timestamp": datetime.now().isoformat(),
    }


def _query_stage_counts(
    conn: sqlite3.Connection, table: str, state_col: str, time_col: str
) -> Dict[str, int]:
    """Query pending/processing/completed counts for a stage table.

    Args:
        conn: SQLite connection
        table: Table name
        state_col: Column containing state/status
        time_col: Column containing timestamp for today's filter

    Returns:
        Dict with pending, processing, completed_today, failed_today counts
    """
    result = {"pending": 0, "processing": 0, "completed_today": 0, "failed_today": 0}

    # Calculate 24-hour cutoff (Unix timestamp)
    cutoff = (datetime.now() - timedelta(hours=24)).timestamp()

    try:
        # Count by state
        rows = conn.execute(
            f"""
            SELECT 
                {state_col},
                COUNT(*) as cnt,
                SUM(CASE WHEN {time_col} >= ? THEN 1 ELSE 0 END) as today_cnt
            FROM {table}
            GROUP BY {state_col}
            """,
            (cutoff,),
        ).fetchall()

        for row in rows:
            state = (row[0] or "").lower()
            count = row[1] or 0
            today_count = row[2] or 0

            if state in ("pending", "collecting", "queued"):
                result["pending"] += count
            elif state in ("in_progress", "processing", "running"):
                result["processing"] += count
            elif state in ("completed", "success", "done"):
                result["completed_today"] += today_count
            elif state in ("failed", "error"):
                result["failed_today"] += today_count

    except sqlite3.OperationalError:
        # Table doesn't exist or has different schema
        pass

    return result


# Stage display name mapping
STAGE_DISPLAY_NAMES = {
    "ingest": "HDF5 Ingest",
    "conversion": "MS Conversion",
    "calibration": "Calibration",
    "imaging": "Imaging",
    "mosaic": "Mosaicking",
    "photometry": "Photometry",
}


@router.get("/workflow-status", response_model=WorkflowStatusResponse)
def get_workflow_status(request: Request) -> WorkflowStatusResponse:
    """Get unified workflow status across all pipeline stages.

    Returns queue depths and processing rates for each stage from
    HDF5 ingestion through light curve generation. Identifies the
    current bottleneck and estimates completion time.
    """
    cfg = request.app.state.cfg
    stages: List[WorkflowStageStatus] = []

    # Stage 1: Ingest (HDF5 files awaiting conversion)
    try:
        with sqlite3.connect(str(cfg.queue_db)) as conn:
            conn.row_factory = sqlite3.Row
            counts = _query_stage_counts(conn, "ingest_queue", "state", "received_at")
            stages.append(
                WorkflowStageStatus(
                    name="ingest",
                    pending=counts["pending"],
                    processing=counts["processing"],
                    completed_today=counts["completed_today"],
                    failed_today=counts["failed_today"],
                )
            )
    except (sqlite3.Error, FileNotFoundError) as e:
        logger.warning(f"Failed to query ingest queue: {e}")
        stages.append(WorkflowStageStatus(name="ingest"))

    # Stage 2: Conversion (MS files - check ms_index for stage)
    try:
        with sqlite3.connect(str(cfg.products_db)) as conn:
            conn.row_factory = sqlite3.Row
            counts = _query_stage_counts(conn, "ms_index", "stage", "processed_at")
            stages.append(
                WorkflowStageStatus(
                    name="conversion",
                    pending=counts["pending"],
                    processing=counts["processing"],
                    completed_today=counts["completed_today"],
                    failed_today=counts["failed_today"],
                )
            )
    except (sqlite3.Error, FileNotFoundError) as e:
        logger.warning(f"Failed to query ms_index: {e}")
        stages.append(WorkflowStageStatus(name="conversion"))

    # Stage 3: Calibration (MS files awaiting/in calibration)
    try:
        with sqlite3.connect(str(cfg.products_db)) as conn:
            conn.row_factory = sqlite3.Row
            cutoff = (datetime.now() - timedelta(hours=24)).timestamp()

            # Count cal_applied = 0 (pending) vs cal_applied = 1 (completed)
            row = conn.execute(
                """
                SELECT 
                    SUM(CASE WHEN cal_applied = 0 THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN cal_applied = 1 AND processed_at >= ? THEN 1 ELSE 0 END) as completed_today
                FROM ms_index
                """,
                (cutoff,),
            ).fetchone()

            stages.append(
                WorkflowStageStatus(
                    name="calibration",
                    pending=row["pending"] or 0 if row else 0,
                    processing=0,  # No separate processing state for calibration
                    completed_today=row["completed_today"] or 0 if row else 0,
                )
            )
    except (sqlite3.Error, FileNotFoundError) as e:
        logger.warning(f"Failed to query calibration status: {e}")
        stages.append(WorkflowStageStatus(name="calibration"))

    # Stage 4: Imaging (images created from calibrated MS)
    try:
        with sqlite3.connect(str(cfg.products_db)) as conn:
            conn.row_factory = sqlite3.Row
            cutoff = (datetime.now() - timedelta(hours=24)).timestamp()

            row = conn.execute(
                """
                SELECT COUNT(*) as completed_today
                FROM images
                WHERE created_at >= ?
                """,
                (cutoff,),
            ).fetchone()

            stages.append(
                WorkflowStageStatus(
                    name="imaging",
                    pending=0,  # No queue - driven by calibration
                    processing=0,
                    completed_today=row["completed_today"] or 0 if row else 0,
                )
            )
    except (sqlite3.Error, FileNotFoundError) as e:
        logger.warning(f"Failed to query imaging status: {e}")
        stages.append(WorkflowStageStatus(name="imaging"))

    # Stage 5: Mosaic (mosaic_groups status)
    try:
        with sqlite3.connect(str(cfg.products_db)) as conn:
            conn.row_factory = sqlite3.Row
            counts = _query_stage_counts(conn, "mosaic_groups", "status", "created_at")
            stages.append(
                WorkflowStageStatus(
                    name="mosaic",
                    pending=counts["pending"],
                    processing=counts["processing"],
                    completed_today=counts["completed_today"],
                    failed_today=counts["failed_today"],
                )
            )
    except (sqlite3.Error, FileNotFoundError) as e:
        logger.warning(f"Failed to query mosaic status: {e}")
        stages.append(WorkflowStageStatus(name="mosaic"))

    # Stage 6: Photometry (photometry results)
    try:
        with sqlite3.connect(str(cfg.products_db)) as conn:
            conn.row_factory = sqlite3.Row
            cutoff = (datetime.now() - timedelta(hours=24)).timestamp()

            row = conn.execute(
                """
                SELECT COUNT(*) as completed_today
                FROM photometry
                WHERE measured_at >= ?
                """,
                (cutoff,),
            ).fetchone()

            stages.append(
                WorkflowStageStatus(
                    name="photometry",
                    pending=0,  # Photometry is driven by mosaics
                    processing=0,
                    completed_today=row["completed_today"] or 0 if row else 0,
                )
            )
    except (sqlite3.Error, FileNotFoundError) as e:
        logger.warning(f"Failed to query photometry status: {e}")
        stages.append(WorkflowStageStatus(name="photometry"))

    # Calculate totals and find bottleneck
    total_pending = sum(s.pending for s in stages)
    total_processing = sum(s.processing for s in stages)

    # Bottleneck is stage with highest pending count
    bottleneck = None
    max_pending = 0
    for stage in stages:
        if stage.pending > max_pending:
            max_pending = stage.pending
            bottleneck = stage.name

    # Determine health based on backlog
    if total_pending == 0 and total_processing == 0:
        health = "idle"
    elif total_pending > 100 or (bottleneck and max_pending > 50):
        health = "slow"
    elif total_pending > 500 or (bottleneck and max_pending > 200):
        health = "stalled"
    else:
        health = "healthy"

    # Estimate completion time (rough: 1 item per minute average)
    estimated_completion = None
    if total_pending > 0:
        estimated_minutes = total_pending * 1  # 1 minute per item estimate
        eta = datetime.now() + timedelta(minutes=estimated_minutes)
        estimated_completion = eta.isoformat()

    return WorkflowStatusResponse(
        stages=stages,
        bottleneck=bottleneck,
        estimated_completion=estimated_completion,
        total_pending=total_pending,
        total_processing=total_processing,
        health=health,
    )
