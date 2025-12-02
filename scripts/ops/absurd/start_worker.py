#!/usr/bin/env python
"""Start Absurd worker for DSA-110 pipeline.

This script starts an Absurd worker that processes tasks from the queue
and executes pipeline stages.
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# DEBUG: Print sys.path and environment
print(f"DEBUG: sys.path: {sys.path}")
print(f"DEBUG: PYTHONPATH: {os.environ.get('PYTHONPATH')}")

# Ensure backend/src is in path
REPO_ROOT = Path(__file__).resolve().parents[3]
src_path = str(REPO_ROOT / "backend" / "src")
if src_path not in sys.path:
    print(f"DEBUG: Adding {src_path} to sys.path")
    sys.path.insert(0, src_path)

try:
    import dsa110_contimg

    print(f"DEBUG: dsa110_contimg location: {dsa110_contimg.__file__}")
    # Try to import pipeline to verify it's accessible
    import dsa110_contimg.pipeline

    print(f"DEBUG: dsa110_contimg.pipeline location: {dsa110_contimg.pipeline.__file__}")
except ImportError as e:
    print(f"DEBUG: Import failed: {e}")
    # Traceback might help
    import traceback

    traceback.print_exc()

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
