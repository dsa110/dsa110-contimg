"""
Event system for pipeline orchestration.

This module provides an event-driven architecture for:
1. Decoupling components (ESE detection → mosaic triggering)
2. Enabling reactive pipelines (auto-mosaic on detection)
3. Supporting audit trails and debugging

Classes:
    EventType: Enumeration of supported event types
    Event: Event data container
    EventEmitter: Singleton event bus for publishing/subscribing

Example:
    # Publishing an event
    from dsa110_contimg.pipeline.events import EventEmitter, EventType

    emitter = EventEmitter.get_instance()
    emitter.emit(EventType.ESE_DETECTED, {
        "source_name": "ESE_2024_001",
        "ra": 123.456,
        "dec": 45.678,
        "detection_snr": 15.3,
        "ms_path": "/data/ese_2024_001.ms"
    })

    # Subscribing to events
    def on_ese_detected(event: Event):
        print(f"ESE detected: {event.data['source_name']}")
        # Trigger deep mosaic pipeline...

    emitter.subscribe(EventType.ESE_DETECTED, on_ese_detected)
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Supported event types in the pipeline system."""

    # Detection events
    ESE_DETECTED = "ese_detected"  # Extreme Scattering Event detected
    TRANSIENT_DETECTED = "transient_detected"  # Generic transient detection
    SOURCE_UPDATED = "source_updated"  # Source catalog updated

    # Pipeline events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"

    # Job events
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"

    # Mosaic events
    MOSAIC_CREATED = "mosaic_created"
    MOSAIC_QA_FAILED = "mosaic_qa_failed"
    MOSAIC_QA_PASSED = "mosaic_qa_passed"

    # Calibration events
    CALIBRATION_STARTED = "calibration_started"
    CALIBRATION_COMPLETED = "calibration_completed"
    CALIBRATION_FAILED = "calibration_failed"

    # Data events
    DATA_INGESTED = "data_ingested"  # New MS/UVH5 file ingested
    DATA_ARCHIVED = "data_archived"

    # System events
    SYSTEM_ALERT = "system_alert"
    RESOURCE_WARNING = "resource_warning"


@dataclass
class Event:
    """Event data container.

    Attributes:
        event_type: Type of the event
        data: Event payload (varies by event type)
        event_id: Unique event identifier
        timestamp: Event creation time (Unix timestamp)
        source: Component that emitted the event
        correlation_id: ID for tracking related events
    """

    event_type: EventType
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


# Type for event handlers
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]  # Can be async


