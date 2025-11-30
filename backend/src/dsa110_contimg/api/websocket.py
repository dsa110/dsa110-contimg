"""
WebSocket support for real-time updates.

Provides WebSocket endpoints for:
- Job status updates
- Pipeline progress notifications
- Live log streaming
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState


logger = logging.getLogger(__name__)


# WebSocket router
ws_router = APIRouter(prefix="/ws", tags=["websocket"])


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.
    
    Supports subscription-based messaging where clients can subscribe
    to specific topics (e.g., "job:123", "pipeline:imaging").
    """
    
    def __init__(self):
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        user_id: Optional[str] = None,
    ) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            self.active_connections[client_id] = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
            )
        
        logger.info(f"WebSocket connected: {client_id}")
    
    async def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
        
        logger.info(f"WebSocket disconnected: {client_id}")
    
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
        except Exception as e:
            logger.error(f"Error sending to {client_id}: {e}")
            await self.disconnect(client_id)
        
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
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                await self.disconnect(client_id)
        
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
    """
    # Generate client ID if not provided
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())
    
    await manager.connect(websocket, client_id)
    await manager.subscribe(client_id, f"job:{job_id}")
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (ping/pong, subscriptions, etc.)
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0,  # Send ping every 30s
                )
                
                # Handle client messages
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    })
                
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
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
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
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0,
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
