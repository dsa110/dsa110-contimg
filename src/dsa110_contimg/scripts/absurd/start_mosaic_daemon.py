#!/usr/bin/env python
"""
Absurd-enabled Streaming Mosaic Runner.

This script runs the AbsurdStreamingMosaicManager in daemon mode,
processing groups via the Absurd task queue.
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Ensure PYTHONPATH is set for imports
sys.path.insert(0, "/data/dsa110-contimg/src/dsa110_contimg/src")

# Import after path setup (module level import not at top of file)
from dsa110_contimg.mosaic.absurd_manager import (  # noqa: E402
    AbsurdStreamingMosaicManager,
)

logger = logging.getLogger(__name__)


class MosaicDaemon:
    """Daemon wrapper for AbsurdStreamingMosaicManager."""

    def __init__(
        self,
        products_db: Path,
        registry_db: Path,
        ms_dir: Path,
        images_dir: Path,
        mosaic_dir: Path,
        use_sliding_window: bool = True,
        sleep_interval: float = 60.0,
    ):
        self.products_db = products_db
        self.registry_db = registry_db
        self.ms_dir = ms_dir
        self.images_dir = images_dir
        self.mosaic_dir = mosaic_dir
        self.use_sliding_window = use_sliding_window
        self.sleep_interval = sleep_interval
        self.running = False
        self.manager = None

    async def start(self):
        """Start the daemon."""
        logger.info("Starting Absurd Mosaic Daemon")
        logger.info(f"  Products DB: {self.products_db}")
        logger.info(f"  Registry DB: {self.registry_db}")
        logger.info(f"  MS Dir: {self.ms_dir}")
        logger.info(f"  Images Dir: {self.images_dir}")
        logger.info(f"  Mosaic Dir: {self.mosaic_dir}")
        logger.info(f"  Sliding Window: {self.use_sliding_window}")
        logger.info(f"  Sleep Interval: {self.sleep_interval}s")

        # Initialize manager
        self.manager = AbsurdStreamingMosaicManager(
            products_db_path=self.products_db,
            registry_db_path=self.registry_db,
            ms_output_dir=self.ms_dir,
            images_dir=self.images_dir,
            mosaic_output_dir=self.mosaic_dir,
        )

        await self.manager.ensure_connected()
        logger.info("Connected to Absurd database")

        self.running = True

        # Main processing loop
        while self.running:
            try:
                logger.info("Checking for next group...")
                processed = await self.manager.process_next_group_async(
                    use_sliding_window=self.use_sliding_window
                )

                if processed:
                    logger.info("Group processed successfully")
                else:
                    logger.info(f"No group ready, sleeping {self.sleep_interval}s")
                    await asyncio.sleep(self.sleep_interval)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                logger.info(f"Sleeping {self.sleep_interval}s before retry")
                await asyncio.sleep(self.sleep_interval)

        await self.stop()

    async def stop(self):
        """Stop the daemon."""
        logger.info("Stopping Absurd Mosaic Daemon")
        self.running = False
        if self.manager:
            await self.manager.close()
        logger.info("Daemon stopped")

    def handle_signal(self, sig):
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig}, initiating shutdown...")
        self.running = False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Absurd-enabled Streaming Mosaic Daemon")
    parser.add_argument(
        "--products-db",
        type=Path,
        default=Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")),
        help="Path to products database",
    )
    parser.add_argument(
        "--registry-db",
        type=Path,
        default=Path(os.getenv("CAL_REGISTRY_DB", "state/cal_registry.sqlite3")),
        help="Path to calibration registry database",
    )
    parser.add_argument(
        "--ms-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/raw/ms")),
        help="Directory containing MS files",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_IMAGES_DIR", "/stage/dsa110-contimg/images")),
        help="Directory for individual image outputs",
    )
    parser.add_argument(
        "--mosaic-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_MOSAIC_DIR", "/stage/dsa110-contimg/mosaics")),
        help="Directory for mosaic output",
    )
    parser.add_argument(
        "--no-sliding-window",
        action="store_true",
        help="Disable sliding window (use simple 10 MS groups)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=60.0,
        help="Sleep time between checks in loop mode (seconds)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create daemon
    daemon = MosaicDaemon(
        products_db=args.products_db,
        registry_db=args.registry_db,
        ms_dir=args.ms_dir,
        images_dir=args.images_dir,
        mosaic_dir=args.mosaic_dir,
        use_sliding_window=not args.no_sliding_window,
        sleep_interval=args.sleep,
    )

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: daemon.handle_signal(s))

    # Start daemon
    try:
        await daemon.start()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
