"""
Plotting utilities for validation results.

Generates diagnostic plots for astrometry, flux scale, and completeness validation.
"""

import base64
import io
import logging
from typing import List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from dsa110_contimg.qa.catalog_validation import CatalogValidationResult

matplotlib.use("Agg", force=True)  # Headless backend


logger = logging.getLogger(__name__)


def plot_astrometry_scatter(
    result: CatalogValidationResult, output_format: str = "png", dpi: int = 100
) -> Optional[str]:
    """
    Generate astrometry scatter plot showing detected vs catalog positions.

    Args:
        result: CatalogValidationResult from astrometry validation
        output_format: Image format ("png", "svg", "pdf")
        dpi: Resolution for raster formats

    Returns:
        Base64-encoded image string, or None if no matched pairs available
    """
    if not result.matched_pairs or len(result.matched_pairs) == 0:
        return None

    try:
        # Extract RA/Dec offsets from matched pairs
        # matched_pairs format: [(detected_ra, detected_dec, catalog_ra, catalog_dec, offset_arcsec), ...]
        offsets_ra = []
        offsets_dec = []
        offsets_total = []

        for pair in result.matched_pairs:
            if len(pair) >= 5:
                offset_total = pair[4]  # Total offset in arcsec
                offsets_total.append(offset_total)

                # Calculate RA/Dec offsets if not directly available
                if len(pair) >= 4:
                    detected_ra, detected_dec = pair[0], pair[1]
                    catalog_ra, catalog_dec = pair[2], pair[3]

                    # Convert to arcsec (assuming degrees)
                    offset_ra = (
                        (detected_ra - catalog_ra)
                        * 3600.0
                        * np.cos(np.radians(catalog_dec))
                    )
                    offset_dec = (detected_dec - catalog_dec) * 3600.0
                    offsets_ra.append(offset_ra)
                    offsets_dec.append(offset_dec)

        if len(offsets_total) == 0:
            return None

        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Plot 1: RA vs Dec offset scatter
        ax1.scatter(
            offsets_ra,
            offsets_dec,
            alpha=0.6,
            s=50,
            c=offsets_total,
            cmap="viridis",
            edgecolors="black",
            linewidths=0.5,
        )
        ax1.axhline(y=0, color="gray", linestyle="--", linewidth=1, alpha=0.5)
        ax1.axvline(x=0, color="gray", linestyle="--", linewidth=1, alpha=0.5)
        ax1.set_xlabel("RA Offset (arcsec)", fontsize=11)
        ax1.set_ylabel("Dec Offset (arcsec)", fontsize=11)
        ax1.set_title("Astrometric Offsets", fontsize=12, fontweight="bold")
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect("equal", adjustable="box")

        # Add colorbar
        cbar = plt.colorbar(ax1.collections[0], ax=ax1)
        cbar.set_label("Total Offset (arcsec)", fontsize=10)

        # Add statistics text
        if result.mean_offset_arcsec is not None:
            stats_text = f'Mean: {result.mean_offset_arcsec:.2f}"\n'
            stats_text += (
                f'RMS: {result.rms_offset_arcsec:.2f}"'
                if result.rms_offset_arcsec
                else ""
            )
            ax1.text(
                0.05,
                0.95,
                stats_text,
                transform=ax1.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
                fontsize=9,
            )

        # Plot 2: Offset histogram
        ax2.hist(
            offsets_total, bins=20, edgecolor="black", alpha=0.7, color="steelblue"
        )
        ax2.axvline(
            x=result.mean_offset_arcsec if result.mean_offset_arcsec else 0,
            color="red",
            linestyle="--",
            linewidth=2,
            label="Mean",
        )
        if result.rms_offset_arcsec:
            ax2.axvline(
                x=result.rms_offset_arcsec,
                color="orange",
                linestyle="--",
                linewidth=2,
                label="RMS",
            )
        ax2.set_xlabel("Total Offset (arcsec)", fontsize=11)
        ax2.set_ylabel("Number of Sources", fontsize=11)
        ax2.set_title("Offset Distribution", fontsize=12, fontweight="bold")
        ax2.grid(True, alpha=0.3, axis="y")
        ax2.legend()

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format=output_format, dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)

        return f"data:image/{output_format};base64,{img_base64}"

    except Exception as e:
        logger.error(f"Error generating astrometry plot: {e}", exc_info=True)
        return None


