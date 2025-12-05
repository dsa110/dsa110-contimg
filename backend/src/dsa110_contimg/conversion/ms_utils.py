"""Shared utilities to configure Measurement Sets for imaging.

This module centralizes robust, repeatable post-write MS preparation:
- Ensure imaging columns exist (MODEL_DATA, CORRECTED_DATA)
- Populate imaging columns for every row with array values matching DATA
- Ensure FLAG and WEIGHT_SPECTRUM arrays are present and correctly shaped
- Initialize weights, including WEIGHT_SPECTRUM, via casatasks.initweights
- Normalize ANTENNA.MOUNT to CASA-compatible values

All callers should prefer `configure_ms_for_imaging()` rather than duplicating
these steps inline in scripts. This provides a single source of truth for MS
readiness across the pipeline.
"""

from __future__ import annotations

import os
from typing import Optional

from dsa110_contimg.utils.runtime_safeguards import require_casa6_python


def _ensure_imaging_columns_exist(ms_path: str) -> None:
    """Add MODEL_DATA and CORRECTED_DATA columns if missing.

    Raises:
        RuntimeError: If column creation fails and columns don't already exist
    """
    import logging

    logger = logging.getLogger(__name__)

    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path

    ensure_casa_path()

    try:
        import casacore.tables as _casatables
        from casacore.tables import addImagingColumns as _addImCols  # type: ignore

        _tb = _casatables.table

        # Check if columns already exist before attempting creation
        with _tb(ms_path, readonly=True) as tb:
            colnames = set(tb.colnames())
            has_model = "MODEL_DATA" in colnames
            has_corrected = "CORRECTED_DATA" in colnames

            if has_model and has_corrected:
                logger.debug(f"Imaging columns already exist in {ms_path}")
                return

        # Attempt to create columns
        _addImCols(ms_path)
        logger.debug(f"Created imaging columns in {ms_path}")

        # Verify columns were actually created
        with _tb(ms_path, readonly=True) as tb:
            colnames = set(tb.colnames())
            if "MODEL_DATA" not in colnames or "CORRECTED_DATA" not in colnames:
                missing = []
                if "MODEL_DATA" not in colnames:
                    missing.append("MODEL_DATA")
                if "CORRECTED_DATA" not in colnames:
                    missing.append("CORRECTED_DATA")
                raise RuntimeError(
                    f"addImagingColumns() succeeded but columns still missing: {missing}"
                )

    except ImportError as e:
        error_msg = f"Failed to import casacore.tables.addImagingColumns: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        # Check if columns exist despite the error (might have been created)
        try:
            import casacore.tables as _casatables

            _tb = _casatables.table

            with _tb(ms_path, readonly=True) as tb:
                colnames = set(tb.colnames())
                has_model = "MODEL_DATA" in colnames
                has_corrected = "CORRECTED_DATA" in colnames

                if has_model and has_corrected:
                    logger.warning(
                        f"addImagingColumns() raised exception but columns exist: {e}. "
                        "Continuing with existing columns."
                    )
                    return
        except (RuntimeError, OSError):
            # RuntimeError: CASA table errors, OSError: file access issues
            pass

        # Columns don't exist - this is a critical failure
        error_msg = f"Failed to create imaging columns in {ms_path}: {e}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e


