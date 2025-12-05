"""
CLI for DSA-110 calibration.

Provides command-line interface for calibrating Measurement Sets.

Example usage:
    # Full calibration sequence for 0834+555
    python -m dsa110_contimg.calibration.cli calibrate \
        --ms /stage/dsa110-contimg/ms/2025-12-05T12:30:00.ms \
        --calibrator 0834+555 \
        --field 12 \
        --refant 3

    # Phaseshift only (no calibration)
    python -m dsa110_contimg.calibration.cli phaseshift \
        --ms /stage/dsa110-contimg/ms/obs.ms \
        --calibrator 0834+555 \
        --field 12 \
        --output /stage/dsa110-contimg/ms/obs_cal.ms
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Run full calibration sequence."""
    from dsa110_contimg.calibration.runner import run_calibrator

    setup_logging(args.verbose)

    if not Path(args.ms).exists():
        logger.error("MS not found: %s", args.ms)
        return 1

    try:
        caltables = run_calibrator(
            ms_path=args.ms,
            cal_field=args.field,
            refant=args.refant,
            calibrator_name=args.calibrator,
            do_flagging=not args.no_flagging,
            do_k=args.do_delay,
            do_phaseshift=not args.no_phaseshift,
            table_prefix=args.output_prefix,
        )

        logger.info("✓ Calibration complete. Created tables:")
        for ct in caltables:
            logger.info("  - %s", ct)

        return 0

    except Exception as e:
        logger.error("Calibration failed: %s", e)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_phaseshift(args: argparse.Namespace) -> int:
    """Phaseshift calibrator field to calibrator position."""
    from dsa110_contimg.calibration.runner import phaseshift_to_calibrator

    setup_logging(args.verbose)

    if not Path(args.ms).exists():
        logger.error("MS not found: %s", args.ms)
        return 1

    try:
        output_ms, phasecenter = phaseshift_to_calibrator(
            ms_path=args.ms,
            field=args.field,
            calibrator_name=args.calibrator,
            output_ms=args.output,
        )

        logger.info("✓ Phaseshift complete")
        logger.info("  Output MS: %s", output_ms)
        logger.info("  Phasecenter: %s", phasecenter)

        return 0

    except Exception as e:
        logger.error("Phaseshift failed: %s", e)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        prog="dsa110_contimg.calibration.cli",
        description="DSA-110 Calibration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full calibration for 0834+555
  python -m dsa110_contimg.calibration.cli calibrate \\
      --ms /stage/dsa110-contimg/ms/obs.ms \\
      --calibrator 0834+555 --field 12 --refant 3

  # Phaseshift only
  python -m dsa110_contimg.calibration.cli phaseshift \\
      --ms /stage/ms/obs.ms --calibrator 0834+555 --field 12
""",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # calibrate subcommand
    cal_parser = sub.add_parser(
        "calibrate",
        help="Run full calibration sequence (phaseshift → model → bandpass → gains)",
        description=(
            "Performs complete calibration sequence for DSA-110 data:\n"
            "1. Phaseshift calibrator field to calibrator position\n"
            "2. Set model visibilities from catalog\n"
            "3. Solve bandpass\n"
            "4. Solve time-dependent gains"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cal_parser.add_argument("--ms", required=True, help="Path to Measurement Set")
    cal_parser.add_argument(
        "--calibrator",
        required=True,
        help="Calibrator name (e.g., '0834+555', '3C286')",
    )
    cal_parser.add_argument(
        "--field",
        required=True,
        help="Field selection (e.g., '12' or '11~13')",
    )
    cal_parser.add_argument(
        "--refant",
        default="3",
        help="Reference antenna (default: 3)",
    )
    cal_parser.add_argument(
        "--output-prefix",
        default=None,
        help="Prefix for calibration table names (default: auto)",
    )
    cal_parser.add_argument(
        "--no-flagging",
        action="store_true",
        help="Skip pre-calibration flagging",
    )
    cal_parser.add_argument(
        "--do-delay",
        action="store_true",
        help="Solve for K (delay) calibration",
    )
    cal_parser.add_argument(
        "--no-phaseshift",
        action="store_true",
        help="Skip phaseshift (only if data already phased to calibrator)",
    )
    cal_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    cal_parser.set_defaults(func=cmd_calibrate)

    # phaseshift subcommand
    ps_parser = sub.add_parser(
        "phaseshift",
        help="Phaseshift calibrator field to calibrator position only",
        description=(
            "Extracts calibrator field and phaseshifts to calibrator's true position.\n"
            "This is step 1 of calibration - use 'calibrate' for full sequence."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ps_parser.add_argument("--ms", required=True, help="Path to input Measurement Set")
    ps_parser.add_argument(
        "--calibrator",
        required=True,
        help="Calibrator name (e.g., '0834+555')",
    )
    ps_parser.add_argument(
        "--field",
        required=True,
        help="Field selection (e.g., '12')",
    )
    ps_parser.add_argument(
        "--output",
        default=None,
        help="Output MS path (default: {input}_cal.ms)",
    )
    ps_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    ps_parser.set_defaults(func=cmd_phaseshift)

    return parser


def main(argv: Optional[list] = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 2

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
