import argparse
import time
import os
import sys
from typing import List

# Ensure headless operation before any CASA imports (prevents casaplotserver X server errors)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.environ.get("DISPLAY"):
    os.environ.pop("DISPLAY", None)

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

# Note: CASA environment setup moved to main() to avoid import-time side effects
# CASA imports deferred until needed

from .flagging import (
    reset_flags, flag_zeros, flag_rfi, flag_antenna, flag_baselines,
    flag_manual, flag_shadow, flag_quack, flag_elevation, flag_clip,
    flag_extend, flag_summary,
)
from .calibration import solve_delay, solve_bandpass, solve_gains, solve_prebandpass_phase
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


# Module-level flag for calibrator info printing (prevents duplicates)
_calibrator_info_printed_global = False


def _clear_all_calibration_artifacts(ms_path: str, logger) -> None:
    """Clear all calibration artifacts from MS and directory.
    
    Clears:
    - MODEL_DATA column (fills with zeros)
    - CORRECTED_DATA column (fills with zeros)
    - Any calibration tables (*.cal) in MS directory
    
    Args:
        ms_path: Path to Measurement Set
        logger: Logger instance
    """
    import numpy as np
    from casacore.tables import table
    import glob
    import os
    
    ms_dir = os.path.dirname(os.path.abspath(ms_path))
    ms_name = os.path.basename(ms_path.rstrip('/').rstrip('.ms'))
    
    cleared_items = []
    
    # 1. Clear MODEL_DATA
    try:
        with table(ms_path, readonly=False) as tb:
            if "MODEL_DATA" in tb.colnames() and tb.nrows() > 0:
                # Get DATA shape to match MODEL_DATA shape
                if "DATA" in tb.colnames():
                    data_sample = tb.getcell("DATA", 0)
                    data_shape = getattr(data_sample, "shape", None)
                    data_dtype = getattr(data_sample, "dtype", None)
                    if data_shape and data_dtype:
                        zeros = np.zeros((tb.nrows(),) + data_shape, dtype=data_dtype)
                        tb.putcol("MODEL_DATA", zeros)
                        cleared_items.append("MODEL_DATA")
                        print(f"  ✓ Cleared MODEL_DATA ({tb.nrows()} rows)")
    except Exception as e:
        logger.warning(f"Could not clear MODEL_DATA: {e}")
    
    # 2. Clear CORRECTED_DATA
    try:
        with table(ms_path, readonly=False) as tb:
            if "CORRECTED_DATA" in tb.colnames() and tb.nrows() > 0:
                # Get DATA shape to match CORRECTED_DATA shape
                if "DATA" in tb.colnames():
                    data_sample = tb.getcell("DATA", 0)
                    data_shape = getattr(data_sample, "shape", None)
                    data_dtype = getattr(data_sample, "dtype", None)
                    if data_shape and data_dtype:
                        zeros = np.zeros((tb.nrows(),) + data_shape, dtype=data_dtype)
                        tb.putcol("CORRECTED_DATA", zeros)
                        cleared_items.append("CORRECTED_DATA")
                        print(f"  ✓ Cleared CORRECTED_DATA ({tb.nrows()} rows)")
    except Exception as e:
        logger.warning(f"Could not clear CORRECTED_DATA: {e}")
    
    # 3. Remove calibration tables in MS directory
    try:
        cal_patterns = [
            os.path.join(ms_dir, "*.cal"),
            os.path.join(ms_dir, "*_kcal"),
            os.path.join(ms_dir, "*_bpcal"),
            os.path.join(ms_dir, "*_gpcal"),
            os.path.join(ms_dir, "*_gacal"),
            os.path.join(ms_dir, f"{ms_name}_*.cal"),
        ]
        
        removed_tables = []
        for pattern in cal_patterns:
            for cal_table in glob.glob(pattern):
                if os.path.isdir(cal_table):  # CASA tables are directories
                    try:
                        import shutil
                        shutil.rmtree(cal_table)
                        removed_tables.append(os.path.basename(cal_table))
                    except Exception as e:
                        logger.warning(f"Could not remove {cal_table}: {e}")
                elif os.path.isfile(cal_table):
                    try:
                        os.remove(cal_table)
                        removed_tables.append(os.path.basename(cal_table))
                    except Exception as e:
                        logger.warning(f"Could not remove {cal_table}: {e}")
        
        if removed_tables:
            cleared_items.append(f"{len(removed_tables)} calibration table(s)")
            print(f"  ✓ Removed {len(removed_tables)} calibration table(s): {', '.join(removed_tables[:5])}")
            if len(removed_tables) > 5:
                print(f"    ... and {len(removed_tables) - 5} more")
        else:
            print(f"  ✓ No calibration tables found to remove")
    except Exception as e:
        logger.warning(f"Could not remove calibration tables: {e}")
    
    if not cleared_items:
        print(f"  ℹ No calibration artifacts found to clear")


