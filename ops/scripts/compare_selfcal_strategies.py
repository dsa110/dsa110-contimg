#!/usr/bin/env python3
"""
Compare Self-Calibration Strategies on Real Observations

Tests multiple configurations:
1. No NVSS seeding (baseline)
2. NVSS seeding with 0.1 mJy limit
3. NVSS seeding with 1.0 mJy limit
4. NVSS seeding with 10.0 mJy limit

Measures:
- Initial vs final SNR
- SNR improvement factor
- Dynamic range
- Convergence iterations
- Processing time

Usage:
    python compare_selfcal_strategies.py <ms_path> [--output-dir OUTPUT_DIR]
"""

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from astropy.io import fits

sys.path.insert(0, "/data/dsa110-contimg/src/dsa110_contimg/src")

from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
LOG = logging.getLogger(__name__)


def get_image_stats(fits_path: str) -> Dict:
    """
    Extract statistics from a FITS image.

    Args:
        fits_path: Path to FITS image

    Returns:
        Dictionary with image statistics
    """
    with fits.open(fits_path) as hdul:
        data = hdul[0].data
        # Handle different dimensionalities
        if data.ndim == 4:
            data = data[0, 0, :, :]
        elif data.ndim == 3:
            data = data[0, :, :]

        # Calculate statistics
        import numpy as np

        # Mask NaN values
        mask = np.isfinite(data)
        clean_data = data[mask]

        if len(clean_data) == 0:
            return {
                "peak": 0.0,
                "rms": 0.0,
                "snr": 0.0,
                "dynamic_range": 0.0,
            }

        peak = np.max(np.abs(clean_data))
        # Use off-source RMS (outer 20% of image)
        ny, nx = data.shape
        outer_mask = (
            (np.arange(ny)[:, None] < 0.1 * ny)
            | (np.arange(ny)[:, None] > 0.9 * ny)
            | (np.arange(nx)[None, :] < 0.1 * nx)
            | (np.arange(nx)[None, :] > 0.9 * nx)
        )
        off_source_data = data[outer_mask & mask]
        rms = np.std(off_source_data) if len(off_source_data) > 0 else np.std(clean_data)

        snr = peak / rms if rms > 0 else 0.0
        dynamic_range = peak / rms if rms > 0 else 0.0

        return {
            "peak": float(peak),
            "rms": float(rms),
            "snr": float(snr),
            "dynamic_range": float(dynamic_range),
        }


