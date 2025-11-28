"""
Absurd worker with WebSocket event emission.

Emits task_update and queue_stats_update events when tasks change state.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

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


class AbsurdWorker:
    """Durable worker process for Absurd tasks.

    Polls the queue for pending tasks, executes them using the provided
    handler function, and manages task state (claim, complete, fail).
    """

    def __init__(
        self,
        config: AbsurdConfig,
        executor_func: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]],
    ):
        self.config = config
        self.executor = executor_func
        self.client = AbsurdClient(config.database_url)
        self.worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self.running = False
        self._stop_event = asyncio.Event()

    async def start(self):
        """Start the worker polling loop."""
        logger.info(f"Starting Absurd worker {self.worker_id} on queue {self.config.queue_name}")
        self.running = True

        async with self.client:
            while self.running:
                try:
                    # 1. Try to claim a task
                    task = await self.client.claim_task(self.config.queue_name, self.worker_id)

                    if task:
                        await self._process_task(task)
                    else:
                        # No tasks, sleep briefly
                        try:
                            await asyncio.wait_for(
                                self._stop_event.wait(),
                                timeout=self.config.worker_poll_interval_sec,
                            )
                        except asyncio.TimeoutError:
                            pass

                except Exception:
                    logger.exception("Error in worker polling loop")
                    await asyncio.sleep(5.0)  # Backoff on infrastructure error

        logger.info(f"Worker {self.worker_id} stopped")

    async def stop(self):
        """Signal the worker to stop after the current task."""
        self.running = False
        self._stop_event.set()

    async def _process_task(self, task: Dict[str, Any]):
        """Process a single claimed task."""
        task_id = task["task_id"]
        task_name = task["task_name"]
        logger.info(f"Processing task {task_id} ({task_name})")

        # Notify start
        await emit_task_update(
            self.config.queue_name,
            task_id,
            {"status": "processing", "worker_id": self.worker_id},
        )

        # Start heartbeat loop
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(task_id))

        try:
            # Execute payload
            result = await self.executor(task_name, task["params"])

            # Check result status
            if result.get("status") == "error":
                error_msg = "; ".join(result.get("errors", ["Unknown error"]))
                await self._handle_failure(task, error_msg)
            else:
                await self.client.complete_task(task_id, result)
                logger.info(f"Task {task_id} completed successfully")
                await emit_task_update(
                    self.config.queue_name,
                    task_id,
                    {"status": "completed", "result": result},
                )

        except Exception as e:
            logger.exception(f"Task {task_id} execution raised exception")
            await self._handle_failure(task, str(e))
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            await emit_queue_stats_update(self.config.queue_name)

    async def _handle_failure(self, task: Dict[str, Any], error_msg: str) -> None:
        """Mark task failed and optionally route to DLQ."""
        task_id = task["task_id"]
        await self.client.fail_task(task_id, error_msg)
        logger.error(f"Task {task_id} failed: {error_msg}")
        await emit_task_update(
            self.config.queue_name,
            task_id,
            {"status": "failed", "error": error_msg},
        )
        await self._maybe_route_to_dlq(task, error_msg)

    async def _maybe_route_to_dlq(self, task: Dict[str, Any], error_msg: str) -> None:
        """Send exhausted tasks to a dead letter queue for inspection."""
        if not self.config.dead_letter_enabled:
            return

        retry_count = task.get("retry_count")
        if retry_count is None:
            return

        # Route to DLQ once retries are exhausted
        if retry_count < self.config.max_retries:
            return

        task_id = task["task_id"]
        queue_name = task.get("queue_name", self.config.queue_name)

        payload = {
            "original_task_id": task_id,
            "original_task_name": task.get("task_name"),
            "original_queue": queue_name,
            "params": task.get("params", {}),
            "error": error_msg,
            "retry_count": retry_count,
            "dead_lettered_at": datetime.utcnow().isoformat() + "Z",
            "worker_id": self.worker_id,
        }

        try:
            dlq_task_id = await self.client.spawn_task(
                queue_name=self.config.dead_letter_queue_name,
                task_name="dead-letter",
                params=payload,
                priority=0,
            )
            logger.warning(
                "Routed task %s to DLQ queue %s as %s",
                task_id,
                self.config.dead_letter_queue_name,
                dlq_task_id,
            )
        except Exception as e:
            logger.error(f"Failed to route task {task_id} to DLQ: {e}")

    async def _heartbeat_loop(self, task_id: str):
        """Send periodic heartbeats."""
        interval = 10.0  # Should be < task_timeout
        while True:
            await asyncio.sleep(interval)
            try:
                active = await self.client.heartbeat_task(task_id)
                if not active:
                    logger.warning(f"Heartbeat rejected for {task_id}, aborting execution")
                    # Ideally we would cancel the running executor here,
                    # but since it's running in a thread/subprocess it might be hard.
                    # For now, we just stop heartbeating.
                    break
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
