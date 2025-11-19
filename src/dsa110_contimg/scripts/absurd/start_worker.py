#!/usr/bin/env python
"""Start Absurd worker for DSA-110 pipeline.

This script starts an Absurd worker that processes tasks from the queue
and executes pipeline stages.
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path

# Ensure we can import the package
# We assume PYTHONPATH is set correctly by systemd, but for safety:
# If we are in scripts/absurd/, we need to add ../../src/dsa110_contimg/src to path?
# No, let's rely on PYTHONPATH being correct or adding the nested src.

# Add the nested src path if dsa110_contimg cannot be imported
try:
    import dsa110_contimg
except ImportError:
    # Fallback: try to find the nested src directory
    # Assuming this script is in scripts/absurd/ relative to CWD
    # And CWD is /data/dsa110-contimg/src/dsa110_contimg
    # The code is in src/dsa110_contimg/src
    
    # We can try to locate it relative to this file
    current_file = Path(__file__).resolve()
    # /data/.../scripts/absurd/start_worker.py
    root = current_file.parent.parent.parent # /data/.../src/dsa110_contimg
    nested_src = root / "src" 
    if nested_src.exists():
        sys.path.insert(0, str(nested_src))

import dsa110_contimg
from dsa110_contimg.absurd.config import AbsurdConfig
from dsa110_contimg.absurd.worker import AbsurdWorker
from dsa110_contimg.absurd.adapter import execute_pipeline_task
from dsa110_contimg.absurd.client import AbsurdClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("dsa110_absurd_worker")

async def main():
    """Main entry point."""
    # Load configuration
    config = AbsurdConfig()
    
    # Override with environment variables if needed (already handled by pydantic/config)
    # Ensure we have a worker ID
    worker_id = f"worker-{os.uname().nodename}-{os.getpid()}"
    logger.info(f"Starting Absurd Worker: {worker_id}")
    logger.info(f"Connecting to DB: {config.database_url}")
    logger.info(f"Queue: {config.queue_name}")

    # Create client
    client = AbsurdClient(config)
    await client.connect()

    # Create worker
    worker = AbsurdWorker(
        client=client,
        queue_name=config.queue_name,
        executor_func=execute_pipeline_task,
        worker_id=worker_id,
        poll_interval=config.poll_interval
    )

    # Handle shutdown signals
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Run worker
    try:
        await worker.start()
        logger.info("Worker started, waiting for tasks...")
        await stop_event.wait()
    finally:
        logger.info("Shutting down worker...")
        await worker.stop()
        await client.close()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())

