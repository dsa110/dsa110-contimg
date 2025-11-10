#!/usr/bin/env python3
"""
Test script for validating forced photometry normalization on 0702+445 field.

Usage:
    # Day 1: Establish baseline
    python test_photometry_normalization_0702.py --image day1_0702.pbcor.fits --mode baseline

    # Day 2: Test normalization
    python test_photometry_normalization_0702.py --image day2_0702.pbcor.fits --mode validate

Validates:
- Reference source selection from master_sources catalog
- Baseline establishment
- Correction factor computation
- Normalized flux scatter < 3% for stable sources
"""
import argparse
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from typing import Tuple

from dsa110_contimg.photometry.normalize import (
    query_reference_sources,
    establish_baselines,
    compute_ensemble_correction,
    normalize_measurement,
)
from dsa110_contimg.photometry.forced import measure_forced_peak
from dsa110_contimg.database.products import ensure_products_db
from astropy.io import fits
from astropy.wcs import WCS


def get_image_center(fits_path):
    """Extract image center coordinates.

    Returns:
        Tuple[float, float]: (ra_deg, dec_deg)
    """
    hdr = fits.getheader(fits_path)
    wcs = WCS(hdr).celestial
    ny, nx = fits.getdata(fits_path).squeeze().shape
    ra, dec = wcs.pixel_to_world_values(nx / 2, ny / 2)
    return float(ra), float(dec)


def mode_baseline(args):
    """Mode 1: Establish baseline from first image."""
    print("=" * 70)
    print("BASELINE ESTABLISHMENT MODE")
    print("=" * 70)

    # Get image center
    ra_center, dec_center = get_image_center(args.image)
    print(f"\nImage center: RA={ra_center:.4f}, Dec={dec_center:.4f}")

    # Query reference sources
    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        print(f"ERROR: Catalog not found: {catalog_path}")
        return 1

    print(f"\nQuerying reference sources from: {catalog_path}")
    ref_sources = query_reference_sources(
        catalog_path,
        ra_center,
        dec_center,
        fov_radius_deg=args.fov_radius,
        min_snr=args.min_snr,
        max_sources=args.max_refs,
    )

    if not ref_sources:
        print("ERROR: No reference sources found in FoV!")
        return 1

    print(f"Found {len(ref_sources)} reference sources:")
    for i, ref in enumerate(ref_sources[:10], 1):
        print(
            f"  {i}. {ref.nvss_name}: SNR={ref.snr_nvss:.1f}, "
            f"RA={ref.ra_deg:.4f}, Dec={ref.dec_deg:.4f}"
        )
    if len(ref_sources) > 10:
        print(f"  ... and {len(ref_sources) - 10} more")

    # Measure all references
    print(f"\nMeasuring {len(ref_sources)} reference sources...")
    measurements = []
    for i, ref in enumerate(ref_sources, 1):
        result = measure_forced_peak(
            args.image,
            ref.ra_deg,
            ref.dec_deg,
            box_size_pix=args.box,
            annulus_pix=tuple(args.annulus),
        )

        if np.isfinite(result.peak_jyb):
            measurements.append(result.peak_jyb)
            print(f"  {i}/{len(ref_sources)}: {result.peak_jyb:.4f} Jy/beam")
        else:
            print(f"  {i}/{len(ref_sources)}: FAILED")
            ref.is_valid = False

    # Statistics
    measurements_arr = np.array(measurements)
    print(f"\nBaseline statistics:")
    print(f"  N valid: {len(measurements)} / {len(ref_sources)}")
    print(f"  Median: {np.median(measurements_arr):.4f} Jy/beam")
    print(
        f"  MAD: {1.4826 * np.median(np.abs(measurements_arr - np.median(measurements_arr))):.4f} Jy/beam"
    )
    print(f"  Min: {np.min(measurements_arr):.4f} Jy/beam")
    print(f"  Max: {np.max(measurements_arr):.4f} Jy/beam")

    # Save baseline to file
    baseline_file = Path(args.baseline_file)
    baseline_file.parent.mkdir(parents=True, exist_ok=True)

    with open(baseline_file, "w") as f:
        f.write(f"# Baseline established: {datetime.utcnow().isoformat()}\n")
        f.write(f"# Image: {args.image}\n")
        f.write(f"# Center: RA={ra_center:.6f}, Dec={dec_center:.6f}\n")
        f.write(f"# source_id,ra_deg,dec_deg,nvss_name,flux_baseline,baseline_rms\n")
        for ref, meas in zip(ref_sources, measurements):
            if ref.is_valid:
                f.write(
                    f"{ref.source_id},{ref.ra_deg:.6f},{ref.dec_deg:.6f},"
                    f"{ref.nvss_name},{meas:.6f},0.0\n"
                )  # RMS computed after N epochs

    print(f"\nBaseline saved to: {baseline_file}")
    print("\nRun in 'validate' mode after 24h with next image.")

    return 0


