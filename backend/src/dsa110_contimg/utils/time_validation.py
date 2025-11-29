"""
Time validation utilities for verifying TIME extraction correctness.

This module provides functions to validate that extracted times are not just
consistent, but actually correct by cross-referencing multiple sources and
performing astronomical consistency checks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
from astropy.time import Time

from dsa110_contimg.calibration.schedule import DSA110_LOCATION
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logger = logging.getLogger(__name__)


def validate_ms_time_against_filename(
    ms_path: str | Path, tolerance_hours: float = 0.5
) -> Tuple[bool, Optional[str], Optional[float]]:
    """Validate MS TIME column against filename timestamp.

    Extracts timestamp from MS filename (if present) and compares with
    TIME column from the MS file. This is a critical validation because
    filename timestamps are set at data creation and should match the
    observation time.

    Parameters
    ----------
    ms_path : str or Path
        Path to Measurement Set
    tolerance_hours : float
        Maximum allowed difference in hours (default: 0.5)

    Returns
    -------
    is_valid : bool
        True if times match within tolerance
    error_msg : str or None
        Error message if validation fails
    time_diff_hours : float or None
        Time difference in hours
    """
    import re

    ms_path = Path(ms_path)

    # Extract timestamp from filename
    match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", ms_path.name)
    if not match:
        return True, None, None  # No filename timestamp to validate against

    try:
        filename_timestamp = Time(match.group(1), format="isot", scale="utc")

        # Extract time from MS
        _, _, mid_mjd = extract_ms_time_range(str(ms_path))
        if mid_mjd is None:
            return False, "Could not extract time from MS", None

        # Compare with filename timestamp
        time_diff_hours = abs((Time(mid_mjd, format="mjd") - filename_timestamp).to("hour").value)

        if time_diff_hours > tolerance_hours:
            error_msg = (
                f"TIME mismatch: MS TIME column indicates {Time(mid_mjd, format='mjd').isot}, "
                f"but filename suggests {filename_timestamp.isot} "
                f"(difference: {time_diff_hours:.2f} hours)"
            )
            return False, error_msg, time_diff_hours

        return True, None, time_diff_hours

    except Exception as e:
        return False, f"Validation error: {e}", None


def validate_ms_time_against_uvh5(
    ms_path: str | Path, uvh5_path: str | Path, tolerance_seconds: float = 1.0
) -> Tuple[bool, Optional[str], Optional[float]]:
    """Validate MS TIME column against source UVH5 file.

    Compares the TIME column in the MS file with the time_array from the
    source UVH5 file. This validates that the conversion from UVH5 to MS
    preserved the correct time information.

    Parameters
    ----------
    ms_path : str or Path
        Path to Measurement Set
    uvh5_path : str or Path
        Path to source UVH5 file
    tolerance_seconds : float
        Maximum allowed difference in seconds (default: 1.0)

    Returns
    -------
    is_valid : bool
        True if times match within tolerance
    error_msg : str or None
        Error message if validation fails
    time_diff_seconds : float or None
        Time difference in seconds
    """
    try:
        from pyuvdata import UVData

        # Read UVH5 time_array (in JD)
        uv = UVData()
        uv.read(str(uvh5_path), file_type="uvh5", read_data=False, run_check=False)
        uvh5_mjd = Time(np.mean(uv.time_array), format="jd").mjd
        del uv

        # Extract time from MS
        _, _, mid_mjd = extract_ms_time_range(str(ms_path))
        if mid_mjd is None:
            return False, "Could not extract time from MS", None

        # Compare
        time_diff_seconds = abs(mid_mjd - uvh5_mjd) * 86400.0

        if time_diff_seconds > tolerance_seconds:
            error_msg = (
                f"TIME mismatch: MS TIME indicates {Time(mid_mjd, format='mjd').isot}, "
                f"but UVH5 indicates {Time(uvh5_mjd, format='mjd').isot} "
                f"(difference: {time_diff_seconds:.2f} seconds)"
            )
            return False, error_msg, time_diff_seconds

        return True, None, time_diff_seconds

    except Exception as e:
        return False, f"Validation error: {e}", None


def validate_lst_consistency(
    ms_path: str | Path, pointing_ra_deg: float, tolerance_deg: float = 1.0
) -> Tuple[bool, Optional[str], Optional[float]]:
    """Validate that LST calculation is consistent with observation time.

    For meridian-tracking observations, the pointing RA should equal LST
    at the observation time. This validates that the TIME extraction is
    correct enough to produce accurate LST calculations.

    Parameters
    ----------
    ms_path : str or Path
        Path to Measurement Set
    pointing_ra_deg : float
        Pointing RA in degrees (from FIELD table or pointing database)
    tolerance_deg : float
        Maximum allowed difference in degrees (default: 1.0)

    Returns
    -------
    is_valid : bool
        True if LST matches pointing RA within tolerance
    error_msg : str or None
        Error message if validation fails
    lst_diff_deg : float or None
        LST difference in degrees
    """
    try:
        # Extract time from MS
        _, _, mid_mjd = extract_ms_time_range(str(ms_path))
        if mid_mjd is None:
            return False, "Could not extract time from MS", None

        # Calculate LST at observation time
        t = Time(mid_mjd, format="mjd", scale="utc", location=DSA110_LOCATION)
        lst_deg = t.sidereal_time("apparent").to_value("deg")

        # Compare with pointing RA
        lst_diff_deg = abs(lst_deg - pointing_ra_deg)

        # Handle wrap-around (RA is modulo 360)
        if lst_diff_deg > 180:
            lst_diff_deg = 360.0 - lst_diff_deg

        if lst_diff_deg > tolerance_deg:
            error_msg = (
                f"LST mismatch: Calculated LST is {lst_deg:.2f}°, "
                f"but pointing RA is {pointing_ra_deg:.2f}° "
                f"(difference: {lst_diff_deg:.2f}°). "
                f"This suggests TIME extraction may be incorrect."
            )
            return False, error_msg, lst_diff_deg

        return True, None, lst_diff_deg

    except Exception as e:
        return False, f"Validation error: {e}", None


def validate_time_ordering(ms_path: str | Path) -> Tuple[bool, Optional[str]]:
    """Validate that TIME values are correctly ordered.

    Checks that:
    1. TIME values are monotonically increasing (or constant within integration)
    2. OBSERVATION TIME_RANGE start < end
    3. TIME values fall within TIME_RANGE

    Parameters
    ----------
    ms_path : str or Path
        Path to Measurement Set

    Returns
    -------
    is_valid : bool
        True if time ordering is correct
    error_msg : str or None
        Error message if validation fails
    """
    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path

    ensure_casa_path()

    try:
        from casatools import table

        # Check main table TIME ordering
        tb = table()
        tb.open(str(ms_path), nomodify=True)
        times = tb.getcol("TIME")
        tb.close()

        if len(times) == 0:
            return False, "MS has no TIME values"

        # Check for decreasing times (allowing for constant values within integration)
        unique_times = np.unique(times)
        if len(unique_times) > 1:
            if np.any(np.diff(unique_times) < 0):
                return False, "TIME values are not monotonically increasing"

        # Check OBSERVATION TIME_RANGE
        tb_obs = table()
        tb_obs.open(f"{ms_path}::OBSERVATION", nomodify=True)
        if tb_obs.nrows() > 0:
            tr = tb_obs.getcol("TIME_RANGE")
            if tr.shape[0] >= 2:
                t0 = float(np.asarray(tr[0]).flat[0])
                t1 = float(np.asarray(tr[1]).flat[0])

                if t1 <= t0:
                    tb_obs.close()
                    return False, f"OBSERVATION TIME_RANGE is invalid: [{t0}, {t1}]"

                # Check that TIME values fall within TIME_RANGE
                if times.min() < t0 or times.max() > t1:
                    tb_obs.close()
                    return False, (
                        f"TIME values [{times.min():.1f}, {times.max():.1f}] "
                        f"outside TIME_RANGE [{t0:.1f}, {t1:.1f}]"
                    )
        tb_obs.close()

        return True, None

    except Exception as e:
        return False, f"Validation error: {e}"


def validate_observation_duration(
    ms_path: str | Path,
    expected_duration_minutes: Optional[float] = None,
    tolerance_percent: float = 10.0,
) -> Tuple[bool, Optional[str], Optional[float]]:
    """Validate that observation duration matches expected value.

    Parameters
    ----------
    ms_path : str or Path
        Path to Measurement Set
    expected_duration_minutes : float or None
        Expected duration in minutes (if None, only checks consistency)
    tolerance_percent : float
        Maximum allowed difference as percentage (default: 10%)

    Returns
    -------
    is_valid : bool
        True if duration is consistent/expected
    error_msg : str or None
        Error message if validation fails
    duration_minutes : float or None
        Actual duration in minutes
    """
    try:
        start_mjd, end_mjd, mid_mjd = extract_ms_time_range(str(ms_path))
        if start_mjd is None or end_mjd is None:
            return False, "Could not extract time range from MS", None

        duration_minutes = (end_mjd - start_mjd) * 24.0 * 60.0

        if expected_duration_minutes is not None:
            diff_percent = (
                abs(duration_minutes - expected_duration_minutes)
                / expected_duration_minutes
                * 100.0
            )
            if diff_percent > tolerance_percent:
                return (
                    False,
                    (
                        f"Duration mismatch: Expected {expected_duration_minutes:.1f} minutes, "
                        f"but got {duration_minutes:.1f} minutes (difference: {diff_percent:.1f}%)"
                    ),
                    duration_minutes,
                )

        return True, None, duration_minutes

    except Exception as e:
        return False, f"Validation error: {e}", None


def comprehensive_time_validation(
    ms_path: str | Path,
    uvh5_path: Optional[str | Path] = None,
    pointing_ra_deg: Optional[float] = None,
    expected_duration_minutes: Optional[float] = None,
) -> Dict[str, any]:
    """Perform comprehensive time validation on an MS file.

    Runs all available validation checks and returns a summary.

    Parameters
    ----------
    ms_path : str or Path
        Path to Measurement Set
    uvh5_path : str or Path or None
        Path to source UVH5 file (for cross-validation)
    pointing_ra_deg : float or None
        Pointing RA in degrees (for LST validation)
    expected_duration_minutes : float or None
        Expected observation duration in minutes

    Returns
    -------
    results : dict
        Dictionary with validation results:
        - 'all_valid': bool - True if all checks pass
        - 'checks': dict - Individual check results
        - 'extracted_time': dict - Extracted time information
        - 'warnings': list - Warning messages
        - 'errors': list - Error messages
    """
    results = {
        "all_valid": True,
        "checks": {},
        "extracted_time": {},
        "warnings": [],
        "errors": [],
    }

    # Extract time information
    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(str(ms_path))
    if mid_mjd is not None:
        results["extracted_time"] = {
            "start_mjd": start_mjd,
            "end_mjd": end_mjd,
            "mid_mjd": mid_mjd,
            "start_iso": Time(start_mjd, format="mjd").isot,
            "end_iso": Time(end_mjd, format="mjd").isot,
            "mid_iso": Time(mid_mjd, format="mjd").isot,
        }
    else:
        results["errors"].append("Could not extract time from MS")
        results["all_valid"] = False
        return results

    # Check 1: Time ordering
    is_valid, error_msg = validate_time_ordering(ms_path)
    results["checks"]["time_ordering"] = {"valid": is_valid, "error": error_msg}
    if not is_valid:
        results["errors"].append(f"Time ordering: {error_msg}")
        results["all_valid"] = False

    # Check 2: Filename timestamp validation
    is_valid, error_msg, time_diff = validate_ms_time_against_filename(ms_path)
    results["checks"]["filename_validation"] = {
        "valid": is_valid,
        "error": error_msg,
        "time_diff_hours": time_diff,
    }
    if not is_valid:
        results["errors"].append(f"Filename validation: {error_msg}")
        results["all_valid"] = False
    elif time_diff is not None and time_diff > 0.1:
        results["warnings"].append(
            f"Filename timestamp differs by {time_diff:.3f} hours "
            f"(within tolerance but worth noting)"
        )

    # Check 3: UVH5 cross-validation
    if uvh5_path is not None:
        is_valid, error_msg, time_diff = validate_ms_time_against_uvh5(ms_path, uvh5_path)
        results["checks"]["uvh5_validation"] = {
            "valid": is_valid,
            "error": error_msg,
            "time_diff_seconds": time_diff,
        }
        if not is_valid:
            results["errors"].append(f"UVH5 validation: {error_msg}")
            results["all_valid"] = False

    # Check 4: LST consistency
    if pointing_ra_deg is not None:
        is_valid, error_msg, lst_diff = validate_lst_consistency(ms_path, pointing_ra_deg)
        results["checks"]["lst_consistency"] = {
            "valid": is_valid,
            "error": error_msg,
            "lst_diff_deg": lst_diff,
        }
        if not is_valid:
            results["errors"].append(f"LST consistency: {error_msg}")
            results["all_valid"] = False

    # Check 5: Duration validation
    is_valid, error_msg, duration = validate_observation_duration(
        ms_path, expected_duration_minutes
    )
    results["checks"]["duration"] = {
        "valid": is_valid,
        "error": error_msg,
        "duration_minutes": duration,
    }
    if not is_valid:
        results["errors"].append(f"Duration validation: {error_msg}")
        results["all_valid"] = False

    return results
