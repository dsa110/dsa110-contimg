"""QA and diagnostic subcommand handlers."""

import argparse
import json
import logging
import sys

from dsa110_contimg.utils.validation import ValidationError, validate_ms_for_calibration

from .diagnostics import compare_calibration_tables, generate_calibration_diagnostics

logger = logging.getLogger(__name__)


def add_qa_parsers(subparsers: argparse._SubParsersAction) -> None:
    """Add QA/diagnostic subcommand parsers."""
    # check-delays
    pc_delays = subparsers.add_parser(
        "check-delays",
        help="Check if delays are corrected upstream",
    )
    pc_delays.add_argument(
        "--ms",
        required=True,
        help="Path to Measurement Set",
    )
    pc_delays.add_argument(
        "--n-baselines",
        type=int,
        default=100,
        help="Number of baselines to analyze (default: 100)",
    )

    # verify-delays
    pv_delays = subparsers.add_parser(
        "verify-delays",
        help="Verify K-calibration delay solutions",
    )
    pv_delays.add_argument(
        "--ms",
        required=True,
        help="Path to Measurement Set",
    )
    pv_delays.add_argument(
        "--kcal",
        help="Path to K-calibration table (auto-detected if not provided)",
    )
    pv_delays.add_argument(
        "--cal-field",
        help="Calibrator field (for creating K-cal if missing)",
    )
    pv_delays.add_argument(
        "--refant",
        default="103",
        help="Reference antenna (default: 103)",
    )
    pv_delays.add_argument(
        "--no-create",
        action="store_true",
        help="Don't create K-cal table if missing",
    )

    # inspect-delays
    pi_delays = subparsers.add_parser(
        "inspect-delays",
        help="Inspect K-calibration delay values",
    )
    pi_delays.add_argument(
        "--kcal",
        help="Path to K-calibration table",
    )
    pi_delays.add_argument(
        "--ms",
        help="Path to MS (to auto-find K-cal table)",
    )
    pi_delays.add_argument(
        "--find",
        action="store_true",
        help="Find K-cal tables for MS instead of inspecting",
    )

    # list-transits
    pl_transits = subparsers.add_parser(
        "list-transits",
        help="List available calibrator transits with data",
    )
    pl_transits.add_argument(
        "--name",
        required=True,
        help="Calibrator name (e.g., '0834+555')",
    )
    pl_transits.add_argument(
        "--input-dir",
        help="Input directory (default: from env/config)",
    )
    pl_transits.add_argument(
        "--max-days-back",
        type=int,
        default=30,
        help="Maximum days to search back (default: 30)",
    )
    pl_transits.add_argument(
        "--window-minutes",
        type=int,
        default=60,
        help="Search window around transit (default: 60)",
    )
    pl_transits.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # validate
    pv = subparsers.add_parser(
        "validate",
        help="Validate MS before calibrating",
        description=(
            "Validate a Measurement Set is ready for calibration. "
            "Checks MS structure, field selection, reference antenna, and data quality.\n\n"
            "Example:\n"
            "  python -m dsa110_contimg.calibration.cli validate \\\n"
            "    --ms /data/ms/0834_2025-10-30.ms \\\n"
            "    --field 0 --refant 103"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pv.add_argument(
        "--ms",
        required=True,
        help="Path to Measurement Set",
    )
    pv.add_argument(
        "--field",
        required=False,
        default=None,
        help="Calibrator field name/index or range",
    )
    pv.add_argument(
        "--refant",
        required=False,
        default=None,
        help="Reference antenna ID",
    )

    # compare
    pcomp = subparsers.add_parser(
        "compare",
        help="Compare two calibration solutions",
        description=(
            "Compare two calibration tables for consistency. "
            "Useful for regression testing and verifying calibration changes.\n\n"
            "Example:\n"
            "  python -m dsa110_contimg.calibration.cli compare \\\n"
            "    --caltable1 cal1.gcal \\\n"
            "    --caltable2 cal2.gcal \\\n"
            "    --tolerance 1e-6"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pcomp.add_argument(
        "--caltable1",
        required=True,
        help="Path to first calibration table",
    )
    pcomp.add_argument(
        "--caltable2",
        required=True,
        help="Path to second calibration table",
    )
    pcomp.add_argument(
        "--tolerance",
        type=float,
        default=1e-6,
        help="Tolerance for solution agreement (default: 1e-6)",
    )


def handle_check_delays(args: argparse.Namespace) -> int:
    """Handle 'check-delays' subcommand."""
    from dsa110_contimg.qa.calibration_quality import check_upstream_delay_correction

    results = check_upstream_delay_correction(args.ms, args.n_baselines)
    if "error" in results:
        sys.exit(1)
    rec = results.get("recommendation", "unknown")
    print(f"\n{'=' * 70}")
    print("Summary:")
    print(f"{'=' * 70}\n")
    if rec == "likely_corrected":
        print("Recommendation: K-calibration may be skipped")
        print("  Delays appear to be corrected upstream")
    elif rec == "partial":
        print("Recommendation: K-calibration optional but recommended")
        print("  Small residual delays may benefit from correction")
    else:
        print("Recommendation: K-calibration is NECESSARY")
        print("  Significant delays require correction")
    return 0


def handle_verify_delays(args: argparse.Namespace) -> int:
    """Handle 'verify-delays' subcommand."""
    from dsa110_contimg.qa.calibration_quality import verify_kcal_delays

    verify_kcal_delays(args.ms, args.kcal, args.cal_field, args.refant, args.no_create)
    return 0


def handle_inspect_delays(args: argparse.Namespace) -> int:
    """Handle 'inspect-delays' subcommand."""
    from dsa110_contimg.qa.calibration_quality import inspect_kcal_simple

    inspect_kcal_simple(args.kcal, args.ms, args.find)
    return 0


def handle_list_transits(args: argparse.Namespace) -> int:
    """Handle 'list-transits' subcommand."""
    from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
    from dsa110_contimg.conversion.config import CalibratorMSConfig

    config = CalibratorMSConfig.from_env()
    if args.input_dir:
        config.input_dir = args.input_dir
    service = CalibratorMSGenerator.from_config(config, verbose=False)

    transits = service.list_available_transits(
        args.name,
        max_days_back=args.max_days_back,
        window_minutes=args.window_minutes,
    )

    if args.json:
        print(json.dumps(transits, indent=2, default=str))
    else:
        print(f"\nFound {len(transits)} transits for {args.name}:\n")
        for i, transit in enumerate(transits, 1):
            print(f"Transit {i}: {transit['transit_iso']}")
            print(f"  Group ID: {transit['group_id']}")
            print(f"  Files: {len(transit.get('files', []))} subband files")
            print(f"  Has MS: {transit.get('has_ms', False)}")
            print(f"  Days ago: {transit.get('days_ago', 0):.1f}")
            print()
    return 0


def handle_validate(args: argparse.Namespace) -> int:
    """Handle 'validate' subcommand."""
    try:
        warnings = validate_ms_for_calibration(
            args.ms,
            field=args.field if args.field else None,
            refant=args.refant,
        )
        logger.info("\n:check_mark: MS validation passed")
        if warnings:
            logger.info("\nWarnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")

        # Generate comprehensive diagnostics
        logger.info("\nGenerating comprehensive diagnostics...")
        diagnostics = generate_calibration_diagnostics(
            args.ms,
            field=args.field or "",
            refant=args.refant,
            check_caltables=True,
            check_corrected_data=True,
        )
        diagnostics.print_report()

    except ValidationError as e:
        logger.error("Validation failed:")
        error_msg = e.format_with_suggestions()
        logger.error(error_msg)
        sys.exit(1)
    return 0


def handle_compare(args: argparse.Namespace) -> int:
    """Handle 'compare' subcommand."""
    try:
        comparison = compare_calibration_tables(
            args.caltable1,
            args.caltable2,
            tolerance=args.tolerance,
        )
        comparison.print_report()

        if not comparison.solutions_agree:
            logger.warning("Calibration solutions differ significantly")
            sys.exit(1)
        else:
            logger.info(":check_mark: Calibration solutions are consistent")
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        sys.exit(1)
    return 0
