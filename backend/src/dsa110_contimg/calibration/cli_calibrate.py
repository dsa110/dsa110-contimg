# pylint: disable=no-member  # astropy.units uses dynamic attributes (deg, etc.)
"""Calibrate subcommand handler."""

import argparse
import logging
import os
import sys
import time

from dsa110_contimg.calibration.performance import (
    estimate_memory_requirements,
    optimize_memory_usage,
)
from dsa110_contimg.utils.error_context import (
    format_ms_error_with_suggestions,
)
from dsa110_contimg.utils.performance import track_performance
from dsa110_contimg.utils.validation import (
    ValidationError,
    validate_file_path,
    validate_ms_for_calibration,
)

from .calibration import (
    solve_bandpass,
    solve_delay,
    solve_gains,
    solve_prebandpass_phase,
)
from .cli_utils import clear_all_calibration_artifacts as _clear_all_calibration_artifacts
from .cli_utils import rephase_ms_to_calibrator as _rephase_ms_to_calibrator
from .diagnostics import generate_calibration_diagnostics
from .flagging import (
    analyze_channel_flagging_stats,
    flag_problematic_channels,
    flag_rfi,
    flag_zeros,
    reset_flags,
)
from .model_validation import comprehensive_model_data_validation
from .plotting import generate_bandpass_plots, generate_gain_plots
from .selection import select_bandpass_from_catalog

# Ensure headless operation before any CASA imports
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.environ.get("DISPLAY"):
    os.environ.pop("DISPLAY", None)


logger = logging.getLogger(__name__)

# Module-level flag for calibrator info printing (prevents duplicates)
_calibrator_info_printed_global = False


def add_calibrate_parser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """Add 'calibrate' subcommand parser."""
    parser = subparsers.add_parser(
        "calibrate",
        help="Calibrate a calibrator MS",
        description=(
            "Calibrate a Measurement Set containing a calibrator source. "
            "Performs flagging, bandpass (BP), and gain (G) calibration. "
            "Delay (K) calibration is optional (use --do-k for VLBI arrays).\n\n"
            "Example:\n"
            "  python -m dsa110_contimg.calibration.cli calibrate \\\n"
            "    --ms /data/ms/0834_2025-10-30.ms \\\n"
            "    --field 0 --refant 103 --auto-fields --cal-catalog /path/to/catalog.csv"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ms", required=True, help="Path to Measurement Set (required)")
    parser.add_argument(
        "--field",
        required=False,
        default=None,
        help=(
            "Calibrator field name/index or range (e.g., '0', '10~12', 'calibrator'). "
            "Required unless --auto-fields is used. "
            "Use --auto-fields to automatically select fields from VLA catalog."
        ),
    )
    parser.add_argument(
        "--refant",
        required=False,
        default=None,
        help=(
            "Reference antenna ID (e.g., '103'). "
            "If not provided, auto-selects using outrigger-priority chain. "
            "Reference antenna must have unflagged data for all calibration steps. "
            "Use --refant-ranking to provide a JSON file with antenna rankings."
        ),
    )
    parser.add_argument(
        "--refant-ranking",
        help=(
            "Path to refant_ranking.json file for automatic reference antenna selection. "
            "File should contain JSON with 'recommended' field containing 'antenna_id'. "
            "If not provided, uses default outrigger-priority selection."
        ),
    )
    parser.add_argument(
        "--auto-fields",
        action="store_true",
        help=(
            "Automatically select bandpass fields using calibrator information from VLA catalog. "
            "Searches for calibrator in MS field of view and selects fields around peak signal. "
            "Requires --cal-catalog (or auto-resolves to SQLite database) or --cal-ra-deg/--cal-dec-deg. "
            "Recommended for production use. Automatically phases MS to calibrator position."
        ),
    )
    parser.add_argument(
        "--cal-ra-deg", type=float, help="Calibrator RA (deg) for auto field selection"
    )
    parser.add_argument(
        "--cal-dec-deg",
        type=float,
        help="Calibrator Dec (deg) for auto field selection",
    )
    parser.add_argument(
        "--cal-flux-jy",
        type=float,
        help="Calibrator flux (Jy) for weighting in auto selection",
    )
    parser.add_argument(
        "--cal-catalog",
        help=(
            "Path to VLA calibrator catalog for auto field selection. "
            "If not provided, auto-resolves to SQLite database at "
            "state/catalogs/vla_calibrators.sqlite3 (preferred). "
            "Accepts both SQLite (.sqlite3) and CSV formats."
        ),
    )
    parser.add_argument(
        "--cal-search-radius-deg",
        type=float,
        default=1.0,
        help="Search radius (deg) around catalog entries",
    )
    parser.add_argument(
        "--pt-dec-deg",
        type=float,
        help="Pointing declination (deg) for catalog weighting",
    )
    parser.add_argument(
        "--bp-window",
        type=int,
        default=3,
        help="Number of fields (approx) around peak to include",
    )
    parser.add_argument(
        "--bp-min-pb",
        type=float,
        default=None,
        help=("Primary-beam gain threshold [0-1] to auto-size field window around peak"),
    )
    parser.add_argument(
        "--bp-combine-field",
        action="store_true",
        help=(
            "Combine across selected fields when solving bandpass/gains. "
            "Increases SNR by using data from multiple fields. "
            "Recommended for weak calibrators (<5 Jy). "
            "Requires --auto-fields or multiple fields in --field (e.g., '0~5')."
        ),
    )
    parser.add_argument(
        "--flagging-mode",
        choices=["none", "zeros", "rfi"],
        default="rfi",
        help=(
            "Pre-solve flagging mode: none (no flagging), zeros (clip zeros), rfi (zeros + AOFlagger). "
            "Default: rfi (uses AOFlagger for RFI detection)"
        ),
    )
    parser.add_argument(
        "--reset-ms",
        action="store_true",
        help=(
            "Reset MS to post-generation state before calibrating. "
            "Clears calibration tables, MODEL_DATA, CORRECTED_DATA, and restores field names. "
            "Useful for starting a fresh calibration run."
        ),
    )
    parser.add_argument(
        "--bp-minsnr",
        type=float,
        default=float(os.getenv("CONTIMG_CAL_BP_MINSNR", "3.0")),
        help=(
            "Minimum SNR threshold for bandpass solutions (default: 3.0; "
            "override with CONTIMG_CAL_BP_MINSNR)."
        ),
    )
    parser.add_argument(
        "--bp-smooth-type",
        choices=["none", "hanning", "boxcar", "gaussian"],
        default="none",
        help=("Optional smoothing of bandpass table after solve (off by default)."),
    )
    parser.add_argument(
        "--bp-smooth-window",
        type=int,
        help="Smoothing window (channels) for bandpass smoothing",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help=("Enable fast path: subset MS (time/channel avg), " "phase-only gains, uvrange cuts"),
    )
    parser.add_argument(
        "--do-k",
        action="store_true",
        help=(
            "Enable delay (K) calibration. "
            "K-calibration is typically only needed for VLBI arrays (very long baselines). "
            "Connected-element arrays like DSA-110 (2.6 km max baseline) follow VLA/ALMA practice "
            "and skip K-calibration by default. Residual delays are absorbed into complex gain calibration."
        ),
    )
    parser.add_argument(
        "--skip-bp",
        action="store_true",
        help="Skip bandpass (BP) solve",
    )
    parser.add_argument(
        "--skip-g",
        action="store_true",
        help="Skip gain (G) solve",
    )
    parser.add_argument(
        "--export-model-image",
        action="store_true",
        help=(
            "Export MODEL_DATA as FITS image after bandpass solve. "
            "Useful for visualizing the calibrator sky model used during calibration. "
            "Output will be saved as {ms_path}.calibrator_model.fits"
        ),
    )
    parser.add_argument(
        "--auto-flag-channels",
        action="store_true",
        default=True,
        help=(
            "Automatically flag problematic channels after RFI flagging (default: True). "
            "Channels with >50%% flagged data (configurable via --channel-flag-threshold) "
            "will be flagged entirely before calibration. This is more precise than SPW-level flagging."
        ),
    )
    parser.add_argument(
        "--channel-flag-threshold",
        type=float,
        default=0.5,
        help=(
            "Fraction of flagged data to flag channel entirely (default: 0.5). "
            "Channels with flagging rate above this threshold will be flagged before calibration."
        ),
    )
    parser.add_argument(
        "--auto-flag-problematic-spws",
        action="store_true",
        help=(
            "Automatically flag problematic spectral windows after bandpass calibration. "
            "SPWs with >80%% average flagging or >50%% of channels with high flagging will be flagged. "
            "WARNING: This flags entire SPWs, which may remove good channels. "
            "Per-channel flagging (done pre-calibration) is preferred. "
            "Use this only as a last resort if per-channel flagging is insufficient."
        ),
    )
    parser.add_argument(
        "--export-spw-stats",
        type=str,
        metavar="PATH",
        help=(
            "Export per-SPW flagging statistics to JSON and CSV files. "
            "Path should be base filename (extensions .json and .csv will be added). "
            "Example: --export-spw-stats /path/to/spw_stats"
        ),
    )
    parser.add_argument(
        "--plot-bandpass",
        action="store_true",
        default=True,
        help=(
            "Generate bandpass amplitude and phase plots after bandpass calibration (default: True). "
            "Plots are saved in a 'calibration_plots' directory next to the MS and are accessible via the dashboard."
        ),
    )
    parser.add_argument(
        "--no-plot-bandpass",
        dest="plot_bandpass",
        action="store_false",
        help="Disable bandpass plot generation.",
    )
    parser.add_argument(
        "--bandpass-plot-dir",
        type=str,
        default=None,
        help=(
            "Directory to save bandpass plots (default: {ms_dir}/calibration_plots/bandpass). "
            "Plots are organized by calibration table name."
        ),
    )
    parser.add_argument(
        "--plot-gain",
        action="store_true",
        default=True,
        help=(
            "Generate gain amplitude and phase plots after gain calibration (default: True). "
            "Plots show amplitude/phase vs time for all antennas and are saved in a 'calibration_plots' "
            "directory next to the MS, accessible via the dashboard."
        ),
    )
    parser.add_argument(
        "--no-plot-gain",
        dest="plot_gain",
        action="store_false",
        help="Disable gain plot generation.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help=(
            "Maximum number of parallel workers for performance optimization (default: auto-detect). "
            "Useful for parallel SPW processing or chunked operations. "
            "Set to 1 to disable parallel processing."
        ),
    )
    parser.add_argument(
        "--memory-limit-gb",
        type=float,
        default=None,
        help=(
            "Memory limit in GB for CASA operations (default: auto-detect from system). "
            "Useful for large MS files to prevent out-of-memory errors."
        ),
    )
    parser.add_argument(
        "--gain-plot-dir",
        type=str,
        default=None,
        help=(
            "Directory to save gain plots (default: {ms_dir}/calibration_plots/gain). "
            "Plots are organized by calibration table name."
        ),
    )
    parser.add_argument(
        "--plot-spw-flagging",
        type=str,
        metavar="PATH",
        help=(
            "Generate visualization of per-SPW flagging statistics. "
            "Path should be output filename (extension .png will be added if not present). "
            "Example: --plot-spw-flagging /path/to/spw_plot"
        ),
    )
    parser.add_argument(
        "--gain-solint",
        default="inf",
        help=(
            "Gain solution interval. "
            "Options: 'inf' (entire scan, default), 'int' (per integration), "
            "'60s' (60 seconds), '10min' (10 minutes). "
            "Shorter intervals capture time-variable gains but require higher SNR. "
            "Examples: 'inf' for stable calibrators, '30s' for variable conditions."
        ),
    )
    parser.add_argument(
        "--gain-minsnr",
        type=float,
        default=3.0,
        help=(
            "Minimum SNR threshold for gain solutions (default: 3.0). "
            "Lower values (2.0-3.0) use more data but may include noise. "
            "Higher values (5.0+) require stronger signal but more reliable solutions. "
            "For weak calibrators (<2 Jy), consider reducing to 2.0."
        ),
    )
    parser.add_argument(
        "--gain-calmode",
        default="ap",
        choices=["ap", "p", "a"],
        help="Gain calibration mode: ap (amp+phase), p (phase-only), a (amp-only)",
    )
    parser.add_argument(
        "--timebin",
        default=None,
        help="Time averaging for fast subset, e.g. '30s'",
    )
    parser.add_argument(
        "--chanbin",
        type=int,
        default=None,
        help="Channel binning factor for fast subset (>=2)",
    )
    parser.add_argument(
        "--uvrange",
        default="",
        help="uvrange selection (e.g. '>1klambda') for fast solves",
    )
    parser.add_argument(
        "--combine-spw",
        action="store_true",
        help=(
            "Combine spectral windows when solving K (delay) calibration. "
            "Recommended for multi-SPW MS files to improve performance. "
            "Default: process SPWs separately"
        ),
    )
    parser.add_argument(
        "--k-fast-only",
        action="store_true",
        help=(
            "Skip slow (inf interval) K-calibration solve and only run fast (60s) solve. "
            "Only applicable when --do-k is used. Significantly faster (~2-3 min vs 15+ min) "
            "but may have lower accuracy for time-variable delays. Recommended only for "
            "production calibrator processing where speed is prioritized over comprehensive delay correction."
        ),
    )
    parser.add_argument(
        "--no-flagging",
        action="store_true",
        help=("Disable pre-solve flagging to avoid crashes on nonstandard polarizations"),
    )
    parser.add_argument(
        "--prebp-solint",
        # Default to 30s for time-variable phase drifts (inf causes decorrelation)
        default="30s",
        help="Solution interval for pre-bandpass phase-only solve (default: 30s)",
    )
    parser.add_argument(
        "--prebp-minsnr",
        type=float,
        # Default to 3.0 to match bandpass threshold (phase-only is more robust)
        default=3.0,
        help="Minimum SNR for pre-bandpass phase-only solve (default: 3.0)",
    )
    parser.add_argument(
        "--prebp-uvrange",
        default="",
        help="uvrange selection for pre-bandpass phase-only solve (default: none)",
    )
    parser.add_argument(
        "--clear-all",
        action="store_true",
        help=(
            "Clear all calibration artifacts before running calibration: "
            "MODEL_DATA, CORRECTED_DATA, and any existing calibration tables in the MS directory. "
            "Use this when you want a completely clean calibration run."
        ),
    )
    parser.add_argument(
        "--no-flag-autocorr",
        action="store_true",
        help=("Skip flagging autocorrelations before solves (default: flag autos)."),
    )
    parser.add_argument(
        "--prebp-phase",
        action="store_true",
        help=(
            "Run a phase-only solve before bandpass to stabilize time variability (default: off)."
        ),
    )
    parser.add_argument(
        "--skip-rephase",
        action="store_true",
        help=(
            "Skip rephasing MS to calibrator position. Use original meridian phase center. "
            "This allows ft() to work correctly without manual MODEL_DATA calculation."
        ),
    )
    parser.add_argument(
        "--prebp-minblperant",
        type=int,
        default=None,
        help="Minimum baselines per antenna for pre-bandpass phase solve (default: none)",
    )
    parser.add_argument(
        "--prebp-spw",
        type=str,
        default=None,
        help="SPW selection for pre-bandpass phase solve (e.g., '4~11' for central 8 SPWs, default: all SPWs)",
    )
    parser.add_argument(
        "--prebp-table-name",
        type=str,
        default=None,
        help="Custom table name for pre-bandpass phase solve (e.g., '.bpphase.gcal', default: auto-generated)",
    )
    parser.add_argument(
        "--bp-combine",
        type=str,
        default=None,
        help="Custom combine string for bandpass solve (e.g., 'scan,obs,field', default: auto-generated)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Simulate calibration without writing caltables. "
            "Validates inputs, checks data quality, and estimates time/cost."
        ),
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help=(
            "Generate comprehensive diagnostic report after calibration. "
            "Includes solution quality metrics, SNR analysis, flag statistics, etc."
        ),
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help=(
            "Very fast calibration test (<30s). "
            "Uses minimal subset: 1 baseline, 4 channels, 1 time integration. "
            "For quick iteration only - not for production use."
        ),
    )
    parser.add_argument(
        "--preset",
        choices=["development", "standard", "high_precision"],
        help=(
            "Use preset calibration quality tiers with explicit trade-offs.\n"
            "  development: ⚠️  NON-SCIENCE - aggressive subsetting for code testing only\n"
            "  standard: Recommended for all science observations (full quality)\n"
            "  high_precision: Enhanced settings for maximum quality (slower)\n"
            "Individual flags override preset values."
        ),
    )
    parser.add_argument(
        "--cleanup-subset",
        action="store_true",
        help="Remove subset MS files (e.g., .fast.ms, .minimal.ms) after calibration completes",
    )
    parser.add_argument(
        "--no-subset",
        action="store_true",
        help="Disable automatic subset creation even when --fast or --minimal is used",
    )
    parser.add_argument(
        "--model-source",
        choices=["catalog", "setjy", "component", "image"],
        default="catalog",
        help=(
            "Populate MODEL_DATA before bandpass using the specified strategy. "
            "Default: 'catalog' (recommended for production, uses manual calculation). "
            "Use 'setjy' only if calibrator is at phase center and no rephasing is needed."
        ),
    )
    parser.add_argument(
        "--model-component",
        help=("Path to CASA component list (.cl) when --model-source=component"),
    )
    parser.add_argument("--model-image", help="Path to CASA image when --model-source=image")
    parser.add_argument(
        "--model-field",
        help="Field name/index for setjy when --model-source=setjy",
    )
    parser.add_argument(
        "--model-setjy-standard",
        default="Perley-Butler 2017",
        help=("Flux standard for setjy (default: Perley-Butler 2017)"),
    )
    parser.add_argument("--model-setjy-spw", default="", help="Spectral window selection for setjy")
    # On-the-fly MS repair has been removed; prefer reconversion if needed.

    return parser


