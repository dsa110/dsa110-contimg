#!/usr/bin/env python3
"""
Test self-calibration with catalog-based multi-window masking.

This script tests the self-calibration pipeline with masked cleaning,
where masks are created around cataloged sources from NVSS+FIRST.

Usage:
    python test_selfcal_masked.py [--flux-limit FLUX_MJY]

Examples:
    # Test with 0.1 mJy flux limit
    python test_selfcal_masked.py --flux-limit 0.1

    # Test with 1 mJy flux limit (default)
    python test_selfcal_masked.py --flux-limit 1.0

    # Test with 10 mJy flux limit
    python test_selfcal_masked.py --flux-limit 10.0
"""

import argparse
import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from dsa110_contimg.calibration.selfcal import SelfCalConfig, selfcal_ms

# MS path
MS_PATH = Path("/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms")

# Initial calibration tables (must be strings, not Path objects)
INITIAL_CALTABLES = [
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_bpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_gpcal",
    "/stage/dsa110-contimg/test_data/2025-10-19T14:31:45_0~23_2gcal",
]

# 0834+555 calibrator info
CALIB_RA = 129.278  # deg
CALIB_DEC = 55.381  # deg
CALIB_FLUX = 0.050  # Jy (50 mJy)


def run_masked_selfcal(flux_limit_mjy: float = 1.0):
    """
    Run self-calibration with catalog-based masking.

    Parameters
    ----------
    flux_limit_mjy : float
        Minimum flux in mJy for sources to include in mask (default: 1.0 mJy)
    """
    # Output directory with flux limit in name
    output_dir = Path(f"/stage/dsa110-contimg/test_data/selfcal_masked_{flux_limit_mjy}mJy")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("MASKED SELF-CALIBRATION TEST")
    print("=" * 80)
    print(f"MS:              {MS_PATH}")
    print(f"Output:          {output_dir}")
    print(f"Flux limit:      >{flux_limit_mjy} mJy")
    print("Calibrator:      0834+555")
    print(f"Initial tables:  {len(INITIAL_CALTABLES)} tables")
    print("=" * 80)
    print()

    # Self-cal configuration with masked cleaning
    config = SelfCalConfig(
        # Iteration control
        max_iterations=5,
        min_snr_improvement=1.02,  # 2% improvement threshold
        # Phase-only solutions
        phase_solints=["inf", "120s", "60s"],
        # Amplitude solutions (optional, run after phase)
        do_amplitude=True,
        amp_solint="inf",
        amp_minsnr=5.0,
        # Imaging parameters
        niter=100000,  # Deep clean
        threshold="0.00005Jy",  # ~0.7x RMS
        robust=-0.5,  # Uniform weighting for cleaner PSF
        deconvolver="hogbom",  # Standard deconvolution
        # Field selection (optimize for 0834+555)
        field="0",  # Only main calibrator field
        # Catalog-based masking (KEY FEATURE)
        use_nvss_seeding=True,  # Enable NVSS+FIRST catalog masking
        nvss_min_mjy=flux_limit_mjy,  # Minimum flux in mJy
        # NOTE: Calibrator model seeding is disabled when using NVSS seeding
        # to avoid MODEL_DATA conflicts. The calibrator (0834+555, ~50 mJy)
        # will be included in the NVSS catalog anyway.
        calib_ra_deg=None,
        calib_dec_deg=None,
        calib_flux_jy=None,
    )

    # Run self-calibration
    print("Starting masked self-calibration...")
    print()

    success, summary = selfcal_ms(
        ms_path=MS_PATH,
        output_dir=output_dir,
        config=config,
        initial_caltables=INITIAL_CALTABLES,
    )

    # Print results
    print()
    print("=" * 80)
    print("SELF-CALIBRATION SUMMARY")
    print("=" * 80)
    print(f"Status:      {':check: SUCCESS' if success else ':cross: FAILED'}")
    print(f"Iterations:  {summary.get('iterations_completed', 0)}")
    print()

    if summary.get("iterations"):
        print("SNR Progress:")
        for iter_data in summary["iterations"]:
            iter_num = iter_data.get("iteration", 0)
            calmode = iter_data.get("calmode", "unknown")
            solint = iter_data.get("solint", "unknown")
            snr = iter_data.get("snr", 0.0)
            snr_improvement = iter_data.get("snr_improvement", 0.0)
            print(
                f"  Iter {iter_num} ({calmode:5s}, {solint:5s}): "
                f"SNR = {snr:7.2f}  "
                f"({snr_improvement:.2f}x improvement)"
            )

    print()
    final_snr = summary.get("final_snr", 0.0)
    initial_snr = summary.get("initial_snr", 0.0)
    total_improvement = summary.get("total_snr_improvement", 0.0)
    final_dr = summary.get("final_dynamic_range", 0.0)
    print(f"Final SNR:        {final_snr:.2f}")
    print(f"Initial SNR:      {initial_snr:.2f}")
    print(f"Total SNR gain:   {total_improvement:.2f}x")
    print(f"Dynamic range:    {final_dr:.1f}")
    print()
    print(f"Output directory: {output_dir}")
    print("=" * 80)

    return success, summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test self-calibration with catalog-based masking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test with 0.1 mJy flux limit (many sources, slower)
    python test_selfcal_masked.py --flux-limit 0.1

    # Test with 1 mJy flux limit (default, moderate sources)
    python test_selfcal_masked.py --flux-limit 1.0

    # Test with 10 mJy flux limit (few sources, faster)
    python test_selfcal_masked.py --flux-limit 10.0
        """,
    )

    parser.add_argument(
        "--flux-limit",
        type=float,
        default=1.0,
        help=("Minimum flux in mJy for sources to include in mask " "(default: 1.0)"),
    )

    args = parser.parse_args()

    # Validate flux limit
    if args.flux_limit <= 0:
        print("Error: Flux limit must be positive")
        return 1

    # Run test
    success, summary = run_masked_selfcal(flux_limit_mjy=args.flux_limit)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
