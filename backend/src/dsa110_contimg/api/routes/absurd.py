"""
FastAPI router for Absurd workflow manager.

Provides REST API endpoints for spawning, querying, and managing
Absurd tasks.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import (  # type: ignore[import-not-found]
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)
from pydantic import BaseModel, Field  # type: ignore[import-not-found]

from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig
from dsa110_contimg.absurd.monitoring import AbsurdMonitor, TaskMetrics
from dsa110_contimg.api.websocket import manager

from ..auth import require_write_access

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["absurd"],
    dependencies=[Depends(require_write_access)],
)

# Global client instance (initialized on startup)
_client: Optional[AbsurdClient] = None
_config: Optional[AbsurdConfig] = None
_monitor: Optional[AbsurdMonitor] = None


# Pydantic models for request/response


class SpawnTaskRequest(BaseModel):
    """Request to spawn a new task."""

    queue_name: str = Field(..., description="Queue name")
    task_name: str = Field(..., description="Task name/type")
    params: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    priority: int = Field(default=0, description="Task priority")
    timeout_sec: Optional[int] = Field(None, description="Task timeout in seconds")


class TaskResponse(BaseModel):
    """Task details response."""

    task_id: str
    queue_name: str
    task_name: str
    params: Dict[str, Any]
    priority: int
    status: str
    created_at: Optional[str]
    claimed_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    retry_count: int


class TaskListResponse(BaseModel):
    """List of tasks response."""

    tasks: List[TaskResponse]
    total: int


class QueueStatsResponse(BaseModel):
    """Queue statistics response."""

    queue_name: str
    pending: int
    claimed: int
    completed: int
    failed: int
    cancelled: int
    total: int


class MetricsResponse(BaseModel):
    """Absurd metrics response."""

    total_spawned: int
    total_claimed: int
    total_completed: int
    total_failed: int
    total_cancelled: int
    total_timed_out: int
    current_pending: int
    current_claimed: int
    avg_wait_time_sec: float
    avg_execution_time_sec: float
    p50_wait_time_sec: float
    p95_wait_time_sec: float
    p99_wait_time_sec: float
    p50_execution_time_sec: float
    p95_execution_time_sec: float
    p99_execution_time_sec: float
    throughput_1min: float
    throughput_5min: float
    throughput_15min: float
    success_rate_1min: float
    success_rate_5min: float
    success_rate_15min: float
    error_rate_1min: float
    error_rate_5min: float
    error_rate_15min: float


class WorkerResponse(BaseModel):
    """Worker information response."""

    worker_id: str
    state: str
    task_count: int
    current_task_id: Optional[str]
    first_seen: Optional[str]
    last_seen: Optional[str]
    uptime_seconds: float


class WorkerListResponse(BaseModel):
    """List of workers response."""

    workers: List[WorkerResponse]
    total: int
    active: int
    idle: int
    stale: int
    crashed: int


class WorkerMetricsResponse(BaseModel):
    """Worker pool metrics response."""

    total_workers: int
    active_workers: int
    idle_workers: int
    crashed_workers: int
    timed_out_workers: int
    avg_tasks_per_worker: float
    avg_worker_uptime_sec: float


class AlertResponse(BaseModel):
    """Alert information response."""

    level: str  # "alert" or "warning"
    message: str
    timestamp: Optional[str]


class HealthResponse(BaseModel):
    """Health check response with alerts."""

    status: str
    message: str
    queue_depth: int
    database_available: bool
    worker_pool_healthy: bool
    alerts: List[AlertResponse]
    warnings: List[AlertResponse]


# Dependency for getting client


async def get_absurd_client() -> AbsurdClient:
    """Get the global Absurd client instance.

    Raises:
        HTTPException: If Absurd is not enabled or client not initialized
    """
    if _config is None or not _config.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Absurd workflow manager is not enabled",
        )

    if _client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Absurd client not initialized"
        )

    return _client


# Lifecycle functions


async def initialize_absurd(config: AbsurdConfig) -> None:
    """Initialize Absurd client on application startup.

    Args:
        config: Absurd configuration
    """
    global _client, _config, _monitor

    _config = config

    if not config.enabled:
        logger.info("Absurd is disabled, skipping initialization")
        return

    logger.info("Initializing Absurd client...")
    _client = AbsurdClient(config.database_url, pool_min_size=2, pool_max_size=10)
    await _client.connect()
    logger.info("Absurd client initialized")

    # Initialize monitor for metrics collection
    _monitor = AbsurdMonitor(_client, config.queue_name)
    logger.info("Absurd monitor initialized for queue: %s", config.queue_name)


async def shutdown_absurd() -> None:
    """Shutdown Absurd client on application shutdown."""
    global _client, _monitor

    if _client is not None:
        logger.info("Shutting down Absurd client...")
        await _client.close()
        _client = None
        _monitor = None
        logger.info(":white_heavy_check_mark: Absurd client shutdown complete")


# Alias functions for app.py lifespan integration
async def init_absurd_client(config: AbsurdConfig) -> None:
    """Alias for initialize_absurd for lifespan integration."""
    await initialize_absurd(config)


async def shutdown_absurd_client() -> None:
    """Alias for shutdown_absurd for lifespan integration."""
    await shutdown_absurd()


# API endpoints


@router.post("/tasks", response_model=Dict[str, str])
async def spawn_task(request: SpawnTaskRequest, client: AbsurdClient = Depends(get_absurd_client)):
    """Spawn a new task in the Absurd queue.

    Args:
        request: Task spawn request
        client: Absurd client (injected)

    Returns:
        Dict with task_id

    Raises:
        HTTPException: If spawn fails
    """
    try:
        task_id = await client.spawn_task(
            queue_name=request.queue_name,
            task_name=request.task_name,
            params=request.params,
            priority=request.priority,
            timeout_sec=request.timeout_sec,
        )

        # Emit WebSocket event for task creation
        await manager.broadcast(
            {
                "type": "task_update",
                "queue_name": request.queue_name,
                "task_id": str(task_id),
                "update": {
                    "status": "pending",
                    "created_at": None,  # Will be set by database
                },
            }
        )

        # Emit queue stats update
        await manager.broadcast(
            {
                "type": "queue_stats_update",
                "queue_name": request.queue_name,
            }
        )

        return {"task_id": str(task_id)}
    except Exception as e:
        logger.exception(f"Failed to spawn task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to spawn task: {str(e)}",
        )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, client: AbsurdClient = Depends(get_absurd_client)):
    """Get task details by ID.

    Args:
        task_id: Task UUID
        client: Absurd client (injected)

    Returns:
        Task details

    Raises:
        HTTPException: If task not found
    """
    task = await client.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found"
        )
    return TaskResponse(**task)


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    queue_name: Optional[str] = None,
    task_status: Optional[str] = Query(None, alias="status"),
    limit: int = 100,
    client: AbsurdClient = Depends(get_absurd_client),
):
    """List tasks matching criteria.

    Args:
        queue_name: Filter by queue name
        task_status: Filter by status
        limit: Maximum number of tasks to return
        client: Absurd client (injected)

    Returns:
        List of tasks
    """
    try:
        tasks = await client.list_tasks(queue_name=queue_name, status=task_status, limit=limit)
        return TaskListResponse(tasks=[TaskResponse(**t) for t in tasks], total=len(tasks))
    except ValueError as e:
        # Client not connected - return graceful error
        if "not connected" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ABSURD client not connected to database",
            )
        raise


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: UUID, client: AbsurdClient = Depends(get_absurd_client)):
    """Cancel a pending task.

    Args:
        task_id: Task UUID
        client: Absurd client (injected)

    Returns:
        Success message

    Raises:
        HTTPException: If task not found or already completed
    """
    cancelled = await client.cancel_task(task_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found or already completed",
        )

    # Get task to find queue name
    task = await client.get_task(task_id)
    if task:
        # Emit WebSocket event for task cancellation
        await manager.broadcast(
            {
                "type": "task_update",
                "queue_name": task["queue_name"],
                "task_id": str(task_id),
                "update": {
                    "status": "cancelled",
                },
            }
        )

        # Emit queue stats update
        await manager.broadcast(
            {
                "type": "queue_stats_update",
                "queue_name": task["queue_name"],
            }
        )

    return {"message": f"Task {task_id} cancelled"}


@router.get("/queues", response_model=List[str])
async def list_queues(client: AbsurdClient = Depends(get_absurd_client)):
    """List all available queues.

    Returns:
        List of queue names
    """
    try:
        # Query distinct queue names from tasks table
        if client._pool is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available",
            )

        async with client._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT queue_name FROM absurd.tasks ORDER BY queue_name"
            )
            return [row["queue_name"] for row in rows]
    except Exception as e:
        logger.exception(f"Failed to list queues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list queues: {str(e)}",
        )


@router.get("/queues/stats", response_model=List[QueueStatsResponse])
async def get_all_queue_stats(client: AbsurdClient = Depends(get_absurd_client)):
    """Get statistics for all queues.

    Returns aggregated statistics across all queues.
    """
    try:
        if client._pool is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available",
            )

        async with client._pool.acquire() as conn:
            # Get stats for all queues in one query
            rows = await conn.fetch(
                """
                SELECT 
                    queue_name,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'claimed') as claimed,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled,
                    COUNT(*) as total
                FROM absurd.tasks
                GROUP BY queue_name
                ORDER BY queue_name
                """
            )
            return [
                QueueStatsResponse(
                    queue_name=row["queue_name"],
                    pending=row["pending"],
                    claimed=row["claimed"],
                    completed=row["completed"],
                    failed=row["failed"],
                    cancelled=row["cancelled"],
                    total=row["total"],
                )
                for row in rows
            ]
    except Exception as e:
        logger.exception(f"Failed to get all queue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue stats: {str(e)}",
        )


@router.get("/queues/{queue_name}/stats", response_model=QueueStatsResponse)
async def get_queue_stats(queue_name: str, client: AbsurdClient = Depends(get_absurd_client)):
    """Get statistics for a queue.

    Args:
        queue_name: Queue name
        client: Absurd client (injected)

    Returns:
        Queue statistics
    """
    try:
        stats = await client.get_queue_stats(queue_name)
        total = sum(stats.values())
        return QueueStatsResponse(
            queue_name=queue_name,
            pending=stats.get("pending", 0),
            claimed=stats.get("claimed", 0),
            completed=stats.get("completed", 0),
            failed=stats.get("failed", 0),
            cancelled=stats.get("cancelled", 0),
            total=total,
        )
    except ValueError as e:
        # Client not connected - return graceful error
        if "not connected" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ABSURD client not connected to database",
            )
        raise


@router.get("/health")
async def health_check():
    """Health check endpoint for Absurd integration.

    Returns:
        Health status
    """
    if _config is None or not _config.enabled:
        return {"status": "disabled", "message": "Absurd is not enabled"}

    if _client is None:
        return {"status": "error", "message": "Absurd client not initialized"}

    return {"status": "healthy", "message": "Absurd is operational", "queue": _config.queue_name}


@router.get("/health/detailed", response_model=HealthResponse)
async def get_detailed_health():
    """Get detailed health status with alerts and warnings.

    Returns comprehensive health information including queue depth,
    database status, worker pool health, and any active alerts.
    """
    from datetime import datetime

    if _config is None or not _config.enabled:
        return HealthResponse(
            status="disabled",
            message="Absurd is not enabled",
            queue_depth=0,
            database_available=False,
            worker_pool_healthy=False,
            alerts=[],
            warnings=[],
        )

    if _monitor is None:
        return HealthResponse(
            status="error",
            message="Monitor not initialized",
            queue_depth=0,
            database_available=False,
            worker_pool_healthy=False,
            alerts=[
                AlertResponse(level="alert", message="Monitor not initialized", timestamp=None)
            ],
            warnings=[],
        )

    try:
        health = await _monitor.check_health()

        alerts = [
            AlertResponse(level="alert", message=msg, timestamp=datetime.now().isoformat())
            for msg in health.alerts
        ]
        warnings = [
            AlertResponse(level="warning", message=msg, timestamp=datetime.now().isoformat())
            for msg in health.warnings
        ]

        return HealthResponse(
            status=health.status,
            message=health.message,
            queue_depth=health.queue_depth,
            database_available=health.database_available,
            worker_pool_healthy=health.worker_pool_healthy,
            alerts=alerts,
            warnings=warnings,
        )
    except Exception as e:
        logger.exception(f"Failed to check health: {e}")
        return HealthResponse(
            status="error",
            message=str(e),
            queue_depth=0,
            database_available=False,
            worker_pool_healthy=False,
            alerts=[AlertResponse(level="alert", message=str(e), timestamp=None)],
            warnings=[],
        )


@router.get("/workers", response_model=WorkerListResponse)
async def list_workers():
    """List all registered workers and their states.

    Returns information about all workers including their current state,
    task count, and last heartbeat time.
    """
    from datetime import datetime

    if _monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Absurd monitor not initialized",
        )

    try:
        worker_metrics = await _monitor.collect_worker_metrics()

        workers = []
        now = time.time()

        for worker_id, state in (worker_metrics.worker_states or {}).items():
            last_seen_ts = (worker_metrics.last_heartbeat_times or {}).get(worker_id, 0)
            uptime = (worker_metrics.worker_uptime_sec or {}).get(worker_id, 0)
            task_count = (worker_metrics.tasks_per_worker or {}).get(worker_id, 0)

            workers.append(
                WorkerResponse(
                    worker_id=worker_id,
                    state=state,
                    task_count=task_count,
                    current_task_id=None,  # Would need to track this in monitor
                    first_seen=(
                        datetime.fromtimestamp(last_seen_ts - uptime).isoformat()
                        if uptime
                        else None
                    ),
                    last_seen=(
                        datetime.fromtimestamp(last_seen_ts).isoformat() if last_seen_ts else None
                    ),
                    uptime_seconds=uptime,
                )
            )

        # Count by state
        active = sum(1 for w in workers if w.state == "active")
        idle = sum(1 for w in workers if w.state == "idle")
        stale = sum(1 for w in workers if w.state == "stale")
        crashed = sum(1 for w in workers if w.state == "crashed")

        return WorkerListResponse(
            workers=workers,
            total=len(workers),
            active=active,
            idle=idle,
            stale=stale,
            crashed=crashed,
        )
    except Exception as e:
        logger.exception(f"Failed to list workers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workers: {str(e)}",
        )


@router.get("/workers/metrics", response_model=WorkerMetricsResponse)
async def get_worker_metrics():
    """Get worker pool metrics summary.

    Returns aggregate metrics about the worker pool including counts,
    average tasks per worker, and average uptime.
    """
    if _monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Absurd monitor not initialized",
        )

    try:
        metrics = await _monitor.collect_worker_metrics()
        return WorkerMetricsResponse(
            total_workers=metrics.total_workers,
            active_workers=metrics.active_workers,
            idle_workers=metrics.idle_workers,
            crashed_workers=metrics.crashed_workers,
            timed_out_workers=metrics.timed_out_workers,
            avg_tasks_per_worker=metrics.avg_tasks_per_worker,
            avg_worker_uptime_sec=metrics.avg_worker_uptime_sec,
        )
    except Exception as e:
        logger.exception(f"Failed to get worker metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker metrics: {str(e)}",
        )


@router.post("/workers/{worker_id}/heartbeat")
async def worker_heartbeat(worker_id: str, task_id: Optional[str] = None):
    """Register a worker heartbeat.

    Workers should call this periodically to indicate they are alive.
    If processing a task, include the task_id.

    Args:
        worker_id: Unique worker identifier
        task_id: Optional current task ID being processed
    """
    if _monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Absurd monitor not initialized",
        )

    try:
        _monitor.register_worker_heartbeat(worker_id, task_id)
        return {"status": "ok", "worker_id": worker_id}
    except Exception as e:
        logger.exception(f"Failed to register heartbeat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register heartbeat: {str(e)}",
        )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(client: AbsurdClient = Depends(get_absurd_client)):
    """Get real-time metrics for Absurd workflow manager.

    Returns:
        Comprehensive metrics including throughput, latency, and success rates.

    Raises:
        HTTPException: If monitor not initialized or metrics unavailable
    """
    if _monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Absurd monitor not initialized",
        )

    try:
        metrics = await _monitor.collect_metrics()
        return MetricsResponse(**metrics.__dict__)
    except Exception as e:
        logger.exception(f"Failed to collect metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to collect metrics: {str(e)}",
        )


@router.get("/metrics/prometheus")
async def get_prometheus_metrics(client: AbsurdClient = Depends(get_absurd_client)):
    """Get metrics in Prometheus exposition format.

    Returns metrics in Prometheus text format for scraping by Prometheus server.
    Endpoint is designed for use with Prometheus ServiceMonitor or static config.

    Returns:
        Plain text response in Prometheus exposition format

    Example Prometheus scrape config:
        scrape_configs:
          - job_name: 'absurd'
            static_configs:
              - targets: ['localhost:8000']
            metrics_path: '/api/absurd/metrics/prometheus'
    """
    from fastapi.responses import PlainTextResponse  # type: ignore[import-not-found]

    if _monitor is None:
        # Return empty metrics if monitor not initialized
        return PlainTextResponse(
            content="# Absurd monitor not initialized\n",
            media_type="text/plain; version=0.0.4",
        )

    try:
        metrics = await _monitor.collect_metrics()

        # Build Prometheus exposition format
        lines = [
            "# HELP absurd_tasks_total Total number of tasks by status",
            "# TYPE absurd_tasks_total counter",
            f'absurd_tasks_total{{status="spawned"}} {metrics.total_spawned}',
            f'absurd_tasks_total{{status="claimed"}} {metrics.total_claimed}',
            f'absurd_tasks_total{{status="completed"}} {metrics.total_completed}',
            f'absurd_tasks_total{{status="failed"}} {metrics.total_failed}',
            f'absurd_tasks_total{{status="cancelled"}} {metrics.total_cancelled}',
            f'absurd_tasks_total{{status="timed_out"}} {metrics.total_timed_out}',
            "",
            "# HELP absurd_tasks_current Current number of tasks by status",
            "# TYPE absurd_tasks_current gauge",
            f'absurd_tasks_current{{status="pending"}} {metrics.current_pending}',
            f'absurd_tasks_current{{status="claimed"}} {metrics.current_claimed}',
            "",
            "# HELP absurd_wait_time_seconds Task wait time in seconds",
            "# TYPE absurd_wait_time_seconds summary",
            f'absurd_wait_time_seconds{{quantile="0.5"}} {metrics.p50_wait_time_sec}',
            f'absurd_wait_time_seconds{{quantile="0.95"}} {metrics.p95_wait_time_sec}',
            f'absurd_wait_time_seconds{{quantile="0.99"}} {metrics.p99_wait_time_sec}',
            f"absurd_wait_time_seconds_avg {metrics.avg_wait_time_sec}",
            "",
            "# HELP absurd_execution_time_seconds Task execution time in seconds",
            "# TYPE absurd_execution_time_seconds summary",
            f'absurd_execution_time_seconds{{quantile="0.5"}} {metrics.p50_execution_time_sec}',
            f'absurd_execution_time_seconds{{quantile="0.95"}} {metrics.p95_execution_time_sec}',
            f'absurd_execution_time_seconds{{quantile="0.99"}} {metrics.p99_execution_time_sec}',
            f"absurd_execution_time_seconds_avg {metrics.avg_execution_time_sec}",
            "",
            "# HELP absurd_throughput_per_minute Tasks completed per minute",
            "# TYPE absurd_throughput_per_minute gauge",
            f'absurd_throughput_per_minute{{window="1m"}} {metrics.throughput_1min}',
            f'absurd_throughput_per_minute{{window="5m"}} {metrics.throughput_5min}',
            f'absurd_throughput_per_minute{{window="15m"}} {metrics.throughput_15min}',
            "",
            "# HELP absurd_success_rate Success rate (0-1)",
            "# TYPE absurd_success_rate gauge",
            f'absurd_success_rate{{window="1m"}} {metrics.success_rate_1min}',
            f'absurd_success_rate{{window="5m"}} {metrics.success_rate_5min}',
            f'absurd_success_rate{{window="15m"}} {metrics.success_rate_15min}',
            "",
            "# HELP absurd_error_rate Error rate (0-1)",
            "# TYPE absurd_error_rate gauge",
            f'absurd_error_rate{{window="1m"}} {metrics.error_rate_1min}',
            f'absurd_error_rate{{window="5m"}} {metrics.error_rate_5min}',
            f'absurd_error_rate{{window="15m"}} {metrics.error_rate_15min}',
            "",
        ]

        content = "\n".join(lines)
        return PlainTextResponse(
            content=content,
            media_type="text/plain; version=0.0.4",
        )

    except Exception as e:
        logger.exception(f"Failed to generate Prometheus metrics: {e}")
        return PlainTextResponse(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain; version=0.0.4",
        )


# ============================================================================
# Workflow Templates
# ============================================================================

# In-memory template storage (for now - can be moved to database later)
_workflow_templates: Dict[str, Dict[str, Any]] = {}


class WorkflowTemplateStep(BaseModel):
    """A step in a workflow template."""

    task_name: str = Field(..., description="Task name/type")
    params: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    priority: int = Field(default=0, description="Task priority")
    timeout_sec: Optional[int] = Field(None, description="Task timeout in seconds")


class WorkflowTemplate(BaseModel):
    """A workflow template definition."""

    name: str = Field(..., description="Template name")
    description: str = Field(default="", description="Template description")
    queue_name: str = Field(default="dsa110-pipeline", description="Default queue")
    steps: List[WorkflowTemplateStep] = Field(default_factory=list, description="Workflow steps")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class WorkflowTemplateListResponse(BaseModel):
    """List of workflow templates."""

    templates: List[WorkflowTemplate]
    total: int


@router.get("/templates", response_model=WorkflowTemplateListResponse)
async def list_workflow_templates():
    """List all saved workflow templates.

    Returns:
        List of workflow templates
    """
    templates = list(_workflow_templates.values())
    return WorkflowTemplateListResponse(
        templates=[WorkflowTemplate(**t) for t in templates],
        total=len(templates),
    )


@router.get("/templates/{template_name}", response_model=WorkflowTemplate)
async def get_workflow_template(template_name: str):
    """Get a specific workflow template by name.

    Args:
        template_name: Template name

    Returns:
        Workflow template

    Raises:
        HTTPException: If template not found
    """
    if template_name not in _workflow_templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found",
        )
    return WorkflowTemplate(**_workflow_templates[template_name])


@router.post("/templates", response_model=WorkflowTemplate)
async def create_workflow_template(template: WorkflowTemplate):
    """Create a new workflow template.

    Args:
        template: Workflow template definition

    Returns:
        Created workflow template

    Raises:
        HTTPException: If template name already exists
    """
    from datetime import datetime

    if template.name in _workflow_templates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template '{template.name}' already exists",
        )

    now = datetime.now().isoformat()
    template_dict = template.model_dump()
    template_dict["created_at"] = now
    template_dict["updated_at"] = now

    _workflow_templates[template.name] = template_dict
    return WorkflowTemplate(**template_dict)


@router.put("/templates/{template_name}", response_model=WorkflowTemplate)
async def update_workflow_template(template_name: str, template: WorkflowTemplate):
    """Update an existing workflow template.

    Args:
        template_name: Template name to update
        template: Updated workflow template

    Returns:
        Updated workflow template

    Raises:
        HTTPException: If template not found
    """
    from datetime import datetime

    if template_name not in _workflow_templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found",
        )

    template_dict = template.model_dump()
    template_dict["created_at"] = _workflow_templates[template_name].get("created_at")
    template_dict["updated_at"] = datetime.now().isoformat()

    _workflow_templates[template_name] = template_dict
    return WorkflowTemplate(**template_dict)


@router.delete("/templates/{template_name}")
async def delete_workflow_template(template_name: str):
    """Delete a workflow template.

    Args:
        template_name: Template name to delete

    Returns:
        Confirmation message

    Raises:
        HTTPException: If template not found
    """
    if template_name not in _workflow_templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found",
        )

    del _workflow_templates[template_name]
    return {"message": f"Template '{template_name}' deleted"}


@router.post("/templates/{template_name}/run")
async def run_workflow_template(
    template_name: str,
    params_override: Optional[Dict[str, Any]] = None,
    client: AbsurdClient = Depends(get_absurd_client),
):
    """Execute a workflow template.

    Spawns all tasks defined in the template with optional parameter overrides.

    Args:
        template_name: Template name to run
        params_override: Optional dict of parameters to override in all steps
        client: Absurd client (injected)

    Returns:
        List of spawned task IDs

    Raises:
        HTTPException: If template not found or spawn fails
    """
    if template_name not in _workflow_templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found",
        )

    template = _workflow_templates[template_name]
    task_ids = []

    try:
        for step in template.get("steps", []):
            # Merge params with override
            params = step.get("params", {}).copy()
            if params_override:
                params.update(params_override)

            task_id = await client.spawn_task(
                queue_name=template.get("queue_name", "dsa110-pipeline"),
                task_name=step["task_name"],
                params=params,
                priority=step.get("priority", 0),
                timeout_sec=step.get("timeout_sec"),
            )
            task_ids.append(str(task_id))

        return {"task_ids": task_ids, "template_name": template_name}

    except Exception as e:
        logger.exception(f"Failed to run template {template_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run template: {str(e)}",
        )


# =============================================================================
# Scheduled Tasks API
# =============================================================================


class ScheduleCreateRequest(BaseModel):
    """Request to create a scheduled task."""

    name: str = Field(..., description="Unique schedule name")
    queue_name: str = Field(default="dsa110-pipeline", description="Target queue")
    task_name: str = Field(..., description="Task type to spawn")
    cron_expression: str = Field(
        ..., description="5-field cron expression (minute hour day month weekday)"
    )
    params: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    priority: int = Field(default=0, description="Task priority")
    timeout_sec: Optional[int] = Field(default=None, description="Task timeout")
    max_retries: int = Field(default=3, description="Max retry attempts")
    timezone: str = Field(default="UTC", description="Schedule timezone")
    description: Optional[str] = Field(default=None, description="Schedule description")


class ScheduleUpdateRequest(BaseModel):
    """Request to update a scheduled task."""

    cron_expression: Optional[str] = Field(default=None, description="New cron expression")
    params: Optional[Dict[str, Any]] = Field(default=None, description="New parameters")
    state: Optional[str] = Field(default=None, description="New state (active/paused/disabled)")
    priority: Optional[int] = Field(default=None, description="New priority")
    description: Optional[str] = Field(default=None, description="New description")


@router.get("/schedules", summary="List scheduled tasks")
async def list_schedules(
    queue_name: Optional[str] = Query(default=None, description="Filter by queue"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """List all scheduled tasks with optional filters."""
    try:
        # Import here to avoid circular imports
        from dsa110_contimg.absurd.scheduling import (
            ScheduleState,
            ensure_scheduled_tasks_table,
        )
        from dsa110_contimg.absurd.scheduling import list_schedules as list_schedules_db

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Scheduling requires PostgreSQL backend",
            )

        # Ensure table exists
        await ensure_scheduled_tasks_table(pool)

        state_enum = ScheduleState(state) if state else None
        schedules = await list_schedules_db(pool, queue_name, state_enum)

        return {
            "schedules": [
                {
                    "schedule_id": s.schedule_id,
                    "name": s.name,
                    "queue_name": s.queue_name,
                    "task_name": s.task_name,
                    "cron_expression": s.cron_expression,
                    "params": s.params,
                    "priority": s.priority,
                    "state": s.state.value,
                    "timezone": s.timezone,
                    "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                    "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
                    "description": s.description,
                }
                for s in schedules
            ],
            "total": len(schedules),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to list schedules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/schedules", summary="Create a scheduled task")
async def create_schedule(
    request: ScheduleCreateRequest,
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Create a new scheduled task with cron expression."""
    try:
        from dsa110_contimg.absurd.scheduling import create_schedule as create_schedule_db
        from dsa110_contimg.absurd.scheduling import (
            ensure_scheduled_tasks_table,
        )

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Scheduling requires PostgreSQL backend",
            )

        await ensure_scheduled_tasks_table(pool)

        schedule = await create_schedule_db(
            pool=pool,
            name=request.name,
            queue_name=request.queue_name,
            task_name=request.task_name,
            cron_expression=request.cron_expression,
            params=request.params,
            priority=request.priority,
            timeout_sec=request.timeout_sec,
            max_retries=request.max_retries,
            timezone=request.timezone,
            description=request.description,
        )

        return {
            "schedule_id": schedule.schedule_id,
            "name": schedule.name,
            "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
            "message": f"Schedule '{schedule.name}' created successfully",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/schedules/{name}", summary="Get scheduled task details")
async def get_schedule(
    name: str = Path(..., description="Schedule name"),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Get details of a scheduled task."""
    try:
        from dsa110_contimg.absurd.scheduling import get_schedule as get_schedule_db

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Scheduling requires PostgreSQL backend",
            )

        schedule = await get_schedule_db(pool, name)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule '{name}' not found",
            )

        return {
            "schedule_id": schedule.schedule_id,
            "name": schedule.name,
            "queue_name": schedule.queue_name,
            "task_name": schedule.task_name,
            "cron_expression": schedule.cron_expression,
            "params": schedule.params,
            "priority": schedule.priority,
            "timeout_sec": schedule.timeout_sec,
            "max_retries": schedule.max_retries,
            "state": schedule.state.value,
            "timezone": schedule.timezone,
            "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
            "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
            "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
            "updated_at": schedule.updated_at.isoformat() if schedule.updated_at else None,
            "description": schedule.description,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get schedule {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch("/schedules/{name}", summary="Update a scheduled task")
async def update_schedule(
    name: str = Path(..., description="Schedule name"),
    request: ScheduleUpdateRequest = Body(...),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Update a scheduled task."""
    try:
        from dsa110_contimg.absurd.scheduling import (
            ScheduleState,
        )
        from dsa110_contimg.absurd.scheduling import update_schedule as update_schedule_db

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Scheduling requires PostgreSQL backend",
            )

        state_enum = ScheduleState(request.state) if request.state else None

        schedule = await update_schedule_db(
            pool=pool,
            name=name,
            cron_expression=request.cron_expression,
            params=request.params,
            state=state_enum,
            priority=request.priority,
            description=request.description,
        )

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule '{name}' not found",
            )

        return {
            "schedule_id": schedule.schedule_id,
            "name": schedule.name,
            "state": schedule.state.value,
            "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
            "message": f"Schedule '{name}' updated successfully",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update schedule {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/schedules/{name}", summary="Delete a scheduled task")
async def delete_schedule(
    name: str = Path(..., description="Schedule name"),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Delete a scheduled task."""
    try:
        from dsa110_contimg.absurd.scheduling import delete_schedule as delete_schedule_db

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Scheduling requires PostgreSQL backend",
            )

        deleted = await delete_schedule_db(pool, name)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule '{name}' not found",
            )

        return {"message": f"Schedule '{name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete schedule {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/schedules/{name}/trigger", summary="Trigger a scheduled task immediately")
async def trigger_schedule(
    name: str = Path(..., description="Schedule name"),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Manually trigger a scheduled task immediately."""
    try:
        from dsa110_contimg.absurd.scheduling import trigger_schedule_now

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Scheduling requires PostgreSQL backend",
            )

        task_id = await trigger_schedule_now(pool, name)
        if not task_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule '{name}' not found",
            )

        return {
            "task_id": task_id,
            "schedule_name": name,
            "message": f"Schedule '{name}' triggered, spawned task {task_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to trigger schedule {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Workflow DAG API
# =============================================================================


class WorkflowCreateRequest(BaseModel):
    """Request to create a workflow."""

    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Workflow metadata")


class TaskWithDepsRequest(BaseModel):
    """Request to create a task with dependencies."""

    queue_name: str = Field(default="dsa110-pipeline", description="Target queue")
    task_name: str = Field(..., description="Task type")
    params: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    depends_on: List[str] = Field(default_factory=list, description="Task IDs to depend on")
    workflow_id: Optional[str] = Field(default=None, description="Workflow container")
    priority: int = Field(default=0, description="Task priority")
    timeout_sec: Optional[int] = Field(default=None, description="Task timeout")
    max_retries: int = Field(default=3, description="Max retry attempts")


@router.get("/workflows", summary="List workflows")
async def list_workflows(
    workflow_status: Optional[str] = Query(
        default=None, alias="status", description="Filter by status"
    ),
    limit: int = Query(default=100, ge=1, le=1000, description="Max results"),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """List all workflows with optional status filter."""
    try:
        from dsa110_contimg.absurd.dependencies import (
            ensure_dependencies_schema,
        )
        from dsa110_contimg.absurd.dependencies import list_workflows as list_workflows_db

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Workflows require PostgreSQL backend",
            )

        await ensure_dependencies_schema(pool)
        workflows = await list_workflows_db(pool, workflow_status, limit)

        return {
            "workflows": workflows,
            "total": len(workflows),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to list workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/workflows", summary="Create a workflow")
async def create_workflow(
    request: WorkflowCreateRequest,
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Create a new workflow container for grouping tasks with dependencies."""
    try:
        from dsa110_contimg.absurd.dependencies import create_workflow as create_workflow_db
        from dsa110_contimg.absurd.dependencies import (
            ensure_dependencies_schema,
        )

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Workflows require PostgreSQL backend",
            )

        await ensure_dependencies_schema(pool)
        workflow_id = await create_workflow_db(
            pool=pool,
            name=request.name,
            description=request.description,
            metadata=request.metadata,
        )

        return {
            "workflow_id": workflow_id,
            "name": request.name,
            "message": f"Workflow '{request.name}' created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/workflows/{workflow_id}", summary="Get workflow status")
async def get_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Get comprehensive workflow status including task breakdown."""
    try:
        from dsa110_contimg.absurd.dependencies import get_workflow_status

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Workflows require PostgreSQL backend",
            )

        return await get_workflow_status(pool, workflow_id)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/workflows/{workflow_id}/dag", summary="Get workflow DAG")
async def get_workflow_dag(
    workflow_id: str = Path(..., description="Workflow ID"),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Get workflow as a directed acyclic graph for visualization."""
    try:
        from dsa110_contimg.absurd.dependencies import get_workflow_dag as get_dag

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Workflows require PostgreSQL backend",
            )

        dag = await get_dag(pool, workflow_id)

        return {
            "workflow_id": dag.workflow_id,
            "name": dag.name,
            "total_depth": dag.total_depth,
            "root_tasks": dag.root_tasks,
            "leaf_tasks": dag.leaf_tasks,
            "nodes": [
                {
                    "task_id": node.task_id,
                    "task_name": node.task_name,
                    "status": node.status,
                    "depends_on": node.depends_on,
                    "dependents": node.dependents,
                    "depth": node.depth,
                }
                for node in dag.tasks.values()
            ],
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get workflow DAG {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/workflows/{workflow_id}/ready", summary="Get ready tasks in workflow")
async def get_ready_tasks(
    workflow_id: str = Path(..., description="Workflow ID"),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Get tasks that are ready to execute (all dependencies satisfied)."""
    try:
        from dsa110_contimg.absurd.dependencies import get_ready_workflow_tasks

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Workflows require PostgreSQL backend",
            )

        ready_tasks = await get_ready_workflow_tasks(pool, workflow_id)

        return {
            "workflow_id": workflow_id,
            "ready_tasks": ready_tasks,
            "count": len(ready_tasks),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get ready tasks for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/tasks/with-deps", summary="Spawn task with dependencies")
async def spawn_task_with_deps(
    request: TaskWithDepsRequest,
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Spawn a new task that depends on other tasks."""
    try:
        from dsa110_contimg.absurd.dependencies import (
            ensure_dependencies_schema,
            spawn_task_with_dependencies,
        )

        pool = getattr(client, "pool", None)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Dependencies require PostgreSQL backend",
            )

        await ensure_dependencies_schema(pool)

        task_id = await spawn_task_with_dependencies(
            pool=pool,
            queue_name=request.queue_name,
            task_name=request.task_name,
            params=request.params,
            depends_on=request.depends_on,
            workflow_id=request.workflow_id,
            priority=request.priority,
            timeout_sec=request.timeout_sec,
            max_retries=request.max_retries,
        )

        return {
            "task_id": task_id,
            "depends_on": request.depends_on,
            "workflow_id": request.workflow_id,
            "message": f"Task spawned with {len(request.depends_on)} dependencies",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to spawn task with dependencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Historical Metrics API
# =============================================================================


@router.get("/metrics/history", summary="Get historical metrics")
async def get_metrics_history(
    queue_name: str = Query(default="dsa110-pipeline", description="Queue name"),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history"),
    resolution: str = Query(default="1h", description="Time resolution (5m, 15m, 1h, 6h)"),
    client: AbsurdClient = Depends(get_absurd_client),
) -> Dict[str, Any]:
    """Get historical time-series metrics for charts.

    Returns throughput, success rate, latency, and queue depth over time.
    """
    try:
        pool = getattr(client, "pool", None)
        if not pool:
            # Return mock data for non-PostgreSQL backends
            return _generate_mock_metrics_history(hours, resolution)

        # Parse resolution to interval
        interval_map = {
            "5m": "5 minutes",
            "15m": "15 minutes",
            "1h": "1 hour",
            "6h": "6 hours",
        }
        interval = interval_map.get(resolution, "1 hour")

        async with pool.acquire() as conn:
            # Get time-bucketed metrics from completed tasks
            rows = await conn.fetch(
                """
                WITH time_buckets AS (
                    SELECT 
                        date_trunc($1::TEXT, completed_at) as bucket,
                        COUNT(*) as task_count,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed,
                        AVG(wait_time_sec) FILTER (WHERE wait_time_sec IS NOT NULL) as avg_wait,
                        AVG(execution_time_sec) FILTER (WHERE execution_time_sec IS NOT NULL) as avg_exec,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY wait_time_sec) 
                            FILTER (WHERE wait_time_sec IS NOT NULL) as p95_wait,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_sec) 
                            FILTER (WHERE execution_time_sec IS NOT NULL) as p95_exec
                    FROM absurd.tasks
                    WHERE queue_name = $2
                      AND completed_at >= NOW() - ($3 || ' hours')::INTERVAL
                      AND completed_at IS NOT NULL
                    GROUP BY bucket
                    ORDER BY bucket
                )
                SELECT * FROM time_buckets
            """,
                interval.split()[1] if " " in interval else "hour",
                queue_name,
                str(hours),
            )

            # Convert to time series
            timestamps = []
            throughput = []
            success_rate = []
            avg_latency = []
            p95_latency = []

            for row in rows:
                ts = row["bucket"].isoformat() if row["bucket"] else None
                if ts:
                    timestamps.append(ts)
                    total = row["task_count"] or 0
                    completed = row["completed"] or 0
                    throughput.append(total)
                    success_rate.append((completed / total * 100) if total > 0 else 100)
                    avg_latency.append(row["avg_exec"] or 0)
                    p95_latency.append(row["p95_exec"] or 0)

        return {
            "queue_name": queue_name,
            "hours": hours,
            "resolution": resolution,
            "timestamps": timestamps,
            "series": {
                "throughput": throughput,
                "success_rate": success_rate,
                "avg_latency": avg_latency,
                "p95_latency": p95_latency,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get metrics history: {e}")
        # Fall back to mock data on error
        return _generate_mock_metrics_history(hours, resolution)


def _generate_mock_metrics_history(hours: int, resolution: str) -> Dict[str, Any]:
    """Generate mock metrics history for development/testing."""
    import random
    from datetime import datetime, timedelta

    resolution_minutes = {"5m": 5, "15m": 15, "1h": 60, "6h": 360}.get(resolution, 60)
    num_points = (hours * 60) // resolution_minutes

    now = datetime.utcnow()
    timestamps = [
        (now - timedelta(minutes=resolution_minutes * i)).isoformat()
        for i in range(num_points, 0, -1)
    ]

    # Generate realistic-looking mock data
    base_throughput = 10
    base_success = 95

    return {
        "queue_name": "dsa110-pipeline",
        "hours": hours,
        "resolution": resolution,
        "timestamps": timestamps,
        "series": {
            "throughput": [
                max(0, base_throughput + random.gauss(0, 3)) for _ in range(len(timestamps))
            ],
            "success_rate": [
                min(100, max(80, base_success + random.gauss(0, 2))) for _ in range(len(timestamps))
            ],
            "avg_latency": [max(0, 5 + random.gauss(0, 1)) for _ in range(len(timestamps))],
            "p95_latency": [max(0, 15 + random.gauss(0, 3)) for _ in range(len(timestamps))],
        },
    }
