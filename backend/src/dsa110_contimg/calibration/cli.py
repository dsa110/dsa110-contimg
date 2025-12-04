"""
CLI-compatible calibration runner for DSA-110.

This module provides the `run_calibrator` function that performs a full
calibration sequence (model → bandpass → gains) for a given MS.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

__all__ = ["run_calibrator"]


def run_calibrator(
    ms_path: str,
    cal_field: str,
    refant: str,
    do_flagging: bool = True,
    do_k: bool = False,
    table_prefix: Optional[str] = None,
    calibrator_name: Optional[str] = None,
) -> List[str]:
    """Run full calibration sequence on a measurement set.

    This performs:
    1. Set model visibilities using catalog lookup (manual phase calculation)
    2. Optionally solve K (delay) calibration
    3. Solve bandpass
    4. Solve time-dependent gains

    Args:
        ms_path: Path to the measurement set
        cal_field: Field selection string for calibrator
        refant: Reference antenna (e.g., "3")
        do_flagging: Whether to run pre-calibration flagging
        do_k: Whether to perform K (delay) calibration
        table_prefix: Prefix for output calibration tables (default: ms_name_field)
        calibrator_name: Calibrator name for catalog lookup (e.g., "0834+555")

    Returns:
        List of calibration table paths created
    """
    from dsa110_contimg.calibration.calibration import (
        solve_bandpass,
        solve_gains,
        solve_delay,
    )
    from dsa110_contimg.calibration.model import populate_model_from_catalog

    ms_file = str(ms_path)
    caltables: List[str] = []

    if table_prefix is None:
        ms_name = os.path.splitext(os.path.basename(ms_file))[0]
        table_prefix = f"{os.path.dirname(ms_file)}/{ms_name}_{cal_field}"

    logger.info(
        "Starting calibration for %s, field=%s, refant=%s",
        ms_file, cal_field, refant
    )

    # Step 0: Pre-calibration flagging (optional)
    if do_flagging:
        try:
            from casatasks import flagdata
            logger.info("Flagging autocorrelations...")
            flagdata(vis=ms_file, autocorr=True, flagbackup=False)
        except Exception as err:
            logger.warning("Pre-calibration flagging failed (continuing): %s", err)

    # Step 1: Set model visibilities
    logger.info("Setting model visibilities for field %s...", cal_field)
    try:
        populate_model_from_catalog(
            ms_file,
            field=cal_field,
            calibrator_name=calibrator_name,
        )
        logger.info("Model visibilities set successfully")
    except Exception as err:
        logger.error("Failed to set model visibilities: %s", err)
        raise RuntimeError(f"Model setup failed: {err}") from err

    # Step 2: K (delay) calibration (optional, not typically used for DSA-110)
    ktable = None
    if do_k:
        logger.info("Solving delay (K) calibration...")
        try:
            ktables = solve_delay(
                ms_file,
                cal_field=cal_field,
                refant=refant,
                table_prefix=table_prefix,
            )
            if ktables:
                ktable = ktables[0]
                caltables.extend(ktables)
                logger.info("K calibration complete: %s", ktable)
        except Exception as err:
            logger.warning("K calibration failed (continuing without K): %s", err)

    # Step 3: Bandpass calibration
    logger.info("Solving bandpass calibration...")
    try:
        bp_tables = solve_bandpass(
            ms_file,
            cal_field=cal_field,
            refant=refant,
            ktable=ktable,
            table_prefix=table_prefix,
            set_model=False,  # Model already set
        )
        caltables.extend(bp_tables)
        logger.info("Bandpass calibration complete: %s", bp_tables)
    except Exception as err:
        logger.error("Bandpass calibration failed: %s", err)
        raise RuntimeError(f"Bandpass solve failed: {err}") from err

    # Step 4: Time-dependent gains
    logger.info("Solving time-dependent gains...")
    try:
        gaintables = solve_gains(
            ms_file,
            cal_field=cal_field,
            refant=refant,
            ktable=ktable,
            bptables=bp_tables,
            table_prefix=table_prefix,
        )
        caltables.extend(gaintables)
        logger.info("Gain calibration complete: %s", gaintables)
    except Exception as err:
        logger.error("Gain calibration failed: %s", err)
        raise RuntimeError(f"Gain solve failed: {err}") from err

    logger.info(
        "Calibration complete for %s: produced %d table(s)",
        ms_file, len(caltables)
    )
    return caltables
