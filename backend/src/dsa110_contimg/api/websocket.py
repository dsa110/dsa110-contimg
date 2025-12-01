"""
WebSocket support for real-time updates.

Provides WebSocket endpoints for:
- Job status updates
- Pipeline progress notifications
- Live log streaming

Features:
- Server-initiated heartbeat for connection health monitoring
- Automatic reconnection hints on graceful disconnect
- Topic-based pub/sub messaging
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

from .config import get_config


logger = logging.getLogger(__name__)


# WebSocket router
ws_router = APIRouter(prefix="/ws", tags=["websocket"])


class DisconnectReason(str, Enum):
    """Reasons for WebSocket disconnection."""
    NORMAL = "normal"
    TIMEOUT = "timeout"
    ERROR = "error"
    SERVER_SHUTDOWN = "server_shutdown"
    CLIENT_GONE = "client_gone"


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    missed_heartbeats: int = 0
    reconnect_token: Optional[str] = None


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.
    
    Supports subscription-based messaging where clients can subscribe
    to specific topics (e.g., "job:123", "pipeline:imaging").
    
    Features:
    - Server-initiated heartbeat for connection health monitoring
    - Graceful disconnect with reason codes and reconnection hints
    - Topic-based pub/sub messaging
    """
    
    # Heartbeat settings
    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_MISSED_HEARTBEATS = 3  # disconnect after this many missed
    
    def __init__(self):
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        user_id: Optional[str] = None,
        reconnect_token: Optional[str] = None,
    ) -> str:
        """Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket instance
            client_id: Unique identifier for this connection
            user_id: Optional user identifier
            reconnect_token: Token from previous connection for session resumption
            
        Returns:
            New reconnect token for future reconnections
        """
        import uuid
        await websocket.accept()
        
        # Generate new reconnect token
        new_token = str(uuid.uuid4())
        
        async with self._lock:
            self.active_connections[client_id] = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                reconnect_token=new_token,
            )
        
        logger.info(f"WebSocket connected: {client_id}")
        return new_token
    
    async def disconnect(
        self,
        client_id: str,
        reason: DisconnectReason = DisconnectReason.NORMAL,
        send_close: bool = True,
    ) -> None:
        """Remove a WebSocket connection with reason.
        
        Args:
            client_id: The client to disconnect
            reason: Reason for disconnection
            send_close: Whether to send close frame to client
        """
        async with self._lock:
            info = self.active_connections.get(client_id)
            if info:
                if send_close:
                    try:
                        if info.websocket.client_state == WebSocketState.CONNECTED:
                            # Send disconnect message with reconnection info
                            await info.websocket.send_json({
                                "type": "disconnect",
                                "reason": reason.value,
                                "reconnect_token": info.reconnect_token,
                                "can_reconnect": reason != DisconnectReason.ERROR,
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                            })
                    except (RuntimeError, ConnectionError):
                        pass  # Connection already closed
                del self.active_connections[client_id]
        
        logger.info(f"WebSocket disconnected: {client_id} (reason: {reason.value})")
    
    async def handle_heartbeat_response(self, client_id: str) -> None:
        """Handle heartbeat response from client, resetting missed count."""
        async with self._lock:
            if client_id in self.active_connections:
                self.active_connections[client_id].last_heartbeat = datetime.utcnow()
                self.active_connections[client_id].missed_heartbeats = 0
    
    async def send_heartbeat(self, client_id: str) -> bool:
        """Send heartbeat to a specific client.
        
        Returns True if heartbeat was sent successfully.
        """
        async with self._lock:
            info = self.active_connections.get(client_id)
        
        if not info:
            return False
        
        try:
            if info.websocket.client_state == WebSocketState.CONNECTED:
                await info.websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
                async with self._lock:
                    if client_id in self.active_connections:
                        self.active_connections[client_id].missed_heartbeats += 1
                return True
        except (RuntimeError, ConnectionError):
            await self.disconnect(client_id, DisconnectReason.CLIENT_GONE, send_close=False)
        
        return False
    
    async def check_connection_health(self) -> List[str]:
        """Check all connections and disconnect unhealthy ones.
        
        Returns list of disconnected client IDs.
        """
        disconnected = []
        
        async with self._lock:
            connections = list(self.active_connections.items())
        
        for client_id, info in connections:
            if info.missed_heartbeats >= self.MAX_MISSED_HEARTBEATS:
                await self.disconnect(client_id, DisconnectReason.TIMEOUT)
                disconnected.append(client_id)
        
        return disconnected
    
    async def start_heartbeat_loop(self) -> None:
        """Start the background heartbeat task."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("WebSocket heartbeat loop started")
    
    async def stop_heartbeat_loop(self) -> None:
        """Stop the background heartbeat task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("WebSocket heartbeat loop stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Background task that sends heartbeats to all connections."""
        while True:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                # Send heartbeats to all connections
                async with self._lock:
                    client_ids = list(self.active_connections.keys())
                
                for client_id in client_ids:
                    await self.send_heartbeat(client_id)
                
                # Check for unhealthy connections
                await self.check_connection_health()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def subscribe(self, client_id: str, topic: str) -> bool:
        """Subscribe a client to a topic."""
        async with self._lock:
            if client_id in self.active_connections:
                self.active_connections[client_id].subscriptions.add(topic)
                return True
        return False
    
    async def unsubscribe(self, client_id: str, topic: str) -> bool:
        """Unsubscribe a client from a topic."""
        async with self._lock:
            if client_id in self.active_connections:
                self.active_connections[client_id].subscriptions.discard(topic)
                return True
        return False
    
    async def send_to_client(
        self,
        client_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """Send a message to a specific client."""
        async with self._lock:
            info = self.active_connections.get(client_id)
        
        if not info:
            return False
        
        try:
            if info.websocket.client_state == WebSocketState.CONNECTED:
                await info.websocket.send_json(message)
                return True
        except (RuntimeError, ConnectionError) as e:
            logger.error(f"Error sending to {client_id}: {e}")
            await self.disconnect(client_id, DisconnectReason.ERROR)
        
        return False
    
    async def broadcast(
        self,
        message: Dict[str, Any],
        topic: Optional[str] = None,
    ) -> int:
        """
        Broadcast a message to all connected clients.
        
        If topic is specified, only send to clients subscribed to that topic.
        Returns number of clients message was sent to.
        """
        sent_count = 0
        
        async with self._lock:
            connections = list(self.active_connections.items())
        
        for client_id, info in connections:
            # Check topic subscription if specified
            if topic and topic not in info.subscriptions:
                continue
            
            try:
                if info.websocket.client_state == WebSocketState.CONNECTED:
                    await info.websocket.send_json(message)
                    sent_count += 1
            except (RuntimeError, ConnectionError) as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                await self.disconnect(client_id, DisconnectReason.ERROR)
        
        return sent_count
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
    
    def get_topic_subscribers(self, topic: str) -> int:
        """Get number of subscribers for a topic."""
        count = 0
        for info in self.active_connections.values():
            if topic in info.subscriptions:
                count += 1
        return count


# Global connection manager
manager = ConnectionManager()


@ws_router.websocket("/jobs/{job_id}")
async def websocket_job_updates(
    websocket: WebSocket,
    job_id: str,
    client_id: str = Query(None),
    reconnect_token: str = Query(None),
):
    """
    WebSocket endpoint for job status updates.
    
    Clients connect to receive real-time updates about a specific job.
    Messages are JSON objects with structure:
    {
        "type": "status" | "progress" | "log" | "error" | "complete",
        "job_id": "...",
        "data": {...},
        "timestamp": "..."
    }
    
    Heartbeat:
    - Server sends "heartbeat" messages periodically
    - Client should respond with "heartbeat_ack" to confirm connection health
    - Connection is dropped after 3 missed heartbeats
    
    Reconnection:
    - On disconnect, client receives a reconnect_token
    - Pass this token when reconnecting to resume subscriptions
    """
    # Generate client ID if not provided
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())
    
    new_token = await manager.connect(websocket, client_id, reconnect_token=reconnect_token)
    await manager.subscribe(client_id, f"job:{job_id}")
    
    try:
        # Send initial connection confirmation with reconnect token
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "client_id": client_id,
            "reconnect_token": new_token,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (ping/pong, subscriptions, etc.)
                config = get_config()
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=config.timeouts.websocket_ping,
                )
                
                # Handle client messages
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    })
                
                elif msg_type == "heartbeat_ack":
                    # Client acknowledged heartbeat - reset missed count
                    await manager.handle_heartbeat_response(client_id)
                
                elif msg_type == "subscribe":
                    topic = data.get("topic")
                    if topic:
                        await manager.subscribe(client_id, topic)
                        await websocket.send_json({
                            "type": "subscribed",
                            "topic": topic,
                        })
                
                elif msg_type == "unsubscribe":
                    topic = data.get("topic")
                    if topic:
                        await manager.unsubscribe(client_id, topic)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "topic": topic,
                        })
                        
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    })
                except (RuntimeError, ConnectionError):
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_id}")
    except (RuntimeError, ConnectionError) as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        await manager.disconnect(client_id)


