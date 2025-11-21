"""
Task queue for long-running operations
Uses RQ (Redis Queue) for background job processing
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Try to import RQ
try:
    from redis import Redis
    from rq import Queue, Retry
    from rq.job import Job

    RQ_AVAILABLE = True
except ImportError:
    RQ_AVAILABLE = False
    logger.warning("RQ not available, task queue disabled")

# Global queue instances
_queues: dict[str, Any] = {}
_redis_conn: Optional[Any] = None


def get_redis_connection() -> Optional[Any]:
    """Get or create Redis connection for RQ"""
    global _redis_conn

    if not RQ_AVAILABLE:
        return None

    if _redis_conn is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            _redis_conn = Redis.from_url(redis_url)
            _redis_conn.ping()  # Test connection
            logger.info(f"RQ Redis connection established: {redis_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for RQ: {e}")
            _redis_conn = None

    return _redis_conn


def get_queue(name: str = "default") -> Optional[Any]:
    """
    Get or create a task queue

    Args:
        name: Queue name (default: "default")

    Returns:
        RQ Queue instance or None if RQ not available
    """
    if not RQ_AVAILABLE:
        return None

    if name not in _queues:
        redis_conn = get_redis_connection()
        if redis_conn is None:
            return None
        _queues[name] = Queue(name, connection=redis_conn)
        logger.info(f"Created task queue: {name}")

    return _queues[name]


def enqueue_task(
    func: Callable,
    *args: Any,
    queue_name: str = "default",
    timeout: int = 300,
    retry: Optional[Retry] = None,
    **kwargs: Any,
) -> Optional[Job]:
    """
    Enqueue a task for background processing

    Args:
        func: Function to execute
        *args: Positional arguments for function
        queue_name: Queue name (default: "default")
        timeout: Job timeout in seconds (default: 300)
        retry: Retry configuration (default: None)
        **kwargs: Keyword arguments for function

    Returns:
        RQ Job instance or None if queue not available
    """
    queue = get_queue(queue_name)
    if queue is None:
        logger.warning(f"Queue '{queue_name}' not available, task not enqueued")
        return None

    try:
        job = queue.enqueue(
            func,
            *args,
            timeout=timeout,
            retry=retry or Retry(max=3, interval=[60, 120, 300]),
            **kwargs,
        )
        logger.info(f"Task enqueued: {job.id} in queue '{queue_name}'")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue task: {e}")
        return None


def get_job_status(job_id: str) -> Optional[dict[str, Any]]:
    """
    Get job status

    Args:
        job_id: Job ID

    Returns:
        Job status dictionary or None if job not found
    """
    if not RQ_AVAILABLE:
        return None

    redis_conn = get_redis_connection()
    if redis_conn is None:
        return None

    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            "id": job.id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "result": str(job.result) if job.result else None,
            "exc_info": job.exc_info if job.exc_info else None,
        }
    except Exception as e:
        logger.warning(f"Failed to get job status: {e}")
        return None


def get_queue_stats(queue_name: str = "default") -> dict[str, Any]:
    """
    Get queue statistics

    Args:
        queue_name: Queue name

    Returns:
        Queue statistics dictionary
    """
    if not RQ_AVAILABLE:
        return {"available": False, "reason": "RQ not installed"}

    queue = get_queue(queue_name)
    if queue is None:
        return {"available": False, "reason": "Queue not available"}

    try:
        return {
            "available": True,
            "name": queue_name,
            "count": len(queue),
            "failed_count": len(queue.failed_job_registry),
            "started_count": len(queue.started_job_registry),
            "finished_count": len(queue.finished_job_registry),
        }
    except Exception as e:
        logger.warning(f"Failed to get queue stats: {e}")
        return {"available": False, "error": str(e)}


def is_task_queue_available() -> bool:
    """Check if task queue is available"""
    return RQ_AVAILABLE and get_redis_connection() is not None
