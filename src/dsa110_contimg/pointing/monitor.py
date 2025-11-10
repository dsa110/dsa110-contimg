import argparse
import json
import logging
import os
import signal
import sqlite3
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.pointing.utils import load_pointing

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PointingMonitorMetrics:
    """Tracks metrics for the pointing monitor."""

    def __init__(self, max_history: int = 1000):
        self.files_processed = 0
        self.files_succeeded = 0
        self.files_failed = 0
        self.last_processed_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.last_error_time: Optional[float] = None
        self.last_error_message: Optional[str] = None
        self.recent_errors = deque(maxlen=max_history)
        self.start_time = time.time()

    def record_success(self):
        """Record a successful file processing."""
        self.files_processed += 1
        self.files_succeeded += 1
        self.last_processed_time = time.time()
        self.last_success_time = time.time()

    def record_failure(self, error_message: str):
        """Record a failed file processing."""
        self.files_processed += 1
        self.files_failed += 1
        self.last_processed_time = time.time()
        self.last_error_time = time.time()
        self.last_error_message = error_message
        self.recent_errors.append({"time": time.time(), "message": error_message})

    def get_stats(self) -> Dict:
        """Get current statistics."""
        uptime = time.time() - self.start_time
        success_rate = (
            (self.files_succeeded / self.files_processed * 100)
            if self.files_processed > 0
            else 0.0
        )

        return {
            "files_processed": self.files_processed,
            "files_succeeded": self.files_succeeded,
            "files_failed": self.files_failed,
            "success_rate_percent": round(success_rate, 2),
            "uptime_seconds": round(uptime, 1),
            "last_processed_time": self.last_processed_time,
            "last_success_time": self.last_success_time,
            "last_error_time": self.last_error_time,
            "last_error_message": self.last_error_message,
            "recent_error_count": len(self.recent_errors),
        }