def plot_flux_ratio_histogram(
    result: CatalogValidationResult, output_format: str = "png", dpi: int = 100
) -> Optional[str]:
    """
    Generate flux ratio histogram plot.

    Args:
        result: CatalogValidationResult from flux scale validation
        output_format: Image format ("png", "svg", "pdf")
        dpi: Resolution for raster formats

    Returns:
        Base64-encoded image string, or None if no matched fluxes available
    """
    if not result.matched_fluxes or len(result.matched_fluxes) == 0:
        return None

    try:
        # Extract flux ratios from matched_fluxes
        # matched_fluxes format: [(detected_flux, catalog_flux, ratio), ...]
        ratios = []
        detected_fluxes = []
        catalog_fluxes = []

        for flux_pair in result.matched_fluxes:
            if len(flux_pair) >= 3:
                detected_flux, catalog_flux, ratio = (
                    flux_pair[0],
                    flux_pair[1],
                    flux_pair[2],
                )
                ratios.append(ratio)
                detected_fluxes.append(detected_flux)
                catalog_fluxes.append(catalog_flux)

        if len(ratios) == 0:
            return None

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Plot 1: Flux ratio histogram
        ax1.hist(ratios, bins=20, edgecolor="black", alpha=0.7, color="steelblue")
        ax1.axvline(
            x=1.0, color="green", linestyle="--", linewidth=2, label="Perfect (1.0)"
        )
        if result.mean_flux_ratio:
            ax1.axvline(
                x=result.mean_flux_ratio,
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Mean ({result.mean_flux_ratio:.3f})",
            )
        ax1.set_xlabel("Flux Ratio (Detected / Catalog)", fontsize=11)
        ax1.set_ylabel("Number of Sources", fontsize=11)
        ax1.set_title("Flux Ratio Distribution", fontsize=12, fontweight="bold")
        ax1.grid(True, alpha=0.3, axis="y")
        ax1.legend()

        # Add statistics text
        if result.mean_flux_ratio and result.rms_flux_ratio:
            stats_text = f"Mean: {result.mean_flux_ratio:.3f}\n"
            stats_text += f"RMS: {result.rms_flux_ratio:.3f}\n"
            if result.flux_scale_error:
                stats_text += f"Error: {result.flux_scale_error*100:.1f}%"
            ax1.text(
                0.05,
                0.95,
                stats_text,
                transform=ax1.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
                fontsize=9,
            )

        # Plot 2: Detected vs Catalog flux scatter
        if len(detected_fluxes) > 0 and len(catalog_fluxes) > 0:
            ax2.scatter(
                catalog_fluxes,
                detected_fluxes,
                alpha=0.6,
                s=50,
                edgecolors="black",
                linewidths=0.5,
            )

            # Add 1:1 line
            flux_min = min(min(catalog_fluxes), min(detected_fluxes))
            flux_max = max(max(catalog_fluxes), max(detected_fluxes))
            ax2.plot(
                [flux_min, flux_max],
                [flux_min, flux_max],
                "r--",
                linewidth=2,
                label="1:1 line",
            )

            ax2.set_xlabel("Catalog Flux (Jy)", fontsize=11)
            ax2.set_ylabel("Detected Flux (Jy)", fontsize=11)
            ax2.set_title("Detected vs Catalog Flux", fontsize=12, fontweight="bold")
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            ax2.set_aspect("equal", adjustable="box")

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format=output_format, dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)

        return f"data:image/{output_format};base64,{img_base64}"

    except Exception as e:
        logger.error(f"Error generating flux ratio plot: {e}", exc_info=True)
        return None


