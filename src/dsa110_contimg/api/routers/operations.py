"""Operations API endpoints for Dead Letter Queue and Circuit Breakers."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from dsa110_contimg.pipeline.circuit_breaker import (
    CircuitState,
    calibration_solve_circuit_breaker,
    ese_detection_circuit_breaker,
    photometry_circuit_breaker,
)
from dsa110_contimg.pipeline.dead_letter_queue import (
    get_dlq,
)

router = APIRouter()


# ============================================================================
# Dead Letter Queue Models
# ============================================================================


class DLQItemResponse(BaseModel):
    """Dead letter queue item response."""

    id: int
    component: str
    operation: str
    error_type: str
    error_message: str
    context: dict
    created_at: float
    retry_count: int
    status: str
    resolved_at: Optional[float] = None
    resolution_note: Optional[str] = None

    class Config:
        from_attributes = True


class DLQStatsResponse(BaseModel):
    """Dead letter queue statistics."""

    total: int
    pending: int
    retrying: int
    resolved: int
    failed: int


class DLQRetryRequest(BaseModel):
    """Request to retry a DLQ item."""

    note: Optional[str] = None


class DLQResolveRequest(BaseModel):
    """Request to resolve a DLQ item."""

    note: Optional[str] = None


# ============================================================================
# Circuit Breaker Models
# ============================================================================


class CircuitBreakerState(BaseModel):
    """Circuit breaker state."""

    name: str
    state: str  # "closed", "open", "half_open"
    failure_count: int
    last_failure_time: Optional[float] = None
    recovery_timeout: float


class CircuitBreakerListResponse(BaseModel):
    """List of circuit breaker states."""

    circuit_breakers: List[CircuitBreakerState]


# ============================================================================
# Dead Letter Queue Endpoints
# ============================================================================


@router.get("/operations/dlq/items", response_model=List[DLQItemResponse])
def get_dlq_items(
    component: Optional[str] = Query(None, description="Filter by component"),
    status: Optional[str] = Query(
        None, description="Filter by status (pending, retrying, resolved, failed)"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get dead letter queue items."""
    dlq = get_dlq()

    # Get pending items (we'll filter by status in Python since DLQ doesn't support it yet)
    items = dlq.get_pending(component=component, limit=limit + offset)

    # Filter by status if provided
    if status:
        items = [item for item in items if item.status.value == status]

    # Apply pagination
    items = items[offset : offset + limit]

    # Convert to response models
    return [
        DLQItemResponse(
            id=item.id or 0,
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


@router.get("/operations/dlq/items/{item_id}", response_model=DLQItemResponse)
def get_dlq_item(item_id: int):
    """Get a specific dead letter queue item."""
    dlq = get_dlq()

    # Get all pending items and find the one we want
    items = dlq.get_pending(limit=10000)
    item = next((i for i in items if i.id == item_id), None)

    if not item:
        raise HTTPException(status_code=404, detail=f"DLQ item {item_id} not found")

    return DLQItemResponse(
        id=item.id or 0,
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


@router.post("/operations/dlq/items/{item_id}/retry")
def retry_dlq_item(item_id: int, request: DLQRetryRequest):
    """Retry a failed operation from the dead letter queue."""
    dlq = get_dlq()

    # Mark as retrying
    dlq.mark_retrying(item_id)

    return {"status": "retrying", "item_id": item_id, "note": request.note}


@router.post("/operations/dlq/items/{item_id}/resolve")
def resolve_dlq_item(item_id: int, request: DLQResolveRequest):
    """Mark a dead letter queue item as resolved."""
    dlq = get_dlq()

    dlq.mark_resolved(item_id, note=request.note)

    return {"status": "resolved", "item_id": item_id, "note": request.note}


@router.post("/operations/dlq/items/{item_id}/fail")
def fail_dlq_item(item_id: int, request: DLQResolveRequest):
    """Mark a dead letter queue item as permanently failed."""
    dlq = get_dlq()

    dlq.mark_failed(item_id, note=request.note)

    return {"status": "failed", "item_id": item_id, "note": request.note}


@router.get("/operations/dlq/stats", response_model=DLQStatsResponse)
def get_dlq_stats():
    """Get dead letter queue statistics."""
    dlq = get_dlq()
    stats = dlq.get_stats()

    return DLQStatsResponse(
        total=stats["total"],
        pending=stats["pending"],
        retrying=stats["retrying"],
        resolved=stats["resolved"],
        failed=stats["failed"],
    )


# ============================================================================
# Circuit Breaker Endpoints
# ============================================================================


@router.get("/operations/circuit-breakers", response_model=CircuitBreakerListResponse)
def get_circuit_breakers():
    """Get all circuit breaker states."""
    breakers = [
        CircuitBreakerState(
            name="ese_detection",
            state=ese_detection_circuit_breaker.state.value,
            failure_count=ese_detection_circuit_breaker.failure_count,
            last_failure_time=ese_detection_circuit_breaker.last_failure_time,
            recovery_timeout=ese_detection_circuit_breaker.recovery_timeout,
        ),
        CircuitBreakerState(
            name="calibration_solve",
            state=calibration_solve_circuit_breaker.state.value,
            failure_count=calibration_solve_circuit_breaker.failure_count,
            last_failure_time=calibration_solve_circuit_breaker.last_failure_time,
            recovery_timeout=calibration_solve_circuit_breaker.recovery_timeout,
        ),
        CircuitBreakerState(
            name="photometry",
            state=photometry_circuit_breaker.state.value,
            failure_count=photometry_circuit_breaker.failure_count,
            last_failure_time=photometry_circuit_breaker.last_failure_time,
            recovery_timeout=photometry_circuit_breaker.recovery_timeout,
        ),
    ]

    return CircuitBreakerListResponse(circuit_breakers=breakers)


@router.get("/operations/circuit-breakers/{name}", response_model=CircuitBreakerState)
def get_circuit_breaker(name: str):
    """Get a specific circuit breaker state."""
    breaker_map = {
        "ese_detection": ese_detection_circuit_breaker,
        "calibration_solve": calibration_solve_circuit_breaker,
        "photometry": photometry_circuit_breaker,
    }

    breaker = breaker_map.get(name)
    if not breaker:
        raise HTTPException(status_code=404, detail=f"Circuit breaker '{name}' not found")

    return CircuitBreakerState(
        name=name,
        state=breaker.state.value,
        failure_count=breaker.failure_count,
        last_failure_time=breaker.last_failure_time,
        recovery_timeout=breaker.recovery_timeout,
    )


@router.post("/operations/circuit-breakers/{name}/reset")
def reset_circuit_breaker(name: str):
    """Reset a circuit breaker."""
    breaker_map = {
        "ese_detection": ese_detection_circuit_breaker,
        "calibration_solve": calibration_solve_circuit_breaker,
        "photometry": photometry_circuit_breaker,
    }

    breaker = breaker_map.get(name)
    if not breaker:
        raise HTTPException(status_code=404, detail=f"Circuit breaker '{name}' not found")

    # Reset circuit breaker
    breaker.state = CircuitState.CLOSED
    breaker.failure_count = 0
    breaker.last_failure_time = None

    return {"status": "reset", "name": name}
