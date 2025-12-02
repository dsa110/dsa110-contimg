"""
Unit tests for the pipeline event system.

Tests event emission, subscription, and handler execution.
"""

from __future__ import annotations

import pytest

from dsa110_contimg.pipeline.events import (
    Event,
    EventEmitter,
    EventType,
    emit_ese_detection,
    emit_job_event,
    emit_pipeline_event,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_event_types_are_strings(self):
        """Verify EventType values are strings."""
        assert EventType.ESE_DETECTED.value == "ese_detected"
        assert EventType.JOB_STARTED.value == "job_started"
        assert EventType.PIPELINE_COMPLETED.value == "pipeline_completed"

    def test_all_expected_types_exist(self):
        """Verify all expected event types are defined."""
        expected_types = [
            "ESE_DETECTED",
            "TRANSIENT_DETECTED",
            "PIPELINE_STARTED",
            "PIPELINE_COMPLETED",
            "PIPELINE_FAILED",
            "JOB_STARTED",
            "JOB_COMPLETED",
            "JOB_FAILED",
            "MOSAIC_CREATED",
            "CALIBRATION_STARTED",
            "CALIBRATION_COMPLETED",
            "DATA_INGESTED",
        ]
        for type_name in expected_types:
            assert hasattr(EventType, type_name)


class TestEvent:
    """Tests for Event dataclass."""

    def test_event_creation(self):
        """Test creating an event with required fields."""
        event = Event(
            event_type=EventType.ESE_DETECTED,
            data={"source_name": "ESE001", "ra": 123.45, "dec": 45.67},
        )

        assert event.event_type == EventType.ESE_DETECTED
        assert event.data["source_name"] == "ESE001"
        assert len(event.event_id) == 16  # UUID hex prefix
        assert event.timestamp > 0
        assert event.source == "unknown"
        assert event.correlation_id is None

    def test_event_with_all_fields(self):
        """Test creating an event with all fields."""
        event = Event(
            event_type=EventType.JOB_COMPLETED,
            data={"job_id": "job123", "result": "success"},
            event_id="custom_id_12345",
            timestamp=1234567890.0,
            source="test_runner",
            correlation_id="corr_abc",
        )

        assert event.event_id == "custom_id_12345"
        assert event.timestamp == 1234567890.0
        assert event.source == "test_runner"
        assert event.correlation_id == "corr_abc"

    def test_event_to_dict(self):
        """Test event serialization."""
        event = Event(
            event_type=EventType.MOSAIC_CREATED,
            data={"mosaic_path": "/data/mosaic.fits"},
            source="mosaic_pipeline",
        )

        d = event.to_dict()

        assert d["event_type"] == "mosaic_created"
        assert d["data"]["mosaic_path"] == "/data/mosaic.fits"
        assert d["source"] == "mosaic_pipeline"
        assert "event_id" in d
        assert "timestamp" in d


class TestEventEmitter:
    """Tests for EventEmitter singleton."""

    @pytest.fixture(autouse=True)
    def reset_emitter(self):
        """Reset the singleton before each test."""
        EventEmitter.reset_instance()
        yield
        EventEmitter.reset_instance()

    def test_singleton_instance(self):
        """Test EventEmitter is a singleton."""
        emitter1 = EventEmitter.get_instance()
        emitter2 = EventEmitter.get_instance()

        assert emitter1 is emitter2

    def test_reset_instance(self):
        """Test singleton can be reset."""
        emitter1 = EventEmitter.get_instance()
        EventEmitter.reset_instance()
        emitter2 = EventEmitter.get_instance()

        assert emitter1 is not emitter2

    def test_subscribe_sync_handler(self):
        """Test subscribing a synchronous handler."""
        emitter = EventEmitter.get_instance()

        def handler(event: Event):
            pass

        unsub = emitter.subscribe(EventType.ESE_DETECTED, handler)

        assert callable(unsub)
        assert handler in emitter._handlers.get(EventType.ESE_DETECTED, [])

    def test_unsubscribe_handler(self):
        """Test unsubscribing a handler."""
        emitter = EventEmitter.get_instance()

        def handler(event: Event):
            pass

        unsub = emitter.subscribe(EventType.ESE_DETECTED, handler)
        unsub()

        assert handler not in emitter._handlers.get(EventType.ESE_DETECTED, [])

    def test_emit_calls_handler(self):
        """Test that emit() calls subscribed handlers."""
        emitter = EventEmitter.get_instance()
        received_events = []

        def handler(event: Event):
            received_events.append(event)

        emitter.subscribe(EventType.JOB_STARTED, handler)
        emitter.emit(
            EventType.JOB_STARTED,
            data={"job_id": "test_job"},
            source="test",
        )

        assert len(received_events) == 1
        assert isinstance(received_events[0], Event)
        assert received_events[0].event_type == EventType.JOB_STARTED
        assert received_events[0].data["job_id"] == "test_job"

    def test_emit_returns_event(self):
        """Test that emit() returns the created Event."""
        emitter = EventEmitter.get_instance()

        event = emitter.emit(
            EventType.PIPELINE_STARTED,
            data={"pipeline": "test"},
            source="test_source",
            correlation_id="corr123",
        )

        assert isinstance(event, Event)
        assert event.event_type == EventType.PIPELINE_STARTED
        assert event.source == "test_source"
        assert event.correlation_id == "corr123"

    def test_multiple_handlers(self):
        """Test multiple handlers for same event type."""
        emitter = EventEmitter.get_instance()
        call_count = [0, 0]

        def handler1(event: Event):
            call_count[0] += 1

        def handler2(event: Event):
            call_count[1] += 1

        emitter.subscribe(EventType.MOSAIC_CREATED, handler1)
        emitter.subscribe(EventType.MOSAIC_CREATED, handler2)
        emitter.emit(EventType.MOSAIC_CREATED, data={})

        assert call_count[0] == 1
        assert call_count[1] == 1

    def test_handler_isolation(self):
        """Test that handler errors don't affect other handlers."""
        emitter = EventEmitter.get_instance()
        success_called = [False]

        def failing_handler(event: Event):
            raise ValueError("test error")

        def success_handler(event: Event):
            success_called[0] = True

        emitter.subscribe(EventType.JOB_FAILED, failing_handler)
        emitter.subscribe(EventType.JOB_FAILED, success_handler)

        # Should not raise, and second handler should still be called
        emitter.emit(EventType.JOB_FAILED, data={"error": "test"})

        assert success_called[0]

    def test_event_history(self):
        """Test that events are stored in history."""
        emitter = EventEmitter.get_instance()

        emitter.emit(EventType.DATA_INGESTED, data={"ms": "test1.ms"})
        emitter.emit(EventType.DATA_INGESTED, data={"ms": "test2.ms"})

        assert len(emitter._event_history) == 2
        assert emitter._event_history[0].data["ms"] == "test1.ms"
        assert emitter._event_history[1].data["ms"] == "test2.ms"

    def test_history_limit(self):
        """Test that event history is limited."""
        emitter = EventEmitter.get_instance()
        emitter._history_limit = 5

        for i in range(10):
            emitter.emit(EventType.JOB_COMPLETED, data={"i": i})

        assert len(emitter._event_history) == 5
        # Should have the last 5 events
        assert emitter._event_history[0].data["i"] == 5

    def test_subscribe_async_handler(self):
        """Test subscribing an async handler."""
        emitter = EventEmitter.get_instance()

        async def async_handler(event: Event):
            pass

        unsub = emitter.subscribe_async(EventType.CALIBRATION_COMPLETED, async_handler)

        assert callable(unsub)
        assert async_handler in emitter._async_handlers.get(
            EventType.CALIBRATION_COMPLETED, []
        )

    def test_different_event_types_isolated(self):
        """Test that handlers only receive their event type."""
        emitter = EventEmitter.get_instance()
        job_called = [False]
        pipeline_called = [False]

        def job_handler(event: Event):
            job_called[0] = True

        def pipeline_handler(event: Event):
            pipeline_called[0] = True

        emitter.subscribe(EventType.JOB_COMPLETED, job_handler)
        emitter.subscribe(EventType.PIPELINE_COMPLETED, pipeline_handler)

        emitter.emit(EventType.JOB_COMPLETED, data={})

        assert job_called[0]
        assert not pipeline_called[0]


class TestEmitHelpers:
    """Tests for emit helper functions."""

    @pytest.fixture(autouse=True)
    def reset_emitter(self):
        """Reset the singleton before each test."""
        EventEmitter.reset_instance()
        yield
        EventEmitter.reset_instance()

    def test_emit_ese_detection(self):
        """Test ESE detection helper."""
        emitter = EventEmitter.get_instance()
        received = []

        def handler(event: Event):
            received.append(event)

        emitter.subscribe(EventType.ESE_DETECTED, handler)

        event = emit_ese_detection(
            source_name="ESE_2024_001",
            ra=123.456,
            dec=45.678,
            detection_snr=15.3,
            ms_path="/data/test.ms",
        )

        assert event.event_type == EventType.ESE_DETECTED
        assert event.data["source_name"] == "ESE_2024_001"
        assert event.data["ra"] == 123.456
        assert event.data["dec"] == 45.678
        assert len(received) == 1

    def test_emit_job_event(self):
        """Test job event helper."""
        emitter = EventEmitter.get_instance()
        received = []

        def handler(event: Event):
            received.append(event)

        emitter.subscribe(EventType.JOB_COMPLETED, handler)

        event = emit_job_event(
            event_type=EventType.JOB_COMPLETED,
            job_id="job123",
            pipeline_name="test_pipeline",
            execution_id="exec123",
        )

        assert event.event_type == EventType.JOB_COMPLETED
        assert event.data["job_id"] == "job123"
        assert event.data["pipeline_name"] == "test_pipeline"
        assert len(received) == 1

    def test_emit_pipeline_event(self):
        """Test pipeline event helper."""
        emitter = EventEmitter.get_instance()
        received = []

        def handler(event: Event):
            received.append(event)

        emitter.subscribe(EventType.PIPELINE_COMPLETED, handler)

        event = emit_pipeline_event(
            event_type=EventType.PIPELINE_COMPLETED,
            pipeline_name="calibration",
            execution_id="exec_abc",
        )

        assert event.event_type == EventType.PIPELINE_COMPLETED
        assert event.data["pipeline_name"] == "calibration"
        assert event.data["execution_id"] == "exec_abc"
        assert len(received) == 1
