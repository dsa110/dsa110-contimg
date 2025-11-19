"""
Disk usage monitoring visualizations.

This module generates plots for:
- Disk space trends over time (per mount point)
- Storage growth rate analysis
- Free space projections
- Cleanup recommendations

Data is collected from system metrics and stored in a dedicated table.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DateFormatter

matplotlib.use("Agg")  # Non-interactive backend

logger = logging.getLogger(__name__)


def collect_current_disk_usage() -> List[Dict]:
    """Collect current disk usage for monitored paths.

    Returns:
        List of dicts with disk usage info
    """
    monitored_paths = [
        "/data",
        "/stage",
        "/tmp",
        "/dev/shm",
    ]

    usage_data = []

    for path_str in monitored_paths:
        path = Path(path_str)
        if path.exists():
            try:
                usage = shutil.disk_usage(path)
                usage_data.append(
                    {
                        "mount_point": path_str,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": 100 * usage.used / usage.total if usage.total > 0 else 0,
                    }
                )
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("Failed to get disk usage for %s: %s", path_str, e)

    return usage_data


def plot_disk_usage_current(
    usage_data: List[Dict],
    output_path: Path,
    title: str = "Current Disk Usage",
) -> Path:
    """Plot current disk usage for all mount points.

    Args:
        usage_data: List of disk usage dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not usage_data:
        logger.warning("No disk usage data to plot")
        return None

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Bar chart of usage percentage
    ax = axes[0]

    mount_points = [d["mount_point"] for d in usage_data]
    percentages = [d["percent"] for d in usage_data]

    # Color bars based on usage level
    colors = []
    for pct in percentages:
        if pct >= 90:
            colors.append("red")
        elif pct >= 75:
            colors.append("orange")
        elif pct >= 50:
            colors.append("yellow")
        else:
            colors.append("green")

    bars = ax.barh(
        mount_points, percentages, color=colors, alpha=0.7, edgecolor="black", linewidth=1
    )

    # Add percentage labels
    for i, (bar, pct) in enumerate(zip(bars, percentages)):
        ax.text(pct + 1, i, f"{pct:.1f}%", va="center", fontsize=10, fontweight="bold")

    # Add warning lines
    ax.axvline(75, color="orange", linestyle="--", alpha=0.5, label="75% warning")
    ax.axvline(90, color="red", linestyle="--", alpha=0.5, label="90% critical")

    ax.set_xlabel("Usage (%)", fontsize=12)
    ax.set_xlim(0, 105)
    ax.set_title("Disk Usage Percentage", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="x")
    ax.legend(loc="lower right")

    # Plot 2: Stacked bar showing used vs free
    ax = axes[1]

    used_gb = [d["used"] / (1024**3) for d in usage_data]
    free_gb = [d["free"] / (1024**3) for d in usage_data]

    ax.barh(mount_points, used_gb, label="Used", color="steelblue", alpha=0.7)
    ax.barh(mount_points, free_gb, left=used_gb, label="Free", color="lightgreen", alpha=0.7)

    # Add size labels
    for i, d in enumerate(usage_data):
        total_gb = d["total"] / (1024**3)
        ax.text(
            total_gb / 2,
            i,
            f"{total_gb:.0f} GB total",
            va="center",
            ha="center",
            fontsize=10,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7),
        )

    ax.set_xlabel("Disk Space (GB)", fontsize=12)
    ax.set_title("Used vs Free Space", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="x")
    ax.legend()

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved disk usage plot to %s", output_path)
    return output_path


def estimate_time_to_full(
    usage_data: List[Dict],
    daily_growth_gb: Optional[Dict[str, float]] = None,
) -> Dict[str, Tuple[float, str]]:
    """Estimate time until disk is full based on growth rate.

    Args:
        usage_data: Current disk usage
        daily_growth_gb: Daily growth rate per mount point (GB/day)

    Returns:
        Dict mapping mount point to (days_remaining, status)
    """
    if daily_growth_gb is None:
        # Default conservative estimates (GB/day)
        daily_growth_gb = {
            "/data": 50.0,
            "/stage": 100.0,
            "/tmp": 10.0,
            "/dev/shm": 5.0,
        }

    estimates = {}

    for d in usage_data:
        mount_point = d["mount_point"]
        free_gb = d["free"] / (1024**3)
        growth_rate = daily_growth_gb.get(mount_point, 10.0)

        if growth_rate > 0:
            days_remaining = free_gb / growth_rate

            if days_remaining < 1:
                status = "CRITICAL"
            elif days_remaining < 7:
                status = "WARNING"
            elif days_remaining < 30:
                status = "CAUTION"
            else:
                status = "OK"

            estimates[mount_point] = (days_remaining, status)
        else:
            estimates[mount_point] = (float("inf"), "OK")

    return estimates


