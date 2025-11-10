"""
State repository abstraction for pipeline state persistence.

Provides a clean interface for persisting and retrieving pipeline state,
allowing for easy testing with in-memory implementations and potential
future migration to other backends.
"""

from __future__ import annotations

import json
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dsa110_contimg.database.jobs import append_job_log as db_append_job_log
from dsa110_contimg.database.jobs import create_job as db_create_job
from dsa110_contimg.database.jobs import (
    ensure_jobs_table,
)
from dsa110_contimg.database.jobs import get_job as db_get_job
from dsa110_contimg.database.jobs import list_jobs as db_list_jobs
from dsa110_contimg.database.jobs import update_job_status as db_update_job_status
from dsa110_contimg.database.products import ensure_products_db


@dataclass
class JobState:
    """Job state representation."""

    id: int
    type: str
    status: str
    context: Dict[str, Any]
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class StateRepository(ABC):
    """Abstract interface for state persistence."""

    @abstractmethod
    def create_job(self, job_type: str, context: Dict[str, Any]) -> int:
        """Create new job and return ID.

        Args:
            job_type: Type of job (e.g., 'workflow', 'convert', 'calibrate')
            context: Initial context dictionary

        Returns:
            Job ID
        """
        ...

    @abstractmethod
    def update_job(self, job_id: int, updates: Dict[str, Any]) -> None:
        """Update job state.

        Args:
            job_id: Job ID
            updates: Dictionary of fields to update (status, context, etc.)
        """
        ...

    @abstractmethod
    def get_job(self, job_id: int) -> Optional[JobState]:
        """Get job state.

        Args:
            job_id: Job ID

        Returns:
            JobState or None if not found
        """
        ...

    @abstractmethod
    def list_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[JobState]:
        """List jobs with filters.

        Args:
            status: Filter by status
            job_type: Filter by job type
            limit: Maximum number of results

        Returns:
            List of JobState
        """
        ...

    @abstractmethod
    def append_job_log(self, job_id: int, line: str) -> None:
        """Append log line to job.

        Args:
            job_id: Job ID
            line: Log line to append
        """
        ...

    @abstractmethod
    def upsert_ms_index(self, ms_path: str, metadata: Dict[str, Any]) -> None:
        """Upsert MS index entry.

        Args:
            ms_path: Path to Measurement Set
            metadata: Metadata dictionary (start_mjd, end_mjd, status, etc.)
        """
        ...


class SQLiteStateRepository(StateRepository):
    """SQLite implementation of state repository.

    Wraps existing database functions to provide repository interface.
    """

    def __init__(self, products_db: Path):
        """Initialize SQLite state repository.

        Args:
            products_db: Path to products database
        """
        self.products_db = products_db
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> "SQLiteStateRepository":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, ensure connection is closed."""
        self.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection, creating if necessary."""
        if self._conn is None:
            self._conn = ensure_products_db(self.products_db)
        return self._conn

    def create_job(self, job_type: str, context: Dict[str, Any]) -> int:
        """Create new job and return ID."""
        conn = self._get_conn()
        # Legacy format: ms_path is required but empty for workflow jobs
        ms_path = context.get("ms_path", "")
        return db_create_job(conn, job_type, ms_path, context)

    def update_job(self, job_id: int, updates: Dict[str, Any]) -> None:
        """Update job state."""
        conn = self._get_conn()
        status = updates.get("status")
        if status:
            db_update_job_status(
                conn,
                job_id,
                status,
                started_at=updates.get("started_at"),
                finished_at=updates.get("finished_at"),
                artifacts=(
                    json.dumps(updates.get("artifacts", []))
                    if "artifacts" in updates
                    else None
                ),
            )

    def get_job(self, job_id: int) -> Optional[JobState]:
        """Get job state."""
        conn = self._get_conn()
        job_dict = db_get_job(conn, job_id)
        if not job_dict:
            return None

        return JobState(
            id=job_dict["id"],
            type=job_dict["type"],
            status=job_dict["status"],
            context=job_dict.get("params", {}),
            created_at=job_dict["created_at"],
            started_at=job_dict.get("started_at"),
            finished_at=job_dict.get("finished_at"),
        )

    def list_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[JobState]:
        """List jobs with filters."""
        conn = self._get_conn()
        jobs_dict = db_list_jobs(conn, limit=limit, status=status)

        # Filter by job_type if specified
        if job_type:
            jobs_dict = [j for j in jobs_dict if j["type"] == job_type]

        return [
            JobState(
                id=j["id"],
                type=j["type"],
                status=j["status"],
                context=j.get("params", {}),
                created_at=j["created_at"],
                started_at=j.get("started_at"),
                finished_at=j.get("finished_at"),
            )
            for j in jobs_dict
        ]

    def append_job_log(self, job_id: int, line: str) -> None:
        """Append log line to job."""
        conn = self._get_conn()
        db_append_job_log(conn, job_id, line)
        # Batch commits - don't commit every line
        # Caller should manage commits

    def upsert_ms_index(self, ms_path: str, metadata: Dict[str, Any]) -> None:
        """Upsert MS index entry."""
        from dsa110_contimg.database.products import ms_index_upsert

        conn = self._get_conn()
        ms_index_upsert(
            conn,
            ms_path,
            start_mjd=metadata.get("start_mjd"),
            end_mjd=metadata.get("end_mjd"),
            mid_mjd=metadata.get("mid_mjd"),
            status=metadata.get("status"),
            stage=metadata.get("stage"),
            cal_applied=metadata.get("cal_applied", 0),
            imagename=metadata.get("imagename"),
        )
        conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


class InMemoryStateRepository(StateRepository):
    """In-memory implementation for testing."""

    def __init__(self):
        """Initialize in-memory repository."""
        self._jobs: Dict[int, JobState] = {}
        self._job_logs: Dict[int, List[str]] = {}
        self._ms_index: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1

    def create_job(self, job_type: str, context: Dict[str, Any]) -> int:
        """Create new job and return ID."""
        job_id = self._next_id
        self._next_id += 1

        job = JobState(
            id=job_id,
            type=job_type,
            status="pending",
            context=context,
            created_at=time.time(),
        )
        self._jobs[job_id] = job
        self._job_logs[job_id] = []
        return job_id

    def update_job(self, job_id: int, updates: Dict[str, Any]) -> None:
        """Update job state."""
        if job_id not in self._jobs:
            return

        job = self._jobs[job_id]
        if "status" in updates:
            job.status = updates["status"]
        if "started_at" in updates:
            job.started_at = updates["started_at"]
        if "finished_at" in updates:
            job.finished_at = updates["finished_at"]
        if "context" in updates:
            job.context.update(updates["context"])
        if "error_message" in updates:
            job.error_message = updates["error_message"]
        if "retry_count" in updates:
            job.retry_count = updates["retry_count"]

    def get_job(self, job_id: int) -> Optional[JobState]:
        """Get job state."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[JobState]:
        """List jobs with filters."""
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]
        if job_type:
            jobs = [j for j in jobs if j.type == job_type]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def append_job_log(self, job_id: int, line: str) -> None:
        """Append log line to job."""
        if job_id not in self._job_logs:
            self._job_logs[job_id] = []
        self._job_logs[job_id].append(line)

    def upsert_ms_index(self, ms_path: str, metadata: Dict[str, Any]) -> None:
        """Upsert MS index entry."""
        self._ms_index[ms_path] = metadata.copy()
