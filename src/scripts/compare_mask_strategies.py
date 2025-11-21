#!/usr/bin/env python
"""
Compare masking strategies with different flux limits.

This script generates unified catalog (FIRST+RACS+NVSS) masks at three different
flux thresholds and compares their properties:
- 0.1 mJy: Deep mask (many faint sources)
- 1.0 mJy: Moderate mask (intermediate sources)
- 10.0 mJy: Shallow mask (only bright sources)

Usage:
    python compare_mask_strategies.py --ms /path/to/observation.ms --imagename /path/to/output
"""

# pylint: disable=no-member  # FITS HDUList access

import argparse
import logging
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

# Enforce CASA6 Python environment
from dsa110_contimg.utils.runtime_safeguards import check_casa6_python

if not check_casa6_python():
    raise RuntimeError(
        "This script requires casa6 Python environment. "
        "Use: /opt/miniforge/envs/casa6/bin/python"
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_mask_at_threshold(
    imagename: str,
    imsize: int,
    cell_arcsec: float,
    ra0_deg: float,
    dec0_deg: float,
    threshold_mjy: float,
    radius_arcsec: float = 60.0,
) -> Dict:
    """Create mask at given flux threshold and return statistics.

    Args:
        imagename: Base image name
        imsize: Image size in pixels
        cell_arcsec: Pixel scale in arcseconds
        ra0_deg: Phase center RA in degrees
        dec0_deg: Phase center Dec in degrees
        threshold_mjy: Flux threshold in mJy
        radius_arcsec: Mask radius around each source

    Returns:
        Dictionary with mask statistics
    """
    from dsa110_contimg.imaging.nvss_tools import create_unicat_fits_mask

    logger.info(f"Creating mask with threshold {threshold_mjy} mJy...")

    mask_path = create_unicat_fits_mask(
        imagename=imagename,
        imsize=imsize,
        cell_arcsec=cell_arcsec,
        ra0_deg=ra0_deg,
        dec0_deg=dec0_deg,
        unicat_min_mjy=threshold_mjy,
        radius_arcsec=radius_arcsec,
        out_path=f"{imagename}.mask_{threshold_mjy:g}mJy.fits",
    )

    # Load mask and compute statistics
    with fits.open(mask_path) as hdul:
        mask_data = hdul[0].data  # type: ignore[attr-defined]

    n_pixels_total = mask_data.size
    n_pixels_masked = np.sum(mask_data > 0)
    fraction_masked = n_pixels_masked / n_pixels_total

    # Count number of separate regions (approximate by counting connected components)
    from scipy import ndimage

    labeled_mask, n_regions = ndimage.label(mask_data > 0)

    stats = {
        "threshold_mjy": threshold_mjy,
        "mask_path": mask_path,
        "n_pixels_total": n_pixels_total,
        "n_pixels_masked": n_pixels_masked,
        "fraction_masked": fraction_masked,
        "n_regions": n_regions,
        "mask_data": mask_data,
    }

    logger.info(
        f"  Threshold {threshold_mjy} mJy: "
        f"{n_regions} sources, "
        f"{fraction_masked*100:.2f}% masked "
        f"({n_pixels_masked}/{n_pixels_total} pixels)"
    )

    return stats


def plot_mask_comparison(results: List[Dict], output_path: str):
    """Create comparison plots of different masks.

    Args:
        results: List of mask statistics dictionaries
        output_path: Output path for plot
    """
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    # Plot masks
    for idx, result in enumerate(results):
        ax = axes[0, idx]
        mask = result["mask_data"]
        threshold = result["threshold_mjy"]

        im = ax.imshow(mask, origin="lower", cmap="gray_r", interpolation="nearest")
        ax.set_title(
            f"Threshold: {threshold} mJy\n"
            f"{result['n_regions']} sources, "
            f"{result['fraction_masked']*100:.2f}% masked"
        )
        ax.set_xlabel("X (pixels)")
        ax.set_ylabel("Y (pixels)")
        plt.colorbar(im, ax=ax, label="Mask value")

    # Plot statistics
    thresholds = [r["threshold_mjy"] for r in results]
    n_regions = [r["n_regions"] for r in results]
    fractions = [r["fraction_masked"] * 100 for r in results]

    # Number of sources
    ax = axes[1, 0]
    ax.bar(range(len(thresholds)), n_regions, color="steelblue")
    ax.set_xticks(range(len(thresholds)))
    ax.set_xticklabels([f"{t} mJy" for t in thresholds])
    ax.set_ylabel("Number of Sources")
    ax.set_title("Sources per Mask")
    ax.grid(axis="y", alpha=0.3)

    # Masked fraction
    ax = axes[1, 1]
    ax.bar(range(len(thresholds)), fractions, color="coral")
    ax.set_xticks(range(len(thresholds)))
    ax.set_xticklabels([f"{t} mJy" for t in thresholds])
    ax.set_ylabel("Masked Fraction (%)")
    ax.set_title("Image Coverage")
    ax.grid(axis="y", alpha=0.3)

    # Summary table
    ax = axes[1, 2]
    ax.axis("off")
    table_data = []
    headers = ["Threshold", "Sources", "Coverage"]
    for result in results:
        table_data.append(
            [
                f"{result['threshold_mjy']} mJy",
                f"{result['n_regions']}",
                f"{result['fraction_masked']*100:.2f}%",
            ]
        )

    table = ax.table(
        cellText=table_data,
        colLabels=headers,
        cellLoc="center",
        loc="center",
        colWidths=[0.3, 0.3, 0.3],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    ax.set_title("Mask Comparison Summary", pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.info(f"Saved comparison plot to: {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Compare masking strategies at different flux thresholds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--ms",
        required=True,
        help="Path to Measurement Set (used to extract phase center)",
    )
    parser.add_argument(
        "--imagename",
        required=True,
        help="Base name for output masks and plots",
    )
    parser.add_argument(
        "--imsize",
        type=int,
        default=1024,
        help="Image size in pixels (default: 1024)",
    )
    parser.add_argument(
        "--cell-arcsec",
        type=float,
        default=None,
        help="Cell size in arcseconds (default: auto-detect from MS)",
    )
    parser.add_argument(
        "--radius-arcsec",
        type=float,
        default=60.0,
        help="Mask radius around each source in arcseconds (default: 60.0)",
    )
    parser.add_argument(
        "--thresholds",
        nargs="+",
        type=float,
        default=[0.1, 1.0, 10.0],
        help="Flux thresholds in mJy to test (default: 0.1 1.0 10.0)",
    )

    args = parser.parse_args()

    # Extract phase center from MS
    logger.info(f"Extracting phase center from: {args.ms}")
    import casacore.tables as casatables

    with casatables.table(f"{args.ms}::FIELD", readonly=True) as fld:
        phase_dir = fld.getcol("PHASE_DIR")[0]
        ra0_deg = float(phase_dir[0][0]) * (180.0 / np.pi)
        dec0_deg = float(phase_dir[0][1]) * (180.0 / np.pi)

    logger.info(f"Phase center: RA={ra0_deg:.6f}°, Dec={dec0_deg:.6f}°")

    # Auto-detect cell size if not provided
    if args.cell_arcsec is None:
        from dsa110_contimg.imaging.cli_utils import default_cell_arcsec

        args.cell_arcsec = default_cell_arcsec(args.ms)
        logger.info(f"Auto-detected cell size: {args.cell_arcsec:.3f} arcsec")

    # Create output directory
    output_dir = Path(args.imagename).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate masks at each threshold
    results = []
    for threshold in args.thresholds:
        result = create_mask_at_threshold(
            imagename=args.imagename,
            imsize=args.imsize,
            cell_arcsec=args.cell_arcsec,
            ra0_deg=ra0_deg,
            dec0_deg=dec0_deg,
            threshold_mjy=threshold,
            radius_arcsec=args.radius_arcsec,
        )
        results.append(result)

    # Create comparison plot
    plot_path = f"{args.imagename}.mask_comparison.png"
    plot_mask_comparison(results, plot_path)

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("MASK COMPARISON SUMMARY")
    logger.info("=" * 70)
    for result in results:
        logger.info(
            f"Threshold {result['threshold_mjy']:>6.1f} mJy: "
            f"{result['n_regions']:>5} sources, "
            f"{result['fraction_masked']*100:>6.2f}% coverage"
        )
    logger.info("=" * 70)

    # Compute speedup estimate
    # Masking typically provides 2-4x speedup, roughly proportional to masked fraction
    logger.info("\nEstimated imaging speedup (relative to no mask):")
    baseline_time = 100.0  # Assume 100 arbitrary time units for unmasked imaging
    for result in results:
        masked_fraction = result["fraction_masked"]
        # Speedup from reducing pixels to clean
        speedup = 1.0 / (1.0 - masked_fraction + 0.25 * masked_fraction)
        time = baseline_time / speedup
        logger.info(
            f"  {result['threshold_mjy']:>6.1f} mJy threshold: "
            f"{speedup:.2f}x faster ({time:.1f}/{baseline_time:.1f} time units)"
        )


if __name__ == "__main__":
    main()
