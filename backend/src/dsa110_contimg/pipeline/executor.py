"""
Pipeline executor: Execute pipelines by spawning ABSURD tasks.

This module bridges the Pipeline abstraction to ABSURD's task queue,
handling:
- Parameter resolution (including ${job.output} references)
- Task spawning with dependencies
- Execution tracking in database
- Status queries

Classes:
    PipelineExecutor: Compiles Pipeline job graphs into ABSURD task chains
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import Job, JobResult, Pipeline, RetryPolicy

logger = logging.getLogger(__name__)


# =============================================================================
# Execution Status
# =============================================================================


@dataclass
class ExecutionStatus:
    """Status of a pipeline execution.

    Attributes:
        execution_id: Unique execution identifier
        pipeline_name: Name of the pipeline
        status: Overall status (pending, running, completed, failed)
        started_at: Start timestamp
        completed_at: Completion timestamp (if finished)
        error: Error message (if failed)
        jobs: List of job statuses
    """

    execution_id: str
    pipeline_name: str
    status: str
    started_at: float
    completed_at: float | None = None
    error: str | None = None
    jobs: list[dict[str, Any]] = field(default_factory=list)


# =============================================================================
# Pipeline Executor
# =============================================================================


class PipelineExecutor:
    """Compiles Pipeline job graphs into ABSURD task chains.

    The executor handles:
    1. Recording execution in the database
    2. Spawning ABSURD tasks for each job
    3. Tracking job -> task mappings
    4. Resolving parameter references

    Example:
        executor = PipelineExecutor(db_path=Path("pipeline.sqlite3"))
        await executor.connect()

        pipeline = NightlyMosaicPipeline(config)
        execution_id = await executor.execute(pipeline)

        status = await executor.get_status(execution_id)
        print(f"Pipeline status: {status.status}")

        await executor.close()
    """

    def __init__(self, db_path: Path):
        """Initialize executor.

        Args:
            db_path: Path to the pipeline database
        """
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure pipeline tracking tables exist."""
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            -- Pipeline execution tracking
            CREATE TABLE IF NOT EXISTS pipeline_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE NOT NULL,
                pipeline_name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at REAL NOT NULL,
                completed_at REAL,
                error TEXT,
                config_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_pipeline_executions_name
                ON pipeline_executions(pipeline_name);
            CREATE INDEX IF NOT EXISTS idx_pipeline_executions_started
                ON pipeline_executions(started_at);
            CREATE INDEX IF NOT EXISTS idx_pipeline_executions_status
                ON pipeline_executions(status);

            -- Individual job tracking within pipeline
            CREATE TABLE IF NOT EXISTS pipeline_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                job_type TEXT NOT NULL,
                absurd_task_id TEXT,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                started_at REAL,
                completed_at REAL,
                params_json TEXT,
                outputs_json TEXT,
                error TEXT,
                FOREIGN KEY(execution_id) REFERENCES pipeline_executions(execution_id)
            );

            CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_execution
                ON pipeline_jobs(execution_id);
            CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_task
                ON pipeline_jobs(absurd_task_id);
            CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_status
                ON pipeline_jobs(status);
        """)
        conn.commit()
        conn.close()

    async def execute(self, pipeline: Pipeline) -> str:
        """Execute a pipeline by spawning ABSURD tasks.

        Args:
            pipeline: Pipeline instance to execute

        Returns:
            execution_id: Unique ID for this pipeline run
        """
        # Generate execution ID
        execution_id = f"{pipeline.pipeline_name}_{uuid.uuid4().hex[:12]}"
        now = time.time()

        conn = sqlite3.connect(str(self.db_path))

        # Record execution
        conn.execute(
            """
            INSERT INTO pipeline_executions
                (execution_id, pipeline_name, status, started_at, config_json)
            VALUES (?, ?, 'running', ?, ?)
            """,
            (
                execution_id,
                pipeline.pipeline_name,
                now,
                json.dumps({"retry_policy": pipeline.retry_policy.__dict__}),
            ),
        )
        conn.commit()

        logger.info(f"Starting pipeline execution: {execution_id}")

        # Get execution order
        execution_order = pipeline.get_execution_order()
        task_map: dict[str, str] = {}  # job_id -> ABSURD task_id

        try:
            for job_id in execution_order:
                job_config = pipeline.get_job(job_id)
                if not job_config:
                    raise ValueError(f"Job {job_id} not found")

                # Resolve dependencies to ABSURD task IDs
                depends_on = []
                for dep_job_id in job_config.dependencies:
                    if dep_job_id not in task_map:
                        raise ValueError(
                            f"Job {job_id} depends on {dep_job_id} "
                            f"which hasn't been spawned yet"
                        )
                    depends_on.append(task_map[dep_job_id])

                # Prepare deferred params (${job.output} references)
                resolved_params = self._prepare_params(
                    job_config.params,
                    execution_id,
                )

                # Add execution context
                resolved_params["_execution_id"] = execution_id
                resolved_params["_job_id"] = job_id
                resolved_params["_pipeline_name"] = pipeline.pipeline_name

                # Record job in database
                task_id = f"task_{job_id}_{uuid.uuid4().hex[:8]}"
                conn.execute(
                    """
                    INSERT INTO pipeline_jobs
                        (execution_id, job_id, job_type, absurd_task_id,
                         status, created_at, params_json)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?)
                    """,
                    (
                        execution_id,
                        job_id,
                        job_config.job_class.job_type,
                        task_id,
                        now,
                        json.dumps(resolved_params),
                    ),
                )
                conn.commit()

                task_map[job_id] = task_id

                logger.info(f"Registered job {job_id} as task {task_id}")

            # Now spawn tasks via ABSURD
            # For now, we execute synchronously in-process
            # Future: Use AbsurdClient.spawn() for distributed execution
            await self._execute_jobs_sync(pipeline, execution_id, conn)

        except Exception as e:
            logger.exception(f"Pipeline execution failed: {e}")
            conn.execute(
                """
                UPDATE pipeline_executions
                SET status = 'failed', completed_at = ?, error = ?
                WHERE execution_id = ?
                """,
                (time.time(), str(e), execution_id),
            )
            conn.commit()
            raise

        finally:
            conn.close()

        return execution_id

    async def _execute_jobs_sync(
        self,
        pipeline: Pipeline,
        execution_id: str,
        conn: sqlite3.Connection,
    ) -> None:
        """Execute jobs synchronously (for now).

        Future: Replace with ABSURD task spawning.
        """
        from .registry import get_job_registry

        execution_order = pipeline.get_execution_order()
        results: dict[str, JobResult] = {}

        for job_id in execution_order:
            job_config = pipeline.get_job(job_id)
            if not job_config:
                continue

            # Update status to running
            conn.execute(
                """
                UPDATE pipeline_jobs
                SET status = 'running', started_at = ?
                WHERE execution_id = ? AND job_id = ?
                """,
                (time.time(), execution_id, job_id),
            )
            conn.commit()

            # Resolve parameter references
            resolved_params = self._resolve_params(job_config.params, results)

            # Execute with retry
            result = await self._execute_with_retry(
                job_config,
                resolved_params,
                pipeline.retry_policy,
                pipeline.config,
            )

            results[job_id] = result

            # Update job status
            if result.success:
                conn.execute(
                    """
                    UPDATE pipeline_jobs
                    SET status = 'completed', completed_at = ?, outputs_json = ?
                    WHERE execution_id = ? AND job_id = ?
                    """,
                    (
                        time.time(),
                        json.dumps(result.outputs),
                        execution_id,
                        job_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE pipeline_jobs
                    SET status = 'failed', completed_at = ?, error = ?
                    WHERE execution_id = ? AND job_id = ?
                    """,
                    (time.time(), result.error, execution_id, job_id),
                )

                # Update execution status
                conn.execute(
                    """
                    UPDATE pipeline_executions
                    SET status = 'failed', completed_at = ?, error = ?
                    WHERE execution_id = ?
                    """,
                    (
                        time.time(),
                        f"Job {job_id} failed: {result.error}",
                        execution_id,
                    ),
                )
                conn.commit()

                # Send failure notification
                self._send_notification(pipeline, job_id, "failure", result.error)
                return

            conn.commit()

        # All jobs completed
        conn.execute(
            """
            UPDATE pipeline_executions
            SET status = 'completed', completed_at = ?
            WHERE execution_id = ?
            """,
            (time.time(), execution_id),
        )
        conn.commit()

        # Send success notification for final job
        if execution_order:
            self._send_notification(pipeline, execution_order[-1], "success", None)

        logger.info(f"Pipeline {execution_id} completed successfully")

    async def _execute_with_retry(
        self,
        job_config: Any,
        params: dict[str, Any],
        retry_policy: RetryPolicy,
        pipeline_config: Any,
    ) -> JobResult:
        """Execute a job with retry policy.

        Args:
            job_config: JobConfig for the job
            params: Resolved parameters
            retry_policy: Retry configuration
            pipeline_config: Pipeline configuration to pass to job

        Returns:
            JobResult from final attempt
        """
        last_result: JobResult | None = None

        for attempt in range(retry_policy.max_retries + 1):
            delay = retry_policy.get_delay(attempt)
            if delay > 0:
                logger.info(
                    f"Retrying job '{job_config.job_id}' in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{retry_policy.max_retries + 1})"
                )
                await asyncio.sleep(delay)

            try:
                # Instantiate job with config if it accepts it
                job_kwargs = dict(params)
                job_kwargs["config"] = pipeline_config

                job = job_config.job_class(**job_kwargs)

                # Validate
                is_valid, error = job.validate()
                if not is_valid:
                    return JobResult.fail(f"Validation failed: {error}")

                # Execute (wrap in thread for blocking jobs)
                result = await asyncio.to_thread(job.execute)

                if result.success:
                    logger.info(f"Job '{job_config.job_id}' succeeded: {result.message}")
                    return result

                last_result = result
                logger.warning(f"Job '{job_config.job_id}' failed: {result.error}")

            except Exception as e:
                logger.exception(f"Job '{job_config.job_id}' raised exception: {e}")
                last_result = JobResult.fail(str(e))

        return last_result or JobResult.fail("Unknown error")

    def _prepare_params(
        self,
        params: dict[str, Any],
        execution_id: str,
    ) -> dict[str, Any]:
        """Prepare parameters for ABSURD task.

        Marks ${job.output} references as deferred for resolution
        by the worker when dependencies complete.

        Args:
            params: Original parameters
            execution_id: Execution ID for lookups

        Returns:
            Prepared parameters
        """
        prepared = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${"):
                # Mark as deferred resolution
                prepared[key] = {
                    "_deferred": True,
                    "_expression": value,
                    "_execution_id": execution_id,
                }
            else:
                prepared[key] = value
        return prepared

    def _resolve_params(
        self,
        params: dict[str, Any],
        results: dict[str, JobResult],
    ) -> dict[str, Any]:
        """Resolve parameter references using completed job results.

        Args:
            params: Parameters with potential ${job.output} references
            results: Completed job results

        Returns:
            Resolved parameters
        """
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Parse reference: ${job_id.output_key}
                ref = value[2:-1]
                if "." in ref:
                    job_id, output_key = ref.split(".", 1)
                    if job_id in results and results[job_id].success:
                        resolved[key] = results[job_id].outputs.get(output_key)
                    else:
                        raise ValueError(
                            f"Cannot resolve '{value}': job '{job_id}' not completed"
                        )
                else:
                    raise ValueError(f"Invalid reference format: '{value}'")
            elif isinstance(value, dict) and value.get("_deferred"):
                # Resolve deferred value
                expr = value["_expression"]
                return self._resolve_params({key: expr}, results)
            else:
                resolved[key] = value
        return resolved

    def _send_notification(
        self,
        pipeline: Pipeline,
        job_id: str,
        event: str,
        error: str | None,
    ) -> None:
        """Send notification for job event.

        Args:
            pipeline: The pipeline
            job_id: Job ID that triggered the event
            event: Event type (failure, success)
            error: Error message if failure
        """
        for notification in pipeline.notifications:
            if notification.job_id != job_id:
                continue

            if event == "failure" and not notification.on_failure:
                continue
            if event == "success" and not notification.on_success:
                continue

            logger.info(
                f"[Notification:{event}] Job '{job_id}' {event} "
                f"(channels={notification.channels}, "
                f"recipients={notification.recipients})"
            )

            # TODO: Integrate with monitoring/alerting system
            # For now, just log

    async def get_status(self, execution_id: str) -> ExecutionStatus:
        """Get pipeline execution status.

        Args:
            execution_id: Execution ID to query

        Returns:
            ExecutionStatus with job details
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        # Get execution record
        cursor = conn.execute(
            "SELECT * FROM pipeline_executions WHERE execution_id = ?",
            (execution_id,),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise ValueError(f"Execution {execution_id} not found")

        # Get job records
        cursor = conn.execute(
            """
            SELECT * FROM pipeline_jobs
            WHERE execution_id = ?
            ORDER BY created_at
            """,
            (execution_id,),
        )
        jobs = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return ExecutionStatus(
            execution_id=row["execution_id"],
            pipeline_name=row["pipeline_name"],
            status=row["status"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            error=row["error"],
            jobs=jobs,
        )

    async def list_executions(
        self,
        pipeline_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ExecutionStatus]:
        """List pipeline executions.

        Args:
            pipeline_name: Filter by pipeline name
            status: Filter by status
            limit: Maximum results

        Returns:
            List of ExecutionStatus
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM pipeline_executions WHERE 1=1"
        params: list[Any] = []

        if pipeline_name:
            query += " AND pipeline_name = ?"
            params.append(pipeline_name)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            ExecutionStatus(
                execution_id=row["execution_id"],
                pipeline_name=row["pipeline_name"],
                status=row["status"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                error=row["error"],
            )
            for row in rows
        ]
