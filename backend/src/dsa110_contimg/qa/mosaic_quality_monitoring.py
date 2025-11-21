"""
Mosaic quality monitoring visualizations.

This module generates trend plots for:
- RMS noise evolution over time
- Dynamic range trends
- Source count trends
- Mosaic creation success rate

Data is read from the products database (mosaics table and related QA tables).
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DateFormatter

matplotlib.use("Agg")  # Non-interactive backend

logger = logging.getLogger(__name__)


def fetch_mosaic_quality_metrics(
    products_db: Path,
    hours: int = 168,  # Default 7 days
) -> List[Dict]:
    """Fetch mosaic quality metrics from the products database.

    Args:
        products_db: Path to the products database
        hours: Number of hours of history to fetch

    Returns:
        List of dicts with mosaic metrics
    """
    if not products_db.exists():
        logger.warning("Products database not found: %s", products_db)
        return []

    conn = sqlite3.connect(str(products_db), timeout=30.0)
    conn.row_factory = sqlite3.Row

    import time

    cutoff_time = time.time() - (hours * 3600) if hours > 0 else 0

    try:
        cursor = conn.execute(
            """
            SELECT 
                id,
                name,
                path,
                start_mjd,
                end_mjd,
                created_at,
                status,
                image_count,
                noise_jy,
                source_count
            FROM mosaics
            WHERE created_at > ?
            ORDER BY created_at ASC
            """,
            (cutoff_time,),
        )

        rows = cursor.fetchall()

        # Also fetch image QA metrics for mosaics
        metrics = []
        for row in rows:
            metric = dict(row)

            # Try to get additional QA metrics from image_qa table
            try:
                qa_cursor = conn.execute(
                    """
                    SELECT rms_noise, peak_flux, dynamic_range
                    FROM image_qa
                    WHERE image_path = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (row["path"],),
                )
                qa_row = qa_cursor.fetchone()
                if qa_row:
                    metric["rms_noise"] = qa_row["rms_noise"]
                    metric["peak_flux"] = qa_row["peak_flux"]
                    metric["dynamic_range"] = qa_row["dynamic_range"]
            except Exception:  # pylint: disable=broad-except
                pass

            metrics.append(metric)

        return metrics

    finally:
        conn.close()