def main():
    global _calibrator_info_printed_global
    
    # Set CASA log directory BEFORE any CASA operations (not at import time)
    # This avoids global side effects when module is imported
    try:
        # Use context manager for CASA operations - will be used in calibrate subcommand
        # For now, set up CWD for CASA log files
        setup_casa_environment()
    except Exception:
        pass  # Best-effort; continue if setup fails
    
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
        help=(
            "Path to VLA calibrator catalog for auto field selection. "
            "If not provided, auto-resolves to SQLite database at "
            "state/catalogs/vla_calibrators.sqlite3 (preferred). "
            "Accepts both SQLite (.sqlite3) and CSV formats."
        ))
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
        "--flagging-mode",
        choices=["none", "zeros", "rfi"],
        default="zeros",
        help=(
            "Pre-solve flagging mode: none (no flagging), zeros (clip zeros), rfi (zeros + tfcrop+rflag). "
            "Recommended for calibrators: zeros"
        ),
    )
    pc.add_argument(
        "--bp-minsnr",
        type=float,
        default=float(os.getenv("CONTIMG_CAL_BP_MINSNR", "3.0")),
        help=(
            "Minimum SNR threshold for bandpass solutions (default: 3.0; "
            "override with CONTIMG_CAL_BP_MINSNR)."
        ),
    )
    pc.add_argument(
        "--bp-smooth-type",
        choices=["none", "hanning", "boxcar", "gaussian"],
        default="none",
        help=(
            "Optional smoothing of bandpass table after solve (off by default)."
        ),
    )
    pc.add_argument(
        "--bp-smooth-window",
        type=int,
        help="Smoothing window (channels) for bandpass smoothing",
    )
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
        "--gain-minsnr",
        type=float,
        default=3.0,
        help="Minimum SNR threshold for gain solutions (default: 3.0)",
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
        "--prebp-solint",
        default="inf",
        help="Solution interval for pre-bandpass phase-only solve (default: inf)",
    )
    pc.add_argument(
        "--prebp-minsnr",
        type=float,
        default=5.0,
        help="Minimum SNR for pre-bandpass phase-only solve (default: 5.0)",
    )
    pc.add_argument(
        "--prebp-uvrange",
        default="",
        help="uvrange selection for pre-bandpass phase-only solve (default: none)",
    )
    pc.add_argument(
        "--clear-all",
        action="store_true",
        help=(
            "Clear all calibration artifacts before running calibration: "
            "MODEL_DATA, CORRECTED_DATA, and any existing calibration tables in the MS directory. "
            "Use this when you want a completely clean calibration run."
        ),
    )
    pc.add_argument(
        "--no-flag-autocorr",
        action="store_true",
        help=(
            "Skip flagging autocorrelations before solves (default: flag autos)."
        ),
    )
    pc.add_argument(
        "--prebp-phase",
        action="store_true",
        help=(
            "Run a phase-only solve before bandpass to stabilize time variability (default: off)."
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
        "--preset",
        choices=["fast", "standard", "production", "test"],
        help=(
            "Use preset calibration configuration to simplify common workflows.\n"
            "  fast: Fast subset mode (timebin=30s, chanbin=4, phase-only gains, uvrange cuts)\n"
            "  standard: Full MS, amp+phase gains, no subset (recommended for production)\n"
            "  production: Full MS, optimized for quality\n"
            "  test: Minimal mode for quick tests\n"
            "Individual flags override preset values."
        ),
    )
    pc.add_argument(
        "--cleanup-subset",
        action="store_true",
        help="Remove subset MS files (e.g., .fast.ms, .minimal.ms) after calibration completes",
    )
    pc.add_argument(
        "--no-subset",
        action="store_true",
        help="Disable automatic subset creation even when --fast or --minimal is used",
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
        
        # Apply preset if specified (presets can be overridden by individual flags)
        if args.preset:
            logger.info(f"Applying preset: {args.preset}")
            if args.preset == "fast":
                if not args.timebin:
                    args.timebin = "30s"
                if not args.chanbin:
                    args.chanbin = 4
                if not args.uvrange:
                    args.uvrange = ">1klambda"
                if args.gain_calmode == "ap":  # Only override if not explicitly set
                    args.gain_calmode = "p"
                # Enable fast mode for preset
                args.fast = True
                logger.info("Fast preset: timebin=30s, chanbin=4, phase-only gains, uvrange cuts")
            elif args.preset == "standard":
                args.fast = False
                args.minimal = False
                if args.gain_calmode == "p":  # Only override if not explicitly set
                    args.gain_calmode = "ap"
                logger.info("Standard preset: full MS, amp+phase gains, no subset")
            elif args.preset == "production":
                args.fast = False
                args.minimal = False
                args.gain_calmode = "ap"
                if not args.gain_solint or args.gain_solint == "inf":
                    args.gain_solint = "int"  # Per-integration for production
                logger.info("Production preset: full MS, optimized for quality")
            elif args.preset == "test":
                args.minimal = True
                args.fast = False
                logger.info("Test preset: minimal mode for quick tests")
        
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
                    catalog_path = args.cal_catalog
                else:
                    # Auto-resolve to SQLite database (preferred) or CSV fallback
                    try:
                        from dsa110_contimg.calibration.catalogs import resolve_vla_catalog_path
                        catalog_path = str(resolve_vla_catalog_path(prefer_sqlite=True))
                        logger.info(f"Auto-resolved catalog to: {catalog_path}")
                    except FileNotFoundError as e:
                        logger.error(f"Catalog auto-resolution failed: {e}")
                        logger.error("Provide --cal-catalog explicitly or ensure SQLite catalog exists at state/catalogs/vla_calibrators.sqlite3")
                        sys.exit(1)
                
                print(f"Selecting bandpass fields from catalog...")
                sel, idxs, wflux, calinfo = select_bandpass_from_catalog(
                    args.ms,
                    catalog_path,
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
                print(f"Catalog selection complete: sel={sel}, calinfo={calinfo}")
                name, ra_deg, dec_deg, flux_jy = calinfo
                # Store catalog path and calinfo for later use in MODEL_DATA population
                resolved_catalog_path = catalog_path
                # Print calibrator info only once (prevent duplicate output)
                global _calibrator_info_printed_global
                if not _calibrator_info_printed_global:
                    # Write directly to stdout to avoid any logging interference
                    import sys
                    sys.stdout.write("=" * 60 + "\n")
                    sys.stdout.write(f"CALIBRATOR SELECTED: {name}\n")
                    sys.stdout.write(f"  RA: {ra_deg:.4f} deg\n")
                    sys.stdout.write(f"  Dec: {dec_deg:.4f} deg\n")
                    sys.stdout.write(f"  Flux: {flux_jy:.2f} Jy\n")
                    sys.stdout.write("=" * 60 + "\n")
                    sys.stdout.flush()
                    _calibrator_info_printed_global = True
                print(
                    "Auto-selected bandpass fields: {} (indices: {})"
                    .format(sel, idxs)
                )
                field_sel = sel
                print(f"DEBUG: Field selection complete, field_sel={field_sel}")
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

        # Clear all calibration artifacts if requested
        if args.clear_all:
            print("\n" + "=" * 70)
            print("CLEARING ALL CALIBRATION ARTIFACTS")
            print("=" * 70)
            _clear_all_calibration_artifacts(args.ms, logger)
            print("✓ All calibration artifacts cleared\n")
        
        # MS repair flags removed.
        # Optionally create a fast subset MS
        ms_in = args.ms
        
        # Handle minimal mode (very fast test calibration)
        if args.minimal:
            # Minimal mode overrides fast mode settings
            from .subset import make_subset
            from casacore.tables import table
            
            base = ms_in.rstrip('/').rstrip('.ms')
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
            from .subset import make_subset
            from casacore.tables import table
            
            base = ms_in.rstrip('/').rstrip('.ms')
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
            logger.info(f"Creating fast subset: timebin={args.timebin} chanbin={args.chanbin} -> {ms_fast}")
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
            mode = getattr(args, 'flagging_mode', 'zeros') or 'zeros'
            if mode == 'zeros':
                reset_flags(ms_in)
                flag_zeros(ms_in)
            elif mode == 'rfi':
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
            logger.info(
                "K-calibration skipped by default for DSA-110 "
                "(short baselines <2.6 km, delays <0.5 ns absorbed into gains). "
                "Use --do-k to enable if needed."
            )
        else:
            logger.info(
                f"Delay solve field (K): {k_field_sel}; BP/G fields: {field_sel}"
            )
        
        # CRITICAL: Populate MODEL_DATA BEFORE calibration (K, BP, or G)
        # All calibration steps require MODEL_DATA to be populated so they know what signal
        # to calibrate against. Without MODEL_DATA, solutions are unreliable or may fail.
        # Populate MODEL_DATA according to requested strategy BEFORE solving.
        # NOTE: MODEL_DATA is required for bandpass calibration even when K-calibration is skipped.
        print(f"DEBUG: Checking if MODEL_DATA needs to be populated...")
        needs_model = args.do_k or not args.skip_bp or not args.skip_g
        print(f"DEBUG: needs_model={needs_model}, skip_bp={args.skip_bp}, skip_g={args.skip_g}, do_k={args.do_k}")
        print(f"DEBUG: model_source={args.model_source}")
        if needs_model and args.model_source is not None:
            print(f"DEBUG: Entering MODEL_DATA population section...")
            try:
                print(f"DEBUG: Importing model helpers...")
                from . import model as model_helpers
                print(f"DEBUG: Model helpers imported successfully")
                if args.model_source == "catalog":
                    print(f"DEBUG: Using catalog model source")
                    # Check if we have calibrator info from auto_fields
                    # calinfo is set when --auto-fields is used (regardless of whether --cal-catalog was explicit)
                    if (
                        args.auto_fields
                        and 'calinfo' in locals()
                        and isinstance(calinfo, (list, tuple))
                        and len(calinfo) >= 4
                    ):
                        name, ra_deg, dec_deg, flux_jy = calinfo
                        print(f"DEBUG: Found calibrator info, proceeding with MODEL_DATA population for {name}...")
                        print(f"Populating MODEL_DATA for {name}...")
                        
                        # CRITICAL: Rephase MS to calibrator position before writing MODEL_DATA
                        # The MS is phased to meridian (RA=LST, Dec=pointing), but we need it
                        # phased to the calibrator position for proper calibration SNR
                        # Check if already phased to calibrator (within 1 arcmin tolerance)
                        print("DEBUG: Starting rephasing check...")
                        print("Checking if MS needs rephasing...")
                        needs_rephasing = True
                        try:
                            from casacore.tables import table
                            import numpy as np
                            from astropy.coordinates import SkyCoord
                            from astropy import units as u
                            
                            print("Reading MS phase center...")
                            with table(f"{args.ms}::FIELD") as tf:
                                # CRITICAL: Check REFERENCE_DIR, not PHASE_DIR
                                # REFERENCE_DIR is what CASA actually uses for phase center calculations
                                # PHASE_DIR may be updated by phaseshift but REFERENCE_DIR may not be
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
                            ms_coord = SkyCoord(ra=ms_ra_deg*u.deg, dec=ms_dec_deg*u.deg)
                            cal_coord = SkyCoord(ra=ra_deg*u.deg, dec=dec_deg*u.deg)
                            sep_arcmin = ms_coord.separation(cal_coord).to(u.arcmin).value
                            
                            print(f"Separation: {sep_arcmin:.2f} arcmin")
                            if sep_arcmin < 1.0:
                                print(f"✓ MS already phased to calibrator position (offset: {sep_arcmin:.2f} arcmin)")
                                # CRITICAL: Even if phase center matches, UVW might be in wrong frame
                                # Check UVW alignment - U and V means should be near zero for correctly phased MS
                                try:
                                    from dsa110_contimg.calibration.uvw_verification import get_uvw_statistics
                                    uvw_stats = get_uvw_statistics(args.ms, n_sample=1000)
                                    u_mean_abs = abs(uvw_stats['u_mean'])
                                    v_mean_abs = abs(uvw_stats['v_mean'])
                                    max_offset = max(u_mean_abs, v_mean_abs)
                                    
                                    # For correctly phased MS, U/V means should be < 100 m
                                    # If offset is > 100 m, UVW is likely in wrong frame
                                    if max_offset > 100.0:
                                        print(f"⚠ WARNING: UVW coordinates appear misaligned:")
                                        print(f"  U mean: {uvw_stats['u_mean']:.1f} m (should be near 0)")
                                        print(f"  V mean: {uvw_stats['v_mean']:.1f} m (should be near 0)")
                                        print(f"  Maximum offset: {max_offset:.1f} m exceeds threshold (100 m)")
                                        print(f"  This suggests UVW is in wrong phase center frame despite phase center match")
                                        print(f"  Rephasing to ensure UVW is correctly aligned...")
                                        needs_rephasing = True  # Force rephasing to fix UVW
                                    else:
                                        needs_rephasing = False
                                        print(f"DEBUG: Phase center matches and UVW is aligned (U={uvw_stats['u_mean']:.1f}m, V={uvw_stats['v_mean']:.1f}m)")
                                except Exception as uvw_check_error:
                                    print(f"WARNING: Could not verify UVW alignment: {uvw_check_error}")
                                    print(f"WARNING: Proceeding assuming UVW is correct, but MODEL_DATA may be wrong")
                                    needs_rephasing = False  # Fallback: assume OK if we can't check
                            else:
                                print(f"Rephasing MS to calibrator position: {name} @ ({ra_deg:.4f}°, {dec_deg:.4f}°)")
                                print(f"  Current phase center offset: {sep_arcmin:.2f} arcmin")
                        except Exception as e:
                            print(f"WARNING: Could not check phase center: {e}. Assuming rephasing needed.")
                            logger.warning(f"Could not check phase center: {e}. Assuming rephasing needed.")
                        
                        # CRITICAL: Check UVW alignment regardless of whether rephasing is triggered
                        # UVW must be aligned with phase center, even if phase center appears correct
                        uvw_misaligned = False
                        try:
                            from dsa110_contimg.calibration.uvw_verification import get_uvw_statistics
                            uvw_stats = get_uvw_statistics(args.ms, n_sample=1000)
                            u_mean_abs = abs(uvw_stats['u_mean'])
                            v_mean_abs = abs(uvw_stats['v_mean'])
                            max_uvw_offset = max(u_mean_abs, v_mean_abs)

                            # For correctly phased MS, U/V means should be < 100 m
                            if max_uvw_offset > 100.0:
                                print(f"⚠ WARNING: UVW coordinates are misaligned before any rephasing:")
                                print(f"  U mean: {uvw_stats['u_mean']:.1f} m (should be near 0)")
                                print(f"  V mean: {uvw_stats['v_mean']:.1f} m (should be near 0)")
                                print(f"  Maximum offset: {max_uvw_offset:.1f} m exceeds threshold (100 m)")
                                uvw_misaligned = True
                                needs_rephasing = True  # Force rephasing to fix UVW
                                print(f"  Forcing rephasing to correct UVW misalignment...")
                            else:
                                print(f"DEBUG: UVW coordinates are aligned (max offset: {max_uvw_offset:.1f} m)")
                        except Exception as uvw_check_error:
                            print(f"WARNING: Could not check UVW alignment: {uvw_check_error}")
                            print(f"WARNING: Proceeding, but UVW may be misaligned")

                        if needs_rephasing:
                            print(f"DEBUG: Rephasing needed, starting rephasing workflow...")

                            # Check if this is a UVW-only correction (phase center matches but UVW is wrong)
                            phase_center_matches = sep_arcmin < 1.0
                            if phase_center_matches and uvw_misaligned:
                                print(f"DEBUG: Phase center matches but UVW is misaligned - applying direct UVW correction")
                                try:
                                    # Directly correct UVW coordinates by centering them
                                    from casacore.tables import table as casa_table
                                    import numpy as np

                                    with casa_table(args.ms, readonly=False) as ms_tb:
                                        uvw_data = ms_tb.getcol("UVW")
                                        print(f"DEBUG: Original UVW means - U: {np.mean(uvw_data[:, 0]):.3f}, V: {np.mean(uvw_data[:, 1]):.3f} m")

                                        # Apply correction to center UVW on zero
                                        uvw_data[:, 0] += uvw_correction_u  # Center U
                                        uvw_data[:, 1] += uvw_correction_v  # Center V
                                        # W correction typically not needed for phase center alignment

                                        ms_tb.putcol("UVW", uvw_data)
                                        print(f"DEBUG: Applied UVW correction - U: {uvw_correction_u:+.3f}, V: {uvw_correction_v:+.3f} m")
                                        print(f"DEBUG: New UVW means - U: {np.mean(uvw_data[:, 0]):.3f}, V: {np.mean(uvw_data[:, 1]):.3f} m")

                                    # Verify the correction worked
                                    corrected_uvw_stats = get_uvw_statistics(args.ms, n_sample=1000)
                                    corrected_max_offset = max(abs(corrected_uvw_stats['u_mean']), abs(corrected_uvw_stats['v_mean']))

                                    if corrected_max_offset < 10.0:  # Much stricter threshold after correction
                                        print(f"✓ UVW correction successful (max offset: {corrected_max_offset:.3f} m)")
                                        needs_rephasing = False  # No need for phaseshift
                                    else:
                                        print(f"⚠ UVW correction incomplete (max offset: {corrected_max_offset:.3f} m > 10 m)")
                                        print(f"  Falling back to phaseshift rephasing...")
                                        # Continue with normal rephasing

                                except Exception as uvw_correct_error:
                                    print(f"WARNING: Direct UVW correction failed: {uvw_correct_error}")
                                    print(f"  Falling back to phaseshift rephasing...")

                            if needs_rephasing:
                                print(f"DEBUG: Importing rephasing tasks...")
                                from casatasks import phaseshift as casa_phaseshift
                                from astropy.coordinates import Angle
                                import shutil
                                from dsa110_contimg.calibration.uvw_verification import (
                                    verify_uvw_transformation,
                                    get_phase_center_from_ms,
                                )
                                print(f"DEBUG: Imports complete, formatting phase center...")

                                try:
                                    # Capture old phase center for UVW verification
                                    old_phase_center = get_phase_center_from_ms(args.ms, field=0)
                                    new_phase_center = (ra_deg, dec_deg)
                                
                                # Format phase center string for CASA
                                ra_hms = Angle(ra_deg, unit='deg').to_string(
                                    unit='hourangle', sep='hms', precision=2, pad=True
                                ).replace(' ', '')
                                dec_dms = Angle(dec_deg, unit='deg').to_string(
                                    unit='deg', sep='dms', precision=2, alwayssign=True, pad=True
                                ).replace(' ', '')
                                phasecenter_str = f"J2000 {ra_hms} {dec_dms}"
                                print(f"DEBUG: Phase center string: {phasecenter_str}")
                                
                                # Create temporary MS for rephased data
                                ms_phased = args.ms.rstrip('/').rstrip('.ms') + '.phased.ms'
                                
                                # Clean up any existing temporary files
                                if os.path.exists(ms_phased):
                                    print(f"DEBUG: Removing existing phased MS: {ms_phased}")
                                    shutil.rmtree(ms_phased, ignore_errors=True)
                                
                                # Calculate phase shift magnitude to determine method
                                from astropy.coordinates import SkyCoord
                                from astropy import units as u
                                old_coord = SkyCoord(ra=old_phase_center[0]*u.deg, dec=old_phase_center[1]*u.deg, frame='icrs')
                                new_coord = SkyCoord(ra=new_phase_center[0]*u.deg, dec=new_phase_center[1]*u.deg, frame='icrs')
                                phase_shift_arcmin = old_coord.separation(new_coord).to(u.arcmin).value
                                
                                print(f"DEBUG: Phase shift magnitude: {phase_shift_arcmin:.1f} arcmin")
                                
                                # Try phaseshift first (preferred method)
                                print(f"DEBUG: Running phaseshift (this may take a while)...")
                                uv_transformation_valid = False
                                
                                try:
                                    casa_phaseshift(
                                        vis=args.ms,
                                        outputvis=ms_phased,
                                        phasecenter=phasecenter_str
                                    )
                                    print(f"DEBUG: phaseshift complete, verifying UVW transformation...")
                                    
                                    # Verify UVW transformation
                                    is_valid, error_msg = verify_uvw_transformation(
                                        args.ms,
                                        ms_phased,
                                        old_phase_center,
                                        new_phase_center,
                                        tolerance_meters=0.1 if phase_shift_arcmin < 30.0 else 1.0,
                                        min_change_meters=0.01 if phase_shift_arcmin < 30.0 else 0.1,
                                    )
                                    
                                    if is_valid:
                                        print(f"✓ UVW transformation verified: phaseshift correctly transformed UVW")
                                        uv_transformation_valid = True
                                    else:
                                        print(f"ERROR: UVW transformation verification failed: {error_msg}")
                                        print(f"ERROR: Cannot proceed - DATA is phased to wrong center")
                                        
                                except Exception as phaseshift_error:
                                    print(f"ERROR: phaseshift failed: {phaseshift_error}")
                                    print(f"ERROR: Cannot proceed - rephasing failed")
                                    uv_transformation_valid = False
                                
                                # CRITICAL: UVW transformation MUST succeed
                                # If UVW is wrong, DATA is phased to wrong center, so MODEL_DATA won't match
                                # This would cause calibration to fail regardless of MODEL_DATA calculation method
                                if not uv_transformation_valid:
                                    # Get error message safely (may not be defined if phaseshift raised exception)
                                    error_detail = error_msg if 'error_msg' in locals() else (
                                        "phaseshift raised exception before verification"
                                    )
                                    error_msg_final = (
                                        f"CRITICAL: UVW transformation verification failed. "
                                        f"DATA is phased to wrong center. Cannot proceed with calibration. "
                                        f"Original error: {error_detail}"
                                    )
                                    print(f"ERROR: {error_msg_final}")
                                    logger.error(error_msg_final)
                                    raise RuntimeError(
                                        "UVW transformation failed. Cannot calibrate MS with incorrect phase center. "
                                        "This may indicate a bug in phaseshift for large phase shifts, or incorrect "
                                        "MS phasing from conversion. Please check the MS phase center and re-run conversion "
                                        "or rephasing manually."
                                    )
                                
                                print(f"✓ UVW transformation verified - DATA is correctly phased")

                                # CRITICAL: Double-check UVW alignment after rephasing
                                # The verification above may have bugs, so verify the final UVW
                                try:
                                    final_uvw_stats = get_uvw_statistics(ms_phased, n_sample=1000)
                                    final_u_abs = abs(final_uvw_stats['u_mean'])
                                    final_v_abs = abs(final_uvw_stats['v_mean'])
                                    final_max_offset = max(final_u_abs, final_v_abs)

                                    if final_max_offset > 100.0:
                                        print(f"ERROR: UVW still misaligned after rephasing!")
                                        print(f"  Final U mean: {final_uvw_stats['u_mean']:.1f} m")
                                        print(f"  Final V mean: {final_uvw_stats['v_mean']:.1f} m")
                                        print(f"  Final max offset: {final_max_offset:.1f} m > 100 m threshold")
                                        # Don't raise error here - let the verification handle it
                                        # But log the issue clearly
                                    else:
                                        print(f"DEBUG: UVW correctly aligned after rephasing (max offset: {final_max_offset:.1f} m)")
                                except Exception as final_uvw_error:
                                    print(f"WARNING: Could not verify final UVW alignment: {final_uvw_error}")

                                print(f"DEBUG: Checking REFERENCE_DIR...")
                                
                                # CRITICAL: phaseshift may update PHASE_DIR but not REFERENCE_DIR
                                # CASA calibration tasks use REFERENCE_DIR, so we must ensure it's correct
                                # Manually update REFERENCE_DIR if phaseshift didn't update it
                                try:
                                    from casacore.tables import table as casa_table
                                    with casa_table(f"{ms_phased}::FIELD", readonly=False) as tf:
                                        if "REFERENCE_DIR" in tf.colnames() and "PHASE_DIR" in tf.colnames():
                                            ref_dir = tf.getcol("REFERENCE_DIR")[0][0]  # Shape: (2,)
                                            phase_dir = tf.getcol("PHASE_DIR")[0][0]  # Shape: (2,)
                                            
                                            # Check if REFERENCE_DIR matches PHASE_DIR (within tolerance)
                                            # Tolerance: 1 arcmin in radians ≈ 2.9e-5 rad
                                            if not np.allclose(ref_dir, phase_dir, atol=2.9e-5):
                                                print(f"DEBUG: REFERENCE_DIR not updated by phaseshift, updating manually...")
                                                print(f"  REFERENCE_DIR: RA={ref_dir[0]*180/np.pi:.6f}°, Dec={ref_dir[1]*180/np.pi:.6f}°")
                                                print(f"  PHASE_DIR:      RA={phase_dir[0]*180/np.pi:.6f}°, Dec={phase_dir[1]*180/np.pi:.6f}°")
                                                # Update REFERENCE_DIR to match PHASE_DIR
                                                # REFERENCE_DIR shape in table: (nrows, 1, 2)
                                                tf.putcol("REFERENCE_DIR", phase_dir.reshape(1, 1, 2))
                                                print(f"DEBUG: REFERENCE_DIR updated to match PHASE_DIR")
                                            else:
                                                print(f"DEBUG: REFERENCE_DIR already correct (matches PHASE_DIR)")
                                except Exception as refdir_error:
                                    print(f"WARNING: Could not verify/update REFERENCE_DIR: {refdir_error}")
                                    print(f"WARNING: Calibration may fail if REFERENCE_DIR is incorrect")
                                print(f"DEBUG: Rephasing complete, verifying phase center...")
                                
                                # Verify REFERENCE_DIR is correct after rephasing
                                try:
                                    from casacore.tables import table as casa_table
                                    with casa_table(f"{ms_phased}::FIELD", readonly=True) as tf:
                                        if "REFERENCE_DIR" in tf.colnames():
                                            ref_dir = tf.getcol("REFERENCE_DIR")[0][0]
                                            ref_ra_deg = ref_dir[0] * 180.0 / np.pi
                                            ref_dec_deg = ref_dir[1] * 180.0 / np.pi
                                            
                                            # Check separation from calibrator
                                            from astropy.coordinates import SkyCoord
                                            from astropy import units as u
                                            ms_coord = SkyCoord(ra=ref_ra_deg*u.deg, dec=ref_dec_deg*u.deg, frame='icrs')
                                            cal_coord = SkyCoord(ra=ra_deg*u.deg, dec=dec_deg*u.deg, frame='icrs')
                                            separation = ms_coord.separation(cal_coord)
                                            
                                            print(f"DEBUG: Final REFERENCE_DIR: RA={ref_ra_deg:.6f}°, Dec={ref_dec_deg:.6f}°")
                                            print(f"DEBUG: Separation from calibrator: {separation.to(u.arcmin):.4f}")
                                            
                                            if separation.to(u.arcmin).value > 1.0:
                                                print(f"WARNING: REFERENCE_DIR still offset by {separation.to(u.arcmin):.4f} - calibration may fail")
                                            else:
                                                print(f"✓ REFERENCE_DIR correctly aligned (separation < 1 arcmin)")
                                except Exception as verify_error:
                                    print(f"WARNING: Could not verify phase center: {verify_error}")
                                
                                # Replace original MS with rephased version
                                print(f"DEBUG: Replacing original MS with rephased version...")
                                shutil.rmtree(args.ms, ignore_errors=True)
                                shutil.move(ms_phased, args.ms)
                                print(f"✓ MS rephased to calibrator position")
                                
                            except ImportError:
                                # phaseshift not available - cannot rephase
                                error_msg_import = (
                                    f"phaseshift task not available. Cannot rephase MS to calibrator position. "
                                    f"Calibration cannot proceed without proper MS phasing."
                                )
                                logger.error(error_msg_import)
                                raise RuntimeError(error_msg_import)
                            except Exception as e:
                                # Rephasing failed - cannot proceed
                                error_msg_rephase = (
                                    f"Could not rephase MS to calibrator position: {e}. "
                                    f"Calibration cannot proceed without proper MS phasing. "
                                    f"Please check MS phase center and re-run conversion or rephasing manually."
                                )
                                logger.error(error_msg_rephase)
                                raise RuntimeError(error_msg_rephase)
                        
                        print(
                            (
                                "Writing catalog point model: {n} @ ("
                                "{ra:.4f},{de:.4f}) deg, {fl:.2f} Jy"
                            ).format(n=name, ra=ra_deg, de=dec_deg, fl=flux_jy)
                        )
                        print(f"DEBUG: Calling MODEL_DATA population (this may take a while)...")
                        # CRITICAL: Clear MODEL_DATA before writing, especially after rephasing
                        # Old MODEL_DATA may have been written for wrong phase center
                        try:
                            from casatasks import clearcal
                            clearcal(vis=args.ms, addmodel=True)
                            print(f"DEBUG: Cleared existing MODEL_DATA before writing new model")
                        except Exception as e:
                            logger.warning(f"Could not clear MODEL_DATA before writing: {e}")
                        
                        # Use manual calculation to populate MODEL_DATA
                        # CRITICAL FIX: ft() does NOT use correct phase center (REFERENCE_DIR/PHASE_DIR).
                        # We verified through empirical testing that ft() has ~101° phase scatter even
                        # when component is at phase center. This causes 80%+ bandpass solution flagging.
                        # The manual calculation explicitly uses REFERENCE_DIR and UVW to compute correct phases.
                        print(f"DEBUG: Using manual MODEL_DATA calculation (ft() is broken - see CASA_FUNCTION_BEHAVIOR_100_PERCENT_VERIFIED.md)...")
                        # Pass field parameter to ensure MODEL_DATA is written to the correct field
                        # Use field_sel (the calibrator field) for MODEL_DATA population
                        model_helpers.write_point_model_with_ft(
                            args.ms, float(ra_deg), float(dec_deg), float(flux_jy),
                            field=field_sel, use_manual=True)
                        print(f"DEBUG: write_point_model_with_ft completed")
                        
                        print(f"DEBUG: MODEL_DATA population completed")
                        # Rename field to calibrator name
                        try:
                            from casacore.tables import table
                            with table(f"{args.ms}::FIELD", readonly=False) as field_tb:
                                # Get current field names
                                field_names = field_tb.getcol("NAME")
                                # Rename field 0 (the calibrator field) to calibrator name
                                if len(field_names) > 0:
                                    field_names[0] = name
                                    field_tb.putcol("NAME", field_names)
                                    print(f"✓ Renamed field 0 to '{name}'")
                        except Exception as e:
                            logger.warning(f"Could not rename field to calibrator name: {e}")
                    else:
                        # PRECONDITION CHECK: If calibrator info is unavailable, we cannot populate MODEL_DATA
                        # This is a required precondition for calibration - fail fast rather than silently skip
                        if needs_model:
                            p.error(
                                "Catalog model requested (--model-source=catalog) but calibrator info "
                                "unavailable. This is required for MODEL_DATA population. "
                                "Ensure --auto-fields is used and a calibrator is found in the MS field of view."
                            )
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
                            "Running setjy on field {} (standard {})"
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
                        "Applying component list model: {}"
                        .format(args.model_component)
                    )
                    model_helpers.write_component_model_with_ft(
                        args.ms, args.model_component)
                elif args.model_source == "image":
                    if not args.model_image:
                        p.error("--model-source=image requires --model-image")
                    print(
                        "Applying image model: {}".format(args.model_image)
                    )
                    model_helpers.write_image_model_with_ft(
                        args.ms, args.model_image)
                elif args.model_source is None:
                    # No model source specified - this violates "measure twice, cut once"
                    # We require MODEL_DATA to be populated before calibration for consistent,
                    # reliable results across all calibrators (bright or faint).
                    # This ensures the calibration approach works generally, not just "sometimes"
                    # for bright sources.
                    if needs_model:
                        p.error(
                            "--model-source is REQUIRED for calibration (K, BP, or G). "
                            "This ensures consistent, reliable calibration results. "
                            "Use --model-source=setjy (for standard calibrators) or "
                            "--model-source=catalog (for catalog-based models)."
                        )
            except Exception as e:
                # PRECONDITION CHECK: MODEL_DATA population failure is a hard error
                # This ensures we follow "measure twice, cut once" - establish requirements upfront
                # before expensive calibration operations.
                p.error(
                    f"MODEL_DATA population failed: {e}. "
                    f"This is required for calibration. Fix the error and retry."
                )
        
        # PRECONDITION CHECK: Validate MODEL_DATA flux values are reasonable
        # This ensures we follow "measure twice, cut once" - verify MODEL_DATA quality
        # before proceeding with calibration.
        if needs_model and args.model_source is not None:
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

        # Flag autocorrelations before any solves unless disabled
        if not args.no_flagging and not getattr(args, 'no_flag_autocorr', False):
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
        if not args.skip_bp and bool(getattr(args, 'prebp_phase', False)):
            print(f"DEBUG: Starting pre-bandpass phase-only solve...")
            t_prebp0 = time.perf_counter()
            try:
                prebp_phase_table = solve_prebandpass_phase(
                    ms_in,
                    field_sel,
                    refant,
                    combine_fields=bool(args.bp_combine_field),
                    uvrange=str(getattr(args, 'prebp_uvrange', '') or ''),
                    solint=str(getattr(args, 'prebp_solint', 'inf') or 'inf'),
                    minsnr=float(getattr(args, 'prebp_minsnr', 5.0)),
                )
                elapsed_prebp = time.perf_counter() - t_prebp0
                print(f"DEBUG: Pre-bandpass phase solve completed in {elapsed_prebp:.2f}s")
                print("Pre-bandpass phase-only solve completed in {:.2f}s".format(elapsed_prebp))
            except Exception as e:
                print(f"WARNING: Pre-bandpass phase solve failed: {e}")
                print("Continuing with bandpass solve without pre-bandpass phase correction...")
                logger.warning(f"Pre-bandpass phase solve failed: {e}")
        
        bptabs = []
        if not args.skip_bp:
            print(f"DEBUG: Starting bandpass solve...")
            t_bp0 = time.perf_counter()
            # No implicit UV range cut; use CLI or env default if provided
            # NOTE: K-table is NOT passed to bandpass (K-calibration not used for DSA-110)
            import os as _os
            bp_uvrange = args.uvrange if args.uvrange else _os.getenv("CONTIMG_CAL_BP_UVRANGE", "")
            print(f"DEBUG: Calling solve_bandpass with uvrange='{bp_uvrange}', field={field_sel}, refant={refant}")
            if prebp_phase_table:
                print(f"DEBUG: Using pre-bandpass phase table: {prebp_phase_table}")
            print(f"DEBUG: This may take several minutes - bandpass solve is running...")
            bptabs = solve_bandpass(
                ms_in,
                field_sel,
                refant,
                None,  # K-table not used for DSA-110
                combine_fields=bool(args.bp_combine_field),
                combine_spw=args.combine_spw,
                uvrange=bp_uvrange,
                minsnr=float(args.bp_minsnr),
                prebandpass_phase_table=prebp_phase_table,  # Apply pre-bandpass phase correction
                bp_smooth_type=(getattr(args, 'bp_smooth_type', 'none') or 'none'),
                bp_smooth_window=(int(getattr(args, 'bp_smooth_window')) if getattr(args, 'bp_smooth_window', None) is not None else None),
            )
            elapsed_bp = time.perf_counter() - t_bp0
            print(f"DEBUG: Bandpass solve completed in {elapsed_bp:.2f}s")
            print("Bandpass solve completed in {:.2f}s".format(elapsed_bp))
            # Always report bandpass flagged fraction
            try:
                if bptabs:
                    from dsa110_contimg.qa.calibration_quality import validate_caltable_quality
                    _bp_metrics = validate_caltable_quality(bptabs[0])
                    print(
                        f"Bandpass flagged solutions: {_bp_metrics.fraction_flagged*100:.1f}%"
                    )
            except Exception as e:
                logger.warning(f"Could not compute bandpass flagged fraction: {e}")
        
        gtabs = []
        if not args.skip_g:
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
                combine_fields=bool(args.bp_combine_field),
                phase_only=phase_only,
                uvrange=(
                    (args.uvrange or "")
                    if args.fast
                    else ""
                ),
                solint=args.gain_solint,
                minsnr=float(getattr(args, 'gain_minsnr', 3.0)),
            )
            elapsed_g = time.perf_counter() - t_g0
            print("Gain solve completed in {:.2f}s".format(elapsed_g))

        tabs = (ktabs[:1] if ktabs else []) + bptabs + gtabs
        print("Generated tables:\n" + "\n".join(tabs))
        
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
        # Use direct table access instead of flag_summary() to avoid casaplotserver launch
        if mode != "summary":
            try:
                from casacore.tables import table
                import numpy as np
                
                with table(args.ms, readonly=True) as tb:
                    n_rows = tb.nrows()
                    if n_rows > 0:
                        # Sample a reasonable number of rows for performance
                        sample_size = min(10000, n_rows)
                        flags = tb.getcol("FLAG", startrow=0, nrow=sample_size)
                        total_points = flags.size
                        flagged_points = np.sum(flags)
                        flagged_pct = (flagged_points / total_points * 100) if total_points > 0 else 0.0
                        logger.info(f"\nFlagging complete. Total flagged: {flagged_pct:.2f}% (sampled {sample_size:,} rows)")
            except Exception as e:
                logger.debug(f"Could not compute flagging statistics: {e}")


if __name__ == "__main__":
    main()
