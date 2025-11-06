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
    reset_flags, flag_zeros, flag_rfi, flag_antenna, flag_baselines,
    flag_manual, flag_shadow, flag_quack, flag_elevation, flag_clip,
    flag_extend, flag_summary,
)
from .calibration import solve_delay, solve_bandpass, solve_gains, solve_prebandpass_phase
from .applycal import apply_to_target
from .selection import select_bandpass_fields, select_bandpass_from_catalog
# Note: Delay QA functions moved to qa.calibration_quality (imported inline where needed)
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
            prepare_temp_environment(os.getenv('CONTIMG_SCRATCH_DIR') or '/scratch/dsa110-contimg')
    except Exception:
        pass
    
    # Ensure scratch directory structure exists
    try:
        ensure_scratch_dirs()
    except Exception:
        pass  # Best-effort; continue if setup fails
    
    p = argparse.ArgumentParser(
        description="CASA 6.7 calibration runner (no dsacalib)")
    # Add common logging arguments
    add_common_logging_args(p)
    
    sub = p.add_subparsers(dest="cmd", required=True)

    # Add subcommand parsers from extracted modules
    add_calibrate_parser(sub)
    add_apply_parser(sub)
    add_flag_parser(sub)
    add_qa_parsers(sub)

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
    else:
        logger.error(f"Unknown command: {args.cmd}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
