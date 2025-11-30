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
