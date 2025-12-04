"""
CLI-compatible calibration runner for DSA-110.

This module provides the `run_calibrator` function that performs a full
calibration sequence (model → bandpass → gains) for a given MS.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
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
    from dsa110_contimg.calibration.flagging import flag_autocorrelations

    ms = str(ms_path)
    caltables: List[str] = []

    if table_prefix is None:
        # Use MS name + field as default prefix
        ms_name = os.path.splitext(os.path.basename(ms))[0]
        table_prefix = f"{os.path.dirname(ms)}/{ms_name}_{cal_field}"

    logger.info(f"Starting calibration for {ms}, field={cal_field}, refant={refant}")

    # Step 0: Pre-calibration flagging (optional)
    if do_flagging:
        try:
            logger.info("Flagging autocorrelations...")
            flag_autocorrelations(ms)
        except Exception as e:
            logger.warning(f"Pre-calibration flagging failed (continuing): {e}")

    # Step 1: Set model visibilities
    try:
        logger.info(f"Setting model visibilities for field {cal_field}...")
        populate_model_from_catalog(
            ms,
            field=cal_field,
            calibrator_name=calibrator_name,
        )
        logger.info("Model visibilities set successfully")
    except Exception as e:
        logger.error(f"Failed to set model visibilities: {e}")
        raise RuntimeError(f"Model setup failed: {e}") from e

    # Step 2: K (delay) calibration (optional, not typically used for DSA-110)
    ktable = None
    if do_k:
        try:
            logger.info("Solving delay (K) calibration...")
            ktables = solve_delay(
                ms,
                cal_field=cal_field,
                refant=refant,
                table_prefix=table_prefix,
            )
            if ktables:
                ktable = ktables[0]  # Primary K table
                caltables.extend(ktables)
                logger.info(f"K calibration complete: {ktable}")
        except Exception as e:
            logger.warning(f"K calibration failed (continuing without K): {e}")

    # Step 3: Bandpass calibration
    try:
        logger.info("Solving bandpass calibration...")
        bp_tables = solve_bandpass(
            ms,
            cal_field=cal_field,
            refant=refant,
            ktable=ktable,
            table_prefix=table_prefix,
            set_model=False,  # Model already set
        )
        caltables.extend(bp_tables)
        logger.info(f"Bandpass calibration complete: {bp_tables}")
    except Exception as e:
        logger.error(f"Bandpass calibration failed: {e}")
        raise RuntimeError(f"Bandpass solve failed: {e}") from e

    # Step 4: Time-dependent gains
    try:
        logger.info("Solving time-dependent gains...")
        gaintables = solve_gains(
            ms,
            cal_field=cal_field,
            refant=refant,
            bp_table=bp_tables[0] if bp_tables else None,
            k_table=ktable,
            table_prefix=table_prefix,
        )
        caltables.extend(gaintables)
        logger.info(f"Gain calibration complete: {gaintables}")
    except Exception as e:
        logger.error(f"Gain calibration failed: {e}")
        raise RuntimeError(f"Gain solve failed: {e}") from e

    logger.info(
        f"Calibration complete for {ms}: produced {len(caltables)} table(s)"
    )
    return caltables
