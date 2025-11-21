"""
Performance monitoring visualizations for operational metrics.

This module generates trend plots and dashboards for:
- Stage duration over time
- Writer performance comparison
- Pipeline throughput (groups/hour)
- Failure rate tracking

Data is read from the performance_metrics table in the streaming ingest database.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DateFormatter, HourLocator

matplotlib.use("Agg")  # Non-interactive backend

logger = logging.getLogger(__name__)


def fetch_performance_metrics(
    queue_db: Path,
    hours: int = 24,
) -> List[Dict]:
    """Fetch performance metrics from the database.

    Args:
        queue_db: Path to the queue/ingest database
        hours: Number of hours of history to fetch

    Returns:
        List of dicts with keys: group_id, load_time, phase_time, write_time,
        total_time, writer_type, recorded_at
    """
    if not queue_db.exists():
        logger.warning(f"Queue database not found: {queue_db}")
        return []

    conn = sqlite3.connect(str(queue_db), timeout=30.0)
    conn.row_factory = sqlite3.Row

    cutoff_time = None
    if hours > 0:
        import time

        cutoff_time = time.time() - (hours * 3600)

    try:
        if cutoff_time:
            cursor = conn.execute(
                """
                SELECT group_id, load_time, phase_time, write_time, 
                       total_time, writer_type, recorded_at
                FROM performance_metrics
                WHERE recorded_at > ?
                ORDER BY recorded_at ASC
                """,
                (cutoff_time,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT group_id, load_time, phase_time, write_time, 
                       total_time, writer_type, recorded_at
                FROM performance_metrics
                ORDER BY recorded_at ASC
                """
            )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    finally:
        conn.close()


