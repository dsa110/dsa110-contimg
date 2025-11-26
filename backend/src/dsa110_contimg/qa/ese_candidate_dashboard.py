#!/opt/miniforge/envs/casa6/bin/python
"""
ESE (Extreme Scattering Event) candidate dashboard visualizations.

This module generates plots for:
- ESE candidate sky distribution
- Flux variation timeline
- Significance vs variability scatter
- Active vs investigated status
- Light curves for top candidates

Data is read from the ese_candidates and variability_stats tables.
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


def fetch_ese_candidates(
    products_db: Path,
    status: Optional[str] = "active",
    min_sigma: float = 3.0,
) -> List[Dict]:
    """Fetch ESE candidates from the database.

    Args:
        products_db: Path to the products database
        status: Filter by status ('active', 'investigated', 'dismissed', or None for all)
        min_sigma: Minimum significance threshold

    Returns:
        List of dicts with ESE candidate data
    """
    if not products_db.exists():
        logger.warning("Products database not found: %s", products_db)
        return []

    conn = sqlite3.connect(str(products_db), timeout=30.0)
    conn.row_factory = sqlite3.Row

    try:
        # Check if tables exist
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "ese_candidates" not in tables or "variability_stats" not in tables:
            logger.warning("ESE candidate tables not found")
            return []

        # Build query
        query = """
            SELECT 
                e.id,
                e.source_id,
                e.flagged_at,
                e.significance,
                e.flag_type,
                e.notes,
                e.status,
                v.ra_deg,
                v.dec_deg,
                v.nvss_flux_mjy,
                v.mean_flux_mjy,
                v.std_flux_mjy,
                v.chi2_nu,
                v.sigma_deviation,
                v.n_obs,
                v.last_measured_at
            FROM ese_candidates e
            LEFT JOIN variability_stats v ON e.source_id = v.source_id
            WHERE e.significance >= ?
        """

        params = [min_sigma]

        if status:
            query += " AND e.status = ?"
            params.append(status)

        query += " ORDER BY e.significance DESC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        candidates = []
        for row in rows:
            candidates.append(dict(row))

        return candidates

    finally:
        conn.close()


def plot_ese_sky_distribution(
    candidates: List[Dict],
    output_path: Path,
    title: str = "ESE Candidate Sky Distribution",
) -> Path:
    """Plot sky distribution of ESE candidates.

    Args:
        candidates: List of ESE candidate dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not candidates:
        logger.warning("No candidates to plot")
        return None

    fig = plt.figure(figsize=(14, 8))

    # Use RA/Dec projection
    ax = fig.add_subplot(111)

    ras = [c["ra_deg"] for c in candidates]
    decs = [c["dec_deg"] for c in candidates]
    significances = [c.get("significance", 0) for c in candidates]

    # Size by significance
    sizes = [max(20, min(200, sig * 10)) for sig in significances]

    scatter = ax.scatter(
        ras,
        decs,
        c=significances,
        s=sizes,
        cmap="YlOrRd",
        alpha=0.7,
        edgecolors="black",
        linewidths=1,
    )

    ax.set_xlabel("Right Ascension (deg)", fontsize=12)
    ax.set_ylabel("Declination (deg)", fontsize=12)
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.invert_xaxis()  # RA increases to the left

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Significance (σ)", fontsize=12)

    # Add statistics box
    stats_text = (
        f"Total candidates: {len(candidates)}\n"
        f"Mean σ: {np.mean(significances):.1f}\n"
        f"Max σ: {np.max(significances):.1f}\n"
        f"RA range: [{np.min(ras):.1f}, {np.max(ras):.1f}]°\n"
        f"Dec range: [{np.min(decs):.1f}, {np.max(decs):.1f}]°"
    )
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved ESE sky distribution to %s", output_path)
    return output_path


