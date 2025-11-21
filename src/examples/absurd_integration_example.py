#!/usr/bin/env python3
"""
Example: Integrating Absurd with DSA-110 Pipeline

This example demonstrates Strategy 1: Wrapping pipeline stages as Absurd tasks.
It shows how to:
1. Set up Absurd connection
2. Register pipeline tasks
3. Execute pipeline with checkpointing
4. Handle errors and retries

Prerequisites:
- PostgreSQL database with Absurd schema installed
- Absurd queue created: `dsa110-pipeline`
- Python packages: asyncpg, psycopg2 (or asyncpg for async)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# For this example, we'll use asyncpg for async PostgreSQL access
# In production, you might want to create a proper Python SDK wrapper
try:
    import asyncpg
except ImportError:
    print("ERROR: asyncpg not installed. Install with: pip install asyncpg")
    raise

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

logger = logging.getLogger(__name__)


class AbsurdClient:
    """Simple Absurd client using direct PostgreSQL calls.

    This is a minimal implementation. In production, you'd want a proper SDK.
    """

    def __init__(self, database_url: str):
        """Initialize Absurd client.

        Args:
            database_url: PostgreSQL connection string
                Example: "postgresql://user:pass@localhost/dbname"
        """
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(self.database_url)
        logger.info("Connected to Absurd database")

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

    async def spawn_task(
        self,
        queue_name: str,
        task_name: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Spawn a new task in Absurd queue.

        Args:
            queue_name: Name of the queue
            task_name: Name of the task
            params: Task parameters (will be JSON serialized)
            headers: Optional task headers

        Returns:
            Task ID (UUID as string)
        """
        async with self.pool.acquire() as conn:
            task_id = await conn.fetchval(
                "SELECT absurd.spawn_task($1, $2, $3::jsonb, $4::jsonb)",
                queue_name,
                task_name,
                json.dumps(params),
                json.dumps(headers or {}),
            )
            logger.info(f"Spawned task {task_id} in queue {queue_name}")
            return str(task_id)

    async def claim_task(
        self, queue_name: str, worker_id: str, lease_duration_seconds: int = 300
    ) -> Optional[Dict[str, Any]]:
        """Claim a task from the queue.

        Args:
            queue_name: Name of the queue
            worker_id: Unique identifier for this worker
            lease_duration_seconds: How long to lease the task

        Returns:
            Task data dict or None if no tasks available
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM absurd.claim_task($1, $2, $3)",
                queue_name,
                worker_id,
                lease_duration_seconds,
            )
            if row:
                return dict(row)
            return None

    async def complete_run(self, queue_name: str, run_id: str, result: Dict[str, Any]):
        """Mark a run as completed.

        Args:
            queue_name: Name of the queue
            run_id: Run ID
            result: Result data (will be JSON serialized)
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "SELECT absurd.complete_run($1, $2, $3::jsonb)",
                queue_name,
                run_id,
                json.dumps(result),
            )
            logger.info(f"Completed run {run_id}")

    async def fail_run(self, queue_name: str, run_id: str, reason: str, retry: bool = True):
        """Mark a run as failed.

        Args:
            queue_name: Name of the queue
            run_id: Run ID
            reason: Failure reason
            retry: Whether to schedule a retry
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "SELECT absurd.fail_run($1, $2, $3, $4)",
                queue_name,
                run_id,
                reason,
                retry,
            )
            logger.warning(f"Failed run {run_id}: {reason}")

    async def set_checkpoint(
        self, queue_name: str, task_id: str, checkpoint_name: str, state: Dict[str, Any]
    ):
        """Set a checkpoint for a task.

        Args:
            queue_name: Name of the queue
            task_id: Task ID
            checkpoint_name: Name of the checkpoint
            state: State data (will be JSON serialized)
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "SELECT absurd.set_task_checkpoint_state($1, $2, $3, $4::jsonb)",
                queue_name,
                task_id,
                checkpoint_name,
                json.dumps(state),
            )

    async def get_checkpoint(
        self, queue_name: str, task_id: str, checkpoint_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get a checkpoint for a task.

        Args:
            queue_name: Name of the queue
            task_id: Task ID
            checkpoint_name: Name of the checkpoint

        Returns:
            Checkpoint state dict or None if not found
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT state FROM absurd.get_task_checkpoint_state($1, $2, $3)",
                queue_name,
                task_id,
                checkpoint_name,
            )
            if row and row["state"]:
                return json.loads(row["state"])
            return None


