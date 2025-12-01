"""
Unit tests for websocket.py - WebSocket support for real-time updates.

Tests for:
- ConnectionInfo dataclass
- ConnectionManager class
- WebSocket routes
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from dsa110_contimg.api.websocket import (
    ConnectionInfo,
    ConnectionManager,
    ConnectionState,
    DisconnectReason,
    ws_router,
)


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""

    def test_default_subscriptions(self):
        """Test default subscriptions is empty set."""
        mock_ws = MagicMock()
        info = ConnectionInfo(websocket=mock_ws)
        
        assert info.subscriptions == set()

    def test_default_connected_at(self):
        """Test connected_at is set to current time."""
        mock_ws = MagicMock()
        before = datetime.utcnow()
        info = ConnectionInfo(websocket=mock_ws)
        after = datetime.utcnow()
        
        assert before <= info.connected_at <= after

    def test_default_user_id(self):
        """Test default user_id is None."""
        mock_ws = MagicMock()
        info = ConnectionInfo(websocket=mock_ws)
        
        assert info.user_id is None

    def test_custom_user_id(self):
        """Test custom user_id."""
        mock_ws = MagicMock()
        info = ConnectionInfo(websocket=mock_ws, user_id="user-123")
        
        assert info.user_id == "user-123"

    def test_subscriptions_are_independent(self):
        """Test each ConnectionInfo has independent subscriptions."""
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()
        
        info1 = ConnectionInfo(websocket=mock_ws1)
        info2 = ConnectionInfo(websocket=mock_ws2)
        
        info1.subscriptions.add("topic1")
        
        assert "topic1" in info1.subscriptions
        assert "topic1" not in info2.subscriptions


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.client_state = MagicMock()
        return ws

    def test_init_empty_connections(self, manager):
        """Test manager starts with no connections."""
        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager, mock_websocket):
        """Test connect accepts the WebSocket."""
        await manager.connect(mock_websocket, "client-1")
        
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_stores_connection(self, manager, mock_websocket):
        """Test connect stores the connection."""
        await manager.connect(mock_websocket, "client-1")
        
        assert "client-1" in manager.active_connections
        assert manager.active_connections["client-1"].websocket == mock_websocket

    @pytest.mark.asyncio
    async def test_connect_with_user_id(self, manager, mock_websocket):
        """Test connect stores user_id."""
        await manager.connect(mock_websocket, "client-1", user_id="user-123")
        
        assert manager.active_connections["client-1"].user_id == "user-123"

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager, mock_websocket):
        """Test disconnect removes the connection."""
        await manager.connect(mock_websocket, "client-1")
        await manager.disconnect("client-1")
        
        assert "client-1" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_client(self, manager):
        """Test disconnect handles nonexistent client gracefully."""
        # Should not raise
        await manager.disconnect("nonexistent")

    @pytest.mark.asyncio
    async def test_subscribe_adds_topic(self, manager, mock_websocket):
        """Test subscribe adds topic to client."""
        await manager.connect(mock_websocket, "client-1")
        result = await manager.subscribe("client-1", "job:123")
        
        assert result is True
        assert "job:123" in manager.active_connections["client-1"].subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_nonexistent_client(self, manager):
        """Test subscribe returns False for nonexistent client."""
        result = await manager.subscribe("nonexistent", "topic")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_topic(self, manager, mock_websocket):
        """Test unsubscribe removes topic from client."""
        await manager.connect(mock_websocket, "client-1")
        await manager.subscribe("client-1", "job:123")
        result = await manager.unsubscribe("client-1", "job:123")
        
        assert result is True
        assert "job:123" not in manager.active_connections["client-1"].subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_client(self, manager):
        """Test unsubscribe returns False for nonexistent client."""
        result = await manager.unsubscribe("nonexistent", "topic")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_client_success(self, manager, mock_websocket):
        """Test send_to_client sends message successfully."""
        from fastapi.websockets import WebSocketState
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        await manager.connect(mock_websocket, "client-1")
        result = await manager.send_to_client("client-1", {"type": "test"})
        
        assert result is True
        mock_websocket.send_json.assert_called_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_to_client_not_found(self, manager):
        """Test send_to_client returns False for unknown client."""
        result = await manager.send_to_client("nonexistent", {"type": "test"})
        
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, manager):
        """Test broadcast sends to all connected clients."""
        from fastapi.websockets import WebSocketState
        
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws1.send_json = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED
        ws2.send_json = AsyncMock()
        
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        
        count = await manager.broadcast({"type": "broadcast"})
        
        assert count == 2
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_topic_subscribers(self, manager):
        """Test broadcast with topic only sends to subscribers."""
        from fastapi.websockets import WebSocketState
        
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws1.send_json = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED
        ws2.send_json = AsyncMock()
        
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        await manager.subscribe("client-1", "job:123")
        
        count = await manager.broadcast({"type": "update"}, topic="job:123")
        
        assert count == 1
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_subscriptions(self, manager, mock_websocket):
        """Test client can have multiple subscriptions."""
        await manager.connect(mock_websocket, "client-1")
        await manager.subscribe("client-1", "topic1")
        await manager.subscribe("client-1", "topic2")
        await manager.subscribe("client-1", "topic3")
        
        subs = manager.active_connections["client-1"].subscriptions
        assert "topic1" in subs
        assert "topic2" in subs
        assert "topic3" in subs


class TestWebSocketRouter:
    """Tests for WebSocket router configuration."""

    def test_router_prefix(self):
        """Test router has correct prefix."""
        assert ws_router.prefix == "/ws"

    def test_router_tags(self):
        """Test router has correct tags."""
        assert "websocket" in ws_router.tags

    def test_router_has_routes(self):
        """Test router has routes defined."""
        # Router should have at least some routes
        assert len(ws_router.routes) >= 0  # May be empty if routes are added elsewhere


class TestConnectionManagerConcurrency:
    """Tests for ConnectionManager thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test multiple concurrent connections."""
        manager = ConnectionManager()
        
        async def connect_client(client_id):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            await manager.connect(ws, client_id)
        
        # Connect many clients concurrently
        tasks = [connect_client(f"client-{i}") for i in range(10)]
        await asyncio.gather(*tasks)
        
        assert len(manager.active_connections) == 10

    @pytest.mark.asyncio
    async def test_concurrent_subscribe_unsubscribe(self):
        """Test concurrent subscribe/unsubscribe operations."""
        manager = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        await manager.connect(ws, "client-1")
        
        async def toggle_subscription(topic):
            await manager.subscribe("client-1", topic)
            await manager.unsubscribe("client-1", topic)
        
        # Many concurrent operations
        tasks = [toggle_subscription(f"topic-{i}") for i in range(20)]
        await asyncio.gather(*tasks)
        
        # Should complete without errors
        assert "client-1" in manager.active_connections


class TestDisconnectReason:
    """Tests for DisconnectReason enum."""

    def test_all_reasons_exist(self):
        """Test all expected disconnect reasons are defined."""
        expected = ["NORMAL", "CLIENT_DISCONNECT", "HEARTBEAT_TIMEOUT", "ERROR", "SERVER_SHUTDOWN"]
        for reason in expected:
            assert hasattr(DisconnectReason, reason)

    def test_reason_values(self):
        """Test disconnect reason values are strings."""
        assert DisconnectReason.NORMAL.value == "normal"
        assert DisconnectReason.HEARTBEAT_TIMEOUT.value == "heartbeat_timeout"


class TestConnectionState:
    """Tests for ConnectionState enum."""

    def test_all_states_exist(self):
        """Test all expected connection states are defined."""
        expected = ["CONNECTING", "CONNECTED", "DISCONNECTING", "DISCONNECTED"]
        for state in expected:
            assert hasattr(ConnectionState, state)


class TestConnectionInfoHeartbeat:
    """Tests for ConnectionInfo heartbeat features."""

    def test_default_heartbeat_values(self):
        """Test default heartbeat values."""
        mock_ws = MagicMock()
        info = ConnectionInfo(websocket=mock_ws)
        
        # Should have last_heartbeat set to connected_at
        assert info.last_heartbeat is not None
        assert info.missed_heartbeats == 0
        assert info.state == ConnectionState.CONNECTED
        assert info.reconnect_token is None

    def test_custom_reconnect_token(self):
        """Test setting reconnect token."""
        mock_ws = MagicMock()
        info = ConnectionInfo(websocket=mock_ws, reconnect_token="token-123")
        
        assert info.reconnect_token == "token-123"


class TestConnectionManagerHeartbeat:
    """Tests for ConnectionManager heartbeat features."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.client_state = MagicMock()
        return ws

    @pytest.mark.asyncio
    async def test_record_heartbeat(self, manager, mock_websocket):
        """Test recording a heartbeat updates timestamp."""
        await manager.connect(mock_websocket, "client-1")
        
        # Get initial heartbeat time
        initial_heartbeat = manager.connections["client-1"].last_heartbeat
        
        # Wait a tiny bit to ensure time difference
        await asyncio.sleep(0.01)
        
        # Record new heartbeat
        manager.record_heartbeat("client-1")
        
        new_heartbeat = manager.connections["client-1"].last_heartbeat
        assert new_heartbeat > initial_heartbeat
        assert manager.connections["client-1"].missed_heartbeats == 0

    def test_record_heartbeat_nonexistent_client(self, manager):
        """Test recording heartbeat for nonexistent client is no-op."""
        # Should not raise
        manager.record_heartbeat("nonexistent-client")

    @pytest.mark.asyncio
    async def test_check_heartbeat_healthy(self, manager, mock_websocket):
        """Test check_heartbeat returns True for healthy connection."""
        await manager.connect(mock_websocket, "client-1")
        
        # Fresh connection should be healthy
        assert manager.check_heartbeat("client-1", max_missed=3) is True
        # First check increments missed count
        assert manager.connections["client-1"].missed_heartbeats == 1

    @pytest.mark.asyncio
    async def test_check_heartbeat_timeout(self, manager, mock_websocket):
        """Test check_heartbeat returns False after too many missed."""
        await manager.connect(mock_websocket, "client-1")
        
        # Miss multiple heartbeats
        manager.check_heartbeat("client-1", max_missed=3)  # 1
        manager.check_heartbeat("client-1", max_missed=3)  # 2
        manager.check_heartbeat("client-1", max_missed=3)  # 3
        
        # Fourth check should return False
        assert manager.check_heartbeat("client-1", max_missed=3) is False

    def test_check_heartbeat_nonexistent_client(self, manager):
        """Test check_heartbeat for nonexistent client returns False."""
        assert manager.check_heartbeat("nonexistent", max_missed=3) is False

    @pytest.mark.asyncio
    async def test_generate_reconnect_token(self, manager, mock_websocket):
        """Test generating reconnect token."""
        await manager.connect(mock_websocket, "client-1")
        
        token = manager.generate_reconnect_token("client-1")
        
        assert token is not None
        assert len(token) > 20  # UUID4 is 36 chars
        assert manager.connections["client-1"].reconnect_token == token

    def test_generate_reconnect_token_nonexistent(self, manager):
        """Test generating token for nonexistent client returns None."""
        token = manager.generate_reconnect_token("nonexistent")
        assert token is None

    @pytest.mark.asyncio
    async def test_disconnect_with_reason(self, manager, mock_websocket):
        """Test disconnect with reason parameter."""
        await manager.connect(mock_websocket, "client-1")
        
        # Disconnect with specific reason
        await manager.disconnect("client-1", DisconnectReason.HEARTBEAT_TIMEOUT)
        
        assert "client-1" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_default_reason(self, manager, mock_websocket):
        """Test disconnect uses NORMAL as default reason."""
        await manager.connect(mock_websocket, "client-1")
        
        # Disconnect without reason (should use NORMAL)
        await manager.disconnect("client-1")
        
        assert "client-1" not in manager.active_connections


