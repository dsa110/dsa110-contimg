"""
Queue health monitoring visualizations for operational visibility.

This module generates visualizations for:
- Queue depth trends over time
- Processing rate analysis
- Time-to-completion cumulative distribution
- Queue state transitions

Data is read from the ingest_queue table in the streaming ingest database.
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


def fetch_queue_history(
    queue_db: Path,
    hours: int = 24,
) -> List[Dict]:
    """Fetch queue state history from the database.

    Args:
        queue_db: Path to the queue/ingest database
        hours: Number of hours of history to fetch

    Returns:
        List of dicts with keys: group_id, state, received_at, last_update,
        expected_subbands, retry_count, processing_stage, chunk_minutes
    """
    if not queue_db.exists():
        logger.warning(f"Queue database not found: {queue_db}")
        return []

    conn = sqlite3.connect(str(queue_db), timeout=30.0)
    conn.row_factory = sqlite3.Row

    import time

    cutoff_time = time.time() - (hours * 3600) if hours > 0 else 0

    try:
        cursor = conn.execute(
            """
            SELECT group_id, state, received_at, last_update,
                   expected_subbands, retry_count, processing_stage, chunk_minutes
            FROM ingest_queue
            WHERE received_at > ?
            ORDER BY received_at ASC
            """,
            (cutoff_time,),
        )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    finally:
        conn.close()


def plot_queue_depth_trends(
    queue_history: List[Dict],
    output_path: Path,
    title: str = "Queue Depth Over Time",
    window_minutes: int = 5,
) -> Path:
    """Plot queue depth trends over time.

    Args:
        queue_history: List of queue state dicts
        output_path: Path to save the plot
        title: Plot title
        window_minutes: Time window for binning (minutes)

    Returns:
        Path to saved plot
    """
    if not queue_history:
        logger.warning("No queue history to plot")
        return None

    from datetime import datetime

    # Build time windows
    min_time = min(row["received_at"] for row in queue_history)
    max_time = max(row["last_update"] for row in queue_history)

    window_seconds = window_minutes * 60
    window_starts = np.arange(min_time, max_time + window_seconds, window_seconds)
    window_times = [datetime.fromtimestamp(t) for t in window_starts]

    # Count queue states in each window
    states = ["collecting", "pending", "in_progress", "completed", "failed"]
    state_counts = {state: [] for state in states}
    total_counts = []

    for window_start in window_starts:
        window_end = window_start + window_seconds

        # Find groups active in this window
        active_groups = []
        for row in queue_history:
            # Group is active if it was received before window end
            # and last updated after window start
            if row["received_at"] <= window_end and row["last_update"] >= window_start:
                active_groups.append(row)

        # Count by state
        total = len(active_groups)
        total_counts.append(total)

        for state in states:
            count = sum(1 for g in active_groups if g["state"] == state)
            state_counts[state].append(count)

    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Stacked area chart
    ax = axes[0]

    colors = {
        "collecting": "lightblue",
        "pending": "yellow",
        "in_progress": "orange",
        "completed": "green",
        "failed": "red",
    }

    # Stack the areas
    bottom = np.zeros(len(window_times))
    for state in states:
        counts = state_counts[state]
        ax.fill_between(
            window_times,
            bottom,
            bottom + counts,
            label=state.capitalize(),
            color=colors[state],
            alpha=0.7,
        )
        bottom += counts

    ax.set_ylabel("Number of Groups", fontsize=12)
    ax.set_title(f"Queue Depth by State ({window_minutes}-min windows)", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    ax.legend(loc="upper left", fontsize=10)

    # Plot 2: Total queue depth with moving average
    ax = axes[1]

    ax.plot(
        window_times,
        total_counts,
        "o-",
        color="steelblue",
        alpha=0.5,
        markersize=3,
        label="Total Queue Depth",
    )

    # Calculate moving average
    ma_window = max(1, len(total_counts) // 20)
    if len(total_counts) >= ma_window:
        moving_avg = np.convolve(total_counts, np.ones(ma_window) / ma_window, mode="valid")
        ma_times = window_times[: len(moving_avg)]
        ax.plot(
            ma_times,
            moving_avg,
            "-",
            color="darkblue",
            linewidth=3,
            label=f"Moving Average (n={ma_window})",
        )

    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Total Groups in Queue", fontsize=12)
    ax.set_title("Total Queue Depth", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    ax.legend(loc="upper left", fontsize=10)

    # Add statistics
    if total_counts:
        stats_text = (
            f"Max depth: {np.max(total_counts)}\n"
            f"Mean depth: {np.mean(total_counts):.1f}\n"
            f"Current depth: {total_counts[-1]}"
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

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved queue depth trends to {output_path}")
    return output_path


def plot_processing_rate(
    queue_history: List[Dict],
    output_path: Path,
    title: str = "Processing Rate Analysis",
    window_minutes: int = 10,
) -> Path:
    """Plot processing rate (completions per unit time).

    Args:
        queue_history: List of queue state dicts
        output_path: Path to save the plot
        title: Plot title
        window_minutes: Time window for rate calculation

    Returns:
        Path to saved plot
    """
    if not queue_history:
        logger.warning("No queue history to plot")
        return None

    from datetime import datetime

    # Filter for completed/failed groups
    terminal_groups = [g for g in queue_history if g["state"] in ("completed", "failed")]

    if not terminal_groups:
        logger.warning("No completed/failed groups to analyze")
        return None

    # Build time windows
    min_time = min(g["last_update"] for g in terminal_groups)
    max_time = max(g["last_update"] for g in terminal_groups)

    window_seconds = window_minutes * 60
    window_starts = np.arange(min_time, max_time + window_seconds, window_seconds)
    window_times = [datetime.fromtimestamp(t) for t in window_starts]

    # Count completions and failures in each window
    completion_counts = []
    failure_counts = []
    processing_rates = []

    for window_start in window_starts:
        window_end = window_start + window_seconds

        completions = sum(
            1
            for g in terminal_groups
            if g["state"] == "completed" and window_start <= g["last_update"] < window_end
        )

        failures = sum(
            1
            for g in terminal_groups
            if g["state"] == "failed" and window_start <= g["last_update"] < window_end
        )

        completion_counts.append(completions)
        failure_counts.append(failures)

        # Rate in groups per hour
        total = completions + failures
        rate = total / (window_minutes / 60.0)
        processing_rates.append(rate)

    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Processing rate
    ax = axes[0]

    ax.plot(
        window_times,
        processing_rates,
        "o-",
        color="green",
        alpha=0.7,
        markersize=4,
        linewidth=2,
        label="Processing Rate",
    )

    if processing_rates:
        mean_rate = np.mean([r for r in processing_rates if r > 0])
        ax.axhline(
            mean_rate,
            color="red",
            linestyle="--",
            alpha=0.5,
            label=f"Mean: {mean_rate:.1f} groups/hr",
        )

    ax.set_ylabel("Groups per Hour", fontsize=12)
    ax.set_title(f"Processing Rate ({window_minutes}-min windows)", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    ax.legend()

    # Plot 2: Stacked bar of completions vs failures
    ax = axes[1]

    ax.bar(
        window_times,
        completion_counts,
        label="Completed",
        color="green",
        alpha=0.7,
        width=window_seconds / (24 * 3600),
    )
    ax.bar(
        window_times,
        failure_counts,
        bottom=completion_counts,
        label="Failed",
        color="red",
        alpha=0.7,
        width=window_seconds / (24 * 3600),
    )

    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Number of Groups", fontsize=12)
    ax.set_title("Completions vs Failures", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    ax.legend()

    # Add statistics
    total_completed = sum(completion_counts)
    total_failed = sum(failure_counts)
    success_rate = (
        100 * total_completed / (total_completed + total_failed)
        if (total_completed + total_failed) > 0
        else 0
    )

    stats_text = (
        f"Total completed: {total_completed}\n"
        f"Total failed: {total_failed}\n"
        f"Success rate: {success_rate:.1f}%"
    )
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.7),
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved processing rate plot to {output_path}")
    return output_path


def plot_time_to_completion_cdf(
    queue_history: List[Dict],
    output_path: Path,
    title: str = "Time-to-Completion Distribution",
) -> Path:
    """Plot cumulative distribution of time to completion.

    Args:
        queue_history: List of queue state dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not queue_history:
        logger.warning("No queue history to plot")
        return None

    # Calculate processing times for completed groups
    completed_groups = [g for g in queue_history if g["state"] == "completed"]

    if not completed_groups:
        logger.warning("No completed groups to analyze")
        return None

    processing_times = []
    for g in completed_groups:
        duration = g["last_update"] - g["received_at"]
        processing_times.append(duration / 60.0)  # Convert to minutes

    processing_times = sorted(processing_times)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Histogram
    ax = axes[0]

    ax.hist(processing_times, bins=30, color="steelblue", alpha=0.7, edgecolor="black")

    # Add percentile lines
    p50 = np.percentile(processing_times, 50)
    p95 = np.percentile(processing_times, 95)
    p99 = np.percentile(processing_times, 99)

    ax.axvline(p50, color="green", linestyle="--", linewidth=2, label=f"P50: {p50:.1f} min")
    ax.axvline(p95, color="orange", linestyle="--", linewidth=2, label=f"P95: {p95:.1f} min")
    ax.axvline(p99, color="red", linestyle="--", linewidth=2, label=f"P99: {p99:.1f} min")

    ax.set_xlabel("Processing Time (minutes)", fontsize=12)
    ax.set_ylabel("Number of Groups", fontsize=12)
    ax.set_title("Processing Time Distribution", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend(loc="upper right")

    # Plot 2: Cumulative distribution
    ax = axes[1]

    # Calculate CDF
    n = len(processing_times)
    cdf_y = np.arange(1, n + 1) / n * 100

    ax.plot(processing_times, cdf_y, "-", color="darkblue", linewidth=2)
    ax.fill_between(processing_times, 0, cdf_y, alpha=0.3, color="skyblue")

    # Add percentile markers
    ax.axhline(50, color="green", linestyle=":", alpha=0.5)
    ax.axhline(95, color="orange", linestyle=":", alpha=0.5)
    ax.axhline(99, color="red", linestyle=":", alpha=0.5)

    ax.axvline(p50, color="green", linestyle="--", linewidth=2, label=f"P50: {p50:.1f} min")
    ax.axvline(p95, color="orange", linestyle="--", linewidth=2, label=f"P95: {p95:.1f} min")
    ax.axvline(p99, color="red", linestyle="--", linewidth=2, label=f"P99: {p99:.1f} min")

    ax.set_xlabel("Processing Time (minutes)", fontsize=12)
    ax.set_ylabel("Cumulative Percentage", fontsize=12)
    ax.set_title("Cumulative Distribution Function (CDF)", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")

    # Add statistics box
    stats_text = (
        f"N = {n} groups\n"
        f"Mean: {np.mean(processing_times):.1f} min\n"
        f"Median: {p50:.1f} min\n"
        f"Std: {np.std(processing_times):.1f} min\n"
        f"Min: {np.min(processing_times):.1f} min\n"
        f"Max: {np.max(processing_times):.1f} min"
    )
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.7),
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved time-to-completion CDF to {output_path}")
    return output_path


def plot_queue_state_transitions(
    queue_history: List[Dict],
    output_path: Path,
    title: str = "Queue State Transitions",
) -> Path:
    """Plot queue state transitions and flow.

    Args:
        queue_history: List of queue state dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not queue_history:
        logger.warning("No queue history to plot")
        return None

    # Count final states
    from collections import Counter

    state_counts = Counter(g["state"] for g in queue_history)
    retry_counts = Counter(g.get("retry_count", 0) for g in queue_history)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: State distribution pie chart
    ax = axes[0]

    states = ["collecting", "pending", "in_progress", "completed", "failed"]
    colors = ["lightblue", "yellow", "orange", "green", "red"]

    counts = [state_counts.get(state, 0) for state in states]
    labels = [f"{state.capitalize()}\n({count})" for state, count in zip(states, counts)]

    wedges, texts, autotexts = ax.pie(
        counts,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        textprops={"fontsize": 11},
    )

    for autotext in autotexts:
        autotext.set_color("black")
        autotext.set_fontweight("bold")

    ax.set_title("Current State Distribution", fontweight="bold", pad=20)

    # Plot 2: Retry count distribution
    ax = axes[1]

    retry_keys = sorted(retry_counts.keys())
    retry_values = [retry_counts[k] for k in retry_keys]

    bars = ax.bar(retry_keys, retry_values, color="coral", alpha=0.7, edgecolor="black")

    # Color code bars with retries > 0
    for i, (key, bar) in enumerate(zip(retry_keys, bars)):
        if key > 0:
            bar.set_color("red")
            bar.set_alpha(0.8)

    ax.set_xlabel("Retry Count", fontsize=12)
    ax.set_ylabel("Number of Groups", fontsize=12)
    ax.set_title("Retry Count Distribution", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # Add statistics
    total_retries = sum(k * v for k, v in retry_counts.items())
    groups_with_retries = sum(v for k, v in retry_counts.items() if k > 0)

    stats_text = (
        f"Total groups: {sum(retry_values)}\n"
        f"Groups with retries: {groups_with_retries}\n"
        f"Total retry attempts: {total_retries}"
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

    logger.info(f"Saved queue state transitions to {output_path}")
    return output_path


def generate_queue_health_dashboard(
    queue_db: Path,
    output_dir: Path,
    hours: int = 24,
) -> Dict[str, Path]:
    """Generate complete queue health monitoring dashboard.

    Args:
        queue_db: Path to the queue/ingest database
        output_dir: Directory to save plots
        hours: Number of hours of history to include

    Returns:
        Dict mapping plot names to their file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch queue history
    queue_history = fetch_queue_history(queue_db, hours=hours)

    plots = {}

    if queue_history:
        # Queue depth trends
        path = plot_queue_depth_trends(queue_history, output_dir / "queue_depth_trends.png")
        if path:
            plots["queue_depth"] = path

        # Processing rate
        path = plot_processing_rate(queue_history, output_dir / "processing_rate.png")
        if path:
            plots["processing_rate"] = path

        # Time to completion CDF
        path = plot_time_to_completion_cdf(queue_history, output_dir / "time_to_completion_cdf.png")
        if path:
            plots["time_to_completion"] = path

        # State transitions
        path = plot_queue_state_transitions(
            queue_history, output_dir / "queue_state_transitions.png"
        )
        if path:
            plots["state_transitions"] = path

    logger.info(f"Generated {len(plots)} queue health monitoring plots")
    return plots


if __name__ == "__main__":
    # CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description="Generate queue health monitoring visualizations")
    parser.add_argument(
        "--queue-db",
        type=Path,
        default=Path("/data/dsa110-contimg/state/streaming_ingest.db"),
        help="Path to queue database",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/dsa110-contimg/qa_outputs/queue_health"),
        help="Output directory for plots",
    )
    parser.add_argument("--hours", type=int, default=24, help="Hours of history to plot")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    plots = generate_queue_health_dashboard(args.queue_db, args.output_dir, hours=args.hours)

    print("\nGenerated plots:")
    for name, path in plots.items():
        print(f"  {name}: {path}")
