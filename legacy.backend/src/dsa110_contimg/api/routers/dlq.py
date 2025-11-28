"""
FastAPI router for Dead Letter Queue (DLQ) management.

Provides REST API endpoints for viewing, retrying, and resolving
failed operations stored in the dead letter queue.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status  # type: ignore[import-not-found]
from pydantic import BaseModel, Field  # type: ignore[import-not-found]

from dsa110_contimg.api.websocket_manager import manager
from dsa110_contimg.pipeline.dead_letter_queue import (
    DeadLetterQueue,
    DeadLetterQueueItem,
    DLQStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dlq"])

# Default DLQ database path
_dlq: Optional[DeadLetterQueue] = None


def get_dlq() -> DeadLetterQueue:
    """Get or initialize the Dead Letter Queue."""
    global _dlq
    if _dlq is None:
        import os

        db_path = (
            Path(os.environ.get("CONTIMG_STATE_DIR", "/data/dsa110-contimg/state")) / "dlq.sqlite3"
        )
        _dlq = DeadLetterQueue(db_path)
    return _dlq


# Pydantic models for request/response


class DLQItemResponse(BaseModel):
    """Dead letter queue item response."""

    id: int
    component: str
    operation: str
    error_type: str
    error_message: str
    context: Dict[str, Any]
    created_at: float
    retry_count: int
    status: str
    resolved_at: Optional[float] = None
    resolution_note: Optional[str] = None


class DLQListResponse(BaseModel):
    """List of DLQ items response."""

    items: List[DLQItemResponse]
    total: int


class DLQStatsResponse(BaseModel):
    """DLQ statistics response."""

    pending: int
    retrying: int
    resolved: int
    failed: int
    total: int
    by_component: Dict[str, int]
    by_error_type: Dict[str, int]


class DLQActionRequest(BaseModel):
    """Request to perform an action on a DLQ item."""

    note: Optional[str] = Field(None, description="Optional note for the action")


class DLQRetryRequest(BaseModel):
    """Request to retry a DLQ item."""

    note: Optional[str] = Field(None, description="Optional note for the retry")
    resubmit_to_absurd: bool = Field(
        False, description="If True, resubmit to Absurd queue instead of immediate retry"
    )


# API endpoints


@router.get("/items", response_model=DLQListResponse)
async def list_dlq_items(
    component: Optional[str] = Query(None, description="Filter by component"),
    dlq_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List dead letter queue items.

    Args:
        component: Filter by component name (e.g., 'calibration', 'imaging')
        dlq_status: Filter by status ('pending', 'retrying', 'resolved', 'failed')
        limit: Maximum number of items to return
        offset: Offset for pagination

    Returns:
        List of DLQ items matching criteria
    """
    dlq = get_dlq()

    # Get items (the current implementation doesn't support offset, but we handle it)
    if dlq_status:
        items = dlq.get_pending(component=component, limit=limit + offset)
        # Filter by status manually since get_pending only returns pending
        items = [i for i in items if i.status.value == dlq_status]
    else:
        items = dlq.get_pending(component=component, limit=limit + offset)

    # Apply offset
    items = items[offset : offset + limit]

    # Convert to response format
    response_items = [
        DLQItemResponse(
            id=item.id,
            component=item.component,
            operation=item.operation,
            error_type=item.error_type,
            error_message=item.error_message,
            context=item.context,
            created_at=item.created_at,
            retry_count=item.retry_count,
            status=item.status.value,
            resolved_at=item.resolved_at,
            resolution_note=item.resolution_note,
        )
        for item in items
    ]

    return DLQListResponse(items=response_items, total=len(response_items))


@router.get("/items/{item_id}", response_model=DLQItemResponse)
async def get_dlq_item(item_id: int):
    """Get a specific DLQ item by ID.

    Args:
        item_id: The DLQ item ID

    Returns:
        DLQ item details

    Raises:
        HTTPException: If item not found
    """
    dlq = get_dlq()

    # Get item by ID
    item = dlq.get_by_id(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"DLQ item {item_id} not found"
        )

    return DLQItemResponse(
        id=item.id,
        component=item.component,
        operation=item.operation,
        error_type=item.error_type,
        error_message=item.error_message,
        context=item.context,
        created_at=item.created_at,
        retry_count=item.retry_count,
        status=item.status.value,
        resolved_at=item.resolved_at,
        resolution_note=item.resolution_note,
    )


@router.post("/items/{item_id}/retry")
async def retry_dlq_item(item_id: int, request: Optional[DLQRetryRequest] = None):
    """Retry a failed operation.

    Args:
        item_id: The DLQ item ID
        request: Retry options

    Returns:
        Success message with new status

    Raises:
        HTTPException: If item not found or cannot be retried
    """
    if request is None:
        request = DLQRetryRequest()

    dlq = get_dlq()

    try:
        dlq.mark_retrying(item_id)

        if request.resubmit_to_absurd:
            # Resubmit to Absurd queue
            item = dlq.get_by_id(item_id)
            if item:
                task_id = await _resubmit_to_absurd(item)
                if task_id:
                    dlq.resolve(item_id, note=f"Resubmitted to Absurd as task {task_id}")
                    # Emit WebSocket event
                    await manager.broadcast(
                        {
                            "type": "dlq_update",
                            "action": "resolved",
                            "item_id": item_id,
                            "task_id": task_id,
                        }
                    )
                    return {
                        "message": f"Item {item_id} resubmitted to Absurd",
                        "task_id": task_id,
                        "status": "resolved",
                    }

        # Emit WebSocket event
        await manager.broadcast(
            {
                "type": "dlq_update",
                "action": "retrying",
                "item_id": item_id,
            }
        )

        return {
            "message": f"Item {item_id} marked for retry",
            "status": "retrying",
        }

    except Exception as e:
        logger.exception(f"Failed to retry DLQ item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retry: {str(e)}"
        )


