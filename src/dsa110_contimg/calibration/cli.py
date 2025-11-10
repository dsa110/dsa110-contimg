import argparse
import os
import sys
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional

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
    ensure_scratch_dirs,
)
from dsa110_contimg.utils.validation import (
    validate_ms_for_calibration,
    validate_corrected_data_quality,
    ValidationError,
)

# Note: CASA environment setup moved to main() to avoid import-time side effects
# CASA imports deferred until needed

from .flagging import (
    reset_flags,
    flag_zeros,
    flag_rfi,
    flag_antenna,
    flag_baselines,
    flag_manual,
    flag_shadow,
    flag_quack,
    flag_elevation,
    flag_clip,
    flag_extend,
    flag_summary,
)
from .calibration import (
    solve_delay,
    solve_bandpass,
    solve_gains,
    solve_prebandpass_phase,
)
from .applycal import apply_to_target
from .selection import select_bandpass_fields, select_bandpass_from_catalog

# Note: Delay QA functions moved to qa.calibration_quality (imported inline where needed)
from .diagnostics import generate_calibration_diagnostics, compare_calibration_tables

try:
    # Ensure casacore temp files go to scratch, not the repo root
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore


def run_calibrator(
    ms: str,
    cal_field: str,
    refant: str,
    *,
    do_flagging: bool = True,
    do_k: bool = False,
) -> List[str]:
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


# Helper functions moved to cli_utils.py
from .cli_utils import (
    rephase_ms_to_calibrator as _rephase_ms_to_calibrator,
    clear_all_calibration_artifacts as _clear_all_calibration_artifacts,
)

# Subcommand handlers extracted to separate modules
from .cli_calibrate import add_calibrate_parser, handle_calibrate
from .cli_apply import add_apply_parser, handle_apply
from .cli_flag import add_flag_parser, handle_flag
from .cli_qa import (
    add_qa_parsers,
    handle_check_delays,
    handle_verify_delays,
    handle_inspect_delays,
    handle_list_transits,
    handle_validate,
    handle_compare,
)


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
            prepare_temp_environment(
                os.getenv("CONTIMG_SCRATCH_DIR") or "/stage/dsa110-contimg"
            )
    except Exception:
        pass

    # Ensure scratch directory structure exists
    try:
        ensure_scratch_dirs()
    except Exception:
        pass  # Best-effort; continue if setup fails

    p = argparse.ArgumentParser(description="CASA 6.7 calibration runner")
    # Add common logging arguments
    add_common_logging_args(p)

    sub = p.add_subparsers(dest="cmd", required=True)

    # Add subcommand parsers from extracted modules
    add_calibrate_parser(sub)
    add_apply_parser(sub)
    add_flag_parser(sub)
    add_qa_parsers(sub)

    # Add find-calibrators-in-ms subcommand
    find_cal_parser = sub.add_parser(
        "find-calibrators-in-ms",
        help="Find VLA calibrators in a directory of MS files",
        description=(
            "Scan a directory for MS files and return the VLA calibrators\n"
            "contained within those MS files.\n\n"
            "Example:\n"
            "  python -m dsa110_contimg.calibration.cli find-calibrators-in-ms \\\n"
            "    --ms-dir /data/ms \\\n"
            "    --radius-deg 1.5 \\\n"
            "    --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    find_cal_parser.add_argument(
        "--ms-dir",
        required=True,
        help="Directory containing MS files to scan",
    )
    find_cal_parser.add_argument(
        "--radius-deg",
        type=float,
        default=1.5,
        help="Search radius in degrees for calibrator matching (default: 1.5)",
    )
    find_cal_parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Maximum number of calibrators to return per MS (default: 5)",
    )
    find_cal_parser.add_argument(
        "--catalog",
        help="Path to VLA catalog (uses default if not provided)",
    )
    find_cal_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    find_cal_parser.add_argument(
        "--no-recursive",
        action="store_false",
        dest="recursive",
        default=True,
        help="Do not recursively search subdirectories",
    )
    find_cal_parser.add_argument(
        "--transit-window-minutes",
        type=float,
        default=None,
        help=(
            "Time window in minutes around transit for peak transit selection. "
            "Only MS files within ±window/2 minutes of transit are considered. "
            "If not specified, all MS files are considered (default: None)"
        ),
    )

    args = p.parse_args()

    # Configure logging using shared utility
    logger = configure_logging_from_args(args)

    # Route to appropriate handler
    if args.cmd == "calibrate":
        return handle_calibrate(args)
    elif args.cmd == "apply":
        return handle_apply(args)
    elif args.cmd == "flag":
        return handle_flag(args)
    elif args.cmd == "check-delays":
        return handle_check_delays(args)
    elif args.cmd == "verify-delays":
        return handle_verify_delays(args)
    elif args.cmd == "inspect-delays":
        return handle_inspect_delays(args)
    elif args.cmd == "list-transits":
        return handle_list_transits(args)
    elif args.cmd == "validate":
        return handle_validate(args)
    elif args.cmd == "compare":
        return handle_compare(args)
    elif args.cmd == "find-calibrators-in-ms":
        return handle_find_calibrators_in_ms(args, logger)
    else:
        logger.error(f"Unknown command: {args.cmd}")
        return 1