def run_selfcal_test(
    ms_path: str,
    output_dir: Path,
    test_name: str,
    nvss_seeding: bool = False,
    flux_limit_mjy: Optional[float] = None,
    caltables: Optional[List[str]] = None,
) -> Dict:
    """
    Run self-calibration with specified configuration.

    Args:
        ms_path: Path to measurement set
        output_dir: Output directory for results
        test_name: Name of this test configuration
        nvss_seeding: Whether to use NVSS MODEL_DATA seeding
        flux_limit_mjy: Flux limit for NVSS sources (if nvss_seeding=True)
        caltables: List of calibration tables to apply

    Returns:
        Dictionary with test results
    """
    test_dir = output_dir / test_name
    test_dir.mkdir(parents=True, exist_ok=True)

    LOG.info("=" * 80)
    LOG.info(f"Running test: {test_name}")
    LOG.info(f"  NVSS seeding: {nvss_seeding}")
    if nvss_seeding:
        LOG.info(f"  Flux limit: {flux_limit_mjy} mJy")
    LOG.info("=" * 80)

    # Copy MS to test directory
    ms_name = Path(ms_path).name
    test_ms = test_dir / ms_name
    if not test_ms.exists():
        LOG.info(f"Copying MS to {test_ms}...")
        shutil.copytree(ms_path, test_ms)

    # Run self-calibration
    start_time = time.perf_counter()
    try:
        # Create configuration (using default field="" to process all rephased fields)
        config = SelfCalConfig(
            use_nvss_seeding=nvss_seeding,
            nvss_min_mjy=flux_limit_mjy if nvss_seeding else None,
            max_iterations=5,  # Full test
            # field="" by default - processes all fields after rephasing for maximum SNR
        )

        success, summary = selfcal_ms(
            ms_path=str(test_ms),
            output_dir=str(test_dir),
            config=config,
            initial_caltables=caltables or [],
        )
    except Exception as e:
        LOG.error(f"Self-calibration failed: {e}")
        return {
            "test_name": test_name,
            "success": False,
            "error": str(e),
            "elapsed_time": time.perf_counter() - start_time,
        }

    elapsed_time = time.perf_counter() - start_time

    if not success:
        LOG.warning(f"Self-calibration did not converge")
        return {
            "test_name": test_name,
            "success": False,
            "elapsed_time": elapsed_time,
        }

    # Get final image statistics
    final_image = test_dir / "selfcal_final.fits"
    if not final_image.exists():
        # Try alternate name
        final_image = test_dir / "selfcal_iter4.fits"

    if not final_image.exists():
        LOG.warning(f"Final image not found")
        stats = {"peak": 0.0, "rms": 0.0, "snr": 0.0, "dynamic_range": 0.0}
    else:
        stats = get_image_stats(str(final_image))

    # Extract SNR progression from summary
    snr_progression = summary.get("snr_progression", [])
    initial_snr = snr_progression[0] if snr_progression else 0.0
    final_snr = snr_progression[-1] if snr_progression else stats["snr"]
    snr_improvement = final_snr / initial_snr if initial_snr > 0 else 0.0

    results = {
        "test_name": test_name,
        "success": True,
        "nvss_seeding": nvss_seeding,
        "flux_limit_mjy": flux_limit_mjy,
        "iterations_completed": summary.get("iterations_completed", 0),
        "initial_snr": initial_snr,
        "final_snr": final_snr,
        "snr_improvement": snr_improvement,
        "dynamic_range": stats["dynamic_range"],
        "peak_jy": stats["peak"],
        "rms_jy": stats["rms"],
        "elapsed_time": elapsed_time,
        "snr_progression": snr_progression,
    }

    LOG.info(f"✅ Test completed: {test_name}")
    LOG.info(f"  Initial SNR: {initial_snr:.2f}")
    LOG.info(f"  Final SNR: {final_snr:.2f}")
    LOG.info(f"  SNR improvement: {snr_improvement:.2f}x")
    LOG.info(f"  Time: {elapsed_time:.1f}s")

    return results


