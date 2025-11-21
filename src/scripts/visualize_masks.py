#!/usr/bin/env python
"""Visualize just the masks from selfcal comparison."""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    base_dir = Path("/stage/dsa110-contimg/selfcal_comparison")

    directories = {
        "Baseline (no mask)": base_dir / "baseline_no_nvss",
        "0.1 mJy mask": base_dir / "nvss_0.1mJy",
    }

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    for idx, (label, dir_path) in enumerate(directories.items()):
        logger.info(f"Processing {label}...")

        # Find mask files (try unicat first, then nvss for backwards compat)
        masks = sorted(dir_path.glob("selfcal_iter*.unicat_mask.fits"))
        if not masks:
            masks = sorted(dir_path.glob("selfcal_iter*.nvss_mask.fits"))
        if not masks:
            logger.warning(f"No masks in {label}")
            axes[idx].axis("off")
            axes[idx].set_title(f"{label}\n(No mask used)")
            continue

        final_mask = masks[-1]
        logger.info(f"  Using: {final_mask.name}")

        # Load mask
        with fits.open(final_mask) as hdul:
            mask = hdul[0].data.squeeze()

            # Downsample if large
            if mask.shape[0] > 512:
                step = mask.shape[0] // 512
                mask = mask[::step, ::step]

            logger.info(f"  Shape: {mask.shape}")
            logger.info(f"  Masked pixels: {np.sum(mask > 0)}/{mask.size}")

        # Plot mask
        ax = axes[idx]
        im = ax.imshow(mask, origin="lower", cmap="gray_r")
        ax.set_title(
            f"{label}\n"
            f"{np.sum(mask > 0)} pixels masked "
            f"({100*np.sum(mask > 0)/mask.size:.1f}%)"
        )
        ax.set_xlabel("X (pixels)")
        ax.set_ylabel("Y (pixels)")
        plt.colorbar(im, ax=ax, label="Mask value")

    plt.tight_layout()
    output_path = base_dir / "mask_comparison.png"
    plt.savefig(output_path, dpi=150)
    logger.info(f"Saved: {output_path}")
    plt.close()


if __name__ == "__main__":
    main()
