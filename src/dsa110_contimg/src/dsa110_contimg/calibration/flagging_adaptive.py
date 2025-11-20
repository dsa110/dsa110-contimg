"""
Adaptive RFI flagging with automatic escalation.

This module provides intelligent flagging that automatically switches to
aggressive mode if calibration fails with default flagging.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CalibrationFailure(Exception):
    """Exception raised when calibration fails."""

    pass


def flag_rfi_adaptive(
    ms_path: str,
    refant: str = "103",
    calibrate_fn: Optional[callable] = None,
    calibrate_kwargs: Optional[dict] = None,
    aggressive_strategy: str = "/data/dsa110-contimg/config/dsa110-aggressive.lua",
    backend: str = "aoflagger",
) -> dict:
    """
    Adaptive RFI flagging with automatic escalation to aggressive mode.

    Strategy:
    1. Apply default flagging
    2. Attempt calibration (if calibrate_fn provided)
    3. If calibration fails, reset flags and retry with aggressive mode
    4. Return strategy used and success status

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    refant : str
        Reference antenna for calibration
    calibrate_fn : callable, optional
        Function to call for calibration. Should raise CalibrationFailure on error.
        If None, only flagging is performed (no adaptive behavior).
    calibrate_kwargs : dict, optional
        Additional kwargs to pass to calibrate_fn
    aggressive_strategy : str
        Path to aggressive AOFlagger strategy file
    backend : str
        Flagging backend ('aoflagger' or 'casa')

    Returns
    -------
    dict
        Results dictionary with keys:
        - 'strategy': "default" or "aggressive"
        - 'success': bool
        - 'attempts': int (1 or 2)
        - 'flagging_stats': dict of flag statistics

    Example
    -------
    >>> def my_calibrate(ms_path, refant, **kwargs):
    ...     # Your calibration logic
    ...     if calibration_fails:
    ...         raise CalibrationFailure("Convergence failed")
    ...
    >>> result = flag_rfi_adaptive(
    ...     "data.ms",
    ...     refant="103",
    ...     calibrate_fn=my_calibrate,
    ...     calibrate_kwargs={"field": "0"}
    ... )
    >>> print(f"Used {result['strategy']} strategy")
    """
    from dsa110_contimg.calibration.flagging import flag_rfi, reset_flags

    calibrate_kwargs = calibrate_kwargs or {}

    # Pass 1: Default flagging
    logger.info("=" * 70)
    logger.info("ADAPTIVE FLAGGING: Pass 1 - Default strategy")
    logger.info("=" * 70)

    flag_rfi(ms_path, backend=backend)
    stats_default = get_flag_summary(ms_path)

    logger.info(
        f"Default flagging complete: {stats_default['overall_flagged_fraction']*100:.2f}% flagged"
    )

    # If no calibration function provided, just return flagging results
    if calibrate_fn is None:
        return {
            "strategy": "default",
            "success": True,
            "attempts": 1,
            "flagging_stats": stats_default,
        }

    # Try calibration with default flagging
    try:
        logger.info("Attempting calibration with default flagging...")
        calibrate_fn(ms_path, refant=refant, **calibrate_kwargs)
        logger.info("✓ Calibration successful with default flagging")

        return {
            "strategy": "default",
            "success": True,
            "attempts": 1,
            "flagging_stats": stats_default,
        }

    except (CalibrationFailure, Exception) as e:
        logger.warning(f"Calibration failed with default flagging: {e}")
        logger.info("=" * 70)
        logger.info("ADAPTIVE FLAGGING: Pass 2 - Aggressive strategy")
        logger.info("=" * 70)

        # Pass 2: Reset flags and try aggressive flagging
        logger.info("Resetting flags for aggressive retry...")
        reset_flags(ms_path)

        # Re-flag zeros (should be done before RFI flagging)
        from dsa110_contimg.calibration.flagging import flag_zeros

        flag_zeros(ms_path)

        logger.info(f"Applying aggressive flagging strategy: {aggressive_strategy}")
        flag_rfi(ms_path, backend=backend, strategy=aggressive_strategy)
        stats_aggressive = get_flag_summary(ms_path)

        logger.info(
            f"Aggressive flagging complete: {stats_aggressive['overall_flagged_fraction']*100:.2f}% flagged"
        )

        # Retry calibration with aggressive flagging
        try:
            logger.info("Retrying calibration with aggressive flagging...")
            calibrate_fn(ms_path, refant=refant, **calibrate_kwargs)
            logger.info("✓ Calibration successful with aggressive flagging")

            return {
                "strategy": "aggressive",
                "success": True,
                "attempts": 2,
                "flagging_stats": stats_aggressive,
            }

        except (CalibrationFailure, Exception) as e2:
            logger.error(f"Calibration failed even with aggressive flagging: {e2}")

            return {
                "strategy": "aggressive",
                "success": False,
                "attempts": 2,
                "flagging_stats": stats_aggressive,
                "error": str(e2),
            }


def get_flag_summary(ms_path: str) -> dict:
    """
    Get flagging statistics summary.

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set

    Returns
    -------
    dict
        Statistics dictionary with keys:
        - 'overall_flagged_fraction': float
        - 'per_spw_flagging': dict[int, float]
        - 'fully_flagged_spws': list[int]
    """
    import numpy as np
    from casacore import tables

    tb = tables.table(ms_path, ack=False)
    flags = tb.getcol("FLAG")
    spw_ids = tb.getcol("DATA_DESC_ID")
    tb.close()

    # Overall statistics
    overall_frac = float(flags.mean())

    # Per-SPW statistics
    per_spw = {}
    fully_flagged = []

    for spw in sorted(set(spw_ids)):
        spw_mask = spw_ids == spw
        spw_flags = flags[spw_mask]
        spw_frac = float(spw_flags.mean())
        per_spw[int(spw)] = spw_frac

        if spw_frac > 0.99:  # >99% flagged = fully flagged
            fully_flagged.append(int(spw))

    return {
        "overall_flagged_fraction": overall_frac,
        "per_spw_flagging": per_spw,
        "fully_flagged_spws": fully_flagged,
    }
