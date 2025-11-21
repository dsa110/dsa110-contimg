#!/usr/bin/env python
"""Quick visualization of selfcal results with downsampling for speed."""

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

    directories = {
        "Baseline (no mask)": base_dir / "baseline_no_nvss",
        "0.1 mJy mask": base_dir / "nvss_0.1mJy",
    }

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    for idx, (label, dir_path) in enumerate(directories.items()):
        logger.info(f"Processing {label}...")

        # Find images
        images = sorted(dir_path.glob("selfcal_iter*-image.fits"))
        if not images:
            logger.warning(f"No images in {label}")
            continue

        final_image = images[-1]
        logger.info(f"  Using: {final_image.name}")

        # Load and downsample
        with fits.open(final_image) as hdul:
            data = hdul[0].data.squeeze()

            # Downsample aggressively
            if data.shape[0] > 256:
                step = data.shape[0] // 256
                data = data[::step, ::step]

            logger.info(f"  Shape: {data.shape}")

        # Plot image
        ax_img = axes[idx, 0]
        norm = ImageNormalize(data, stretch=AsinhStretch(a=0.1))
        im = ax_img.imshow(data, origin="lower", cmap="viridis", norm=norm)
        ax_img.set_title(f"{label}\nFinal Image")
        plt.colorbar(im, ax=ax_img, label="Jy/beam")

        # Histogram
        ax_hist = axes[idx, 1]
        valid_data = data[np.isfinite(data)]
        ax_hist.hist(valid_data.flatten(), bins=100, alpha=0.7, color="steelblue")
        ax_hist.set_xlabel("Flux (Jy/beam)")
        ax_hist.set_ylabel("Pixels")
        ax_hist.set_yscale("log")
        ax_hist.set_title("Flux Distribution")
        ax_hist.grid(alpha=0.3)

        # Stats
        ax_stats = axes[idx, 2]
        ax_stats.axis("off")
        stats_text = (
            f"Final Iteration: {final_image.stem}\n\n"
            f"Image shape: {data.shape}\n"
            f"Min: {np.nanmin(data):.2e} Jy/beam\n"
            f"Max: {np.nanmax(data):.2e} Jy/beam\n"
            f"Mean: {np.nanmean(data):.2e} Jy/beam\n"
            f"Std: {np.nanstd(data):.2e} Jy/beam\n"
            f"RMS: {np.sqrt(np.nanmean(data**2)):.2e} Jy/beam"
        )
        ax_stats.text(0.1, 0.5, stats_text, fontsize=10, family="monospace", va="center")

    plt.tight_layout()
    output_path = base_dir / "selfcal_comparison_quick.png"
    plt.savefig(output_path, dpi=72)
    logger.info(f"Saved: {output_path}")
    plt.close()


if __name__ == "__main__":
    main()
