#!/opt/miniforge/envs/casa6/bin/python
"""Monitor publish status and alert on failures.

This script monitors the publish status of the DSA-110 Continuum Imaging Pipeline
and can alert on failures or retry failed publishes.

Usage:
    # Check current status
    python scripts/monitor_publish_status.py

    # Test mode (dry run)
    python scripts/monitor_publish_status.py --test

    # Retry failed publishes
    python scripts/monitor_publish_status.py --retry-failed

    # Retry all failed publishes (up to limit)
    python scripts/monitor_publish_status.py --retry-all --limit 10

    # Daemon mode (run continuously)
    python scripts/monitor_publish_status.py --daemon --interval 300
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.database.data_registry import (
    ensure_data_registry_db,
    list_data,
    trigger_auto_publish,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_publish_status(db_path: Path) -> dict:
    """Get publish status metrics."""
    conn = ensure_data_registry_db(db_path)

    # Get all published data
    published, total_published = list_data(conn, status="published")

    # Get all staging data (may include failed publishes)
    staging, total_staging = list_data(conn, status="staging")

    # Get publishing data (currently being published)
    publishing, total_publishing = list_data(conn, status="publishing")

    # Count failed publishes (staging with publish_attempts > 0)
    failed_publishes = [
        r for r in staging if r.publish_attempts and r.publish_attempts > 0
    ]

    # Count max attempts exceeded
    max_attempts_exceeded = [
        r for r in staging if r.publish_attempts and r.publish_attempts >= 3
    ]

    # Calculate success rate
    total_attempts = total_published + len(failed_publishes)
    success_rate = (
        (total_published / total_attempts * 100) if total_attempts > 0 else 100.0
    )

    conn.close()

    return {
        "total_published": total_published,
        "total_staging": total_staging,
        "total_publishing": total_publishing,
        "failed_publishes": len(failed_publishes),
        "max_attempts_exceeded": len(max_attempts_exceeded),
        "success_rate_percent": round(success_rate, 2),
    }


def get_failed_publishes(db_path: Path, max_attempts: Optional[int] = None) -> list:
    """Get list of failed publishes."""
    conn = ensure_data_registry_db(db_path)

    staging, _ = list_data(conn, status="staging")
    failed = [r for r in staging if r.publish_attempts and r.publish_attempts > 0]

    if max_attempts is not None:
        failed = [r for r in failed if r.publish_attempts >= max_attempts]

    failed.sort(key=lambda x: x.publish_attempts or 0, reverse=True)
    conn.close()

    return failed


def retry_failed_publish(db_path: Path, data_id: str, dry_run: bool = False) -> bool:
    """Retry a failed publish."""
    conn = ensure_data_registry_db(db_path)

    from dsa110_contimg.database.data_registry import get_data

    record = get_data(conn, data_id)
    if not record:
        logger.error(f"Data {data_id} not found")
        conn.close()
        return False

    if record.status == "published":
        logger.warning(f"Data {data_id} is already published")
        conn.close()
        return True

    if dry_run:
        logger.info(f"[DRY RUN] Would retry publish for {data_id}")
        conn.close()
        return True

    # Reset publish attempts
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE data_registry
        SET publish_attempts = 0,
            publish_error = NULL,
            status = 'staging'
        WHERE data_id = ?
        """,
        (data_id,),
    )
    conn.commit()

    # Trigger auto-publish
    success = trigger_auto_publish(conn, data_id)
    conn.close()

    if success:
        logger.info(f"Successfully retried publish for {data_id}")
    else:
        logger.error(f"Failed to retry publish for {data_id}")

    return success


def retry_all_failed(db_path: Path, limit: int = 10, dry_run: bool = False) -> dict:
    """Retry all failed publishes."""
    failed = get_failed_publishes(db_path)
    failed = failed[:limit]

    if dry_run:
        logger.info(f"[DRY RUN] Would retry {len(failed)} failed publishes")
        return {"total": len(failed), "successful": 0, "failed": 0}

    results = {"total": len(failed), "successful": 0, "failed": 0}

    for record in failed:
        success = retry_failed_publish(db_path, record.data_id, dry_run=False)
        if success:
            results["successful"] += 1
        else:
            results["failed"] += 1

    return results


