"""
Absurd client for durable task execution.

Provides an async client for interacting with the Absurd task queue system.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


class AbsurdClient:
    """Async client for Absurd durable task queue.

    Provides methods for spawning tasks, querying task status, and
    managing the task lifecycle.

    Args:
        database_url: PostgreSQL connection URL
        pool_min_size: Minimum connection pool size
        pool_max_size: Maximum connection pool size
    """

    def __init__(self, database_url: str, pool_min_size: int = 2, pool_max_size: int = 10):
        self.database_url = database_url
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Establish connection pool to Absurd database.

        Raises:
            asyncpg.PostgresError: If connection fails
        """
        if self._pool is not None:
            logger.warning("Client already connected")
            return

        logger.info(
            f"Connecting to Absurd database " f"(pool: {self.pool_min_size}-{self.pool_max_size})"
        )
        self._pool = await asyncpg.create_pool(
            self.database_url,
            min_size=self.pool_min_size,
            max_size=self.pool_max_size,
            command_timeout=60,
        )
        logger.info("Connected to Absurd database")

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("Disconnected from Absurd database")

    async def __aenter__(self) -> AbsurdClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def spawn_task(
        self,
        queue_name: str,
        task_name: str,
        params: Dict[str, Any],
        priority: int = 0,
        timeout_sec: Optional[int] = None,
    ) -> UUID:
        """Spawn a new task in the queue.

        Args:
            queue_name: Name of the queue
            task_name: Name/type of the task
            params: Task parameters (JSON-serializable dict)
            priority: Task priority (higher = more urgent)
            timeout_sec: Task timeout in seconds (None = queue default)

        Returns:
            Task UUID

        Raises:
            ValueError: If not connected
            asyncpg.PostgresError: If spawn fails
        """
        if self._pool is None:
            raise ValueError("Client not connected. Call connect() first.")

        logger.info(
            f"Spawning task '{task_name}' in queue '{queue_name}' " f"(priority={priority})"
        )

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT absurd.spawn_task($1, $2, $3, $4, $5)",
                queue_name,
                task_name,
                json.dumps(params),
                priority,
                timeout_sec,
            )
            task_id = row[0]
            logger.info(f"Spawned task {task_id}")
            return task_id

    async def get_task(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """Get task details by ID.

        Args:
            task_id: Task UUID

        Returns:
            Task details dict or None if not found

        Raises:
            ValueError: If not connected
        """
        if self._pool is None:
            raise ValueError("Client not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT t.task_id, t.queue_name, t.task_name, t.params,
                       t.priority, t.status, t.created_at, t.claimed_at,
                       t.completed_at, t.result, t.error, t.retry_count
                FROM absurd.t_tasks t
                WHERE t.task_id = $1
                """,
                task_id,
            )

            if row is None:
                return None

            return {
                "task_id": str(row["task_id"]),
                "queue_name": row["queue_name"],
                "task_name": row["task_name"],
                "params": json.loads(row["params"]) if row["params"] else {},
                "priority": row["priority"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "claimed_at": row["claimed_at"].isoformat() if row["claimed_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "result": json.loads(row["result"]) if row["result"] else None,
                "error": row["error"],
                "retry_count": row["retry_count"],
            }

    async def list_tasks(
        self,
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List tasks matching criteria.

        Args:
            queue_name: Filter by queue name (None = all queues)
            status: Filter by status (None = all statuses)
            limit: Maximum number of tasks to return

        Returns:
            List of task dicts

        Raises:
            ValueError: If not connected
        """
        if self._pool is None:
            raise ValueError("Client not connected. Call connect() first.")

        query = """
            SELECT t.task_id, t.queue_name, t.task_name, t.params,
                   t.priority, t.status, t.created_at, t.claimed_at,
                   t.completed_at, t.retry_count
            FROM absurd.t_tasks t
            WHERE 1=1
        """
        params = []

        if queue_name:
            params.append(queue_name)
            query += f" AND t.queue_name = ${len(params)}"

        if status:
            params.append(status)
            query += f" AND t.status = ${len(params)}"

        params.append(limit)
        query += f" ORDER BY t.created_at DESC LIMIT ${len(params)}"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            return [
                {
                    "task_id": str(row["task_id"]),
                    "queue_name": row["queue_name"],
                    "task_name": row["task_name"],
                    "params": json.loads(row["params"]) if row["params"] else {},
                    "priority": row["priority"],
                    "status": row["status"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "claimed_at": row["claimed_at"].isoformat() if row["claimed_at"] else None,
                    "completed_at": (
                        row["completed_at"].isoformat() if row["completed_at"] else None
                    ),
                    "retry_count": row["retry_count"],
                }
                for row in rows
            ]

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a pending task.

        Args:
            task_id: Task UUID

        Returns:
            True if task was cancelled, False if not found or
            already completed

        Raises:
            ValueError: If not connected
        """
        if self._pool is None:
            raise ValueError("Client not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE absurd.t_tasks
                SET status = 'cancelled',
                    completed_at = NOW(),
                    error = 'Cancelled by user'
                WHERE task_id = $1
                  AND status IN ('pending', 'claimed')
                """,
                task_id,
            )

            cancelled = result.split()[-1] != "0"
            if cancelled:
                logger.info(f"Cancelled task {task_id}")
            return cancelled

    async def get_queue_stats(self, queue_name: str) -> Dict[str, int]:
        """Get statistics for a queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Dict with counts by status

        Raises:
            ValueError: If not connected
        """
        if self._pool is None:
            raise ValueError("Client not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT status, COUNT(*) as count
                FROM absurd.t_tasks
                WHERE queue_name = $1
                GROUP BY status
                """,
                queue_name,
            )

            stats = {row["status"]: row["count"] for row in rows}
            stats.setdefault("pending", 0)
            stats.setdefault("claimed", 0)
            stats.setdefault("completed", 0)
            stats.setdefault("failed", 0)
            stats.setdefault("cancelled", 0)

            return stats
