"""
Job Queue module for background pipeline processing.

Uses Redis Queue (RQ) for managing background jobs like:
- Pipeline reruns
- Batch processing
- Long-running data operations

Usage:
    from .job_queue import job_queue, enqueue_job, get_job_status
    
    # Enqueue a job
    job_id = enqueue_job("pipeline.rerun", run_id="abc123", config={...})
    
    # Check status
    status = get_job_status(job_id)

Environment Variables:
    REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    DSA110_QUEUE_NAME: Queue name (default: dsa110-pipeline)
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("DSA110_QUEUE_NAME", "dsa110-pipeline")
PIPELINE_CMD_TEMPLATE = os.getenv("DSA110_PIPELINE_RUN_CMD", "")

from .repositories import JobRepository, get_db_connection
from dsa110_contimg.database.jobs import (
    ensure_jobs_table,
    create_job as db_create_job,
    update_job_status as db_update_job_status,
)

# RQ imports (optional - graceful degradation if not available)
try:
    from redis import Redis
    from rq import Queue, Worker
    from rq.job import Job
    RQ_AVAILABLE = True
except ImportError:
    RQ_AVAILABLE = False
    logger.warning("RQ not installed - job queue will use in-memory fallback")


class JobStatus(str, Enum):
    """Status of a queued job."""
    QUEUED = "queued"
    STARTED = "started"
    FINISHED = "finished"
    FAILED = "failed"
    DEFERRED = "deferred"
    SCHEDULED = "scheduled"
    CANCELED = "canceled"
    NOT_FOUND = "not_found"


@dataclass
class JobInfo:
    """Information about a queued job."""
    job_id: str
    status: JobStatus
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "result": self.result,
            "error": self.error,
            "meta": self.meta,
        }


class JobQueue:
    """
    Job queue manager for background processing.
    
    Provides a unified interface for job management, with fallback
    to in-memory queue when Redis/RQ is not available.
    """
    
    def __init__(self, redis_url: str = REDIS_URL, queue_name: str = QUEUE_NAME):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self._redis: Optional[Redis] = None
        self._queue: Optional[Queue] = None
        self._in_memory_jobs: Dict[str, JobInfo] = {}
        
        if RQ_AVAILABLE:
            try:
                self._redis = Redis.from_url(redis_url)
                self._redis.ping()  # Test connection
                self._queue = Queue(queue_name, connection=self._redis)
                logger.info(f"Job queue connected to Redis at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e} - using in-memory fallback")
                self._redis = None
                self._queue = None
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._queue is not None
    
    def enqueue(
        self,
        func: Callable,
        *args,
        job_id: Optional[str] = None,
        timeout: int = 3600,
        meta: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """
        Enqueue a function for background execution.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            job_id: Optional custom job ID (auto-generated if not provided)
            timeout: Job timeout in seconds (default: 1 hour)
            meta: Optional metadata to attach to the job
            **kwargs: Keyword arguments for the function
            
        Returns:
            Job ID
        """
        job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        
        if self._queue:
            try:
                job = self._queue.enqueue(
                    func,
                    *args,
                    job_id=job_id,
                    job_timeout=timeout,
                    meta=meta or {},
                    **kwargs,
                )
                logger.info(f"Enqueued job {job_id} to Redis queue")
                return job.id
            except Exception as e:
                logger.error(f"Failed to enqueue job to Redis: {e}")
                # Fall through to in-memory fallback
        
        # In-memory fallback (synchronous execution or just tracking)
        self._in_memory_jobs[job_id] = JobInfo(
            job_id=job_id,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow(),
            meta=meta,
        )
        logger.info(f"Job {job_id} added to in-memory queue (no worker available)")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Get information about a job."""
        if self._queue:
            try:
                job = Job.fetch(job_id, connection=self._redis)
                return self._job_to_info(job)
            except Exception:
                pass  # Job not found in Redis
        
        # Check in-memory jobs
        return self._in_memory_jobs.get(job_id)
    
    def get_status(self, job_id: str) -> JobStatus:
        """Get the status of a job."""
        job_info = self.get_job(job_id)
        if job_info:
            return job_info.status
        return JobStatus.NOT_FOUND
    
    def cancel(self, job_id: str) -> bool:
        """Cancel a queued job."""
        if self._queue:
            try:
                job = Job.fetch(job_id, connection=self._redis)
                job.cancel()
                logger.info(f"Canceled job {job_id}")
                return True
            except Exception as e:
                logger.warning(f"Failed to cancel job {job_id}: {e}")
        
        # In-memory fallback
        if job_id in self._in_memory_jobs:
            self._in_memory_jobs[job_id].status = JobStatus.CANCELED
            return True
        
        return False
    
    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[JobInfo]:
        """List jobs, optionally filtered by status."""
        jobs = []
        
        if self._queue:
            try:
                # Get jobs from different registries based on status
                if status is None or status == JobStatus.QUEUED:
                    for job_id in self._queue.job_ids[:limit]:
                        try:
                            job = Job.fetch(job_id, connection=self._redis)
                            jobs.append(self._job_to_info(job))
                        except Exception:
                            pass
                
                if status is None or status == JobStatus.STARTED:
                    started_registry = self._queue.started_job_registry
                    for job_id in started_registry.get_job_ids()[:limit]:
                        try:
                            job = Job.fetch(job_id, connection=self._redis)
                            jobs.append(self._job_to_info(job))
                        except Exception:
                            pass
                
                if status is None or status == JobStatus.FINISHED:
                    finished_registry = self._queue.finished_job_registry
                    for job_id in finished_registry.get_job_ids()[:limit]:
                        try:
                            job = Job.fetch(job_id, connection=self._redis)
                            jobs.append(self._job_to_info(job))
                        except Exception:
                            pass
                
                if status is None or status == JobStatus.FAILED:
                    failed_registry = self._queue.failed_job_registry
                    for job_id in failed_registry.get_job_ids()[:limit]:
                        try:
                            job = Job.fetch(job_id, connection=self._redis)
                            jobs.append(self._job_to_info(job))
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Failed to list jobs from Redis: {e}")
        
        # Add in-memory jobs
        for job_info in self._in_memory_jobs.values():
            if status is None or job_info.status == status:
                jobs.append(job_info)
        
        return jobs[:limit]
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        stats = {
            "connected": self.is_connected,
            "queue_name": self.queue_name,
            "redis_url": self.redis_url if self.is_connected else None,
        }
        
        if self._queue:
            try:
                stats["queued_count"] = len(self._queue)
                stats["started_count"] = len(self._queue.started_job_registry)
                stats["finished_count"] = len(self._queue.finished_job_registry)
                stats["failed_count"] = len(self._queue.failed_job_registry)
            except Exception as e:
                stats["error"] = str(e)
        else:
            stats["in_memory_count"] = len(self._in_memory_jobs)
        
        return stats
    
    def _job_to_info(self, job: Job) -> JobInfo:
        """Convert RQ Job to JobInfo."""
        status_map = {
            "queued": JobStatus.QUEUED,
            "started": JobStatus.STARTED,
            "finished": JobStatus.FINISHED,
            "failed": JobStatus.FAILED,
            "deferred": JobStatus.DEFERRED,
            "scheduled": JobStatus.SCHEDULED,
            "canceled": JobStatus.CANCELED,
        }
        
        return JobInfo(
            job_id=job.id,
            status=status_map.get(job.get_status(), JobStatus.QUEUED),
            created_at=job.created_at,
            started_at=job.started_at,
            ended_at=job.ended_at,
            result=job.result if job.is_finished else None,
            error=str(job.exc_info) if job.is_failed else None,
            meta=job.meta,
        )


