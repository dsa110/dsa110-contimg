#!/usr/bin/env python
"""Quantitative comparison of baseline vs 0.1 mJy masked results."""

# pylint: disable=no-member  # FITS HDUList access

import logging
from pathlib import Path

import numpy as np
from astropy.io import fits

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def compute_stats(data):
    """Compute image statistics."""
    valid = data[np.isfinite(data)]

    rms = np.sqrt(np.nanmean(data**2))
    mad_rms = 1.4826 * np.nanmedian(np.abs(data - np.nanmedian(data)))
    peak = np.nanmax(data)
    peak_pos = np.unravel_index(np.nanargmax(data), data.shape)
    dynamic_range = peak / rms if rms > 0 else 0

    return {
        "peak": peak,
        "peak_pos": peak_pos,
        "rms": rms,
        "mad_rms": mad_rms,
        "mean": np.nanmean(data),
        "median": np.nanmedian(data),
        "std": np.nanstd(data),
        "min": np.nanmin(data),
        "max": np.nanmax(data),
        "dynamic_range": dynamic_range,
    }


def main():
    base_dir = Path("/stage/dsa110-contimg/selfcal_comparison")

    # Load baseline image
    baseline_img = sorted((base_dir / "baseline_no_nvss").glob("selfcal_iter*-image.fits"))[-1]
    logger.info(f"Baseline: {baseline_img.name}")

    with fits.open(baseline_img) as hdul:
        baseline_data = hdul[0].data.squeeze()

    baseline_stats = compute_stats(baseline_data)

    # Load 0.1 mJy masked image
    masked_img = sorted((base_dir / "nvss_0.1mJy").glob("selfcal_iter*-image.fits"))[-1]
    logger.info(f"Masked: {masked_img.name}")

    with fits.open(masked_img) as hdul:
        masked_data = hdul[0].data.squeeze()

    masked_stats = compute_stats(masked_data)

    # Compute difference
    diff = masked_data - baseline_data
    diff_stats = compute_stats(diff)

    # Print comparison
    print("\n" + "=" * 70)
    print("BASELINE VS 0.1 mJy MASKED COMPARISON")
    print("=" * 70)
    print(f"\n{'Metric':<20} {'Baseline':<20} {'0.1 mJy Mask':<20} {'Difference':<15}")
    print("-" * 70)

    metrics = [
        ("Peak (Jy/beam)", "peak"),
        ("RMS (Jy/beam)", "rms"),
        ("MAD RMS (Jy/beam)", "mad_rms"),
        ("Dynamic Range", "dynamic_range"),
        ("Mean (Jy/beam)", "mean"),
        ("Median (Jy/beam)", "median"),
        ("Std (Jy/beam)", "std"),
    ]

    for label, key in metrics:
        base_val = baseline_stats[key]
        mask_val = masked_stats[key]
        diff_val = mask_val - base_val
        pct_change = 100 * diff_val / base_val if base_val != 0 else 0

        print(
            f"{label:<20} {base_val:<20.3e} {mask_val:<20.3e} "
            f"{diff_val:>+.2e} ({pct_change:>+.1f}%)"
        )

    print("\n" + "=" * 70)
    print("PIXEL-BY-PIXEL DIFFERENCE ANALYSIS")
    print("=" * 70)
    print(f"Max absolute difference:  {np.nanmax(np.abs(diff)):.3e} Jy/beam")
    print(f"Mean absolute difference: {np.nanmean(np.abs(diff)):.3e} Jy/beam")
    print(f"RMS difference:           {np.sqrt(np.nanmean(diff**2)):.3e} Jy/beam")

    # Fractional difference where both images have signal
    threshold = 5 * baseline_stats["rms"]
    signal_mask = (np.abs(baseline_data) > threshold) & (np.abs(masked_data) > threshold)

    if np.any(signal_mask):
        frac_diff = diff[signal_mask] / baseline_data[signal_mask]
        print(f"\nFractional difference (signal pixels > 5σ):")
        print(f"  Mean: {np.nanmean(frac_diff):.3%}")
        print(f"  Median: {np.nanmedian(frac_diff):.3%}")
        print(f"  Std: {np.nanstd(frac_diff):.3%}")
        print(f"  N pixels: {np.sum(signal_mask)}")

    # Correlation
    valid = np.isfinite(baseline_data) & np.isfinite(masked_data)
    correlation = np.corrcoef(
        baseline_data[valid].flatten(),
        masked_data[valid].flatten(),
    )[0, 1]
    print(f"\nPearson correlation: {correlation:.6f}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
