#!/opt/miniforge/envs/casa6/bin/python
"""
Absurd worker runner script.

Starts a worker process that claims and executes tasks from the Absurd queue.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig, AbsurdWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("absurd_worker.log"),
    ],
)

logger = logging.getLogger(__name__)


class WorkerRunner:
    """Runner for Absurd worker with graceful shutdown."""

    def __init__(self, config: AbsurdConfig, worker_id: str = "worker"):
        self.config = config
        self.worker_id = worker_id
        self.client: Optional[AbsurdClient] = None
        self.worker: Optional[AbsurdWorker] = None
        self.shutdown_event = asyncio.Event()

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""

        def handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

    async def shutdown(self):
        """Perform graceful shutdown."""
        logger.info("Shutting down worker...")
        self.shutdown_event.set()

        if self.worker:
            await self.worker.stop()

        if self.client:
            await self.client.close()

        logger.info("Shutdown complete")

    async def run(self):
        """Run worker until shutdown signal."""
        try:
            # Initialize client
            logger.info(f"Connecting to database: {self.config.database_url}")
            self.client = AbsurdClient(
                self.config.database_url,
                pool_min_size=2,
                pool_max_size=self.config.worker_concurrency + 2,
            )
            await self.client.connect()
            logger.info("Database connection established")

            # Create worker
            self.worker = AbsurdWorker(self.client, self.config, worker_id=self.worker_id)

            # Start worker
            logger.info(f"Starting worker '{self.worker_id}' on queue '{self.config.queue_name}'")
            logger.info(f"Concurrency: {self.config.worker_concurrency}")
            logger.info(f"Poll interval: {self.config.worker_poll_interval}s")

            # Run worker until shutdown
            worker_task = asyncio.create_task(self.worker.start())
            shutdown_task = asyncio.create_task(self.shutdown_event.wait())

            # Wait for either worker completion or shutdown signal
            done, pending = await asyncio.wait(
                [worker_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # If worker task completed, check for errors
            if worker_task in done:
                try:
                    await worker_task
                except Exception as e:
                    logger.error(f"Worker failed: {e}", exc_info=True)
                    raise

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise

        finally:
            await self.shutdown()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Absurd worker")

    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "ABSURD_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/absurd"
        ),
        help="PostgreSQL connection URL",
    )

    parser.add_argument(
        "--queue-name",
        default=os.getenv("ABSURD_QUEUE_NAME", "dsa110-pipeline"),
        help="Queue name to process",
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.getenv("ABSURD_WORKER_CONCURRENCY", "4")),
        help="Number of concurrent tasks",
    )

    parser.add_argument(
        "--poll-interval",
        type=float,
        default=float(os.getenv("ABSURD_WORKER_POLL_INTERVAL", "1.0")),
        help="Poll interval in seconds",
    )

    parser.add_argument(
        "--task-timeout",
        type=int,
        default=int(os.getenv("ABSURD_TASK_TIMEOUT", "3600")),
        help="Task timeout in seconds",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=int(os.getenv("ABSURD_MAX_RETRIES", "3")),
        help="Maximum retry attempts",
    )

    parser.add_argument(
        "--worker-id",
        default=os.getenv("ABSURD_WORKER_ID", f"worker-{os.getpid()}"),
        help="Unique worker identifier",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create config
    config = AbsurdConfig(
        enabled=True,
        database_url=args.database_url,
        queue_name=args.queue_name,
        worker_concurrency=args.concurrency,
        worker_poll_interval=args.poll_interval,
        task_timeout=args.task_timeout,
        max_retries=args.max_retries,
    )

    # Print configuration
    logger.info("=" * 80)
    logger.info("ABSURD WORKER CONFIGURATION")
    logger.info("=" * 80)
    logger.info(f"Worker ID: {args.worker_id}")
    logger.info(f"Queue: {config.queue_name}")
    logger.info(f"Database: {config.database_url}")
    logger.info(f"Concurrency: {config.worker_concurrency}")
    logger.info(f"Poll Interval: {config.worker_poll_interval}s")
    logger.info(f"Task Timeout: {config.task_timeout}s")
    logger.info(f"Max Retries: {config.max_retries}")
    logger.info("=" * 80)

    # Create and run worker
    runner = WorkerRunner(config, worker_id=args.worker_id)
    runner.setup_signal_handlers()

    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
