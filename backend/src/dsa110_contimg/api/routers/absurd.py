"""
FastAPI router for Absurd workflow manager.

Provides REST API endpoints for spawning, querying, and managing
Absurd tasks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig
from dsa110_contimg.api.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["absurd"])

# Global client instance (initialized on startup)
_client: Optional[AbsurdClient] = None
_config: Optional[AbsurdConfig] = None


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
    global _client, _config

    _config = config

    if not config.enabled:
        logger.info("Absurd is disabled, skipping initialization")
        return

    logger.info("Initializing Absurd client...")
    _client = AbsurdClient(config.database_url, pool_min_size=2, pool_max_size=10)
    await _client.connect()
    logger.info("Absurd client initialized")


async def shutdown_absurd() -> None:
    """Shutdown Absurd client on application shutdown."""
    global _client

    if _client is not None:
        logger.info("Shutting down Absurd client...")
        await _client.close()
        _client = None
        logger.info("Absurd client shutdown complete")


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
