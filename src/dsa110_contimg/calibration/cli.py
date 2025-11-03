import argparse
import time
import os
import sys
from typing import List

# Use shared CLI utilities
from dsa110_contimg.utils.cli_helpers import (
    setup_casa_environment,
    add_common_ms_args,
    add_common_logging_args,
    configure_logging_from_args,
)
from dsa110_contimg.utils.validation import (
    validate_ms_for_calibration,
    validate_corrected_data_quality,
    ValidationError,
)

# Set CASA log directory BEFORE any CASA imports - CASA writes logs to CWD
setup_casa_environment()

from .flagging import (
    reset_flags, flag_zeros, flag_rfi, flag_antenna, flag_baselines,
    flag_manual, flag_shadow, flag_quack, flag_elevation, flag_clip,
    flag_extend, flag_summary,
)
from .calibration import solve_delay, solve_bandpass, solve_gains
from .applycal import apply_to_target
from .selection import select_bandpass_fields, select_bandpass_from_catalog
from . import qa
from .diagnostics import generate_calibration_diagnostics, compare_calibration_tables
try:
    # Ensure casacore temp files go to scratch, not the repo root
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore


def run_calibrator(ms: str, cal_field: str, refant: str, *,
                   do_flagging: bool = True, do_k: bool = False) -> List[str]:
    """Run K, BP and G solves on a calibrator MS.

    Note: On-the-fly MS metadata repair has been removed. If a dataset is
    malformed, prefer reconversion with the current writer.
    
    Args:
        do_k: If True, perform K-calibration (delay). Default False for connected-element
              arrays like DSA-110. K-calibration is primarily needed for VLBI arrays.
    """
    if do_flagging:
        reset_flags(ms)
        flag_zeros(ms)
        flag_rfi(ms)
    ktabs = solve_delay(ms, cal_field, refant) if do_k else []
    bptabs = solve_bandpass(ms, cal_field, refant, ktabs[0] if ktabs else None)
    gtabs = solve_gains(ms, cal_field, refant, ktabs[0] if ktabs else None, bptabs)
    return ktabs[:1] + bptabs + gtabs