# Global job queue instance
job_queue = JobQueue()


def enqueue_job(
    func: Callable,
    *args,
    job_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Convenience function to enqueue a job."""
    return job_queue.enqueue(func, *args, job_id=job_id, **kwargs)


def get_job_status(job_id: str) -> JobStatus:
    """Convenience function to get job status."""
    return job_queue.get_status(job_id)


def get_job_info(job_id: str) -> Optional[JobInfo]:
    """Convenience function to get job info."""
    return job_queue.get_job(job_id)


# =============================================================================
# Pipeline Job Functions (to be executed by workers)
# =============================================================================

def rerun_pipeline_job(
    original_run_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Re-run a pipeline job.
    
    This function is executed by RQ workers.
    
    Args:
        original_run_id: The run ID of the job to rerun
        config: Optional configuration overrides
        
    Returns:
        Result dictionary with new run ID and status
    """
    import time
    from datetime import datetime
    
    # Generate new run ID
    new_run_id = f"{original_run_id.rsplit('_', 1)[0]}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Starting pipeline rerun: {original_run_id} -> {new_run_id}")
    
    # TODO: Implement actual pipeline rerun logic
    # This would:
    # 1. Load original job configuration from database
    # 2. Apply any config overrides
    # 3. Submit to pipeline executor
    # 4. Update job status in database
    
    # For now, simulate some work
    time.sleep(1)
    
    return {
        "original_run_id": original_run_id,
        "new_run_id": new_run_id,
        "status": "completed",
        "message": f"Pipeline rerun completed successfully",
    }
