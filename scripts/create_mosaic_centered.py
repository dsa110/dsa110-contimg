#!/usr/bin/env python3
"""
Create a mosaic centered on a calibrator transit.

Single trigger, hands-off operation: creates mosaic and waits until published.

Usage:
    PYTHONPATH=/data/dsa110-contimg/src python scripts/create_mosaic_centered.py \
        --calibrator 0834+555 \
        [--timespan-minutes 50] \
        [--no-wait]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Create mosaic centered on calibrator transit"
    )
    parser.add_argument(
        "--calibrator",
        required=True,
        help="Calibrator name (e.g., '0834+555')",
    )
    parser.add_argument(
        "--timespan-minutes",
        type=int,
        default=50,
        help="Mosaic timespan in minutes (default: 50)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for published status (return immediately after creation)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Polling interval in seconds for published status (default: 5)",
    )
    parser.add_argument(
        "--max-wait-hours",
        type=float,
        default=24.0,
        help="Maximum hours to wait for published status (default: 24)",
    )

    args = parser.parse_args()

    logger.info(
        f"Creating {args.timespan_minutes}-minute mosaic centered on {args.calibrator}"
    )

    # Initialize orchestrator
    orchestrator = MosaicOrchestrator()

    # Create mosaic
    published_path = orchestrator.create_mosaic_centered_on_calibrator(
        calibrator_name=args.calibrator,
        timespan_minutes=args.timespan_minutes,
        wait_for_published=not args.no_wait,
        poll_interval_seconds=args.poll_interval,
        max_wait_hours=args.max_wait_hours,
    )

    if published_path:
        logger.info(f"SUCCESS: Mosaic published at {published_path}")
        print(f"Published mosaic: {published_path}")
        return 0
    else:
        logger.error("FAILED: Mosaic creation or publishing failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

