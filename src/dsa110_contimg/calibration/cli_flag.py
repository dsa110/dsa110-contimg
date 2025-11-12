"""Flag subcommand handler."""

from .flagging import (
    flag_antenna,
    flag_baselines,
    flag_clip,
    flag_elevation,
    flag_extend,
    flag_manual,
    flag_quack,
    flag_rfi,
    flag_shadow,
    flag_summary,
    flag_zeros,
    reset_flags,
)
from dsa110_contimg.utils.validation import ValidationError, validate_ms
import casacore.tables as casatables

table = casatables.table  # noqa: N816
import numpy as np
import argparse
import logging
import sys

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()


logger = logging.getLogger(__name__)


def add_flag_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add 'flag' subcommand parser."""
    parser = subparsers.add_parser(
        "flag",
        help="Flag bad data in a Measurement Set",
        description=(
            "Apply various flagging operations to identify and mark corrupted data.\n\n"
            "Standard flagging modes:\n"
            "  reset      - Unflag all data\n"
            "  zeros      - Flag zero-value data (correlator failures)\n"
            "  rfi        - RFI detection (CASA tfcrop + rflag, or AOFlagger)\n"
            "  shadow     - Flag geometrically shadowed baselines\n"
            "  quack      - Flag beginning/end of scans (antenna settling)\n"
            "  elevation  - Flag low/high elevation observations\n"
            "  clip       - Flag by amplitude thresholds\n"
            "  extend     - Extend existing flags to neighbors\n"
            "  manual     - Manual selection-based flagging\n"
            "  antenna    - Flag specific antennas\n"
            "  baselines  - Flag by UV range\n"
            "  summary    - Report flagging statistics (doesn't flag)\n\n"
            "Examples:\n"
            "  # Standard RFI flagging sequence\n"
            "  python -m dsa110_contimg.calibration.cli flag --ms ms.ms --mode reset\n"
            "  python -m dsa110_contimg.calibration.cli flag --ms ms.ms --mode zeros\n"
            "  python -m dsa110_contimg.calibration.cli flag --ms ms.ms --mode rfi\n\n"
            "  # Flag shadowed baselines\n"
            "  python -m dsa110_contimg.calibration.cli flag --ms ms.ms --mode shadow\n\n"
            "  # Flag first 2 seconds of each scan\n"
            "  python -m dsa110_contimg.calibration.cli flag --ms ms.ms --mode quack --quack-interval 2.0\n\n"
            "  # Flag data below 10 degrees elevation\n"
            "  python -m dsa110_contimg.calibration.cli flag --ms ms.ms --mode elevation --lower-limit 10\n\n"
            "  # Check flagging statistics\n"
            "  python -m dsa110_contimg.calibration.cli flag --ms ms.ms --mode summary"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ms", required=True, help="Path to Measurement Set")
    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "reset",
            "zeros",
            "rfi",
            "shadow",
            "quack",
            "elevation",
            "clip",
            "extend",
            "manual",
            "antenna",
            "baselines",
            "summary",
        ],
        help="Flagging mode",
    )
    parser.add_argument(
        "--datacolumn",
        default="data",
        choices=["data", "corrected_data", "model_data"],
        help="Data column to use (default: data)",
    )
    parser.add_argument(
        "--rfi-backend",
        default="aoflagger",
        choices=["casa", "aoflagger"],
        help="RFI flagging backend (default: aoflagger). Use 'casa' for CASA tfcrop+rflag algorithm.",
    )
    parser.add_argument(
        "--aoflagger-path",
        help=(
            "Path to aoflagger executable, or 'docker' to force Docker usage. "
            "If not specified, defaults to Docker (required on Ubuntu 18.x). "
            "Use explicit path to override with native installation."
        ),
    )
    parser.add_argument(
        "--aoflagger-strategy",
        help="Path to custom AOFlagger Lua strategy file (optional, uses auto-detection if not specified)",
    )

    # Mode-specific arguments
    parser.add_argument(
        "--shadow-tolerance",
        type=float,
        default=0.0,
        help="Shadow tolerance in degrees (for shadow mode)",
    )
    parser.add_argument(
        "--quack-interval",
        type=float,
        default=2.0,
        help="Quack interval in seconds (for quack mode, default: 2.0)",
    )
    parser.add_argument(
        "--quack-mode",
        default="beg",
        choices=["beg", "end", "tail", "endb"],
        help="Quack mode: beg (beginning), end, tail, or endb (default: beg)",
    )
    parser.add_argument(
        "--lower-limit",
        type=float,
        help="Minimum elevation in degrees (for elevation mode)",
    )
    parser.add_argument(
        "--upper-limit",
        type=float,
        help="Maximum elevation in degrees (for elevation mode)",
    )
    parser.add_argument(
        "--clip-min",
        type=float,
        help="Minimum amplitude threshold in Jy (for clip mode)",
    )
    parser.add_argument(
        "--clip-max",
        type=float,
        help="Maximum amplitude threshold in Jy (for clip mode)",
    )
    parser.add_argument(
        "--clip-outside",
        action="store_true",
        default=True,
        help="Flag outside clip range (default: True, use --no-clip-outside for inside)",
    )
    parser.add_argument(
        "--no-clip-outside",
        dest="clip_outside",
        action="store_false",
        help="Flag inside clip range instead of outside",
    )
    parser.add_argument(
        "--grow-time",
        type=float,
        default=0.0,
        help="Fraction of time flagged to flag entire time slot (0-1, for extend mode)",
    )
    parser.add_argument(
        "--grow-freq",
        type=float,
        default=0.0,
        help="Fraction of frequency flagged to flag entire channel (0-1, for extend mode)",
    )
    parser.add_argument(
        "--grow-around",
        action="store_true",
        help="Flag points if most neighbors are flagged (for extend mode)",
    )
    parser.add_argument(
        "--flag-near-time",
        action="store_true",
        help="Flag points before/after flagged regions (for extend mode)",
    )
    parser.add_argument(
        "--flag-near-freq",
        action="store_true",
        help="Flag points adjacent to flagged channels (for extend mode)",
    )
    parser.add_argument(
        "--antenna",
        help="Antenna selection (for antenna or manual mode)",
    )
    parser.add_argument(
        "--uvrange",
        help="UV range selection (for baselines or manual mode, e.g., '2~50m')",
    )
    parser.add_argument(
        "--scan",
        help="Scan selection (for manual mode, e.g., '1~5')",
    )
    parser.add_argument(
        "--spw",
        help="Spectral window selection (for manual mode, e.g., '0:10~20')",
    )
    parser.add_argument(
        "--field",
        help="Field selection (for manual mode)",
    )
    parser.add_argument(
        "--timerange",
        help="Time range selection (for manual mode)",
    )
    parser.add_argument(
        "--correlation",
        help="Correlation selection (for manual mode, e.g., 'RR,LL')",
    )
    return parser


def handle_flag(args: argparse.Namespace) -> int:
    """Handle 'flag' subcommand."""
    # Validate MS before flagging
    try:
        validate_ms(args.ms, check_empty=True)
    except ValidationError as e:
        logger.error("MS validation failed:")
        error_msg = e.format_with_suggestions()
        logger.error(error_msg)
        sys.exit(1)

    # Execute flagging based on mode
    mode = args.mode
    logger.info(f"Flagging mode: {mode}")

    if mode == "reset":
        logger.info("Resetting all flags...")
        reset_flags(args.ms)
        logger.info("✓ All flags reset")

    elif mode == "zeros":
        logger.info("Flagging zero-value data...")
        flag_zeros(args.ms, datacolumn=args.datacolumn)
        logger.info("✓ Zero-value data flagged")

    elif mode == "rfi":
        if args.rfi_backend == "aoflagger":
            logger.info("Flagging RFI using AOFlagger (SumThreshold algorithm)...")
            flag_rfi(
                args.ms,
                datacolumn=args.datacolumn,
                backend="aoflagger",
                aoflagger_path=getattr(args, "aoflagger_path", None),
                strategy=getattr(args, "aoflagger_strategy", None),
            )
        else:
            logger.info("Flagging RFI (CASA tfcrop + rflag)...")
            flag_rfi(args.ms, datacolumn=args.datacolumn, backend="casa")
        logger.info("✓ RFI flagging complete")

    elif mode == "shadow":
        logger.info(
            f"Flagging shadowed baselines (tolerance: {args.shadow_tolerance} deg)..."
        )
        flag_shadow(args.ms, tolerance=args.shadow_tolerance)
        logger.info("✓ Shadow flagging complete")

    elif mode == "quack":
        logger.info(f"Flagging {args.quack_mode} of scans ({args.quack_interval}s)...")
        flag_quack(
            args.ms,
            quackinterval=args.quack_interval,
            quackmode=args.quack_mode,
            datacolumn=args.datacolumn,
        )
        logger.info(
            f"✓ Quack flagging complete ({args.quack_mode}, {args.quack_interval}s)"
        )

    elif mode == "elevation":
        limits = []
        if args.lower_limit is not None:
            limits.append(f"lower={args.lower_limit}°")
        if args.upper_limit is not None:
            limits.append(f"upper={args.upper_limit}°")
        limit_str = ", ".join(limits) if limits else "no limits"
        logger.info(f"Flagging elevation: {limit_str}...")
        flag_elevation(
            args.ms,
            lowerlimit=args.lower_limit,
            upperlimit=args.upper_limit,
            datacolumn=args.datacolumn,
        )
        logger.info("✓ Elevation flagging complete")

    elif mode == "clip":
        if args.clip_min is None or args.clip_max is None:
            logger.error("--clip-min and --clip-max are required for clip mode")
            sys.exit(1)
        clip_range = [args.clip_min, args.clip_max]
        direction = "outside" if args.clip_outside else "inside"
        logger.info(
            f"Flagging amplitudes {direction} range "
            f"[{clip_range[0]}, {clip_range[1]}] Jy..."
        )
        flag_clip(
            args.ms,
            clipminmax=clip_range,
            clipoutside=args.clip_outside,
            datacolumn=args.datacolumn,
        )
        logger.info(
            f"✓ Clip flagging complete ({direction} "
            f"[{clip_range[0]}, {clip_range[1]}] Jy)"
        )

    elif mode == "extend":
        logger.info("Extending existing flags...")
        flag_extend(
            args.ms,
            growtime=args.grow_time,
            growfreq=args.grow_freq,
            growaround=args.grow_around,
            flagneartime=args.flag_near_time,
            flagnearfreq=args.flag_near_freq,
            datacolumn=args.datacolumn,
        )
        logger.info("✓ Flag extension complete")

    elif mode == "manual":
        # Check that at least one selection parameter is provided
        selections = {
            "antenna": args.antenna,
            "scan": args.scan,
            "spw": args.spw,
            "field": args.field,
            "uvrange": args.uvrange,
            "timerange": args.timerange,
            "correlation": args.correlation,
        }
        provided = {k: v for k, v in selections.items() if v is not None}
        if not provided:
            logger.error("At least one selection parameter is required for manual mode")
            logger.error("Examples:")
            logger.error("  --antenna '10' --scan '1~5'")
            logger.error("  --spw '0:10~20'")
            logger.error("  --field '0' --timerange '2025/01/01/10:00:00~10:05:00'")
            sys.exit(1)

        selection_str = ", ".join([f"{k}={v}" for k, v in provided.items()])
        logger.info(f"Manual flagging with selection: {selection_str}")
        flag_manual(
            args.ms,
            antenna=args.antenna,
            scan=args.scan,
            spw=args.spw,
            field=args.field,
            uvrange=args.uvrange,
            timerange=args.timerange,
            correlation=args.correlation,
            datacolumn=args.datacolumn,
        )
        logger.info("✓ Manual flagging complete")

    elif mode == "antenna":
        if not args.antenna:
            logger.error("--antenna is required for antenna mode")
            sys.exit(1)
        logger.info(f"Flagging antenna: {args.antenna}")
        flag_antenna(args.ms, args.antenna, datacolumn=args.datacolumn)
        logger.info(f"✓ Antenna {args.antenna} flagged")

    elif mode == "baselines":
        if not args.uvrange:
            logger.error("--uvrange is required for baselines mode")
            logger.error("Example: --uvrange '2~50m'")
            sys.exit(1)
        logger.info(f"Flagging baselines with UV range: {args.uvrange}")
        flag_baselines(args.ms, args.uvrange, datacolumn=args.datacolumn)
        logger.info(f"✓ Baselines {args.uvrange} flagged")

    elif mode == "summary":
        logger.info("Computing flagging statistics...")
        stats = flag_summary(args.ms)
        logger.info("\n" + "=" * 70)
        logger.info("Flagging Summary")
        logger.info("=" * 70)
        logger.info(f"MS: {args.ms}")
        logger.info(
            f"Total fraction flagged: "
            f"{stats.get('total_fraction_flagged', 0.0)*100:.2f}%"
        )
        logger.info(f"Total rows: {stats.get('n_rows', 0):,}")
        logger.info("=" * 70)

    # Report flagging statistics after flagging (except for summary mode)
    # Use memory-efficient sampling instead of flag_summary() to avoid casaplotserver launch
    if mode != "summary":
        try:
            from dsa110_contimg.utils.ms_helpers import validate_ms_unflagged_fraction

            unflagged_fraction = validate_ms_unflagged_fraction(
                args.ms, sample_size=10000
            )
            flagged_pct = (1.0 - unflagged_fraction) * 100
            logger.info(
                f"\nFlagging complete. Total flagged: {flagged_pct:.2f}% "
                f"(estimated from 10,000 row sample)"
            )
        except Exception as e:
            logger.debug(f"Could not compute flagging statistics: {e}")

    return 0
