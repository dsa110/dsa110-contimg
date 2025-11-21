#!/usr/bin/env python3
"""
Automated test monitoring daemon for DSA-110 pipeline.

Runs comprehensive tests on a schedule, records results, and alerts
on regressions or failures. Designed for lights-out operation.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dsa110_contimg.testing.monitor import TestMonitor, run_comprehensive_tests
from dsa110_contimg.utils import alerting

logger = logging.getLogger(__name__)


class TestMonitorDaemon:
    """Automated test monitoring daemon."""

    def __init__(
        self,
        test_db_path: str = "state/testing/test_results.sqlite3",
        check_interval: int = 3600,  # 1 hour
        max_failures: int = 3,
        alert_on_regression: bool = True,
    ):
        self.test_monitor = TestMonitor(test_db_path)
        self.check_interval = check_interval
        self.max_failures = max_failures
        self.alert_on_regression = alert_on_regression
        self.running = False
        self.failure_count = 0
        self.last_successful_run = None

    def start(self) -> None:
        """Start the monitoring daemon."""
        self.running = True
        logger.info("Starting test monitoring daemon")

        try:
            while self.running:
                try:
                    self._run_test_cycle()
                    time.sleep(self.check_interval)
                except KeyboardInterrupt:
                    logger.info("Received shutdown signal")
                    break
                except Exception as e:
                    logger.error(f"Test cycle failed: {e}")
                    self.failure_count += 1

                    if self.failure_count >= self.max_failures:
                        alerting.critical(
                            "test_monitoring",
                            f"Test monitoring daemon failed {self.failure_count} times",
                            {"error": str(e), "failure_count": self.failure_count},
                        )
                        break

                    time.sleep(60)  # Wait before retrying

        except Exception as e:
            logger.error(f"Daemon failed: {e}")
            alerting.critical("test_monitoring", f"Test daemon crashed: {e}")
            raise
        finally:
            logger.info("Test monitoring daemon stopped")

    def _run_test_cycle(self) -> None:
        """Run a complete test cycle."""
        logger.info("Starting test cycle")

        try:
            # Run comprehensive tests
            suite_run = run_comprehensive_tests()

            # Record results
            run_id = self.test_monitor.record_suite_run(suite_run)
            logger.info(
                f"Test run {run_id} completed: {suite_run.passed}/{suite_run.total_tests} passed"
            )

            # Check for regressions
            if self.alert_on_regression:
                self._check_for_regressions()

            # Update success tracking
            if suite_run.failed == 0 and suite_run.errors == 0:
                self.last_successful_run = datetime.now(timezone.utc)
                self.failure_count = 0  # Reset failure count on success
            else:
                self.failure_count += 1

            # Send appropriate alerts
            if suite_run.failed > 0 or suite_run.errors > 0:
                alerting.error(
                    "test_monitoring",
                    f"Test failures detected: {suite_run.failed} failed, {suite_run.errors} errors",
                    {
                        "failed_tests": suite_run.failed,
                        "error_tests": suite_run.errors,
                        "total_tests": suite_run.total_tests,
                        "commit": suite_run.commit_hash,
                        "branch": suite_run.branch,
                        "run_id": run_id,
                    },
                )
            else:
                alerting.info(
                    "test_monitoring",
                    f"All tests passed: {suite_run.passed}/{suite_run.total_tests}",
                    {
                        "passed": suite_run.passed,
                        "total": suite_run.total_tests,
                        "run_id": run_id,
                    },
                )

        except Exception as e:
            logger.error(f"Test cycle execution failed: {e}")
            alerting.error("test_monitoring", f"Test execution failed: {e}")

    def _check_for_regressions(self) -> None:
        """Check for test regressions and alert if found."""
        try:
            analysis = self.test_monitor.get_regression_analysis()

            if not analysis["stable"] and analysis["regressions"]:
                for regression in analysis["regressions"]:
                    alerting.warning(
                        "test_monitoring",
                        f"Test regression detected: lost {regression['tests_lost']} tests",
                        {
                            "timestamp": regression["timestamp"],
                            "tests_lost": regression["tests_lost"],
                            "total_runs": analysis["total_runs"],
                        },
                    )

            if analysis["improvements"]:
                for improvement in analysis["improvements"]:
                    alerting.info(
                        "test_monitoring",
                        f"Test improvement: gained {improvement['tests_gained']} tests",
                        {
                            "timestamp": improvement["timestamp"],
                            "tests_gained": improvement["tests_gained"],
                        },
                    )

        except Exception as e:
            logger.warning(f"Regression analysis failed: {e}")

    def stop(self) -> None:
        """Stop the monitoring daemon."""
        self.running = False
        logger.info("Test monitoring daemon stopping")


def main():
    """Main entry point for test monitoring daemon."""
    import argparse

    parser = argparse.ArgumentParser(description="DSA-110 Automated Test Monitoring")
    parser.add_argument(
        "--db",
        default="state/testing/test_results.sqlite3",
        help="Test results database path",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Check interval in seconds (default: 1 hour)",
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=3,
        help="Max consecutive failures before critical alert",
    )
    parser.add_argument(
        "--no-regression-alerts",
        action="store_true",
        help="Disable regression detection alerts",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run tests once and exit (no daemon mode)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    daemon = TestMonitorDaemon(
        test_db_path=args.db,
        check_interval=args.interval,
        max_failures=args.max_failures,
        alert_on_regression=not args.no_regression_alerts,
    )

    if args.run_once:
        # Single test run
        logger.info("Running single test cycle")
        daemon._run_test_cycle()
        return 0
    else:
        # Continuous monitoring
        logger.info(f"Starting continuous monitoring (interval: {args.interval}s)")
        daemon.start()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