def check_alerts(status: dict, alert_thresholds: dict) -> list:
    """Check for alert conditions."""
    alerts = []

    # Check success rate
    if status["success_rate_percent"] < alert_thresholds.get("min_success_rate", 95.0):
        alerts.append(
            f"Low publish success rate: {status['success_rate_percent']:.2f}% "
            f"(threshold: {alert_thresholds.get('min_success_rate', 95.0)}%)"
        )

    # Check failed publishes
    if status["failed_publishes"] > alert_thresholds.get("max_failed", 10):
        alerts.append(
            f"High number of failed publishes: {status['failed_publishes']} "
            f"(threshold: {alert_thresholds.get('max_failed', 10)})"
        )

    # Check max attempts exceeded
    if status["max_attempts_exceeded"] > 0:
        alerts.append(
            f"Publishes with max attempts exceeded: {status['max_attempts_exceeded']} "
            f"(manual intervention required)"
        )

    return alerts


def main():
    parser = argparse.ArgumentParser(description="Monitor publish status")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("/data/dsa110-contimg/state/db/products.sqlite3"),
        help="Path to data registry database",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode (dry run)",
    )
    parser.add_argument(
        "--retry-failed",
        type=str,
        metavar="DATA_ID",
        help="Retry a specific failed publish",
    )
    parser.add_argument(
        "--retry-all",
        action="store_true",
        help="Retry all failed publishes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit number of publishes to retry (default: 10)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in daemon mode (continuous monitoring)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Interval between checks in seconds (default: 300)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--alert-thresholds",
        type=str,
        help="JSON file with alert thresholds",
    )

    args = parser.parse_args()

    # Load alert thresholds
    alert_thresholds = {
        "min_success_rate": 95.0,
        "max_failed": 10,
    }
    if args.alert_thresholds:
        with open(args.alert_thresholds) as f:
            alert_thresholds.update(json.load(f))

    # Retry specific failed publish
    if args.retry_failed:
        success = retry_failed_publish(
            args.db_path, args.retry_failed, dry_run=args.test
        )
        sys.exit(0 if success else 1)

    # Retry all failed publishes
    if args.retry_all:
        results = retry_all_failed(args.db_path, limit=args.limit, dry_run=args.test)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            logger.info(
                f"Retry results: {results['successful']}/{results['total']} successful, "
                f"{results['failed']} failed"
            )
        sys.exit(0 if results["failed"] == 0 else 1)

    # Daemon mode
    if args.daemon:
        logger.info(f"Starting daemon mode (interval: {args.interval}s)")
        while True:
            try:
                status = get_publish_status(args.db_path)
                alerts = check_alerts(status, alert_thresholds)

                if alerts:
                    logger.warning("ALERTS:")
                    for alert in alerts:
                        logger.warning(f"  - {alert}")
                else:
                    logger.info(
                        f"Status OK: {status['total_published']} published, "
                        f"{status['failed_publishes']} failed, "
                        f"{status['success_rate_percent']:.2f}% success rate"
                    )

                time.sleep(args.interval)
            except KeyboardInterrupt:
                logger.info("Stopping daemon")
                break
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}", exc_info=True)
                time.sleep(args.interval)
        sys.exit(0)

    # One-time status check
    status = get_publish_status(args.db_path)
    alerts = check_alerts(status, alert_thresholds)

    if args.json:
        output = {
            "status": status,
            "alerts": alerts,
        }
        print(json.dumps(output, indent=2))
    else:
        print("\n=== Publish Status ===")
        print(f"Total Published: {status['total_published']}")
        print(f"Total Staging: {status['total_staging']}")
        print(f"Currently Publishing: {status['total_publishing']}")
        print(f"Failed Publishes: {status['failed_publishes']}")
        print(f"Max Attempts Exceeded: {status['max_attempts_exceeded']}")
        print(f"Success Rate: {status['success_rate_percent']:.2f}%")

        if alerts:
            print("\n=== ALERTS ===")
            for alert in alerts:
                print(f"  - {alert}")
        else:
            print("\n=== Status OK ===")

    # Show failed publishes if any
    if status["failed_publishes"] > 0:
        failed = get_failed_publishes(args.db_path)
        print(f"\n=== Failed Publishes (showing top 10) ===")
        for record in failed[:10]:
            print(
                f"  - {record.data_id}: "
                f"{record.publish_attempts} attempts, "
                f"error: {record.publish_error[:100] if record.publish_error else 'None'}"
            )

    sys.exit(0 if not alerts else 1)


if __name__ == "__main__":
    main()