@router.post("/items/{item_id}/resolve")
async def resolve_dlq_item(item_id: int, request: Optional[DLQActionRequest] = None):
    """Mark a DLQ item as resolved.

    Args:
        item_id: The DLQ item ID
        request: Resolution options

    Returns:
        Success message

    Raises:
        HTTPException: If item not found
    """
    if request is None:
        request = DLQActionRequest()

    dlq = get_dlq()

    try:
        dlq.resolve(item_id, note=request.note)
        # Emit WebSocket event
        await manager.broadcast(
            {
                "type": "dlq_update",
                "action": "resolved",
                "item_id": item_id,
            }
        )
        return {
            "message": f"Item {item_id} marked as resolved",
            "status": "resolved",
        }
    except Exception as e:
        logger.exception(f"Failed to resolve DLQ item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to resolve: {str(e)}"
        )


@router.post("/items/{item_id}/fail")
async def fail_dlq_item(item_id: int, request: Optional[DLQActionRequest] = None):
    """Mark a DLQ item as permanently failed.

    Args:
        item_id: The DLQ item ID
        request: Failure options

    Returns:
        Success message

    Raises:
        HTTPException: If item not found
    """
    if request is None:
        request = DLQActionRequest()

    dlq = get_dlq()

    try:
        dlq.mark_failed(item_id, note=request.note)
        # Emit WebSocket event
        await manager.broadcast(
            {
                "type": "dlq_update",
                "action": "failed",
                "item_id": item_id,
            }
        )
        return {
            "message": f"Item {item_id} marked as failed",
            "status": "failed",
        }
    except Exception as e:
        logger.exception(f"Failed to mark DLQ item {item_id} as failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark as failed: {str(e)}",
        )


@router.get("/stats", response_model=DLQStatsResponse)
async def get_dlq_stats():
    """Get DLQ statistics.

    Returns:
        Statistics including counts by status, component, and error type
    """
    dlq = get_dlq()

    stats = dlq.get_stats()

    return DLQStatsResponse(
        pending=stats.get("pending", 0),
        retrying=stats.get("retrying", 0),
        resolved=stats.get("resolved", 0),
        failed=stats.get("failed", 0),
        total=stats.get("total", 0),
        by_component=stats.get("by_component", {}),
        by_error_type=stats.get("by_error_type", {}),
    )


@router.delete("/items/{item_id}")
async def delete_dlq_item(item_id: int):
    """Delete a DLQ item permanently.

    Args:
        item_id: The DLQ item ID

    Returns:
        Success message

    Raises:
        HTTPException: If item not found
    """
    dlq = get_dlq()

    try:
        dlq.delete(item_id)
        # Emit WebSocket event
        await manager.broadcast(
            {
                "type": "dlq_update",
                "action": "deleted",
                "item_id": item_id,
            }
        )
        return {"message": f"Item {item_id} deleted"}
    except Exception as e:
        logger.exception(f"Failed to delete DLQ item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete: {str(e)}"
        )


# Helper functions


async def _resubmit_to_absurd(item: DeadLetterQueueItem) -> Optional[str]:
    """Resubmit a DLQ item to the Absurd queue.

    Args:
        item: The DLQ item to resubmit

    Returns:
        Task ID if successful, None otherwise
    """
    from dsa110_contimg.api.routers.absurd import _client, _config

    if _client is None or _config is None or not _config.enabled:
        logger.warning("Cannot resubmit to Absurd: client not initialized")
        return None

    try:
        # Map component/operation to Absurd task name
        task_name = _map_to_task_name(item.component, item.operation)
        if not task_name:
            logger.warning(f"Cannot map {item.component}/{item.operation} to Absurd task")
            return None

        # Build params from context
        params = {
            "config": item.context.get("config"),
            "inputs": item.context.get("inputs", {}),
            "outputs": item.context.get("outputs", {}),
            "dlq_retry": True,
            "dlq_item_id": item.id,
        }

        # Spawn task
        task_id = await _client.spawn_task(
            queue_name=_config.queue_name,
            task_name=task_name,
            params=params,
            priority=10,  # Higher priority for retries
        )

        logger.info(f"Resubmitted DLQ item {item.id} as Absurd task {task_id}")
        return str(task_id)

    except Exception as e:
        logger.exception(f"Failed to resubmit DLQ item {item.id} to Absurd: {e}")
        return None


def _map_to_task_name(component: str, operation: str) -> Optional[str]:
    """Map component/operation to Absurd task name."""
    mapping = {
        ("conversion", "convert"): "convert-uvh5-to-ms",
        ("calibration", "solve"): "calibration-solve",
        ("calibration", "apply"): "calibration-apply",
        ("imaging", "image"): "imaging",
        ("imaging", "wsclean"): "imaging",
        ("validation", "validate"): "validation",
        ("photometry", "measure"): "photometry",
        ("crossmatch", "crossmatch"): "crossmatch",
    }

    return mapping.get((component, operation))
