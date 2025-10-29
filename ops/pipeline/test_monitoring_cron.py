#!/usr/bin/env python3
"""
Cron job script for automated test monitoring.

Designed to be run periodically (e.g., every hour) to execute tests,
record results, and alert on failures. Safe to run multiple times.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dsa110_contimg.testing.monitor import TestMonitor, run_comprehensive_tests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("state/logs/test_monitoring_cron.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main cron job execution."""
    logger.info("Starting scheduled test monitoring")

    try:
        # Initialize monitor
        test_db_path = os.getenv("CONTIMG_TEST_DB", "state/testing/test_results.sqlite3")
        monitor = TestMonitor(test_db_path)

        # Run comprehensive tests
        logger.info("Running comprehensive test suite...")
        suite_run = run_comprehensive_tests()

        # Record results
        run_id = monitor.record_suite_run(suite_run)

        # Log results
        logger.info(f"Test run {run_id} completed")
        logger.info(f"Results: {suite_run.passed}/{suite_run.total_tests} passed")
        logger.info(f"Duration: {suite_run.total_duration:.1f".1f"conds")

        # Check for issues and alert
        if suite_run.failed > 0 or suite_run.errors > 0:
            logger.warning(f"Test failures detected: {suite_run.failed} failed, {suite_run.errors} errors")
            # Alerting is handled by the run_comprehensive_tests function
        else:
            logger.info("All tests passed successfully")

        # Log environment info
        if suite_run.commit_hash:
            logger.info(f"Commit: {suite_run.commit_hash[:8]} ({suite_run.branch or 'unknown'})")

        logger.info("Test monitoring completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Test monitoring failed: {e}")
        # Don't exit with error code for cron jobs - just log the failure
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
