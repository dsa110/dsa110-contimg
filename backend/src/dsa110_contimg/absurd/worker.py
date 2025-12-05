"""
Absurd worker implementation.

Provides a worker that polls for tasks from the Absurd queue and
executes them.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import socket
import time
import uuid
from typing import Any, Callable, Coroutine, Dict, Optional

import aiohttp

from dsa110_contimg.absurd import AbsurdClient
from dsa110_contimg.absurd.config import AbsurdConfig

logger = logging.getLogger(__name__)

# Global WebSocket manager for emitting events
_websocket_manager = None


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
            logger.warning(f"Failed to emit task update: {e}")


def _create_jwt_token(secret: str, worker_id: str) -> str:
    """Create a JWT token for worker API authentication.

    Args:
        secret: The JWT secret (DSA110_JWT_SECRET)
        worker_id: The worker ID to use as subject

    Returns:
        JWT token string
    """
    try:
        import jwt
    except ImportError:
        logger.warning("PyJWT not installed - cannot create JWT token")
        return ""

    now = int(time.time())
    payload = {
        "sub": f"worker:{worker_id}",
        "iat": now,
        "exp": now + 3600,  # 1 hour expiry
        "scopes": ["write"],
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class AbsurdWorker:
    """Worker that processes Absurd tasks.

    The worker polls for available tasks, claims them, executes them,
    and reports results back to the queue. Supports graceful shutdown
    and task-level heartbeats for long-running operations.
    """

    def __init__(
        self,
        config: AbsurdConfig,
        executor: Callable[[str, Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]],
    ):
        """Initialize the worker.

        Args:
            config: Absurd configuration
            executor: Async function to execute tasks. Takes task_name and params,
                     returns result dict.
        """
        self.config = config
        self.executor = executor
        self.worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self.client = AbsurdClient(config.database_url)
        self.running = False
        self._current_task_id: Optional[str] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._api_heartbeat_task: Optional[asyncio.Task] = None
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._jwt_token: Optional[str] = None
        self._jwt_refresh_time: float = 0

    async def start(self) -> None:
        """Start the worker loop.

        Continuously polls for tasks, claims them, executes them, and
        reports results. Runs until stop() is called.
        """
        self.running = True
        logger.info(f"Worker {self.worker_id} starting")

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        async with self.client:
            # Start API heartbeat loop if configured
            if self.config.api_base_url:
                self._http_session = aiohttp.ClientSession()
                self._api_heartbeat_task = asyncio.create_task(self._api_heartbeat_loop())
                logger.info(
                    f"API heartbeat enabled: {self.config.api_base_url} "
                    f"(every {self.config.api_heartbeat_interval_sec}s)"
                )

            logger.info(
                f"Worker {self.worker_id} connected, polling queue: {self.config.queue_name}"
            )

            while self.running:
                try:
                    # Try to claim a task
                    task = await self.client.claim_task(
                        queue_name=self.config.queue_name,
                        worker_id=self.worker_id,
                    )

                    if task:
                        await self._process_task(task)
                    else:
                        # No tasks available, wait before polling again
                        await asyncio.sleep(self.config.worker_poll_interval_sec)

                except asyncio.CancelledError:
                    logger.info(f"Worker {self.worker_id} cancelled")
                    break
                except Exception as e:
                    logger.exception(f"Worker error: {e}")
                    await asyncio.sleep(5)  # Back off on errors

        # Clean up
        if self._api_heartbeat_task:
            self._api_heartbeat_task.cancel()
            try:
                await self._api_heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._http_session:
            await self._http_session.close()

        logger.info(f"Worker {self.worker_id} stopped")

    async def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info(f"Worker {self.worker_id} stopping...")
        self.running = False

        # Cancel task heartbeat if running
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

    async def _process_task(self, task: Dict[str, Any]) -> None:
        """Process a claimed task.

        Args:
            task: Task dict with task_id, task_name, params, etc.
        """
        task_id = str(task["task_id"])
        task_name = task["task_name"]
        params = task["params"] or {}

        self._current_task_id = task_id
        logger.info(f"Processing task {task_id}: {task_name}")

        # Start heartbeat loop for this task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(task_id))

        try:
            # Execute the task
            result = await self.executor(task_name, params)

            # Complete the task
            await self.client.complete_task(task_id, result)
            logger.info(f"Task {task_id} completed successfully")

        except asyncio.CancelledError:
            logger.warning(f"Task {task_id} cancelled")
            await self.client.fail_task(task_id, "Task cancelled")
            raise

        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            await self.client.fail_task(task_id, str(e))

        finally:
            self._current_task_id = None
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass

    async def _heartbeat_loop(self, task_id: str) -> None:
        """Send periodic heartbeats for a task.

        Args:
            task_id: The task to heartbeat
        """
        interval = 30  # seconds
        while True:
            try:
                await asyncio.sleep(interval)
                await self.client.heartbeat_task(task_id)
                logger.debug(f"Heartbeat sent for task {task_id}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Failed to send heartbeat for task {task_id}: {e}")

    async def _api_heartbeat_loop(self) -> None:
        """Send periodic heartbeats to the API server for worker registration.

        This allows the API's AbsurdMonitor to track active workers even when
        they are idle (not processing tasks).
        """
        interval = self.config.api_heartbeat_interval_sec
        jwt_secret = os.getenv("DSA110_JWT_SECRET", "")

        if not jwt_secret:
            logger.warning("DSA110_JWT_SECRET not set - API heartbeats will fail authentication")

        while self.running:
            try:
                # Refresh JWT token if needed (every 50 minutes to be safe)
                now = time.time()
                if not self._jwt_token or now - self._jwt_refresh_time > 3000:
                    if jwt_secret:
                        self._jwt_token = _create_jwt_token(jwt_secret, self.worker_id)
                        self._jwt_refresh_time = now
                        logger.debug(f"Refreshed JWT token for worker {self.worker_id}")

                # Send heartbeat to API
                url = f"{self.config.api_base_url}/absurd/workers/{self.worker_id}/heartbeat"
                headers = {}
                if self._jwt_token:
                    headers["Authorization"] = f"Bearer {self._jwt_token}"

                params = {}
                if self._current_task_id:
                    params["task_id"] = self._current_task_id

                async with self._http_session.post(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        logger.debug(f"API heartbeat sent for worker {self.worker_id}")
                    else:
                        text = await resp.text()
                        logger.warning(f"API heartbeat failed ({resp.status}): {text[:200]}")

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except aiohttp.ClientError as e:
                logger.warning(f"API heartbeat connection error: {e}")
                await asyncio.sleep(interval)
            except Exception as e:
                logger.exception(f"API heartbeat error: {e}")
                await asyncio.sleep(interval)


async def default_executor(task_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Default task executor that does nothing.

    This is a placeholder - real workers should provide their own executor.

    Args:
        task_name: Name of the task to execute
        params: Task parameters

    Returns:
        Empty result dict
    """
    logger.warning(f"Default executor called for task {task_name} - no-op")
    return {"status": "no-op", "task_name": task_name}


async def main():
    """Main entry point for running a worker."""
    import argparse

    parser = argparse.ArgumentParser(description="Run an Absurd worker")
    parser.add_argument(
        "--queue", default=None, help="Queue name (default: from ABSURD_QUEUE_NAME)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Number of concurrent tasks (default: from ABSURD_WORKER_CONCURRENCY)",
    )
    args = parser.parse_args()

    # Load configuration
    config = AbsurdConfig.from_env()

    # Override from command line
    if args.queue:
        config.queue_name = args.queue
    if args.concurrency:
        config.worker_concurrency = args.concurrency

    config.validate()

    if not config.enabled:
        logger.error("Absurd is not enabled. Set ABSURD_ENABLED=true")
        return

    # Create and run worker
    worker = AbsurdWorker(config, default_executor)
    await worker.start()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())