def plot_completeness_curve(
    result: CatalogValidationResult, output_format: str = "png", dpi: int = 100
) -> Optional[str]:
    """
    Generate completeness vs flux density curve plot.

    Args:
        result: CatalogValidationResult from source counts validation
        output_format: Image format ("png", "svg", "pdf")
        dpi: Resolution for raster formats

    Returns:
        Base64-encoded image string, or None if no completeness bins available
    """
    if (
        not result.completeness_bins_jy
        or not result.completeness_per_bin
        or not result.catalog_counts_per_bin
    ):
        return None

    try:
        # Extract data
        flux_bins = np.array(result.completeness_bins_jy) * 1000  # Convert to mJy
        # Convert to percentage
        completeness = np.array(result.completeness_per_bin) * 100
        catalog_counts = np.array(result.catalog_counts_per_bin)

        # Filter out bins with no catalog sources
        valid_mask = catalog_counts > 0
        flux_bins = flux_bins[valid_mask]
        completeness = completeness[valid_mask]
        catalog_counts = catalog_counts[valid_mask]

        if len(flux_bins) == 0:
            return None

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Plot 1: Completeness curve
        ax1.plot(
            flux_bins,
            completeness,
            "o-",
            linewidth=2,
            markersize=8,
            color="steelblue",
            label="Completeness",
        )
        ax1.axhline(
            y=95,
            color="green",
            linestyle="--",
            linewidth=2,
            label="95% threshold",
            alpha=0.7,
        )
        ax1.axhline(
            y=80,
            color="orange",
            linestyle="--",
            linewidth=1,
            label="80% threshold",
            alpha=0.5,
        )

        # Mark completeness limit if available
        if result.completeness_limit_jy:
            limit_mjy = result.completeness_limit_jy * 1000
            ax1.axvline(
                x=limit_mjy,
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Completeness limit ({limit_mjy:.2f} mJy)",
                alpha=0.7,
            )

        ax1.set_xlabel("Flux Density (mJy)", fontsize=11)
        ax1.set_ylabel("Completeness (%)", fontsize=11)
        ax1.set_title("Completeness vs Flux Density", fontsize=12, fontweight="bold")
        ax1.grid(True, alpha=0.3)
        ax1.set_xscale("log")
        ax1.set_ylim(0, 105)
        ax1.legend()

        # Add overall completeness text
        if result.completeness:
            ax1.text(
                0.05,
                0.05,
                f"Overall: {result.completeness*100:.1f}%",
                transform=ax1.transAxes,
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
                fontsize=10,
            )

        # Plot 2: Source counts per bin
        ax2.bar(
            flux_bins,
            catalog_counts,
            width=flux_bins * 0.15,
            alpha=0.7,
            color="steelblue",
            edgecolor="black",
            label="Catalog",
        )

        if result.detected_counts_per_bin:
            detected_counts = np.array(result.detected_counts_per_bin)[valid_mask]
            ax2.bar(
                flux_bins,
                detected_counts,
                width=flux_bins * 0.15,
                alpha=0.5,
                color="green",
                edgecolor="black",
                label="Detected",
            )

        ax2.set_xlabel("Flux Density (mJy)", fontsize=11)
        ax2.set_ylabel("Number of Sources", fontsize=11)
        ax2.set_title("Source Counts per Flux Bin", fontsize=12, fontweight="bold")
        ax2.grid(True, alpha=0.3, axis="y")
        ax2.set_xscale("log")
        ax2.legend()

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format=output_format, dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)

        return f"data:image/{output_format};base64,{img_base64}"

    except Exception as e:
        logger.error(f"Error generating completeness plot: {e}", exc_info=True)
        return None


def plot_spatial_distribution(
    result: CatalogValidationResult, output_format: str = "png", dpi: int = 100
) -> Optional[str]:
    """
    Generate spatial distribution plot showing matched sources on the sky.

    Useful for identifying systematic spatial biases in astrometry or flux scale.

    Args:
        result: CatalogValidationResult (works with astrometry or flux scale)
        output_format: Image format ("png", "svg", "pdf")
        dpi: Resolution for raster formats

    Returns:
        Base64-encoded image string, or None if no matched pairs available
    """
    if not result.matched_pairs or len(result.matched_pairs) == 0:
        return None

    try:
        # Extract RA/Dec positions
        detected_ras = []
        detected_decs = []
        offsets = []

        for pair in result.matched_pairs:
            if len(pair) >= 5:
                detected_ra, detected_dec = pair[0], pair[1]
                offset_arcsec = pair[4]
                detected_ras.append(detected_ra)
                detected_decs.append(detected_dec)
                offsets.append(offset_arcsec)

        if len(detected_ras) == 0:
            return None

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Plot 1: Spatial distribution colored by offset
        scatter = ax1.scatter(
            detected_ras,
            detected_decs,
            c=offsets,
            cmap="viridis",
            s=50,
            alpha=0.7,
            edgecolors="black",
            linewidths=0.5,
        )
        ax1.set_xlabel("RA (degrees)", fontsize=11)
        ax1.set_ylabel("Dec (degrees)", fontsize=11)
        ax1.set_title(
            "Spatial Distribution of Matched Sources\n(colored by offset)",
            fontsize=12,
            fontweight="bold",
        )
        ax1.grid(True, alpha=0.3)
        cbar1 = plt.colorbar(scatter, ax=ax1)
        cbar1.set_label("Offset (arcsec)", fontsize=10)

        # Plot 2: Offset vs RA (to check for systematic trends)
        ax2.scatter(
            detected_ras, offsets, alpha=0.6, s=50, edgecolors="black", linewidths=0.5
        )
        ax2.axhline(y=0, color="red", linestyle="--", linewidth=1, alpha=0.5)
        ax2.set_xlabel("RA (degrees)", fontsize=11)
        ax2.set_ylabel("Offset (arcsec)", fontsize=11)
        ax2.set_title(
            "Offset vs RA\n(check for systematic trends)",
            fontsize=12,
            fontweight="bold",
        )
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format=output_format, dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)

        return f"data:image/{output_format};base64,{img_base64}"

    except Exception as e:
        logger.error(f"Error generating spatial distribution plot: {e}", exc_info=True)
        return None


