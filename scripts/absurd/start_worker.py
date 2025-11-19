#!/usr/bin/env python
"""Start Absurd worker for DSA-110 pipeline.

This script starts an Absurd worker that processes tasks from the queue
and executes pipeline stages.

Usage:
    python scripts/absurd/start_worker.py

Environment Variables:
    ABSURD_ENABLED: Enable Absurd (default: true)
    ABSURD_DATABASE_URL: PostgreSQL connection URL
    ABSURD_QUEUE_NAME: Queue name (default: dsa110-pipeline)
    ABSURD_WORKER_CONCURRENCY: Worker concurrency (default: 4)
    ABSURD_WORKER_POLL_INTERVAL: Poll interval in seconds (default: 1.0)
    ABSURD_TASK_TIMEOUT: Task timeout in seconds (default: 3600)
    ABSURD_MAX_RETRIES: Maximum retry attempts (default: 3)
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dsa110_contimg.absurd import AbsurdConfig
from dsa110_contimg.absurd.adapter import execute_pipeline_task
from dsa110_contimg.absurd.worker import AbsurdWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("/tmp/absurd_worker.log")],
)
logger = logging.getLogger(__name__)

# Global worker instance for signal handling
worker_instance = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    if worker_instance:
        asyncio.create_task(worker_instance.stop())


async def main():
    """Start the Absurd worker."""
    global worker_instance

    logger.info("=" * 80)
    logger.info("DSA-110 Absurd Worker Starting")
    logger.info("=" * 80)

    # Load configuration from environment
    try:
        config = AbsurdConfig.from_env()
        config.validate()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    logger.info(f"Configuration:")
    logger.info(f"  Database URL: {config.database_url}")
    logger.info(f"  Queue Name: {config.queue_name}")
    logger.info(f"  Concurrency: {config.worker_concurrency}")
    logger.info(f"  Poll Interval: {config.worker_poll_interval_sec}s")
    logger.info(f"  Task Timeout: {config.task_timeout_sec}s")
    logger.info(f"  Max Retries: {config.max_retries}")
    logger.info("=" * 80)

    # Create worker
    worker_instance = AbsurdWorker(config, execute_pipeline_task)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Worker starting... Press Ctrl+C to stop")
        await worker_instance.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.exception(f"Worker error: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down worker...")
        await worker_instance.stop()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
