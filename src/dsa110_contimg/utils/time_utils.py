"""Utilities for handling TIME in Measurement Sets using astropy.

This module provides robust TIME conversion utilities that leverage astropy.Time
for validation and conversion. It standardizes CASA TIME format handling across
the codebase to ensure consistency and correctness.

CASA TIME Format:
- CASA TIME is stored in seconds since MJD 51544.0 (2000-01-01 00:00:00 UTC)
- Conversion: mjd = 51544.0 + casa_time_sec / 86400.0
- msmetadata.timerangeforobs() returns MJD days directly (no conversion needed)
- msmetadata.timesforscans() returns seconds (needs conversion with epoch offset)
- Main table TIME column is in seconds (needs conversion with epoch offset)
- OBSERVATION table TIME_RANGE is in seconds (needs conversion with epoch offset)
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Union

import numpy as np
from astropy.time import Time
import astropy.units as u

logger = logging.getLogger(__name__)

# CASA TIME epoch: MJD 51544.0 = 2000-01-01 00:00:00 UTC
# This is the reference epoch for CASA Measurement Set TIME columns
CASA_TIME_EPOCH_MJD = 51544.0

# Reasonable date range for validation (2000-2100)
DEFAULT_YEAR_RANGE = (2000, 2100)


def casa_time_to_mjd(time_sec: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Convert CASA TIME (seconds since MJD 51544.0) to MJD days using astropy.
    
    This function uses astropy for robust time conversion and validation.
    CASA TIME is defined as seconds since MJD 51544.0 (2000-01-01).
    
    Parameters
    ----------
    time_sec : float or array-like
        CASA TIME in seconds since MJD 51544.0
        
    Returns
    -------
    float or array
        MJD days (Modified Julian Date)
        
    Examples
    --------
    >>> casa_time_to_mjd(0.0)
    51544.0
    >>> casa_time_to_mjd(86400.0)  # One day later
    51545.0
    """
    if isinstance(time_sec, np.ndarray):
        return CASA_TIME_EPOCH_MJD + time_sec / 86400.0
    return CASA_TIME_EPOCH_MJD + float(time_sec) / 86400.0