def plot_flux_vs_offset(
    astrometry_result: CatalogValidationResult,
    flux_scale_result: CatalogValidationResult,
    output_format: str = "png",
    dpi: int = 100,
) -> Optional[str]:
    """
    Generate plot showing correlation between flux and astrometric offset.

    Useful for identifying if brighter sources have better/worse astrometry.

    Args:
        astrometry_result: CatalogValidationResult from astrometry validation
        flux_scale_result: CatalogValidationResult from flux scale validation
        output_format: Image format ("png", "svg", "pdf")
        dpi: Resolution for raster formats

    Returns:
        Base64-encoded image string, or None if insufficient data
    """
    if (
        not astrometry_result.matched_pairs
        or not flux_scale_result.matched_fluxes
        or len(astrometry_result.matched_pairs) == 0
        or len(flux_scale_result.matched_fluxes) == 0
    ):
        return None

    try:
        # Extract offsets and fluxes
        # Match sources by position (simplified - assumes same sources)
        offsets = []
        fluxes = []

        # Get offsets from astrometry
        for pair in astrometry_result.matched_pairs:
            if len(pair) >= 5:
                offsets.append(pair[4])  # offset in arcsec

        # Get fluxes from flux scale
        for flux_pair in flux_scale_result.matched_fluxes:
            if len(flux_pair) >= 2:
                # Use catalog flux as reference
                fluxes.append(flux_pair[1])  # catalog flux in Jy

        # Match lengths (take minimum)
        min_len = min(len(offsets), len(fluxes))
        offsets = offsets[:min_len]
        fluxes = fluxes[:min_len]

        if len(offsets) == 0 or len(fluxes) == 0:
            return None

        # Create figure
        fig, ax = plt.subplots(figsize=(8, 6))

        # Scatter plot
        ax.scatter(fluxes, offsets, alpha=0.6, s=50, edgecolors="black", linewidths=0.5)
        ax.axhline(y=0, color="red", linestyle="--", linewidth=1, alpha=0.5)

        # Add trend line if enough points
        if len(fluxes) > 5:
            z = np.polyfit(fluxes, offsets, 1)
            p = np.poly1d(z)
            flux_sorted = sorted(fluxes)
            ax.plot(
                flux_sorted,
                p(flux_sorted),
                "r--",
                alpha=0.8,
                linewidth=2,
                label=f"Trend: {z[0]:.3f}x + {z[1]:.3f}",
            )
            ax.legend()

        ax.set_xlabel("Flux Density (Jy)", fontsize=11)
        ax.set_ylabel("Astrometric Offset (arcsec)", fontsize=11)
        ax.set_title(
            "Flux vs Astrometric Offset\n(check for flux-dependent bias)",
            fontsize=12,
            fontweight="bold",
        )
        ax.grid(True, alpha=0.3)
        ax.set_xscale("log")

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format=output_format, dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)

        return f"data:image/{output_format};base64,{img_base64}"

    except Exception as e:
        logger.error(f"Error generating flux vs offset plot: {e}", exc_info=True)
        return None


