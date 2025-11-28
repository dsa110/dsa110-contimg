#!/usr/bin/env python3
"""Command-line interface for self-calibration.

Provides CLI commands for running self-calibration on Measurement Sets.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from dsa110_contimg.calibration.selfcal import (
    SelfCalConfig,
    selfcal_ms,
)
from dsa110_contimg.utils.runtime_safeguards import require_casa6_python

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@require_casa6_python
def cmd_selfcal(args: argparse.Namespace) -> int:
    """Run self-calibration on an MS."""
    setup_logging(args.verbose)

    # Build configuration
    config = SelfCalConfig(
        max_iterations=args.max_iterations,
        min_snr_improvement=args.min_snr_improvement,
        do_delay=args.delay,
        delay_solint=args.delay_solint,
        delay_minsnr=args.delay_minsnr,
        phase_solints=args.phase_solints.split(","),
        phase_minsnr=args.phase_minsnr,
        do_amplitude=not args.no_amplitude,
        amp_solint=args.amp_solint,
        amp_minsnr=args.amp_minsnr,
        imsize=args.imsize,
        cell_arcsec=args.cell_arcsec,
        niter=args.niter,
        threshold=args.threshold,
        robust=args.robust,
        backend=args.backend,
        min_initial_snr=args.min_initial_snr,
        refant=args.refant,
        uvrange=args.uvrange,
        spw=args.spw,
        field=args.field,
        concatenate_fields=args.concatenate_fields,
        use_unicat_seeding=not args.no_unicat_seeding,
        unicat_min_mjy=args.unicat_min_mjy,
        calib_ra_deg=args.calib_ra_deg,
        calib_dec_deg=args.calib_dec_deg,
        calib_flux_jy=args.calib_flux_jy,
        reset_ms=args.reset_ms,
    )

    # Parse initial calibration tables
    initial_caltables = None
    if args.initial_caltables:
        initial_caltables = [ct.strip() for ct in args.initial_caltables.split(",")]
        logger.info(f"Initial calibration tables: {initial_caltables}")

    # Run self-calibration
    logger.info(f"Running self-calibration on {args.ms}")
    logger.info(f"Output directory: {args.output_dir}")

    success, summary = selfcal_ms(
        ms_path=args.ms,
        output_dir=args.output_dir,
        config=config,
        initial_caltables=initial_caltables,
    )

    # Save summary
    summary_path = Path(args.output_dir) / "selfcal_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Summary saved to: {summary_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("SELF-CALIBRATION SUMMARY")
    print("=" * 80)
    print(f"Status: {summary['status']}")
    if "iterations_completed" in summary:
        print(f"Iterations completed: {summary['iterations_completed']}")

    if summary["status"] == "success":
        print(f"Initial SNR: {summary['initial_snr']:.1f}")
        print(f"Best SNR: {summary['best_snr']:.1f}")
        print(f"SNR improvement: {summary['snr_improvement']:.2f}x")
        print(f"Best iteration: {summary['best_iteration']}")
        print(f"\nMessage: {summary['message']}")
    else:
        print(f"Message: {summary.get('message', 'Failed')}")

    print("=" * 80)

    return 0 if success else 1


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Self-calibration for radio interferometric data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required arguments
    parser.add_argument(
        "ms",
        type=str,
        help="Path to Measurement Set",
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="Output directory for self-cal products",
    )

    # Initial calibration
    parser.add_argument(
        "--initial-caltables",
        type=str,
        default=None,
        help="Comma-separated list of initial calibration tables (e.g., BP,GP)",
    )

    # Iteration control
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum number of self-cal iterations",
    )
    parser.add_argument(
        "--min-snr-improvement",
        type=float,
        default=1.05,
        help="Minimum SNR improvement ratio to continue (1.05 = 5%%)",
    )
    parser.add_argument(
        "--min-initial-snr",
        type=float,
        default=10.0,
        help="Minimum initial SNR required to attempt self-cal",
    )

    # MS state management
    parser.add_argument(
        "--reset-ms",
        action="store_true",
        help="Reset MS to pristine state before self-cal: clear CORRECTED_DATA/MODEL_DATA and restore original flags",
    )

    # Delay calibration (removes geometric offsets)
    parser.add_argument(
        "--delay",
        action="store_true",
        help="Enable delay (K) calibration to remove geometric offsets (experimental - testing showed minimal benefit)",
    )
    parser.add_argument(
        "--delay-solint",
        type=str,
        default="inf",
        help="Solution interval for delay calibration",
    )
    parser.add_argument(
        "--delay-minsnr",
        type=float,
        default=3.0,
        help="Minimum SNR for delay solutions",
    )

    # Phase-only iterations
    parser.add_argument(
        "--phase-solints",
        type=str,
        default="30s,60s,inf",
        help="Comma-separated solution intervals for phase-only self-cal",
    )
    parser.add_argument(
        "--phase-minsnr",
        type=float,
        default=3.0,
        help="Minimum SNR for phase-only solutions",
    )

    # Amplitude+phase iteration
    parser.add_argument(
        "--no-amplitude",
        action="store_true",
        help="Skip amplitude+phase self-cal (phase-only)",
    )
    parser.add_argument(
        "--amp-solint",
        type=str,
        default="inf",
        help="Solution interval for amplitude+phase self-cal",
    )
    parser.add_argument(
        "--amp-minsnr",
        type=float,
        default=5.0,
        help="Minimum SNR for amplitude+phase solutions",
    )

    # Imaging parameters
    parser.add_argument(
        "--imsize",
        type=int,
        default=1024,
        help="Image size in pixels",
    )
    parser.add_argument(
        "--cell-arcsec",
        type=float,
        default=None,
        help="Pixel size in arcseconds (auto if not specified)",
    )
    parser.add_argument(
        "--niter",
        type=int,
        default=10000,
        help="Number of CLEAN iterations",
    )
    parser.add_argument(
        "--threshold",
        type=str,
        default="0.0005Jy",
        help="Cleaning threshold (e.g., 0.0005Jy, 0.5mJy)",
    )
    parser.add_argument(
        "--robust",
        type=float,
        default=0.0,
        help="Briggs robust parameter",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="wsclean",
        choices=["wsclean", "casa"],
        help="Imaging backend",
    )

    # Data selection
    parser.add_argument(
        "--field",
        type=str,
        default="",
        help="Field selection",
    )
    parser.add_argument(
        "--concatenate-fields",
        action="store_true",
        help="Concatenate rephased fields into single field (faster gaincal, ~24x speedup)",
    )
    parser.add_argument(
        "--spw",
        type=str,
        default="",
        help="Spectral window selection",
    )
    parser.add_argument(
        "--uvrange",
        type=str,
        default="",
        help="UV range selection",
    )
    parser.add_argument(
        "--refant",
        type=str,
        default=None,
        help="Reference antenna",
    )

    # Model seeding
    parser.add_argument(
        "--no-unicat-seeding",
        action="store_true",
        help="Disable unified catalog model seeding",
    )
    parser.add_argument(
        "--unicat-min-mjy",
        type=float,
        default=10.0,
        help="Minimum flux for unified catalog sources (mJy)",
    )
    parser.add_argument(
        "--calib-ra-deg",
        type=float,
        default=None,
        help="Calibrator RA in degrees (for model seeding)",
    )
    parser.add_argument(
        "--calib-dec-deg",
        type=float,
        default=None,
        help="Calibrator Dec in degrees (for model seeding)",
    )
    parser.add_argument(
        "--calib-flux-jy",
        type=float,
        default=None,
        help="Calibrator flux in Jy (for model seeding)",
    )

    # General
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    try:
        return cmd_selfcal(args)
    except Exception as e:
        logger.error(f"Self-calibration failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
