"""
Calibration quality monitoring visualizations.

This module generates trend plots for:
- SNR (Signal-to-Noise Ratio) trends over time
- Solution convergence metrics
- Flagging statistics
- Per-antenna calibration stability

Data is read from the calibration_qa table in the products database.
"""

from __future__ import annotations

import json
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


def fetch_calibration_quality_metrics(
    products_db: Path,
    hours: int = 168,  # Default 7 days
) -> List[Dict]:
    """Fetch calibration quality metrics from the products database.

    Args:
        products_db: Path to the products database
        hours: Number of hours of history to fetch

    Returns:
        List of dicts with calibration metrics
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
                ms_path,
                job_id,
                k_metrics,
                bp_metrics,
                g_metrics,
                overall_quality,
                flags_total,
                per_spw_stats,
                timestamp
            FROM calibration_qa
            WHERE timestamp > ?
            ORDER BY timestamp ASC
            """,
            (cutoff_time,),
        )

        rows = cursor.fetchall()

        metrics = []
        for row in rows:
            metric = dict(row)

            # Parse JSON fields
            for json_field in ["k_metrics", "bp_metrics", "g_metrics", "per_spw_stats"]:
                if metric.get(json_field):
                    try:
                        metric[json_field] = json.loads(metric[json_field])
                    except Exception:  # pylint: disable=broad-except
                        metric[json_field] = None

            metrics.append(metric)

        return metrics

    finally:
        conn.close()


