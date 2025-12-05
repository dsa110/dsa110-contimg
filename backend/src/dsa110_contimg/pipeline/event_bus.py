"""Event-driven architecture for pipeline components.

Provides event bus for decoupled component communication.
Supports both in-memory and external message brokers (RabbitMQ, Kafka).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types in the pipeline."""

    # Photometry events
    PHOTOMETRY_MEASUREMENT_COMPLETED = "photometry_measurement_completed"
    PHOTOMETRY_NORMALIZATION_COMPLETED = "photometry_normalization_completed"

    # ESE detection events
    ESE_CANDIDATE_DETECTED = "ese_candidate_detected"
    VARIABILITY_STATS_UPDATED = "variability_stats_updated"

    # Calibration events
    CALIBRATION_SOLVED = "calibration_solved"
    CALIBRATION_APPLIED = "calibration_applied"

    # Pipeline events
    PIPELINE_STAGE_STARTED = "pipeline_stage_started"
    PIPELINE_STAGE_COMPLETED = "pipeline_stage_completed"
    PIPELINE_STAGE_FAILED = "pipeline_stage_failed"

    # Error events
    ERROR_OCCURRED = "error_occurred"


@dataclass
class PipelineEvent:
    """Base event class."""

    event_type: EventType
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class PhotometryMeasurementCompleted(PipelineEvent):
    """Event when photometry measurement completes."""

    fits_path: str
    ra_deg: float
    dec_deg: float
    flux_jy: float
    method: str
    source_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ESECandidateDetected(PipelineEvent):
    """Event when ESE candidate is detected."""

    source_id: str
    significance: float
    sigma_deviation: float
    n_observations: int
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CalibrationSolved(PipelineEvent):
    """Event when calibration is solved."""

    ms_path: str
    calibrator_name: str
    calibration_type: str
    quality_score: Optional[float] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EventBus:
    """Event bus for pipeline events."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[PipelineEvent], None]]] = {}
        self._event_history: List[PipelineEvent] = []
        self._max_history: int = 1000
        self._event_counts: Dict[EventType, int] = {}
        self._total_events: int = 0

    def subscribe(self, event_type: EventType, handler: Callable[[PipelineEvent], None]):
        """Subscribe to event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event occurs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: Callable[[PipelineEvent], None]):
        """Unsubscribe from event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                pass

    def publish(self, event: PipelineEvent):
        """Publish event to all subscribers.

        Args:
            event: Event to publish
        """
        # Set timestamp if not set
        if event.timestamp == 0:
            event.timestamp = datetime.now().timestamp()

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Notify subscribers
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"Error in event handler for {event.event_type.value}: {e}",
                    exc_info=True,
                )

        logger.debug(f"Published event {event.event_type.value} to {len(handlers)} subscribers")

        # Update statistics
        self._total_events += 1
        self._event_counts[event.event_type] = self._event_counts.get(event.event_type, 0) + 1

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
        since: Optional[float] = None,
    ) -> List[PipelineEvent]:
        """Get event history with optional filtering.

        Args:
            event_type: Filter by event type
            limit: Maximum number of events to return
            since: Only return events after this timestamp

        Returns:
            List of events, most recent first
        """
        events = self._event_history

        # Filter by type
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # Filter by timestamp
        if since:
            events = [e for e in events if e.timestamp >= since]

        # Return most recent first, limited
        return list(reversed(events[-limit:]))

    def get_statistics(self) -> Dict[str, Any]:
        """Get event statistics.

        Returns:
            Dictionary with event counts and rates
        """
        now = datetime.now().timestamp()
        last_minute = now - 60
        last_hour = now - 3600

        recent_events = [e for e in self._event_history if e.timestamp >= last_minute]
        hourly_events = [e for e in self._event_history if e.timestamp >= last_hour]

        return {
            "total_events": self._total_events,
            "events_in_history": len(self._event_history),
            "events_per_type": {
                event_type.value: count for event_type, count in self._event_counts.items()
            },
            "events_last_minute": len(recent_events),
            "events_last_hour": len(hourly_events),
            "subscribers": {
                event_type.value: len(handlers)
                for event_type, handlers in self._subscribers.items()
            },
        }

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# Convenience functions for common events


def publish_photometry_measurement(
    fits_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    method: str,
    source_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
):
    """Publish photometry measurement completed event."""
    event = PhotometryMeasurementCompleted(
        event_type=EventType.PHOTOMETRY_MEASUREMENT_COMPLETED,
        timestamp=datetime.now().timestamp(),
        correlation_id=correlation_id,
        fits_path=fits_path,
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        flux_jy=flux_jy,
        method=method,
        source_id=source_id,
    )
    get_event_bus().publish(event)


def publish_ese_candidate(
    source_id: str,
    significance: float,
    sigma_deviation: float,
    n_observations: int,
    correlation_id: Optional[str] = None,
):
    """Publish ESE candidate detected event."""
    event = ESECandidateDetected(
        event_type=EventType.ESE_CANDIDATE_DETECTED,
        timestamp=datetime.now().timestamp(),
        correlation_id=correlation_id,
        source_id=source_id,
        significance=significance,
        sigma_deviation=sigma_deviation,
        n_observations=n_observations,
    )
    get_event_bus().publish(event)


def publish_calibration_solved(
    ms_path: str,
    calibrator_name: str,
    calibration_type: str,
    quality_score: Optional[float] = None,
    correlation_id: Optional[str] = None,
):
    """Publish calibration solved event."""
    event = CalibrationSolved(
        event_type=EventType.CALIBRATION_SOLVED,
        timestamp=datetime.now().timestamp(),
        correlation_id=correlation_id,
        ms_path=ms_path,
        calibrator_name=calibrator_name,
        calibration_type=calibration_type,
        quality_score=quality_score,
    )
    get_event_bus().publish(event)