def _ensure_imaging_columns_populated(ms_path: str) -> None:
    """
    Ensure MODEL_DATA and CORRECTED_DATA contain array values for every
    row, with shapes/dtypes matching the DATA column cells.

    This function uses vectorized operations for performance (~50x faster
    than row-by-row iteration on large MS files). It checks if columns need
    initialization by sampling rows, then uses bulk putcol operations.

    Raises:
        RuntimeError: If columns exist but cannot be populated
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        import casacore.tables as _casatables  # type: ignore
        import numpy as _np

        _tb = _casatables.table
    except ImportError as e:
        error_msg = f"Failed to import required modules for column population: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

    try:
        with _tb(ms_path, readonly=False) as tb:
            nrow = tb.nrows()
            if nrow == 0:
                logger.warning(f"MS {ms_path} has no rows - cannot populate columns")
                return

            colnames = set(tb.colnames())
            if "MODEL_DATA" not in colnames or "CORRECTED_DATA" not in colnames:
                missing = []
                if "MODEL_DATA" not in colnames:
                    missing.append("MODEL_DATA")
                if "CORRECTED_DATA" not in colnames:
                    missing.append("CORRECTED_DATA")
                raise RuntimeError(f"Cannot populate columns - they don't exist: {missing}")

            # Get DATA shape and dtype from first row
            try:
                data0 = tb.getcell("DATA", 0)
                data_shape = getattr(data0, "shape", None)
                data_dtype = getattr(data0, "dtype", None)
                if not data_shape or data_dtype is None:
                    raise RuntimeError("Cannot determine DATA column shape/dtype")
            except Exception as e:
                error_msg = f"Failed to read DATA column from {ms_path}: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

            # Populate each column using vectorized operations
            for col in ("MODEL_DATA", "CORRECTED_DATA"):
                if col not in tb.colnames():
                    continue

                # Quick check: sample first, middle, and last rows to determine
                # if the column needs initialization. This catches the common cases:
                # 1. All rows properly initialized (no work needed)
                # 2. All rows need initialization (bulk write)
                # 3. Mixed state (fall back to row-by-row for safety)
                needs_init = False
                has_valid_data = False
                sample_indices = [0, nrow // 2, nrow - 1] if nrow > 2 else list(range(nrow))

                for idx in sample_indices:
                    try:
                        val = tb.getcell(col, idx)
                        if val is None or getattr(val, "shape", None) != data_shape:
                            needs_init = True
                        elif _np.any(val != 0):
                            # Column has non-zero data - it's been populated
                            has_valid_data = True
                    except (RuntimeError, KeyError, IndexError):
                        # RuntimeError: CASA errors, KeyError: missing col, IndexError: bad row
                        needs_init = True

                # If column already has valid non-zero data, skip initialization
                if has_valid_data and not needs_init:
                    logger.debug(f"Column {col} already populated in {ms_path}")
                    continue

                # If all sampled rows need initialization, use fast bulk write
                if needs_init:
                    try:
                        # Use vectorized putcol for ~50x speedup over row-by-row
                        # Process in chunks to manage memory for very large MS files
                        chunk_size = 100000  # ~100k rows per chunk
                        fixed = 0

                        for start_row in range(0, nrow, chunk_size):
                            end_row = min(start_row + chunk_size, nrow)
                            chunk_nrow = end_row - start_row

                            # Create zero array for this chunk
                            # Shape is (nrow, nfreq, npol) for casacore putcol
                            zeros = _np.zeros((chunk_nrow,) + data_shape, dtype=data_dtype)
                            tb.putcol(col, zeros, startrow=start_row, nrow=chunk_nrow)
                            fixed += chunk_nrow

                        logger.debug(f"Bulk-populated {fixed} rows in {col} column for {ms_path}")

                    except Exception as bulk_err:
                        # Fall back to row-by-row if bulk operation fails
                        logger.warning(
                            f"Bulk population failed for {col}, falling back to "
                            f"row-by-row: {bulk_err}"
                        )
                        fixed, errors = _populate_column_row_by_row(
                            tb, col, nrow, data_shape, data_dtype, logger, ms_path
                        )
                        if fixed > 0:
                            logger.debug(
                                f"Row-by-row populated {fixed} rows in {col} for {ms_path}"
                            )

    except RuntimeError:
        # Re-raise RuntimeError (our own errors)
        raise
    except Exception as e:
        error_msg = f"Failed to populate imaging columns in {ms_path}: {e}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e


def _populate_column_row_by_row(
    tb, col: str, nrow: int, data_shape: tuple, data_dtype, logger, ms_path: str
) -> tuple:
    """
    Fallback row-by-row population for columns with mixed initialization states.

    This preserves the original behavior for edge cases where bulk operations
    might overwrite valid data.

    Returns:
        tuple: (fixed_count, error_count)
    """
    import numpy as _np

    fixed = 0
    errors = 0
    error_examples = []

    for r in range(nrow):
        try:
            val = tb.getcell(col, r)
            if (val is None) or (getattr(val, "shape", None) != data_shape):
                tb.putcell(col, r, _np.zeros(data_shape, dtype=data_dtype))
                fixed += 1
        except (RuntimeError, KeyError, IndexError):
            try:
                tb.putcell(col, r, _np.zeros(data_shape, dtype=data_dtype))
                fixed += 1
            except (RuntimeError, OSError) as e2:
                errors += 1
                if len(error_examples) < 5:
                    error_examples.append(f"row {r}: {e2}")

    if errors > 0:
        error_summary = (
            f"Failed to populate {errors} out of {nrow} rows in {col} column for {ms_path}"
        )
        if error_examples:
            error_summary += f". Examples: {'; '.join(error_examples)}"
        logger.warning(error_summary)

    return fixed, errors


def _ensure_flag_and_weight_spectrum(ms_path: str) -> None:
    """
    Ensure FLAG and WEIGHT_SPECTRUM cells exist with correct shapes for all rows.

    - FLAG: boolean array shaped like DATA; fill with False when undefined
    - WEIGHT_SPECTRUM: float array shaped like DATA; when undefined,
      repeat WEIGHT across channels; if WEIGHT_SPECTRUM appears
      inconsistent across rows, drop the column to let CASA fall back
      to WEIGHT.
    """
    try:
        import casacore.tables as _casatables  # type: ignore
        import numpy as _np

        _tb = _casatables.table
    except ImportError:
        return

    try:
        with _tb(ms_path, readonly=False) as tb:
            nrow = tb.nrows()
            colnames = set(tb.colnames())
            has_ws = "WEIGHT_SPECTRUM" in colnames
            ws_bad = False
            for i in range(nrow):
                try:
                    data = tb.getcell("DATA", i)
                except (RuntimeError, KeyError, IndexError):
                    # RuntimeError: CASA errors, KeyError: missing col, IndexError: bad row
                    continue
                target_shape = getattr(data, "shape", None)
                if not target_shape or len(target_shape) != 2:
                    continue
                nchan, npol = int(target_shape[0]), int(target_shape[1])
                # FLAG
                try:
                    f = tb.getcell("FLAG", i)
                    if f is None or getattr(f, "shape", None) != (nchan, npol):
                        raise RuntimeError("FLAG shape mismatch")
                except (RuntimeError, KeyError, IndexError):
                    tb.putcell("FLAG", i, _np.zeros((nchan, npol), dtype=bool))
                # WEIGHT_SPECTRUM
                if has_ws:
                    try:
                        ws_val = tb.getcell("WEIGHT_SPECTRUM", i)
                        if ws_val is None or getattr(ws_val, "shape", None) != (
                            nchan,
                            npol,
                        ):
                            raise RuntimeError("WS shape mismatch")
                    except (RuntimeError, KeyError, IndexError):
                        try:
                            w = tb.getcell("WEIGHT", i)
                            w = _np.asarray(w).reshape(-1)
                            if w.size != npol:
                                w = _np.ones((npol,), dtype=float)
                        except (RuntimeError, KeyError, IndexError):
                            w = _np.ones((npol,), dtype=float)
                        ws = _np.repeat(w[_np.newaxis, :], nchan, axis=0)
                        tb.putcell("WEIGHT_SPECTRUM", i, ws)
                        ws_bad = True
            if has_ws and ws_bad:
                try:
                    tb.removecols(["WEIGHT_SPECTRUM"])
                except (RuntimeError, OSError):
                    # RuntimeError: CASA errors, OSError: file issues
                    pass
    except (RuntimeError, OSError, ImportError):
        # RuntimeError: CASA errors, OSError: file issues, ImportError: casacore
        return


@require_casa6_python
def _initialize_weights(ms_path: str) -> None:
    """Initialize WEIGHT_SPECTRUM via casatasks.initweights.

    NOTE: CASA's initweights does NOT have doweight or doflag parameters.
    When wtmode='weight', it initializes WEIGHT_SPECTRUM from the existing WEIGHT column.
    """
    try:
        try:
            from dsa110_contimg.utils.tempdirs import casa_log_environment

            with casa_log_environment():
                from casatasks import initweights as _initweights  # type: ignore
        except ImportError:
            from casatasks import initweights as _initweights  # type: ignore

        # NOTE: When wtmode='weight', initweights initializes WEIGHT_SPECTRUM from WEIGHT column
        # dowtsp=True creates/updates WEIGHT_SPECTRUM column
        _initweights(vis=ms_path, wtmode="weight", dowtsp=True)
    except (RuntimeError, OSError):
        # Non-fatal: initweights can fail on edge cases; downstream tools may
        # still work. RuntimeError: CASA errors, OSError: file issues
        pass


def _fix_mount_type_in_ms(ms_path: str) -> None:
    """Normalize ANTENNA.MOUNT values to CASA-supported strings."""
    try:
        import casacore.tables as _casatables  # type: ignore

        _tb = _casatables.table

        with _tb(ms_path + "/ANTENNA", readonly=False) as ant_table:
            mounts = ant_table.getcol("MOUNT")
            fixed = []
            for m in mounts:
                normalized = str(m or "").lower().strip()
                if normalized in (
                    "alt-az",
                    "altaz",
                    "alt_az",
                    "alt az",
                    "az-el",
                    "azel",
                ):
                    fixed.append("alt-az")
                elif normalized in ("equatorial", "eq"):
                    fixed.append("equatorial")
                elif normalized in ("x-y", "xy"):
                    fixed.append("x-y")
                elif normalized in ("spherical", "sphere"):
                    fixed.append("spherical")
                else:
                    fixed.append("alt-az")
            ant_table.putcol("MOUNT", fixed)
    except (RuntimeError, OSError, ImportError):
        # Non-fatal normalization
        # RuntimeError: CASA errors, OSError: file issues, ImportError: casacore
        pass


def _fix_field_phase_centers_from_times(ms_path: str) -> None:
    """Fix FIELD table PHASE_DIR/REFERENCE_DIR with correct time-dependent RA values.

    This function corrects a bug where pyuvdata.write_ms() may assign incorrect RA
    values to fields when using time-dependent phase centers. For meridian-tracking
    phasing (RA = LST), each field should have RA corresponding to LST at that field's
    time, not a single midpoint RA.

    The function:
    1. Reads the main table to determine which times correspond to which FIELD_ID
    2. For each field, calculates the correct RA = LST(time) at that field's time
    3. Updates PHASE_DIR and REFERENCE_DIR in the FIELD table with correct values

    Args:
        ms_path: Path to Measurement Set
    """
    try:
        import astropy.units as u  # type: ignore
        import casacore.tables as _casatables  # type: ignore
        import numpy as _np

        _tb = _casatables.table

        from dsa110_contimg.conversion.helpers_coordinates import get_meridian_coords
    except ImportError:
        # Non-fatal: if dependencies aren't available, skip this fix
        return

    try:
        # Read main table to get FIELD_ID and TIME mapping
        with _tb(ms_path, readonly=True, ack=False) as main_table:
            if main_table.nrows() == 0:
                return

            field_ids = main_table.getcol("FIELD_ID")
            times = main_table.getcol("TIME")  # CASA TIME is in seconds since MJD epoch

            # Get unique field IDs and their corresponding times
            unique_field_ids = _np.unique(field_ids)
            field_times = {}
            for fid in unique_field_ids:
                mask = field_ids == fid
                field_times[int(fid)] = _np.mean(times[mask])  # Use mean time for the field

        # Read FIELD table
        with _tb(ms_path + "::FIELD", readonly=False) as field_table:
            nfields = field_table.nrows()
            if nfields == 0:
                return

            # Get current PHASE_DIR and REFERENCE_DIR
            has_phase_dir = "PHASE_DIR" in field_table.colnames()
            has_ref_dir = "REFERENCE_DIR" in field_table.colnames()

            if not has_phase_dir and not has_ref_dir:
                return  # Can't fix if neither column exists

            phase_dir = field_table.getcol("PHASE_DIR") if has_phase_dir else None
            ref_dir = field_table.getcol("REFERENCE_DIR") if has_ref_dir else None

            # Get pointing declination from first field (should be constant)
            if phase_dir is not None:
                pt_dec_rad = phase_dir[0, 0, 1]  # Dec from first field
            elif ref_dir is not None:
                pt_dec_rad = ref_dir[0, 0, 1]
            else:
                return

            pt_dec = pt_dec_rad * u.rad

            # Note: get_meridian_coords() uses DSA-110 coordinates internally,
            # so no explicit telescope location lookup is needed here.

            # Fix each field's phase center
            updated = False
            # Import time conversion utilities for proper format detection
            from dsa110_contimg.utils.time_utils import detect_casa_time_format

            for field_idx in range(nfields):
                # Get time for this field (CASA TIME format varies: seconds since MJD 0 or MJD 51544.0)
                if field_idx in field_times:
                    time_sec = field_times[field_idx]
                    # Use format detection to handle both TIME formats correctly
                    # This is critical: pyuvdata.write_ms() uses seconds since MJD 0,
                    # but standard CASA uses seconds since MJD 51544.0
                    _, time_mjd = detect_casa_time_format(time_sec)
                else:
                    # Fallback: use mean time from main table with format detection
                    mean_time_sec = _np.mean(times)
                    _, time_mjd = detect_casa_time_format(mean_time_sec)

                # Calculate correct RA = LST(time) at meridian
                phase_ra, phase_dec = get_meridian_coords(pt_dec, time_mjd)
                ra_rad = float(phase_ra.to_value(u.rad))
                dec_rad = float(phase_dec.to_value(u.rad))

                # Update PHASE_DIR if it exists
                if has_phase_dir:
                    current_ra = phase_dir[field_idx, 0, 0]
                    current_dec = phase_dir[field_idx, 0, 1]
                    # Only update if significantly different (more than 1 arcsec)
                    ra_diff_rad = abs(ra_rad - current_ra)
                    dec_diff_rad = abs(dec_rad - current_dec)
                    if ra_diff_rad > _np.deg2rad(1.0 / 3600.0) or dec_diff_rad > _np.deg2rad(
                        1.0 / 3600.0
                    ):
                        phase_dir[field_idx, 0, 0] = ra_rad
                        phase_dir[field_idx, 0, 1] = dec_rad
                        updated = True

                # Update REFERENCE_DIR if it exists
                if has_ref_dir:
                    current_ra = ref_dir[field_idx, 0, 0]
                    current_dec = ref_dir[field_idx, 0, 1]
                    # Only update if significantly different (more than 1 arcsec)
                    ra_diff_rad = abs(ra_rad - current_ra)
                    dec_diff_rad = abs(dec_rad - current_dec)
                    if ra_diff_rad > _np.deg2rad(1.0 / 3600.0) or dec_diff_rad > _np.deg2rad(
                        1.0 / 3600.0
                    ):
                        ref_dir[field_idx, 0, 0] = ra_rad
                        ref_dir[field_idx, 0, 1] = dec_rad
                        updated = True

            # Write back updated values
            if updated:
                if has_phase_dir:
                    field_table.putcol("PHASE_DIR", phase_dir)
                if has_ref_dir:
                    field_table.putcol("REFERENCE_DIR", ref_dir)
    except (RuntimeError, OSError, ValueError, KeyError):
        # Non-fatal: if fixing fails, log warning but don't crash
        # RuntimeError: CASA errors, OSError: file issues,
        # ValueError: time conversion, KeyError: missing columns
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Could not fix FIELD table phase centers (non-fatal)", exc_info=True)


def _ensure_observation_table_valid(ms_path: str) -> None:
    """
    Ensure OBSERVATION table exists and has at least one valid row.

    This fixes MS files where the OBSERVATION table is empty or malformed,
    which causes CASA msmetadata to fail with "Observation ID -1 out of range".

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    """
    try:
        import casacore.tables as _casatables
        import numpy as _np

        _tb = _casatables.table
    except ImportError:
        return

    try:
        with _tb(f"{ms_path}::OBSERVATION", readonly=False) as obs_tb:
            # If table is empty, create a default observation row
            if obs_tb.nrows() == 0:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"OBSERVATION table is empty in {ms_path}, creating default row")

                # Get telescope name from environment or use default
                telescope_name = os.getenv("PIPELINE_TELESCOPE_NAME", "DSA_110")

                # Create a default observation row
                # CASA requires specific columns - use minimal valid values
                default_values = {
                    "TIME_RANGE": _np.array([0.0, 0.0], dtype=_np.float64),
                    "LOG": "",
                    "SCHEDULE": "",
                    "FLAG_ROW": False,
                    "OBSERVER": "",
                    "PROJECT": "",
                    "RELEASE_DATE": 0.0,
                    "SCHEDULE_TYPE": "",
                    "TELESCOPE_NAME": telescope_name,
                }

                # Add row with default values
                obs_tb.addrows(1)
                for col, val in default_values.items():
                    if col in obs_tb.colnames():
                        obs_tb.putcell(col, 0, val)

                logger.info(f"Created default OBSERVATION row in {ms_path}")

    except (RuntimeError, OSError, KeyError):
        # Non-fatal: best-effort fix only
        # RuntimeError: CASA errors, OSError: file issues, KeyError: missing columns
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Could not ensure OBSERVATION table validity (non-fatal)", exc_info=True)


def _fix_observation_id_column(ms_path: str) -> None:
    """
    Ensure OBSERVATION_ID column in main table has valid values (>= 0).

    This fixes MS files where OBSERVATION_ID values are negative or invalid,
    which causes CASA msmetadata to fail.

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    """
    try:
        import casacore.tables as _casatables
        import numpy as _np

        _tb = _casatables.table
    except ImportError:
        return

    try:
        with _tb(ms_path, readonly=False) as main_tb:
            if "OBSERVATION_ID" not in main_tb.colnames():
                return

            obs_ids = main_tb.getcol("OBSERVATION_ID")
            if obs_ids is None or len(obs_ids) == 0:
                return

            # Check if any values are negative
            negative_mask = obs_ids < 0
            if _np.any(negative_mask):
                import logging

                logger = logging.getLogger(__name__)
                n_negative = _np.sum(negative_mask)
                logger.warning(
                    f"Found {n_negative} rows with negative OBSERVATION_ID in {ms_path}, fixing"
                )

                # Fix negative values to 0
                fixed_ids = obs_ids.copy()
                fixed_ids[negative_mask] = 0
                main_tb.putcol("OBSERVATION_ID", fixed_ids)

                logger.info(f"Fixed {n_negative} negative OBSERVATION_ID values in {ms_path}")

    except (RuntimeError, OSError, KeyError):
        # Non-fatal: best-effort fix only
        # RuntimeError: CASA errors, OSError: file issues, KeyError: missing columns
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Could not fix OBSERVATION_ID column (non-fatal)", exc_info=True)


def _fix_observation_time_range(ms_path: str) -> None:
    """
    Fix OBSERVATION table TIME_RANGE by reading from main table TIME column.

    This corrects MS files where OBSERVATION table TIME_RANGE is [0, 0] or invalid.
    The TIME column in the main table is the authoritative source.

    Uses the same format detection logic as extract_ms_time_range() to handle
    both TIME formats (seconds since MJD 0 vs seconds since MJD 51544.0).

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    """
    try:
        import casacore.tables as _casatables
        import numpy as _np

        _tb = _casatables.table

        from dsa110_contimg.utils.time_utils import (
            DEFAULT_YEAR_RANGE,
            detect_casa_time_format,
            validate_time_mjd,
        )
    except ImportError:
        return

    try:
        # First ensure OBSERVATION table exists and has at least one row
        _ensure_observation_table_valid(ms_path)

        # Read TIME column from main table (authoritative source)
        with _tb(ms_path, readonly=True) as main_tb:
            if "TIME" not in main_tb.colnames() or main_tb.nrows() == 0:
                return

            times = main_tb.getcol("TIME")
            if len(times) == 0:
                return

            t0_sec = float(_np.min(times))
            t1_sec = float(_np.max(times))

        # Detect correct format using the same logic as extract_ms_time_range()
        # This handles both formats: seconds since MJD 0 vs seconds since MJD 51544.0
        _, start_mjd = detect_casa_time_format(t0_sec, DEFAULT_YEAR_RANGE)
        _, end_mjd = detect_casa_time_format(t1_sec, DEFAULT_YEAR_RANGE)

        # Validate using astropy
        if not (
            validate_time_mjd(start_mjd, DEFAULT_YEAR_RANGE)
            and validate_time_mjd(end_mjd, DEFAULT_YEAR_RANGE)
        ):
            # Invalid dates, skip update
            return

        # OBSERVATION table TIME_RANGE should be in the same format as the main table TIME
        # (seconds, not MJD days). Use the raw seconds values directly.
        # Shape should be [2] (start, end), not [1, 2]
        time_range_sec = _np.array([t0_sec, t1_sec], dtype=_np.float64)

        # Update OBSERVATION table
        with _tb(f"{ms_path}::OBSERVATION", readonly=False) as obs_tb:
            if obs_tb.nrows() == 0:
                # Should not happen after _ensure_observation_table_valid, but handle gracefully
                return

            if "TIME_RANGE" not in obs_tb.colnames():
                return

            # Check if TIME_RANGE is invalid (all zeros or very small)
            existing_tr = obs_tb.getcol("TIME_RANGE")
            if existing_tr is not None and len(existing_tr) > 0:
                # Handle both shapes: (2, 1) and (2,)
                if existing_tr.shape[0] >= 2:
                    # Shape is (2, 1) or (2, N) - access as [row][col]
                    existing_t0 = float(_np.asarray(existing_tr[0]).flat[0])
                    existing_t1 = float(_np.asarray(existing_tr[1]).flat[0])
                else:
                    # Shape is (2,) - flat array
                    existing_t0 = float(_np.asarray(existing_tr).flat[0])
                    existing_t1 = (
                        float(_np.asarray(existing_tr).flat[1])
                        if len(existing_tr) > 1
                        else existing_t0
                    )

                # Only update if TIME_RANGE is invalid (zero or very small)
                if existing_t0 > 1.0 and existing_t1 > existing_t0:
                    # TIME_RANGE is already valid, don't overwrite
                    return

            # Update TIME_RANGE for all observation rows
            for row in range(obs_tb.nrows()):
                obs_tb.putcell("TIME_RANGE", row, time_range_sec)

        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            f"Fixed OBSERVATION table TIME_RANGE for {ms_path}: "
            f"{t0_sec:.1f} to {t1_sec:.1f} seconds "
            f"({start_mjd:.8f} to {end_mjd:.8f} MJD)"
        )
    except (RuntimeError, OSError, KeyError, ValueError):
        # Non-fatal: best-effort fix only
        # RuntimeError: CASA errors, OSError: file issues,
        # KeyError: missing columns, ValueError: time conversion
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("Could not fix OBSERVATION table TIME_RANGE (non-fatal)", exc_info=True)


@require_casa6_python
def configure_ms_for_imaging(
    ms_path: str,
    *,
    ensure_columns: bool = True,
    ensure_flag_and_weight: bool = True,
    do_initweights: bool = True,
    fix_mount: bool = True,
    stamp_observation_telescope: bool = True,
    validate_columns: bool = True,
    rename_calibrator_fields: bool = True,
    catalog_path: Optional[str] = None,
) -> None:
    """
    Make a Measurement Set safe and ready for imaging and calibration.

    This function performs essential post-conversion setup to ensure an MS is
    ready for downstream processing (calibration, imaging). It uses consistent
    error handling: critical failures raise exceptions, while non-critical issues
    log warnings and continue.

    **What this function does:**

    1. **Ensures imaging columns exist**: Creates MODEL_DATA and CORRECTED_DATA
       columns if missing, and populates them with properly-shaped arrays
    2. **Ensures flag/weight arrays**: Creates FLAG and WEIGHT_SPECTRUM arrays
       with correct shapes matching the DATA column
    3. **Initializes weights**: Runs CASA's initweights task to set proper
       weight values based on data quality
    4. **Fixes antenna mount types**: Normalizes ANTENNA.MOUNT values to
       CASA-compatible format
    5. **Stamps telescope identity**: Sets consistent telescope name and location
    6. **Fixes phase centers**: Updates FIELD table phase centers based on
       observation times
    7. **Fixes observation time range**: Updates OBSERVATION table with correct
       time range

    Parameters
    ----------
    ms_path : str
        Path to the Measurement Set (directory path).
    ensure_columns : bool, optional
        Ensure MODEL_DATA and CORRECTED_DATA columns exist and are populated.
        Default: True
    ensure_flag_and_weight : bool, optional
        Ensure FLAG and WEIGHT_SPECTRUM arrays exist and are well-shaped.
        Default: True
    do_initweights : bool, optional
        Run casatasks.initweights with WEIGHT_SPECTRUM initialization enabled.
        Default: True
    fix_mount : bool, optional
        Normalize ANTENNA.MOUNT values to CASA-compatible format.
        Default: True
    stamp_observation_telescope : bool, optional
        Set consistent telescope name and location metadata.
        Default: True
    validate_columns : bool, optional
        Validate that columns exist and contain data after creation.
        Set to False for high-throughput scenarios where validation overhead
        is unacceptable. Default: True
    rename_calibrator_fields : bool, optional
        Auto-detect and rename fields containing known calibrators.
        Uses VLA calibrator catalog to identify which field contains a calibrator,
        then renames it from 'meridian_icrs_t{i}' to '{calibrator}_t{i}'.
        Recommended for drift-scan observations. Default: True
    catalog_path : str, optional
        Path to VLA calibrator catalog (SQLite or CSV).
        If None, uses automatic resolution (prefers SQLite).
        Only used if rename_calibrator_fields=True. Default: None
        is a concern. Default: True

    Raises
    ------
    ConversionError
        If MS path does not exist, is not readable, or becomes unreadable
        after configuration (critical failures)

    Examples
    --------
    Basic usage after converting UVH5 to MS:

    >>> from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
    >>> configure_ms_for_imaging("/path/to/observation.ms")

    Configure only essential columns (skip weight initialization):

    >>> configure_ms_for_imaging(
    ...     "/path/to/observation.ms",
    ...     do_initweights=False
    ... )

    Minimal configuration (only columns and flags):

    >>> configure_ms_for_imaging(
    ...     "/path/to/observation.ms",
    ...     do_initweights=False,
    ...     fix_mount=False,
    ...     stamp_observation_telescope=False
    ... )

    Notes
    -----
    - This function should be called after converting UVH5 to MS format
    - All operations are idempotent (safe to call multiple times)
    - Non-critical failures (e.g., column population issues) are logged as
      warnings but don't stop execution
    - Critical failures (e.g., MS not found) raise ConversionError with
      context and suggestions
    """
    if not isinstance(ms_path, str):
        ms_path = os.fspath(ms_path)

    # CRITICAL: Validate MS exists and is readable
    from dsa110_contimg.utils.exceptions import ConversionError

    if not os.path.exists(ms_path):
        raise ConversionError(
            f"MS does not exist: {ms_path}",
            context={"ms_path": ms_path, "operation": "configure_ms_for_imaging"},
            suggestion="Check that the MS path is correct and the file exists",
        )
    if not os.path.isdir(ms_path):
        raise ConversionError(
            f"MS path is not a directory: {ms_path}",
            context={"ms_path": ms_path, "operation": "configure_ms_for_imaging"},
            suggestion="Measurement Sets are directories, not files. Check the path.",
        )
    if not os.access(ms_path, os.R_OK):
        raise ConversionError(
            f"MS is not readable: {ms_path}",
            context={"ms_path": ms_path, "operation": "configure_ms_for_imaging"},
            suggestion="Check file permissions: ls -ld " + ms_path,
        )

    # Initialize logger early for use in error handling
    import logging

    logger = logging.getLogger(__name__)

    # Track which operations succeeded for summary logging
    operations_status = {
        "columns": "skipped",
        "flag_weight": "skipped",
        "initweights": "skipped",
        "mount_fix": "skipped",
        "telescope_stamp": "skipped",
        "field_phase_centers": "skipped",
        "observation_time_range": "skipped",
    }

    if ensure_columns:
        try:
            _ensure_imaging_columns_exist(ms_path)
            _ensure_imaging_columns_populated(ms_path)

            # CRITICAL: Validate columns actually exist and are populated (if enabled)
            if validate_columns:
                import casacore.tables as _casatables

                _tb = _casatables.table

                with _tb(ms_path, readonly=True) as tb:
                    colnames = set(tb.colnames())
                    missing = []
                    if "MODEL_DATA" not in colnames:
                        missing.append("MODEL_DATA")
                    if "CORRECTED_DATA" not in colnames:
                        missing.append("CORRECTED_DATA")

                    if missing:
                        error_msg = (
                            f"CRITICAL: Required imaging columns missing after creation: {missing}. "
                            f"MS {ms_path} is not ready for calibration/imaging."
                        )
                        logger.error(error_msg)
                        raise ConversionError(
                            error_msg,
                            context={"ms_path": ms_path, "missing_columns": missing},
                            suggestion="Check MS file permissions and disk space. "
                            "Try recreating the MS if the issue persists.",
                        )

                    # Verify columns have data (at least one row)
                    if tb.nrows() > 0:
                        try:
                            model_sample = tb.getcell("MODEL_DATA", 0)
                            corrected_sample = tb.getcell("CORRECTED_DATA", 0)
                            if model_sample is None or corrected_sample is None:
                                logger.warning(
                                    f"Imaging columns exist but contain None values in {ms_path}"
                                )
                        except Exception as e:
                            logger.warning(f"Could not verify column data in {ms_path}: {e}")
                    logger.info(f":check_mark: Imaging columns verified in {ms_path}")
            else:
                logger.debug(f"Imaging columns created (validation skipped) in {ms_path}")

            operations_status["columns"] = "success"
        except ConversionError:
            # Re-raise ConversionError (critical failures)
            raise
        except Exception as e:
            operations_status["columns"] = f"failed: {e}"
            error_msg = (
                f"CRITICAL: Failed to create/verify imaging columns in {ms_path}: {e}. "
                "MS is not ready for calibration/imaging."
            )
            logger.error(error_msg, exc_info=True)
            raise ConversionError(
                error_msg,
                context={"ms_path": ms_path, "error": str(e)},
                suggestion="Check MS file permissions, disk space, and CASA installation. "
                "Try recreating the MS if the issue persists.",
            ) from e

    if ensure_flag_and_weight:
        try:
            _ensure_flag_and_weight_spectrum(ms_path)
            operations_status["flag_weight"] = "success"
        except Exception as e:
            operations_status["flag_weight"] = f"failed: {e}"
            # Non-fatal: continue with other operations

    if do_initweights:
        try:
            _initialize_weights(ms_path)
            operations_status["initweights"] = "success"
        except Exception as e:
            operations_status["initweights"] = f"failed: {e}"
            # Non-fatal: initweights often fails on edge cases

    if fix_mount:
        try:
            _fix_mount_type_in_ms(ms_path)
            operations_status["mount_fix"] = "success"
        except Exception as e:
            operations_status["mount_fix"] = f"failed: {e}"
            # Non-fatal: mount type normalization is optional

    if stamp_observation_telescope:
        try:
            import casacore.tables as _casatables  # type: ignore

            _tb = _casatables.table

            name = os.getenv("PIPELINE_TELESCOPE_NAME", "DSA_110")
            with _tb(ms_path + "::OBSERVATION", readonly=False) as tb:
                n = tb.nrows()
                if n:
                    tb.putcol("TELESCOPE_NAME", [name] * n)
            operations_status["telescope_stamp"] = "success"
        except Exception as e:
            operations_status["telescope_stamp"] = f"failed: {e}"
            # Non-fatal: telescope name stamping is optional

    # Fix FIELD table phase centers (corrects RA assignment bug)
    try:
        _fix_field_phase_centers_from_times(ms_path)
        operations_status["field_phase_centers"] = "success"
    except Exception as e:
        operations_status["field_phase_centers"] = f"failed: {e}"
        # Non-fatal: field phase center fix is best-effort

    # Fix OBSERVATION table and OBSERVATION_ID column (critical for CASA msmetadata)
    try:
        _ensure_observation_table_valid(ms_path)
        _fix_observation_id_column(ms_path)
        operations_status["observation_table"] = "success"
    except Exception as e:
        operations_status["observation_table"] = f"failed: {e}"
        # Non-fatal: observation table fix is best-effort

    # Fix OBSERVATION table TIME_RANGE (corrects missing/invalid time range)
    try:
        _fix_observation_time_range(ms_path)
        operations_status["observation_time_range"] = "success"
    except Exception as e:
        operations_status["observation_time_range"] = f"failed: {e}"
        # Non-fatal: observation time range fix is best-effort

    # Auto-detect and rename calibrator fields (recommended for drift-scan observations)
    if rename_calibrator_fields:
        try:
            from dsa110_contimg.calibration.field_naming import (
                rename_calibrator_fields_from_catalog,
            )

            result = rename_calibrator_fields_from_catalog(
                ms_path,
                catalog_path=catalog_path,
            )
            if result:
                cal_name, field_idx = result
                operations_status["calibrator_renaming"] = "success"
                logger.info(
                    f":check_mark: Auto-renamed field {field_idx} to '{cal_name}_t{field_idx}'"
                )
            else:
                operations_status["calibrator_renaming"] = "no calibrator found"
                logger.debug("No calibrator found in MS for field renaming")
        except Exception as e:
            operations_status["calibrator_renaming"] = f"failed: {e}"
            logger.debug(f"Calibrator field renaming not available: {e}")
            # Non-fatal: field renaming is optional

    # Summary logging - report what worked and what didn't
    success_ops = [op for op, status in operations_status.items() if status == "success"]
    failed_ops = [
        f"{op}({status.split(': ')[1]})"
        for op, status in operations_status.items()
        if status.startswith("failed")
    ]

    if success_ops:
        logger.info(f":check_mark: MS configuration completed: {', '.join(success_ops)}")
    if failed_ops:
        logger.warning(f":warning_sign: MS configuration partial failures: {'; '.join(failed_ops)}")

    # Final validation: verify MS is still readable after all operations
    try:
        import casacore.tables as _casatables

        _tb = _casatables.table

        with _tb(ms_path, readonly=True) as tb:
            if tb.nrows() == 0:
                raise RuntimeError(f"MS has no data after configuration: {ms_path}")
    except Exception as e:
        raise RuntimeError(f"MS became unreadable after configuration: {e}")


__all__ = [
    "configure_ms_for_imaging",
    "_ensure_imaging_columns_exist",
    "_ensure_imaging_columns_populated",
    "_ensure_flag_and_weight_spectrum",
    "_initialize_weights",
    "_fix_mount_type_in_ms",
    "_fix_field_phase_centers_from_times",
    "_ensure_observation_table_valid",
    "_fix_observation_id_column",
    "_fix_observation_time_range",
]
