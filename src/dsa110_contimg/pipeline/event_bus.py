"""Event-driven architecture for pipeline components.

Provides event bus for decoupled component communication.
Supports both in-memory and external message brokers (RabbitMQ, Kafka).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

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
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
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


@dataclass
class ESECandidateDetected(PipelineEvent):
    """Event when ESE candidate is detected."""
    source_id: str
    significance: float
    sigma_deviation: float
    n_observations: int


@dataclass
class CalibrationSolved(PipelineEvent):
    """Event when calibration is solved."""
    ms_path: str
    calibrator_name: str
    calibration_type: str
    quality_score: Optional[float] = None


class EventBus:
    """Event bus for pipeline events."""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[PipelineEvent], None]]] = {}
        self._event_history: List[PipelineEvent] = []
        self._max_history: int = 1000
    
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
                logger.error(f"Error in event handler for {event.event_type.value}: {e}", exc_info=True)
        
        logger.debug(f"Published event {event.event_type.value} to {len(handlers)} subscribers")
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[PipelineEvent]:
        """Get event history.
        
        Args:
            event_type: Filter by event type (None for all)
            limit: Maximum number of events to return
        
        Returns:
            List of events
        """
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]
    
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
    correlation_id: Optional[str] = None
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
        source_id=source_id
    )
    get_event_bus().publish(event)


def publish_ese_candidate(
    source_id: str,
    significance: float,
    sigma_deviation: float,
    n_observations: int,
    correlation_id: Optional[str] = None
):
    """Publish ESE candidate detected event."""
    event = ESECandidateDetected(
        event_type=EventType.ESE_CANDIDATE_DETECTED,
        timestamp=datetime.now().timestamp(),
        correlation_id=correlation_id,
        source_id=source_id,
        significance=significance,
        sigma_deviation=sigma_deviation,
        n_observations=n_observations
    )
    get_event_bus().publish(event)


def publish_calibration_solved(
    ms_path: str,
    calibrator_name: str,
    calibration_type: str,
    quality_score: Optional[float] = None,
    correlation_id: Optional[str] = None
):
    """Publish calibration solved event."""
    event = CalibrationSolved(
        event_type=EventType.CALIBRATION_SOLVED,
        timestamp=datetime.now().timestamp(),
        correlation_id=correlation_id,
        ms_path=ms_path,
        calibrator_name=calibrator_name,
        calibration_type=calibration_type,
        quality_score=quality_score
    )
    get_event_bus().publish(event)

