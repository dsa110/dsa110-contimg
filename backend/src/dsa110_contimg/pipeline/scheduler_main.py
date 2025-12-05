#!/usr/bin/env python3
"""
Pipeline Scheduler entry point.

Run with: python -m dsa110_contimg.pipeline.scheduler_main

This module starts the pipeline scheduler daemon that monitors cron-scheduled
pipelines (like NightlyMosaicPipeline) and triggers them when their schedules
fire. The actual job execution happens via ABSURD workers.

Architecture:
    1. Pipeline scheduler monitors cron schedules
    2. When a schedule fires, it creates a Pipeline instance
    3. Pipeline is executed via PipelineExecutor
    4. Jobs are spawned as ABSURD tasks
    5. ABSURD workers execute the actual job logic
"""

import asyncio
import logging
import signal
import sys

from dsa110_contimg.config import settings

# Import pipeline classes to register them
from dsa110_contimg.mosaic.pipeline import NightlyMosaicPipeline
from dsa110_contimg.pipeline.scheduler import PipelineScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pipeline.scheduler")


async def main() -> int:
    """Main entry point for the pipeline scheduler."""
    logger.info("=" * 60)
    logger.info("Pipeline Scheduler Starting")
    logger.info("=" * 60)
    logger.info(f"Database: {settings.paths.pipeline_db}")
    logger.info("=" * 60)

    # Create scheduler
    scheduler = PipelineScheduler(
        db_path=settings.paths.pipeline_db,
        config=settings,
    )

    # Register scheduled pipelines
    try:
        scheduler.register(NightlyMosaicPipeline)
        logger.info(
            f"Registered: NightlyMosaicPipeline (schedule: {NightlyMosaicPipeline.schedule})"
        )
    except ValueError as e:
        logger.warning(f"Skipping NightlyMosaicPipeline: {e}")

    # Note: CalibrationPipeline is typically on-demand, not scheduled
    # Add more scheduled pipelines here as needed

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        scheduler.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Run scheduler
    try:
        await scheduler.start()
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        return 1

    logger.info("Pipeline scheduler stopped")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