def plot_stage_duration_trends(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Pipeline Stage Duration Trends",
) -> Path:
    """Plot stage duration over time.

    Args:
        metrics: List of performance metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    # Extract data
    from datetime import datetime

    timestamps = [datetime.fromtimestamp(m["recorded_at"]) for m in metrics]
    load_times = [m.get("load_time", 0) or 0 for m in metrics]
    phase_times = [m.get("phase_time", 0) or 0 for m in metrics]
    write_times = [m.get("write_time", 0) or 0 for m in metrics]
    total_times = [m.get("total_time", 0) or 0 for m in metrics]

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Load time
    ax = axes[0, 0]
    ax.plot(timestamps, load_times, "o-", label="Load Time", alpha=0.7, markersize=3)
    ax.set_ylabel("Time (seconds)", fontsize=12)
    ax.set_title("UVH5 Load Time", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    if load_times:
        median = np.median([t for t in load_times if t > 0])
        ax.axhline(median, color="r", linestyle="--", alpha=0.5, label=f"Median: {median:.1f}s")
    ax.legend()

    # Plot 2: Phase time
    ax = axes[0, 1]
    ax.plot(
        timestamps, phase_times, "o-", label="Phase Time", color="orange", alpha=0.7, markersize=3
    )
    ax.set_ylabel("Time (seconds)", fontsize=12)
    ax.set_title("Phasing Time", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    if phase_times:
        median = np.median([t for t in phase_times if t > 0])
        ax.axhline(median, color="r", linestyle="--", alpha=0.5, label=f"Median: {median:.1f}s")
    ax.legend()

    # Plot 3: Write time
    ax = axes[1, 0]
    ax.plot(
        timestamps, write_times, "o-", label="Write Time", color="green", alpha=0.7, markersize=3
    )
    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Time (seconds)", fontsize=12)
    ax.set_title("MS Write Time", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    if write_times:
        median = np.median([t for t in write_times if t > 0])
        ax.axhline(median, color="r", linestyle="--", alpha=0.5, label=f"Median: {median:.1f}s")
    ax.legend()

    # Plot 4: Total time
    ax = axes[1, 1]
    ax.plot(
        timestamps, total_times, "o-", label="Total Time", color="purple", alpha=0.7, markersize=3
    )
    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Time (seconds)", fontsize=12)
    ax.set_title("Total Processing Time", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    if total_times:
        median = np.median([t for t in total_times if t > 0])
        ax.axhline(median, color="r", linestyle="--", alpha=0.5, label=f"Median: {median:.1f}s")
    ax.legend()

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved stage duration trends to {output_path}")
    return output_path


def plot_writer_performance_comparison(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Writer Performance Comparison",
) -> Path:
    """Compare performance of different writer types.

    Args:
        metrics: List of performance metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    # Group by writer type
    from collections import defaultdict

    writer_data = defaultdict(lambda: {"write_times": [], "total_times": []})

    for m in metrics:
        writer_type = m.get("writer_type") or "unknown"
        write_time = m.get("write_time")
        total_time = m.get("total_time")

        if write_time is not None and write_time > 0:
            writer_data[writer_type]["write_times"].append(write_time)
        if total_time is not None and total_time > 0:
            writer_data[writer_type]["total_times"].append(total_time)

    if not writer_data:
        logger.warning("No writer data to compare")
        return None

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    writer_types = sorted(writer_data.keys())
    colors = plt.cm.Set2(np.linspace(0, 1, len(writer_types)))

    # Plot 1: Write time comparison (violin plot)
    ax = axes[0]
    write_data = [writer_data[w]["write_times"] for w in writer_types]
    parts = ax.violinplot(
        write_data, positions=range(len(writer_types)), showmeans=True, showmedians=True
    )

    # Color the violins
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.7)

    ax.set_xticks(range(len(writer_types)))
    ax.set_xticklabels(writer_types, rotation=45, ha="right")
    ax.set_ylabel("Write Time (seconds)", fontsize=12)
    ax.set_title("Write Time Distribution by Writer", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # Add statistics text
    stats_text = []
    for i, w in enumerate(writer_types):
        times = writer_data[w]["write_times"]
        if times:
            median = np.median(times)
            n = len(times)
            stats_text.append(f"{w}: n={n}, med={median:.1f}s")

    ax.text(
        0.02,
        0.98,
        "\n".join(stats_text),
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    # Plot 2: Total time comparison
    ax = axes[1]
    total_data = [writer_data[w]["total_times"] for w in writer_types]
    parts = ax.violinplot(
        total_data, positions=range(len(writer_types)), showmeans=True, showmedians=True
    )

    # Color the violins
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.7)

    ax.set_xticks(range(len(writer_types)))
    ax.set_xticklabels(writer_types, rotation=45, ha="right")
    ax.set_ylabel("Total Time (seconds)", fontsize=12)
    ax.set_title("Total Processing Time by Writer", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # Add statistics text
    stats_text = []
    for i, w in enumerate(writer_types):
        times = writer_data[w]["total_times"]
        if times:
            median = np.median(times)
            n = len(times)
            stats_text.append(f"{w}: n={n}, med={median:.1f}s")

    ax.text(
        0.02,
        0.98,
        "\n".join(stats_text),
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved writer performance comparison to {output_path}")
    return output_path


def plot_pipeline_throughput(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Pipeline Throughput",
    window_hours: float = 1.0,
) -> Path:
    """Plot pipeline throughput (groups processed per hour).

    Args:
        metrics: List of performance metric dicts
        output_path: Path to save the plot
        title: Plot title
        window_hours: Rolling window size in hours for throughput calculation

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    from datetime import datetime

    # Sort by time
    sorted_metrics = sorted(metrics, key=lambda m: m["recorded_at"])

    timestamps = [datetime.fromtimestamp(m["recorded_at"]) for m in sorted_metrics]

    # Calculate rolling throughput
    window_seconds = window_hours * 3600
    throughput_times = []
    throughput_values = []

    for i, m in enumerate(sorted_metrics):
        current_time = m["recorded_at"]
        window_start = current_time - window_seconds

        # Count groups in the window
        count = sum(1 for m2 in sorted_metrics if window_start <= m2["recorded_at"] <= current_time)

        throughput = count / window_hours  # groups per hour
        throughput_times.append(timestamps[i])
        throughput_values.append(throughput)

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(
        throughput_times,
        throughput_values,
        "o-",
        color="steelblue",
        alpha=0.7,
        markersize=4,
        linewidth=2,
        label=f"Throughput ({window_hours}h window)",
    )

    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Groups Processed per Hour", fontsize=12)
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))

    if throughput_values:
        mean_throughput = np.mean(throughput_values)
        ax.axhline(
            mean_throughput,
            color="r",
            linestyle="--",
            alpha=0.5,
            label=f"Mean: {mean_throughput:.1f} groups/hr",
        )

    # Add statistics box
    if throughput_values:
        stats_text = (
            f"Mean: {np.mean(throughput_values):.1f} groups/hr\n"
            f"Median: {np.median(throughput_values):.1f} groups/hr\n"
            f"Max: {np.max(throughput_values):.1f} groups/hr\n"
            f"Min: {np.min(throughput_values):.1f} groups/hr\n"
            f"Total groups: {len(metrics)}"
        )
        ax.text(
            0.02,
            0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.7),
        )

    ax.legend(loc="upper right")

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved pipeline throughput plot to {output_path}")
    return output_path


def plot_failure_rate_tracking(
    queue_db: Path,
    output_path: Path,
    hours: int = 24,
    title: str = "Processing Failure Rate",
) -> Path:
    """Plot failure rate over time from the ingest_queue table.

    Args:
        queue_db: Path to the queue/ingest database
        output_path: Path to save the plot
        hours: Number of hours of history to fetch
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not queue_db.exists():
        logger.warning(f"Queue database not found: {queue_db}")
        return None

    conn = sqlite3.connect(str(queue_db), timeout=30.0)
    conn.row_factory = sqlite3.Row

    import time

    cutoff_time = time.time() - (hours * 3600) if hours > 0 else 0

    try:
        cursor = conn.execute(
            """
            SELECT group_id, state, received_at, last_update, retry_count
            FROM ingest_queue
            WHERE received_at > ?
            ORDER BY received_at ASC
            """,
            (cutoff_time,),
        )

        rows = cursor.fetchall()

    finally:
        conn.close()

    if not rows:
        logger.warning("No queue data to plot")
        return None

    from datetime import datetime

    # Organize data by time windows
    window_minutes = 30
    window_seconds = window_minutes * 60

    # Build time windows
    min_time = min(row["received_at"] for row in rows)
    max_time = max(row["last_update"] for row in rows)

    window_starts = np.arange(min_time, max_time, window_seconds)
    window_times = [datetime.fromtimestamp(t) for t in window_starts]

    total_counts = []
    failed_counts = []
    failure_rates = []

    for window_start in window_starts:
        window_end = window_start + window_seconds

        # Count groups in this window
        window_groups = [r for r in rows if window_start <= r["received_at"] < window_end]

        total = len(window_groups)
        failed = sum(1 for r in window_groups if r["state"] == "failed")

        total_counts.append(total)
        failed_counts.append(failed)
        failure_rates.append(100 * failed / total if total > 0 else 0)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Failure rate percentage
    ax = axes[0]
    ax.plot(
        window_times,
        failure_rates,
        "o-",
        color="red",
        alpha=0.7,
        markersize=5,
        linewidth=2,
        label="Failure Rate",
    )
    ax.set_ylabel("Failure Rate (%)", fontsize=12)
    ax.set_title(f"Failure Rate ({window_minutes}-minute windows)", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))

    if failure_rates:
        mean_rate = np.mean(failure_rates)
        ax.axhline(
            mean_rate, color="orange", linestyle="--", alpha=0.5, label=f"Mean: {mean_rate:.1f}%"
        )

    ax.legend()

    # Plot 2: Stacked bar chart of success vs failure
    ax = axes[1]
    success_counts = [t - f for t, f in zip(total_counts, failed_counts)]

    ax.bar(
        window_times,
        success_counts,
        label="Success",
        color="green",
        alpha=0.7,
        width=window_seconds / (24 * 3600),
    )
    ax.bar(
        window_times,
        failed_counts,
        bottom=success_counts,
        label="Failed",
        color="red",
        alpha=0.7,
        width=window_seconds / (24 * 3600),
    )

    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Number of Groups", fontsize=12)
    ax.set_title("Processing Success vs Failure", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    ax.legend()

    # Add statistics box
    total_processed = len(rows)
    total_failed = sum(1 for r in rows if r["state"] == "failed")
    overall_rate = 100 * total_failed / total_processed if total_processed > 0 else 0

    stats_text = (
        f"Total processed: {total_processed}\n"
        f"Failed: {total_failed}\n"
        f"Overall failure rate: {overall_rate:.1f}%"
    )
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.7),
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved failure rate plot to {output_path}")
    return output_path


def generate_performance_monitoring_dashboard(
    queue_db: Path,
    output_dir: Path,
    hours: int = 24,
) -> Dict[str, Path]:
    """Generate complete performance monitoring dashboard.

    Args:
        queue_db: Path to the queue/ingest database
        output_dir: Directory to save plots
        hours: Number of hours of history to include

    Returns:
        Dict mapping plot names to their file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch metrics
    metrics = fetch_performance_metrics(queue_db, hours=hours)

    plots = {}

    if metrics:
        # Stage duration trends
        path = plot_stage_duration_trends(metrics, output_dir / "stage_duration_trends.png")
        if path:
            plots["stage_duration_trends"] = path

        # Writer performance comparison
        path = plot_writer_performance_comparison(
            metrics, output_dir / "writer_performance_comparison.png"
        )
        if path:
            plots["writer_performance"] = path

        # Pipeline throughput
        path = plot_pipeline_throughput(metrics, output_dir / "pipeline_throughput.png")
        if path:
            plots["pipeline_throughput"] = path

    # Failure rate (uses queue table directly)
    path = plot_failure_rate_tracking(
        queue_db, output_dir / "failure_rate_tracking.png", hours=hours
    )
    if path:
        plots["failure_rate"] = path

    logger.info(f"Generated {len(plots)} performance monitoring plots")
    return plots


if __name__ == "__main__":
    # CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description="Generate performance monitoring visualizations")
    parser.add_argument(
        "--queue-db",
        type=Path,
        default=Path("/data/dsa110-contimg/state/streaming_ingest.db"),
        help="Path to queue database",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/dsa110-contimg/qa_outputs/performance"),
        help="Output directory for plots",
    )
    parser.add_argument("--hours", type=int, default=24, help="Hours of history to plot")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    plots = generate_performance_monitoring_dashboard(
        args.queue_db, args.output_dir, hours=args.hours
    )

    print("\nGenerated plots:")
    for name, path in plots.items():
        print(f"  {name}: {path}")
