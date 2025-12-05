"""
Pipeline scheduler: Triggers pipelines based on cron schedules.

This module provides a daemon that monitors pipeline schedules and
triggers executions when due.

Classes:
    PipelineScheduler: Daemon that triggers scheduled pipelines
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Type

from .base import Pipeline
from .executor import PipelineExecutor

logger = logging.getLogger(__name__)


class PipelineScheduler:
    """Daemon that monitors schedules and triggers pipelines.

    The scheduler:
    1. Registers pipeline classes with cron schedules
    2. Tracks next execution time for each pipeline
    3. Triggers execution when due
    4. Handles failures gracefully

    Example:
        scheduler = PipelineScheduler(
            db_path=Path("pipeline.sqlite3"),
            config=settings,
        )
        scheduler.register(NightlyMosaicPipeline)
        scheduler.register(HousekeepingPipeline)

        # Run forever
        await scheduler.start()

        # Or run once (for testing)
        await scheduler.run_once()
    """

    def __init__(self, db_path: Path, config: Any = None):
        """Initialize scheduler.

        Args:
            db_path: Path to the pipeline database
            config: Application configuration to pass to pipelines
        """
        self.db_path = db_path
        self.config = config
        self.executor = PipelineExecutor(db_path)
        self.pipelines: dict[str, Type[Pipeline]] = {}
        self._running = False
        self._check_interval = 60  # seconds

    def register(self, pipeline_class: Type[Pipeline]) -> None:
        """Register a pipeline for scheduling.

        Args:
            pipeline_class: Pipeline class with schedule attribute

        Raises:
            ValueError: If pipeline has no schedule defined
        """
        if not pipeline_class.schedule:
            raise ValueError(
                f"{pipeline_class.__name__} has no schedule defined. "
                f"Set class attribute schedule = '0 3 * * *' (cron syntax)"
            )

        name = pipeline_class.pipeline_name
        self.pipelines[name] = pipeline_class
        logger.info(f"Registered pipeline '{name}' with schedule: {pipeline_class.schedule}")

    def unregister(self, pipeline_name: str) -> None:
        """Unregister a pipeline.

        Args:
            pipeline_name: Name of pipeline to remove
        """
        if pipeline_name in self.pipelines:
            del self.pipelines[pipeline_name]
            logger.info(f"Unregistered pipeline '{pipeline_name}'")

    async def start(self) -> None:
        """Start the scheduler (blocking).

        Runs forever, checking schedules every minute.
        """
        self._running = True
        logger.info("Pipeline scheduler started")

        # Track next execution time for each pipeline
        next_run = self._compute_next_runs()

        try:
            while self._running:
                now = datetime.now()

                # Check if any pipelines are due
                for name, pipeline_class in self.pipelines.items():
                    if name in next_run and now >= next_run[name]:
                        await self._trigger_pipeline(name, pipeline_class)

                        # Compute next run
                        next_run[name] = self._get_next_run(pipeline_class.schedule)
                        logger.info(f"Next {name} at {next_run[name]}")

                # Sleep until next check
                await asyncio.sleep(self._check_interval)

        except asyncio.CancelledError:
            logger.info("Pipeline scheduler cancelled")
        finally:
            self._running = False
            logger.info("Pipeline scheduler stopped")

    async def run_once(self) -> dict[str, str]:
        """Check schedules once and trigger due pipelines.

        Returns:
            Dict of pipeline_name -> execution_id for triggered pipelines
        """
        next_run = self._compute_next_runs()
        now = datetime.now()
        triggered = {}

        for name, pipeline_class in self.pipelines.items():
            if name in next_run and now >= next_run[name]:
                execution_id = await self._trigger_pipeline(name, pipeline_class)
                if execution_id:
                    triggered[name] = execution_id

        return triggered

    async def trigger(self, pipeline_name: str) -> str:
        """Manually trigger a pipeline.

        Args:
            pipeline_name: Name of pipeline to trigger

        Returns:
            execution_id

        Raises:
            ValueError: If pipeline not registered
        """
        if pipeline_name not in self.pipelines:
            raise ValueError(f"Pipeline '{pipeline_name}' not registered")

        pipeline_class = self.pipelines[pipeline_name]
        execution_id = await self._trigger_pipeline(pipeline_name, pipeline_class)
        if not execution_id:
            raise RuntimeError(f"Failed to trigger {pipeline_name}")
        return execution_id

    async def _trigger_pipeline(
        self,
        name: str,
        pipeline_class: Type[Pipeline],
    ) -> str | None:
        """Trigger a pipeline execution.

        Args:
            name: Pipeline name
            pipeline_class: Pipeline class to instantiate

        Returns:
            execution_id or None if failed
        """
        logger.info(f"Triggering pipeline '{name}' at {datetime.now()}")

        try:
            # Instantiate pipeline with config
            pipeline = pipeline_class(self.config)
            execution_id = await self.executor.execute(pipeline)
            logger.info(f"Started {name}: {execution_id}")
            return execution_id

        except Exception as e:
            logger.exception(f"Failed to trigger pipeline '{name}': {e}")
            return None

    def _compute_next_runs(self) -> dict[str, datetime]:
        """Compute next run time for all registered pipelines.

        Returns:
            Dict of pipeline_name -> next_run_datetime
        """
        next_run = {}
        for name, pipeline_class in self.pipelines.items():
            next_run[name] = self._get_next_run(pipeline_class.schedule)
        return next_run

    def _get_next_run(self, schedule: str) -> datetime:
        """Get next run time for a cron schedule.

        Args:
            schedule: Cron expression (e.g., "0 3 * * *")

        Returns:
            Next datetime when schedule triggers
        """
        try:
            from croniter import croniter

            cron = croniter(schedule, datetime.now())
            return cron.get_next(datetime)
        except ImportError:
            # Fallback: just return now + 24 hours if croniter not available
            logger.warning(
                "croniter not installed, using fallback scheduling. "
                "Install with: pip install croniter"
            )
            from datetime import timedelta

            return datetime.now() + timedelta(hours=24)

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        logger.info("Pipeline scheduler stopping...")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    def list_pipelines(self) -> list[dict[str, Any]]:
        """List registered pipelines with their schedules.

        Returns:
            List of pipeline info dicts
        """
        result = []
        next_runs = self._compute_next_runs()

        for name, pipeline_class in self.pipelines.items():
            result.append(
                {
                    "name": name,
                    "class": pipeline_class.__name__,
                    "schedule": pipeline_class.schedule,
                    "next_run": next_runs.get(name),
                }
            )

        return result


# =============================================================================
# Main Entry Point
# =============================================================================


async def run_scheduler(
    db_path: Path,
    config: Any = None,
    pipelines: list[Type[Pipeline]] | None = None,
) -> None:
    """Run the pipeline scheduler.

    Convenience function to start the scheduler with registered pipelines.

    Args:
        db_path: Path to the pipeline database
        config: Application configuration
        pipelines: Pipeline classes to register
    """
    scheduler = PipelineScheduler(db_path, config)

    for pipeline_class in pipelines or []:
        scheduler.register(pipeline_class)

    await scheduler.start()