def plot_mosaic_rms_trends(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Mosaic RMS Noise Trends",
) -> Path:
    """Plot RMS noise trends over time.

    Args:
        metrics: List of mosaic metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    from datetime import datetime

    # Extract data
    timestamps = []
    rms_values = []

    for m in metrics:
        if m.get("noise_jy") is not None or m.get("rms_noise") is not None:
            timestamps.append(datetime.fromtimestamp(m["created_at"]))
            # Prefer rms_noise from image_qa, fallback to noise_jy
            rms = m.get("rms_noise") or m.get("noise_jy")
            rms_values.append(rms * 1000)  # Convert to mJy

    if not timestamps:
        logger.warning("No RMS data to plot")
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: RMS time series
    ax = axes[0]
    ax.plot(timestamps, rms_values, "o-", color="steelblue", alpha=0.7, markersize=5, linewidth=2)

    # Add median and percentile lines
    median_rms = np.median(rms_values)
    p25 = np.percentile(rms_values, 25)
    p75 = np.percentile(rms_values, 75)

    ax.axhline(
        median_rms,
        color="green",
        linestyle="--",
        linewidth=2,
        label=f"Median: {median_rms:.2f} mJy",
    )
    ax.axhline(p25, color="orange", linestyle=":", alpha=0.5)
    ax.axhline(p75, color="orange", linestyle=":", alpha=0.5)
    ax.fill_between(timestamps, p25, p75, alpha=0.2, color="orange", label="25-75th percentile")

    ax.set_ylabel("RMS Noise (mJy/beam)", fontsize=12)
    ax.set_title("RMS Noise Over Time", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend()

    # Plot 2: RMS distribution
    ax = axes[1]
    ax.hist(rms_values, bins=20, color="steelblue", alpha=0.7, edgecolor="black")
    ax.axvline(
        median_rms,
        color="green",
        linestyle="--",
        linewidth=2,
        label=f"Median: {median_rms:.2f} mJy",
    )

    ax.set_xlabel("RMS Noise (mJy/beam)", fontsize=12)
    ax.set_ylabel("Number of Mosaics", fontsize=12)
    ax.set_title("RMS Noise Distribution", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend()

    # Add statistics
    stats_text = (
        f"N = {len(rms_values)} mosaics\n"
        f"Mean: {np.mean(rms_values):.2f} mJy\n"
        f"Median: {median_rms:.2f} mJy\n"
        f"Std: {np.std(rms_values):.2f} mJy\n"
        f"Min: {np.min(rms_values):.2f} mJy\n"
        f"Max: {np.max(rms_values):.2f} mJy"
    )
    ax.text(
        0.98,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.7),
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved mosaic RMS trends to %s", output_path)
    return output_path


def plot_mosaic_dynamic_range_trends(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Mosaic Dynamic Range Trends",
) -> Path:
    """Plot dynamic range trends over time.

    Args:
        metrics: List of mosaic metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    from datetime import datetime

    # Extract data
    timestamps = []
    dynamic_ranges = []
    peak_fluxes = []

    for m in metrics:
        dr = m.get("dynamic_range")
        peak = m.get("peak_flux")

        if dr is not None:
            timestamps.append(datetime.fromtimestamp(m["created_at"]))
            dynamic_ranges.append(dr)
            if peak:
                peak_fluxes.append(peak * 1000)  # Convert to mJy
            else:
                peak_fluxes.append(None)

    if not timestamps:
        logger.warning("No dynamic range data to plot")
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Dynamic range time series
    ax = axes[0]
    ax.semilogy(
        timestamps, dynamic_ranges, "o-", color="purple", alpha=0.7, markersize=5, linewidth=2
    )

    median_dr = np.median(dynamic_ranges)
    ax.axhline(
        median_dr, color="red", linestyle="--", linewidth=2, label=f"Median: {median_dr:.0f}"
    )

    ax.set_ylabel("Dynamic Range", fontsize=12)
    ax.set_title("Dynamic Range Over Time", fontweight="bold")
    ax.grid(True, alpha=0.3, which="both")
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend()

    # Plot 2: Peak flux vs dynamic range scatter
    ax = axes[1]

    # Filter out None values
    valid_data = [(p, d) for p, d in zip(peak_fluxes, dynamic_ranges) if p is not None]
    if valid_data:
        peaks, drs = zip(*valid_data)
        scatter = ax.scatter(
            peaks,
            drs,
            c=range(len(peaks)),
            cmap="viridis",
            s=80,
            alpha=0.7,
            edgecolors="black",
            linewidths=0.5,
        )

        ax.set_xlabel("Peak Flux (mJy/beam)", fontsize=12)
        ax.set_ylabel("Dynamic Range", fontsize=12)
        ax.set_title("Peak Flux vs Dynamic Range", fontweight="bold")
        ax.set_yscale("log")
        ax.grid(True, alpha=0.3, which="both")

        # Add colorbar for time
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("Mosaic Index (time →)", fontsize=10)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved mosaic dynamic range trends to %s", output_path)
    return output_path


