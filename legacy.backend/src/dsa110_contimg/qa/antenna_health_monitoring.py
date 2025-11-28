"""
Antenna health monitoring visualizations for long-term tracking.

This module generates visualizations for:
- Antenna health heatmap (time × antenna)
- Per-antenna stability trends
- Reference antenna stability report

Data is aggregated from per-MS QA metrics stored in the products database.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.dates import DateFormatter

matplotlib.use("Agg")  # Non-interactive backend

logger = logging.getLogger(__name__)


def fetch_antenna_qa_history(
    products_db: Path,
    hours: int = 24,
) -> List[Dict]:
    """Fetch antenna QA metrics from the products database.

    This looks for qa_artifacts that contain per-antenna metrics
    (typically from fast_plots.py).

    Args:
        products_db: Path to the products database
        hours: Number of hours of history to fetch

    Returns:
        List of dicts with antenna metrics
    """
    if not products_db.exists():
        logger.warning("Products database not found: %s", products_db)
        return []

    conn = sqlite3.connect(str(products_db), timeout=30.0)
    conn.row_factory = sqlite3.Row

    import time

    cutoff_time = time.time() - (hours * 3600) if hours > 0 else 0

    try:
        # Look for refant_ranking.json artifacts
        cursor = conn.execute(
            """
            SELECT group_id, name, path, created_at
            FROM qa_artifacts
            WHERE name LIKE '%refant_ranking%' AND created_at > ?
            ORDER BY created_at ASC
            """,
            (cutoff_time,),
        )

        artifacts = cursor.fetchall()

    finally:
        conn.close()

    # Parse the JSON files to extract antenna metrics
    metrics_list = []

    for artifact in artifacts:
        json_path = Path(artifact["path"])
        if not json_path.exists():
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Add metadata
            data["group_id"] = artifact["group_id"]
            data["timestamp"] = artifact["created_at"]
            metrics_list.append(data)

        except Exception:  # pylint: disable=broad-except
            logger.warning("Failed to parse %s", json_path)
            continue

    return metrics_list


def plot_antenna_health_heatmap(
    antenna_metrics: List[Dict],
    output_path: Path,
    title: str = "Antenna Health Heatmap (Time × Antenna)",
) -> Path:
    """Create a heatmap showing antenna health over time.

    Uses the 'score' field from refant ranking data where available.
    Higher score = better antenna health.

    Args:
        antenna_metrics: List of antenna metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not antenna_metrics:
        logger.warning("No antenna metrics to plot")
        return None

    from datetime import datetime

    # Extract antenna IDs and timestamps
    antenna_ids = set()
    for metrics in antenna_metrics:
        if "rankings" in metrics:
            for entry in metrics["rankings"]:
                antenna_ids.add(entry["antenna"])

    if not antenna_ids:
        logger.warning("No antenna data found in metrics")
        return None  # pylint: disable=used-before-assignment

    antenna_ids = sorted(antenna_ids)
    timestamps = [datetime.fromtimestamp(m["timestamp"]) for m in antenna_metrics]

    # Build the heatmap matrix
    # Rows = antennas, Columns = time points
    health_matrix = np.full((len(antenna_ids), len(antenna_metrics)), np.nan)

    for j, metrics in enumerate(antenna_metrics):
        if "rankings" not in metrics:
            continue

        for entry in metrics["rankings"]:
            ant = entry["antenna"]
            score = entry.get("score", 0)

            i = antenna_ids.index(ant)
            health_matrix[i, j] = score

    _, ax = plt.subplots(figsize=(16, max(8, len(antenna_ids) * 0.25)))

    # Create custom colormap (red = bad, yellow = ok, green = good)
    colors = ["darkred", "red", "orange", "yellow", "yellowgreen", "green", "darkgreen"]
    n_bins = 100
    cmap = LinearSegmentedColormap.from_list("health", colors, N=n_bins)

    # Plot heatmap
    im = ax.imshow(
        health_matrix, aspect="auto", cmap=cmap, interpolation="nearest", vmin=0, vmax=100
    )

    # Set ticks
    ax.set_xticks(range(len(timestamps)))
    ax.set_xticklabels(
        [t.strftime("%H:%M") for t in timestamps], rotation=45, ha="right", fontsize=8
    )

    ax.set_yticks(range(len(antenna_ids)))
    ax.set_yticklabels(antenna_ids, fontsize=8)

    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Antenna ID", fontsize=12)
    ax.set_title(title, fontsize=16, fontweight="bold")

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Health Score (0-100)", fontsize=12)

    # Add grid
    ax.set_xticks(np.arange(len(timestamps)) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(antenna_ids)) - 0.5, minor=True)
    ax.grid(which="minor", color="gray", linestyle="-", linewidth=0.5, alpha=0.3)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved antenna health heatmap to %s", output_path)
    return output_path