def generate_comparison_report(results: List[Dict], output_dir: Path):
    """
    Generate comparison report and visualizations.

    Args:
        results: List of test results
        output_dir: Output directory
    """
    report_path = output_dir / "comparison_report.txt"
    json_path = output_dir / "comparison_results.json"

    # Save JSON results
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    # Generate text report
    with open(report_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("SELF-CALIBRATION STRATEGY COMPARISON\n")
        f.write("=" * 80 + "\n\n")

        # Sort results by SNR improvement
        sorted_results = sorted(
            [r for r in results if r.get("success", False)],
            key=lambda x: x.get("snr_improvement", 0),
            reverse=True,
        )

        if not sorted_results:
            f.write("❌ No successful tests\n")
            return

        # Summary table
        f.write("RESULTS SUMMARY (sorted by SNR improvement)\n")
        f.write("-" * 80 + "\n")
        f.write(
            f"{'Test':<30} {'Initial SNR':>12} {'Final SNR':>12} {'Improvement':>12} {'Time (s)':>10}\n"
        )
        f.write("-" * 80 + "\n")

        for result in sorted_results:
            test_name = result["test_name"]
            initial_snr = result["initial_snr"]
            final_snr = result["final_snr"]
            improvement = result["snr_improvement"]
            elapsed = result["elapsed_time"]
            f.write(
                f"{test_name:<30} {initial_snr:>12.2f} {final_snr:>12.2f} {improvement:>12.2f}x {elapsed:>10.1f}\n"
            )

        f.write("\n\n")

        # Detailed results
        f.write("DETAILED RESULTS\n")
        f.write("=" * 80 + "\n\n")

        for result in sorted_results:
            f.write(f"Test: {result['test_name']}\n")
            f.write("-" * 80 + "\n")
            f.write(f"  NVSS Seeding: {result['nvss_seeding']}\n")
            if result["nvss_seeding"]:
                f.write(f"  Flux Limit: {result['flux_limit_mjy']} mJy\n")
            f.write(f"  Iterations: {result['iterations_completed']}\n")
            f.write(f"  Initial SNR: {result['initial_snr']:.2f}\n")
            f.write(f"  Final SNR: {result['final_snr']:.2f}\n")
            f.write(f"  SNR Improvement: {result['snr_improvement']:.2f}x\n")
            f.write(f"  Dynamic Range: {result['dynamic_range']:.1f}\n")
            f.write(f"  Elapsed Time: {result['elapsed_time']:.1f}s\n")

            # SNR progression
            if result.get("snr_progression"):
                f.write(
                    f"  SNR Progression: {', '.join(f'{s:.2f}' for s in result['snr_progression'])}\n"
                )

            f.write("\n")

        # Recommendations
        f.write("\n")
        f.write("RECOMMENDATIONS\n")
        f.write("=" * 80 + "\n")

        best = sorted_results[0]
        baseline = next((r for r in results if not r.get("nvss_seeding", True)), None)

        if baseline and best["nvss_seeding"]:
            improvement_over_baseline = best["snr_improvement"] / baseline["snr_improvement"]
            f.write(f"✅ Best strategy: {best['test_name']}\n")
            f.write(f"   SNR improvement: {best['snr_improvement']:.2f}x\n")
            f.write(f"   {improvement_over_baseline:.2f}x better than baseline (no NVSS seeding)\n")
            f.write(f"   Recommended for production: YES\n")
        else:
            f.write(f"⚠️  NVSS seeding did not improve results\n")
            f.write(f"   Stick with baseline self-calibration\n")

    LOG.info(f"📊 Report saved to: {report_path}")
    LOG.info(f"📊 JSON results saved to: {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare self-calibration strategies on real observations"
    )
    parser.add_argument("ms_path", help="Path to measurement set")
    parser.add_argument(
        "--output-dir",
        default="/stage/dsa110-contimg/selfcal_comparison",
        help="Output directory for test results",
    )
    parser.add_argument(
        "--caltables",
        nargs="+",
        help="Calibration tables to apply (optional)",
    )
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip baseline test (no NVSS seeding)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: 2 iterations, fewer imaging iterations",
    )

    args = parser.parse_args()

    ms_path = Path(args.ms_path)
    if not ms_path.exists():
        LOG.error(f"MS not found: {ms_path}")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    LOG.info("=" * 80)
    LOG.info("SELF-CALIBRATION STRATEGY COMPARISON")
    LOG.info("=" * 80)
    LOG.info(f"MS: {ms_path}")
    LOG.info(f"Output: {output_dir}")
    LOG.info("=" * 80)

    results = []

    # Test configurations
    tests = []

    if not args.skip_baseline:
        tests.append(
            {
                "name": "baseline_no_nvss",
                "nvss_seeding": False,
                "flux_limit_mjy": None,
            }
        )

    tests.extend(
        [
            {
                "name": "nvss_0.1mJy",
                "nvss_seeding": True,
                "flux_limit_mjy": 0.1,
            },
            {
                "name": "nvss_1.0mJy",
                "nvss_seeding": True,
                "flux_limit_mjy": 1.0,
            },
            {
                "name": "nvss_10.0mJy",
                "nvss_seeding": True,
                "flux_limit_mjy": 10.0,
            },
        ]
    )

    # Run all tests
    for test_config in tests:
        result = run_selfcal_test(
            str(ms_path),
            output_dir,
            test_config["name"],
            nvss_seeding=test_config["nvss_seeding"],
            flux_limit_mjy=test_config["flux_limit_mjy"],
            caltables=args.caltables,
        )
        results.append(result)

    # Generate comparison report
    generate_comparison_report(results, output_dir)

    LOG.info("=" * 80)
    LOG.info("✅ Comparison complete!")
    LOG.info(f"📊 Results in: {output_dir}")
    LOG.info("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