class EventEmitter:
    """Singleton event bus for publishing and subscribing to events.

    The EventEmitter provides:
    - Synchronous and asynchronous event handlers
    - Event filtering by type
    - Error isolation (handler errors don't affect other handlers)
    - Event history for debugging

    Thread Safety:
        The emitter is thread-safe for subscription and emission.

    Example:
        emitter = EventEmitter.get_instance()

        # Sync handler
        emitter.subscribe(EventType.ESE_DETECTED, my_handler)

        # Async handler
        emitter.subscribe_async(EventType.MOSAIC_CREATED, my_async_handler)

        # Emit event
        emitter.emit(EventType.ESE_DETECTED, {"source": "ESE001"})
    """

    _instance: EventEmitter | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize the event emitter."""
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._async_handlers: dict[EventType, list[AsyncEventHandler]] = {}
        self._event_history: list[Event] = []
        self._history_limit = 1000
        self._handler_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> EventEmitter:
        """Get the singleton EventEmitter instance.

        Returns:
            The global EventEmitter instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> Callable[[], None]:
        """Subscribe a synchronous handler to an event type.

        Args:
            event_type: Type of event to listen for
            handler: Function to call when event is emitted

        Returns:
            Unsubscribe function - call to remove the handler
        """
        with self._handler_lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

        logger.debug(f"Subscribed handler {handler.__name__} to {event_type.value}")

        def unsubscribe() -> None:
            with self._handler_lock:
                if event_type in self._handlers and handler in self._handlers[event_type]:
                    self._handlers[event_type].remove(handler)
                    logger.debug(
                        f"Unsubscribed handler {handler.__name__} from {event_type.value}"
                    )

        return unsubscribe

    def subscribe_async(
        self,
        event_type: EventType,
        handler: AsyncEventHandler,
    ) -> Callable[[], None]:
        """Subscribe an asynchronous handler to an event type.

        Args:
            event_type: Type of event to listen for
            handler: Async function to call when event is emitted

        Returns:
            Unsubscribe function - call to remove the handler
        """
        with self._handler_lock:
            if event_type not in self._async_handlers:
                self._async_handlers[event_type] = []
            self._async_handlers[event_type].append(handler)

        logger.debug(f"Subscribed async handler {handler.__name__} to {event_type.value}")

        def unsubscribe() -> None:
            with self._handler_lock:
                if (
                    event_type in self._async_handlers
                    and handler in self._async_handlers[event_type]
                ):
                    self._async_handlers[event_type].remove(handler)
                    logger.debug(
                        f"Unsubscribed async handler {handler.__name__} from {event_type.value}"
                    )

        return unsubscribe

    def emit(
        self,
        event_type: EventType,
        data: dict[str, Any],
        source: str = "unknown",
        correlation_id: str | None = None,
    ) -> Event:
        """Emit an event to all subscribed handlers.

        Synchronous handlers are called immediately.
        Asynchronous handlers are scheduled in the event loop.

        Args:
            event_type: Type of event
            data: Event payload
            source: Component emitting the event
            correlation_id: ID for tracking related events

        Returns:
            The emitted Event object
        """
        event = Event(
            event_type=event_type,
            data=data,
            source=source,
            correlation_id=correlation_id,
        )

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._history_limit:
            self._event_history.pop(0)

        logger.info(
            f"Event emitted: {event_type.value} "
            f"(id={event.event_id}, source={source})"
        )

        # Call synchronous handlers
        with self._handler_lock:
            handlers = self._handlers.get(event_type, []).copy()

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    f"Error in event handler {handler.__name__} "
                    f"for {event_type.value}"
                )

        # Schedule asynchronous handlers
        with self._handler_lock:
            async_handlers = self._async_handlers.get(event_type, []).copy()

        if async_handlers:
            self._schedule_async_handlers(event, async_handlers)

        return event

    def _schedule_async_handlers(
        self,
        event: Event,
        handlers: list[AsyncEventHandler],
    ) -> None:
        """Schedule async handlers in the event loop.

        Args:
            event: Event to pass to handlers
            handlers: List of async handlers to call
        """
        try:
            loop = asyncio.get_running_loop()
            for handler in handlers:
                loop.create_task(self._call_async_handler(handler, event))
        except RuntimeError:
            # No running loop - run in new loop
            asyncio.run(self._call_all_async_handlers(handlers, event))

    async def _call_async_handler(
        self,
        handler: AsyncEventHandler,
        event: Event,
    ) -> None:
        """Call a single async handler with error handling."""
        try:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            logger.exception(
                f"Error in async event handler {handler.__name__} "
                f"for {event.event_type.value}"
            )

    async def _call_all_async_handlers(
        self,
        handlers: list[AsyncEventHandler],
        event: Event,
    ) -> None:
        """Call all async handlers concurrently."""
        tasks = [self._call_async_handler(h, event) for h in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_history(
        self,
        event_type: EventType | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get recent event history.

        Args:
            event_type: Filter by event type (None = all)
            limit: Maximum events to return

        Returns:
            List of recent events (newest first)
        """
        events = self._event_history.copy()

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:][::-1]

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()

    def get_handler_count(self, event_type: EventType) -> int:
        """Get number of handlers for an event type.

        Args:
            event_type: Event type to check

        Returns:
            Total count of sync + async handlers
        """
        with self._handler_lock:
            sync_count = len(self._handlers.get(event_type, []))
            async_count = len(self._async_handlers.get(event_type, []))
            return sync_count + async_count


# Convenience functions for common patterns
def emit_ese_detection(
    source_name: str,
    ra: float,
    dec: float,
    detection_snr: float,
    ms_path: str,
    **extra_data: Any,
) -> Event:
    """Emit an ESE detection event.

    Args:
        source_name: Name of the detected ESE source
        ra: Right ascension (degrees)
        dec: Declination (degrees)
        detection_snr: Detection SNR
        ms_path: Path to the measurement set
        **extra_data: Additional event data

    Returns:
        The emitted Event
    """
    emitter = EventEmitter.get_instance()
    return emitter.emit(
        EventType.ESE_DETECTED,
        {
            "source_name": source_name,
            "ra": ra,
            "dec": dec,
            "detection_snr": detection_snr,
            "ms_path": ms_path,
            **extra_data,
        },
        source="ese_detection",
    )


def emit_job_event(
    event_type: EventType,
    job_id: str,
    pipeline_name: str,
    execution_id: str,
    message: str | None = None,
    error: str | None = None,
    **extra_data: Any,
) -> Event:
    """Emit a job lifecycle event.

    Args:
        event_type: One of JOB_STARTED, JOB_COMPLETED, JOB_FAILED
        job_id: ID of the job
        pipeline_name: Name of the containing pipeline
        execution_id: Pipeline execution ID
        message: Success message (for completed)
        error: Error message (for failed)
        **extra_data: Additional event data

    Returns:
        The emitted Event
    """
    emitter = EventEmitter.get_instance()
    data = {
        "job_id": job_id,
        "pipeline_name": pipeline_name,
        "execution_id": execution_id,
        **extra_data,
    }
    if message:
        data["message"] = message
    if error:
        data["error"] = error

    return emitter.emit(
        event_type,
        data,
        source=f"pipeline:{pipeline_name}",
        correlation_id=execution_id,
    )


def emit_pipeline_event(
    event_type: EventType,
    pipeline_name: str,
    execution_id: str,
    message: str | None = None,
    error: str | None = None,
    **extra_data: Any,
) -> Event:
    """Emit a pipeline lifecycle event.

    Args:
        event_type: One of PIPELINE_STARTED, PIPELINE_COMPLETED, PIPELINE_FAILED
        pipeline_name: Name of the pipeline
        execution_id: Pipeline execution ID
        message: Success message (for completed)
        error: Error message (for failed)
        **extra_data: Additional event data

    Returns:
        The emitted Event
    """
    emitter = EventEmitter.get_instance()
    data = {
        "pipeline_name": pipeline_name,
        "execution_id": execution_id,
        **extra_data,
    }
    if message:
        data["message"] = message
    if error:
        data["error"] = error

    return emitter.emit(
        event_type,
        data,
        source=f"pipeline:{pipeline_name}",
        correlation_id=execution_id,
    )