def handle_find_calibrators_in_ms(
    args: argparse.Namespace, logger: logging.Logger
) -> int:
    """Handle the find-calibrators-in-ms subcommand."""
    from dsa110_contimg.calibration.catalogs import (
        load_vla_catalog,
    )
    from dsa110_contimg.pointing.utils import load_pointing
    from dsa110_contimg.calibration.schedule import next_transit_time, DSA110_LOCATION
    from astropy.time import Time
    import astropy.units as u

    ms_dir = Path(args.ms_dir)
    if not ms_dir.exists() or not ms_dir.is_dir():
        logger.error(f"MS directory does not exist or is not a directory: {ms_dir}")
        return 1

    # Find all MS files in the directory
    logger.info(f"Scanning {ms_dir} for MS files...")
    ms_files = []
    if args.recursive:
        patterns = ["**/*.ms"]
    else:
        patterns = ["*.ms"]

    for pattern in patterns:
        for ms_path in ms_dir.glob(pattern):
            if ms_path.is_dir():
                ms_files.append(ms_path)

    if not ms_files:
        logger.warning(f"No MS files found in {ms_dir}")
        return 1

    logger.info(f"Found {len(ms_files)} MS file(s)")

    # Load VLA catalog
    try:
        if args.catalog:
            catalog_path = Path(args.catalog)
            if catalog_path.suffix == ".sqlite3":
                from dsa110_contimg.calibration.catalogs import (
                    load_vla_catalog_from_sqlite,
                )

                df = load_vla_catalog_from_sqlite(str(catalog_path))
            else:
                from dsa110_contimg.calibration.catalogs import (
                    read_vla_calibrator_catalog,
                )

                df = read_vla_calibrator_catalog(str(catalog_path))
        else:
            df = load_vla_catalog()
        logger.info(f"Loaded VLA catalog with {len(df)} calibrators")
    except Exception as e:
        logger.error(f"Failed to load VLA catalog: {e}")
        return 1

    # Collect calibrators from all MS files
    all_calibrators: Dict[str, Dict] = {}  # name -> calibrator info
    ms_calibrator_map: Dict[str, List[str]] = {}  # ms_path -> list of calibrator names
    ms_times: Dict[str, float] = {}  # ms_path -> mid_mjd

    for ms_path in ms_files:
        try:
            # Get pointing information from MS
            pointing_info = load_pointing(ms_path)
            if pointing_info is None or "dec_deg" not in pointing_info:
                logger.warning(f"Could not read pointing from {ms_path}, skipping")
                continue

            pt_dec = pointing_info["dec_deg"] * u.deg

            # Get observation time using standardized utility function
            # This uses the authoritative TIME column from the MS file
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(str(ms_path))

            if mid_mjd is None:
                logger.warning(f"Could not extract time from MS {ms_path}, skipping")
                continue

            # CRITICAL VALIDATION: Check if filename timestamp (if present) matches TIME column
            # This detects data quality issues where MS files have incorrect TIME values
            match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", ms_path.name)
            if match:
                try:
                    filename_timestamp = Time(
                        match.group(1), format="isot", scale="utc"
                    )
                    filename_mjd = filename_timestamp.mjd
                    time_mjd = Time(mid_mjd, format="mjd")
                    time_diff_hours = abs(
                        (time_mjd - filename_timestamp).to(u.hour).value
                    )

                    # If difference is more than 30 minutes, this indicates a serious data quality issue
                    if time_diff_hours > 0.5:
                        error_msg = (
                            f"DATA QUALITY ERROR: MS file {ms_path.name} has inconsistent time information. "
                            f"TIME column indicates {time_mjd.isot}, but filename suggests {filename_timestamp.isot} "
                            f"(difference: {time_diff_hours:.2f} hours). "
                            f"The TIME column is the authoritative source in MS files, and this inconsistency "
                            f"indicates the MS file was created incorrectly. "
                            f"This must be fixed at the data creation/processing stage, not worked around."
                        )
                        logger.error(error_msg)
                        # Continue processing but log the error - don't silently work around it
                except Exception as e:
                    logger.debug(
                        f"Could not validate filename timestamp for {ms_path.name}: {e}"
                    )

            ms_times[str(ms_path)] = mid_mjd

            # Find calibrator matches by declination (not by meridian RA)
            # This finds calibrators that are in the primary beam based on pointing,
            # regardless of whether they're transiting at the observation time
            import numpy as np

            dec_meridian = float(pt_dec.to_value(u.deg))
            # Match by declination within radius
            dec_match = df[
                (df["dec_deg"] >= dec_meridian - args.radius_deg)
                & (df["dec_deg"] <= dec_meridian + args.radius_deg)
            ].copy()

            if dec_match.empty:
                matches = []
            else:
                # Calculate separation and weighted flux for matching calibrators
                sep = np.abs(dec_match["dec_deg"] - dec_meridian)
                dec_match["sep_deg"] = sep

                # Calculate weighted flux if available
                if "flux_20_cm" in dec_match.columns:
                    from dsa110_contimg.calibration.catalogs import (
                        airy_primary_beam_response,
                    )

                    # Use meridian RA at observation time for PB calculation
                    t = Time(
                        mid_mjd, format="mjd", scale="utc", location=DSA110_LOCATION
                    )
                    ra_meridian = t.sidereal_time("apparent").to_value(u.deg)

                    w = []
                    for _, r in dec_match.iterrows():
                        resp = airy_primary_beam_response(
                            np.deg2rad(ra_meridian),
                            np.deg2rad(dec_meridian),
                            np.deg2rad(r["ra_deg"]),
                            np.deg2rad(r["dec_deg"]),
                            1.4,
                        )
                        w.append(resp * float(r["flux_20_cm"]) / 1e3)
                    dec_match["weighted_flux"] = w
                    dec_match = dec_match.sort_values(
                        ["weighted_flux", "sep_deg"], ascending=[False, True]
                    )
                else:
                    dec_match = dec_match.sort_values(["sep_deg"], ascending=[True])

                # Convert to match format
                matches = []
                for name, r in dec_match.head(args.top_n).iterrows():
                    matches.append(
                        {
                            "name": name if isinstance(name, str) else str(name),
                            "ra_deg": float(r["ra_deg"]),
                            "dec_deg": float(r["dec_deg"]),
                            "sep_deg": float(r["sep_deg"]),
                            "weighted_flux": float(r.get("weighted_flux", np.nan)),
                        }
                    )

            if matches:
                ms_calibrator_map[str(ms_path)] = []
                for match in matches:
                    cal_name = match["name"]
                    ms_calibrator_map[str(ms_path)].append(cal_name)

                    # Store calibrator info (keep first/best match if duplicate)
                    if cal_name not in all_calibrators:
                        all_calibrators[cal_name] = {
                            "name": cal_name,
                            "ra_deg": match["ra_deg"],
                            "dec_deg": match["dec_deg"],
                            "sep_deg": match.get("sep_deg", 0.0),
                            "weighted_flux": match.get("weighted_flux", 0.0),
                            "ms_files": [],
                        }

                    # Add this MS to the calibrator's MS list
                    if str(ms_path) not in all_calibrators[cal_name]["ms_files"]:
                        all_calibrators[cal_name]["ms_files"].append(str(ms_path))

        except Exception as e:
            logger.warning(f"Error processing {ms_path}: {e}")
            continue

    # For each calibrator, find the MS file closest to peak transit
    for cal_name, cal_info in all_calibrators.items():
        cal_ra_deg = cal_info["ra_deg"]
        peak_ms = None
        min_delta_minutes = None

        # Calculate transit time for this calibrator
        # Use the earliest MS time as reference
        if ms_times:
            earliest_mjd = min(ms_times.values())
            transit_time = next_transit_time(cal_ra_deg, earliest_mjd)

            # Find MS file with observation time closest to transit
            # Optionally filter by time window if specified
            window_half_minutes = None
            if args.transit_window_minutes is not None:
                window_half_minutes = args.transit_window_minutes / 2.0

            for ms_path_str in cal_info["ms_files"]:
                if ms_path_str in ms_times:
                    obs_mjd = ms_times[ms_path_str]
                    delta_minutes = abs(
                        (Time(obs_mjd, format="mjd") - transit_time).to(u.min).value
                    )

                    # Skip if outside time window (if window is specified)
                    if (
                        window_half_minutes is not None
                        and delta_minutes > window_half_minutes
                    ):
                        continue

                    if min_delta_minutes is None or delta_minutes < min_delta_minutes:
                        min_delta_minutes = delta_minutes
                        peak_ms = ms_path_str

            cal_info["peak_transit_ms"] = peak_ms
            cal_info["transit_time_iso"] = transit_time.isot
            cal_info["delta_from_transit_minutes"] = (
                min_delta_minutes if min_delta_minutes is not None else None
            )
            if window_half_minutes is not None:
                cal_info["transit_window_minutes"] = args.transit_window_minutes

    # Prepare output
    results = {
        "total_ms_files": len(ms_files),
        "ms_files_processed": len(ms_calibrator_map),
        "unique_calibrators": len(all_calibrators),
        "calibrators": list(all_calibrators.values()),
        "ms_calibrator_map": ms_calibrator_map,
    }

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        logger.info(
            f"\nFound {len(all_calibrators)} unique VLA calibrator(s) in {len(ms_calibrator_map)} MS file(s):\n"
        )
        for cal_name, cal_info in sorted(all_calibrators.items()):
            logger.info(f"  {cal_name}")
            logger.info(
                f"    RA: {cal_info['ra_deg']:.4f}°, Dec: {cal_info['dec_deg']:.4f}°"
            )
            if cal_info.get("weighted_flux", 0) > 0:
                logger.info(f"    Weighted flux: {cal_info['weighted_flux']:.2f} Jy")
            logger.info(f"    Found in {len(cal_info['ms_files'])} MS file(s)")
            if cal_info.get("peak_transit_ms"):
                logger.info(f"    Peak transit MS: {cal_info['peak_transit_ms']}")
                if cal_info.get("transit_time_iso"):
                    logger.info(f"    Transit time: {cal_info['transit_time_iso']}")
                if cal_info.get("delta_from_transit_minutes") is not None:
                    logger.info(
                        f"    Time from transit: {cal_info['delta_from_transit_minutes']:.1f} minutes"
                    )
            logger.info("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