def plot_disk_usage_projection(
    usage_data: List[Dict],
    output_path: Path,
    title: str = "Disk Usage Projections",
    days_ahead: int = 30,
    daily_growth_gb: Optional[Dict[str, float]] = None,
) -> Path:
    """Plot disk usage projections.

    Args:
        usage_data: Current disk usage
        output_path: Path to save the plot
        title: Plot title
        days_ahead: Number of days to project
        daily_growth_gb: Daily growth rate per mount point

    Returns:
        Path to saved plot
    """
    if not usage_data:
        logger.warning("No disk usage data to plot")
        return None

    if daily_growth_gb is None:
        daily_growth_gb = {
            "/data": 50.0,
            "/stage": 100.0,
            "/tmp": 10.0,
            "/dev/shm": 5.0,
        }

    estimates = estimate_time_to_full(usage_data, daily_growth_gb)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Projected usage over time
    ax = axes[0]

    days = np.arange(0, days_ahead + 1)

    for d in usage_data:
        mount_point = d["mount_point"]
        current_used_gb = d["used"] / (1024**3)
        total_gb = d["total"] / (1024**3)
        growth_rate = daily_growth_gb.get(mount_point, 10.0)

        # Project usage
        projected_used = current_used_gb + days * growth_rate
        projected_pct = 100 * projected_used / total_gb

        # Clip at 100%
        projected_pct = np.clip(projected_pct, 0, 100)

        ax.plot(days, projected_pct, "o-", label=mount_point, alpha=0.7, markersize=3)

    ax.axhline(75, color="orange", linestyle="--", alpha=0.5, label="75% warning")
    ax.axhline(90, color="red", linestyle="--", alpha=0.5, label="90% critical")
    ax.axhline(100, color="darkred", linestyle="-", alpha=0.5, linewidth=2)

    ax.set_xlabel("Days from Now", fontsize=12)
    ax.set_ylabel("Usage (%)", fontsize=12)
    ax.set_title(f"{days_ahead}-Day Usage Projection", fontweight="bold")
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")

    # Plot 2: Time to full estimate
    ax = axes[1]

    mount_points = []
    days_remaining = []
    colors = []

    for mount_point, (days_left, status) in sorted(estimates.items()):
        if days_left < float("inf"):
            mount_points.append(mount_point)
            days_remaining.append(days_left)

            if status == "CRITICAL":
                colors.append("red")
            elif status == "WARNING":
                colors.append("orange")
            elif status == "CAUTION":
                colors.append("yellow")
            else:
                colors.append("green")

    if mount_points:
        bars = ax.barh(
            mount_points, days_remaining, color=colors, alpha=0.7, edgecolor="black", linewidth=1
        )

        # Add day labels
        for i, (bar, days) in enumerate(zip(bars, days_remaining)):
            ax.text(days + 1, i, f"{days:.1f} days", va="center", fontsize=10, fontweight="bold")

        ax.axvline(7, color="red", linestyle="--", alpha=0.5, label="7 days")
        ax.axvline(30, color="orange", linestyle="--", alpha=0.5, label="30 days")

        ax.set_xlabel("Days Until Full", fontsize=12)
        ax.set_title("Estimated Time Until Disk Full", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="x")
        ax.legend()

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved disk usage projection to %s", output_path)
    return output_path


def generate_disk_usage_dashboard(
    output_dir: Path,
    daily_growth_gb: Optional[Dict[str, float]] = None,
) -> Dict[str, Path]:
    """Generate complete disk usage monitoring dashboard.

    Args:
        output_dir: Directory to save plots
        daily_growth_gb: Daily growth rate per mount point (GB/day)

    Returns:
        Dict mapping plot names to their file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect current disk usage
    usage_data = collect_current_disk_usage()

    plots = {}

    if usage_data:
        # Current usage
        plot_path = plot_disk_usage_current(usage_data, output_dir / "disk_usage_current.png")
        if plot_path:
            plots["current"] = plot_path

        # Projections
        plot_path = plot_disk_usage_projection(
            usage_data, output_dir / "disk_usage_projection.png", daily_growth_gb=daily_growth_gb
        )
        if plot_path:
            plots["projection"] = plot_path

    logger.info("Generated %d disk usage monitoring plots", len(plots))
    return plots


if __name__ == "__main__":
    # CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description="Generate disk usage monitoring visualizations")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/dsa110-contimg/qa_outputs/disk_usage"),
        help="Output directory for plots",
    )
    parser.add_argument(
        "--data-growth",
        type=float,
        default=50.0,
        help="Daily growth rate for /data in GB/day",
    )
    parser.add_argument(
        "--stage-growth",
        type=float,
        default=100.0,
        help="Daily growth rate for /stage in GB/day",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    daily_growth = {
        "/data": args.data_growth,
        "/stage": args.stage_growth,
        "/tmp": 10.0,
        "/dev/shm": 5.0,
    }

    plots = generate_disk_usage_dashboard(args.output_dir, daily_growth_gb=daily_growth)

    print("\nGenerated plots:")
    for name, path in plots.items():
        print(f"  {name}: {path}")