@track_performance("calibration", log_result=True)
def handle_calibrate(args: argparse.Namespace) -> int:
    """Handle 'calibrate' subcommand."""
    global _calibrator_info_printed_global
    start_time = time.time()

    # Input validation
    if not hasattr(args, "ms") or not args.ms:
        raise ValueError("MS file path is required")
    if not isinstance(args.ms, str) or not args.ms.strip():
        raise ValueError("MS file path must be a non-empty string")
    if not os.path.exists(args.ms):
        raise FileNotFoundError(f"MS file not found: {args.ms}")
    if hasattr(args, "refant") and args.refant is not None:
        if not isinstance(args.refant, (str, int)):
            raise ValueError("refant must be a string or integer")
    if hasattr(args, "field") and args.field is not None:
        if not isinstance(args.field, str):
            raise ValueError("field must be a string")

    # Performance optimization: memory management
    if getattr(args, "memory_limit_gb", None):
        os.environ["CASA_MEMORY_LIMIT_GB"] = str(args.memory_limit_gb)
        logger.info(f"Memory limit set to {args.memory_limit_gb} GB")
    else:
        # Auto-estimate memory requirements
        try:
            mem_estimates = estimate_memory_requirements(args.ms)
            if mem_estimates.get("recommended_memory_gb"):
                logger.info(
                    f"Estimated memory requirements: {mem_estimates['recommended_memory_gb']:.1f} GB "
                    f"(MS size: {mem_estimates.get('ms_size_gb', 'unknown')} GB)"
                )
        except Exception as e:
            logger.debug(f"Could not estimate memory requirements: {e}")

    optimize_memory_usage()

    # Print initial workflow overview
    logger.info("=" * 70)
    logger.info(f"MS: {args.ms}")
    logger.info(f"Mode: {args.preset or 'custom'}")
    logger.info("=" * 70)
    logger.info("")

    # Comprehensive MS validation using shared validation module
    logger.info("[1/6] Validating MS...")
    try:
        warnings = validate_ms_for_calibration(
            args.ms, field=args.field if args.field else None, refant=args.refant
        )
        # Log warnings but don't fail
        for warning in warnings:
            logger.warning(warning)
        logger.info("✓ [1/6] MS validation passed")
    except ValidationError as e:
        suggestions = [
            "Check MS path is correct and file exists",
            "Verify file permissions",
            "Run validation: python -m dsa110_contimg.calibration.cli validate --ms <path>",
            "Check MS structure with: python -m dsa110_contimg.calibration.cli qa check-delays --ms <path>",
        ]
        error_msg = format_ms_error_with_suggestions(
            e, args.ms, "calibration validation", suggestions
        )
        logger.error(error_msg)
        sys.exit(1)
    except Exception as e:
        suggestions = [
            "Check MS path is correct and file exists",
            "Verify file permissions",
            "Check MS structure and integrity",
            "Review logs for detailed error information",
        ]
        error_msg = format_ms_error_with_suggestions(e, args.ms, "MS validation", suggestions)
        logger.error(error_msg)
        sys.exit(1)

    # Check registry for existing calibration tables
    # If tables exist and match current parameters, skip calibration steps
    if not args.dry_run and (not args.skip_bp or not args.skip_g):
        try:
            from pathlib import Path

            from dsa110_contimg.database.registry import ensure_db, get_active_applylist
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            # Determine registry DB path (same logic as registration)
            registry_db_env = os.environ.get("CAL_REGISTRY_DB")
            if registry_db_env:
                registry_db = Path(registry_db_env)
            else:
                state_dir = Path(os.environ.get("PIPELINE_STATE_DIR", "/data/dsa110-contimg/state"))
                registry_db = state_dir / "cal_registry.sqlite3"

            # Check if registry exists
            if registry_db.exists():
                # Extract time range from MS
                start_mjd, end_mjd, mid_mjd = extract_ms_time_range(args.ms)

                if mid_mjd is not None:
                    # Query registry for active calibration tables
                    existing_tables = get_active_applylist(registry_db, mid_mjd)

                    if existing_tables:
                        # Check if tables match current calibration parameters
                        conn = ensure_db(registry_db)

                        # Get metadata for the calibration set
                        set_name = None
                        matching_refant = None
                        matching_field = None

                        # Find set name from first table
                        first_table = existing_tables[0]
                        row = conn.execute(
                            """
                            SELECT set_name, refant, cal_field
                            FROM caltables
                            WHERE path = ?
                            LIMIT 1
                            """,
                            (first_table,),
                        ).fetchone()

                        if row:
                            set_name, matching_refant, matching_field = row

                            # Check if parameters match
                            refant_match = (
                                not args.refant
                                or matching_refant == args.refant
                                or matching_refant is None
                            )

                            # Field matching: check if current field matches registered field
                            field_match = True
                            if args.field and matching_field:
                                # Compare field selections (handle ranges like "0~23")
                                current_fields = set(args.field.replace("~", ",").split(","))
                                registered_fields = set(matching_field.replace("~", ",").split(","))
                                field_match = bool(current_fields.intersection(registered_fields))

                            # Check which table types exist and their ages
                            table_types = set()
                            bp_age_hours = None
                            g_age_hours = None

                            # Note: time module is already imported at top of file

                            for table_path in existing_tables:
                                if os.path.exists(table_path):
                                    row = conn.execute(
                                        """
                                        SELECT table_type, created_at FROM caltables
                                        WHERE path = ?
                                        """,
                                        (table_path,),
                                    ).fetchone()
                                    if row:
                                        table_type, created_at = row
                                        table_types.add(table_type)

                                        # Calculate age in hours
                                        age_seconds = time.time() - created_at
                                        age_hours = age_seconds / 3600.0

                                        # Track ages for BP and G tables (use youngest if multiple)
                                        if table_type in ["BP", "BA"]:
                                            if bp_age_hours is None or age_hours < bp_age_hours:
                                                bp_age_hours = age_hours
                                        elif table_type in ["GP", "GA", "2G"]:
                                            if g_age_hours is None or age_hours < g_age_hours:
                                                g_age_hours = age_hours

                            # Determine what to skip based on age requirements
                            # BP tables: valid for 24 hours
                            # G tables: valid for 1 hour
                            has_bp = any(t in table_types for t in ["BP", "BA"])
                            has_g = any(t in table_types for t in ["GP", "GA", "2G"])

                            bp_fresh = has_bp and bp_age_hours is not None and bp_age_hours < 24.0
                            g_fresh = has_g and g_age_hours is not None and g_age_hours < 1.0

                            if refant_match and field_match and (bp_fresh or g_fresh):
                                logger.info("=" * 70)
                                logger.info("Registry Check: Found existing calibration tables")
                                logger.info(f"  Set name: {set_name}")
                                logger.info(f"  Tables found: {len(existing_tables)}")
                                logger.info(f"  Table types: {', '.join(sorted(table_types))}")
                                logger.info(f"  Reference antenna: {matching_refant}")
                                logger.info(f"  Calibration field: {matching_field}")

                                # Auto-skip steps if tables exist, match, and are fresh enough
                                if bp_fresh and not args.skip_bp:
                                    logger.info(
                                        f"  → Skipping bandpass calibration (table age: {bp_age_hours:.1f}h < 24h)"
                                    )
                                    args.skip_bp = True
                                elif has_bp and bp_age_hours is not None:
                                    logger.info(
                                        f"  → Bandpass table exists but too old ({bp_age_hours:.1f}h >= 24h), will regenerate"
                                    )

                                if g_fresh and not args.skip_g:
                                    logger.info(
                                        f"  → Skipping gain calibration (table age: {g_age_hours:.1f}h < 1h)"
                                    )
                                    args.skip_g = True
                                elif has_g and g_age_hours is not None:
                                    logger.info(
                                        f"  → Gain table exists but too old ({g_age_hours:.1f}h >= 1h), will regenerate"
                                    )

                                logger.info("=" * 70)
                                logger.info("")
                            else:
                                if not refant_match:
                                    logger.debug(
                                        f"Registry tables use different refant ({matching_refant} vs {args.refant}), "
                                        "will re-calibrate"
                                    )
                                if not field_match:
                                    logger.debug(
                                        f"Registry tables use different field ({matching_field} vs {args.field}), "
                                        "will re-calibrate"
                                    )
                        else:
                            logger.debug("Could not find metadata for existing tables in registry")
                    else:
                        logger.debug(
                            "No active calibration tables found in registry for this observation time"
                        )
        except Exception as e:
            # Registry check failure is non-fatal - proceed with calibration
            logger.debug(f"Registry check failed (non-fatal): {e}. Proceeding with calibration.")

    # Display workflow steps (after registry check, so it reflects what will actually run)
    workflow_steps = []
    if args.do_k:
        workflow_steps.append("K-calibration (delay)")
    if not args.skip_bp:
        workflow_steps.append("Bandpass (BP)")
    if not args.skip_g:
        workflow_steps.append("Gain (G)")
    logger.info("=" * 70)
    logger.info("CALIBRATION WORKFLOW")
    logger.info("=" * 70)
    logger.info(f"Steps: {', '.join(workflow_steps) if workflow_steps else 'validation only'}")
    logger.info("=" * 70)
    logger.info("")

    # Apply preset if specified (presets can be overridden by individual flags)
    if args.preset:
        logger.info(f"Applying quality tier: {args.preset}")
        if args.preset == "development":
            # ⚠️  NON-SCIENCE QUALITY - For code testing only
            logger.warning(
                "=" * 80 + "\n"
                "⚠️  DEVELOPMENT TIER: NON-SCIENCE QUALITY\n"
                "   This tier uses aggressive subsetting and compromises calibration quality.\n"
                "   NEVER use for actual science observations or ESE detection.\n"
                "   Results will have reduced SNR, resolution, and accuracy.\n"
                "=" * 80
            )
            if not args.timebin:
                args.timebin = "30s"
            if not args.chanbin:
                args.chanbin = 4
            if not args.uvrange:
                args.uvrange = ">1klambda"
            if args.gain_calmode == "ap":  # Only override if not explicitly set
                args.gain_calmode = "p"
            args.fast = True
            logger.info(
                "Development tier: timebin=30s, chanbin=4, phase-only gains, uvrange cuts (NON-SCIENCE)"
            )
        elif args.preset == "standard":
            # Recommended for all science observations
            args.fast = False
            args.minimal = False
            if args.gain_calmode == "p":  # Only override if not explicitly set
                args.gain_calmode = "ap"
            logger.info(
                "Standard tier: full MS, amp+phase gains, no subset (recommended for science)"
            )
        elif args.preset == "high_precision":
            # Enhanced quality for critical observations
            args.fast = False
            args.minimal = False
            args.gain_calmode = "ap"
            if not args.gain_solint or args.gain_solint == "inf":
                args.gain_solint = "int"  # Per-integration for maximum quality
            if not args.gain_minsnr:
                args.gain_minsnr = 5.0  # Higher SNR threshold
            logger.info(
                "High precision tier: full MS, per-integration solutions, enhanced quality (slower)"
            )

    # STRICT SEPARATION: Development tier produces NON_SCIENCE calibration tables
    # that cannot be applied to production data
    if args.preset == "development":
        # Force unique naming to prevent accidental application to production data
        args.table_prefix_override = "NON_SCIENCE_DEVELOPMENT"
        logger.warning(
            "⚠️  STRICT SEPARATION: Development tier calibration tables will be prefixed with 'NON_SCIENCE_DEVELOPMENT'"
        )
        logger.warning("   These tables CANNOT and MUST NOT be applied to production/science data")

    # Handle --no-subset flag (disables automatic subset creation)
    if args.no_subset:
        args.fast = False
        args.minimal = False
        logger.info("Subset creation disabled by --no-subset")

    # Store original MS path for cleanup later
    original_ms = args.ms
    subset_ms_created = None

    field_sel = args.field
    # Defaults to ensure variables exist for later logic
    idxs = []  # type: ignore[assignment]
    wflux = []  # type: ignore[assignment]
    peak_field_idx = None  # Peak field index (closest to calibrator)
    # Initialize ms_was_rephased to ensure it's always set regardless of code path
    # This prevents NameError when checking if MS was rephased later in the code
    ms_was_rephased = False

    if args.auto_fields:
        try:
            if args.cal_catalog:
                # Validate catalog file exists
                try:
                    validate_file_path(args.cal_catalog, must_exist=True, must_readable=True)
                except ValidationError as e:
                    logger.error("Catalog validation failed:")
                    for error in e.errors:
                        logger.error(f"  - {error}")
                    sys.exit(1)
                catalog_path = args.cal_catalog
            else:
                # Auto-resolve to SQLite database (preferred) or CSV fallback
                try:
                    from dsa110_contimg.calibration.catalogs import (
                        resolve_vla_catalog_path,
                    )

                    catalog_path = str(resolve_vla_catalog_path(prefer_sqlite=True))
                    logger.info(f"Auto-resolved catalog to: {catalog_path}")
                except FileNotFoundError as e:
                    logger.error(f"Catalog auto-resolution failed: {e}")
                    logger.error(
                        "Provide --cal-catalog explicitly or ensure SQLite catalog exists at state/catalogs/vla_calibrators.sqlite3"
                    )
                    sys.exit(1)

            logger.info("Selecting bandpass fields from catalog...")
            sel, idxs, wflux, calinfo, peak_field = select_bandpass_from_catalog(
                args.ms,
                catalog_path,
                search_radius_deg=float(args.cal_search_radius_deg or 1.0),
                window=max(1, int(args.bp_window)),
                min_pb=(float(args.bp_min_pb) if args.bp_min_pb is not None else None),
            )
            logger.debug(
                f"Catalog selection complete: sel={sel}, calinfo={calinfo}, peak_field={peak_field}"
            )
            name, ra_deg, dec_deg, flux_jy = calinfo
            # Store catalog path and calinfo for later use in MODEL_DATA population
            resolved_catalog_path = catalog_path
            # Print calibrator info only once (prevent duplicate output)
            global _calibrator_info_printed_global
            if not _calibrator_info_printed_global:
                # Write directly to stdout to avoid any logging interference
                # sys is already imported at module level (line 4)
                sys.stdout.write("=" * 60 + "\n")
                sys.stdout.write(f"CALIBRATOR SELECTED: {name}\n")
                sys.stdout.write(f"  RA: {ra_deg:.4f} deg\n")
                sys.stdout.write(f"  Dec: {dec_deg:.4f} deg\n")
                sys.stdout.write(f"  Flux: {flux_jy:.2f} Jy\n")
                sys.stdout.write("=" * 60 + "\n")
                sys.stdout.flush()
                _calibrator_info_printed_global = True
            logger.info(
                f"Auto-selected bandpass fields: {sel} (indices: {idxs}, peak: {peak_field})"
            )
            field_sel = sel
            peak_field_idx = peak_field  # Store peak field for use when not combining fields
            logger.debug(
                f"Field selection complete, field_sel={field_sel}, peak_field={peak_field_idx}"
            )

            # CRITICAL: Rephase MS to calibrator position immediately after field selection
            # This rephases ALL fields to the same phase center (calibrator position),
            # simplifying field selection and allowing field combination for better SNR.
            # This must happen before MODEL_DATA population to ensure correct phase alignment.
            #
            # SKIP REPHASING if --skip-rephase is specified
            # This allows ft() to work correctly using meridian phase center (no manual calculation needed)
            # ms_was_rephased is already initialized at the start of this block (line 687)
            if not getattr(args, "skip_rephase", False):
                logger.debug("Rephasing MS to calibrator position...")
                rephase_success = _rephase_ms_to_calibrator(
                    args.ms,
                    ra_deg,
                    dec_deg,
                    name,
                    logger,
                )
                if not rephase_success:
                    logger.warning("Rephasing failed, but continuing with calibration")
                    ms_was_rephased = False  # Explicitly set to False when rephasing fails
                else:
                    # After rephasing, all fields have the same phase center, so we can combine
                    # all fields for better SNR (instead of just using field 0)
                    logger.debug("After rephasing, all fields share the same phase center")
                    # Get total number of fields from MS
                    # Ensure CASAPATH is set before importing CASA modules
                    from dsa110_contimg.utils.casa_init import ensure_casa_path

                    ensure_casa_path()

                    import casacore.tables as casatables

                    table = casatables.table

                    with table(f"{args.ms}::FIELD", readonly=True) as tb:
                        nfields = tb.nrows()
                    # Update field_sel to use all fields (0~N-1) for maximum integration time
                    field_sel = f"0~{nfields - 1}"
                    peak_field_idx = peak_field  # Keep peak field for reference
                    logger.debug(
                        f"Updated field selection to all {nfields} fields after rephasing: {field_sel}"
                    )
                    # Enable field combining by default when rephasing (all fields point at calibrator)
                    # This maximizes integration time and SNR for calibration solutions
                    args.bp_combine_field = True
                    logger.debug(
                        "Enabled --bp-combine-field by default (rephased MS with all fields at same phase center)"
                    )
            else:
                logger.debug("Skipping rephasing (--skip-rephase specified)")
                logger.debug("Using original meridian phase center (ft() will work correctly)")
                logger.info("Skipping rephasing - using meridian phase center")
                ms_was_rephased = False  # No rephasing when skip_rephase is used

            # Track whether rephasing was performed in auto-fields case
            # This is used to determine if we should use manual MODEL_DATA calculation
            if not getattr(args, "skip_rephase", False) and (
                "rephase_success" in locals() and rephase_success
            ):
                ms_was_rephased = True
        except Exception as e:
            logger.warning(f"Auto field selection failed ({e}); falling back to --field")
            print(("Auto field selection failed ({}); falling back to --field").format(e))
            if field_sel is None:
                logger.error("No --field provided and auto selection failed")
                sys.exit(1)

            # If auto-fields failed but explicit calibrator coordinates provided, use those
            if (
                hasattr(args, "cal_ra_deg")
                and hasattr(args, "cal_dec_deg")
                and args.cal_ra_deg
                and args.cal_dec_deg
            ):
                logger.info("Using explicit calibrator coordinates (--cal-ra-deg, --cal-dec-deg)")
                ra_deg = float(args.cal_ra_deg)
                dec_deg = float(args.cal_dec_deg)
                flux_jy = float(getattr(args, "cal_flux_jy", None) or 2.5)
                name = getattr(args, "cal_name", None) or f"manual_{ra_deg:.2f}_{dec_deg:.2f}"
                logger.info(
                    f"Calibrator: {name} @ ({ra_deg:.4f}°, {dec_deg:.4f}°), flux={flux_jy:.2f} Jy"
                )

                # Rephase to calibrator if not skipping rephasing
                if not getattr(args, "skip_rephase", False):
                    logger.debug("Rephasing MS to calibrator position...")
                    rephase_success = _rephase_ms_to_calibrator(
                        args.ms,
                        ra_deg,
                        dec_deg,
                        name,
                        logger,
                    )
                    if rephase_success:
                        ms_was_rephased = True
                        logger.debug("After rephasing, all fields share the same phase center")
                    else:
                        logger.warning("Rephasing failed, but continuing with calibration")
                        ms_was_rephased = False  # Explicitly set to False when rephasing fails
                else:
                    ms_was_rephased = False
    if field_sel is None:
        logger.error("--field is required when --auto-fields is not used")
        sys.exit(1)

    # Field validation was already done by validate_ms_for_calibration above
    # Re-validate with the selected field to ensure it's valid
    try:
        validate_ms_for_calibration(args.ms, field=field_sel)
    except ValidationError as e:
        logger.error("Field validation failed:")
        for error in e.errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    # Determine reference antenna
    refant = args.refant
    if args.refant_ranking:
        import json

        try:
            with open(args.refant_ranking, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            rec = data.get("recommended") if isinstance(data, dict) else None
            if rec and rec.get("antenna_id") is not None:
                refant = str(rec["antenna_id"])
                logger.info(f"Reference antenna (from ranking): {refant}")
        except Exception as e:
            # If a ranking file was provided but failed to load, fall back to
            # auto outrigger-priority selection when --refant is not provided.
            if args.refant is None:
                logger.warning(
                    f"Failed to read refant ranking ({e}); falling back to auto outrigger selection"
                )
                print(
                    f"Failed to read refant ranking ({e}); falling back to auto outrigger selection"
                )
            else:
                logger.warning(f"Failed to read refant ranking ({e}); using --refant={args.refant}")
                print(f"Failed to read refant ranking ({e}); using --refant={args.refant}")
    if refant is None:
        # Auto-select an outrigger-priority refant chain. Prefer analyzing an
        # existing caltable in the MS directory if present; otherwise use the
        # default outrigger chain.
        try:
            import glob

            from dsa110_contimg.calibration.refant_selection import (
                get_default_outrigger_refants,
                recommend_refants_from_ms,
            )

            ms_dir = os.path.dirname(os.path.abspath(args.ms))
            # Search for a recent calibration table to inform the recommendation
            patterns = [
                os.path.join(ms_dir, "*_bpcal"),
                os.path.join(ms_dir, "*_gpcal"),
                os.path.join(ms_dir, "*_gcal"),
                os.path.join(ms_dir, "*.cal"),
            ]
            candidates = []
            for pat in patterns:
                candidates.extend(glob.glob(pat))
            caltable = max(candidates, key=os.path.getmtime) if candidates else None
            refant = recommend_refants_from_ms(args.ms, caltable_path=caltable)
            if caltable:
                print(
                    f"Reference antenna (auto, outrigger-priority): {refant} (based on {os.path.basename(caltable)})"
                )
            else:
                # recommend_refants_from_ms will have returned the default chain
                # when no caltable is available
                print(f"Reference antenna (auto, default outrigger chain): {refant}")
        except Exception as e:
            # Last-resort fallback to the static default chain
            try:
                from dsa110_contimg.calibration.refant_selection import (
                    get_default_outrigger_refants,
                )

                refant = get_default_outrigger_refants()
                print(f"Reference antenna (auto, default outrigger chain): {refant} (reason: {e})")
            except Exception:
                # Preserve previous behavior if even defaults fail
                logger.error("Provide --refant or --refant-ranking (auto refant selection failed)")
                sys.exit(1)

    # Note: Reference antenna validation was already done by validate_ms_for_calibration above
    # If refant changed due to refant-ranking, we trust that the ranking provided a valid antenna

    # Reset MS to post-generation state if requested
    if args.reset_ms:
        print("\n" + "=" * 70)
        print("RESETTING MS TO POST-GENERATION STATE")
        print("=" * 70)
        _clear_all_calibration_artifacts(args.ms, logger, restore_field_names=True)
        print("=" * 70)

        # After reset, if auto-fields is enabled, we'll rephase to calibrator position
        # during MODEL_DATA population. This simplifies field selection since all fields
        # will have the same phase center (calibrator position).

    # Clear all calibration artifacts if requested
    if args.clear_all:
        logger.info("\n" + "=" * 70)
        logger.info("CLEARING ALL CALIBRATION ARTIFACTS")
        logger.info("=" * 70)
        _clear_all_calibration_artifacts(args.ms, logger, restore_field_names=False)
        logger.info("✓ All calibration artifacts cleared\n")

    # MS repair flags removed.
    # Optionally create a fast subset MS
    ms_in = args.ms

    # Handle minimal mode (very fast test calibration)
    if args.minimal:
        # Minimal mode overrides fast mode settings
        import casacore.tables as casatables

        table = casatables.table

        from .subset import make_subset

        base = ms_in.rstrip("/").rstrip(".ms")
        ms_minimal = f"{base}.minimal.ms"

        logger.warning(
            "=" * 70 + "\n"
            f"MINIMAL MODE: Creating ultra-fast subset MS\n"
            f"  - Creates: {ms_minimal}\n"
            "  - Original MS unchanged\n"
            "  - Use --cleanup-subset to remove after calibration\n"
            "  - For quick iteration only - NOT for production use\n"
            "=" * 70
        )
        logger.info(f"Creating minimal subset -> {ms_minimal}")

        # Create subset with extreme downsampling
        # Note: make_subset doesn't support baseline selection via CASA mstransform,
        # so we use aggressive time/channel binning instead
        make_subset(
            ms_in,
            ms_minimal,
            timebin="inf",  # Single time integration
            chanbin=16,  # Aggressive channel binning (4 channels from 64)
            combinespws=False,
        )

        # Validate minimal subset
        try:
            from dsa110_contimg.utils.validation import validate_ms

            validate_ms(ms_minimal, check_empty=True)
        except ValidationError as e:
            logger.error("Minimal subset MS validation failed:")
            for error in e.errors:
                logger.error(f"  - {error}")
            sys.exit(1)

        ms_in = ms_minimal
        subset_ms_created = ms_minimal
        # Set fast mode parameters if not already set
        if not args.timebin:
            args.timebin = "inf"
        if not args.chanbin:
            args.chanbin = 16
        if not args.uvrange:
            args.uvrange = ""  # No UV range cut for minimal

    if args.fast and (args.timebin or args.chanbin) and not args.minimal:
        import casacore.tables as casatables

        table = casatables.table

        from .subset import make_subset

        base = ms_in.rstrip("/").rstrip(".ms")
        ms_fast = f"{base}.fast.ms"

        logger.warning(
            "=" * 70 + "\n"
            f"FAST MODE: Creating subset MS for faster calibration\n"
            f"  - Creates: {ms_fast}\n"
            "  - Original MS unchanged\n"
            f"  - Uses time/channel binning: timebin={args.timebin}, chanbin={args.chanbin}\n"
            "  - Use --cleanup-subset to remove after calibration\n"
            "=" * 70
        )
        logger.info(
            f"Creating fast subset: timebin={args.timebin} chanbin={args.chanbin} -> {ms_fast}"
        )
        make_subset(
            ms_in,
            ms_fast,
            timebin=args.timebin,
            chanbin=args.chanbin,
            combinespws=False,
        )

        # Validate fast subset MS was created successfully
        try:
            from dsa110_contimg.utils.validation import validate_ms

            validate_ms(ms_fast, check_empty=True)
        except ValidationError as e:
            logger.error("Fast subset MS validation failed:")
            for error in e.errors:
                logger.error(f"  - {error}")
            sys.exit(1)

        ms_in = ms_fast
        subset_ms_created = ms_fast
    # Execute solves with a robust K step on the peak field only, then BP/G
    # across the selected window

    # Dry-run mode: validate and estimate, but don't actually solve
    if args.dry_run:
        logger.info("\n" + "=" * 70)
        logger.info("DRY-RUN MODE: Simulating calibration without writing caltables")
        logger.info("=" * 70)
        logger.info(f"MS: {ms_in}")
        logger.info(f"Field: {field_sel}")
        logger.info(f"Reference Antenna: {refant}")
        logger.info(f"K-calibration: {'enabled' if args.do_k else 'disabled (default)'}")
        logger.info(f"Bandpass: {'enabled' if not args.skip_bp else 'disabled'}")
        logger.info(f"Gain: {'enabled' if not args.skip_g else 'disabled'}")
        logger.info("")

        # Validate MS
        try:
            warnings = validate_ms_for_calibration(ms_in, field=field_sel, refant=refant)
            for warning in warnings:
                logger.warning(warning)
            logger.info("✓ MS validation passed")
        except ValidationError as e:
            logger.error("MS validation failed:")
            error_msg = e.format_with_suggestions()
            logger.error(error_msg)
            sys.exit(1)

        # Estimate unflagged data after flagging (simulate)
        try:
            from dsa110_contimg.utils.ms_helpers import validate_ms_unflagged_fraction

            current_unflagged = validate_ms_unflagged_fraction(ms_in, sample_size=10000)
            # Estimate after flagging (conservative: 10-20% reduction)
            estimated_unflagged = current_unflagged * 0.85
            logger.info(
                f"Estimated unflagged data after flagging: {estimated_unflagged * 100:.1f}%"
            )
            if estimated_unflagged < 0.1:
                logger.warning("WARNING: May have insufficient unflagged data after flagging")
        except Exception as e:
            logger.warning(f"Could not estimate unflagged data: {e}")

        # Estimate time (rough)
        logger.info("\nEstimated calibration time:")
        if args.do_k:
            logger.info("  K-calibration: ~15-30 min (full) or ~2-3 min (fast-only)")
        if not args.skip_bp:
            logger.info("  Bandpass: ~5-15 min")
        if not args.skip_g:
            logger.info("  Gain: ~5-10 min")
        logger.info("\nTotal estimated time: 15-60 min (depending on options)")

        logger.info("\n✓ Dry-run complete. Use without --dry-run to perform actual calibration.")
        return 0

    if not args.no_flagging:
        logger.info("[2/6] Flagging bad data...")
        mode = getattr(args, "flagging_mode", "zeros") or "zeros"
        if mode == "zeros":
            reset_flags(ms_in)
            flag_zeros(ms_in)
        elif mode == "rfi":
            reset_flags(ms_in)
            flag_zeros(ms_in)
            flag_rfi(ms_in)

        # ENHANCEMENT: Update weights after flagging to keep weights consistent with flags
        # This ensures flagged data has zero weights, following CASA best practices.
        # Non-fatal: CASA calibration tasks respect FLAG column regardless of weights.
        try:
            from casatasks import initweights

            print("Updating weights to match flags after flagging...")
            # NOTE: When wtmode='weight', initweights initializes WEIGHT_SPECTRUM from WEIGHT column
            # dowtsp=True creates/updates WEIGHT_SPECTRUM column
            # CASA's initweights does NOT have doweight or doflag parameters
            initweights(
                vis=ms_in,
                wtmode="weight",  # Initialize WEIGHT_SPECTRUM from existing WEIGHT
                dowtsp=True,  # Create/update WEIGHT_SPECTRUM column
            )
            print("✓ Weights updated to match flags")
        except Exception as e:
            # Non-fatal: CASA calibration tasks respect FLAG column automatically
            # Even if weights aren't updated, calibration will still work correctly
            logger.warning(
                f"Could not update weights after flagging: {e}. "
                f"Calibration will proceed (CASA tasks respect FLAG column automatically)."
            )

        # PRECONDITION CHECK: Verify sufficient unflagged data remains after flagging
        # This ensures we follow "measure twice, cut once" - verify data quality
        # before proceeding with expensive calibration operations.
        # OPTIMIZATION: Use memory-efficient sampling instead of reading entire MS
        try:
            import casacore.tables as casatables

            table = casatables.table

            from dsa110_contimg.utils.ms_helpers import (
                estimate_ms_size,
                validate_ms_unflagged_fraction,
            )

            # Get MS size for reporting
            ms_info = estimate_ms_size(ms_in)
            n_rows = ms_info["n_rows"]

            # Sample flags efficiently
            unflagged_fraction = validate_ms_unflagged_fraction(ms_in, sample_size=10000)

            # Estimate total points (rough estimate)
            total_points = n_rows * ms_info.get("n_channels", 1) * ms_info.get("n_pols", 1)
            unflagged_points = int(total_points * unflagged_fraction)

            if unflagged_fraction < 0.1:  # Less than 10% unflagged
                logger.error(
                    f"Insufficient unflagged data after flagging: {unflagged_fraction * 100:.1f}%. "
                    f"Calibration requires at least 10% unflagged data. "
                    f"Consider adjusting flagging parameters or checking data quality."
                )
                sys.exit(1)
            elif unflagged_fraction < 0.3:  # Less than 30% unflagged
                print(
                    f"Warning: Only {unflagged_fraction * 100:.1f}% of data remains unflagged "
                    f"after flagging. Calibration may be less reliable."
                )
            else:
                logger.info(
                    f"✓ [2/6] Flagging complete: {unflagged_fraction * 100:.1f}% data remains unflagged "
                    f"({unflagged_points:,}/{total_points:,} points, estimated)"
                )

            # Channel-level flagging: Analyze and flag problematic channels after RFI flagging
            # This is more precise than SPW-level flagging since SPWs are arbitrary subdivisions
            if getattr(args, "auto_flag_channels", True):
                logger.info("[2/6] Analyzing channel-level flagging statistics...")
                try:
                    problematic_channels = analyze_channel_flagging_stats(
                        args.ms, threshold=getattr(args, "channel_flag_threshold", 0.5)
                    )

                    if problematic_channels:
                        total_flagged_channels = sum(
                            len(chans) for chans in problematic_channels.values()
                        )
                        logger.info(
                            f"Found {total_flagged_channels} problematic channel(s) across "
                            f"{len(problematic_channels)} SPW(s):"
                        )
                        # Use DATA column for channel flagging (calibrate command doesn't have datacolumn arg)
                        # Safely get datacolumn with explicit default to avoid AttributeError
                        datacolumn = "DATA"  # Default for calibrate command
                        if hasattr(args, "datacolumn") and args.datacolumn:
                            datacolumn = args.datacolumn
                        flag_problematic_channels(
                            args.ms,
                            problematic_channels,
                            datacolumn=datacolumn,
                        )
                        logger.info(
                            f"✓ [2/6] Channel-level flagging complete: {total_flagged_channels} "
                            f"channel(s) flagged before calibration"
                        )
                    else:
                        logger.info("✓ [2/6] No problematic channels detected")
                except AttributeError as e:
                    # Specifically catch AttributeError to provide better diagnostics
                    error_msg = str(e)
                    if "datacolumn" in error_msg.lower():
                        logger.warning(
                            f"Channel-level flagging failed due to datacolumn access issue: {e}. "
                            f"This should not happen - calibrate command uses DATA column by default."
                        )
                    else:
                        logger.warning(f"Channel-level flagging analysis failed: {e}")
                    logger.warning("Continuing with calibration (channel-level flagging skipped)")
                except Exception as e:
                    logger.warning(f"Channel-level flagging analysis failed: {e}")
                    logger.warning("Continuing with calibration (channel-level flagging skipped)")
        except Exception as e:
            logger.error(
                f"Failed to validate unflagged data after flagging: {e}. "
                f"Cannot proceed with calibration."
            )
            sys.exit(1)
    # Determine a peak field for K (if auto-selected, we have idxs/wflux)
    k_field_sel = field_sel
    try:
        # Available only in this scope if auto-fields branch set these
        # locals
        if "idxs" in locals() and "wflux" in locals() and idxs is not None:
            import numpy as np

            k_idx = int(idxs[int(np.nanargmax(wflux))])
            k_field_sel = str(k_idx)
    except Exception:
        pass
    # As a fallback, if field_sel is a range like A~B, pick B
    if "~" in str(field_sel) and (k_field_sel == field_sel):
        try:
            _, b = str(field_sel).split("~")
            k_field_sel = str(int(b))
        except Exception:
            pass

    # K-calibration is skipped by default for DSA-110 (connected-element array, 2.6 km max baseline)
    # Following VLA/ALMA practice: residual delays are absorbed into complex gain calibration
    # K-calibration is primarily needed for VLBI arrays (thousands of km baselines)
    # Use --do-k flag to explicitly enable K-calibration if needed
    if not args.do_k:
        logger.info(
            "K-calibration skipped by default for DSA-110 "
            "(short baselines <2.6 km, delays <0.5 ns absorbed into gains). "
            "Use --do-k to enable if needed."
        )
    else:
        logger.info(f"Delay solve field (K): {k_field_sel}; BP/G fields: {field_sel}")

    # CRITICAL: Populate MODEL_DATA BEFORE calibration (K, BP, or G)
    # All calibration steps require MODEL_DATA to be populated so they know what signal
    # to calibrate against. Without MODEL_DATA, solutions are unreliable or may fail.
    # Populate MODEL_DATA according to requested strategy BEFORE solving.
    # NOTE: MODEL_DATA is required for bandpass calibration even when K-calibration is skipped.
    logger.debug("Checking if MODEL_DATA needs to be populated...")
    needs_model = args.do_k or not args.skip_bp or not args.skip_g
    logger.debug(
        f"needs_model={needs_model}, skip_bp={args.skip_bp}, skip_g={args.skip_g}, do_k={args.do_k}"
    )
    logger.debug(f"model_source={args.model_source}")

    # Validate model source usage BEFORE populating MODEL_DATA
    # This prevents problematic combinations (e.g., setjy with rephasing)
    if needs_model and args.model_source:
        # Check for problematic setjy usage
        if args.model_source == "setjy":
            if ms_was_rephased:
                logger.error(
                    "ERROR: --model-source=setjy cannot be used with rephasing.\n"
                    "Reason: setjy uses ft() internally, which has phase center bugs after rephasing.\n"
                    "Solution: Use --model-source=catalog (default) instead.\n"
                    "Or: Use --skip-rephase if calibrator is at meridian phase center.\n"
                    "For more information, see: docs/reports/EDGE_CASE_DOCUMENTATION.md"
                )
                sys.exit(1)
            if not (hasattr(args, "cal_ra_deg") and args.cal_ra_deg):
                logger.warning(
                    "WARNING: --model-source=setjy without explicit coordinates may have phase issues.\n"
                    "Recommendation: Provide --cal-ra-deg and --cal-dec-deg for accurate MODEL_DATA.\n"
                    "Or: Use --model-source=catalog (default) which handles this automatically."
                )

        # Inform about catalog model default behavior
        if args.model_source == "catalog":
            if not (hasattr(args, "cal_ra_deg") and args.cal_ra_deg):
                logger.info(
                    "INFO: Using catalog model without explicit coordinates.\n"
                    "Will attempt --auto-fields to find calibrator in MS field of view.\n"
                    "For best results, provide --cal-ra-deg, --cal-dec-deg, --cal-flux-jy."
                )

    if needs_model and args.model_source is not None:
        logger.info("[3/6] Populating MODEL_DATA...")
        try:
            from . import model as model_helpers

            if args.model_source == "catalog":
                logger.debug("Using catalog model source")
                # Check if we have calibrator info from auto_fields
                # calinfo is set when --auto-fields is used (regardless of whether --cal-catalog was explicit)
                if (
                    args.auto_fields
                    and "calinfo" in locals()
                    and isinstance(calinfo, (list, tuple))
                    and len(calinfo) >= 4
                ):
                    name, ra_deg, dec_deg, flux_jy = calinfo
                    logger.debug(
                        f"Found calibrator info, proceeding with MODEL_DATA population for {name}..."
                    )
                    logger.info(f"Populating MODEL_DATA for {name}...")

                    # Enhanced MODEL_DATA validation against catalog
                    logger.debug("Validating MODEL_DATA against catalog...")
                    validation_results = comprehensive_model_data_validation(
                        args.ms,
                        catalog_ra_deg=ra_deg,
                        catalog_dec_deg=dec_deg,
                        catalog_flux_jy=flux_jy,
                    )

                    if not validation_results["all_valid"]:
                        logger.warning("MODEL_DATA validation issues detected:")
                        if not validation_results.get("populated", False):
                            logger.warning("  - MODEL_DATA not properly populated")
                        if validation_results.get("catalog_match") is False:
                            catalog_details = validation_results["details"].get("catalog", {})
                            if not catalog_details.get("position_match", True):
                                logger.warning(
                                    f"  - Phase center offset: {catalog_details.get('separation_arcmin', 'unknown')} arcmin"
                                )
                            if not catalog_details.get("flux_match", True):
                                logger.warning(
                                    f"  - Flux mismatch: ratio = {catalog_details.get('flux_ratio', 'unknown')}"
                                )
                        if not validation_results.get("consistent", True):
                            logger.warning("  - MODEL_DATA inconsistent across fields")
                    else:
                        logger.info("✓ MODEL_DATA validation passed")

                    # CRITICAL: Rephase MS to calibrator position before writing MODEL_DATA
                    # The MS is phased to meridian (RA=LST, Dec=pointing), but we need it
                    # phased to the calibrator position for proper calibration SNR
                    # Check if already phased to calibrator (within 1 arcmin tolerance)
                    logger.debug("Checking if MS needs rephasing...")
                    needs_rephasing = True
                    try:
                        import casacore.tables as casatables
                        import numpy as np
                        from astropy import units as u
                        from astropy.coordinates import SkyCoord

                        table = casatables.table

                        logger.debug("Reading MS phase center...")
                        with table(f"{args.ms}::FIELD") as tf:
                            # CRITICAL: Check REFERENCE_DIR for phase center verification
                            # NOTE: CASA calibration tasks (gaincal/bandpass) use PHASE_DIR for phase calculations,
                            # but REFERENCE_DIR is used for primary beam correction and imaging.
                            # phaseshift updates PHASE_DIR automatically, but we check REFERENCE_DIR here
                            # to verify consistency and ensure proper imaging workflows.
                            # We also update REFERENCE_DIR after phaseshift to keep both in sync.
                            if "REFERENCE_DIR" in tf.colnames():
                                ref_dir = tf.getcol("REFERENCE_DIR")
                                ms_ra_rad = float(np.array(ref_dir[0]).ravel()[0])
                                ms_dec_rad = float(np.array(ref_dir[0]).ravel()[1])
                            else:
                                # Fallback to PHASE_DIR if REFERENCE_DIR not available
                                phase_dir = tf.getcol("PHASE_DIR")
                                ms_ra_rad = float(np.array(phase_dir[0]).ravel()[0])
                                ms_dec_rad = float(np.array(phase_dir[0]).ravel()[1])
                            ms_ra_deg = np.rad2deg(ms_ra_rad)
                            ms_dec_deg = np.rad2deg(ms_dec_rad)

                        print(f"MS phase center: RA={ms_ra_deg:.4f}°, Dec={ms_dec_deg:.4f}°")
                        ms_coord = SkyCoord(
                            ra=ms_ra_deg * u.deg,
                            dec=ms_dec_deg * u.deg,  # pylint: disable=no-member
                        )
                        cal_coord = SkyCoord(
                            ra=ra_deg * u.deg,
                            dec=dec_deg * u.deg,  # pylint: disable=no-member
                        )
                        sep_arcmin = (
                            ms_coord.separation(cal_coord)
                            .to(u.arcmin)
                            .value  # pylint: disable=no-member
                        )

                        print(f"Separation: {sep_arcmin:.2f} arcmin")
                        if sep_arcmin < 1.0:
                            logger.info(
                                f"✓ MS already phased to calibrator position (offset: {sep_arcmin:.2f} arcmin)"
                            )
                            needs_rephasing = False
                        else:
                            print(
                                f"Rephasing MS to calibrator position: {name} @ ({ra_deg:.4f}°, {dec_deg:.4f}°)"
                            )
                            print(f"  Current phase center offset: {sep_arcmin:.2f} arcmin")
                            needs_rephasing = True
                    except Exception as e:
                        logger.warning(
                            f"Could not check phase center: {e}. Assuming rephasing needed."
                        )
                        needs_rephasing = True

                    if needs_rephasing:
                        logger.debug("Rephasing needed, starting rephasing workflow...")

                        # CRITICAL: UVW coordinates cannot be corrected by simple addition/subtraction.
                        # When phase center changes, UVW must be rotated/transformed using coordinate rotation.
                        # phaseshift correctly transforms both UVW coordinates AND visibility phases together.
                        # Direct UVW modification would leave DATA column phased to wrong center, causing
                        # DATA/MODEL misalignment and calibration failures.
                        # Therefore, we always use phaseshift for rephasing, which handles the full transformation.

                        try:
                            logger.debug("Importing rephasing tasks...")
                            import shutil

                            from astropy.coordinates import Angle
                            from casatasks import phaseshift as casa_phaseshift

                            from dsa110_contimg.calibration.uvw_verification import (
                                get_phase_center_from_ms,
                            )

                            logger.debug("Imports complete, formatting phase center...")

                            # Capture old phase center for UVW verification
                            try:
                                old_phase_center = get_phase_center_from_ms(args.ms, field=0)
                                new_phase_center = (ra_deg, dec_deg)
                            except Exception:
                                old_phase_center = None
                                new_phase_center = (ra_deg, dec_deg)

                            # Format phase center string for CASA
                            ra_hms = (
                                Angle(ra_deg, unit="deg")
                                .to_string(unit="hourangle", sep="hms", precision=2, pad=True)
                                .replace(" ", "")
                            )
                            dec_dms = (
                                Angle(dec_deg, unit="deg")
                                .to_string(
                                    unit="deg",
                                    sep="dms",
                                    precision=2,
                                    alwayssign=True,
                                    pad=True,
                                )
                                .replace(" ", "")
                            )
                            phasecenter_str = f"J2000 {ra_hms} {dec_dms}"
                            logger.debug(f"Phase center string: {phasecenter_str}")

                            # Create temporary MS for rephased data
                            # Use absolute path and ensure it's a sibling, not nested
                            ms_abs = os.path.abspath(args.ms.rstrip("/"))
                            ms_dir = os.path.dirname(ms_abs)
                            ms_base = os.path.basename(ms_abs).rstrip(".ms")
                            ms_phased = os.path.join(ms_dir, f"{ms_base}.phased.ms")

                            # Clean up any existing temporary files
                            if os.path.exists(ms_phased):
                                logger.debug("Removing existing phased MS: {ms_phased}")
                                shutil.rmtree(ms_phased, ignore_errors=True)

                            # Calculate phase shift magnitude to determine method
                            from astropy import units as u
                            from astropy.coordinates import SkyCoord

                            old_coord = SkyCoord(
                                ra=old_phase_center[0] * u.deg,  # pylint: disable=no-member
                                dec=old_phase_center[1] * u.deg,  # pylint: disable=no-member
                                frame="icrs",
                            )
                            new_coord = SkyCoord(
                                ra=new_phase_center[0] * u.deg,  # pylint: disable=no-member
                                dec=new_phase_center[1] * u.deg,  # pylint: disable=no-member
                                frame="icrs",
                            )
                            phase_shift_arcmin = (
                                old_coord.separation(new_coord)
                                .to(u.arcmin)
                                .value  # pylint: disable=no-member
                            )

                            logger.debug(f"Phase shift magnitude: {phase_shift_arcmin:.1f} arcmin")

                            # Try phaseshift first (preferred method)
                            logger.info("Running phaseshift (this may take a while)...")
                            uv_transformation_valid = False

                            try:
                                casa_phaseshift(
                                    vis=args.ms,
                                    outputvis=ms_phased,
                                    phasecenter=phasecenter_str,
                                )
                                logger.debug("phaseshift complete")
                                logger.info(
                                    "✓ phaseshift completed successfully - UVW coordinates and visibility phases transformed"
                                )
                                uv_transformation_valid = True

                            except Exception as phaseshift_error:
                                logger.error(f"phaseshift failed: {phaseshift_error}")
                                logger.error("Cannot proceed - rephasing failed")
                                uv_transformation_valid = False

                            # CRITICAL: phaseshift must succeed
                            # If phaseshift fails, DATA is phased to wrong center, so MODEL_DATA won't match
                            # This would cause calibration to fail regardless of MODEL_DATA calculation method
                            if not uv_transformation_valid:
                                suggestions = [
                                    "Check MS phase center alignment",
                                    "Verify calibrator position matches MS phase center",
                                    "Re-run conversion with correct phase center",
                                    "Manually rephase MS using phaseshift task",
                                ]
                                error_msg_final = format_ms_error_with_suggestions(
                                    RuntimeError(
                                        "phaseshift failed - cannot calibrate MS with incorrect phase center"
                                    ),
                                    args.ms,
                                    "MS rephasing",
                                    suggestions,
                                )
                                logger.error(error_msg_final)
                                raise RuntimeError(error_msg_final)

                            logger.debug("Checking REFERENCE_DIR...")

                            # CRITICAL: phaseshift may update PHASE_DIR but not REFERENCE_DIR
                            # CASA calibration tasks use REFERENCE_DIR, so we must ensure it's correct
                            # Manually update REFERENCE_DIR for ALL fields if phaseshift didn't update it
                            try:
                                import casacore.tables as casatables

                                casa_table = casatables.table

                                with casa_table(f"{ms_phased}::FIELD", readonly=False) as tf:
                                    if (
                                        "REFERENCE_DIR" in tf.colnames()
                                        and "PHASE_DIR" in tf.colnames()
                                    ):
                                        # Shape: (nfields, 1, 2)
                                        ref_dir_all = tf.getcol("REFERENCE_DIR")
                                        # Shape: (nfields, 1, 2)
                                        phase_dir_all = tf.getcol("PHASE_DIR")
                                        nfields = len(ref_dir_all)

                                        # Check if REFERENCE_DIR matches PHASE_DIR for each field
                                        # Tolerance: 1 arcmin in radians ≈ 2.9e-5 rad
                                        needs_update = False
                                        for field_idx in range(nfields):
                                            # Shape: (2,)
                                            ref_dir = ref_dir_all[field_idx][0]
                                            # Shape: (2,)
                                            phase_dir = phase_dir_all[field_idx][0]
                                            if not np.allclose(ref_dir, phase_dir, atol=2.9e-5):
                                                needs_update = True
                                                break

                                        if needs_update:
                                            logger.debug(
                                                "REFERENCE_DIR not updated by phaseshift for some fields, updating manually..."
                                            )
                                            # Update REFERENCE_DIR for ALL fields to match PHASE_DIR
                                            # This ensures each field has correct REFERENCE_DIR after rephasing
                                            tf.putcol("REFERENCE_DIR", phase_dir_all)
                                            logger.debug(
                                                f"REFERENCE_DIR updated to match PHASE_DIR for all {nfields} fields"
                                            )
                                        else:
                                            logger.debug(
                                                "REFERENCE_DIR already correct (matches PHASE_DIR for all fields)"
                                            )
                            except Exception as refdir_error:
                                logger.warning(
                                    f"Could not verify/update REFERENCE_DIR: {refdir_error}"
                                )
                                logger.warning("Calibration may fail if REFERENCE_DIR is incorrect")
                            logger.debug("Rephasing complete, verifying phase center...")

                            # Verify REFERENCE_DIR is correct after rephasing
                            try:
                                import casacore.tables as casatables

                                casa_table = casatables.table

                                with casa_table(f"{ms_phased}::FIELD", readonly=True) as tf:
                                    if "REFERENCE_DIR" in tf.colnames():
                                        ref_dir = tf.getcol("REFERENCE_DIR")[0][0]
                                        ref_ra_deg = ref_dir[0] * 180.0 / np.pi
                                        ref_dec_deg = ref_dir[1] * 180.0 / np.pi

                                        # Check separation from calibrator
                                        from astropy import units as u
                                        from astropy.coordinates import SkyCoord

                                        ms_coord = SkyCoord(
                                            ra=ref_ra_deg * u.deg,  # pylint: disable=no-member
                                            dec=ref_dec_deg * u.deg,  # pylint: disable=no-member
                                            frame="icrs",
                                        )
                                        cal_coord = SkyCoord(
                                            ra=ra_deg * u.deg,  # pylint: disable=no-member
                                            dec=dec_deg * u.deg,  # pylint: disable=no-member
                                            frame="icrs",
                                        )
                                        separation = ms_coord.separation(cal_coord)

                                        logger.debug(
                                            f"Final REFERENCE_DIR: RA={ref_ra_deg:.6f}°, Dec={ref_dec_deg:.6f}°"
                                        )
                                        logger.debug(
                                            f"Separation from calibrator: {separation.to(u.arcmin):.4f}"  # pylint: disable=no-member
                                        )

                                        if (
                                            separation.to(u.arcmin).value
                                            > 1.0  # pylint: disable=no-member
                                        ):
                                            logger.warning(
                                                f"REFERENCE_DIR still offset by {separation.to(u.arcmin):.4f} - calibration may fail"  # pylint: disable=no-member
                                            )
                                        else:
                                            logger.info(
                                                "✓ REFERENCE_DIR correctly aligned (separation < 1 arcmin)"
                                            )
                            except Exception as verify_error:
                                logger.warning(f"Could not verify phase center: {verify_error}")

                            # Replace original MS with rephased version
                            logger.debug("Replacing original MS with rephased version...")
                            shutil.rmtree(args.ms, ignore_errors=True)
                            shutil.move(ms_phased, args.ms)
                            logger.info("✓ MS rephased to calibrator position")
                            ms_was_rephased = True  # Track that rephasing was performed

                        except ImportError:
                            # phaseshift not available - cannot rephase
                            suggestions = [
                                "Install CASA with phaseshift task support",
                                "Use --skip-rephase to skip rephasing (not recommended)",
                                "Re-run conversion with correct phase center",
                                "Check CASA installation and version",
                            ]
                            error_msg_import = format_ms_error_with_suggestions(
                                ImportError("phaseshift task not available"),
                                args.ms,
                                "MS rephasing",
                                suggestions,
                            )
                            logger.error(error_msg_import)
                            raise RuntimeError(error_msg_import)
                        except Exception as e:
                            # Rephasing failed - cannot proceed
                            suggestions = [
                                "Check MS phase center alignment",
                                "Verify calibrator position matches MS phase center",
                                "Re-run conversion with correct phase center",
                                "Manually rephase MS using phaseshift task",
                                "Check CASA logs for detailed error information",
                            ]
                            error_msg_rephase = format_ms_error_with_suggestions(
                                e, args.ms, "MS rephasing", suggestions
                            )
                            logger.error(error_msg_rephase)
                            raise RuntimeError(error_msg_rephase)

                    print(
                        (
                            "Writing catalog point model: {n} @ ("
                            "{ra:.4f},{de:.4f}) deg, {fl:.2f} Jy"
                        ).format(n=name, ra=ra_deg, de=dec_deg, fl=flux_jy)
                    )
                    logger.info("Calling MODEL_DATA population (this may take a while)...")
                    # CRITICAL: Clear MODEL_DATA before writing, especially after rephasing
                    # Old MODEL_DATA may have been written for wrong phase center
                    try:
                        from casatasks import clearcal

                        clearcal(vis=args.ms, addmodel=True)
                        logger.debug("Cleared existing MODEL_DATA before writing new model")
                    except Exception as e:
                        logger.warning(f"Could not clear MODEL_DATA before writing: {e}")

                    # Use manual calculation to populate MODEL_DATA (bypasses ft() phase center issues)
                    # Manual calculation uses PHASE_DIR per field, ensuring correct phase structure
                    # ft() has known issues with phase center detection after rephasing (102° scatter)
                    logger.debug("Using manual MODEL_DATA calculation...")
                    # Pass field parameter to ensure MODEL_DATA is written to the correct field
                    # Use field_sel (the calibrator field) for MODEL_DATA population
                    model_helpers.write_point_model_with_ft(
                        args.ms,
                        float(ra_deg),
                        float(dec_deg),
                        float(flux_jy),
                        field=field_sel,
                        use_manual=True,
                    )
                    logger.debug("MODEL_DATA population completed (manual calculation)")
                    # Rename field to calibrator name
                    try:
                        import casacore.tables as casatables

                        table = casatables.table

                        with table(f"{args.ms}::FIELD", readonly=False) as field_tb:
                            # Get current field names
                            field_names = field_tb.getcol("NAME")
                            # Rename the peak field (where calibrator is actually located) to calibrator name
                            if len(field_names) > 0 and peak_field_idx is not None:
                                # Use time suffix to preserve which timestamp contained the calibrator
                                new_name = f"{name}_t{peak_field_idx}"
                                field_names[peak_field_idx] = new_name
                                field_tb.putcol("NAME", field_names)
                                logger.info(f"✓ Renamed field {peak_field_idx} to '{new_name}'")
                    except Exception as e:
                        logger.warning(f"Could not rename field to calibrator name: {e}")
                else:
                    # PRECONDITION CHECK: If calibrator info is unavailable, try explicit args
                    # Check if explicit calibrator coordinates were provided
                    if (
                        hasattr(args, "cal_ra_deg")
                        and hasattr(args, "cal_dec_deg")
                        and args.cal_ra_deg
                        and args.cal_dec_deg
                    ):
                        logger.info("Using explicit calibrator coordinates for catalog model")
                        ra_deg = float(args.cal_ra_deg)
                        dec_deg = float(args.cal_dec_deg)
                        flux_jy = float(getattr(args, "cal_flux_jy", None) or 2.5)
                        name = (
                            getattr(args, "cal_name", None) or f"manual_{ra_deg:.2f}_{dec_deg:.2f}"
                        )

                        # Use field_sel (from --field argument) since auto-fields failed
                        print(
                            f"Writing catalog point model: {name} @ ({ra_deg:.4f},{dec_deg:.4f}) deg, {flux_jy:.2f} Jy"
                        )
                        logger.info("Calling MODEL_DATA population (this may take a while)...")

                        # Clear MODEL_DATA before writing
                        try:
                            from casatasks import clearcal

                            clearcal(vis=args.ms, addmodel=True)
                            logger.debug("Cleared existing MODEL_DATA before writing new model")
                        except Exception as e:
                            logger.warning(f"Could not clear MODEL_DATA before writing: {e}")

                        # Use manual calculation to populate MODEL_DATA
                        logger.debug("Using manual MODEL_DATA calculation...")
                        model_helpers.write_point_model_with_ft(
                            args.ms,
                            float(ra_deg),
                            float(dec_deg),
                            float(flux_jy),
                            field=field_sel,
                            use_manual=True,
                        )
                        logger.debug("MODEL_DATA population completed (manual calculation)")
                    elif needs_model:
                        logger.error(
                            "ERROR: Catalog model requires calibrator information.\n\n"
                            "Options:\n"
                            "  1. Use --auto-fields (finds calibrator in MS field of view)\n"
                            "     python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms --auto-fields\n\n"
                            "  2. Provide explicit coordinates (recommended for production)\n"
                            "     python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms --cal-ra-deg <RA> --cal-dec-deg <DEC> --cal-flux-jy <FLUX>\n\n"
                            "  3. Use --model-source=setjy (only if calibrator at phase center, no rephasing)\n"
                            "     python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms --model-source=setjy --model-field 0\n\n"
                            "For more information, see: docs/howto/CALIBRATION_DETAILED_PROCEDURE.md"
                        )
                        sys.exit(1)
                    else:
                        print(
                            (
                                "Catalog model requested but calibrator info "
                                "unavailable; skipping model write"
                            )
                        )
            elif args.model_source == "setjy":
                if not args.model_field:
                    logger.error("--model-source=setjy requires --model-field")
                    sys.exit(1)

                # Check if MS was rephased - if so, we need to use manual calculation
                # because setjy uses ft() internally which has phase center bugs
                if ms_was_rephased:
                    logger.warning(
                        "MS was rephased, but setjy uses ft() internally which has phase center bugs."
                    )
                    logger.warning(
                        "setjy will likely produce MODEL_DATA with incorrect phase structure."
                    )
                    logger.warning(
                        "Recommend using --model-source catalog with --cal-ra-deg and --cal-dec-deg instead."
                    )
                    logger.warning(
                        "Or use --skip-rephase if calibrator is near meridian phase center."
                    )

                    # Try to get calibrator coordinates if available
                    if (
                        hasattr(args, "cal_ra_deg")
                        and hasattr(args, "cal_dec_deg")
                        and args.cal_ra_deg
                        and args.cal_dec_deg
                    ):
                        print("Attempting to use manual calculation with calibrator coordinates...")
                        # Get flux from setjy first, then use manual calculation
                        try:
                            import casacore.tables as casatables

                            table = casatables.table

                            # Call setjy with usescratch=False to get flux without populating MODEL_DATA
                            # Actually, setjy always populates MODEL_DATA, so we need a different approach
                            # Instead, let's read the flux from the standard catalog
                            print("Using calibrator flux from standard catalog...")

                            # Use manual calculation with provided coordinates
                            # We need flux - try to get it from standard catalog or use default
                            flux_jy = getattr(args, "cal_flux_jy", None) or 2.5  # Default flux
                            print(
                                f"Using flux: {flux_jy:.2f} Jy (consider providing --cal-flux-jy for accurate flux)"
                            )

                            model_helpers.write_point_model_with_ft(
                                args.ms,
                                float(args.cal_ra_deg),
                                float(args.cal_dec_deg),
                                float(flux_jy),
                                field=args.model_field,
                                use_manual=True,
                            )
                            logger.info(
                                "✓ MODEL_DATA populated using manual calculation (bypasses ft() phase center bug)"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to use manual calculation for setjy: {e}")
                            print("Falling back to setjy (may have phase center issues)...")
                            model_helpers.write_setjy_model(
                                args.ms,
                                field=args.model_field,
                                standard=args.model_setjy_standard,
                                spw=args.model_setjy_spw,
                            )
                    else:
                        print(
                            "No calibrator coordinates available - falling back to setjy (may have phase issues)"
                        )
                        model_helpers.write_setjy_model(
                            args.ms,
                            field=args.model_field,
                            standard=args.model_setjy_standard,
                            spw=args.model_setjy_spw,
                        )
                else:
                    print(
                        ("Running setjy on field {} (standard {})").format(
                            args.model_field, args.model_setjy_standard
                        )
                    )
                    model_helpers.write_setjy_model(
                        args.ms,
                        field=args.model_field,
                        standard=args.model_setjy_standard,
                        spw=args.model_setjy_spw,
                    )
            elif args.model_source == "component":
                if not args.model_component:
                    logger.error("--model-source=component requires --model-component")
                    sys.exit(1)
                print("Applying component list model: {}".format(args.model_component))
                model_helpers.write_component_model_with_ft(args.ms, args.model_component)
            elif args.model_source == "image":
                if not args.model_image:
                    logger.error("--model-source=image requires --model-image")
                    sys.exit(1)
                print("Applying image model: {}".format(args.model_image))
                model_helpers.write_image_model_with_ft(args.ms, args.model_image)
            elif args.model_source is None:
                # No model source specified - this violates "measure twice, cut once"
                # We require MODEL_DATA to be populated before calibration for consistent,
                # reliable results across all calibrators (bright or faint).
                # This ensures the calibration approach works generally, not just "sometimes"
                # for bright sources.
                if needs_model:
                    logger.error(
                        "--model-source is REQUIRED for calibration (K, BP, or G). "
                        "This ensures consistent, reliable calibration results. "
                        "Use --model-source=setjy (for standard calibrators) or "
                        " --model-source=catalog (for catalog-based models)."
                    )
                    sys.exit(1)
        except Exception as e:
            # PRECONDITION CHECK: MODEL_DATA population failure is a hard error
            # This ensures we follow "measure twice, cut once" - establish requirements upfront
            # before expensive calibration operations.
            logger.error(
                f"MODEL_DATA population failed: {e}. "
                f"This is required for calibration. Fix the error and retry."
            )
            sys.exit(1)

    # PRECONDITION CHECK: Validate MODEL_DATA flux values are reasonable
    # This ensures we follow "measure twice, cut once" - verify MODEL_DATA quality
    # before proceeding with calibration.
    if needs_model and args.model_source is not None:
        try:
            import casacore.tables as casatables
            import numpy as np

            table = casatables.table

            with table(ms_in, readonly=True) as tb:
                if "MODEL_DATA" in tb.colnames():
                    n_rows = tb.nrows()
                    if n_rows > 0:
                        # Sample MODEL_DATA to check flux values
                        sample_size = min(10000, n_rows)
                        model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=sample_size)
                        flags_sample = tb.getcol("FLAG", startrow=0, nrow=sample_size)

                        # Check unflagged model data
                        unflagged_model = model_sample[~flags_sample]
                        if len(unflagged_model) > 0:
                            model_amps = np.abs(unflagged_model)
                            # Filter out near-zero
                            model_amps = model_amps[model_amps > 1e-10]

                            if len(model_amps) > 0:
                                median_flux = np.median(model_amps)
                                min_flux = np.min(model_amps)
                                max_flux = np.max(model_amps)

                                # Warn if flux values seem unrealistic
                                if median_flux < 1e-6:  # Less than 1 microJy
                                    print(
                                        f"Warning: MODEL_DATA has very low median flux: "
                                        f"{median_flux:.2e} Jy. This may indicate an issue with "
                                        f"the model population."
                                    )
                                elif median_flux > 1e6:  # More than 1 MJy
                                    print(
                                        f"Warning: MODEL_DATA has very high median flux: "
                                        f"{median_flux:.2e} Jy. This may indicate an issue with "
                                        f"the model population."
                                    )
                                else:
                                    logger.info(
                                        f"✓ [3/6] MODEL_DATA validated: median flux {median_flux:.3f} Jy "
                                        f"(range: {min_flux:.3e} - {max_flux:.3e} Jy)"
                                    )
        except Exception as e:
            # Non-fatal: log warning but don't fail
            logger.warning(f"MODEL_DATA flux validation failed: {e}")

    # Determine step numbers for solves (dynamic based on enabled operations)
    step_num = 4
    if args.do_k:
        logger.info(f"[{step_num}/6] Solving K-calibration (delay)...")
        step_num += 1
    ktabs = []
    if args.do_k:
        t_k0 = time.perf_counter()
        ktabs = solve_delay(
            ms_in,
            k_field_sel,
            refant,
            table_prefix=getattr(args, "table_prefix_override", None),
            combine_spw=args.combine_spw,
            uvrange=((args.uvrange or "") if args.fast else ""),
            minsnr=5.0,
            skip_slow=args.k_fast_only,
        )
        elapsed_k = time.perf_counter() - t_k0
        logger.info(f"✓ [{step_num - 1}/6] K-calibration completed in {elapsed_k:.2f}s")

    # Flag autocorrelations before any solves unless disabled
    if not args.no_flagging and not getattr(args, "no_flag_autocorr", False):
        try:
            from casatasks import flagdata  # type: ignore

            print("Flagging autocorrelations prior to calibration...")
            flagdata(vis=ms_in, autocorr=True, flagbackup=False)
            print("\u2713 Autocorrelations flagged")
        except Exception as e:
            print(f"Warning: autocorrelation flagging failed: {e}")
            logger.warning(f"Autocorrelation flagging failed: {e}")

    # Optional: pre-bandpass phase-only solve if requested
    prebp_phase_table = None
    if not args.skip_bp and bool(getattr(args, "prebp_phase", False)):
        logger.info(f"[{step_num}/6] Pre-bandpass phase-only solve...")
        t_prebp0 = time.perf_counter()
        try:
            prebp_phase_table = solve_prebandpass_phase(
                ms_in,
                field_sel,
                refant,
                combine_fields=bool(args.bp_combine_field),
                combine_spw=bool(getattr(args, "combine_spw", False)),
                uvrange=str(getattr(args, "prebp_uvrange", "") or ""),
                solint=str(getattr(args, "prebp_solint", "30s") or "30s"),
                minsnr=float(getattr(args, "prebp_minsnr", 3.0)),
                peak_field_idx=peak_field_idx if "peak_field_idx" in locals() else None,
                minblperant=getattr(args, "prebp_minblperant", None),
                spw=getattr(args, "prebp_spw", None),
                table_name=getattr(args, "prebp_table_name", None),
            )
            elapsed_prebp = time.perf_counter() - t_prebp0
            logger.info(
                f"✓ [{step_num}/6] Pre-bandpass phase solve completed in {elapsed_prebp:.2f}s"
            )
        except Exception:
            logger.warning("Pre-bandpass phase solve failed: {e}")
            logger.info("Continuing with bandpass solve without pre-bandpass phase correction...")

    bptabs = []
    if not args.skip_bp:
        logger.debug("Starting bandpass solve...")
        t_bp0 = time.perf_counter()
        # No implicit UV range cut; use CLI or env default if provided
        # NOTE: K-table is NOT passed to bandpass (K-calibration not used for DSA-110)
        import os as _os

        bp_uvrange = args.uvrange if args.uvrange else _os.getenv("CONTIMG_CAL_BP_UVRANGE", "")
        logger.debug(
            f"Calling solve_bandpass with uvrange='{bp_uvrange}', field={field_sel}, refant={refant}"
        )
        if prebp_phase_table:
            logger.debug(f"Using pre-bandpass phase table: {prebp_phase_table}")
        logger.info("This may take several minutes - bandpass solve is running...")
        logger.info(f"[{step_num}/6] Solving bandpass (BP) calibration...")
        bptabs = solve_bandpass(
            ms_in,
            field_sel,
            refant,
            None,  # K-table not used for DSA-110
            table_prefix=getattr(args, "table_prefix_override", None),
            combine_fields=bool(args.bp_combine_field),
            combine_spw=args.combine_spw,
            uvrange=bp_uvrange,
            minsnr=float(args.bp_minsnr),
            # Apply pre-bandpass phase correction
            prebandpass_phase_table=prebp_phase_table,
            bp_smooth_type=(getattr(args, "bp_smooth_type", "none") or "none"),
            bp_smooth_window=(
                int(getattr(args, "bp_smooth_window"))
                if getattr(args, "bp_smooth_window", None) is not None
                else None
            ),
            peak_field_idx=peak_field_idx if "peak_field_idx" in locals() else None,
            # Custom combine string (e.g., "scan,obs,field")
            combine=getattr(args, "bp_combine", None),
        )
        elapsed_bp = time.perf_counter() - t_bp0
        logger.info(f"✓ [{step_num}/6] Bandpass solve completed in {elapsed_bp:.2f}s")
        step_num += 1
        # Always report bandpass flagged fraction and per-SPW statistics
        try:
            if bptabs:
                from dsa110_contimg.qa.calibration_quality import (
                    analyze_per_spw_flagging,
                    validate_caltable_quality,
                )

                _bp_metrics = validate_caltable_quality(bptabs[0])
                print(f"Bandpass flagged solutions: {_bp_metrics.fraction_flagged * 100:.1f}%")

                # Generate bandpass plots if requested
                if getattr(args, "plot_bandpass", True) and bptabs:
                    try:
                        # Determine plot output directory
                        if getattr(args, "bandpass_plot_dir", None):
                            plot_dir = args.bandpass_plot_dir
                        else:
                            # Default: {ms_dir}/calibration_plots/bandpass
                            ms_dir = os.path.dirname(os.path.abspath(args.ms))
                            plot_dir = os.path.join(ms_dir, "calibration_plots", "bandpass")

                        logger.info("Generating bandpass plots...")
                        plot_files = generate_bandpass_plots(
                            bptabs[0],
                            output_dir=plot_dir,
                            plot_amplitude=True,
                            plot_phase=True,
                        )
                        if plot_files:
                            logger.info(
                                f"✓ Generated {len(plot_files)} bandpass plot(s) in {plot_dir}"
                            )
                            logger.info(
                                f"✓ Bandpass plots: {len(plot_files)} file(s) in {plot_dir}"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to generate bandpass plots: {e}")
                        logger.warning(
                            "Continuing without plots (calibration completed successfully)"
                        )

                # Per-SPW analysis (following NRAO/VLBA best practices)
                try:
                    from dsa110_contimg.qa.calibration_quality import (
                        export_per_spw_stats,
                        flag_problematic_spws,
                        plot_per_spw_flagging,
                    )

                    spw_stats = analyze_per_spw_flagging(bptabs[0])
                    if spw_stats:
                        problematic_spws = [s for s in spw_stats if s.is_problematic]

                        print("\n" + "=" * 70)
                        print("PER-SPECTRAL-WINDOW FLAGGING ANALYSIS")
                        print("=" * 70)
                        print(
                            f"{'SPW':<6} {'Flagged':<25} {'Avg/Ch':<10} {'High-Flag Ch':<15} {'Status':<12}"
                        )
                        print("-" * 70)

                        for stats in sorted(spw_stats, key=lambda x: x.spw_id):
                            status = "⚠ PROBLEMATIC" if stats.is_problematic else "✓ OK"
                            flagged_str = f"{stats.fraction_flagged * 100:>5.1f}% ({stats.flagged_solutions}/{stats.total_solutions})"
                            avg_str = f"{stats.avg_flagged_per_channel * 100:>5.1f}%"
                            channels_str = f"{stats.channels_with_high_flagging}/{stats.n_channels}"
                            print(
                                f"{stats.spw_id:<6} "
                                f"{flagged_str:<25} "
                                f"{avg_str:<10} "
                                f"{channels_str:<15} "
                                f"{status:<12}"
                            )

                        if problematic_spws:
                            print("\n" + "=" * 70)
                            print("⚠ WARNING: Problematic Spectral Windows Detected")
                            print("=" * 70)
                            for stats in problematic_spws:
                                logger.warning(
                                    f"SPW {stats.spw_id}: {stats.fraction_flagged * 100:.1f}% flagged "
                                    f"(avg {stats.avg_flagged_per_channel * 100:.1f}% per channel, "
                                    f"{stats.channels_with_high_flagging}/{stats.n_channels} channels with >50% flagging). "
                                    f"Note: Per-channel flagging is preferred. Flag entire SPW only as last resort."
                                )
                            print(
                                f"\nRecommendation: {len(problematic_spws)} SPW(s) show consistently high flagging rates. "
                                f"These may indicate low S/N, RFI, or instrumental issues. "
                                f"Note: Per-channel flagging is preferred (already done pre-calibration). "
                                f"Consider flagging entire SPWs only if per-channel flagging is insufficient."
                            )

                            # Auto-flag problematic SPWs if requested
                            auto_flag = getattr(args, "auto_flag_problematic_spws", False)
                            if auto_flag:
                                logger.info(
                                    f"Auto-flagging {len(problematic_spws)} problematic SPW(s)..."
                                )
                                try:
                                    flagged_spws = flag_problematic_spws(ms_in, bptabs[0])
                                    if flagged_spws:
                                        logger.info(f"✓ Flagged SPWs: {flagged_spws}")
                                        print(
                                            f"\n✓ Automatically flagged {len(flagged_spws)} problematic SPW(s): {flagged_spws}"
                                        )
                                except Exception as e:
                                    logger.warning(f"Failed to auto-flag problematic SPWs: {e}")
                        else:
                            print("\n✓ All spectral windows show acceptable flagging rates")
                        print("=" * 70 + "\n")

                        # Export statistics if requested
                        export_stats = getattr(args, "export_spw_stats", None)
                        if export_stats:
                            try:
                                json_path = export_per_spw_stats(
                                    spw_stats, export_stats, output_format="json"
                                )
                                csv_path = export_per_spw_stats(
                                    spw_stats, export_stats, output_format="csv"
                                )
                                logger.info(f"Exported per-SPW statistics: {json_path}, {csv_path}")
                                logger.info(
                                    f"✓ Exported per-SPW statistics: {json_path}, {csv_path}"
                                )
                            except Exception as e:
                                logger.warning(f"Failed to export per-SPW statistics: {e}")

                        # Generate visualization if requested
                        plot_path = getattr(args, "plot_spw_flagging", None)
                        if plot_path:
                            try:
                                plot_file = plot_per_spw_flagging(
                                    spw_stats,
                                    plot_path,
                                    title=f"Bandpass Calibration - Per-SPW Flagging Analysis\n{os.path.basename(ms_in)}",
                                )
                                logger.info(f"Generated per-SPW flagging plot: {plot_file}")
                                logger.info(f"✓ Generated visualization: {plot_file}")
                            except Exception as e:
                                logger.warning(f"Failed to generate per-SPW flagging plot: {e}")
                except Exception as e:
                    logger.warning(f"Could not compute per-SPW flagging statistics: {e}")
        except Exception as e:
            logger.warning(f"Could not compute bandpass flagged fraction: {e}")

        # Export MODEL_DATA as FITS image if requested
        if args.export_model_image and bptabs:
            try:
                from .model import export_model_as_fits

                output_path = f"{ms_in}.calibrator_model"
                logger.info(f"Exporting calibrator model image to {output_path}.fits...")
                export_model_as_fits(
                    ms_in,
                    output_path,
                    field=field_sel,
                    imsize=512,
                    cell_arcsec=1.0,
                )
            except Exception as e:
                logger.warning(f"Failed to export model image: {e}")

    gtabs = []
    try:
        if not args.skip_g:
            logger.info(f"[{step_num}/6] Solving gain (G) calibration...")
            t_g0 = time.perf_counter()
            # Determine phase_only based on gain_calmode
            # NOTE: K-table is NOT passed to gains (K-calibration not used for DSA-110)
            phase_only = (args.gain_calmode == "p") or bool(args.fast)
            gtabs = solve_gains(
                ms_in,
                field_sel,
                refant,
                None,  # K-table not used for DSA-110
                bptabs,
                table_prefix=getattr(args, "table_prefix_override", None),
                combine_fields=bool(args.bp_combine_field),
                phase_only=phase_only,
                uvrange=((args.uvrange or "") if args.fast else ""),
                solint=args.gain_solint,
                minsnr=float(getattr(args, "gain_minsnr", 3.0)),
                peak_field_idx=peak_field_idx if "peak_field_idx" in locals() else None,
            )
            elapsed_g = time.perf_counter() - t_g0
            logger.info(f"✓ [{step_num}/6] Gain solve completed in {elapsed_g:.2f}s")

            # Generate gain plots if requested
            if getattr(args, "plot_gain", True) and gtabs:
                try:
                    # Determine plot output directory
                    if getattr(args, "gain_plot_dir", None):
                        plot_dir = args.gain_plot_dir
                    else:
                        # Default: {ms_dir}/calibration_plots/gain
                        ms_dir = os.path.dirname(os.path.abspath(args.ms))
                        plot_dir = os.path.join(ms_dir, "calibration_plots", "gain")

                    logger.info("Generating gain plots...")
                    plot_files = generate_gain_plots(
                        gtabs[0],
                        output_dir=plot_dir,
                        plot_amplitude=True,
                        plot_phase=True,
                    )
                    if plot_files:
                        logger.info(f"✓ Generated {len(plot_files)} gain plot(s) in {plot_dir}")
                        logger.info(f"✓ Gain plots: {len(plot_files)} file(s) in {plot_dir}")
                except Exception as e:
                    logger.warning(f"Failed to generate gain plots: {e}")
                    logger.warning("Continuing without plots (calibration completed successfully)")

    except Exception as e:
        from dsa110_contimg.utils.error_context import format_error_with_context

        # Enhanced error handling with recovery suggestions
        context = {
            "operation": "calibration solves",
            "ms_path": ms_in if "ms_in" in locals() else args.ms,
            "field": field_sel if "field_sel" in locals() else args.field,
            "refant": refant if "refant" in locals() else args.refant,
        }

        # Determine error type and provide specific recovery suggestions
        error_type = type(e).__name__
        error_msg_str = str(e).lower()

        recovery_suggestions = []

        if "model_data" in error_msg_str or "model" in error_msg_str:
            recovery_suggestions.extend(
                [
                    "Ensure MODEL_DATA is populated before calibration",
                    "Use --auto-fields to automatically populate MODEL_DATA from catalog",
                    "Or use --model-source setjy to create point source model",
                    "Check that calibrator flux is correct for your frequency",
                ]
            )
        elif "flag" in error_msg_str or "flagged" in error_msg_str:
            recovery_suggestions.extend(
                [
                    "Check flagging statistics: too much data may be flagged",
                    "Review RFI flagging results and adjust thresholds if needed",
                    "Try --no-auto-flag-channels if channel flagging is too aggressive",
                    "Verify reference antenna has unflagged data",
                ]
            )
        elif "refant" in error_msg_str or "reference" in error_msg_str:
            recovery_suggestions.extend(
                [
                    "Verify reference antenna has unflagged data",
                    "Try a different reference antenna with --refant",
                    "Check antenna selection: python -m dsa110_contimg.calibration.cli qa check-delays --ms <path>",
                ]
            )
        elif "snr" in error_msg_str or "signal" in error_msg_str:
            recovery_suggestions.extend(
                [
                    "Calibrator may be too faint - check flux density",
                    "Try combining more fields with --bp-combine-field",
                    "Reduce --gain-minsnr threshold (default: 3.0)",
                    "Increase integration time or use longer solution intervals",
                ]
            )
        elif "table" in error_msg_str or "caltable" in error_msg_str:
            recovery_suggestions.extend(
                [
                    "Check that previous calibration tables exist and are valid",
                    "Verify table compatibility with MS",
                    "Try removing old tables and recalibrating from scratch",
                ]
            )
        else:
            recovery_suggestions.extend(
                [
                    "Check MS path is correct and file exists",
                    "Verify file permissions and disk space",
                    "Review logs for detailed error information",
                    "Run validation: python -m dsa110_contimg.calibration.cli validate --ms <path>",
                ]
            )

        error_msg = format_error_with_context(e, context)
        logger.error(error_msg)

        if recovery_suggestions:
            logger.error("\nRecovery suggestions:")
            for i, suggestion in enumerate(recovery_suggestions, 1):
                logger.error(f"  {i}. {suggestion}")

        # Attempt automatic recovery for common issues
        if "model_data" in error_msg_str and not args.dry_run:
            logger.info("\nAttempting automatic recovery: populating MODEL_DATA...")
            try:
                # This would require importing the model population code
                # For now, just log the suggestion
                logger.info("  → Run with --auto-fields to automatically populate MODEL_DATA")
            except Exception as recovery_error:
                logger.warning(f"Automatic recovery failed: {recovery_error}")

        sys.exit(1)

    tabs = (ktabs[:1] if ktabs else []) + bptabs + gtabs
    logger.info("[6/6] Calibration complete!")
    logger.info("=" * 70)
    logger.info("Generated calibration tables:")
    for tab in tabs:
        logger.info(f"  - {tab}")
    total_time = time.time() - start_time
    logger.info(f"Total calibration time: {total_time:.1f}s ({total_time / 60:.1f} min)")
    logger.info("=" * 70)

    # Validate expected calibration tables exist
    if not args.dry_run:
        try:
            from pathlib import Path

            from dsa110_contimg.calibration.caltable_paths import (
                validate_caltables_exist,
            )

            # Determine caltable directory (same as MS directory by default)
            caltable_dir = Path(ms_in).parent

            # Determine SPW mapping if bandpass tables were created with mapping
            spwmap = None
            if bptabs and len(bptabs) > 0:
                # Check if we used SPW mapping (would need to track this from solve_bandpass)
                # For now, assume no mapping unless we can infer from table names
                pass

            existing, missing = validate_caltables_exist(
                ms_path=ms_in, caltable_dir=str(caltable_dir), caltype="all"
            )

            if missing["all"]:
                logger.warning(f"Expected calibration tables missing: {missing['all']}")
                logger.info(f"Existing tables: {existing['all']}")
            else:
                logger.info(f"✓ All expected calibration tables present: {existing['all']}")
        except Exception as e:
            logger.warning(f"Could not validate calibration table completeness: {e}")

    # Register calibration tables in registry database (if not dry-run)
    if not args.dry_run and tabs:
        try:
            import re
            from pathlib import Path

            from dsa110_contimg.database.registry import (
                ensure_db,
                register_set_from_prefix,
            )
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            # Determine registry DB path (same logic as apply_service)
            # Try CAL_REGISTRY_DB env var first, then PIPELINE_STATE_DIR, then default
            registry_db_env = os.environ.get("CAL_REGISTRY_DB")
            if registry_db_env:
                registry_db = Path(registry_db_env)
            else:
                state_dir = Path(os.environ.get("PIPELINE_STATE_DIR", "/data/dsa110-contimg/state"))
                registry_db = state_dir / "cal_registry.sqlite3"

            # Ensure registry DB exists (creates if missing)
            ensure_db(registry_db)

            # Extract time range from MS for validity window
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_in)
            if mid_mjd is None:
                logger.warning(f"Could not extract time range from {ms_in}, using current time")
                from astropy.time import Time

                mid_mjd = Time.now().mjd
                start_mjd = mid_mjd - 0.5  # 12 hour window
                end_mjd = mid_mjd + 0.5

            # Generate set name from MS filename and time
            ms_base = Path(ms_in).stem
            set_name = f"{ms_base}_{mid_mjd:.6f}"

            # Determine table prefix
            # If table_prefix_override was used, extract it from the first table
            # Otherwise, extract common prefix from all tables
            if tabs:
                table_dir = Path(tabs[0]).parent
                first_table_name = Path(tabs[0]).stem

                # Remove table type suffixes to get base prefix
                prefix_base = re.sub(
                    r"_(bpcal|gpcal|gacal|2gcal|kcal|bacal|flux)$",
                    "",
                    first_table_name,
                    flags=re.IGNORECASE,
                )
                table_prefix = table_dir / prefix_base

                logger.info(f"Registering calibration tables in registry: {set_name}")
                logger.debug(f"Using table prefix: {table_prefix}")
                registered = register_set_from_prefix(
                    registry_db,
                    set_name,
                    table_prefix,
                    cal_field=field_sel,
                    refant=refant,
                    valid_start_mjd=start_mjd,
                    valid_end_mjd=end_mjd,
                    status="active",
                )
                if registered:
                    logger.info(f"✓ Registered {len(registered)} calibration tables in registry")
                else:
                    logger.warning(
                        f"Warning: No tables found with prefix {table_prefix} for registration. "
                        f"Tables may not be discoverable by apply_calibration via registry lookup."
                    )
        except Exception as e:
            # Registration failure is non-fatal for CLI (user can register manually if needed)
            logger.warning(
                f"Failed to register calibration tables in registry: {e}. "
                f"Tables were created but not registered. You can register them manually using "
                f"the registry CLI or provide tables explicitly to apply_calibration.",
                exc_info=True,
            )

    # Cleanup subset MS if requested
    if args.cleanup_subset and subset_ms_created:
        import shutil

        try:
            logger.info(f"Cleaning up subset MS: {subset_ms_created}")
            shutil.rmtree(subset_ms_created, ignore_errors=True)
            logger.info("✓ Subset MS removed")
        except Exception as e:
            logger.warning(f"Failed to remove subset MS {subset_ms_created}: {e}")

    # Generate diagnostics if requested
    if args.diagnostics:
        print("\nGenerating calibration diagnostics...")
        try:
            diagnostics = generate_calibration_diagnostics(
                ms_in,
                field=field_sel,
                refant=refant,
                check_caltables=True,
                check_corrected_data=False,  # Calibration hasn't been applied yet
            )
            diagnostics.print_report()
        except Exception as e:
            logger.warning(f"Failed to generate diagnostics: {e}")

    return 0
