"""
CLI for the streaming data processing pipeline.

This module provides command-line interface for the streaming converter,
allowing it to be run directly without a systemd service wrapper.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import List, Optional

from dsa110_contimg.conversion.streaming.queue import SubbandQueue
from dsa110_contimg.conversion.streaming.watcher import StreamingWatcher
from dsa110_contimg.conversion.streaming.worker import StreamingWorker, WorkerConfig

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the streaming pipeline.
    
    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("watchdog").setLevel(logging.WARNING)
    logging.getLogger("casatasks").setLevel(logging.WARNING)


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for streaming converter CLI.
    
    Returns:
        Configured ArgumentParser
    """
    p = argparse.ArgumentParser(
        description="DSA-110 streaming data pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # Required paths
    p.add_argument(
        "--input-dir",
        required=True,
        help="Directory to watch for incoming HDF5 files",
    )
    p.add_argument(
        "--output-dir",
        required=True,
        help="Directory for output MS files and images",
    )
    
    # Database paths (unified by default)
    p.add_argument(
        "--queue-db",
        default="state/db/pipeline.sqlite3",
        help="Path to queue/products database",
    )
    p.add_argument(
        "--registry-db",
        default=None,
        help="Path to calibration registry database (defaults to queue-db)",
    )
    
    # Processing directories
    p.add_argument(
        "--scratch-dir",
        default="/stage/dsa110-contimg",
        help="Directory for temporary/scratch files",
    )
    
    # Subband settings
    p.add_argument(
        "--expected-subbands",
        type=int,
        default=16,
        help="Number of subbands per observation",
    )
    p.add_argument(
        "--chunk-duration",
        type=float,
        default=5.0,
        help="Minutes per time chunk for grouping",
    )
    
    # Logging
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    
    # Execution mode
    p.add_argument(
        "--execution-mode",
        choices=["inprocess", "subprocess", "auto"],
        default="auto",
        help="Execution mode for conversion tasks",
    )
    
    # Resource limits
    p.add_argument(
        "--memory-limit-mb",
        type=int,
        default=16000,
        help="Memory limit in MB for conversion tasks",
    )
    p.add_argument(
        "--omp-threads",
        type=int,
        default=4,
        help="OMP_NUM_THREADS for conversion tasks",
    )
    
    # Polling intervals
    p.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds between directory polls (if watchdog unavailable)",
    )
    p.add_argument(
        "--worker-poll-interval",
        type=float,
        default=5.0,
        help="Seconds between queue polls",
    )
    p.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum worker threads",
    )
    
    # Feature flags
    p.add_argument(
        "--enable-calibration-solving",
        action="store_true",
        help="Enable automatic calibration solving for calibrator observations",
    )
    p.add_argument(
        "--enable-group-imaging",
        action="store_true",
        help="Enable group detection and coordinated imaging",
    )
    p.add_argument(
        "--enable-mosaic-creation",
        action="store_true",
        help="Enable automatic mosaic creation for complete groups",
    )
    p.add_argument(
        "--enable-auto-qa",
        action="store_true",
        help="Enable automatic QA validation after mosaic creation",
    )
    p.add_argument(
        "--enable-auto-publish",
        action="store_true",
        help="Enable automatic publishing after QA passes",
    )
    p.add_argument(
        "--enable-photometry",
        action="store_true",
        default=True,
        help="Enable automatic photometry measurement",
    )
    p.add_argument(
        "--no-photometry",
        dest="enable_photometry",
        action="store_false",
        help="Disable automatic photometry measurement",
    )
    
    # Photometry settings
    p.add_argument(
        "--photometry-catalog",
        default="nvss",
        choices=["nvss", "first", "rax", "vlass", "master", "atnf"],
        help="Catalog for source queries",
    )
    p.add_argument(
        "--photometry-radius",
        type=float,
        default=0.5,
        help="Search radius in degrees for source queries",
    )
    
    # Calibration settings
    p.add_argument(
        "--cal-fence-timeout",
        type=float,
        default=60.0,
        help="Seconds to wait for calibration registration propagation",
    )
    p.add_argument(
        "--use-interpolated-cal",
        action="store_true",
        default=True,
        help="Use interpolated calibration between sets",
    )
    p.add_argument(
        "--no-interpolated-cal",
        dest="use_interpolated_cal",
        action="store_false",
        help="Disable calibration interpolation",
    )
    
    # Tmpfs staging
    p.add_argument(
        "--stage-to-tmpfs",
        action="store_true",
        default=True,
        help="Stage intermediate files to tmpfs",
    )
    p.add_argument(
        "--no-stage-to-tmpfs",
        dest="stage_to_tmpfs",
        action="store_false",
        help="Disable tmpfs staging",
    )
    p.add_argument(
        "--tmpfs-path",
        default="/dev/shm",
        help="Path to tmpfs mount",
    )
    
    # Monitoring
    p.add_argument(
        "--monitoring",
        action="store_true",
        help="Enable Prometheus monitoring endpoint",
    )
    p.add_argument(
        "--monitor-interval",
        type=float,
        default=60.0,
        help="Seconds between monitoring reports",
    )
    
    return p


