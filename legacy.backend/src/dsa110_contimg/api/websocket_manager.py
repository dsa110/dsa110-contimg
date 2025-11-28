"""
WebSocket/SSE manager for real-time updates.
Manages connections and broadcasts updates to all connected clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Set

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket/SSE connections and broadcasts."""

    def __init__(self):
        self.active_connections: Set[any] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: any):
        """Add a new connection."""
        async with self._lock:
            self.active_connections.add(websocket)
            logger.info(
                f"New connection established. Total connections: {len(self.active_connections)}"
            )

    async def disconnect(self, websocket: any):
        """Remove a connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
            logger.info(f"Connection closed. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        message_str = json.dumps(message)
        dead_connections = set()

        async with self._lock:
            for connection in self.active_connections:
                try:
                    # Try WebSocket send first
                    if hasattr(connection, "send_text"):
                        await connection.send_text(message_str)
                    elif hasattr(connection, "send"):
                        await connection.send(message_str)
                    # SSE format: data: {...}\n\n
                    elif hasattr(connection, "write"):
                        await connection.write(f"data: {message_str}\n\n")
                except Exception as e:
                    logger.warning(f"Failed to send message to connection: {e}")
                    dead_connections.add(connection)

            # Remove dead connections
            self.active_connections -= dead_connections

    async def send_personal_message(self, message: dict, websocket: any):
        """Send a message to a specific connection."""
        message_str = json.dumps(message)
        try:
            if hasattr(websocket, "send_text"):
                await websocket.send_text(message_str)
            elif hasattr(websocket, "send"):
                await websocket.send(message_str)
            elif hasattr(websocket, "write"):
                await websocket.write(f"data: {message_str}\n\n")
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")


# Global connection manager instance
manager = ConnectionManager()


async def event_generator() -> AsyncIterator[str]:
    """Generator for Server-Sent Events."""
    try:
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.now().isoformat()})}\n\n"

        # Keep connection alive with periodic heartbeats
        while True:
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
    except asyncio.CancelledError:
        logger.info("SSE connection cancelled")
    except Exception as e:
        logger.error(f"Error in SSE generator: {e}")


def create_status_update(
    pipeline_status: dict = None, metrics: dict = None, ese_candidates: dict = None
) -> dict:
    """Create a status update message."""
    return {
        "type": "status_update",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "pipeline_status": pipeline_status,
            "metrics": metrics,
            "ese_candidates": ese_candidates,
        },
    }