def plot_calibration_snr_trends(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Calibration SNR Trends",
) -> Path:
    """Plot SNR trends for different calibration types.

    Args:
        metrics: List of calibration metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    from datetime import datetime

    # Extract SNR data for each calibration type
    timestamps = []
    k_snrs = []
    bp_snrs = []
    g_snrs = []

    for m in metrics:
        timestamp = datetime.fromtimestamp(m["timestamp"])

        # K calibration SNR
        if m.get("k_metrics") and isinstance(m["k_metrics"], dict):
            k_snr = m["k_metrics"].get("mean_snr")
            if k_snr is not None:
                timestamps.append(timestamp)
                k_snrs.append(k_snr)

        # Bandpass SNR
        if m.get("bp_metrics") and isinstance(m["bp_metrics"], dict):
            bp_snr = m["bp_metrics"].get("mean_snr")
            if bp_snr is not None:
                if timestamp not in timestamps:
                    timestamps.append(timestamp)
                bp_snrs.append((timestamp, bp_snr))

        # Gain SNR
        if m.get("g_metrics") and isinstance(m["g_metrics"], dict):
            g_snr = m["g_metrics"].get("mean_snr")
            if g_snr is not None:
                if timestamp not in timestamps:
                    timestamps.append(timestamp)
                g_snrs.append((timestamp, g_snr))

    # Organize data by timestamp
    bp_data = {}
    g_data = {}
    for ts, snr in bp_snrs:
        bp_data[ts] = snr
    for ts, snr in g_snrs:
        g_data[ts] = snr

    # Get unique sorted timestamps
    all_timestamps = sorted(set(timestamps))

    if not all_timestamps:
        logger.warning("No SNR data to plot")
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: SNR time series for all calibration types
    ax = axes[0]

    if bp_data:
        bp_times = sorted(bp_data.keys())
        bp_values = [bp_data[t] for t in bp_times]
        ax.plot(
            bp_times, bp_values, "o-", label="Bandpass (BP)", color="blue", alpha=0.7, markersize=4
        )

    if g_data:
        g_times = sorted(g_data.keys())
        g_values = [g_data[t] for t in g_times]
        ax.plot(g_times, g_values, "s-", label="Gain (G)", color="green", alpha=0.7, markersize=4)

    if k_snrs:
        k_times = timestamps[: len(k_snrs)]
        ax.plot(k_times, k_snrs, "^-", label="Delay (K)", color="red", alpha=0.7, markersize=4)

    ax.set_ylabel("Mean SNR", fontsize=12)
    ax.set_title("Calibration SNR Over Time", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend()

    # Plot 2: SNR distributions
    ax = axes[1]

    snr_data = []
    labels = []
    colors = []

    if bp_data:
        snr_data.append(list(bp_data.values()))
        labels.append("Bandpass")
        colors.append("blue")

    if g_data:
        snr_data.append(list(g_data.values()))
        labels.append("Gain")
        colors.append("green")

    if k_snrs:
        snr_data.append(k_snrs)
        labels.append("Delay")
        colors.append("red")

    if snr_data:
        bp_violin = ax.violinplot(
            snr_data, positions=range(len(snr_data)), showmeans=True, showmedians=True
        )

        # Color the violins
        for i, pc in enumerate(bp_violin["bodies"]):
            pc.set_facecolor(colors[i])
            pc.set_alpha(0.7)

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_ylabel("SNR", fontsize=12)
        ax.set_title("SNR Distribution by Calibration Type", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # Add statistics
        stats_lines = []
        for label, data in zip(labels, snr_data):
            median = np.median(data)
            stats_lines.append(f"{label}: med={median:.1f}, n={len(data)}")

        ax.text(
            0.02,
            0.98,
            "\n".join(stats_lines),
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.7),
        )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved calibration SNR trends to %s", output_path)
    return output_path


def plot_calibration_convergence(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Calibration Convergence Metrics",
) -> Path:
    """Plot convergence metrics (iteration counts, chi-squared).

    Args:
        metrics: List of calibration metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    from datetime import datetime

    # Extract convergence data
    timestamps = []
    bp_iterations = []
    g_iterations = []
    chi2_values = []

    for m in metrics:
        timestamp = datetime.fromtimestamp(m["timestamp"])

        # Bandpass iterations
        if m.get("bp_metrics") and isinstance(m["bp_metrics"], dict):
            iters = m["bp_metrics"].get("iterations")
            if iters is not None:
                timestamps.append(timestamp)
                bp_iterations.append((timestamp, iters))

        # Gain iterations
        if m.get("g_metrics") and isinstance(m["g_metrics"], dict):
            iters = m["g_metrics"].get("iterations")
            chi2 = m["g_metrics"].get("chi2_reduced")
            if iters is not None:
                if timestamp not in timestamps:
                    timestamps.append(timestamp)
                g_iterations.append((timestamp, iters))
            if chi2 is not None:
                chi2_values.append((timestamp, chi2))

    if not timestamps:
        logger.warning("No convergence data to plot")
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Iteration counts
    ax = axes[0]

    if bp_iterations:
        bp_times, bp_vals = zip(*bp_iterations)
        ax.plot(bp_times, bp_vals, "o-", label="Bandpass", color="blue", alpha=0.7, markersize=4)

    if g_iterations:
        g_times, g_vals = zip(*g_iterations)
        ax.plot(g_times, g_vals, "s-", label="Gain", color="green", alpha=0.7, markersize=4)

    ax.set_ylabel("Iteration Count", fontsize=12)
    ax.set_title("Solver Iterations Over Time", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend()

    # Plot 2: Reduced chi-squared
    ax = axes[1]

    if chi2_values:
        chi2_times, chi2_vals = zip(*chi2_values)
        ax.semilogy(
            chi2_times, chi2_vals, "o-", color="purple", alpha=0.7, markersize=4, linewidth=2
        )

        median_chi2 = np.median(chi2_vals)
        ax.axhline(
            median_chi2,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Median: {median_chi2:.2f}",
        )
        ax.axhline(1.0, color="green", linestyle=":", alpha=0.5, label="Ideal (χ²=1)")

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Reduced χ²", fontsize=12)
    ax.set_title("Reduced Chi-Squared (Fit Quality)", fontweight="bold")
    ax.grid(True, alpha=0.3, which="both")
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend()

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved calibration convergence to %s", output_path)
    return output_path


def plot_calibration_flagging_trends(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Calibration Flagging Trends",
) -> Path:
    """Plot flagging statistics over time.

    Args:
        metrics: List of calibration metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    from datetime import datetime

    # Extract flagging data
    timestamps = []
    total_flags = []
    spw_flag_stats = []

    for m in metrics:
        if m.get("flags_total") is not None:
            timestamps.append(datetime.fromtimestamp(m["timestamp"]))
            total_flags.append(m["flags_total"] * 100)  # Convert to percentage

            # Per-SPW flagging stats
            if m.get("per_spw_stats") and isinstance(m["per_spw_stats"], list):
                spw_flags = [spw.get("fraction_flagged", 0) * 100 for spw in m["per_spw_stats"]]
                spw_flag_stats.append(spw_flags)
            else:
                spw_flag_stats.append([])

    if not timestamps:
        logger.warning("No flagging data to plot")
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Total flagging percentage
    ax = axes[0]
    ax.plot(timestamps, total_flags, "o-", color="red", alpha=0.7, markersize=4, linewidth=2)

    median_flags = np.median(total_flags)
    ax.axhline(
        median_flags,
        color="orange",
        linestyle="--",
        linewidth=2,
        label=f"Median: {median_flags:.1f}%",
    )
    ax.axhline(50, color="red", linestyle=":", alpha=0.5, label="50% threshold")

    ax.set_ylabel("Flagged Solutions (%)", fontsize=12)
    ax.set_title("Total Flagging Percentage Over Time", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend()

    # Plot 2: Per-SPW flagging heatmap
    ax = axes[1]

    if spw_flag_stats and any(spw_flag_stats):
        # Find max SPW count
        max_spws = max(len(spw) for spw in spw_flag_stats if spw)

        # Build matrix
        flag_matrix = np.full((max_spws, len(timestamps)), np.nan)
        for j, spw_flags in enumerate(spw_flag_stats):
            for i, flag_pct in enumerate(spw_flags):
                if i < max_spws:
                    flag_matrix[i, j] = flag_pct

        im = ax.imshow(
            flag_matrix, aspect="auto", cmap="YlOrRd", interpolation="nearest", vmin=0, vmax=100
        )

        ax.set_xlabel("Calibration Index", fontsize=12)
        ax.set_ylabel("SPW ID", fontsize=12)
        ax.set_title("Per-SPW Flagging Heatmap", fontweight="bold")

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Flagged (%)", fontsize=10)
    else:
        ax.text(
            0.5,
            0.5,
            "No per-SPW data available",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=14,
            style="italic",
            color="gray",
        )
        ax.axis("off")

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved calibration flagging trends to %s", output_path)
    return output_path


def plot_calibration_quality_distribution(
    metrics: List[Dict],
    output_path: Path,
    title: str = "Calibration Quality Distribution",
) -> Path:
    """Plot overall quality grade distribution.

    Args:
        metrics: List of calibration metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not metrics:
        logger.warning("No metrics to plot")
        return None

    from collections import Counter
    from datetime import datetime

    # Extract quality grades over time
    timestamps = []
    qualities = []

    for m in metrics:
        if m.get("overall_quality"):
            timestamps.append(datetime.fromtimestamp(m["timestamp"]))
            qualities.append(m["overall_quality"])

    if not qualities:
        logger.warning("No quality data to plot")
        return None

    quality_counts = Counter(qualities)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Quality distribution pie chart
    ax = axes[0]

    quality_order = ["excellent", "good", "marginal", "poor", "unknown"]
    colors_map = {
        "excellent": "darkgreen",
        "good": "green",
        "marginal": "orange",
        "poor": "red",
        "unknown": "gray",
    }

    plot_qualities = []
    plot_counts = []
    plot_colors = []

    for q in quality_order:
        if q in quality_counts:
            plot_qualities.append(q.capitalize())
            plot_counts.append(quality_counts[q])
            plot_colors.append(colors_map[q])

    if plot_counts:
        wedges, texts, autotexts = ax.pie(
            plot_counts, labels=plot_qualities, colors=plot_colors, autopct="%1.1f%%", startangle=90
        )

        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")

    ax.set_title("Overall Quality Distribution", fontweight="bold", pad=20)

    # Plot 2: Quality over time (stacked bar)
    ax = axes[1]

    # Group by time windows (e.g., daily)
    from collections import defaultdict

    daily_quality = defaultdict(lambda: Counter())

    for timestamp, quality in zip(timestamps, qualities):
        date = timestamp.date()
        daily_quality[date][quality] += 1

    dates = sorted(daily_quality.keys())
    date_labels = [datetime.combine(d, datetime.min.time()) for d in dates]

    # Build stacked data
    quality_series = {q: [] for q in quality_order}
    for date in dates:
        for q in quality_order:
            quality_series[q].append(daily_quality[date].get(q, 0))

    # Plot stacked bars
    bottom = np.zeros(len(dates))
    for q in quality_order:
        if any(quality_series[q]):
            ax.bar(
                date_labels,
                quality_series[q],
                bottom=bottom,
                label=q.capitalize(),
                color=colors_map[q],
                alpha=0.8,
            )
            bottom += quality_series[q]

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Number of Calibrations", fontsize=12)
    ax.set_title("Quality Grades Over Time", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.legend(loc="upper left")

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved calibration quality distribution to %s", output_path)
    return output_path


def generate_calibration_quality_dashboard(
    products_db: Path,
    output_dir: Path,
    hours: int = 168,  # 7 days
) -> Dict[str, Path]:
    """Generate complete calibration quality monitoring dashboard.

    Args:
        products_db: Path to the products database
        output_dir: Directory to save plots
        hours: Number of hours of history to include

    Returns:
        Dict mapping plot names to their file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch calibration metrics
    metrics = fetch_calibration_quality_metrics(products_db, hours=hours)

    plots = {}

    if metrics:
        # SNR trends
        plot_path = plot_calibration_snr_trends(metrics, output_dir / "calibration_snr_trends.png")
        if plot_path:
            plots["snr_trends"] = plot_path

        # Convergence metrics
        plot_path = plot_calibration_convergence(
            metrics, output_dir / "calibration_convergence.png"
        )
        if plot_path:
            plots["convergence"] = plot_path

        # Flagging trends
        plot_path = plot_calibration_flagging_trends(
            metrics, output_dir / "calibration_flagging_trends.png"
        )
        if plot_path:
            plots["flagging"] = plot_path

        # Quality distribution
        plot_path = plot_calibration_quality_distribution(
            metrics, output_dir / "calibration_quality_distribution.png"
        )
        if plot_path:
            plots["quality_dist"] = plot_path

    logger.info("Generated %d calibration quality monitoring plots", len(plots))
    return plots


if __name__ == "__main__":
    # CLI for testing
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate calibration quality monitoring visualizations"
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
        default=Path("/data/dsa110-contimg/qa_outputs/calibration_quality"),
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

    plots = generate_calibration_quality_dashboard(
        args.products_db, args.output_dir, hours=args.hours
    )

    print("\nGenerated plots:")
    for name, path in plots.items():
        print(f"  {name}: {path}")
