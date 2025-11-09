"""
Plotting utilities for validation results.

Generates diagnostic plots for astrometry, flux scale, and completeness validation.
"""

from dsa110_contimg.qa.catalog_validation import CatalogValidationResult
import numpy as np
import matplotlib.pyplot as plt
import base64
import io
import logging
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use("Agg", force=True)  # Headless backend


logger = logging.getLogger(__name__)


def plot_astrometry_scatter(
    result: CatalogValidationResult,
    output_format: str = "png",
    dpi: int = 100
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
                    offset_ra = (detected_ra - catalog_ra) * \
                        3600.0 * np.cos(np.radians(catalog_dec))
                    offset_dec = (detected_dec - catalog_dec) * 3600.0
                    offsets_ra.append(offset_ra)
                    offsets_dec.append(offset_dec)

        if len(offsets_total) == 0:
            return None

        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Plot 1: RA vs Dec offset scatter
        ax1.scatter(offsets_ra, offsets_dec, alpha=0.6, s=50, c=offsets_total,
                    cmap='viridis', edgecolors='black', linewidths=0.5)
        ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.set_xlabel('RA Offset (arcsec)', fontsize=11)
        ax1.set_ylabel('Dec Offset (arcsec)', fontsize=11)
        ax1.set_title('Astrometric Offsets', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal', adjustable='box')

        # Add colorbar
        cbar = plt.colorbar(ax1.collections[0], ax=ax1)
        cbar.set_label('Total Offset (arcsec)', fontsize=10)

        # Add statistics text
        if result.mean_offset_arcsec is not None:
            stats_text = f'Mean: {result.mean_offset_arcsec:.2f}"\n'
            stats_text += f'RMS: {result.rms_offset_arcsec:.2f}"' if result.rms_offset_arcsec else ''
            ax1.text(0.05, 0.95, stats_text, transform=ax1.transAxes,
                     verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                     fontsize=9)

        # Plot 2: Offset histogram
        ax2.hist(offsets_total, bins=20, edgecolor='black',
                 alpha=0.7, color='steelblue')
        ax2.axvline(x=result.mean_offset_arcsec if result.mean_offset_arcsec else 0,
                    color='red', linestyle='--', linewidth=2, label='Mean')
        if result.rms_offset_arcsec:
            ax2.axvline(x=result.rms_offset_arcsec, color='orange',
                        linestyle='--', linewidth=2, label='RMS')
        ax2.set_xlabel('Total Offset (arcsec)', fontsize=11)
        ax2.set_ylabel('Number of Sources', fontsize=11)
        ax2.set_title('Offset Distribution', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.legend()

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format=output_format, dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return f"data:image/{output_format};base64,{img_base64}"

    except Exception as e:
        logger.error(f"Error generating astrometry plot: {e}", exc_info=True)
        return None


def plot_flux_ratio_histogram(
    result: CatalogValidationResult,
    output_format: str = "png",
    dpi: int = 100
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
                detected_flux, catalog_flux, ratio = flux_pair[0], flux_pair[1], flux_pair[2]
                ratios.append(ratio)
                detected_fluxes.append(detected_flux)
                catalog_fluxes.append(catalog_flux)

        if len(ratios) == 0:
            return None

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Plot 1: Flux ratio histogram
        ax1.hist(ratios, bins=20, edgecolor='black',
                 alpha=0.7, color='steelblue')
        ax1.axvline(x=1.0, color='green', linestyle='--',
                    linewidth=2, label='Perfect (1.0)')
        if result.mean_flux_ratio:
            ax1.axvline(x=result.mean_flux_ratio, color='red', linestyle='--',
                        linewidth=2, label=f'Mean ({result.mean_flux_ratio:.3f})')
        ax1.set_xlabel('Flux Ratio (Detected / Catalog)', fontsize=11)
        ax1.set_ylabel('Number of Sources', fontsize=11)
        ax1.set_title('Flux Ratio Distribution',
                      fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.legend()

        # Add statistics text
        if result.mean_flux_ratio and result.rms_flux_ratio:
            stats_text = f'Mean: {result.mean_flux_ratio:.3f}\n'
            stats_text += f'RMS: {result.rms_flux_ratio:.3f}\n'
            if result.flux_scale_error:
                stats_text += f'Error: {result.flux_scale_error*100:.1f}%'
            ax1.text(0.05, 0.95, stats_text, transform=ax1.transAxes,
                     verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                     fontsize=9)

        # Plot 2: Detected vs Catalog flux scatter
        if len(detected_fluxes) > 0 and len(catalog_fluxes) > 0:
            ax2.scatter(catalog_fluxes, detected_fluxes, alpha=0.6, s=50,
                        edgecolors='black', linewidths=0.5)

            # Add 1:1 line
            flux_min = min(min(catalog_fluxes), min(detected_fluxes))
            flux_max = max(max(catalog_fluxes), max(detected_fluxes))
            ax2.plot([flux_min, flux_max], [flux_min, flux_max],
                     'r--', linewidth=2, label='1:1 line')

            ax2.set_xlabel('Catalog Flux (Jy)', fontsize=11)
            ax2.set_ylabel('Detected Flux (Jy)', fontsize=11)
            ax2.set_title('Detected vs Catalog Flux',
                          fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            ax2.set_aspect('equal', adjustable='box')

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format=output_format, dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return f"data:image/{output_format};base64,{img_base64}"

    except Exception as e:
        logger.error(f"Error generating flux ratio plot: {e}", exc_info=True)
        return None


def plot_completeness_curve(
    result: CatalogValidationResult,
    output_format: str = "png",
    dpi: int = 100
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
    if (not result.completeness_bins_jy or not result.completeness_per_bin or
            not result.catalog_counts_per_bin):
        return None

    try:
        # Extract data
        flux_bins = np.array(result.completeness_bins_jy) * \
            1000  # Convert to mJy
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
        ax1.plot(flux_bins, completeness, 'o-', linewidth=2, markersize=8,
                 color='steelblue', label='Completeness')
        ax1.axhline(y=95, color='green', linestyle='--', linewidth=2,
                    label='95% threshold', alpha=0.7)
        ax1.axhline(y=80, color='orange', linestyle='--', linewidth=1,
                    label='80% threshold', alpha=0.5)

        # Mark completeness limit if available
        if result.completeness_limit_jy:
            limit_mjy = result.completeness_limit_jy * 1000
            ax1.axvline(x=limit_mjy, color='red', linestyle='--', linewidth=2,
                        label=f'Completeness limit ({limit_mjy:.2f} mJy)', alpha=0.7)

        ax1.set_xlabel('Flux Density (mJy)', fontsize=11)
        ax1.set_ylabel('Completeness (%)', fontsize=11)
        ax1.set_title('Completeness vs Flux Density',
                      fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.set_xscale('log')
        ax1.set_ylim(0, 105)
        ax1.legend()

        # Add overall completeness text
        if result.completeness:
            ax1.text(0.05, 0.05, f'Overall: {result.completeness*100:.1f}%',
                     transform=ax1.transAxes, bbox=dict(boxstyle='round',
                                                        facecolor='wheat', alpha=0.8), fontsize=10)

        # Plot 2: Source counts per bin
        ax2.bar(flux_bins, catalog_counts, width=flux_bins*0.15, alpha=0.7,
                color='steelblue', edgecolor='black', label='Catalog')

        if result.detected_counts_per_bin:
            detected_counts = np.array(
                result.detected_counts_per_bin)[valid_mask]
            ax2.bar(flux_bins, detected_counts, width=flux_bins*0.15, alpha=0.5,
                    color='green', edgecolor='black', label='Detected')

        ax2.set_xlabel('Flux Density (mJy)', fontsize=11)
        ax2.set_ylabel('Number of Sources', fontsize=11)
        ax2.set_title('Source Counts per Flux Bin',
                      fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.set_xscale('log')
        ax2.legend()

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format=output_format, dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return f"data:image/{output_format};base64,{img_base64}"

    except Exception as e:
        logger.error(f"Error generating completeness plot: {e}", exc_info=True)
        return None