def mjd_to_casa_time(mjd: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Convert MJD days to CASA TIME (seconds since MJD 51544.0) using astropy.
    
    Parameters
    ----------
    mjd : float or array-like
        MJD days (Modified Julian Date)
        
    Returns
    -------
    float or array
        CASA TIME in seconds since MJD 51544.0
        
    Examples
    --------
    >>> mjd_to_casa_time(51544.0)
    0.0
    >>> mjd_to_casa_time(51545.0)  # One day later
    86400.0
    """
    if isinstance(mjd, np.ndarray):
        return (mjd - CASA_TIME_EPOCH_MJD) * 86400.0
    return (float(mjd) - CASA_TIME_EPOCH_MJD) * 86400.0


def casa_time_to_astropy_time(
    time_sec: Union[float, np.ndarray],
    scale: str = 'utc'
) -> Time:
    """Convert CASA TIME to astropy Time object.
    
    This leverages astropy's robust time handling and validation.
    
    Parameters
    ----------
    time_sec : float or array-like
        CASA TIME in seconds since MJD 51544.0
    scale : str, optional
        Time scale (default: 'utc')
        
    Returns
    -------
    Time
        Astropy Time object
        
    Examples
    --------
    >>> t = casa_time_to_astropy_time(0.0)
    >>> t.mjd
    51544.0
    >>> t.isot
    '2000-01-01T00:00:00.000'
    """
    mjd = casa_time_to_mjd(time_sec)
    return Time(mjd, format='mjd', scale=scale)


def validate_time_mjd(
    mjd: float,
    year_range: Tuple[int, int] = DEFAULT_YEAR_RANGE
) -> bool:
    """Validate that MJD corresponds to a reasonable date using astropy.
    
    Uses astropy Time to check if the date falls within expected range.
    
    Parameters
    ----------
    mjd : float
        MJD days to validate
    year_range : tuple of int, optional
        Expected year range (min_year, max_year)
        
    Returns
    -------
    bool
        True if date is within reasonable range
        
    Examples
    --------
    >>> validate_time_mjd(51544.0)  # 2000-01-01
    True
    >>> validate_time_mjd(0.0)  # 1858-11-17 (too old)
    False
    """
    try:
        t = Time(mjd, format='mjd')
        year = t.datetime.year
        return year_range[0] <= year <= year_range[1]
    except Exception:
        return False


def detect_casa_time_format(
    time_sec: float,
    year_range: Tuple[int, int] = DEFAULT_YEAR_RANGE
) -> Tuple[bool, float]:
    """Detect if CASA TIME needs epoch offset using astropy validation.
    
    Tests both with and without epoch offset to determine correct format.
    Uses astropy Time for robust date validation.
    
    Parameters
    ----------
    time_sec : float
        TIME value in seconds (format unknown)
    year_range : tuple of int, optional
        Expected year range for validation
        
    Returns
    -------
    tuple of (bool, float)
        (needs_offset, mjd)
        - needs_offset: True if epoch offset 51544.0 should be applied
        - mjd: The correctly converted MJD value
        
    Examples
    --------
    >>> needs_offset, mjd = detect_casa_time_format(0.0)
    >>> needs_offset
    True
    >>> abs(mjd - 51544.0) < 0.001
    True
    """
    # Test with epoch offset (standard CASA format)
    mjd_with_offset = casa_time_to_mjd(time_sec)
    valid_with_offset = validate_time_mjd(mjd_with_offset, year_range)
    
    # Test without epoch offset (legacy format)
    mjd_without_offset = time_sec / 86400.0
    valid_without_offset = validate_time_mjd(mjd_without_offset, year_range)
    
    # Prefer format that gives valid date
    if valid_with_offset and not valid_without_offset:
        return True, mjd_with_offset
    elif valid_without_offset and not valid_with_offset:
        return False, mjd_without_offset
    elif valid_with_offset:
        # Both valid, prefer standard CASA format (with offset)
        return True, mjd_with_offset
    else:
        # Neither valid, default to standard CASA format
        # (better to fail with correct format than wrong format)
        return True, mjd_with_offset


def extract_ms_time_range(
    ms_path: str,
    year_range: Tuple[int, int] = DEFAULT_YEAR_RANGE
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Extract time range from MS using astropy for validation.
    
    This is a robust, standardized implementation that:
    1. Uses msmetadata.timerangeforobs() (most reliable, returns MJD directly)
    2. Falls back to msmetadata.timesforscans() (with proper epoch conversion)
    3. Falls back to main table TIME column (with proper epoch conversion)
    4. Falls back to OBSERVATION table TIME_RANGE (with proper epoch conversion)
    5. Validates all extracted times using astropy
    
    All TIME conversions use casa_time_to_mjd() for consistency.
    
    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    year_range : tuple of int, optional
        Expected year range for validation
        
    Returns
    -------
    tuple of (Optional[float], Optional[float], Optional[float])
        (start_mjd, end_mjd, mid_mjd) or (None, None, None) if unavailable
        
    Examples
    --------
    >>> start, end, mid = extract_ms_time_range('observation.ms')
    >>> if mid is not None:
    ...     t = Time(mid, format='mjd')
    ...     print(f"Observation time: {t.isot}")
    """
    # Method 1: msmetadata.timerangeforobs() - most reliable, returns MJD days directly
    try:
        from casatools import msmetadata  # type: ignore
        
        msmd = msmetadata()
        msmd.open(ms_path)
        try:
            tr = msmd.timerangeforobs()
            msmd.close()
            if tr and isinstance(tr, (list, tuple)) and len(tr) >= 2:
                start_mjd = float(tr[0])
                end_mjd = float(tr[1])
                mid_mjd = 0.5 * (start_mjd + end_mjd)
                
                # Validate using astropy
                if (validate_time_mjd(start_mjd, year_range) and
                    validate_time_mjd(end_mjd, year_range)):
                    return start_mjd, end_mjd, mid_mjd
                else:
                    logger.warning(
                        f"msmetadata.timerangeforobs() returned invalid dates "
                        f"for {ms_path}: start={start_mjd}, end={end_mjd}"
                    )
        except Exception as e:
            logger.debug(f"msmetadata.timerangeforobs() failed for {ms_path}: {e}")
        finally:
            try:
                msmd.close()
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Failed to open msmetadata for {ms_path}: {e}")
    
    # Method 2: msmetadata.timesforscans() - returns seconds, needs epoch conversion
    try:
        from casatools import msmetadata  # type: ignore
        
        msmd = msmetadata()
        msmd.open(ms_path)
        try:
            tmap = msmd.timesforscans()
            msmd.close()
            if isinstance(tmap, dict) and tmap:
                all_ts = [t for arr in tmap.values() for t in arr]
                if all_ts:
                    t0_sec = min(all_ts)
                    t1_sec = max(all_ts)
                    # Convert using proper CASA TIME format
                    start_mjd = casa_time_to_mjd(t0_sec)
                    end_mjd = casa_time_to_mjd(t1_sec)
                    mid_mjd = 0.5 * (start_mjd + end_mjd)
                    
                    # Validate using astropy
                    if (validate_time_mjd(start_mjd, year_range) and
                        validate_time_mjd(end_mjd, year_range)):
                        return float(start_mjd), float(end_mjd), float(mid_mjd)
        except Exception as e:
            logger.debug(f"msmetadata.timesforscans() failed for {ms_path}: {e}")
        finally:
            try:
                msmd.close()
            except Exception:
                pass
    except Exception:
        pass
    
    # Method 3: Main table TIME column - seconds, needs epoch conversion
    try:
        from casacore.tables import table as _tb
        
        with _tb(ms_path, readonly=True) as _main:
            if 'TIME' in _main.colnames():
                times = _main.getcol('TIME')
                if len(times) > 0:
                    t0_sec = float(times.min())
                    t1_sec = float(times.max())
                    
                    # Detect format and convert
                    needs_offset, start_mjd = detect_casa_time_format(t0_sec, year_range)
                    _, end_mjd = detect_casa_time_format(t1_sec, year_range)
                    mid_mjd = 0.5 * (start_mjd + end_mjd)
                    
                    # Validate using astropy
                    if (validate_time_mjd(start_mjd, year_range) and
                        validate_time_mjd(end_mjd, year_range)):
                        return float(start_mjd), float(end_mjd), float(mid_mjd)
                    else:
                        logger.warning(
                            f"TIME column values failed validation for {ms_path}: "
                            f"start={start_mjd}, end={end_mjd}"
                        )
    except Exception as e:
        logger.debug(f"Failed to read TIME column from {ms_path}: {e}")
    
    # Method 4: OBSERVATION table TIME_RANGE - seconds, needs epoch conversion
    try:
        from casacore.tables import table as _tb
        
        with _tb(f"{ms_path}::OBSERVATION", readonly=True) as _obs:
            if _obs.nrows() > 0 and 'TIME_RANGE' in _obs.colnames():
                tr = _obs.getcol("TIME_RANGE")
                if tr is not None and len(tr) > 0:
                    t0_sec = float(tr[0][0])
                    t1_sec = float(tr[0][1])
                    
                    # Convert using proper CASA TIME format
                    start_mjd = casa_time_to_mjd(t0_sec)
                    end_mjd = casa_time_to_mjd(t1_sec)
                    mid_mjd = 0.5 * (start_mjd + end_mjd)
                    
                    # Validate using astropy
                    if (validate_time_mjd(start_mjd, year_range) and
                        validate_time_mjd(end_mjd, year_range)):
                        return float(start_mjd), float(end_mjd), float(mid_mjd)
    except Exception as e:
        logger.debug(f"Failed to read TIME_RANGE from OBSERVATION table: {e}")
    
    logger.warning(f"Could not extract valid time range from {ms_path}")
    return None, None, None


__all__ = [
    'CASA_TIME_EPOCH_MJD',
    'DEFAULT_YEAR_RANGE',
    'casa_time_to_mjd',
    'mjd_to_casa_time',
    'casa_time_to_astropy_time',
    'validate_time_mjd',
    'detect_casa_time_format',
    'extract_ms_time_range',
]

