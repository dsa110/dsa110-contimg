"""
Absurd worker with WebSocket event emission.

Emits task_update and queue_stats_update events when tasks change state.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from dsa110_contimg.absurd.client import AbsurdClient
from dsa110_contimg.absurd.config import AbsurdConfig

logger = logging.getLogger(__name__)

# Global WebSocket manager (set by API on worker initialization)
_websocket_manager: Optional[object] = None


def set_websocket_manager(manager):
    """Set the WebSocket manager for emitting events."""
    global _websocket_manager
    _websocket_manager = manager


async def emit_task_update(queue_name: str, task_id: str, update: dict):
    """Emit task_update WebSocket event."""
    if _websocket_manager:
        try:
            await _websocket_manager.broadcast(
                {
                    "type": "task_update",
                    "queue_name": queue_name,
                    "task_id": task_id,
                    "update": update,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to emit task_update event: {e}")


async def emit_queue_stats_update(queue_name: str):
    """Emit queue_stats_update WebSocket event."""
    if _websocket_manager:
        try:
            await _websocket_manager.broadcast(
                {
                    "type": "queue_stats_update",
                    "queue_name": queue_name,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to emit queue_stats_update event: {e}")
