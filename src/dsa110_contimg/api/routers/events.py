"""API endpoints for event bus monitoring."""

import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from dsa110_contimg.pipeline.event_bus import EventType, get_event_bus

router = APIRouter()


@router.get("/stream")
def get_event_stream(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events"),
    since_minutes: Optional[int] = Query(None, ge=1, description="Only events from last N minutes"),
):
    """Get recent events from the event bus."""
    bus = get_event_bus()

    # Parse event type filter
    event_type_filter = None
    if event_type:
        try:
            event_type_filter = EventType(event_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type: {event_type}. Valid types: {[e.value for e in EventType]}",
            )

    # Calculate since timestamp
    since = None
    if since_minutes:
        since = time.time() - (since_minutes * 60)

    # Get events
    events = bus.get_history(event_type=event_type_filter, limit=limit, since=since)

    # Convert to dict format
    return [
        {
            **event.to_dict(),
            "timestamp_iso": datetime.fromtimestamp(event.timestamp).isoformat(),
        }
        for event in events
    ]


@router.get("/stats")
def get_event_statistics():
    """Get event bus statistics."""
    bus = get_event_bus()
    stats = bus.get_statistics()

    return {
        **stats,
        "event_types": [e.value for e in EventType],
    }


@router.get("/types")
def get_event_types():
    """Get list of available event types."""
    return {
        "event_types": [
            {
                "value": e.value,
                "name": e.name,
            }
            for e in EventType
        ]
    }
