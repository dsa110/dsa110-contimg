"""
Calibration runner functions for DSA-110.

This module provides the core calibration functions used by the CLI
(dsa110_contimg.calibration.cli) and other modules.

Functions:
    run_calibrator: Full calibration sequence (phaseshift → model → bandpass → gains)
    phaseshift_ms: Unified phaseshift function (calibrator or median meridian mode)
    phaseshift_to_calibrator: Legacy wrapper for backward compatibility

**Critical**: DSA-110 data is initially phased to each field's meridian position.
For optimal results:
- **Calibrator MS**: Phaseshift to calibrator position (removes geometric phase gradient)
- **Science MS**: Phaseshift to median meridian position (minimizes phase offsets across 24 fields)
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["run_calibrator", "phaseshift_to_calibrator", "phaseshift_ms"]


def _compute_median_meridian_position(ms_path: str, field: str = "") -> tuple:
    """Compute the median meridian RA/Dec across all fields in the MS.

    For science observations with 24 drift-scan fields, each field has a slightly
    different meridian position due to time progression. This function computes
    the median position to minimize phase gradients when combining fields.

    Args:
        ms_path: Path to Measurement Set
        field: Field selection (default: "" for all fields)

    Returns:
        Tuple of (median_ra_deg, median_dec_deg)
    """
    import casacore.tables as ct
    from astropy.coordinates import SkyCoord
    import astropy.units as u

    with ct.table(ms_path + "::FIELD", readonly=True) as field_table:
        # Get phase centers for all fields
        phase_dir = field_table.getcol("PHASE_DIR")  # Shape: (nfields, 1, 2) in radians
        
        # Extract RA/Dec in radians, squeeze out middle dimension
        ra_rad = phase_dir[:, 0, 0]
        dec_rad = phase_dir[:, 0, 1]
        
        # Convert to degrees
        ra_deg = np.degrees(ra_rad)
        dec_deg = np.degrees(dec_rad)
        
        # Compute median (use circular mean for RA to handle 0/360 wrap)
        # For RA near 0/360 boundary, convert to complex representation
        ra_complex = np.exp(1j * ra_rad)
        median_ra_complex = np.median(ra_complex)
        median_ra_rad = np.angle(median_ra_complex)
        median_ra_deg = np.degrees(median_ra_rad)
        if median_ra_deg < 0:
            median_ra_deg += 360.0
        
        # Dec is linear, just use median
        median_dec_deg = np.median(dec_deg)
        
        logger.debug(
            "Computed median meridian position from %d fields: RA=%.4f, Dec=%.4f",
            len(ra_deg), median_ra_deg, median_dec_deg
        )
        
        return float(median_ra_deg), float(median_dec_deg)


def _get_calibrator_position(calibrator_name: str) -> tuple:
    """Get calibrator position from VLA catalog.

    Args:
        calibrator_name: Calibrator name (e.g., "0834+555")

    Returns:
        Tuple of (ra_deg, dec_deg)

    Raises:
        ValueError: If calibrator not found in catalog
    """
    import sqlite3
    from dsa110_contimg.calibration.catalogs import resolve_vla_catalog_path

    catalog_path = resolve_vla_catalog_path()

    # Query the SQLite database
    conn = sqlite3.connect(str(catalog_path))
    try:
        # Try various name formats
        name_variants = [
            calibrator_name,
            calibrator_name.upper(),
            calibrator_name.lower(),
            "J" + calibrator_name if not calibrator_name.startswith("J") else calibrator_name,
            calibrator_name[1:] if calibrator_name.startswith("J") else calibrator_name,
        ]

        for name in name_variants:
            cursor = conn.execute(
                "SELECT ra_deg, dec_deg FROM calibrators WHERE name = ? COLLATE NOCASE",
                (name,)
            )
            row = cursor.fetchone()
            if row:
                ra_deg, dec_deg = row
                logger.debug(
                    "Found calibrator %s: RA=%.4f, Dec=%.4f",
                    calibrator_name, ra_deg, dec_deg
                )
                return float(ra_deg), float(dec_deg)

        raise ValueError(f"Calibrator '{calibrator_name}' not found in VLA catalog at {catalog_path}")
    finally:
        conn.close()


def phaseshift_to_calibrator(
    ms_path: str,
    field: str,
    calibrator_name: str,
    output_ms: Optional[str] = None,
) -> tuple:
    """Phaseshift calibrator field(s) to the calibrator's true position.

    **DEPRECATED**: This function is a backward-compatibility wrapper.
    Use `phaseshift_ms(mode='calibrator')` instead.

    DSA-110 data is initially phased to each field's meridian position (RA=LST).
    For bandpass calibration, we need the calibrator to be at phase center so
    that all baselines see the same phase (for a point source).

    This function:
    1. Looks up the calibrator position from the VLA catalog
    2. Extracts the specified field(s) and phaseshifts to calibrator position
    3. Creates a new MS with the calibrator at phase center

    The output MS contains ONLY the selected field(s), which is appropriate
    for calibration. The calibration tables can then be applied to the
    original full MS.

    Args:
        ms_path: Path to input Measurement Set
        field: Field selection (e.g., "12" or "11~13")
        calibrator_name: Calibrator name for position lookup (e.g., "0834+555")
        output_ms: Path to output MS (default: input_ms + "_cal.ms")

    Returns:
        Tuple of (output_ms_path, phasecenter_string)
    """
    # Wrapper around unified phaseshift_ms function
    return phaseshift_ms(
        ms_path=ms_path,
        field=field,
        output_ms=output_ms,
        mode="calibrator",
        calibrator_name=calibrator_name,
    )


def phaseshift_ms(
    ms_path: str,
    field: str = "",
    output_ms: Optional[str] = None,
    mode: str = "median_meridian",
    calibrator_name: Optional[str] = None,
    target_ra_deg: Optional[float] = None,
    target_dec_deg: Optional[float] = None,
) -> tuple:
    """Unified phaseshift function for both calibrator and science MS.

    This function handles two main use cases:
    1. **Calibrator MS** (mode='calibrator'): Phaseshift to calibrator position
       for stable bandpass calibration (point source at phase center)
    2. **Science MS** (mode='median_meridian'): Phaseshift to median meridian position
       across all 24 fields to minimize phase gradients for imaging

    DSA-110 drift-scan observations create 24 fields over ~5 minutes, each with
    slightly different meridian RA. Phaseshifting to the median position minimizes
    the maximum phase offset across all fields.

    Args:
        ms_path: Path to input Measurement Set
        field: Field selection (e.g., "12", "0~23", or "" for all fields)
        output_ms: Path to output MS (default: auto-generated based on mode)
        mode: Phaseshift mode:
            - "median_meridian" (default): Compute median RA/Dec across fields
            - "calibrator": Use calibrator position from catalog
            - "manual": Use explicitly provided target_ra_deg/target_dec_deg
        calibrator_name: Calibrator name for mode='calibrator' (e.g., "0834+555")
        target_ra_deg: Manual target RA in degrees (mode='manual' only)
        target_dec_deg: Manual target Dec in degrees (mode='manual' only)

    Returns:
        Tuple of (output_ms_path, phasecenter_string)

    Raises:
        ValueError: If required parameters are missing for the selected mode

    Examples:
        >>> # Calibrator MS: phaseshift to 0834+555 position
        >>> phaseshift_ms("data.ms", field="12", mode="calibrator",
        ...               calibrator_name="0834+555")
        
        >>> # Science MS: phaseshift to median meridian of all 24 fields
        >>> phaseshift_ms("data.ms", field="", mode="median_meridian")
        
        >>> # Manual target position
        >>> phaseshift_ms("data.ms", mode="manual",
        ...               target_ra_deg=128.7287, target_dec_deg=55.5725)
    """
    from pathlib import Path
    from casatasks import phaseshift
    from astropy.coordinates import SkyCoord
    import astropy.units as u

    # Determine target position based on mode
    if mode == "calibrator":
        if not calibrator_name:
            raise ValueError("calibrator_name is required when mode='calibrator'")
        ra_deg, dec_deg = _get_calibrator_position(calibrator_name)
        mode_suffix = "cal"
        logger.info(
            "Phaseshift mode: calibrator '%s' at RA=%.4f, Dec=%.4f",
            calibrator_name, ra_deg, dec_deg
        )
    
    elif mode == "median_meridian":
        ra_deg, dec_deg = _compute_median_meridian_position(ms_path, field)
        mode_suffix = "meridian"
        logger.info(
            "Phaseshift mode: median meridian at RA=%.4f, Dec=%.4f",
            ra_deg, dec_deg
        )
    
    elif mode == "manual":
        if target_ra_deg is None or target_dec_deg is None:
            raise ValueError("target_ra_deg and target_dec_deg are required when mode='manual'")
        ra_deg, dec_deg = target_ra_deg, target_dec_deg
        mode_suffix = "manual"
        logger.info(
            "Phaseshift mode: manual target at RA=%.4f, Dec=%.4f",
            ra_deg, dec_deg
        )
    
    else:
        raise ValueError(
            f"Invalid mode '{mode}'. Must be 'calibrator', 'median_meridian', or 'manual'"
        )

    # Convert to CASA phasecenter format (J2000 HH:MM:SS.S +DD:MM:SS.S)
    coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
    ra_hms = coord.ra.to_string(unit=u.hour, sep="hms", precision=2)
    dec_dms = coord.dec.to_string(unit=u.deg, sep="dms", precision=1, alwayssign=True)
    phasecenter = f"J2000 {ra_hms} {dec_dms}"

    # Determine output path
    if output_ms is None:
        ms_stem = Path(ms_path).stem
        ms_dir = Path(ms_path).parent
        output_ms = str(ms_dir / f"{ms_stem}_{mode_suffix}.ms")

    # Remove existing output if present
    output_path = Path(output_ms)
    if output_path.exists():
        import shutil
        shutil.rmtree(output_path)
        logger.debug(f"Removed existing {output_ms}")

    logger.info(
        "Phaseshifting field '%s' to %s: %s",
        field if field else "all", mode, phasecenter
    )
    logger.info(f"Output MS: {output_ms}")

    # Run CASA phaseshift
    phaseshift(
        vis=ms_path,
        outputvis=output_ms,
        field=field,
        phasecenter=phasecenter,
        datacolumn="all",  # Shift all data columns
    )

    logger.info("✓ Phaseshift complete: %s", output_ms)
    return output_ms, phasecenter


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
    do_phaseshift: bool = True,
) -> List[str]:
    """Run full calibration sequence on a measurement set.

    This performs:
    1. Phaseshift calibrator field to calibrator position (critical for DSA-110!)
    2. Set model visibilities (now simple: calibrator at phase center)
    3. Optionally solve K (delay) calibration
    4. Solve bandpass
    5. Solve time-dependent gains

    **CRITICAL**: DSA-110 data is initially phased to each field's meridian.
    The phaseshift step is REQUIRED for bandpass calibration to work, because
    otherwise there's a large geometric phase gradient across baselines from
    the offset between the meridian and the calibrator position.

    Args:
        ms_path: Path to the measurement set
        cal_field: Field selection string for calibrator
        refant: Reference antenna (e.g., "3")
        do_flagging: Whether to run pre-calibration flagging
        do_k: Whether to perform K (delay) calibration
        table_prefix: Prefix for output calibration tables (default: ms_name_field)
        calibrator_name: Calibrator name for catalog lookup (e.g., "0834+555").
            REQUIRED for phaseshift and model setup.
        do_phaseshift: Whether to phaseshift to calibrator position (default: True).
            Set False only if data is already phased to calibrator.

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

            # RFI flagging with AOFlagger (critical for bandpass!)
            logger.info("Running AOFlagger RFI flagging...")
            try:
                from dsa110_contimg.calibration.flagging import flag_rfi

                flag_rfi(ms_file, backend="aoflagger")
                logger.info("✓ AOFlagger RFI flagging complete")
            except Exception as aoflagger_err:
                logger.warning(
                    "AOFlagger failed (%s), falling back to CASA tfcrop+rflag",
                    aoflagger_err
                )
                # Fallback to CASA flagging
                flagdata(
                    vis=ms_file,
                    mode="tfcrop",
                    datacolumn="data",
                    timecutoff=4.0,
                    freqcutoff=4.0,
                    extendflags=False,
                    flagbackup=False,
                )
                flagdata(
                    vis=ms_file,
                    mode="rflag",
                    datacolumn="data",
                    timedevscale=4.0,
                    freqdevscale=4.0,
                    extendflags=False,
                    flagbackup=False,
                )
                logger.info("✓ CASA tfcrop+rflag flagging complete")
        except Exception as err:
            logger.warning("Pre-calibration flagging failed (continuing): %s", err)

    # Step 1: Phaseshift to calibrator position (CRITICAL for DSA-110!)
    # This removes the geometric phase gradient from the offset between
    # the meridian phase center and the calibrator's actual position.
    # Creates a NEW MS with only the calibrator field, phaseshifted.
    cal_ms = ms_file  # Default: use original MS
    cal_field_for_solve = cal_field  # Field selection for solving

    if do_phaseshift:
        if calibrator_name is None:
            raise ValueError(
                "calibrator_name is required for phaseshift. "
                "Provide the calibrator name (e.g., '0834+555') to look up its position."
            )
        try:
            cal_ms, phasecenter = phaseshift_to_calibrator(
                ms_file, cal_field, calibrator_name
            )
            # The phaseshifted MS has only one field (index 0)
            cal_field_for_solve = "0"
            logger.info(
                f"Using phaseshifted MS for calibration: {cal_ms} "
                f"(field {cal_field} -> field 0)"
            )
        except Exception as err:
            logger.error("Phaseshift failed: %s", err)
            raise RuntimeError(f"Phaseshift to calibrator failed: {err}") from err

    # Step 2: Set model visibilities on the calibration MS
    # After phaseshift, calibrator is at phase center, so MODEL_DATA is simple:
    # constant amplitude (= catalog flux), zero phase for all baselines.
    logger.info("Setting model visibilities for field %s on %s...", cal_field_for_solve, cal_ms)
    try:
        populate_model_from_catalog(
            cal_ms,
            field=cal_field_for_solve,
            calibrator_name=calibrator_name,
        )
        logger.info("Model visibilities set successfully")
    except Exception as err:
        logger.error("Failed to set model visibilities: %s", err)
        raise RuntimeError(f"Model setup failed: {err}") from err

    # VALIDATION: Verify MODEL_DATA is actually populated (not all zeros)
    _validate_model_data_populated(cal_ms, cal_field_for_solve)

    # Step 3: K (delay) calibration (optional, not typically used for DSA-110)
    ktable = None
    if do_k:
        logger.info("Solving delay (K) calibration...")
        try:
            ktables = solve_delay(
                cal_ms,
                cal_field=cal_field_for_solve,
                refant=refant,
                table_prefix=table_prefix,
            )
            if ktables:
                ktable = ktables[0]
                caltables.extend(ktables)
                logger.info("K calibration complete: %s", ktable)
        except Exception as err:
            logger.warning("K calibration failed (continuing without K): %s", err)

    # Step 4: Bandpass calibration
    logger.info("Solving bandpass calibration...")
    try:
        bp_tables = solve_bandpass(
            cal_ms,
            cal_field=cal_field_for_solve,
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

    # Step 5: Time-dependent gains
    logger.info("Solving time-dependent gains...")
    try:
        gaintables = solve_gains(
            cal_ms,
            cal_field=cal_field_for_solve,
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