class PointingMonitor:
    """Main pointing monitor with health checks and metrics."""

    def __init__(
        self, watch_dir: Path, products_db: Path, status_file: Optional[Path] = None
    ):
        self.watch_dir = Path(watch_dir)
        self.products_db = Path(products_db)
        self.status_file = Path(status_file) if status_file else None
        self.metrics = PointingMonitorMetrics()
        self.conn: Optional[sqlite3.Connection] = None
        self.observer: Optional[Observer] = None
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _check_health(self) -> tuple[bool, list[str]]:
        """Perform health checks and return (is_healthy, issues)."""
        issues = []

        # Check watch directory exists and is readable
        if not self.watch_dir.exists():
            issues.append(f"Watch directory does not exist: {self.watch_dir}")
        elif not self.watch_dir.is_dir():
            issues.append(f"Watch path is not a directory: {self.watch_dir}")
        elif not os.access(self.watch_dir, os.R_OK):
            issues.append(f"Watch directory is not readable: {self.watch_dir}")

        # Check database accessibility
        try:
            test_conn = ensure_products_db(self.products_db)
            test_conn.execute("SELECT 1").fetchone()
            test_conn.close()
        except Exception as e:
            issues.append(f"Database not accessible: {self.products_db} ({e})")

        # Check database connection if established
        if self.conn is not None:
            try:
                self.conn.execute("SELECT 1").fetchone()
            except Exception as e:
                issues.append(f"Database connection lost: {e}")

        return len(issues) == 0, issues

    def _write_status(self):
        """Write status to file for external monitoring."""
        if self.status_file is None:
            return

        try:
            is_healthy, issues = self._check_health()
            stats = self.metrics.get_stats()

            status = {
                "running": self.running,
                "healthy": is_healthy,
                "issues": issues,
                "watch_dir": str(self.watch_dir),
                "products_db": str(self.products_db),
                "metrics": stats,
                "timestamp": time.time(),
                "timestamp_iso": datetime.utcnow().isoformat() + "Z",
            }

            # Write atomically
            temp_file = self.status_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(status, f, indent=2)
            temp_file.replace(self.status_file)
        except Exception as e:
            logger.warning(f"Failed to write status file: {e}")

    def log_pointing_from_file(self, file_path: Path):
        """Extracts pointing from a file and logs it to the database."""
        try:
            logger.info(f"Processing new file: {file_path}")

            # Reconnect if connection lost
            if self.conn is None:
                self.conn = ensure_products_db(self.products_db)

            info = load_pointing(file_path)
            if info and "mid_time" in info and "dec_deg" in info and "ra_deg" in info:
                self.conn.execute(
                    "INSERT OR REPLACE INTO pointing_history (timestamp, ra_deg, dec_deg) VALUES (?, ?, ?)",
                    (info["mid_time"].mjd, info["ra_deg"], info["dec_deg"]),
                )
                self.conn.commit()
                logger.info(
                    f"Logged pointing from {file_path}: RA={info['ra_deg']:.2f}, Dec={info['dec_deg']:.2f}"
                )
                self.metrics.record_success()
            else:
                error_msg = f"Missing required fields in pointing info: {list(info.keys()) if info else 'None'}"
                logger.warning(error_msg)
                self.metrics.record_failure(error_msg)
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {e}"
            logger.error(error_msg)
            self.metrics.record_failure(error_msg)
            # Try to reconnect on database errors
            if "database" in str(e).lower() or "locked" in str(e).lower():
                try:
                    if self.conn:
                        self.conn.close()
                except Exception:
                    pass
                self.conn = None

    def start(self, health_check_interval: int = 300):
        """Start the monitor with periodic health checks."""
        # Initial health check
        is_healthy, issues = self._check_health()
        if not is_healthy:
            logger.warning(f"Health check failed on startup: {issues}")
            logger.warning("Continuing anyway, but monitor may not function correctly")
        else:
            logger.info("Health check passed")

        # Initialize database connection
        try:
            self.conn = ensure_products_db(self.products_db)
            logger.info(f"Connected to database: {self.products_db}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

        # Setup file watcher
        event_handler = NewFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.watch_dir, recursive=True)

        logger.info(
            f"Starting to monitor {self.watch_dir} for new observation files..."
        )
        logger.info(f"Status file: {self.status_file}")
        self.running = True
        self.observer.start()

        # Write initial status
        self._write_status()

        # Main loop with periodic health checks
        last_health_check = time.time()
        last_status_write = time.time()
        status_write_interval = 30  # Write status every 30 seconds

        try:
            while self.running:
                time.sleep(1)

                # Periodic health check
                now = time.time()
                if now - last_health_check >= health_check_interval:
                    is_healthy, issues = self._check_health()
                    if not is_healthy:
                        logger.warning(f"Health check failed: {issues}")
                    last_health_check = now

                # Periodic status write
                if now - last_status_write >= status_write_interval:
                    self._write_status()
                    last_status_write = now

                    # Log metrics summary
                    stats = self.metrics.get_stats()
                    if stats["files_processed"] > 0:
                        logger.info(
                            f"Metrics: {stats['files_processed']} files processed, "
                            f"{stats['success_rate_percent']:.1f}% success rate, "
                            f"{stats['uptime_seconds']:.0f}s uptime"
                        )
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()

    def stop(self):
        """Stop the monitor gracefully."""
        if not self.running:
            return

        logger.info("Stopping monitor...")
        self.running = False

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)

        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

        # Write final status
        self._write_status()

        # Log final metrics
        stats = self.metrics.get_stats()
        logger.info(f"Final metrics: {stats}")


class NewFileHandler(FileSystemEventHandler):
    """File system event handler for new files."""

    def __init__(self, monitor: PointingMonitor):
        self.monitor = monitor

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.name.endswith("_sb00.hdf5") or file_path.name.endswith(".ms"):
            self.monitor.log_pointing_from_file(file_path)


def main():
    """Main function to monitor a directory for new observation files."""
    parser = argparse.ArgumentParser(
        description="Monitor a directory for new observation files and log their pointing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python -m dsa110_contimg.pointing.monitor /data/incoming /data/dsa110-contimg/state/products.sqlite3
  
  # With status file for monitoring
  python -m dsa110_contimg.pointing.monitor \\
    /data/incoming \\
    /data/dsa110-contimg/state/products.sqlite3 \\
    --status-file /data/dsa110-contimg/state/pointing-monitor-status.json
        """,
    )
    parser.add_argument(
        "watch_dir",
        type=Path,
        help="Directory to watch for new files (e.g., /data/incoming/).",
    )
    parser.add_argument("products_db", type=Path, help="Path to the products database.")
    parser.add_argument(
        "--status-file",
        type=Path,
        default=None,
        help="Path to write status JSON file for external monitoring (default: disabled)",
    )
    parser.add_argument(
        "--health-check-interval",
        type=int,
        default=300,
        help="Interval between health checks in seconds (default: 300)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Create and start monitor
    monitor = PointingMonitor(
        watch_dir=args.watch_dir,
        products_db=args.products_db,
        status_file=args.status_file,
    )

    try:
        monitor.start(health_check_interval=args.health_check_interval)
    except Exception as e:
        logger.error(f"Monitor failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
