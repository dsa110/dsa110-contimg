#!/usr/bin/env python3
"""
ABSURD Scheduler entry point.

Run with: python -m dsa110_contimg.absurd.scheduler

This module starts a scheduler daemon that monitors cron-scheduled tasks
and spawns actual queue tasks when their schedules trigger.
"""

import asyncio
import logging
import signal
import sys

import asyncpg

from dsa110_contimg.absurd.config import AbsurdConfig
from dsa110_contimg.absurd.scheduling import TaskScheduler, ensure_scheduled_tasks_table

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("absurd.scheduler")


async def main() -> int:
    """Main entry point for the ABSURD scheduler."""
    # Load configuration from environment
    config = AbsurdConfig.from_env()

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    if not config.enabled:
        logger.error("ABSURD is not enabled. Set ABSURD_ENABLED=true to start scheduler.")
        return 1

    logger.info("=" * 60)
    logger.info("ABSURD Scheduler Starting")
    logger.info("=" * 60)
    logger.info(f"Database: {config.database_url.split('@')[1] if '@' in config.database_url else config.database_url}")
    logger.info(f"Queue: {config.queue_name}")
    logger.info("=" * 60)

    # Create connection pool
    try:
        pool = await asyncpg.create_pool(
            config.database_url,
            min_size=1,
            max_size=3,
            command_timeout=60,
        )
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return 1

    try:
        # Ensure scheduled tasks table exists
        await ensure_scheduled_tasks_table(pool)

        # Create scheduler
        scheduler = TaskScheduler(pool=pool, check_interval=60.0)

        # Set up signal handlers for graceful shutdown
        shutdown_event = asyncio.Event()

        def signal_handler(sig: int, frame) -> None:
            logger.info(f"Received signal {sig}, initiating graceful shutdown...")
            shutdown_event.set()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Start scheduler
        await scheduler.start()
        logger.info("Scheduler running. Press Ctrl+C to stop.")

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Stop scheduler
        logger.info("Stopping scheduler...")
        await scheduler.stop()

    finally:
        # Close connection pool
        await pool.close()
        logger.info("Database connection closed")

    logger.info("Scheduler stopped")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        exit_code = 130
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        exit_code = 1

    sys.exit(exit_code)