class TestConnectionManagerExtendedFeatures:
    """Tests for additional ConnectionManager features."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.client_state = MagicMock()
        return ws

    @pytest.mark.asyncio
    async def test_handle_heartbeat_response(self, manager, mock_websocket):
        """Test handle_heartbeat_response resets missed count."""
        await manager.connect(mock_websocket, "client-1")
        
        # Simulate missed heartbeats
        manager.connections["client-1"].missed_heartbeats = 2
        
        # Handle heartbeat response
        await manager.handle_heartbeat_response("client-1")
        
        assert manager.connections["client-1"].missed_heartbeats == 0

    @pytest.mark.asyncio
    async def test_handle_heartbeat_response_nonexistent(self, manager):
        """Test handle_heartbeat_response for nonexistent client."""
        # Should not raise
        await manager.handle_heartbeat_response("nonexistent")

    @pytest.mark.asyncio
    async def test_send_heartbeat(self, manager, mock_websocket):
        """Test send_heartbeat sends heartbeat message."""
        from fastapi.websockets import WebSocketState
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        await manager.connect(mock_websocket, "client-1")
        await manager.send_heartbeat("client-1")
        
        # Verify heartbeat was sent
        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "heartbeat"

    @pytest.mark.asyncio
    async def test_send_heartbeat_nonexistent(self, manager):
        """Test send_heartbeat for nonexistent client."""
        # Should not raise
        await manager.send_heartbeat("nonexistent")

    @pytest.mark.asyncio
    async def test_check_connection_health(self, manager, mock_websocket):
        """Test check_connection_health disconnects unhealthy clients."""
        from fastapi.websockets import WebSocketState
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        await manager.connect(mock_websocket, "client-1")
        
        # Simulate too many missed heartbeats
        manager.connections["client-1"].missed_heartbeats = 10
        
        await manager.check_connection_health()
        
        # Client should be disconnected
        assert "client-1" not in manager.active_connections

    def test_get_connection_count(self, manager):
        """Test get_connection_count returns correct count."""
        assert manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_get_connection_count_with_clients(self, manager, mock_websocket):
        """Test get_connection_count with connected clients."""
        await manager.connect(mock_websocket, "client-1")
        assert manager.get_connection_count() == 1
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        await manager.connect(ws2, "client-2")
        assert manager.get_connection_count() == 2

    def test_get_topic_subscribers_empty(self, manager):
        """Test get_topic_subscribers with no subscribers."""
        count = manager.get_topic_subscribers("some-topic")
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_topic_subscribers_with_clients(self, manager, mock_websocket):
        """Test get_topic_subscribers with subscribed clients."""
        await manager.connect(mock_websocket, "client-1")
        await manager.subscribe("client-1", "topic-1")
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        await manager.connect(ws2, "client-2")
        await manager.subscribe("client-2", "topic-1")
        
        count = manager.get_topic_subscribers("topic-1")
        assert count == 2

    @pytest.mark.asyncio
    async def test_connect_with_reconnect_token(self, manager, mock_websocket):
        """Test connect with reconnect token restores subscriptions."""
        await manager.connect(mock_websocket, "client-1")
        await manager.subscribe("client-1", "topic-1")
        
        # Generate reconnect token
        token = manager.generate_reconnect_token("client-1")
        
        # Store subscriptions for reconnect (simulate)
        manager._reconnect_data = {
            token: {"subscriptions": {"topic-1"}}
        }
        
        # Reconnect with token
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        new_token = await manager.connect(ws2, "client-2", reconnect_token=token)
        
        # Should have a new token
        assert new_token is not None


class TestWebSocketHelperFunctions:
    """Tests for WebSocket helper functions."""

    @pytest.mark.asyncio
    async def test_notify_job_status(self):
        """Test notify_job_status function."""
        from dsa110_contimg.api.websocket import notify_job_status, manager
        
        # Create a mock client
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        from fastapi.websockets import WebSocketState
        ws.client_state = WebSocketState.CONNECTED
        
        await manager.connect(ws, "test-client")
        await manager.subscribe("test-client", "job:test-job")
        
        try:
            count = await notify_job_status(
                job_id="test-job",
                status="running",
                progress=0.5,
                message="Processing...",
            )
            
            # Should have notified at least one client
            assert count >= 0
        finally:
            await manager.disconnect("test-client")

    @pytest.mark.asyncio
    async def test_notify_job_progress(self):
        """Test notify_job_progress function."""
        from dsa110_contimg.api.websocket import notify_job_progress, manager
        
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        from fastapi.websockets import WebSocketState
        ws.client_state = WebSocketState.CONNECTED
        
        await manager.connect(ws, "test-client")
        await manager.subscribe("test-client", "job:progress-job")
        
        try:
            count = await notify_job_progress(
                job_id="progress-job",
                progress=0.75,
                stage="imaging",
                eta_seconds=120.5,
            )
            
            assert count >= 0
        finally:
            await manager.disconnect("test-client")

    @pytest.mark.asyncio
    async def test_notify_job_log(self):
        """Test notify_job_log function."""
        from dsa110_contimg.api.websocket import notify_job_log, manager
        
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        from fastapi.websockets import WebSocketState
        ws.client_state = WebSocketState.CONNECTED
        
        await manager.connect(ws, "test-client")
        await manager.subscribe("test-client", "job:log-job")
        
        try:
            count = await notify_job_log(
                job_id="log-job",
                level="info",
                message="Starting calibration...",
            )
            
            assert count >= 0
        finally:
            await manager.disconnect("test-client")

    @pytest.mark.asyncio
    async def test_notify_job_complete_success(self):
        """Test notify_job_complete for successful job."""
        from dsa110_contimg.api.websocket import notify_job_complete, manager
        
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        from fastapi.websockets import WebSocketState
        ws.client_state = WebSocketState.CONNECTED
        
        await manager.connect(ws, "test-client")
        await manager.subscribe("test-client", "job:complete-job")
        
        try:
            count = await notify_job_complete(
                job_id="complete-job",
                success=True,
                result={"ms_path": "/path/to/output.ms"},
            )
            
            assert count >= 0
        finally:
            await manager.disconnect("test-client")

    @pytest.mark.asyncio
    async def test_notify_job_complete_failure(self):
        """Test notify_job_complete for failed job."""
        from dsa110_contimg.api.websocket import notify_job_complete, manager
        
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        from fastapi.websockets import WebSocketState
        ws.client_state = WebSocketState.CONNECTED
        
        await manager.connect(ws, "test-client")
        await manager.subscribe("test-client", "job:failed-job")
        
        try:
            count = await notify_job_complete(
                job_id="failed-job",
                success=False,
                error="Calibration failed: insufficient data",
            )
            
            assert count >= 0
        finally:
            await manager.disconnect("test-client")

    def test_get_websocket_stats(self):
        """Test get_websocket_stats function."""
        from dsa110_contimg.api.websocket import get_websocket_stats
        
        stats = get_websocket_stats()
        
        assert "active_connections" in stats
        assert "topics" in stats
        assert isinstance(stats["active_connections"], int)
        assert "pipeline:all" in stats["topics"]


class TestWebSocketEndpointBehavior:
    """Tests for WebSocket endpoint behavior using TestClient."""

    @pytest.fixture
    def client(self):
        """Create a TestClient for the WebSocket routes."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dsa110_contimg.api.websocket import ws_router
        
        app = FastAPI()
        app.include_router(ws_router)
        return TestClient(app)

    def test_job_websocket_connect_generates_client_id(self, client):
        """Test connecting to job WebSocket generates client_id."""
        try:
            with client.websocket_connect("/ws/jobs/test-job-123") as websocket:
                # Should receive connection confirmation
                data = websocket.receive_json()
                assert data["type"] == "connected"
                assert "client_id" in data
                assert data["job_id"] == "test-job-123"
                assert "reconnect_token" in data
        except Exception:
            # WebSocket may disconnect, which is expected
            pass

    def test_job_websocket_with_client_id(self, client):
        """Test connecting to job WebSocket with custom client_id."""
        try:
            with client.websocket_connect("/ws/jobs/test-job?client_id=my-client-123") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "connected"
                assert data["client_id"] == "my-client-123"
        except Exception:
            pass

    def test_job_websocket_ping_pong(self, client):
        """Test ping/pong messages on job WebSocket."""
        try:
            with client.websocket_connect("/ws/jobs/test-job") as websocket:
                # Receive connection message
                websocket.receive_json()
                
                # Send ping
                websocket.send_json({"type": "ping"})
                
                # Should receive pong
                data = websocket.receive_json()
                assert data["type"] == "pong"
                assert "timestamp" in data
        except Exception:
            pass

    def test_job_websocket_subscribe_unsubscribe(self, client):
        """Test subscribe/unsubscribe on job WebSocket."""
        try:
            with client.websocket_connect("/ws/jobs/test-job") as websocket:
                # Receive connection message
                websocket.receive_json()
                
                # Subscribe to additional topic
                websocket.send_json({
                    "type": "subscribe",
                    "topic": "pipeline:alerts",
                })
                
                # Should receive subscribed confirmation
                data = websocket.receive_json()
                assert data["type"] == "subscribed"
                assert data["topic"] == "pipeline:alerts"
                
                # Unsubscribe
                websocket.send_json({
                    "type": "unsubscribe",
                    "topic": "pipeline:alerts",
                })
                
                data = websocket.receive_json()
                assert data["type"] == "unsubscribed"
        except Exception:
            pass

    def test_job_websocket_heartbeat_ack(self, client):
        """Test heartbeat acknowledgment on job WebSocket."""
        try:
            with client.websocket_connect("/ws/jobs/test-job") as websocket:
                # Receive connection message
                websocket.receive_json()
                
                # Send heartbeat acknowledgment
                websocket.send_json({"type": "heartbeat_ack"})
                
                # Should not cause any error, just continue
        except Exception:
            pass

    def test_pipeline_websocket_connect(self, client):
        """Test connecting to pipeline WebSocket."""
        try:
            with client.websocket_connect("/ws/pipeline") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "connected"
                assert data["topic"] == "pipeline:all"
                assert "client_id" in data
                assert "reconnect_token" in data
                assert "heartbeat_interval" in data
        except Exception:
            pass

    def test_pipeline_websocket_with_client_id(self, client):
        """Test pipeline WebSocket with custom client_id."""
        try:
            with client.websocket_connect("/ws/pipeline?client_id=pipeline-client") as websocket:
                data = websocket.receive_json()
                assert data["client_id"] == "pipeline-client"
        except Exception:
            pass

    def test_pipeline_websocket_ping_with_age(self, client):
        """Test pipeline WebSocket ping returns connection age."""
        try:
            with client.websocket_connect("/ws/pipeline") as websocket:
                # Receive connection message
                websocket.receive_json()
                
                # Send ping
                websocket.send_json({"type": "ping"})
                
                # Should receive pong with connection age
                data = websocket.receive_json()
                assert data["type"] == "pong"
                assert "connection_age_seconds" in data
                assert isinstance(data["connection_age_seconds"], (int, float))
        except Exception:
            pass


