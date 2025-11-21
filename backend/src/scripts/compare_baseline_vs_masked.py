#!/usr/bin/env python
"""Compare baseline (no mask) vs 0.1 mJy masked self-calibration results."""

# pylint: disable=no-member  # FITS HDUList access

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.visualization import AsinhStretch, ImageNormalize

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    base_dir = Path("/stage/dsa110-contimg/selfcal_comparison")

    comparisons = {
        "Baseline\n(no mask)": base_dir / "baseline_no_nvss",
        "0.1 mJy mask\n(unified catalog)": base_dir / "nvss_0.1mJy",
    }

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))

    for row_idx, (label, dir_path) in enumerate(comparisons.items()):
        logger.info("Processing %s...", label)

        # Find final iteration image
        images = sorted(dir_path.glob("selfcal_iter*-image.fits"))
        if not images:
            logger.warning("No images in %s", label)
            continue

        final_image = images[-1]
        logger.info("  Using: %s", final_image.name)

        # Load and downsample
        with fits.open(final_image) as hdul:
            data = hdul[0].data.squeeze()

            # Downsample for speed
            if data.shape[0] > 512:
                step = data.shape[0] // 512
                data = data[::step, ::step]

            logger.info("  Shape: %s", data.shape)

        # 1. Full image
        ax = axes[row_idx, 0]
        norm = ImageNormalize(data, stretch=AsinhStretch(a=0.1))
        im = ax.imshow(data, origin="lower", cmap="viridis", norm=norm)
        ax.set_title(f"{label}\nFull Image")
        ax.set_xlabel("X (pixels)")
        ax.set_ylabel("Y (pixels)")
        plt.colorbar(im, ax=ax, label="Jy/beam", fraction=0.046)

        # 2. Zoomed center
        ax = axes[row_idx, 1]
        center = data.shape[0] // 2
        zoom_size = data.shape[0] // 4
        zoom_data = data[
            center - zoom_size : center + zoom_size,
            center - zoom_size : center + zoom_size,
        ]
        norm_zoom = ImageNormalize(zoom_data, stretch=AsinhStretch(a=0.1))
        im = ax.imshow(zoom_data, origin="lower", cmap="viridis", norm=norm_zoom)
        ax.set_title("Zoomed Center")
        ax.set_xlabel("X (pixels)")
        ax.set_ylabel("Y (pixels)")
        plt.colorbar(im, ax=ax, label="Jy/beam", fraction=0.046)

        # 3. Flux histogram
        ax = axes[row_idx, 2]
        valid_data = data[np.isfinite(data)]
        ax.hist(
            valid_data.flatten(),
            bins=100,
            alpha=0.7,
            color="steelblue",
            label=label.replace("\n", " "),
        )
        ax.set_xlabel("Flux (Jy/beam)")
        ax.set_ylabel("Pixels")
        ax.set_yscale("log")
        ax.set_title("Flux Distribution")
        ax.grid(alpha=0.3)
        ax.legend()

        # 4. Statistics
        ax = axes[row_idx, 3]
        ax.axis("off")
        rms = np.sqrt(np.nanmean(data**2))
        mad_rms = 1.4826 * np.nanmedian(np.abs(data - np.nanmedian(data)))
        peak = np.nanmax(data)
        dynamic_range = peak / rms if rms > 0 else 0

        stats_text = (
            f"Statistics:\n\n"
            f"Image: {final_image.name}\n"
            f"Shape: {data.shape}\n\n"
            f"Peak: {peak:.2e} Jy/beam\n"
            f"RMS: {rms:.2e} Jy/beam\n"
            f"MAD RMS: {mad_rms:.2e} Jy/beam\n"
            f"Dynamic Range: {dynamic_range:.1f}\n\n"
            f"Min: {np.nanmin(data):.2e}\n"
            f"Mean: {np.nanmean(data):.2e}\n"
            f"Median: {np.nanmedian(data):.2e}\n"
            f"Std: {np.nanstd(data):.2e}"
        )
        ax.text(
            0.1,
            0.5,
            stats_text,
            fontsize=9,
            family="monospace",
            va="center",
            transform=ax.transAxes,
        )

    plt.tight_layout()
    output_path = base_dir / "baseline_vs_masked_comparison.png"
    plt.savefig(output_path, dpi=100)
    logger.info("Saved: %s", output_path)
    plt.close()

    # Also create side-by-side mask comparison
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # Baseline - show that no mask was used
    ax = axes[0]
    ax.text(
        0.5,
        0.5,
        "No Mask Used\n\nCLEAN searched\nentire image",
        ha="center",
        va="center",
        fontsize=20,
        transform=ax.transAxes,
    )
    ax.set_title("Baseline (no mask)", fontsize=16)
    ax.axis("off")

    # 0.1 mJy mask
    mask_file = base_dir / "nvss_0.1mJy" / "selfcal_iter1.unicat_mask.fits"
    if mask_file.exists():
        with fits.open(mask_file) as hdul:
            mask = hdul[0].data.squeeze()
            if mask.shape[0] > 512:
                step = mask.shape[0] // 512
                mask = mask[::step, ::step]

        ax = axes[1]
        im = ax.imshow(mask, origin="lower", cmap="gray_r")
        masked_frac = 100 * np.sum(mask > 0) / mask.size
        ax.set_title(
            f"0.1 mJy unified catalog mask\n" f"{np.sum(mask > 0)} pixels ({masked_frac:.1f}%)",
            fontsize=16,
        )
        ax.set_xlabel("X (pixels)")
        ax.set_ylabel("Y (pixels)")
        plt.colorbar(im, ax=ax, label="Mask value")

    plt.tight_layout()
    mask_output = base_dir / "mask_strategy_comparison.png"
    plt.savefig(mask_output, dpi=100)
    logger.info("Saved: %s", mask_output)
    plt.close()


if __name__ == "__main__":
    main()