@ws_router.websocket("/pipeline")
async def websocket_pipeline_updates(
    websocket: WebSocket,
    client_id: str = Query(None),
):
    """
    WebSocket endpoint for general pipeline updates.
    
    Receives updates about all pipeline activity:
    - New jobs started
    - Job completions
    - Error notifications
    - System status changes
    """
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())
    
    await manager.connect(websocket, client_id)
    await manager.subscribe(client_id, "pipeline:all")
    
    try:
        await websocket.send_json({
            "type": "connected",
            "topic": "pipeline:all",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        
        while True:
            try:
                config = get_config()
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=config.timeouts.websocket_ping,
                )
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(client_id)


# Helper functions for sending updates

async def notify_job_status(
    job_id: str,
    status: str,
    progress: Optional[float] = None,
    message: Optional[str] = None,
) -> int:
    """
    Send job status update to subscribed clients.
    
    Returns number of clients notified.
    """
    update = {
        "type": "status",
        "job_id": job_id,
        "data": {
            "status": status,
            "progress": progress,
            "message": message,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    # Notify job-specific subscribers
    count = await manager.broadcast(update, topic=f"job:{job_id}")
    
    # Also notify pipeline subscribers
    count += await manager.broadcast(update, topic="pipeline:all")
    
    return count


async def notify_job_progress(
    job_id: str,
    progress: float,
    stage: Optional[str] = None,
    eta_seconds: Optional[float] = None,
) -> int:
    """Send job progress update."""
    update = {
        "type": "progress",
        "job_id": job_id,
        "data": {
            "progress": progress,
            "stage": stage,
            "eta_seconds": eta_seconds,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    return await manager.broadcast(update, topic=f"job:{job_id}")


async def notify_job_log(
    job_id: str,
    level: str,
    message: str,
) -> int:
    """Send job log message."""
    update = {
        "type": "log",
        "job_id": job_id,
        "data": {
            "level": level,
            "message": message,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    return await manager.broadcast(update, topic=f"job:{job_id}")


async def notify_job_complete(
    job_id: str,
    success: bool,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> int:
    """Send job completion notification."""
    update = {
        "type": "complete",
        "job_id": job_id,
        "data": {
            "success": success,
            "result": result,
            "error": error,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    count = await manager.broadcast(update, topic=f"job:{job_id}")
    count += await manager.broadcast(update, topic="pipeline:all")
    
    return count


def get_websocket_stats() -> Dict[str, Any]:
    """Get WebSocket connection statistics."""
    return {
        "active_connections": manager.get_connection_count(),
        "topics": {
            "pipeline:all": manager.get_topic_subscribers("pipeline:all"),
        },
    }