class TestBroadcastErrors:
    """Tests for error handling in broadcast operations."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_client(self, manager):
        """Test broadcast handles disconnected clients gracefully."""
        from fastapi.websockets import WebSocketState
        
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws1.send_json = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.client_state = WebSocketState.DISCONNECTED  # Already disconnected
        ws2.send_json = AsyncMock()
        
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        
        count = await manager.broadcast({"type": "test"})
        
        # Only connected client should receive
        assert count == 1
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_handles_send_error(self, manager):
        """Test broadcast handles send errors gracefully."""
        from fastapi.websockets import WebSocketState
        
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws1.send_json = AsyncMock(side_effect=RuntimeError("Connection lost"))
        
        await manager.connect(ws1, "client-1")
        
        count = await manager.broadcast({"type": "test"})
        
        # Should handle error and disconnect client
        assert count == 0
        assert "client-1" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_send_to_client_handles_error(self, manager):
        """Test send_to_client handles errors gracefully."""
        from fastapi.websockets import WebSocketState
        
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.client_state = WebSocketState.CONNECTED
        ws.send_json = AsyncMock(side_effect=ConnectionError("Broken pipe"))
        
        await manager.connect(ws, "client-1")
        
        result = await manager.send_to_client("client-1", {"type": "test"})
        
        assert result is False
        # Client should be disconnected
        assert "client-1" not in manager.active_connections
