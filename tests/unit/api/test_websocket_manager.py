"""Tests for the WebSocket/SSE manager."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from dsa110_contimg.api.websocket_manager import (ConnectionManager,
                                                  create_status_update,
                                                  event_generator, manager)


class MockWebSocket:
    """Mock WebSocket connection for testing."""

    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def send_text(self, message: str):
        """Mock send_text method."""
        if self.closed:
            raise ConnectionError("Connection closed")
        self.sent_messages.append(message)

    async def send(self, message: str):
        """Mock send method."""
        if self.closed:
            raise ConnectionError("Connection closed")
        self.sent_messages.append(message)

    async def write(self, message: str):
        """Mock write method (for SSE)."""
        if self.closed:
            raise ConnectionError("Connection closed")
        self.sent_messages.append(message)

    def close(self):
        """Close the connection."""
        self.closed = True


class MockSSEConnection:
    """Mock SSE connection for testing."""

    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def write(self, message: str):
        """Mock write method for SSE."""
        if self.closed:
            raise ConnectionError("Connection closed")
        self.sent_messages.append(message)

    def close(self):
        """Close the connection."""
        self.closed = True


@pytest_asyncio.fixture
async def connection_manager():
    """Fixture for ConnectionManager instance."""
    return ConnectionManager()


@pytest.mark.asyncio
class TestConnectionManager:
    """Test ConnectionManager class."""

    async def test_connect(self):
        """Test connecting a new client."""
        cm = ConnectionManager()
        ws = MockWebSocket()

        await cm.connect(ws)
        assert len(cm.active_connections) == 1
        assert ws in cm.active_connections

    async def test_disconnect(self):
        """Test disconnecting a client."""
        cm = ConnectionManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await cm.connect(ws1)
        await cm.connect(ws2)
        assert len(cm.active_connections) == 2

        await cm.disconnect(ws1)
        assert len(cm.active_connections) == 1
        assert ws1 not in cm.active_connections
        assert ws2 in cm.active_connections

    async def test_broadcast_to_websocket(self):
        """Test broadcasting to WebSocket connections."""
        cm = ConnectionManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await cm.connect(ws1)
        await cm.connect(ws2)

        message = {"type": "test", "data": "hello"}
        await cm.broadcast(message)

        # Both connections should receive the message
        assert len(ws1.sent_messages) == 1
        assert len(ws2.sent_messages) == 1

        # Verify message content
        received1 = json.loads(ws1.sent_messages[0])
        received2 = json.loads(ws2.sent_messages[0])
        assert received1 == message
        assert received2 == message

    async def test_broadcast_to_sse(self):
        """Test broadcasting to SSE connections."""
        cm = ConnectionManager()
        sse1 = MockSSEConnection()
        sse2 = MockSSEConnection()

        await cm.connect(sse1)
        await cm.connect(sse2)

        message = {"type": "test", "data": "hello"}
        await cm.broadcast(message)

        # Both connections should receive the message
        assert len(sse1.sent_messages) == 1
        assert len(sse2.sent_messages) == 1

        # Verify SSE format
        assert sse1.sent_messages[0].startswith("data: ")
        assert sse1.sent_messages[0].endswith("\n\n")

    async def test_broadcast_empty_connections(self):
        """Test broadcasting with no connections."""
        cm = ConnectionManager()
        message = {"type": "test", "data": "hello"}

        # Should not raise an error
        await cm.broadcast(message)

    async def test_broadcast_removes_dead_connections(self):
        """Test that dead connections are removed during broadcast."""
        cm = ConnectionManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws2.closed = True  # Mark as closed

        await cm.connect(ws1)
        await cm.connect(ws2)

        message = {"type": "test", "data": "hello"}
        await cm.broadcast(message)

        # Dead connection should be removed
        assert len(cm.active_connections) == 1
        assert ws1 in cm.active_connections
        assert ws2 not in cm.active_connections

    async def test_send_personal_message_websocket(self):
        """Test sending a personal message to a WebSocket."""
        cm = ConnectionManager()
        ws = MockWebSocket()

        message = {"type": "personal", "data": "hello"}
        await cm.send_personal_message(message, ws)

        assert len(ws.sent_messages) == 1
        received = json.loads(ws.sent_messages[0])
        assert received == message

    async def test_send_personal_message_sse(self):
        """Test sending a personal message to an SSE connection."""
        cm = ConnectionManager()
        sse = MockSSEConnection()

        message = {"type": "personal", "data": "hello"}
        await cm.send_personal_message(message, sse)

        assert len(sse.sent_messages) == 1
        assert sse.sent_messages[0].startswith("data: ")

    async def test_send_personal_message_failure(self):
        """Test handling of send failures."""
        cm = ConnectionManager()
        ws = MockWebSocket()
        ws.closed = True

        message = {"type": "personal", "data": "hello"}
        # Should not raise an error, just log a warning
        await cm.send_personal_message(message, ws)

        assert len(ws.sent_messages) == 0

    async def test_concurrent_connections(self):
        """Test concurrent connection handling."""
        cm = ConnectionManager()
        connections = [MockWebSocket() for _ in range(10)]

        # Connect all concurrently
        await asyncio.gather(*[cm.connect(ws) for ws in connections])

        assert len(cm.active_connections) == 10

        # Disconnect all concurrently
        await asyncio.gather(*[cm.disconnect(ws) for ws in connections])

        assert len(cm.active_connections) == 0


@pytest.mark.asyncio
class TestEventGenerator:
    """Test SSE event generator."""

    async def test_event_generator_initial_message(self):
        """Test that event generator sends initial connection message."""
        events = []
        async for event in event_generator():
            events.append(event)
            if len(events) >= 1:
                break  # Stop after first message

        assert len(events) == 1
        assert events[0].startswith("data: ")
        data = json.loads(events[0].replace("data: ", "").strip())
        assert data["type"] == "connected"
        assert "timestamp" in data

    async def test_event_generator_heartbeat(self):
        """Test that event generator sends periodic heartbeats."""
        events = []
        async for event in event_generator():
            events.append(event)
            if len(events) >= 2:
                break  # Stop after second message (first heartbeat)

        assert len(events) >= 2
        # Second message should be a heartbeat
        data = json.loads(events[1].replace("data: ", "").strip())
        assert data["type"] == "heartbeat"


class TestCreateStatusUpdate:
    """Test create_status_update function."""

    def test_create_status_update_minimal(self):
        """Test creating a minimal status update."""
        update = create_status_update()

        assert update["type"] == "status_update"
        assert "timestamp" in update
        assert "data" in update
        assert update["data"]["pipeline_status"] is None
        assert update["data"]["metrics"] is None
        assert update["data"]["ese_candidates"] is None

    def test_create_status_update_with_data(self):
        """Test creating a status update with data."""
        pipeline_status = {"state": "running", "stage": "calibration"}
        metrics = {"throughput": 100.0, "latency": 0.5}
        ese_candidates = {"count": 5}

        update = create_status_update(
            pipeline_status=pipeline_status, metrics=metrics, ese_candidates=ese_candidates
        )

        assert update["type"] == "status_update"
        assert update["data"]["pipeline_status"] == pipeline_status
        assert update["data"]["metrics"] == metrics
        assert update["data"]["ese_candidates"] == ese_candidates


class TestGlobalManager:
    """Test global manager instance."""

    def test_manager_instance(self):
        """Test that global manager exists and is a ConnectionManager."""
        from dsa110_contimg.api.websocket_manager import manager

        assert manager is not None
        assert isinstance(manager, ConnectionManager)