def plot_validation_summary(
    astrometry_result: Optional[CatalogValidationResult],
    flux_scale_result: Optional[CatalogValidationResult],
    source_counts_result: Optional[CatalogValidationResult],
    output_format: str = "png",
    dpi: int = 100,
) -> Optional[str]:
    """
    Generate a summary plot showing key metrics from all validation tests.

    Args:
        astrometry_result: Optional astrometry validation result
        flux_scale_result: Optional flux scale validation result
        source_counts_result: Optional source counts validation result
        output_format: Image format ("png", "svg", "pdf")
        dpi: Resolution for raster formats

    Returns:
        Base64-encoded image string
    """
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle("Validation Summary Dashboard", fontsize=14, fontweight="bold")

        # Plot 1: Astrometry metrics
        ax1 = axes[0, 0]
        if astrometry_result and astrometry_result.mean_offset_ra is not None:
            metrics = [
                (
                    "Mean RA Offset",
                    astrometry_result.mean_offset_ra * 3600,
                ),  # Convert to arcsec
                ("Mean Dec Offset", astrometry_result.mean_offset_dec * 3600),
                ("RMS Offset", astrometry_result.rms_offset_arcsec),
                ("Max Offset", astrometry_result.max_offset_arcsec),
            ]
            names, values = zip(*metrics)
            bars = ax1.barh(
                names, values, color=["steelblue", "steelblue", "orange", "red"]
            )
            ax1.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
            ax1.set_xlabel("Offset (arcsec)", fontsize=10)
            ax1.set_title("Astrometry Metrics", fontsize=11, fontweight="bold")
            ax1.grid(True, alpha=0.3, axis="x")
        else:
            ax1.text(
                0.5,
                0.5,
                "No astrometry data",
                ha="center",
                va="center",
                transform=ax1.transAxes,
            )
            ax1.set_title("Astrometry Metrics", fontsize=11, fontweight="bold")

        # Plot 2: Flux scale metrics
        ax2 = axes[0, 1]
        if flux_scale_result and flux_scale_result.mean_flux_ratio is not None:
            metrics = [
                ("Mean Ratio", flux_scale_result.mean_flux_ratio),
                ("RMS Ratio", flux_scale_result.rms_flux_ratio),
                (
                    "Error %",
                    (
                        abs(flux_scale_result.flux_scale_error * 100)
                        if flux_scale_result.flux_scale_error
                        else 0
                    ),
                ),
            ]
            names, values = zip(*metrics)
            bars = ax2.barh(names, values, color=["green", "orange", "red"])
            ax2.axvline(x=1.0, color="black", linestyle="--", linewidth=1, alpha=0.5)
            ax2.set_xlabel("Value", fontsize=10)
            ax2.set_title("Flux Scale Metrics", fontsize=11, fontweight="bold")
            ax2.grid(True, alpha=0.3, axis="x")
        else:
            ax2.text(
                0.5,
                0.5,
                "No flux scale data",
                ha="center",
                va="center",
                transform=ax2.transAxes,
            )
            ax2.set_title("Flux Scale Metrics", fontsize=11, fontweight="bold")

        # Plot 3: Completeness metrics
        ax3 = axes[1, 0]
        if source_counts_result and source_counts_result.completeness is not None:
            metrics = [
                ("Overall Completeness", source_counts_result.completeness * 100),
                (
                    "Completeness Limit (mJy)",
                    (
                        source_counts_result.completeness_limit_jy * 1000
                        if source_counts_result.completeness_limit_jy
                        else 0
                    ),
                ),
                ("Matched Sources", source_counts_result.n_matched),
                ("Catalog Sources", source_counts_result.n_catalog),
            ]
            names, values = zip(*metrics)
            bars = ax3.barh(
                names, values, color=["green", "orange", "steelblue", "steelblue"]
            )
            ax3.set_xlabel("Value", fontsize=10)
            ax3.set_title("Source Counts Metrics", fontsize=11, fontweight="bold")
            ax3.grid(True, alpha=0.3, axis="x")
        else:
            ax3.text(
                0.5,
                0.5,
                "No source counts data",
                ha="center",
                va="center",
                transform=ax3.transAxes,
            )
            ax3.set_title("Source Counts Metrics", fontsize=11, fontweight="bold")

        # Plot 4: Overall status
        ax4 = axes[1, 1]
        ax4.axis("off")

        status_text = "Validation Summary\n\n"
        if astrometry_result:
            status = "PASS" if not astrometry_result.has_issues else "FAIL"
            status_text += f"Astrometry: {status}\n"
        if flux_scale_result:
            status = "PASS" if not flux_scale_result.has_issues else "FAIL"
            status_text += f"Flux Scale: {status}\n"
        if source_counts_result:
            status = "PASS" if not source_counts_result.has_issues else "FAIL"
            status_text += f"Source Counts: {status}\n"

        ax4.text(
            0.5,
            0.5,
            status_text,
            ha="center",
            va="center",
            transform=ax4.transAxes,
            fontsize=12,
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        )
        ax4.set_title("Overall Status", fontsize=11, fontweight="bold")

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format=output_format, dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)

        return f"data:image/{output_format};base64,{img_base64}"

    except Exception as e:
        logger.error(f"Error generating validation summary plot: {e}", exc_info=True)
        return None