def mode_validate(args):
    """Mode 2: Validate normalization against baseline."""
    print("=" * 70)
    print("NORMALIZATION VALIDATION MODE")
    print("=" * 70)

    # Load baseline
    baseline_file = Path(args.baseline_file)
    if not baseline_file.exists():
        print(f"ERROR: Baseline file not found: {baseline_file}")
        print("Run in 'baseline' mode first!")
        return 1

    print(f"\nLoading baseline from: {baseline_file}")
    baselines = {}
    ref_coords = {}
    with open(baseline_file, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split(",")
            if len(parts) == 6:
                source_id = int(parts[0])
                ra = float(parts[1])
                dec = float(parts[2])
                name = parts[3]
                flux_base = float(parts[4])
                baselines[source_id] = flux_base
                ref_coords[source_id] = (ra, dec, name)

    print(f"Loaded {len(baselines)} reference baselines")

    # Measure current epoch
    print(f"\nMeasuring references in: {args.image}")
    measurements_current = {}
    ratios = []

    for source_id, flux_base in baselines.items():
        ra, dec, name = ref_coords[source_id]
        result = measure_forced_peak(
            args.image,
            ra,
            dec,
            box_size_pix=args.box,
            annulus_pix=tuple(args.annulus),
        )

        if np.isfinite(result.peak_jyb) and result.peak_jyb > 0:
            measurements_current[source_id] = result.peak_jyb
            ratio = result.peak_jyb / flux_base
            ratios.append(ratio)
            print(f"  {name}: {result.peak_jyb:.4f} / {flux_base:.4f} = {ratio:.4f}")
        else:
            print(f"  {name}: FAILED")

    # Compute correction statistics
    ratios_arr = np.array(ratios)
    correction = np.median(ratios_arr)
    mad = np.median(np.abs(ratios_arr - correction))
    rms = 1.4826 * mad

    print(f"\nCorrection factor statistics:")
    print(f"  Median ratio: {correction:.4f}")
    print(f"  RMS scatter: {rms:.4f} ({100*rms:.2f}%)")
    print(f"  N valid: {len(ratios)} / {len(baselines)}")

    # Normalize measurements
    normalized = {}
    for source_id, flux_raw in measurements_current.items():
        flux_norm = flux_raw / correction
        normalized[source_id] = flux_norm

    # Compare to baseline
    print(f"\nNormalized vs Baseline comparison:")
    deviations = []
    for source_id, flux_norm in normalized.items():
        flux_base = baselines[source_id]
        dev = (flux_norm - flux_base) / flux_base
        deviations.append(dev)
        ra, dec, name = ref_coords[source_id]
        print(f"  {name}: {flux_norm:.4f} vs {flux_base:.4f} ({100*dev:+.2f}%)")

    dev_arr = np.array(deviations)
    dev_rms = np.std(dev_arr)
    dev_mad = 1.4826 * np.median(np.abs(dev_arr - np.median(dev_arr)))

    print(f"\nDeviation statistics:")
    print(f"  Median: {100*np.median(dev_arr):.2f}%")
    print(f"  RMS: {100*dev_rms:.2f}%")
    print(f"  MAD (robust RMS): {100*dev_mad:.2f}%")

    # Success criteria
    print(f"\nValidation:")
    if dev_mad < 0.03:
        print(f"  ✓ Normalization PASSED: MAD={100*dev_mad:.2f}% < 3%")
        status = 0
    else:
        print(f"  ✗ Normalization FAILED: MAD={100*dev_mad:.2f}% >= 3%")
        status = 1

    # Plot
    if args.plot:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # Raw flux comparison
        ax = axes[0, 0]
        baseline_vals = [baselines[sid] for sid in measurements_current.keys()]
        current_vals = list(measurements_current.values())
        ax.scatter(baseline_vals, current_vals, alpha=0.6)
        ax.plot(
            [min(baseline_vals), max(baseline_vals)],
            [min(baseline_vals), max(baseline_vals)],
            "r--",
            alpha=0.5,
            label="1:1",
        )
        ax.set_xlabel("Baseline Flux (Jy/beam)")
        ax.set_ylabel("Current Raw Flux (Jy/beam)")
        ax.set_title("Raw Flux: Day 1 vs Day 2")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Normalized flux comparison
        ax = axes[0, 1]
        norm_vals = list(normalized.values())
        ax.scatter(baseline_vals, norm_vals, alpha=0.6, color="green")
        ax.plot(
            [min(baseline_vals), max(baseline_vals)],
            [min(baseline_vals), max(baseline_vals)],
            "r--",
            alpha=0.5,
            label="1:1",
        )
        ax.set_xlabel("Baseline Flux (Jy/beam)")
        ax.set_ylabel("Normalized Flux (Jy/beam)")
        ax.set_title("Normalized Flux: Day 1 vs Day 2")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Ratio distribution
        ax = axes[1, 0]
        ax.hist(ratios, bins=20, alpha=0.7, edgecolor="black")
        ax.axvline(
            correction, color="r", linestyle="--", label=f"Median={correction:.4f}"
        )
        ax.axvline(correction - rms, color="orange", linestyle=":", label=f"±RMS")
        ax.axvline(correction + rms, color="orange", linestyle=":")
        ax.set_xlabel("Flux Ratio (Current / Baseline)")
        ax.set_ylabel("N References")
        ax.set_title(f"Correction Factor Distribution (RMS={100*rms:.2f}%)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Deviation distribution
        ax = axes[1, 1]
        ax.hist(100 * dev_arr, bins=20, alpha=0.7, edgecolor="black", color="green")
        ax.axvline(0, color="r", linestyle="--", label="Zero deviation")
        ax.axvline(-100 * dev_mad, color="orange", linestyle=":", label=f"±MAD")
        ax.axvline(+100 * dev_mad, color="orange", linestyle=":")
        ax.set_xlabel("Deviation (%)")
        ax.set_ylabel("N References")
        ax.set_title(f"Normalized Flux Deviation (MAD={100*dev_mad:.2f}%)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_file = (
            Path(args.image).parent
            / f"{Path(args.image).stem}_normalization_validation.png"
        )
        plt.savefig(plot_file, dpi=150)
        print(f"\nPlot saved to: {plot_file}")

    return status


def main():
    parser = argparse.ArgumentParser(
        description="Test forced photometry normalization on 0702+445 field"
    )
    parser.add_argument("--image", required=True, help="FITS image (.pbcor.fits)")
    parser.add_argument(
        "--mode",
        choices=["baseline", "validate"],
        required=True,
        help="'baseline' for Day 1, 'validate' for Day 2",
    )
    parser.add_argument(
        "--catalog",
        default="state/catalogs/master_sources.sqlite3",
        help="Path to master_sources catalog",
    )
    parser.add_argument(
        "--baseline-file",
        default="state/photometry_baseline_0702.csv",
        help="File to store/load baseline",
    )
    parser.add_argument(
        "--fov-radius",
        type=float,
        default=1.5,
        help="FoV radius for reference search (deg)",
    )
    parser.add_argument(
        "--min-snr", type=float, default=50.0, help="Minimum NVSS SNR for references"
    )
    parser.add_argument(
        "--max-refs", type=int, default=20, help="Maximum number of references"
    )
    parser.add_argument(
        "--box", type=int, default=5, help="Pixel box size for forced photometry"
    )
    parser.add_argument(
        "--annulus",
        nargs=2,
        type=int,
        default=[12, 20],
        help="Annulus inner/outer radii",
    )
    parser.add_argument("--plot", action="store_true", help="Generate diagnostic plots")

    args = parser.parse_args()

    if args.mode == "baseline":
        return mode_baseline(args)
    else:
        return mode_validate(args)


if __name__ == "__main__":
    sys.exit(main())
