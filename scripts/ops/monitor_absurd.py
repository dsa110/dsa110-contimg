#!/opt/miniforge/envs/casa6/bin/python
"""
Real-time monitoring script for Absurd workflow manager.

Displays live metrics, health status, and alerts.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dsa110_contimg.absurd import AbsurdClient
from dsa110_contimg.absurd.monitoring import AbsurdMonitor


def clear_screen():
    """Clear terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 0:
        return "N/A"
    elif seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        return f"{seconds/86400:.1f}d"


def print_header():
    """Print monitoring header."""
    print("=" * 100)
    print(f"{'ABSURD WORKFLOW MONITOR':^100}")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^100}")
    print("=" * 100)


def print_health(health):
    """Print health status."""
    status_colors = {
        "healthy": "\033[92m",  # Green
        "degraded": "\033[93m",  # Yellow
        "critical": "\033[91m",  # Red
        "down": "\033[91m",  # Red
    }
    reset = "\033[0m"

    color = status_colors.get(health["status"], "")

    print(f"\n{'HEALTH STATUS':^100}")
    print("-" * 100)
    print(f"Status: {color}{health['status'].upper()}{reset} - {health['message']}")
    print(f"Queue Depth: {health['queue_depth']} tasks")
    print(
        f"Database: {':check: Available' if health['database_available'] else ':cross: Unavailable'} "
        f"({health['database_latency_ms']:.0f}ms)"
    )
    print(f"Workers: {health['worker_pool_message']}")

    if health["age_oldest_pending_sec"] > 0:
        print(f"Oldest Pending: {format_duration(health['age_oldest_pending_sec'])}")

    if health["last_task_completed_sec_ago"] >= 0:
        print(f"Last Completion: {format_duration(health['last_task_completed_sec_ago'])} ago")

    # Print alerts
    if health["alerts"]:
        print(f"\n{'ALERTS':^100}")
        print("-" * 100)
        for alert in health["alerts"]:
            print(f":police_cars_revolving_light: {alert}")

    # Print warnings
    if health["warnings"]:
        print(f"\n{'WARNINGS':^100}")
        print("-" * 100)
        for warning in health["warnings"]:
            print(f":warning:  {warning}")


def print_task_metrics(metrics):
    """Print task metrics."""
    print(f"\n{'TASK METRICS':^100}")
    print("-" * 100)

    # Counts
    print(f"Total Tasks:    {metrics['total_spawned']:>8}")
    print(
        f"  Completed:    {metrics['total_completed']:>8} ({metrics['total_completed']/max(1,metrics['total_spawned'])*100:>5.1f}%)"
    )
    print(
        f"  Failed:       {metrics['total_failed']:>8} ({metrics['total_failed']/max(1,metrics['total_spawned'])*100:>5.1f}%)"
    )
    print(f"  Cancelled:    {metrics['total_cancelled']:>8}")
    print(f"  Pending:      {metrics['current_pending']:>8}")
    print(f"  In Progress:  {metrics['current_claimed']:>8}")

    # Throughput
    print(f"\nThroughput:")
    print(f"  1 min:        {metrics['throughput_1min']:>8.2f} tasks/sec")
    print(f"  5 min:        {metrics['throughput_5min']:>8.2f} tasks/sec")
    print(f"  15 min:       {metrics['throughput_15min']:>8.2f} tasks/sec")

    # Success rates
    print(f"\nSuccess Rate:")
    print(f"  1 min:        {metrics['success_rate_1min']*100:>8.1f}%")
    print(f"  5 min:        {metrics['success_rate_5min']*100:>8.1f}%")
    print(f"  15 min:       {metrics['success_rate_15min']*100:>8.1f}%")

    # Latency
    if metrics["p50_wait_time_sec"] > 0:
        print(f"\nWait Time Latency:")
        print(f"  P50:          {metrics['p50_wait_time_sec']:>8.2f}s")
        print(f"  P95:          {metrics['p95_wait_time_sec']:>8.2f}s")
        print(f"  P99:          {metrics['p99_wait_time_sec']:>8.2f}s")

    if metrics["p50_execution_time_sec"] > 0:
        print(f"\nExecution Time:")
        print(f"  P50:          {metrics['p50_execution_time_sec']:>8.2f}s")
        print(f"  P95:          {metrics['p95_execution_time_sec']:>8.2f}s")
        print(f"  P99:          {metrics['p99_execution_time_sec']:>8.2f}s")


def print_worker_metrics(metrics):
    """Print worker metrics."""
    print(f"\n{'WORKER METRICS':^100}")
    print("-" * 100)

    print(f"Total Workers:  {metrics['total_workers']:>8}")
    print(f"  Active:       {metrics['active_workers']:>8}")
    print(f"  Idle:         {metrics['idle_workers']:>8}")
    print(f"  Crashed:      {metrics['crashed_workers']:>8}")

    if metrics["avg_tasks_per_worker"] > 0:
        print(f"\nAvg Tasks/Worker: {metrics['avg_tasks_per_worker']:>6.1f}")

    if metrics["avg_worker_uptime_sec"] > 0:
        print(f"Avg Uptime:       {format_duration(metrics['avg_worker_uptime_sec'])}")


async def monitor_loop(client: AbsurdClient, queue_name: str, interval: float):
    """Main monitoring loop."""
    monitor = AbsurdMonitor(client, queue_name)

    while True:
        try:
            clear_screen()
            print_header()

            # Generate report
            report = await monitor.generate_report()

            # Print sections
            print_health(report["health"])
            print_task_metrics(report["task_metrics"])
            print_worker_metrics(report["worker_metrics"])

            # Footer
            print("\n" + "=" * 100)
            print(f"{'Press Ctrl+C to exit | Refreshing every ' + str(interval) + 's':^100}")
            print("=" * 100)

        except Exception as e:
            print(f"\n:cross: Monitoring error: {e}")

        await asyncio.sleep(interval)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor Absurd workflow manager")

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
        help="Queue name to monitor",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Refresh interval in seconds",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (no loop)",
    )

    args = parser.parse_args()

    # Create client
    client = AbsurdClient(args.database_url)
    await client.connect()

    try:
        if args.once:
            # Run once
            monitor = AbsurdMonitor(client, args.queue_name)
            report = await monitor.generate_report()

            print_header()
            print_health(report["health"])
            print_task_metrics(report["task_metrics"])
            print_worker_metrics(report["worker_metrics"])
        else:
            # Continuous monitoring
            await monitor_loop(client, args.queue_name, args.interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