def plot_mosaic_source_count_trends(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Mosaic Source Count Trends",
) -> Path:
    """Plot source count trends over time.

    Args:
        metrics: List of mosaic metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    from datetime import datetime

    # Extract data
    timestamps = []
    source_counts = []
    image_counts = []

    for m in metrics:
        if m.get("source_count") is not None:
            timestamps.append(datetime.fromtimestamp(m["created_at"]))
            source_counts.append(m["source_count"])
            image_counts.append(m.get("image_count") or 0)

    if not timestamps:
        logger.warning("No source count data to plot")
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Source count time series
    ax = axes[0]
    ax.plot(
        timestamps,
        source_counts,
        "o-",
        color="forestgreen",
        alpha=0.7,
        markersize=5,
        linewidth=2,
        label="Source Count",
    )

    median_sources = np.median(source_counts)
    ax.axhline(
        median_sources,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Median: {median_sources:.0f} sources",
    )

    ax.set_ylabel("Number of Sources", fontsize=12)
    ax.set_title("Detected Sources Over Time", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend()

    # Plot 2: Sources per image (density)
    ax = axes[1]

    sources_per_image = []
    for sc, ic in zip(source_counts, image_counts):
        if ic > 0:
            sources_per_image.append(sc / ic)
        else:
            sources_per_image.append(0)

    ax.plot(
        timestamps, sources_per_image, "o-", color="darkblue", alpha=0.7, markersize=5, linewidth=2
    )

    if sources_per_image:
        median_density = np.median([s for s in sources_per_image if s > 0])
        ax.axhline(
            median_density,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Median: {median_density:.1f} sources/image",
        )
        ax.legend()

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Sources per Image", fontsize=12)
    ax.set_title("Source Density (Sources/Image)", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved mosaic source count trends to %s", output_path)
    return output_path


def plot_mosaic_success_rate(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Mosaic Creation Success Rate",
    window_hours: int = 24,
) -> Path:
    """Plot mosaic creation success rate over time.

    Args:
        metrics: List of mosaic metric dicts
        output_path: Path to save the plot
        title: Plot title
        window_hours: Window size for rate calculation

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    from collections import Counter
    from datetime import datetime

    # Build time windows
    min_time = min(m["created_at"] for m in metrics)
    max_time = max(m["created_at"] for m in metrics)

    window_seconds = window_hours * 3600
    window_starts = np.arange(min_time, max_time + window_seconds, window_seconds)
    window_times = [datetime.fromtimestamp(t) for t in window_starts]

    # Count statuses in each window
    completed_counts = []
    failed_counts = []
    success_rates = []

    for window_start in window_starts:
        window_end = window_start + window_seconds

        window_mosaics = [m for m in metrics if window_start <= m["created_at"] < window_end]

        status_counts = Counter(m.get("status", "unknown") for m in window_mosaics)

        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        total = len(window_mosaics)

        completed_counts.append(completed)
        failed_counts.append(failed)

        if total > 0:
            success_rates.append(100 * completed / total)
        else:
            success_rates.append(None)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Success rate percentage
    ax = axes[0]

    # Filter out None values for plotting
    valid_times = [t for t, r in zip(window_times, success_rates) if r is not None]
    valid_rates = [r for r in success_rates if r is not None]

    if valid_times:
        ax.plot(valid_times, valid_rates, "o-", color="green", alpha=0.7, markersize=5, linewidth=2)

        mean_rate = np.mean(valid_rates)
        ax.axhline(
            mean_rate, color="red", linestyle="--", linewidth=2, label=f"Mean: {mean_rate:.1f}%"
        )
        ax.axhline(90, color="orange", linestyle=":", alpha=0.5, label="90% threshold")

    ax.set_ylabel("Success Rate (%)", fontsize=12)
    ax.set_title(f"Success Rate ({window_hours}h windows)", fontweight="bold")
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend()

    # Plot 2: Stacked bar of success vs failure
    ax = axes[1]

    ax.bar(window_times, completed_counts, label="Completed", color="green", alpha=0.7)
    ax.bar(
        window_times, failed_counts, bottom=completed_counts, label="Failed", color="red", alpha=0.7
    )

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Number of Mosaics", fontsize=12)
    ax.set_title("Mosaic Creation Outcomes", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend()

    # Add statistics
    total_completed = sum(completed_counts)
    total_failed = sum(failed_counts)
    overall_rate = (
        100 * total_completed / (total_completed + total_failed)
        if (total_completed + total_failed) > 0
        else 0
    )

    stats_text = (
        f"Total mosaics: {len(metrics)}\n"
        f"Completed: {total_completed}\n"
        f"Failed: {total_failed}\n"
        f"Overall success: {overall_rate:.1f}%"
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

    logger.info("Saved mosaic success rate to %s", output_path)
    return output_path


def generate_mosaic_quality_dashboard(
    products_db: Path,
    output_dir: Path,
    hours: int = 168,  # 7 days
) -> Dict[str, Path]:
    """Generate complete mosaic quality monitoring dashboard.

    Args:
        products_db: Path to the products database
        output_dir: Directory to save plots
        hours: Number of hours of history to include

    Returns:
        Dict mapping plot names to their file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch mosaic metrics
    metrics = fetch_mosaic_quality_metrics(products_db, hours=hours)

    plots = {}

    if metrics:
        # RMS trends
        plot_path = plot_mosaic_rms_trends(metrics, output_dir / "mosaic_rms_trends.png")
        if plot_path:
            plots["rms_trends"] = plot_path

        # Dynamic range trends
        plot_path = plot_mosaic_dynamic_range_trends(
            metrics, output_dir / "mosaic_dynamic_range_trends.png"
        )
        if plot_path:
            plots["dynamic_range"] = plot_path

        # Source count trends
        plot_path = plot_mosaic_source_count_trends(
            metrics, output_dir / "mosaic_source_count_trends.png"
        )
        if plot_path:
            plots["source_counts"] = plot_path

        # Success rate
        plot_path = plot_mosaic_success_rate(metrics, output_dir / "mosaic_success_rate.png")
        if plot_path:
            plots["success_rate"] = plot_path

    logger.info("Generated %d mosaic quality monitoring plots", len(plots))
    return plots


if __name__ == "__main__":
    # CLI for testing
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate mosaic quality monitoring visualizations"
    )
    parser.add_argument(
        "--products-db",
        type=Path,
        default=Path("/data/dsa110-contimg/state/products.sqlite3"),
        help="Path to products database",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/dsa110-contimg/qa_outputs/mosaic_quality"),
        help="Output directory for plots",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=168,
        help="Hours of history to plot (default: 168 = 7 days)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    plots = generate_mosaic_quality_dashboard(args.products_db, args.output_dir, hours=args.hours)

    print("\nGenerated plots:")
    for name, path in plots.items():
        print(f"  {name}: {path}")
