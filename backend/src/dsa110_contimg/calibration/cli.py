"""
CLI-compatible calibration runner for DSA-110.

This module provides the `run_calibrator` function that performs a full
calibration sequence (model → bandpass → gains) for a given MS.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["run_calibrator"]


def _validate_model_data_populated(ms_path: str, field: str) -> None:
    """Validate that MODEL_DATA column is populated (not all zeros).

    This is a critical precondition check - bandpass calibration will fail
    silently or with confusing errors if MODEL_DATA is empty.

    Args:
        ms_path: Path to Measurement Set
        field: Field selection string (e.g., "0" or "11~13")

    Raises:
        RuntimeError: If MODEL_DATA is all zeros or doesn't exist
    """
    import casacore.tables as ct

    with ct.table(ms_path, readonly=True) as t:
        if "MODEL_DATA" not in t.colnames():
            raise RuntimeError(
                "MODEL_DATA column not found in MS. "
                "Model visibilities must be set before calibration."
            )

        # Parse field selection to get field indices
        if "~" in str(field):
            parts = str(field).split("~")
            field_indices = list(range(int(parts[0]), int(parts[1]) + 1))
        elif field.isdigit():
            field_indices = [int(field)]
        else:
            field_indices = None  # Use all

        # Read FIELD_ID to filter
        field_id = t.getcol("FIELD_ID")

        if field_indices is not None:
            mask = np.isin(field_id, field_indices)
            selected_rows = np.where(mask)[0]
            if len(selected_rows) == 0:
                raise RuntimeError(f"No rows found for field selection '{field}'")
            # Sample from selected rows
            sample_rows = selected_rows[:1000]
        else:
            sample_rows = list(range(min(1000, t.nrows())))

        # Read MODEL_DATA for sample rows
        model_sample = np.array([t.getcell("MODEL_DATA", int(r)) for r in sample_rows])
        max_amp = np.nanmax(np.abs(model_sample))

        if max_amp == 0:
            raise RuntimeError(
                f"MODEL_DATA is all zeros for field '{field}'. "
                "This will cause bandpass calibration to fail. "
                "Possible causes:\n"
                "  - Calibrator flux not found in catalog\n"
                "  - populate_model_from_catalog() failed silently\n"
                "  - Wrong field selection"
            )

        logger.info(
            "MODEL_DATA validation passed: max amplitude = %.3f Jy (field=%s)",
            max_amp, field
        )


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
        solve_delay,
        solve_gains,
    )
    from dsa110_contimg.calibration.model import populate_model_from_catalog

    ms_file = str(ms_path)
    caltables: List[str] = []

    if table_prefix is None:
        ms_name = os.path.splitext(os.path.basename(ms_file))[0]
        table_prefix = f"{os.path.dirname(ms_file)}/{ms_name}_{cal_field}"

    logger.info("Starting calibration for %s, field=%s, refant=%s", ms_file, cal_field, refant)

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

    # VALIDATION: Verify MODEL_DATA is actually populated (not all zeros)
    _validate_model_data_populated(ms_file, cal_field)

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

    logger.info("Calibration complete for %s: produced %d table(s)", ms_file, len(caltables))
    return caltables
