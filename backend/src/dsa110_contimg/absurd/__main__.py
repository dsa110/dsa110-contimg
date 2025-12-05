#!/usr/bin/env python3
"""
ABSURD Worker entry point.

Run with: python -m dsa110_contimg.absurd.worker

This module starts a worker process that polls the ABSURD queue for pending
tasks and executes them using the pipeline task executor.
"""

import asyncio
import logging
import signal
import sys

from dsa110_contimg.absurd.adapter import execute_pipeline_task
from dsa110_contimg.absurd.config import AbsurdConfig
from dsa110_contimg.absurd.worker import AbsurdWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("absurd.worker")


async def main() -> int:
    """Main entry point for the ABSURD worker."""
    # Load configuration from environment
    config = AbsurdConfig.from_env()

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    if not config.enabled:
        logger.error("ABSURD is not enabled. Set ABSURD_ENABLED=true to start worker.")
        return 1

    logger.info("=" * 60)
    logger.info("ABSURD Worker Starting")
    logger.info("=" * 60)
    logger.info(f"Queue: {config.queue_name}")
    logger.info(f"Concurrency: {config.worker_concurrency}")
    logger.info(f"Poll interval: {config.worker_poll_interval_sec}s")
    logger.info(f"Task timeout: {config.task_timeout_sec}s")
    logger.info(f"Max retries: {config.max_retries}")
    logger.info(f"DLQ enabled: {config.dead_letter_enabled}")
    if config.dead_letter_enabled:
        logger.info(f"DLQ queue: {config.dead_letter_queue_name}")
    logger.info("=" * 60)

    # Create worker with pipeline executor
    worker = AbsurdWorker(config, execute_pipeline_task)

    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    shutdown_requested = False

    def signal_handler(sig: int, frame) -> None:
        nonlocal shutdown_requested
        if shutdown_requested:
            return  # Already shutting down, ignore duplicate signals
        shutdown_requested = True
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start worker
    worker_task = asyncio.create_task(worker.start())

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Stop worker gracefully
    logger.info("Stopping worker...")
    await worker.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=30.0)
    except asyncio.TimeoutError:
        logger.warning("Worker did not stop within timeout, cancelling...")
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    logger.info("Worker stopped")
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