def plot_per_antenna_stability_trends(
    antenna_metrics: List[Dict],
    output_path: Path,
    top_n: int = 10,
    title: str = "Per-Antenna Stability Trends",
) -> Path:
    """Plot stability metrics for top antennas over time.

    Args:
        antenna_metrics: List of antenna metric dicts
        output_path: Path to save the plot
        top_n: Number of top antennas to plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not antenna_metrics:
        logger.warning("No antenna metrics to plot")
        return None

    # Collect time series for each antenna
    from collections import defaultdict
    from datetime import datetime

    antenna_scores = defaultdict(list)
    antenna_times = defaultdict(list)

    for metrics in antenna_metrics:
        timestamp = datetime.fromtimestamp(metrics["timestamp"])

        if "rankings" not in metrics:
            continue

        for entry in metrics["rankings"]:
            ant = entry["antenna"]
            score = entry.get("score", 0)

            antenna_scores[ant].append(score)
            antenna_times[ant].append(timestamp)

    if not antenna_scores:
        logger.warning("No antenna score data found")
        return None

    # Calculate mean score for each antenna to identify top performers
    antenna_means = {ant: np.mean(scores) for ant, scores in antenna_scores.items()}

    # Get top N antennas by mean score
    top_antennas = sorted(antenna_means.items(), key=lambda x: x[1], reverse=True)[:top_n]

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Top antennas time series
    ax = axes[0]
    # pylint: disable=no-member
    colors = plt.cm.tab10(np.linspace(0, 1, top_n))

    for i, (ant, mean_score) in enumerate(top_antennas):
        times = antenna_times[ant]
        scores = antenna_scores[ant]
        ax.plot(
            times,
            scores,
            "o-",
            label=f"Ant {ant} (μ={mean_score:.1f})",
            color=colors[i],
            alpha=0.7,
            markersize=3,
        )

    ax.set_ylabel("Health Score", fontsize=12)
    ax.set_title(f"Top {top_n} Antennas by Mean Score", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=9)

    # Plot 2: Score variance (stability indicator)
    ax = axes[1]

    # Calculate variance for all antennas
    antenna_vars = {ant: np.var(scores) for ant, scores in antenna_scores.items()}

    # Sort by variance (lower = more stable)
    sorted_vars = sorted(antenna_vars.items(), key=lambda x: x[1])

    antennas = [ant for ant, _ in sorted_vars]
    variances = [var for _, var in sorted_vars]

    # Color code by mean score
    colors_variance = [antenna_means[ant] for ant in antennas]

    _ = ax.scatter(
        range(len(antennas)),
        variances,
        c=colors_variance,
        cmap="RdYlGn",
        s=50,
        alpha=0.7,
        edgecolors="black",
        linewidths=0.5,
    )

    ax.set_xlabel("Antenna (sorted by stability)", fontsize=12)
    ax.set_ylabel("Score Variance", fontsize=12)
    ax.set_title("Antenna Stability (lower variance = more stable)", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # Only show every Nth antenna label to avoid crowding
    step = max(1, len(antennas) // 20)
    ax.set_xticks(range(0, len(antennas), step))
    ax.set_xticklabels(
        [antennas[i] for i in range(0, len(antennas), step)], rotation=45, ha="right", fontsize=8
    )

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Mean Health Score", fontsize=10)

    # Highlight most stable antennas
    n_stable = 5
    stable_antennas = antennas[:n_stable]
    stable_text = f"Most stable: {', '.join(map(str, stable_antennas))}"
    ax.text(
        0.02,
        0.98,
        stable_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.7),
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved antenna stability trends to %s", output_path)
    return output_path


def generate_refant_stability_report(
    antenna_metrics: List[Dict],
    output_path: Path,
    title: str = "Reference Antenna Stability Report",
) -> Path:
    """Generate comprehensive reference antenna stability report.

    Analyzes which antennas would make the best reference antennas
    based on stability and performance over time.

    Args:
        antenna_metrics: List of antenna metric dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not antenna_metrics:
        logger.warning("No antenna metrics to plot")
        return None

    from collections import defaultdict

    # Collect metrics for each antenna
    antenna_data = defaultdict(
        lambda: {"scores": [], "mean_amps": [], "phase_stds": [], "flagged_fracs": []}
    )

    for metrics in antenna_metrics:
        if "rankings" not in metrics:
            continue

        for entry in metrics["rankings"]:
            ant = entry["antenna"]
            antenna_data[ant]["scores"].append(entry.get("score", 0))

            # Additional metrics if available
            if "mean_amp" in entry:
                antenna_data[ant]["mean_amps"].append(entry["mean_amp"])
            if "phase_std" in entry:
                antenna_data[ant]["phase_stds"].append(entry["phase_std"])
            if "flagged_frac" in entry:
                antenna_data[ant]["flagged_fracs"].append(entry["flagged_frac"])

    if not antenna_data:
        logger.warning("No antenna data for report")
        return None

    # Calculate statistics for each antenna
    antenna_stats = {}
    for ant, data in antenna_data.items():
        scores = np.array(data["scores"])
        antenna_stats[ant] = {
            "mean_score": np.mean(scores),
            "std_score": np.std(scores),
            "min_score": np.min(scores),
            "max_score": np.max(scores),
            "cv": np.std(scores) / np.mean(scores) if np.mean(scores) > 0 else np.inf,
            "n_obs": len(scores),
        }

        # Add additional metrics if available
        if data["mean_amps"]:
            antenna_stats[ant]["mean_amp"] = np.mean(data["mean_amps"])
        if data["phase_stds"]:
            antenna_stats[ant]["mean_phase_std"] = np.mean(data["phase_stds"])
        if data["flagged_fracs"]:
            antenna_stats[ant]["mean_flagged"] = np.mean(data["flagged_fracs"])

    # Rank antennas for refant suitability
    # Good refants have: high mean score, low std (stable), low CV
    antenna_ranks = sorted(
        antenna_stats.items(), key=lambda x: (x[1]["mean_score"], -x[1]["cv"]), reverse=True
    )

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Mean score vs stability (CV)
    ax1 = fig.add_subplot(gs[0, 0])

    antennas = list(antenna_stats.keys())
    mean_scores = [antenna_stats[ant]["mean_score"] for ant in antennas]
    cvs = [antenna_stats[ant]["cv"] for ant in antennas]

    _ = ax1.scatter(mean_scores, cvs, s=80, alpha=0.6, edgecolors="black", linewidths=1)

    # Label top candidates
    top_5 = antenna_ranks[:5]
    for ant, ant_stats in top_5:
        ax1.annotate(
            f"{ant}",
            xy=(ant_stats["mean_score"], ant_stats["cv"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
        )

    ax1.set_xlabel("Mean Health Score", fontsize=12)
    ax1.set_ylabel("Coefficient of Variation (lower = more stable)", fontsize=12)
    ax1.set_title("RefAnt Candidate Selection", fontweight="bold")
    ax1.grid(True, alpha=0.3)

    # Add quadrant lines
    median_score = np.median(mean_scores)
    median_cv = np.median(cvs)
    ax1.axvline(median_score, color="gray", linestyle="--", alpha=0.5)
    ax1.axhline(median_cv, color="gray", linestyle="--", alpha=0.5)

    # Annotate quadrants
    ax1.text(
        0.98,
        0.02,
        "High Score\nLow Stability",
        transform=ax1.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        style="italic",
        alpha=0.6,
    )
    ax1.text(
        0.98,
        0.98,
        "High Score\nHigh Stability\n(BEST)",
        transform=ax1.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        style="italic",
        alpha=0.6,
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.3),
    )

    # Plot 2: Top 10 candidates bar chart
    ax2 = fig.add_subplot(gs[0, 1])

    top_10 = antenna_ranks[:10]
    ant_names = [str(ant) for ant, _ in top_10]
    scores = [stats["mean_score"] for _, stats in top_10]

    bars = ax2.barh(ant_names, scores, color="steelblue", alpha=0.7)
    ax2.set_xlabel("Mean Health Score", fontsize=12)
    ax2.set_title("Top 10 RefAnt Candidates", fontweight="bold")
    ax2.grid(True, alpha=0.3, axis="x")
    ax2.invert_yaxis()

    # Color code the top 3
    for i in range(min(3, len(bars))):
        bars[i].set_color(["gold", "silver", "#CD7F32"][i])

    # Plot 3: Score distribution histogram
    ax3 = fig.add_subplot(gs[1, 0])

    all_scores = []
    for data in antenna_data.values():
        all_scores.extend(data["scores"])

    ax3.hist(all_scores, bins=30, color="skyblue", alpha=0.7, edgecolor="black")
    ax3.set_xlabel("Health Score", fontsize=12)
    ax3.set_ylabel("Frequency", fontsize=12)
    ax3.set_title("Overall Score Distribution", fontweight="bold")
    ax3.grid(True, alpha=0.3, axis="y")

    # Add statistics
    stats_text = (
        f"Mean: {np.mean(all_scores):.1f}\n"
        f"Median: {np.median(all_scores):.1f}\n"
        f"Std: {np.std(all_scores):.1f}"
    )
    ax3.text(
        0.02,
        0.98,
        stats_text,
        transform=ax3.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.7),
    )

    # Plot 4: Observation count per antenna
    ax4 = fig.add_subplot(gs[1, 1])

    n_obs = [antenna_stats[ant]["n_obs"] for ant in antennas]

    ax4.hist(n_obs, bins=20, color="lightcoral", alpha=0.7, edgecolor="black")
    ax4.set_xlabel("Number of Observations", fontsize=12)
    ax4.set_ylabel("Number of Antennas", fontsize=12)
    ax4.set_title("Observation Coverage per Antenna", fontweight="bold")
    ax4.grid(True, alpha=0.3, axis="y")

    # Plot 5: Recommended RefAnt List (text)
    ax5 = fig.add_subplot(gs[2, :])
    ax5.axis("off")

    # Create recommendation table
    table_data = []
    table_data.append(["Rank", "Antenna", "Mean Score", "Std", "CV", "N Obs", "Recommendation"])

    for i, (ant, stats) in enumerate(antenna_ranks[:15], 1):
        if i <= 3:
            rec = "★★★ EXCELLENT"
        elif i <= 8:
            rec = "★★ GOOD"
        else:
            rec = "★ ACCEPTABLE"

        table_data.append(
            [
                str(i),
                str(ant),
                f"{stats['mean_score']:.1f}",
                f"{stats['std_score']:.1f}",
                f"{stats['cv']:.3f}",
                str(stats["n_obs"]),
                rec,
            ]
        )

    # Create table
    table = ax5.table(cellText=table_data, cellLoc="center", loc="center", bbox=[0, 0, 1, 1])

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Style header row
    for i in range(7):
        cell = table[(0, i)]
        cell.set_facecolor("#4CAF50")
        cell.set_text_props(weight="bold", color="white")

    # Color code rows
    for i in range(1, min(4, len(table_data))):
        for j in range(7):
            table[(i, j)].set_facecolor("#FFD700")  # Gold

    for i in range(4, min(9, len(table_data))):
        for j in range(7):
            table[(i, j)].set_facecolor("#C0C0C0")  # Silver

    ax5.set_title(
        "Recommended Reference Antennas (Ranked by Suitability)",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved refant stability report to %s", output_path)
    return output_path


def generate_antenna_health_dashboard(
    products_db: Path,
    output_dir: Path,
    hours: int = 24,
) -> Dict[str, Path]:
    """Generate complete antenna health monitoring dashboard.

    Args:
        products_db: Path to the products database
        output_dir: Directory to save plots
        hours: Number of hours of history to include

    Returns:
        Dict mapping plot names to their file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch antenna metrics
    antenna_metrics = fetch_antenna_qa_history(products_db, hours=hours)

    generated_plots = {}

    if antenna_metrics:
        # Health heatmap
        plot_path = plot_antenna_health_heatmap(
            antenna_metrics, output_dir / "antenna_health_heatmap.png"
        )
        if plot_path:
            generated_plots["antenna_heatmap"] = plot_path

        # Stability trends
        plot_path = plot_per_antenna_stability_trends(
            antenna_metrics, output_dir / "antenna_stability_trends.png"
        )
        if plot_path:
            generated_plots["antenna_stability"] = plot_path

        # RefAnt report
        plot_path = generate_refant_stability_report(
            antenna_metrics, output_dir / "refant_stability_report.png"
        )
        if plot_path:
            generated_plots["refant_report"] = plot_path

    logger.info("Generated %d antenna health monitoring plots", len(generated_plots))
    return generated_plots


if __name__ == "__main__":
    # CLI for testing
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate antenna health monitoring visualizations"
    )
    parser.add_argument(
        "--products-db",
        type=Path,
        default=Path("/data/dsa110-contimg/state/db/products.sqlite3"),
        help="Path to products database",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/dsa110-contimg/qa_outputs/antenna_health"),
        help="Output directory for plots",
    )
    parser.add_argument("--hours", type=int, default=24, help="Hours of history to plot")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    plots = generate_antenna_health_dashboard(args.products_db, args.output_dir, hours=args.hours)

    print("\nGenerated plots:")
    for name, path in plots.items():
        print(f"  {name}: {path}")