class AbsurdPipelineAdapter:
    """Adapter to run DSA-110 pipeline stages as Absurd tasks."""

    def __init__(self, config: PipelineConfig, absurd_client: AbsurdClient):
        """Initialize adapter.

        Args:
            config: Pipeline configuration
            absurd_client: Absurd client instance
        """
        self.config = config
        self.absurd = absurd_client
        self.queue_name = "dsa110-pipeline"

    async def execute_pipeline_task(self, task_data: Dict[str, Any]):
        """Execute pipeline as Absurd task with checkpointed steps.

        This function is called by the worker when it claims a task.

        Args:
            task_data: Task data from Absurd (includes task_id, run_id, params, etc.)
        """
        task_id = task_data["task_id"]
        run_id = task_data["run_id"]
        params = json.loads(task_data["params"])

        logger.info(f"Executing pipeline task {task_id}, run {run_id}")

        try:
            # Step 1: Setup (checkpointed)
            setup_result = await self._execute_step(
                task_id, run_id, "setup", lambda: self._setup_pipeline(params)
            )

            # Step 2: Catalog setup (checkpointed)
            catalog_result = await self._execute_step(
                task_id,
                run_id,
                "catalog_setup",
                lambda: self._execute_stage("catalog_setup", setup_result["context"]),
            )

            # Step 3: Conversion (checkpointed)
            conversion_result = await self._execute_step(
                task_id,
                run_id,
                "convert",
                lambda: self._execute_stage("convert", catalog_result["context"]),
            )

            # Step 4: Calibration solve (checkpointed)
            cal_solve_result = await self._execute_step(
                task_id,
                run_id,
                "calibrate_solve",
                lambda: self._execute_stage("calibrate_solve", conversion_result["context"]),
            )

            # Step 5: Calibration apply (checkpointed)
            cal_apply_result = await self._execute_step(
                task_id,
                run_id,
                "calibrate_apply",
                lambda: self._execute_stage("calibrate_apply", cal_solve_result["context"]),
            )

            # Step 6: Imaging (checkpointed)
            imaging_result = await self._execute_step(
                task_id,
                run_id,
                "image",
                lambda: self._execute_stage("image", cal_apply_result["context"]),
            )

            # Step 7: Validation (checkpointed, optional)
            final_result = imaging_result
            if self.config.validation.enabled:
                validation_result = await self._execute_step(
                    task_id,
                    run_id,
                    "validate",
                    lambda: self._execute_stage("validate", imaging_result["context"]),
                )
                final_result = validation_result

            # Mark task as completed
            await self.absurd.complete_run(
                self.queue_name,
                run_id,
                {
                    "status": "completed",
                    "outputs": final_result["context"].outputs,
                    "completed_at": datetime.now().isoformat(),
                },
            )

            logger.info(f"Pipeline task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Pipeline task {task_id} failed: {e}", exc_info=True)

            # Determine if we should retry
            should_retry = self._should_retry(e)

            await self.absurd.fail_run(self.queue_name, run_id, str(e), retry=should_retry)

            raise

    async def _execute_step(
        self, task_id: str, run_id: str, step_name: str, step_func
    ) -> Dict[str, Any]:
        """Execute a step with checkpointing.

        Args:
            task_id: Task ID
            run_id: Run ID
            step_name: Name of the step
            step_func: Function to execute for this step

        Returns:
            Step result
        """
        # Check if checkpoint exists (resume from checkpoint)
        checkpoint = await self.absurd.get_checkpoint(self.queue_name, task_id, step_name)

        if checkpoint:
            logger.info(f"Resuming from checkpoint: {step_name}")
            return checkpoint

        # Execute step
        logger.info(f"Executing step: {step_name}")
        result = step_func()

        # Save checkpoint
        await self.absurd.set_checkpoint(
            self.queue_name,
            task_id,
            step_name,
            {
                "context": self._serialize_context(result["context"]),
                "status": (
                    result["status"].value
                    if hasattr(result["status"], "value")
                    else str(result["status"])
                ),
                "timestamp": datetime.now().isoformat(),
            },
        )

        return result

    def _setup_pipeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize pipeline orchestrator."""
        standard_imaging_workflow(self.config)
        initial_context = PipelineContext(config=self.config, inputs=params)
        return {"context": initial_context, "status": "pending"}

    def _execute_stage(self, stage_name: str, context: PipelineContext) -> Dict[str, Any]:
        """Execute a single pipeline stage."""
        orchestrator = standard_imaging_workflow(self.config)
        stage_def = orchestrator.stages[stage_name]

        # Execute stage (this would use the actual orchestrator logic)
        # For this example, we'll simulate it
        result_context = orchestrator._execute_stage(stage_def, context)

        return {"context": result_context.context, "status": result_context.status}

    def _serialize_context(self, context: PipelineContext) -> Dict[str, Any]:
        """Serialize pipeline context for checkpointing."""
        return {
            "inputs": context.inputs,
            "outputs": context.outputs,
            "metadata": context.metadata or {},
        }

    def _should_retry(self, error: Exception) -> bool:
        """Determine if error should trigger retry."""
        # Transient errors: retry
        if isinstance(error, (TimeoutError, ConnectionError, OSError)):
            return True

        # Data errors: don't retry
        if isinstance(error, (ValueError, KeyError, FileNotFoundError)):
            return False

        # CASA errors: check error message
        error_str = str(error).lower()
        if "casa" in error_str:
            if "timeout" in error_str:
                return True
            if "disk full" in error_str:
                return False

        # Default: retry once
        return True


class AbsurdWorker:
    """Worker that pulls tasks from Absurd queue and executes them."""

    def __init__(
        self,
        absurd_client: AbsurdClient,
        adapter: AbsurdPipelineAdapter,
        worker_id: str = None,
    ):
        """Initialize worker.

        Args:
            absurd_client: Absurd client instance
            adapter: Pipeline adapter instance
            worker_id: Unique worker identifier (defaults to hostname)
        """
        self.absurd = absurd_client
        self.adapter = adapter
        self.worker_id = worker_id or f"worker-{Path(__file__).stem}"
        self.running = False

    async def start(self, poll_interval: float = 5.0):
        """Start worker loop.

        Args:
            poll_interval: Seconds to wait between polling for tasks
        """
        self.running = True
        logger.info(f"Worker {self.worker_id} started")

        while self.running:
            try:
                # Claim a task
                task = await self.absurd.claim_task(
                    self.adapter.queue_name, self.worker_id, lease_duration_seconds=300
                )

                if task:
                    logger.info(f"Claimed task {task['task_id']}")
                    try:
                        await self.adapter.execute_pipeline_task(task)
                    except Exception as e:
                        logger.error(f"Error executing task: {e}", exc_info=True)
                else:
                    # No tasks available, wait before polling again
                    await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)

    def stop(self):
        """Stop worker loop."""
        self.running = False
        logger.info(f"Worker {self.worker_id} stopped")


async def main():
    """Example usage."""
    import os

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Database URL (from environment or default)
    database_url = os.getenv(
        "ABSURD_DATABASE_URL", "postgresql://user:password@localhost/dsa110_absurd"
    )

    # Initialize Absurd client
    absurd_client = AbsurdClient(database_url)
    await absurd_client.connect()

    try:
        # Create pipeline config (from environment or defaults)
        config = PipelineConfig.from_env()

        # Create adapter
        adapter = AbsurdPipelineAdapter(config, absurd_client)

        # Example: Spawn a pipeline task
        task_id = await absurd_client.spawn_task(
            adapter.queue_name,
            "dsa110-pipeline",
            {
                "input_path": "/data/incoming/observation.hdf5",
                "calibrator": "0834+555",
                "output_dir": "/stage/dsa110-contimg/mosaics",
            },
        )

        print(f"Spawned task: {task_id}")

        # Start worker (in production, this would run in a separate process)
        worker = AbsurdWorker(absurd_client, adapter)

        # Run worker for a short time (for demo)
        # In production, you'd run this indefinitely
        await asyncio.wait_for(worker.start(poll_interval=2.0), timeout=30.0)

    finally:
        await absurd_client.close()


if __name__ == "__main__":
    asyncio.run(main())