def validate_paths(args: argparse.Namespace) -> bool:
    """Validate input/output paths before starting.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        True if paths are valid, False otherwise
    """
    # Validate input directory
    input_path = Path(args.input_dir)
    if not input_path.exists():
        logger.error(f"Input directory does not exist: {args.input_dir}")
        return False
    if not input_path.is_dir():
        logger.error(f"Input path is not a directory: {args.input_dir}")
        return False
    if not os.access(args.input_dir, os.R_OK):
        logger.error(f"Input directory is not readable: {args.input_dir}")
        return False

    # Validate/create output directory
    output_path = Path(args.output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create output directory: {e}")
        return False
    
    if not os.access(args.output_dir, os.W_OK):
        logger.error(f"Output directory is not writable: {args.output_dir}")
        return False

    # Validate/create database directory
    queue_db_path = Path(args.queue_db)
    try:
        queue_db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create database directory: {e}")
        return False

    # Validate/create scratch directory
    scratch_path = Path(args.scratch_dir)
    try:
        scratch_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create scratch directory: {e}")
        return False

    return True


class StreamingPipeline:
    """Main pipeline coordinator.
    
    Manages the watcher and worker threads, handling graceful shutdown.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        """Initialize the pipeline.
        
        Args:
            args: Parsed command line arguments
        """
        self.args = args
        self._shutdown_event = threading.Event()
        self._queue: Optional[SubbandQueue] = None
        self._watcher: Optional[StreamingWatcher] = None
        self._worker: Optional[StreamingWorker] = None
        self._watcher_thread: Optional[threading.Thread] = None
        self._polling_thread: Optional[threading.Thread] = None

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def handler(signum: int, frame: object) -> None:
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def _start_watcher(self) -> None:
        """Start the filesystem watcher."""
        if self._queue is None:
            return
            
        self._watcher = StreamingWatcher(
            queue=self._queue,
            watch_dir=Path(self.args.input_dir),
        )
        
        try:
            self._watcher.start()
            logger.info(f"Watchdog monitoring {self.args.input_dir}")
        except ImportError:
            logger.info("Watchdog not available, using polling fallback")
            self._start_polling()

    def _start_polling(self) -> None:
        """Start polling fallback if watchdog is unavailable."""
        def poll_loop() -> None:
            input_dir = Path(self.args.input_dir)
            interval = self.args.poll_interval
            
            while not self._shutdown_event.is_set():
                try:
                    for p in input_dir.glob("*_sb??.hdf5"):
                        if self._queue is not None:
                            from dsa110_contimg.conversion.streaming.queue import (
                                parse_subband_info,
                            )
                            info = parse_subband_info(p)
                            if info is not None:
                                gid, sb = info
                                try:
                                    self._queue.record_subband(gid, sb, p)
                                except Exception:
                                    pass  # Duplicate or error
                except Exception as e:
                    logger.warning(f"Polling error: {e}")
                
                self._shutdown_event.wait(interval)
        
        self._polling_thread = threading.Thread(target=poll_loop, daemon=True)
        self._polling_thread.start()

    def run(self) -> int:
        """Run the streaming pipeline.
        
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        self._setup_signal_handlers()
        
        # Initialize queue
        registry_db = self.args.registry_db or self.args.queue_db
        self._queue = SubbandQueue(
            db_path=Path(self.args.queue_db),
            expected_subbands=self.args.expected_subbands,
            chunk_duration_minutes=self.args.chunk_duration,
        )
        
        # Start filesystem watching
        self._start_watcher()
        
        # Create worker
        config = WorkerConfig.from_args(self.args)
        # Use registry_db if specified, otherwise fallback to queue_db
        if self.args.registry_db:
            config.registry_db = Path(self.args.registry_db)
        self._worker = StreamingWorker(config, self._queue)
        
        # Run worker (blocking)
        logger.info("Streaming pipeline started")
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Process one group
                    group_id = self._queue.acquire_next_pending()
                    if group_id is not None:
                        result = self._worker.process_group(group_id)
                        if result.success:
                            self._queue.update_state(group_id, "completed")
                            logger.info(
                                f"Completed {group_id} in {result.elapsed_seconds:.2f}s"
                            )
                        else:
                            self._queue.update_state(
                                group_id,
                                "failed",
                                error=result.error_message,
                            )
                            logger.error(f"Failed {group_id}: {result.error_message}")
                    else:
                        self._shutdown_event.wait(self.args.worker_poll_interval)
                except Exception as e:
                    logger.exception(f"Processing error: {e}")
                    self._shutdown_event.wait(2.0)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
        
        return 0

    def shutdown(self) -> None:
        """Gracefully shutdown the pipeline."""
        logger.info("Shutting down streaming pipeline...")
        self._shutdown_event.set()
        
        if self._watcher is not None:
            self._watcher.stop()
        
        if self._queue is not None:
            self._queue.close()
        
        logger.info("Streaming pipeline stopped")


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the streaming converter CLI.
    
    Args:
        argv: Command line arguments (defaults to sys.argv)
        
    Returns:
        Exit code
    """
    # Set CASA log directory before any CASA imports
    try:
        from dsa110_contimg.utils.cli_helpers import setup_casa_environment
        setup_casa_environment()
    except ImportError:
        pass
    
    parser = build_parser()
    args = parser.parse_args(argv)
    
    setup_logging(args.log_level)
    
    # Validate paths
    if not validate_paths(args):
        return 1
    
    # Run pipeline
    pipeline = StreamingPipeline(args)
    return pipeline.run()


if __name__ == "__main__":
    sys.exit(main())