def main():
    # Best-effort: route TempLattice and similar to scratch
    try:
        if prepare_temp_environment is not None:
            prepare_temp_environment(os.getenv('CONTIMG_SCRATCH_DIR') or '/scratch/dsa110-contimg')
    except Exception:
        pass
    p = argparse.ArgumentParser(
        description="CASA 6.7 calibration runner (no dsacalib)")
    # Add common logging arguments
    add_common_logging_args(p)
    
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser(
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
    pc.add_argument("--ms", required=True, help="Path to Measurement Set")
    pc.add_argument("--field", required=False, default=None,
                    help="Calibrator field name/index or range (e.g. 10~12)")
    pc.add_argument("--refant", required=False, default=None)
    pc.add_argument(
        "--refant-ranking",
        help="Path to refant_ranking.json for auto selection")
    pc.add_argument(
        "--auto-fields",
        action="store_true",
        help="Automatically select bandpass fields using calibrator info")
    pc.add_argument(
        "--cal-ra-deg",
        type=float,
        help="Calibrator RA (deg) for auto field selection")
    pc.add_argument(
        "--cal-dec-deg",
        type=float,
        help="Calibrator Dec (deg) for auto field selection")
    pc.add_argument(
        "--cal-flux-jy",
        type=float,
        help="Calibrator flux (Jy) for weighting in auto selection")
    pc.add_argument(
        "--cal-catalog",
        help="Path to VLA calibrator catalog for auto field selection")
    pc.add_argument(
        "--cal-search-radius-deg",
        type=float,
        default=1.0,
        help="Search radius (deg) around catalog entries")
    pc.add_argument(
        "--pt-dec-deg",
        type=float,
        help="Pointing declination (deg) for catalog weighting")
    pc.add_argument(
        "--bp-window",
        type=int,
        default=3,
        help="Number of fields (approx) around peak to include")
    pc.add_argument(
        "--bp-min-pb",
        type=float,
        default=None,
        help=(
            "Primary-beam gain threshold [0-1] to auto-size field window "
            "around peak"
        ),
    )
    pc.add_argument(
        "--bp-combine-field",
        action="store_true",
        help="Combine across selected fields when solving bandpass/gains")
    pc.add_argument(
        "--fast",
        action="store_true",
        help=(
            "Enable fast path: subset MS (time/channel avg), "
            "phase-only gains, uvrange cuts"
        ),
    )
    pc.add_argument(
        "--do-k",
        action="store_true",
        help=(
            "Enable delay (K) calibration. "
            "K-calibration is typically only needed for VLBI arrays (very long baselines). "
            "Connected-element arrays like DSA-110 (2.6 km max baseline) follow VLA/ALMA practice "
            "and skip K-calibration by default. Residual delays are absorbed into complex gain calibration."
        ),
    )
    pc.add_argument(
        "--skip-bp",
        action="store_true",
        help="Skip bandpass (BP) solve",
    )
    pc.add_argument(
        "--skip-g",
        action="store_true",
        help="Skip gain (G) solve",
    )
    pc.add_argument(
        "--gain-solint",
        default="inf",
        help="Gain solution interval (e.g., 'inf', '60s', '10min')",
    )
    pc.add_argument(
        "--gain-calmode",
        default="ap",
        choices=["ap", "p", "a"],
        help="Gain calibration mode: ap (amp+phase), p (phase-only), a (amp-only)",
    )
    pc.add_argument(
        "--timebin",
        default=None,
        help="Time averaging for fast subset, e.g. '30s'",
    )
    pc.add_argument(
        "--chanbin",
        type=int,
        default=None,
        help="Channel binning factor for fast subset (>=2)",
    )
    pc.add_argument(
        "--uvrange",
        default="",
        help="uvrange selection (e.g. '>1klambda') for fast solves",
    )
    pc.add_argument(
        "--combine-spw",
        action="store_true",
        help=(
            "Combine spectral windows when solving K (delay) calibration. "
            "Recommended for multi-SPW MS files to improve performance. "
            "Default: process SPWs separately"
        ),
    )
    pc.add_argument(
        "--k-fast-only",
        action="store_true",
        help=(
            "Skip slow (inf interval) K-calibration solve and only run fast (60s) solve. "
            "Only applicable when --do-k is used. Significantly faster (~2-3 min vs 15+ min) "
            "but may have lower accuracy for time-variable delays. Recommended only for "
            "production calibrator processing where speed is prioritized over comprehensive delay correction."
        ),
    )
    pc.add_argument(
        "--no-flagging",
        action="store_true",
        help=(
            "Disable pre-solve flagging to avoid crashes on nonstandard "
            "polarizations"
        ),
    )
    pc.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Simulate calibration without writing caltables. "
            "Validates inputs, checks data quality, and estimates time/cost."
        ),
    )
    pc.add_argument(
        "--diagnostics",
        action="store_true",
        help=(
            "Generate comprehensive diagnostic report after calibration. "
            "Includes solution quality metrics, SNR analysis, flag statistics, etc."
        ),
    )
    pc.add_argument(
        "--minimal",
        action="store_true",
        help=(
            "Very fast calibration test (<30s). "
            "Uses minimal subset: 1 baseline, 4 channels, 1 time integration. "
            "For quick iteration only - not for production use."
        ),
    )
    pc.add_argument(
        "--model-source",
        choices=["catalog", "setjy", "component", "image"],
        help=(
            "Populate MODEL_DATA before bandpass using the specified strategy"
        ),
    )
    pc.add_argument(
        "--model-component",
        help=(
            "Path to CASA component list (.cl) when --model-source=component"
        ),
    )
    pc.add_argument(
        "--model-image",
        help="Path to CASA image when --model-source=image")
    pc.add_argument(
        "--model-field",
        help="Field name/index for setjy when --model-source=setjy",
    )
    pc.add_argument(
        "--model-setjy-standard",
        default="Perley-Butler 2017",
        help=(
            "Flux standard for setjy (default: Perley-Butler 2017)"
        ),
    )
    pc.add_argument(
        "--model-setjy-spw",
        default="",
        help="Spectral window selection for setjy")
    # On-the-fly MS repair has been removed; prefer reconversion if needed.

    pt = sub.add_parser("apply", help="Apply calibration to target MS")
    pt.add_argument("--ms", required=True)
    pt.add_argument("--field", required=True)
    pt.add_argument("--tables", nargs="+", required=True,
                    help="Calibration tables in order")

    # QA/Diagnostic subcommands
    pc_delays = sub.add_parser("check-delays", help="Check if delays are corrected upstream")
    pc_delays.add_argument("--ms", required=True, help="Path to Measurement Set")
    pc_delays.add_argument("--n-baselines", type=int, default=100,
                          help="Number of baselines to analyze (default: 100)")

    pv_delays = sub.add_parser("verify-delays", help="Verify K-calibration delay solutions")
    pv_delays.add_argument("--ms", required=True, help="Path to Measurement Set")
    pv_delays.add_argument("--kcal", help="Path to K-calibration table (auto-detected if not provided)")
    pv_delays.add_argument("--cal-field", help="Calibrator field (for creating K-cal if missing)")
    pv_delays.add_argument("--refant", default="103", help="Reference antenna (default: 103)")
    pv_delays.add_argument("--no-create", action="store_true",
                          help="Don't create K-cal table if missing")

    pi_delays = sub.add_parser("inspect-delays", help="Inspect K-calibration delay values")
    pi_delays.add_argument("--kcal", help="Path to K-calibration table")
    pi_delays.add_argument("--ms", help="Path to MS (to auto-find K-cal table)")
    pi_delays.add_argument("--find", action="store_true",
                          help="Find K-cal tables for MS instead of inspecting")

    pl_transits = sub.add_parser("list-transits", help="List available calibrator transits with data")
    pl_transits.add_argument("--name", required=True, help="Calibrator name (e.g., '0834+555')")
    pl_transits.add_argument("--input-dir", help="Input directory (default: from env/config)")
    pl_transits.add_argument("--max-days-back", type=int, default=30,
                           help="Maximum days to search back (default: 30)")
    pl_transits.add_argument("--window-minutes", type=int, default=60,
                           help="Search window around transit (default: 60)")
    pl_transits.add_argument("--json", action="store_true", help="Output as JSON")

    # Validation subcommand
    pv = sub.add_parser(
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
    pv.add_argument("--ms", required=True, help="Path to Measurement Set")
    pv.add_argument("--field", required=False, default=None,
                    help="Calibrator field name/index or range")
    pv.add_argument("--refant", required=False, default=None,
                    help="Reference antenna ID")
    
    # Compare subcommand
    pcomp = sub.add_parser(
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
    pcomp.add_argument("--caltable1", required=True, help="Path to first calibration table")
    pcomp.add_argument("--caltable2", required=True, help="Path to second calibration table")
    pcomp.add_argument("--tolerance", type=float, default=1e-6,
                      help="Tolerance for solution agreement (default: 1e-6)")

    # Flag subcommand
    pflag = sub.add_parser(
        "flag",
        help="Flag bad data in a Measurement Set",
        description=(
            "Apply various flagging operations to identify and mark corrupted data.\n\n"
            "Standard flagging modes:\n"
            "  reset      - Unflag all data\n"
            "  zeros      - Flag zero-value data (correlator failures)\n"
            "  rfi        - RFI detection (tfcrop + rflag algorithms)\n"
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
    pflag.add_argument("--ms", required=True, help="Path to Measurement Set")
    pflag.add_argument(
        "--mode",
        required=True,
        choices=["reset", "zeros", "rfi", "shadow", "quack", "elevation",
                 "clip", "extend", "manual", "antenna", "baselines", "summary"],
        help="Flagging mode"
    )
    pflag.add_argument("--datacolumn", default="data",
                       choices=["data", "corrected_data", "model_data"],
                       help="Data column to use (default: data)")
    
    # Mode-specific arguments
    pflag.add_argument("--shadow-tolerance", type=float, default=0.0,
                       help="Shadow tolerance in degrees (for shadow mode)")
    pflag.add_argument("--quack-interval", type=float, default=2.0,
                       help="Quack interval in seconds (for quack mode, default: 2.0)")
    pflag.add_argument("--quack-mode", default="beg",
                       choices=["beg", "end", "tail", "endb"],
                       help="Quack mode: beg (beginning), end, tail, or endb (default: beg)")
    pflag.add_argument("--lower-limit", type=float,
                       help="Minimum elevation in degrees (for elevation mode)")
    pflag.add_argument("--upper-limit", type=float,
                       help="Maximum elevation in degrees (for elevation mode)")
    pflag.add_argument("--clip-min", type=float,
                       help="Minimum amplitude threshold in Jy (for clip mode)")
    pflag.add_argument("--clip-max", type=float,
                       help="Maximum amplitude threshold in Jy (for clip mode)")
    pflag.add_argument("--clip-outside", action="store_true", default=True,
                       help="Flag outside clip range (default: True, use --no-clip-outside for inside)")
    pflag.add_argument("--no-clip-outside", dest="clip_outside", action="store_false",
                       help="Flag inside clip range instead of outside")
    pflag.add_argument("--grow-time", type=float, default=0.0,
                       help="Fraction of time flagged to flag entire time slot (0-1, for extend mode)")
    pflag.add_argument("--grow-freq", type=float, default=0.0,
                       help="Fraction of frequency flagged to flag entire channel (0-1, for extend mode)")
    pflag.add_argument("--grow-around", action="store_true",
                       help="Flag points if most neighbors are flagged (for extend mode)")
    pflag.add_argument("--flag-near-time", action="store_true",
                       help="Flag points before/after flagged regions (for extend mode)")
    pflag.add_argument("--flag-near-freq", action="store_true",
                       help="Flag points adjacent to flagged channels (for extend mode)")
    pflag.add_argument("--antenna", help="Antenna selection (for antenna or manual mode)")
    pflag.add_argument("--uvrange", help="UV range selection (for baselines or manual mode, e.g., '2~50m')")
    pflag.add_argument("--scan", help="Scan selection (for manual mode, e.g., '1~5')")
    pflag.add_argument("--spw", help="Spectral window selection (for manual mode, e.g., '0:10~20')")
    pflag.add_argument("--field", help="Field selection (for manual mode)")
    pflag.add_argument("--timerange", help="Time range selection (for manual mode)")
    pflag.add_argument("--correlation", help="Correlation selection (for manual mode, e.g., 'RR,LL')")

    args = p.parse_args()

    # Configure logging using shared utility
    logger = configure_logging_from_args(args)

    if args.cmd == "calibrate":
        # Comprehensive MS validation using shared validation module
        try:
            warnings = validate_ms_for_calibration(
                args.ms,
                field=args.field if args.field else None,
                refant=args.refant
            )
            # Log warnings but don't fail
            for warning in warnings:
                logger.warning(warning)
        except ValidationError as e:
            logger.error("Validation failed:")
            error_msg = e.format_with_suggestions()
            logger.error(error_msg)
            sys.exit(1)
        
        field_sel = args.field
        # Defaults to ensure variables exist for later logic
        idxs = []  # type: ignore[assignment]
        wflux = []  # type: ignore[assignment]
        if args.auto_fields:
            try:
                if args.cal_catalog:
                    # Validate catalog file exists
                    try:
                        from dsa110_contimg.utils.validation import validate_file_path
                        validate_file_path(args.cal_catalog, must_exist=True, must_readable=True)
                    except ValidationError as e:
                        logger.error("Catalog validation failed:")
                        for error in e.errors:
                            logger.error(f"  - {error}")
                        sys.exit(1)
                    
                    sel, idxs, wflux, calinfo = select_bandpass_from_catalog(
                        args.ms,
                        args.cal_catalog,
                        search_radius_deg=float(
                            args.cal_search_radius_deg or 1.0
                        ),
                        window=max(1, int(args.bp_window)),
                        min_pb=(
                            float(args.bp_min_pb)
                            if args.bp_min_pb is not None
                            else None
                        ),
                    )
                    name, ra_deg, dec_deg, flux_jy = calinfo
                    print(
                        (
                            "Catalog calibrator: {name} (RA {ra_deg:.4f} deg, "
                            "Dec {dec_deg:.4f} deg, flux {flux_jy:.2f} Jy)"
                        ).format(
                            name=name,
                            ra_deg=ra_deg,
                            dec_deg=dec_deg,
                            flux_jy=flux_jy,
                        )
                    )
                    print(
                        "Auto-selected bandpass fields: {} (indices: {})"
                        .format(sel, idxs)
                    )
                    field_sel = sel
                else:
                    if (
                        args.cal_ra_deg is None
                        or args.cal_dec_deg is None
                        or args.cal_flux_jy is None
                    ):
                        p.error(
                            (
                                "--auto-fields requires --cal-ra-deg/"
                                "--cal-dec-deg/--cal-flux-jy or --cal-catalog"
                            )
                        )
                    sel, idxs, wflux = select_bandpass_fields(
                        args.ms,
                        args.cal_ra_deg,
                        args.cal_dec_deg,
                        args.cal_flux_jy,
                        window=max(1, int(args.bp_window)),
                        min_pb=(
                            float(args.bp_min_pb)
                            if args.bp_min_pb is not None
                            else None
                        ),
                    )
                    print(
                        "Auto-selected bandpass fields: {} (indices: {})"
                        .format(sel, idxs)
                    )
                    field_sel = sel
            except Exception as e:
                print(
                    (
                        "Auto field selection failed ({}); falling back to "
                        "--field"
                    ).format(e)
                )
                if field_sel is None:
                    p.error(
                        "No --field provided and auto selection failed"
                    )
        if field_sel is None:
            p.error("--field is required when --auto-fields is not used")
        
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
                with open(args.refant_ranking, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                rec = data.get('recommended') if isinstance(
                    data, dict) else None
                if rec and rec.get('antenna_id') is not None:
                    refant = str(rec['antenna_id'])
                    print(f"Reference antenna (from ranking): {refant}")
            except Exception as e:
                # PRECONDITION CHECK: If refant ranking fails and --refant not provided, fail fast
                # This ensures we follow "measure twice, cut once" - establish requirements upfront.
                if args.refant is None:
                    p.error(
                        f"Failed to read refant ranking ({e}) and --refant not provided. "
                        f"Provide one or the other."
                    )
                print(
                    f"Failed to read refant ranking ({e}); using --refant={args.refant}"
                )
        if refant is None:
            p.error("Provide --refant or --refant-ranking")
        
        # Note: Reference antenna validation was already done by validate_ms_for_calibration above
        # If refant changed due to refant-ranking, we trust that the ranking provided a valid antenna

        # MS repair flags removed.
        # Optionally create a fast subset MS
        ms_in = args.ms
        
        # Handle minimal mode (very fast test calibration)
        if args.minimal:
            # Minimal mode overrides fast mode settings
            logger.info("Minimal mode: creating ultra-fast subset (1 baseline, 4 channels, 1 time)")
            from .subset import make_subset
            from casacore.tables import table
            
            base = ms_in.rstrip('/').rstrip('.ms')
            ms_minimal = f"{base}.minimal.ms"
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
            # Set fast mode parameters if not already set
            if not args.timebin:
                args.timebin = "inf"
            if not args.chanbin:
                args.chanbin = 16
            if not args.uvrange:
                args.uvrange = ""  # No UV range cut for minimal
        
        if args.fast and (args.timebin or args.chanbin) and not args.minimal:
            from .subset import make_subset
            from casacore.tables import table
            
            base = ms_in.rstrip('/').rstrip('.ms')
            ms_fast = f"{base}.fast.ms"
            print(
                (
                    "Creating fast subset: timebin={tb} chanbin={cb} -> {out}"
                ).format(tb=args.timebin, cb=args.chanbin, out=ms_fast)
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
            logger.info()
            
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
                from casacore.tables import table
                import numpy as np
                with table(ms_in, readonly=True) as tb:
                    n_rows = tb.nrows()
                    sample_size = min(10000, n_rows)
                    if sample_size > 0:
                        flags_sample = tb.getcol('FLAG', startrow=0, nrow=sample_size)
                        current_unflagged = float(np.mean(~flags_sample))
                        # Estimate after flagging (conservative: 10-20% reduction)
                        estimated_unflagged = current_unflagged * 0.85
                        logger.info(f"Estimated unflagged data after flagging: {estimated_unflagged*100:.1f}%")
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
            reset_flags(ms_in)
            flag_zeros(ms_in)
            flag_rfi(ms_in)
            
            # PRECONDITION CHECK: Verify sufficient unflagged data remains after flagging
            # This ensures we follow "measure twice, cut once" - verify data quality
            # before proceeding with expensive calibration operations.
            # OPTIMIZATION: Sample flags instead of reading entire MS to avoid performance hit
            try:
                from casacore.tables import table
                import numpy as np
                with table(ms_in, readonly=True) as tb:
                    n_rows = tb.nrows()
                    # Sample up to 10000 rows to estimate flagging fraction
                    sample_size = min(10000, n_rows)
                    if sample_size > 0:
                        flags_sample = tb.getcol('FLAG', startrow=0, nrow=sample_size)
                        total_points = flags_sample.size
                        unflagged_points_sample = np.sum(~flags_sample)
                        unflagged_fraction = unflagged_points_sample / total_points if total_points > 0 else 0.0
                        # Estimate total unflagged points
                        unflagged_points = int(unflagged_points_sample * (n_rows / sample_size))
                    else:
                        total_points = 0
                        unflagged_points = 0
                        unflagged_fraction = 0.0
                    
                    if unflagged_fraction < 0.1:  # Less than 10% unflagged
                        p.error(
                            f"Insufficient unflagged data after flagging: {unflagged_fraction*100:.1f}%. "
                            f"Calibration requires at least 10% unflagged data. "
                            f"Consider adjusting flagging parameters or checking data quality."
                        )
                    elif unflagged_fraction < 0.3:  # Less than 30% unflagged
                        print(
                            f"Warning: Only {unflagged_fraction*100:.1f}% of data remains unflagged "
                            f"after flagging. Calibration may be less reliable."
                        )
                    else:
                        print(
                            f"✓ Flagging complete: {unflagged_fraction*100:.1f}% data remains unflagged "
                            f"({unflagged_points:,}/{total_points:,} points)"
                        )
            except Exception as e:
                p.error(
                    f"Failed to validate unflagged data after flagging: {e}. "
                    f"Cannot proceed with calibration."
                )

        # Determine a peak field for K (if auto-selected, we have idxs/wflux)
        k_field_sel = field_sel
        try:
            # Available only in this scope if auto-fields branch set these
            # locals
            if (
                'idxs' in locals()
                and 'wflux' in locals()
                and idxs is not None
            ):
                import numpy as np
                k_idx = int(idxs[int(np.nanargmax(wflux))])
                k_field_sel = str(k_idx)
        except Exception:
            pass
        # As a fallback, if field_sel is a range like A~B, pick B
        if '~' in str(field_sel) and (k_field_sel == field_sel):
            try:
                _, b = str(field_sel).split('~')
                k_field_sel = str(int(b))
            except Exception:
                pass

        # K-calibration is skipped by default for DSA-110 (connected-element array, 2.6 km max baseline)
        # Following VLA/ALMA practice: residual delays are absorbed into complex gain calibration
        # K-calibration is primarily needed for VLBI arrays (thousands of km baselines)
        # Use --do-k flag to explicitly enable K-calibration if needed
        
        if not args.do_k:
            print(
                "Skipping delay (K) calibration by default (connected-element array practice). "
                "Use --do-k to enable if explicitly needed."
            )
        else:
            print(
                "Delay solve field (K): {}; BP/G fields: {}".format(
                    k_field_sel, field_sel
                )
            )
        
        # CRITICAL: Populate MODEL_DATA BEFORE K-calibration (if enabled)
        # K-calibration requires MODEL_DATA to be populated so it knows what signal
        # to calibrate against. Without MODEL_DATA, solutions are unreliable or may fail.
        # Populate MODEL_DATA according to requested strategy BEFORE solving delays.
        if args.do_k:
            try:
                from . import model as model_helpers
                if args.model_source == "catalog":
                    if (
                        args.auto_fields
                        and args.cal_catalog
                        and 'calinfo' in locals()
                        and isinstance(calinfo, (list, tuple))
                        and len(calinfo) >= 4
                    ):
                        name, ra_deg, dec_deg, flux_jy = calinfo
                        print(
                            (
                                "Writing catalog point model BEFORE K-calibration: {n} @ ("
                                "{ra:.4f},{de:.4f}) deg, {fl:.2f} Jy"
                            ).format(n=name, ra=ra_deg, de=dec_deg, fl=flux_jy)
                        )
                        model_helpers.write_point_model_with_ft(
                            args.ms, float(ra_deg), float(dec_deg), float(flux_jy))
                    else:
                        print(
                            (
                                "Catalog model requested but calibrator info "
                                "unavailable; skipping model write"
                            )
                        )
                elif args.model_source == "setjy":
                    if not args.model_field:
                        p.error("--model-source=setjy requires --model-field")
                    print(
                        (
                            "Running setjy BEFORE K-calibration on field {} (standard {})"
                        ).format(args.model_field, args.model_setjy_standard)
                    )
                    model_helpers.write_setjy_model(
                        args.ms,
                        field=args.model_field,
                        standard=args.model_setjy_standard,
                        spw=args.model_setjy_spw,
                    )
                elif args.model_source == "component":
                    if not args.model_component:
                        p.error(
                            "--model-source=component requires --model-component"
                        )
                    print(
                        "Applying component list model BEFORE K-calibration: {}"
                        .format(args.model_component)
                    )
                    model_helpers.write_component_model_with_ft(
                        args.ms, args.model_component)
                elif args.model_source == "image":
                    if not args.model_image:
                        p.error("--model-source=image requires --model-image")
                    print(
                        "Applying image model BEFORE K-calibration: {}".format(args.model_image)
                    )
                    model_helpers.write_image_model_with_ft(
                        args.ms, args.model_image)
                elif args.model_source is None:
                    # No model source specified - this violates "measure twice, cut once"
                    # We require MODEL_DATA to be populated before K-calibration for consistent,
                    # reliable results across all calibrators (bright or faint).
                    # This ensures the calibration approach works generally, not just "sometimes"
                    # for bright sources.
                    p.error(
                        "--model-source is REQUIRED for K-calibration. "
                        "This ensures consistent, reliable calibration results. "
                        "Use --model-source=setjy (for standard calibrators) or "
                        "--model-source=catalog (for catalog-based models)."
                    )
            except Exception as e:
                # PRECONDITION CHECK: MODEL_DATA population failure is a hard error if K-calibration is enabled
                # This ensures we follow "measure twice, cut once" - establish requirements upfront
                # before expensive calibration operations.
                p.error(
                    f"MODEL_DATA population failed: {e}. "
                    f"This is required for K-calibration. Fix the error and retry."
                )
            
            # PRECONDITION CHECK: Validate MODEL_DATA flux values are reasonable
            # This ensures we follow "measure twice, cut once" - verify MODEL_DATA quality
            # before proceeding with calibration.
            if args.model_source is not None:
                try:
                    from casacore.tables import table
                    import numpy as np
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
                                    model_amps = model_amps[model_amps > 1e-10]  # Filter out near-zero
                                    
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
                                            print(
                                                f"✓ MODEL_DATA validated: median flux {median_flux:.3f} Jy "
                                                f"(range: {min_flux:.3e} - {max_flux:.3e} Jy)"
                                            )
                except Exception as e:
                    # Non-fatal: log warning but don't fail
                    print(f"Warning: MODEL_DATA flux validation failed: {e}")
        
        ktabs = []
        if args.do_k:
            t_k0 = time.perf_counter()
            ktabs = solve_delay(
                ms_in,
                k_field_sel,
                refant,
                combine_spw=args.combine_spw,
                uvrange=(
                    (args.uvrange or "")
                    if args.fast
                    else ""
                ),
                minsnr=5.0,
                skip_slow=args.k_fast_only,
            )
            print(
                "K (delay) solve completed in {:.2f}s".format(
                    time.perf_counter() - t_k0
                )
            )

        bptabs = []
        if not args.skip_bp:
            t_bp0 = time.perf_counter()
            bptabs = solve_bandpass(
                ms_in,
                field_sel,
                refant,
                ktabs[0] if ktabs else None,
                combine_fields=bool(args.bp_combine_field),
                combine_spw=args.combine_spw,
                uvrange=(
                    (args.uvrange or "")
                    if args.fast
                    else ""
                ),
            )
            elapsed_bp = time.perf_counter() - t_bp0
            print("Bandpass solve completed in {:.2f}s".format(elapsed_bp))
        
        gtabs = []
        if not args.skip_g:
            t_g0 = time.perf_counter()
            # Determine phase_only based on gain_calmode
            phase_only = (args.gain_calmode == "p") or bool(args.fast)
            gtabs = solve_gains(
                ms_in,
                field_sel,
                refant,
                ktabs[0] if ktabs else None,
                bptabs,
                combine_fields=bool(args.bp_combine_field),
                phase_only=phase_only,
                uvrange=(
                    (args.uvrange or "")
                    if args.fast
                    else ""
                ),
                solint=args.gain_solint,
            )
            elapsed_g = time.perf_counter() - t_g0
            print("Gain solve completed in {:.2f}s".format(elapsed_g))

        tabs = (ktabs[:1] if ktabs else []) + bptabs + gtabs
        print("Generated tables:\n" + "\n".join(tabs))
        
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
    elif args.cmd == "apply":
        apply_to_target(args.ms, args.field, args.tables)
        print("Applied calibration to target")
    elif args.cmd == "check-delays":
        results = qa.check_upstream_delay_correction(args.ms, args.n_baselines)
        if "error" in results:
            sys.exit(1)
        rec = results.get("recommendation", "unknown")
        print(f"\n{'='*70}")
        print("Summary:")
        print(f"{'='*70}\n")
        if rec == "likely_corrected":
            print("Recommendation: K-calibration may be skipped")
            print("  Delays appear to be corrected upstream")
        elif rec == "partial":
            print("Recommendation: K-calibration optional but recommended")
            print("  Small residual delays may benefit from correction")
        else:
            print("Recommendation: K-calibration is NECESSARY")
            print("  Significant delays require correction")
    elif args.cmd == "verify-delays":
        # Import verify function from qa (we'll add this next)
        from dsa110_contimg.calibration.qa import verify_kcal_delays
        verify_kcal_delays(args.ms, args.kcal, args.cal_field, args.refant, args.no_create)
    elif args.cmd == "inspect-delays":
        # Import inspect function from qa (we'll add this next)
        from dsa110_contimg.calibration.qa import inspect_kcal_simple
        inspect_kcal_simple(args.kcal, args.ms, args.find)
    elif args.cmd == "list-transits":
        from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
        from dsa110_contimg.conversion.config import CalibratorMSConfig
        import json
        
        config = CalibratorMSConfig.from_env()
        if args.input_dir:
            config.input_dir = args.input_dir
        service = CalibratorMSGenerator.from_config(config, verbose=False)
        
        transits = service.list_available_transits(
            args.name,
            max_days_back=args.max_days_back,
            window_minutes=args.window_minutes
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
    elif args.cmd == "validate":
        # Validate MS for calibration
        try:
            warnings = validate_ms_for_calibration(
                args.ms,
                field=args.field if args.field else None,
                refant=args.refant
            )
            logger.info("\n✓ MS validation passed")
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
    elif args.cmd == "compare":
        # Compare two calibration tables
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
                logger.info("✓ Calibration solutions are consistent")
        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            sys.exit(1)
    elif args.cmd == "flag":
        # Validate MS before flagging
        try:
            from dsa110_contimg.utils.validation import validate_ms
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
            logger.info("Flagging RFI (tfcrop + rflag)...")
            flag_rfi(args.ms, datacolumn=args.datacolumn)
            logger.info("✓ RFI flagging complete")
        
        elif mode == "shadow":
            logger.info(f"Flagging shadowed baselines (tolerance: {args.shadow_tolerance} deg)...")
            flag_shadow(args.ms, tolerance=args.shadow_tolerance)
            logger.info("✓ Shadow flagging complete")
        
        elif mode == "quack":
            logger.info(f"Flagging {args.quack_mode} of scans ({args.quack_interval}s)...")
            flag_quack(args.ms, quackinterval=args.quack_interval,
                      quackmode=args.quack_mode, datacolumn=args.datacolumn)
            logger.info(f"✓ Quack flagging complete ({args.quack_mode}, {args.quack_interval}s)")
        
        elif mode == "elevation":
            limits = []
            if args.lower_limit is not None:
                limits.append(f"lower={args.lower_limit}°")
            if args.upper_limit is not None:
                limits.append(f"upper={args.upper_limit}°")
            limit_str = ", ".join(limits) if limits else "no limits"
            logger.info(f"Flagging elevation: {limit_str}...")
            flag_elevation(args.ms, lowerlimit=args.lower_limit,
                          upperlimit=args.upper_limit, datacolumn=args.datacolumn)
            logger.info("✓ Elevation flagging complete")
        
        elif mode == "clip":
            if args.clip_min is None or args.clip_max is None:
                logger.error("--clip-min and --clip-max are required for clip mode")
                sys.exit(1)
            clip_range = [args.clip_min, args.clip_max]
            direction = "outside" if args.clip_outside else "inside"
            logger.info(f"Flagging amplitudes {direction} range [{clip_range[0]}, {clip_range[1]}] Jy...")
            flag_clip(args.ms, clipminmax=clip_range, clipoutside=args.clip_outside,
                     datacolumn=args.datacolumn)
            logger.info(f"✓ Clip flagging complete ({direction} [{clip_range[0]}, {clip_range[1]}] Jy)")
        
        elif mode == "extend":
            logger.info("Extending existing flags...")
            flag_extend(args.ms, growtime=args.grow_time, growfreq=args.grow_freq,
                       growaround=args.grow_around, flagneartime=args.flag_near_time,
                       flagnearfreq=args.flag_near_freq, datacolumn=args.datacolumn)
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
            flag_manual(args.ms, antenna=args.antenna, scan=args.scan, spw=args.spw,
                       field=args.field, uvrange=args.uvrange, timerange=args.timerange,
                       correlation=args.correlation, datacolumn=args.datacolumn)
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
            logger.info(f"Total fraction flagged: {stats.get('total_fraction_flagged', 0.0)*100:.2f}%")
            logger.info(f"Total rows: {stats.get('n_rows', 0):,}")
            logger.info("=" * 70)
        
        # Report flagging statistics after flagging (except for summary mode)
        if mode != "summary":
            try:
                stats = flag_summary(args.ms)
                flagged_pct = stats.get('total_fraction_flagged', 0.0) * 100
                logger.info(f"\nFlagging complete. Total flagged: {flagged_pct:.2f}%")
            except Exception as e:
                logger.debug(f"Could not compute flagging statistics: {e}")


if __name__ == "__main__":
    main()