def plot_ese_flux_variations(
    candidates: List[Dict],
    output_path: Path,
    title: str = "ESE Candidate Flux Variations",
) -> Path:
    """Plot flux variation statistics.

    Args:
        candidates: List of ESE candidate dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not candidates:
        logger.warning("No candidates to plot")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Extract data
    baseline_flux = []
    mean_flux = []
    std_flux = []
    flux_ratios = []

    for c in candidates:
        nvss = c.get("nvss_flux_mjy")
        mean = c.get("mean_flux_mjy")
        std = c.get("std_flux_mjy")

        if nvss and mean:
            baseline_flux.append(nvss / 1000)  # Convert to Jy
            mean_flux.append(mean / 1000)
            if std:
                std_flux.append(std / 1000)
            else:
                std_flux.append(0)

            flux_ratios.append(mean / nvss)

    if not baseline_flux:
        logger.warning("No flux data to plot")
        return None

    # Plot 1: Baseline vs current flux
    ax = axes[0, 0]
    scatter = ax.scatter(
        baseline_flux,
        mean_flux,
        c=flux_ratios,
        cmap="RdYlGn_r",
        s=80,
        alpha=0.7,
        edgecolors="black",
        linewidths=0.5,
        vmin=0.5,
        vmax=1.5,
    )

    # Add 1:1 line
    min_flux = min(min(baseline_flux), min(mean_flux))
    max_flux = max(max(baseline_flux), max(mean_flux))
    ax.plot([min_flux, max_flux], [min_flux, max_flux], "k--", alpha=0.5, label="No change")

    ax.set_xlabel("NVSS Baseline Flux (Jy)", fontsize=12)
    ax.set_ylabel("Current Mean Flux (Jy)", fontsize=12)
    ax.set_title("Baseline vs Current Flux", fontweight="bold")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend()

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Flux Ratio (Current/Baseline)", fontsize=10)

    # Plot 2: Flux ratio distribution
    ax = axes[0, 1]
    ax.hist(flux_ratios, bins=20, color="steelblue", alpha=0.7, edgecolor="black")
    ax.axvline(1.0, color="red", linestyle="--", linewidth=2, label="No change")

    median_ratio = np.median(flux_ratios)
    ax.axvline(
        median_ratio,
        color="green",
        linestyle="--",
        linewidth=2,
        label=f"Median: {median_ratio:.2f}",
    )

    ax.set_xlabel("Flux Ratio (Current/Baseline)", fontsize=12)
    ax.set_ylabel("Number of Candidates", fontsize=12)
    ax.set_title("Flux Ratio Distribution", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend()

    # Plot 3: Coefficient of variation
    ax = axes[1, 0]
    cv = [std / mean if mean > 0 else 0 for std, mean in zip(std_flux, mean_flux)]

    scatter = ax.scatter(
        mean_flux, cv, s=80, alpha=0.7, c="purple", edgecolors="black", linewidths=0.5
    )

    ax.set_xlabel("Mean Flux (Jy)", fontsize=12)
    ax.set_ylabel("Coefficient of Variation (σ/μ)", fontsize=12)
    ax.set_title("Variability vs Brightness", fontweight="bold")
    ax.set_xscale("log")
    ax.grid(True, alpha=0.3, which="both")

    # Plot 4: Fractional flux change
    ax = axes[1, 1]
    frac_change = [(m - b) / b if b > 0 else 0 for b, m in zip(baseline_flux, mean_flux)]

    ax.hist(frac_change, bins=20, color="coral", alpha=0.7, edgecolor="black")
    ax.axvline(0, color="red", linestyle="--", linewidth=2)

    ax.set_xlabel("Fractional Flux Change", fontsize=12)
    ax.set_ylabel("Number of Candidates", fontsize=12)
    ax.set_title("Flux Change Distribution", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # Add statistics
    stats_text = (
        f"Median change: {np.median(frac_change):.2%}\n"
        f"Brightening: {sum(1 for x in frac_change if x > 0.1)}\n"
        f"Dimming: {sum(1 for x in frac_change if x < -0.1)}"
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

    logger.info("Saved ESE flux variations to %s", output_path)
    return output_path


def plot_ese_significance_analysis(
    candidates: List[Dict],
    output_path: Path,
    title: str = "ESE Significance Analysis",
) -> Path:
    """Plot significance vs variability metrics.

    Args:
        candidates: List of ESE candidate dicts
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    if not candidates:
        logger.warning("No candidates to plot")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Extract data
    significances = [c.get("significance", 0) for c in candidates]
    chi2_values = [c.get("chi2_nu", 0) for c in candidates if c.get("chi2_nu")]
    sigma_devs = [c.get("sigma_deviation", 0) for c in candidates if c.get("sigma_deviation")]
    n_obs = [c.get("n_obs", 0) for c in candidates]

    # Plot 1: Significance distribution
    ax = axes[0, 0]
    ax.hist(significances, bins=20, color="steelblue", alpha=0.7, edgecolor="black")

    median_sig = np.median(significances)
    ax.axvline(
        median_sig, color="red", linestyle="--", linewidth=2, label=f"Median: {median_sig:.1f}σ"
    )
    ax.axvline(5.0, color="orange", linestyle=":", alpha=0.5, label="5σ threshold")

    ax.set_xlabel("Significance (σ)", fontsize=12)
    ax.set_ylabel("Number of Candidates", fontsize=12)
    ax.set_title("Significance Distribution", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend()

    # Plot 2: Chi-squared vs significance
    ax = axes[0, 1]
    if chi2_values:
        valid_chi2_sig = [
            (chi2, sig)
            for chi2, sig in zip(chi2_values, significances[: len(chi2_values)])
            if chi2 > 0
        ]
        if valid_chi2_sig:
            chi2_plot, sig_plot = zip(*valid_chi2_sig)
            scatter = ax.scatter(
                chi2_plot, sig_plot, s=80, alpha=0.7, c="purple", edgecolors="black", linewidths=0.5
            )

            ax.set_xlabel("Reduced χ²", fontsize=12)
            ax.set_ylabel("Significance (σ)", fontsize=12)
            ax.set_title("χ² vs Significance", fontweight="bold")
            ax.set_xscale("log")
            ax.grid(True, alpha=0.3, which="both")

            # Add reference line
            ax.axvline(1.0, color="green", linestyle="--", alpha=0.5, label="χ²=1 (ideal)")
            ax.legend()

    # Plot 3: Number of observations vs significance
    ax = axes[1, 0]
    scatter = ax.scatter(
        n_obs, significances, s=80, alpha=0.7, c="forestgreen", edgecolors="black", linewidths=0.5
    )

    ax.set_xlabel("Number of Observations", fontsize=12)
    ax.set_ylabel("Significance (σ)", fontsize=12)
    ax.set_title("Observations vs Significance", fontweight="bold")
    ax.grid(True, alpha=0.3)

    # Plot 4: Sigma deviation distribution
    ax = axes[1, 1]
    if sigma_devs:
        ax.hist(sigma_devs, bins=20, color="coral", alpha=0.7, edgecolor="black")

        median_sigma = np.median(sigma_devs)
        ax.axvline(
            median_sigma,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Median: {median_sigma:.1f}σ",
        )

        ax.set_xlabel("Sigma Deviation", fontsize=12)
        ax.set_ylabel("Number of Candidates", fontsize=12)
        ax.set_title("Sigma Deviation Distribution", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        ax.legend()

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved ESE significance analysis to %s", output_path)
    return output_path


def plot_ese_status_overview(
    products_db: Path,
    output_path: Path,
    title: str = "ESE Candidate Status Overview",
) -> Path:
    """Plot overview of candidate statuses.

    Args:
        products_db: Path to the products database
        output_path: Path to save the plot
        title: Plot title

    Returns:
        Path to saved plot
    """
    from collections import Counter
    from datetime import datetime, timedelta

    # Fetch all candidates (not just active)
    all_candidates = fetch_ese_candidates(products_db, status=None, min_sigma=0)

    if not all_candidates:
        logger.warning("No candidates to plot")
        return None

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    # Plot 1: Status distribution pie chart
    ax = axes[0]

    status_counts = Counter(c.get("status", "unknown") for c in all_candidates)

    statuses = []
    counts = []
    colors = []

    status_colors = {
        "active": "red",
        "investigated": "orange",
        "dismissed": "gray",
        "unknown": "lightgray",
    }

    for status in ["active", "investigated", "dismissed", "unknown"]:
        if status in status_counts:
            statuses.append(status.capitalize())
            counts.append(status_counts[status])
            colors.append(status_colors[status])

    if counts:
        wedges, texts, autotexts = ax.pie(
            counts, labels=statuses, colors=colors, autopct="%1.1f%%", startangle=90
        )

        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")

    ax.set_title("Status Distribution", fontweight="bold", pad=20)

    # Plot 2: Detection timeline (last 30 days)
    ax = axes[1]

    # Group by day
    from collections import defaultdict

    daily_detections = defaultdict(int)

    cutoff_time = datetime.now().timestamp() - (30 * 24 * 3600)

    for c in all_candidates:
        flagged_at = c.get("flagged_at")
        if flagged_at and flagged_at > cutoff_time:
            date = datetime.fromtimestamp(flagged_at).date()
            daily_detections[date] += 1

    if daily_detections:
        dates = sorted(daily_detections.keys())
        counts = [daily_detections[d] for d in dates]
        date_labels = [datetime.combine(d, datetime.min.time()) for d in dates]

        ax.bar(date_labels, counts, color="red", alpha=0.7, edgecolor="black")

        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Candidates Detected", fontsize=12)
        ax.set_title("Detection Timeline (Last 30 Days)", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))

        # Add statistics
        total_recent = sum(counts)
        stats_text = (
            f"Total (30d): {total_recent}\n"
            f"Peak day: {max(counts)}\n"
            f"Avg/day: {np.mean(counts):.1f}"
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
    else:
        ax.text(
            0.5,
            0.5,
            "No recent detections (last 30 days)",
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

    logger.info("Saved ESE status overview to %s", output_path)
    return output_path


def generate_ese_candidate_dashboard(
    products_db: Path,
    output_dir: Path,
    min_sigma: float = 3.0,
) -> Dict[str, Path]:
    """Generate complete ESE candidate dashboard.

    Args:
        products_db: Path to the products database
        output_dir: Directory to save plots
        min_sigma: Minimum significance threshold

    Returns:
        Dict mapping plot names to their file paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch ESE candidates
    candidates = fetch_ese_candidates(products_db, status="active", min_sigma=min_sigma)

    plots = {}

    if candidates:
        # Sky distribution
        plot_path = plot_ese_sky_distribution(candidates, output_dir / "ese_sky_distribution.png")
        if plot_path:
            plots["sky_distribution"] = plot_path

        # Flux variations
        plot_path = plot_ese_flux_variations(candidates, output_dir / "ese_flux_variations.png")
        if plot_path:
            plots["flux_variations"] = plot_path

        # Significance analysis
        plot_path = plot_ese_significance_analysis(
            candidates, output_dir / "ese_significance_analysis.png"
        )
        if plot_path:
            plots["significance"] = plot_path

    # Status overview (uses all candidates, not just active)
    plot_path = plot_ese_status_overview(products_db, output_dir / "ese_status_overview.png")
    if plot_path:
        plots["status_overview"] = plot_path

    logger.info("Generated %d ESE candidate dashboard plots", len(plots))
    return plots


if __name__ == "__main__":
    # CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description="Generate ESE candidate dashboard visualizations")
    parser.add_argument(
        "--products-db",
        type=Path,
        default=Path("/data/dsa110-contimg/state/db/products.sqlite3"),
        help="Path to products database",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/dsa110-contimg/qa_outputs/ese_candidates"),
        help="Output directory for plots",
    )
    parser.add_argument(
        "--min-sigma",
        type=float,
        default=3.0,
        help="Minimum significance threshold",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    plots = generate_ese_candidate_dashboard(
        args.products_db, args.output_dir, min_sigma=args.min_sigma
    )

    print("\nGenerated plots:")
    for name, path in plots.items():
        print(f"  {name}: {path}")
