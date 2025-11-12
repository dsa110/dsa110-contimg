#!/usr/bin/env python3
"""
UVH5 to CASA Measurement Set converter (legacy implementation).

This module implements our original conversion flow (including optional
UVFITS+CASA import path, 5-minute slot grouping, and frequency filling).
It is preserved for reference and reproducibility.

Note: The default converter used by the streaming worker now lives in
`dsa110_contimg.core.conversion.uvh5_to_ms_converter_v2`, which adopts
the grouping and direct MS-writing behavior consistent with the separate
DSA-110 scripts. Prefer that version for new processing.
"""

import os
import glob
import shutil
import argparse
from datetime import datetime, timedelta
from typing import List, Optional, Union, Tuple, Dict
import logging
import warnings
import time
from pathlib import Path

import numpy as np
import astropy.units as u
import astropy.constants as c
from astropy.time import Time
from astropy.coordinates import angular_separation, SkyCoord, EarthLocation, HADec
from pyuvdata import UVData
from casatasks import importuvfits
from casacore.tables import addImagingColumns, table
import casatools as cc
from scipy.special import j1

import sys
from pathlib import Path

from dsa110_contimg.utils.antpos_local import get_itrf

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("uvh5_to_ms_converter")


def get_meridian_coords(pt_dec: u.Quantity, time_mjd: float) -> Tuple[u.Quantity, u.Quantity]:
    """Calculate meridian RA/Dec at a given time and pointing dec using Astropy."""
    ovro_loc = EarthLocation.from_geodetic(lon=-118.2817 * u.deg, lat=37.2314 * u.deg, height=1222 * u.m)
    obstime = Time(time_mjd, format='mjd')
    hadec_coord = SkyCoord(ha=0 * u.hourangle, dec=pt_dec, frame='hadec', obstime=obstime, location=ovro_loc)
    icrs_coord = hadec_coord.transform_to('icrs')
    return icrs_coord.ra.to(u.rad), icrs_coord.dec.to(u.rad)


def setup_logging(level: str) -> None:
    """Configure root logger level at runtime."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)
    logger.debug("Log level set to %s", level.upper())


# DSA-110 Constants (from dsacalib.constants)
SECONDS_PER_SIDEREAL_DAY = 3600 * 23.9344699
SECONDS_PER_DAY = 3600 * 24
DEG_PER_HOUR = 360 / SECONDS_PER_SIDEREAL_DAY * 3600
CASA_TIME_OFFSET = 0.00042824074625968933  # in days

# OVRO site coordinates (from dsacalib.constants) - REMOVED, now using astropy EarthLocation
DEFAULT_CHUNK_MINUTES = 5.0
DEFAULT_CLUSTER_TOLERANCE = DEFAULT_CHUNK_MINUTES / 2.0
ROUNDING_SLACK_SECONDS = 0.0


def _parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    base = os.path.splitext(filename)[0]
    if '_sb' not in base:
        return None
    ts_part = base.rsplit('_sb', maxsplit=1)[0]
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y%m%d_%H%M%S'):
        try:
            return datetime.strptime(ts_part, fmt)
        except ValueError:
            continue
    return None


def _extract_subband_index(filename: str) -> Optional[int]:
    base = os.path.splitext(filename)[0]
    if '_sb' not in base:
        return None
    try:
        return int(base.rsplit('_sb', maxsplit=1)[1])
    except ValueError:
        return None


def _normalize_chunk_start(dt: datetime, chunk_minutes: float) -> datetime:
    """Round a datetime to the nearest configured chunk boundary with slack."""
    chunk_seconds = chunk_minutes * 60.0
    slack = ROUNDING_SLACK_SECONDS
    epoch = datetime.utcfromtimestamp(0)
    seconds_from_epoch = (dt - epoch).total_seconds()
    base_seconds = (seconds_from_epoch // chunk_seconds) * chunk_seconds
    base_dt = epoch + timedelta(seconds=base_seconds)
    offset = (dt - base_dt).total_seconds()
    if offset >= chunk_seconds - slack:
        base_dt += timedelta(seconds=chunk_seconds)
    return base_dt


def _within_cluster(a: datetime, b: datetime, tolerance_minutes: float) -> bool:
    delta = abs(a - b)
    return delta <= timedelta(minutes=tolerance_minutes)


def _coerce_uvdata_float64(uv: UVData) -> None:
    """Force key UVData arrays to float64 precision."""
    if uv.uvw_array.dtype != np.float64:
        logger.info("Converting UVW array from %s to float64", uv.uvw_array.dtype)
        uv.uvw_array = uv.uvw_array.astype(np.float64)
    if uv.time_array.dtype != np.float64:
        logger.info("Converting time array from %s to float64", uv.time_array.dtype)
        uv.time_array = uv.time_array.astype(np.float64)
    if uv.lst_array.dtype != np.float64:
        logger.info("Converting LST array from %s to float64", uv.lst_array.dtype)
        uv.lst_array = uv.lst_array.astype(np.float64)


def _load_subband_uvdata(path: str, antenna_list: Optional[List[str]]) -> UVData:
    """Read a single subband UVH5 file into a UVData object without checks."""
    uv = UVData()
    read_kwargs = dict(
        file_type='uvh5',
        run_check=False,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
        check_extra=False,
    )
    if antenna_list is not None:
        read_kwargs['antenna_names'] = antenna_list
    uv.read(path, **read_kwargs)
    if uv.uvw_array.dtype != np.float64:
        uv.uvw_array = uv.uvw_array.astype(np.float64)
    if uv.time_array.dtype != np.float64:
        uv.time_array = uv.time_array.astype(np.float64)
    if uv.lst_array.dtype != np.float64:
        uv.lst_array = uv.lst_array.astype(np.float64)
    return uv


def _get_relative_antenna_positions(uv: UVData) -> np.ndarray:
    """Return the UVData antenna positions relative to telescope location."""
    if hasattr(uv, 'antenna_positions') and uv.antenna_positions is not None:
        return uv.antenna_positions
    telescope = getattr(uv, 'telescope', None)
    if telescope is not None and getattr(telescope, 'antenna_positions', None) is not None:
        return telescope.antenna_positions
    raise AttributeError("UVData object has no antenna_positions information")


def _set_relative_antenna_positions(uv: UVData, rel_positions: np.ndarray) -> None:
    """Write relative antenna positions back to the UVData structure."""
    if hasattr(uv, 'antenna_positions') and uv.antenna_positions is not None:
        uv.antenna_positions[:rel_positions.shape[0]] = rel_positions
    elif hasattr(uv, 'antenna_positions'):
        uv.antenna_positions = rel_positions
    else:
        setattr(uv, 'antenna_positions', rel_positions)

    telescope = getattr(uv, 'telescope', None)
    if telescope is not None:
        if getattr(telescope, 'antenna_positions', None) is not None:
            telescope.antenna_positions[:rel_positions.shape[0]] = rel_positions
        elif hasattr(telescope, 'antenna_positions'):
            telescope.antenna_positions = rel_positions
        else:
            setattr(telescope, 'antenna_positions', rel_positions)

def find_subband_groups(
    input_dir: str,
    start_time: str,
    end_time: str,
    chunk_minutes: float = DEFAULT_CHUNK_MINUTES,
    tolerance_minutes: float = DEFAULT_CLUSTER_TOLERANCE,
) -> List[List[str]]:
    """
    Find all DSA-110 subband file groups in the input directory that fall within
    the specified time range.
    """
    logger.info("Searching for DSA-110 subband files in %s", input_dir)

    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    # Allow filename timestamp jitter by expanding selection window by tolerance
    start_dt_tol = start_dt - timedelta(minutes=tolerance_minutes)
    end_dt_tol = end_dt + timedelta(minutes=tolerance_minutes)

    # Collect candidate files with parsed timestamps and indices
    candidates: List[Tuple[str, datetime, int]] = []
    for file_path in glob.glob(os.path.join(input_dir, '*_sb??.hdf5')):
        filename = os.path.basename(file_path)
        ts = _parse_timestamp_from_filename(filename)
        if ts is None:
            logger.debug("Skipping file with unparsable timestamp: %s", filename)
            continue
        # Include candidates whose filename timestamp falls within the expanded window
        if not (start_dt_tol <= ts <= end_dt_tol):
            continue
        sb_idx = _extract_subband_index(filename)
        if sb_idx is None:
            logger.debug("Skipping file with missing subband index: %s", filename)
            continue
        candidates.append((file_path, ts, sb_idx))

    if not candidates:
        logger.info("No files found within time range")
        return []

    # Sort by timestamp so we can cluster deterministically
    candidates.sort(key=lambda item: item[1])
    groups: Dict[str, Dict[int, str]] = {}
    for file_path, ts, sb_idx in candidates:
        # Map each file to a normalized 5-minute slot. This absorbs per-file
        # timestamp jitter of up to +/- chunk_minutes/2 by design.
        normalized_start = _normalize_chunk_start(ts, chunk_minutes)
        assigned_group = normalized_start.strftime('%Y-%m-%dT%H:%M:%S')
        slot = groups.setdefault(assigned_group, {})
        if sb_idx in slot:
            logger.warning(
                "Duplicate subband sb%02d detected for group %s; keeping first entry and skipping %s",
                sb_idx,
                assigned_group,
                file_path,
            )
            continue
        slot[sb_idx] = file_path

    file_groups: List[List[str]] = []
    expected_indices = set(range(16))
    for group_id_str, slot in sorted(groups.items()):
        have = set(slot.keys())
        missing = sorted(expected_indices - have)
        if missing:
            logger.warning(
                "Group %s has missing subbands: %s (%s/%s present)",
                group_id_str,
                ','.join(f"sb{idx:02d}" for idx in missing),
                len(have),
                16,
            )
            continue
        ordered = [slot[idx] for idx in sorted(slot.keys())]
        logger.info("Identified group at %s with %s subband files", group_id_str, len(ordered))
        file_groups.append(ordered)

    logger.info("Found %s complete observation groups within time range", len(file_groups))
    return file_groups


def load_uvh5_file(fname: str, antenna_list: Optional[List[str]] = None,
                   dt: Optional[u.Quantity] = None,
                   phase_ra: Optional[u.Quantity] = None,
                   phase_dec: Optional[u.Quantity] = None,
                   phase_time: Optional[Time] = None) -> tuple:
    """
    Load a UVH5 file and optionally filter by antennas and time duration.
    Based on dsacalib.uvh5_to_ms.load_uvh5_file.
    
    Parameters:
    -----------
    fname : str
        Path to UVH5 file
    antenna_list : list, optional
        List of antenna names to include
    dt : astropy.Quantity, optional
        Duration of data to extract
    phase_ra : astropy.Quantity, optional
        RA for phasing
    phase_dec : astropy.Quantity, optional
        DEC for phasing
    phase_time : astropy.time.Time, optional
        Time for phasing
        
    Returns:
    --------
    tuple
        (uvdata, pt_dec, phase_ra, phase_dec)
    """
    logger.info("Loading UVH5 file: %s", os.path.basename(fname))
    
    # Validate phasing parameters
    if ((phase_ra is None and phase_dec is not None) or 
        (phase_ra is not None and phase_dec is None)):
        logger.error("Only one of phase_ra/phase_dec defined for %s", fname)
        raise RuntimeError(
            "Only one of phase_ra and phase_dec defined. Please define both or neither."
        )
    if phase_time is not None and phase_ra is not None:
        logger.error("Both phase_time and phase_ra supplied for %s", fname)
        raise RuntimeError(
            "Please specify only one of phase_time and phasing direction (phase_ra + phase_dec)"
        )
    
    # Initialize UVData object
    uvdata = UVData()
    
    # Read the UVH5 file with relaxed checks so we can coerce dtypes first
    read_kwargs = dict(
        file_type='uvh5',
        run_check=False,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
        check_extra=False,
    )
    if antenna_list is not None:
        read_kwargs['antenna_names'] = antenna_list
    uvdata.read(fname, **read_kwargs)
    _coerce_uvdata_float64(uvdata)

    try:
        uvdata.check()
    except Exception as exc:  # noqa: BLE001
        logger.warning("UVData validation failed after dtype coercion: %s", exc)
    
    # Get pointing declination
    pt_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad
    
    # Get pointing information
    if phase_ra is None:
        if phase_time is None:
            phase_time = Time(np.mean(uvdata.time_array), format='jd')
        
        # Calculate meridian coordinates using Astropy
        phase_ra, phase_dec = get_meridian_coords(pt_dec, phase_time.mjd)
    
    # Extract time duration if specified
    if dt is not None:
        extract_times_dsacalib(uvdata, phase_ra, dt)
    
    logger.info(
        "Loaded %s baselines, %s frequencies, %s polarisations",
        uvdata.Nblts,
        uvdata.Nfreqs,
        uvdata.Npols
    )
    return uvdata, pt_dec, phase_ra, phase_dec


def extract_times_dsacalib(uvdata: UVData, ra: u.Quantity,
                          dt: u.Quantity) -> None:
    """
    Extract a specific time duration from UVData object using DSA-110 approach.
    Based on dsacalib.uvh5_to_ms.extract_times.
    
    Parameters:
    -----------
    uvdata : UVData
        UVData object to modify in-place
    ra : astropy.Quantity
        RA around which to extract data
    dt : astropy.Quantity
        Duration of data to extract
    """
    logger.debug("Extracting %s of data around RA %s", dt, ra)
    
    # Calculate LST range based on RA and duration
    lst_min = (ra - (dt * 2 * np.pi * u.rad /
                     (SECONDS_PER_SIDEREAL_DAY * u.s)) / 2
              ).to_value(u.rad) % (2 * np.pi)
    lst_max = (ra + (dt * 2 * np.pi * u.rad /
                     (SECONDS_PER_SIDEREAL_DAY * u.s)) / 2
              ).to_value(u.rad) % (2 * np.pi)
    
    if lst_min < lst_max:
        idx_to_extract = np.where(
            (uvdata.lst_array >= lst_min) & (uvdata.lst_array <= lst_max)
        )[0]
    else:
        idx_to_extract = np.where(
            (uvdata.lst_array >= lst_min) | (uvdata.lst_array <= lst_max)
        )[0]
    
    if len(idx_to_extract) == 0:
        message = (
            f"No times in uvh5 file match requested timespan with duration {dt} "
            f"centered at RA {ra}."
        )
        logger.error(message)
        raise ValueError(message)
    
    idxmin = min(idx_to_extract)
    idxmax = max(idx_to_extract) + 1
    assert (idxmax - idxmin) % uvdata.Nbls == 0
    
    # Extract data for the time range
    uvdata.uvw_array = uvdata.uvw_array[idxmin:idxmax, ...]
    uvdata.data_array = uvdata.data_array[idxmin:idxmax, ...]
    uvdata.time_array = uvdata.time_array[idxmin:idxmax, ...]
    uvdata.lst_array = uvdata.lst_array[idxmin:idxmax, ...]
    uvdata.nsample_array = uvdata.nsample_array[idxmin:idxmax, ...]
    uvdata.flag_array = uvdata.flag_array[idxmin:idxmax, ...]
    uvdata.ant_1_array = uvdata.ant_1_array[idxmin:idxmax, ...]
    uvdata.ant_2_array = uvdata.ant_2_array[idxmin:idxmax, ...]
    uvdata.baseline_array = uvdata.baseline_array[idxmin:idxmax, ...]
    uvdata.integration_time = uvdata.integration_time[idxmin:idxmax, ...]
    
    # Update Nblts and Ntimes
    uvdata.Nblts = int(idxmax - idxmin)
    assert uvdata.data_array.shape[0] == uvdata.Nblts
    uvdata.Ntimes = uvdata.Nblts // uvdata.Nbls
    
    logger.debug("Extracted %s time samples", len(idx_to_extract))


def extract_times(uvdata: UVData, dt: u.Quantity) -> None:
    """
    Extract a specific time duration from UVData object (legacy function).
    
    Parameters:
    -----------
    uvdata : UVData
        UVData object to modify in-place
    dt : astropy.Quantity
        Duration of data to extract
    """
    logger.debug("Extracting %s of data (legacy extractor)", dt)
    
    # Get the time range
    time_center = np.mean(uvdata.time_array)
    time_start = time_center - dt.to(u.day).value / 2
    time_end = time_center + dt.to(u.day).value / 2
    
    # Find indices within time range
    time_mask = (uvdata.time_array >= time_start) & (uvdata.time_array <= time_end)
    time_indices = np.where(time_mask)[0]
    
    if len(time_indices) == 0:
        logger.warning("No data found within specified time range (legacy extractor)")
        return
    
    # Extract data for the time range
    uvdata.uvw_array = uvdata.uvw_array[time_indices, ...]
    uvdata.data_array = uvdata.data_array[time_indices, ...]
    uvdata.time_array = uvdata.time_array[time_indices, ...]
    uvdata.lst_array = uvdata.lst_array[time_indices, ...]
    uvdata.nsample_array = uvdata.nsample_array[time_indices, ...]
    uvdata.flag_array = uvdata.flag_array[time_indices, ...]
    uvdata.ant_1_array = uvdata.ant_1_array[time_indices, ...]
    uvdata.ant_2_array = uvdata.ant_2_array[time_indices, ...]
    uvdata.baseline_array = uvdata.baseline_array[time_indices, ...]
    uvdata.integration_time = uvdata.integration_time[time_indices, ...]
    
    # Update Nblts
    uvdata.Nblts = len(time_indices)
    
    logger.debug("Extracted %s time samples (legacy extractor)", len(time_indices))


def set_antenna_positions(uvdata: UVData) -> np.ndarray:
    """
    Set antenna positions for the measurement set using DSA-110 positions.
    Based on dsacalib.uvh5_to_ms.set_antenna_positions.

    Parameters:
    -----------
    uvdata : UVData
        UVData object containing antenna information

    Returns:
    --------
    np.ndarray
        Array of antenna positions in ITRF coordinates (absolute, in meters)
    """
    logger.info("Setting DSA-110 antenna positions")

    try:
        # Use local antenna catalog; defaults to tee center for relative offsets.
        # We need absolute ITRF positions (x_m, y_m, z_m) for MS ANTENNA table,
        # and relative positions (antenna_positions) relative to telescope_location
        # for UVData. The catalog provides both absolute and relative columns.
        df_itrf = get_itrf(latlon_center=None)
    except Exception as exc:
        logger.error("Failed to load antenna coordinates from local catalogue: %s", exc)
        raise

    # Absolute ITRF antenna positions in meters
    abs_positions = np.array([
        df_itrf['x_m'],
        df_itrf['y_m'],
        df_itrf['z_m']
    ]).T.astype(np.float64)

    n_itrf_antennas = len(df_itrf)

    # Obtain telescope location (handle astropy EarthLocation structure)
    telescope_location = getattr(uvdata, 'telescope_location', None)
    if telescope_location is None and getattr(uvdata, 'telescope', None) is not None:
        telescope_location = getattr(uvdata.telescope, 'location', None)
    if telescope_location is None:
        raise AttributeError("UVData object lacks telescope location information")
    if hasattr(telescope_location, 'value'):
        telescope_location = telescope_location.value
    telescope_location = np.asarray(telescope_location)
    if telescope_location.dtype.names is not None:
        telescope_location = np.array([telescope_location['x'], telescope_location['y'], telescope_location['z']])

    rel_positions_target = None
    try:
        rel_positions_target = _get_relative_antenna_positions(uvdata)
    except AttributeError:
        pass

    if rel_positions_target is not None and rel_positions_target.shape[0] != n_itrf_antennas:
        message = (
            "Mismatch between antennas in current environment (%s) and correlator environment (%s)"
            % (n_itrf_antennas, rel_positions_target.shape[0])
        )
        logger.error(message)
        raise ValueError(message)

    # Relative positions for UVData are w.r.t. telescope_location
    relative_positions = abs_positions - telescope_location
    _set_relative_antenna_positions(uvdata, relative_positions)

    logger.info("Loaded dynamic antenna positions for %s antennas", n_itrf_antennas)
    logger.debug("Antenna positions sourced from local catalogue")
    return abs_positions


def _ensure_antenna_diameters(uvdata: UVData, diameter_m: float = 4.65) -> None:
    """Populate antenna diameter metadata for UVFITS/MS exports."""

    # Determine number of antennas from the modern telescope container if present
    nants: Optional[int] = None
    if hasattr(uvdata, "telescope") and getattr(uvdata.telescope, "antenna_numbers", None) is not None:
        nants = len(uvdata.telescope.antenna_numbers)
    elif getattr(uvdata, "antenna_numbers", None) is not None:
        nants = len(np.unique(uvdata.antenna_numbers))

    if nants is None:
        raise AttributeError("Unable to determine antenna count to assign diameters")

    diam_array = np.full(nants, diameter_m, dtype=np.float64)

    if hasattr(uvdata, "telescope") and hasattr(uvdata.telescope, "antenna_diameters"):
        uvdata.telescope.antenna_diameters = diam_array
    else:
        uvdata.antenna_diameters = diam_array


def get_blen(uvdata: UVData) -> np.ndarray:
    """
    Calculate baseline lengths using antenna positions in the UVData file.
    Based on dsacalib.uvh5_to_ms.get_blen.
    
    Parameters:
    -----------
    uvdata : UVData
        UVData object containing antenna information
        
    Returns:
    --------
    np.ndarray
        Array of baseline lengths (Nbls, 3)
    """
    rel_positions = _get_relative_antenna_positions(uvdata)
    blen = np.zeros((uvdata.Nbls, 3))
    for i, ant1 in enumerate(uvdata.ant_1_array[:uvdata.Nbls]):
        ant2 = uvdata.ant_2_array[i]
        blen[i, ...] = rel_positions[ant2, :] - rel_positions[ant1, :]
    return blen


def calc_uvw_blt(blen: np.ndarray, time_mjd: np.ndarray, frame: str,
                 ra: u.Quantity, dec: u.Quantity, obs: str = "OVRO_MMA") -> np.ndarray:
    """
    Vectorized uvw for baseline-time pairs using Astropy/ERFA.

    Falls back to casacore.measures if the fast path fails.
    """
    try:
        # Site EarthLocation (default OVRO)
        if obs == 'OVRO_MMA':
            site = EarthLocation.from_geodetic(lon=-118.2817 * u.deg, lat=37.2314 * u.deg, height=1222 * u.m)
        else:
            site = EarthLocation.from_geodetic(lon=-118.2817 * u.deg, lat=37.2314 * u.deg, height=1222 * u.m)

        # Rotation ECEF -> ENU at site
        lon = site.lon.to_value(u.rad)
        lat = site.lat.to_value(u.rad)
        slon, clon = np.sin(lon), np.cos(lon)
        slat, clat = np.sin(lat), np.cos(lat)
        R = np.array([
            [-slon,        clon,       0.0],
            [-slat*clon,  -slat*slon,  clat],
            [ clat*clon,   clat*slon,  slat],
        ], dtype=np.float64)

        blen = np.asarray(blen, dtype=np.float64)
        nblt = blen.shape[0]
        ben = (R @ blen.T).T  # (nblt, 3)
        E = ben[:, 0]
        N = ben[:, 1]
        U = ben[:, 2]

        # Time and hour angle
        t = Time(np.asarray(time_mjd, dtype=float), format='mjd', location=site)
        if frame.upper() == 'HADEC':
            H = u.Quantity(ra).to_value(u.rad) if isinstance(ra, u.Quantity) else np.asarray(ra, dtype=float)
            if np.ndim(H) == 0:
                H = np.full(nblt, float(H), dtype=float)
            d = u.Quantity(dec).to_value(u.rad) if isinstance(dec, u.Quantity) else np.asarray(dec, dtype=float)
            if np.ndim(d) == 0:
                d = np.full(nblt, float(d), dtype=float)
        else:
            lst = t.sidereal_time('apparent').to(u.rad).value
            ra_rad = u.Quantity(ra).to_value(u.rad) if isinstance(ra, u.Quantity) else np.asarray(ra, dtype=float)
            if np.ndim(ra_rad) == 0:
                ra_rad = np.full(nblt, float(ra_rad), dtype=float)
            d = u.Quantity(dec).to_value(u.rad) if isinstance(dec, u.Quantity) else np.asarray(dec, dtype=float)
            if np.ndim(d) == 0:
                d = np.full(nblt, float(d), dtype=float)
            H = lst - ra_rad
        H = (H + np.pi) % (2 * np.pi) - np.pi

        sH = np.sin(H); cH = np.cos(H)
        sd = np.sin(d); cd = np.cos(d)

        # Use non-conflicting names to avoid shadowing astropy.units as 'u'
        u_comp = E * sH + N * cH
        v_comp = -E * sd * cH + N * sd * sH + U * cd
        w_comp = E * cd * cH - N * cd * sH + U * sd

        return np.column_stack([u_comp, v_comp, w_comp])

    except Exception as exc:
        logger.debug("Astropy UVW failed (%s); falling back to CASA measures", exc)
        nblt = time_mjd.shape[0]
        buvw = np.zeros((nblt, 3))
        me = cc.measures()
        qa = cc.quanta()
        if obs is not None:
            me.doframe(me.observatory(obs))
        # Handle time-varying coords
        if hasattr(ra, 'ndim') and getattr(ra, 'ndim') and ra.ndim > 0:
            direction_set = False
        else:
            if (frame == 'HADEC') and (nblt > 1):
                raise TypeError('HA and DEC must be specified at each baseline-time in time_mjd.')
            me.doframe(me.direction(
                frame,
                qa.quantity(u.Quantity(ra).to_value(u.deg), 'deg'),
                qa.quantity(u.Quantity(dec).to_value(u.deg), 'deg')
            ))
            direction_set = True
        contains_nans = False
        tarr = np.asarray(time_mjd)
        for i in range(nblt):
            me.doframe(me.epoch('UTC', qa.quantity(float(tarr[i]), 'd')))
            if not direction_set:
                me.doframe(me.direction(
                    frame,
                    qa.quantity(u.Quantity(ra[i]).to_value(u.deg), 'deg'),
                    qa.quantity(u.Quantity(dec[i]).to_value(u.deg), 'deg')
                ))
            bl = me.baseline('itrf',
                             qa.quantity(float(blen[i, 0]), 'm'),
                             qa.quantity(float(blen[i, 1]), 'm'),
                             qa.quantity(float(blen[i, 2]), 'm'))
            try:
                buvw[i, :] = me.touvw(bl)[1]['value']
            except KeyError:
                contains_nans = True
                buvw[i, :] = np.nan
        if contains_nans:
            logger.warning('Some solutions not found for u, v, w coordinates')
        return buvw


def calc_uvw(blen: np.ndarray, time_mjd: np.ndarray, frame: str,
             ra: u.Quantity, dec: u.Quantity, obs: str = "OVRO_MMA") -> tuple:
    """
    Calculate uvw coordinates for baselines and times using CASA.
    
    Uses CASA to calculate the u,v,w coordinates of baselines towards a
    source or phase center at the specified times.
    Full implementation based on dsacalib.fringestopping.calc_uvw.
    
    Parameters:
    -----------
    blen : np.ndarray
        The ITRF coordinates of the baselines. Shape (nbaselines, 3), units of meters.
    time_mjd : np.ndarray or float
        Array of times in MJD or single time value
    frame : str
        The epoch of the source or phase-center, e.g. 'J2000' or 'HADEC'
    ra : astropy.Quantity
        The longitude of the source or phase-center
    dec : astropy.Quantity
        The latitude of the source or phase-center
    obs : str
        The name of the observatory in CASA (default: 'OVRO_MMA')
    
    Returns:
    --------
    tuple
        (bu, bv, bw) - The u,v,w values for each time and baseline, in meters.
        Shape (nbaselines, ntimes).
    """
    # Ensure time_mjd is array
    if not hasattr(time_mjd, '__len__'):
        time_mjd = np.array([time_mjd])
    else:
        time_mjd = np.asarray(time_mjd)
    
    nt = time_mjd.shape[0]
    nb = blen.shape[0]
    bu = np.zeros((nt, nb))
    bv = np.zeros((nt, nb))
    bw = np.zeros((nt, nb))
    
    # Define the reference frame
    me = cc.measures()
    qa = cc.quanta()
    if obs is not None:
        me.doframe(me.observatory(obs))
    
    # Handle time-varying coordinates
    if not isinstance(ra.ndim, float) and ra.ndim > 0:
        assert ra.ndim == 1
        assert ra.shape[0] == nt
        assert dec.shape[0] == nt
        direction_set = False
    else:
        if (frame == "HADEC") and (nt > 1):
            raise TypeError("HA and DEC must be specified at each time in time_mjd.")
        me.doframe(me.direction(
            frame,
            qa.quantity(ra.to_value(u.deg), "deg"),
            qa.quantity(dec.to_value(u.deg), "deg"),
        ))
        direction_set = True
    
    contains_nans = False
    
    for i in range(nt):
        me.doframe(me.epoch("UTC", qa.quantity(time_mjd[i], "d")))
        if not direction_set:
            me.doframe(me.direction(
                frame,
                qa.quantity(ra[i].to_value(u.deg), "deg"),
                qa.quantity(dec[i].to_value(u.deg), "deg"),
            ))
        for j in range(nb):
            bl = me.baseline(
                "itrf",
                qa.quantity(blen[j, 0], "m"),
                qa.quantity(blen[j, 1], "m"),
                qa.quantity(blen[j, 2], "m"),
            )
            # Get the uvw coordinates
            try:
                uvw = me.touvw(bl)[1]["value"]
                bu[i, j], bv[i, j], bw[i, j] = uvw[0], uvw[1], uvw[2]
            except KeyError:
                contains_nans = True
                bu[i, j], bv[i, j], bw[i, j] = np.nan, np.nan, np.nan
    
    if contains_nans:
        logger.warning("Some solutions not found for u, v, w coordinates")
    
    return bu.T, bv.T, bw.T


def calc_uvw_interpolate(blen: np.ndarray, tobs: Time, frame: str,
                        lon: u.Quantity, lat: u.Quantity) -> np.ndarray:
    """
    Calculate uvw coordinates with linear interpolation.
    Full implementation based on dsacalib.fringestopping.calc_uvw_interpolate.
    
    Parameters:
    -----------
    blen : np.ndarray
        Baseline lengths (Nbls, 3)
    tobs : astropy.time.Time
        Time array
    frame : str
        Coordinate frame
    lon : astropy.Quantity
        Longitude
    lat : astropy.Quantity
        Latitude
        
    Returns:
    --------
    np.ndarray
        Interpolated uvw coordinates
    """
    ntimebins = len(tobs)
    buvw_start_tuple = calc_uvw(blen, tobs.mjd[0], frame, lon, lat)
    buvw_start = np.array(buvw_start_tuple).T

    buvw_end_tuple = calc_uvw(blen, tobs.mjd[-1], frame, lon, lat)
    buvw_end = np.array(buvw_end_tuple).T

    buvw = (
        buvw_start +
        ((buvw_end-buvw_start) / (ntimebins - 1)) * np.arange(ntimebins)[:, np.newaxis, np.newaxis]
    )

    return buvw


def generate_phase_model_antbased(uvw: np.ndarray, uvw_m: np.ndarray, nbls: int, nts: int,
                                 lamb: u.Quantity, ant1: np.ndarray, ant2: np.ndarray) -> np.ndarray:
    """
    Generate phase model using antenna-based geometric delays.
    Full implementation based on dsacalib.uvh5_to_ms.generate_phase_model_antbased.
    
    This function generates a phase model to apply using antenna-based geometric delays.
    It calculates the geometric delay differences between antennas and applies them
    as phase corrections to the visibilities.
    
    Parameters:
    -----------
    uvw : np.ndarray
        uvw coordinates at each time bin (Nblts, 3)
    uvw_m : np.ndarray
        uvw coordinates at the meridian (Nbls, 3)
    nbls : int
        Number of unique baselines
    nts : int
        Number of unique times
    lamb : astropy.Quantity
        The observing wavelength of each channel
    ant1 : np.ndarray
        The antenna 1 indices in order
    ant2 : np.ndarray
        The antenna 2 indices in order
        
    Returns:
    --------
    np.ndarray
        The phase model to apply, shape (Nblts, Nfreqs, Npols)
    """
    # Need ant1 and ant2 to be passed here
    # Need to check that this gets the correct refidxs
    refant = ant1[0]
    refidxs = np.where(ant1 == refant)[0]

    antenna_order = list(ant2[refidxs])

    # Support both time-invariant and time-varying reference uvw_m inputs.
    # uvw has shape (Nblts, 3) and reshapes to (nts, nbls, 3).
    uvw_delays = uvw.reshape((nts, nbls, 3))
    antenna_w = uvw_delays[:, refidxs, -1]

    # If uvw_m is provided per-baseline only, broadcast to all times.
    if uvw_m.shape == (nbls, 3):
        antenna_w_m = uvw_m[refidxs, -1][np.newaxis, :]
        antenna_dw = antenna_w - antenna_w_m
    elif uvw_m.shape == (nts * nbls, 3):
        uvw_m_delays = uvw_m.reshape((nts, nbls, 3))
        antenna_w_m = uvw_m_delays[:, refidxs, -1]
        antenna_dw = antenna_w - antenna_w_m
    else:
        raise ValueError(
            f"Unexpected uvw_m shape {uvw_m.shape}; expected (nbls,3) or (nts*nbls,3)"
        )
    dw = np.zeros((nts, nbls))
    for i, a1 in enumerate(ant1):
        a2 = ant2[i]
        dw[:, i] = antenna_dw[:, antenna_order.index(a2)] - \
            antenna_dw[:, antenna_order.index(a1)]
    dw = dw.reshape(-1) * u.m
    phase_model = np.exp((2j * np.pi / lamb * dw[:, np.newaxis, np.newaxis]
                          ).to_value(u.dimensionless_unscaled))
    return phase_model


def generate_phase_model(uvw: np.ndarray, uvw_m: np.ndarray, nts: int,
                        lamb: u.Quantity) -> np.ndarray:
    """
    Generate phase model using baseline-based delays.
    Full implementation based on dsacalib.uvh5_to_ms.generate_phase_model.
    
    Parameters:
    -----------
    uvw : np.ndarray
        The uvw coordinates at each time bin (baseline, 3)
    uvw_m : np.ndarray
        The uvw coordinates at the meridian, (time, baseline, 3)
    nts : int
        The number of unique times
    lamb : astropy.Quantity
        The observing wavelength of each channel
        
    Returns:
    --------
    np.ndarray
        The phase model to apply
    """
    dw = (uvw[:, -1] - np.tile(uvw_m[np.newaxis, :, -1], (nts, 1, 1)).reshape(-1)) * u.m
    phase_model = np.exp((2j * np.pi / lamb * dw[:, np.newaxis, np.newaxis]
                          ).to_value(u.dimensionless_unscaled))
    return phase_model


def phase_visibilities(uvdata: UVData, phase_ra: u.Quantity, phase_dec: u.Quantity, 
                      fringestop: bool = True, refmjd: Optional[float] = None) -> None:
    """
    Phase a UVData instance using DSA-110 approach.
    Based on dsacalib.uvh5_to_ms.phase_visibilities.
    
    Parameters:
    -----------
    uvdata : UVData
        UVData object to phase
    phase_ra : astropy.Quantity
        RA to phase to
    phase_dec : astropy.Quantity
        DEC to phase to
    fringestop : bool
        Whether to apply fringestopping
    refmjd : float
        Reference MJD for fringestopping
    """
    logger.info("Phasing visibilities (fringestop=%s, refmjd=%s)", fringestop, refmjd)
    logger.debug(
        "Phase centre: RA=%.8f rad, Dec=%.8f rad",
        phase_ra.to_value(u.rad),
        phase_dec.to_value(u.rad),
    )
    
    # Get baseline lengths
    blen = get_blen(uvdata)
    lamb = c.c / (uvdata.freq_array * u.Hz)
    time = Time(uvdata.time_array, format='jd')
    
    if refmjd is None:
        refmjd = np.mean(time.mjd)
    
    # Get pointing declination
    pt_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad
    
    # Calculate meridian uvw coordinates referenced at each timestamp (HA=0 per time).
    # This accounts for raw correlator visibilities being referenced to the instantaneous meridian.
    blen_tiled_full = np.tile(blen[np.newaxis, :, :], (uvdata.Ntimes, 1, 1)).reshape(-1, 3)
    uvw_m = calc_uvw_blt(
        blen_tiled_full,
        Time(uvdata.time_array, format='jd').mjd,
        'HADEC',
        np.zeros(uvdata.Nblts) * u.rad,
        np.tile(pt_dec, uvdata.Nblts),
    )

    # Optional diagnostic: compare time-varying meridian uvw with a single-time reference
    # Enable via DEBUG log level or env DSA_UVW_DIAG=1
    try:
        import os as _os
        if logger.isEnabledFor(logging.DEBUG) or _os.getenv('DSA_UVW_DIAG') == '1':
            if refmjd is None:
                refmjd_chk = float(Time(np.mean(uvdata.time_array), format='jd').mjd)
            else:
                refmjd_chk = refmjd
            uvw_ref = calc_uvw_blt(
                blen, np.tile(refmjd_chk, (uvdata.Nbls)), 'HADEC',
        np.zeros(uvdata.Nbls) * u.rad, np.tile(pt_dec, (uvdata.Nbls))
    )
            uvw_m_t = uvw_m.reshape(uvdata.Ntimes, uvdata.Nbls, 3)
            uvw_ref_t = np.tile(uvw_ref[np.newaxis, :, :], (uvdata.Ntimes, 1, 1))
            delta = np.abs(uvw_m_t - uvw_ref_t)
            logger.debug(
                "Meridian uvw diag | max=%.3f m, median=%.3f m",
                float(np.nanmax(delta)), float(np.nanmedian(delta))
            )
    except Exception:
        # Never fail phasing due to diagnostics
        pass
    
    if fringestop:
        # Calculate uvw coordinates for phasing
        blen_tiled = np.tile(blen[np.newaxis, :, :], (uvdata.Ntimes, 1, 1)).reshape(-1, 3)
        uvw = calc_uvw_blt(
            blen_tiled, time.mjd, 'J2000', phase_ra, phase_dec
        )
        
        # Generate and apply phase model
        phase_model = generate_phase_model_antbased(
            uvw, uvw_m, uvdata.Nbls, uvdata.Ntimes, lamb, 
            uvdata.ant_1_array[:uvdata.Nbls], uvdata.ant_2_array[:uvdata.Nbls]
        )
        phase_model = phase_model.reshape((uvdata.Nblts, uvdata.Nspws, uvdata.Nfreqs))
        if uvdata.Nspws == 1:
            phase_model = phase_model[:, 0, :]

        if uvdata.data_array.ndim == 4:
            if uvdata.Nspws == 1:
                uvdata.data_array /= phase_model[:, np.newaxis, :, np.newaxis]
            else:
                uvdata.data_array /= phase_model[..., np.newaxis]
        elif uvdata.data_array.ndim == 3:
            uvdata.data_array /= phase_model[:, :, np.newaxis] if phase_model.ndim == 2 else phase_model
        else:
            raise ValueError(
                f"Unexpected data_array dimensions {uvdata.data_array.shape}"
            )
    else:
        # Simple phasing without fringestopping
        uvw = calc_uvw_blt(
            blen, np.tile(np.mean(time.mjd), (uvdata.Nbls)), 'J2000',
            np.tile(phase_ra, (uvdata.Nbls)), np.tile(phase_dec, (uvdata.Nbls))
        )
        phase_model = generate_phase_model_antbased(
            uvw, uvw_m, uvdata.Nbls, 1, lamb,
            uvdata.ant_1_array[:uvdata.Nbls], uvdata.ant_2_array[:uvdata.Nbls]
        )
        phase_model = phase_model.reshape((uvdata.Nblts, uvdata.Nspws, uvdata.Nfreqs))
        if uvdata.Nspws == 1:
            phase_model = phase_model[:, 0, :]

        if uvdata.data_array.ndim == 4:
            if uvdata.Nspws == 1:
                uvdata.data_array /= phase_model[:, np.newaxis, :, np.newaxis]
            else:
                uvdata.data_array /= phase_model[..., np.newaxis]
        elif uvdata.data_array.ndim == 3:
            uvdata.data_array /= phase_model[:, :, np.newaxis] if phase_model.ndim == 2 else phase_model
        else:
            raise ValueError(
                f"Unexpected data_array dimensions {uvdata.data_array.shape}"
            )
        uvw = np.tile(uvw.reshape((1, uvdata.Nbls, 3)),
                      (1, uvdata.Ntimes, 1)).reshape((uvdata.Nblts, 3))
    
    # Update uvw array and phase information
    uvdata.uvw_array = uvw
    uvdata.phase_type = 'phased'
    uvdata.phase_center_dec = phase_dec.to_value(u.rad)
    uvdata.phase_center_ra = phase_ra.to_value(u.rad)
    uvdata.phase_center_epoch = 2000.
    uvdata.phase_center_frame = 'icrs'
    
    try:
        uvdata._set_app_coords_helper()
    except AttributeError:
        pass
    
    logger.info("Phasing complete")


def fix_descending_missing_freqs(uvdata: UVData) -> None:
    """
    Fix descending frequency arrays and fill missing channels.
    Based on dsacalib.uvh5_to_ms.fix_descending_missing_freqs.
    
    Parameters:
    -----------
    uvdata : UVData
        UVData object to fix
    """
    logger.info("Fixing frequency arrays")
    
    # Look for missing channels
    freq = uvdata.freq_array.squeeze()
    
    # Check if frequencies are ascending or descending
    ascending = np.median(np.diff(freq)) > 0
    if ascending:
        if not np.all(np.diff(freq) >= -1e-12):
            raise ValueError("Frequency axis is neither strictly ascending nor descending")
    else:
        if not np.all(np.diff(freq) <= 1e-12):
            raise ValueError("Frequency axis is neither strictly ascending nor descending")
        # Flip descending arrays
        uvdata.freq_array = np.flip(uvdata.freq_array, axis=-1)

        if uvdata.data_array.ndim == 4:
            flip_axis = -2  # frequency axis
            uvdata.data_array = np.flip(uvdata.data_array, axis=flip_axis)
            uvdata.nsample_array = np.flip(uvdata.nsample_array, axis=flip_axis)
            uvdata.flag_array = np.flip(uvdata.flag_array, axis=flip_axis)
        elif uvdata.data_array.ndim == 3:
            flip_axis = -2  # frequency axis for (Nblts, Nfreqs, Npols)
            uvdata.data_array = np.flip(uvdata.data_array, axis=flip_axis)
            uvdata.nsample_array = np.flip(uvdata.nsample_array, axis=flip_axis)
            uvdata.flag_array = np.flip(uvdata.flag_array, axis=flip_axis)
        else:
            raise ValueError(
                f"Unsupported data_array dimensionality {uvdata.data_array.shape}"
            )
        freq = uvdata.freq_array.squeeze()
    
    # Update channel width (store as absolute value)
    uvdata.channel_width = np.abs(uvdata.channel_width)
    channel_width_vals = np.atleast_1d(np.squeeze(uvdata.channel_width))
    if channel_width_vals.size == 0:
        raise ValueError("channel_width has no entries after squeezing")

    if channel_width_vals.size == 1:
        channel_width_cmp = channel_width_vals[0]
    elif channel_width_vals.size == freq.size:
        channel_width_cmp = channel_width_vals[:-1]
    elif channel_width_vals.size == np.diff(freq).size:
        channel_width_cmp = channel_width_vals
    else:
        raise ValueError(
            f"Unexpected channel_width shape {uvdata.channel_width.shape}"
        )

    diff_freq = np.diff(freq)

    # Check for missing channels
    if not np.all(np.isclose(diff_freq, channel_width_cmp, atol=1e-5)):
        logger.info("Filling missing frequency channels")
        # There are missing channels!
        channel_width_scalar = float(channel_width_vals[0])
        nfreq = int(np.rint(np.abs(freq[-1] - freq[0]) / channel_width_scalar + 1))
        freq_out = freq[0] + np.arange(nfreq) * channel_width_scalar
        existing_idxs = np.rint((freq - freq[0]) / channel_width_scalar).astype(int)
        
        # Create output arrays
        if uvdata.data_array.ndim == 4:
            data_out = np.zeros((uvdata.Nblts, uvdata.Nspws, nfreq, uvdata.Npols),
                               dtype=uvdata.data_array.dtype)
            nsample_out = np.zeros((uvdata.Nblts, uvdata.Nspws, nfreq, uvdata.Npols),
                                 dtype=uvdata.nsample_array.dtype)
            flag_out = np.zeros((uvdata.Nblts, uvdata.Nspws, nfreq, uvdata.Npols),
                               dtype=uvdata.flag_array.dtype)
            data_out[:, :, existing_idxs, :] = uvdata.data_array
            nsample_out[:, :, existing_idxs, :] = uvdata.nsample_array
            flag_out[:, :, existing_idxs, :] = uvdata.flag_array
        elif uvdata.data_array.ndim == 3:
            data_out = np.zeros((uvdata.Nblts, nfreq, uvdata.Npols),
                               dtype=uvdata.data_array.dtype)
            nsample_out = np.zeros((uvdata.Nblts, nfreq, uvdata.Npols),
                                 dtype=uvdata.nsample_array.dtype)
            flag_out = np.zeros((uvdata.Nblts, nfreq, uvdata.Npols),
                               dtype=uvdata.flag_array.dtype)
            data_out[:, existing_idxs, :] = uvdata.data_array
            nsample_out[:, existing_idxs, :] = uvdata.nsample_array
            flag_out[:, existing_idxs, :] = uvdata.flag_array
        else:
            raise ValueError(
                f"Unsupported data_array dimensionality {uvdata.data_array.shape}"
            )
        
        # Update UVData object
        freq_array_ndim = uvdata.freq_array.ndim
        uvdata.Nfreqs = nfreq
        uvdata.freq_array = freq_out[np.newaxis, :] if freq_array_ndim == 2 else freq_out
        uvdata.data_array = data_out
        uvdata.nsample_array = nsample_out
        uvdata.flag_array = flag_out
        if freq_array_ndim == 1:
            uvdata.channel_width = np.full(nfreq, channel_width_scalar, dtype=channel_width_vals.dtype)
        else:
            uvdata.channel_width = np.full((uvdata.Nspws, nfreq), channel_width_scalar, dtype=channel_width_vals.dtype)
    
    # Final sanity checks: ascending frequency and positive channel width
    freq_final = uvdata.freq_array.squeeze()
    if not np.all(np.diff(freq_final) > -1e-12):
        raise ValueError("Frequency axis not strictly ascending after processing")
    chw = np.atleast_1d(np.squeeze(uvdata.channel_width))
    if not np.all(chw > 0):
        raise ValueError("channel_width must be positive after processing")
    
    logger.info("Frequency array processing complete")


def write_uvdata_to_ms(
        uvdata: UVData,
        msname: str,
        antenna_positions: np.ndarray,
        scratch_dir: Optional[str] = None,
) -> None:
    """
    Write UVData object to CASA Measurement Set using UVFITS as intermediate format.
    
    Parameters:
    -----------
    uvdata : UVData
        UVData object to convert
    msname : str
        Name of the measurement set (without .ms extension)
    antenna_positions : np.ndarray
        Antenna positions in ITRF coordinates
    """
    ms_dir = Path(msname).with_suffix('.ms')
    logger.info("Converting to Measurement Set: %s", ms_dir)

    scratch_ms_dir: Path
    fits_path: Path
    if scratch_dir is not None:
        scratch_base = Path(scratch_dir).expanduser().resolve()
        scratch_base.mkdir(parents=True, exist_ok=True)
        scratch_ms_dir = scratch_base / ms_dir.name
        fits_path = scratch_base / f"{ms_dir.stem}.fits"
    else:
        scratch_ms_dir = ms_dir
        fits_path = Path(f'{msname}.fits')

    if fits_path.exists():
        fits_path.unlink()
    if scratch_ms_dir.exists():
        shutil.rmtree(scratch_ms_dir)

    if scratch_dir is not None and scratch_ms_dir != ms_dir:
        scratch_ms_dir.parent.mkdir(parents=True, exist_ok=True)

    # Write UVData to UVFITS format
    logger.info("Writing UVFITS intermediate file")
    t0 = time.perf_counter()
    uvdata.write_uvfits(
        str(fits_path),
        write_lst=True,
        use_miriad_convention=True,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
        run_check=False,
        check_extra=False,
        check_autos=False
    )
    t1 = time.perf_counter()
    logger.info("UVFITS write completed in %.2f s", t1 - t0)
    
    # Convert UVFITS to Measurement Set using CASA
    logger.info("Converting UVFITS to Measurement Set")
    t2 = time.perf_counter()
    importuvfits(str(fits_path), str(scratch_ms_dir))
    t3 = time.perf_counter()
    logger.info("CASA importuvfits completed in %.2f s", t3 - t2)
    
    # Update antenna positions in the measurement set
    logger.info("Updating antenna positions in Measurement Set")
    with table(str(scratch_ms_dir / 'ANTENNA'), readonly=False) as tb:
        # Ensure we have the right number of antennas
        n_ants_ms = tb.nrows()
        if n_ants_ms == antenna_positions.shape[0]:
            tb.putcol('POSITION', antenna_positions)
        else:
            logger.warning(
                "Antenna count mismatch. MS has %s, positions provided for %s",
                n_ants_ms,
                antenna_positions.shape[0]
            )
    
    # Add imaging columns to the measurement set
    logger.info("Adding imaging columns to Measurement Set")
    t4 = time.perf_counter()
    addImagingColumns(str(scratch_ms_dir))
    t5 = time.perf_counter()
    logger.info("addImagingColumns completed in %.2f s", t5 - t4)
    
    if scratch_dir is not None and scratch_ms_dir != ms_dir:
        if ms_dir.exists():
            shutil.rmtree(ms_dir)
        shutil.move(str(scratch_ms_dir), str(ms_dir))
    
    # Clean up intermediate UVFITS file
    fits_path.unlink(missing_ok=True)
    
    # --- Post-import fixes ---
    # 1. Set FIELD table to the actual phase center
    with table(str(scratch_ms_dir / 'FIELD'), readonly=False) as tb:
        phase_dir = np.array([[[uvdata.phase_center_ra, uvdata.phase_center_dec]]], dtype=np.float64)
        tb.putcol("PHASE_DIR", phase_dir)
        tb.putcol("DELAY_DIR", phase_dir)
        tb.putcol("REFERENCE_DIR", phase_dir)
    logger.info("Updated FIELD table with actual phase center.")

    # 2. Recompute UVW coordinates against the updated geometry
    with table(str(scratch_ms_dir), readonly=False) as tb:
        blen = get_blen(uvdata)
        times_jd = tb.getcol('TIME')
        times_mjd = Time(times_jd, format='jd').mjd
        
        blen_tiled = np.tile(blen[np.newaxis, :, :], (uvdata.Ntimes, 1, 1)).reshape(-1, 3)
        
        new_uvw = calc_uvw_blt(
            blen_tiled,
            times_mjd,
            'J2000',
            uvdata.phase_center_ra * u.rad,
            uvdata.phase_center_dec * u.rad
        )
        tb.putcol('UVW', new_uvw)
    logger.info("Recomputed UVW coordinates.")
    
    logger.info("Successfully created %s", ms_dir)


def amplitude_sky_model(source_ra: u.Quantity, source_dec: u.Quantity, flux_Jy: float,
                       lst: np.ndarray, pt_dec: u.Quantity, fobs: np.ndarray,
                       dish_dia: float = 4.65, spind: float = 0.7) -> np.ndarray:
    """
    Generate amplitude sky model for primary beam response.
    Full implementation based on dsacalib.fringestopping.amplitude_sky_model.
    
    Computes the amplitude sky model for a single source due to the primary
    beam response of an antenna.
    
    Parameters:
    -----------
    source_ra : astropy.Quantity
        Source right ascension
    source_dec : astropy.Quantity
        Source declination
    flux_Jy : float
        Source flux in Jy
    lst : np.ndarray
        Local sidereal time array (antenna RA pointing)
    pt_dec : astropy.Quantity
        Pointing declination
    fobs : np.ndarray
        Observed frequencies in GHz
    dish_dia : float
        Dish diameter in meters (default: 4.65)
    spind : float
        Spectral index of the source (default: 0.7)
        
    Returns:
    --------
    np.ndarray
        Amplitude model array with spectral index and primary beam response
    """
    # Apply spectral index
    spectral_factor = (fobs / 1.4) ** (-spind)
    
    # Calculate primary beam response
    pb_response = pb_resp(
        lst,
        pt_dec.to_value(u.rad),
        source_ra.to_value(u.rad),
        source_dec.to_value(u.rad),
        fobs,
        dish_dia
    )
    
    # Combine flux, spectral index, and primary beam response
    model = flux_Jy * spectral_factor * pb_response
    
    return model


def pb_resp_uniform_ill(ant_ra: np.ndarray, ant_dec: float, src_ra: float, src_dec: float,
                       freq: np.ndarray, dish_dia: float = 4.9) -> np.ndarray:
    """
    Compute primary beam response with uniform illumination.
    Full implementation based on dsacalib.fringestopping.pb_resp_uniform_ill.
    
    Assumes uniform illumination of the disk. Returns a value between 0 and 1
    for each value passed in ant_ra.
    
    Parameters:
    -----------
    ant_ra : np.ndarray
        The antenna right ascension pointing in radians
    ant_dec : float
        The antenna declination pointing in radians
    src_ra : float
        The source right ascension in radians
    src_dec : float
        The source declination in radians
    freq : np.ndarray
        The frequency of each channel in GHz
    dish_dia : float
        The dish diameter in meters (default: 4.9)
        
    Returns:
    --------
    np.ndarray
        The primary beam response, dimensions (ant_ra, freq)
    """
    dis = angular_separation(ant_ra, ant_dec, src_ra, src_dec)
    lam = 0.299792458 / freq
    pb = (
        2.0
        * j1(np.pi * dis[:, np.newaxis] * dish_dia / lam)
        / (np.pi * dis[:, np.newaxis] * dish_dia / lam)
    ) ** 4
    return pb


def pb_resp(ant_ra: np.ndarray, ant_dec: float, src_ra: float, src_dec: float, 
            freq: np.ndarray, dish_dia: float = 4.7) -> np.ndarray:
    """
    Compute primary beam response with tapered illumination.
    Full implementation based on dsacalib.fringestopping.pb_resp.
    
    Assumes tapered illumination of the disk. Returns a value between 0 and 1
    for each value passed in ant_ra.
    
    Parameters:
    -----------
    ant_ra : np.ndarray
        The antenna right ascension pointing in radians
    ant_dec : float
        The antenna declination pointing in radians
    src_ra : float
        The source right ascension in radians
    src_dec : float
        The source declination in radians
    freq : np.ndarray
        The frequency of each channel in GHz
    dish_dia : float
        The dish diameter in meters (default: 4.7)
        
    Returns:
    --------
    np.ndarray
        The primary beam response, dimensions (ant_ra, freq)
    """
    dis = np.array(angular_separation(ant_ra, ant_dec, src_ra, src_dec))
    if dis.ndim > 0 and dis.shape[0] > 1:
        dis = dis[:, np.newaxis]  # prepare for broadcasting

    lam = 0.299792458 / freq
    arg = 1.2 * dis * dish_dia / lam
    pb = (np.cos(np.pi * arg) / (1 - 4 * arg**2)) ** 4
    return pb


def set_model_column(msname: str, uvdata: UVData, pt_dec: u.Quantity,
                    ra: u.Quantity, dec: u.Quantity,
                    flux_Jy: Union[float, None] = None) -> None:
    """
    Set the MODEL_DATA column in the measurement set using DSA-110 approach.
    Based on dsacalib.uvh5_to_ms.set_ms_model_column.
    
    Parameters:
    -----------
    msname : str
        Name of the measurement set (without .ms extension)
    uvdata : UVData
        UVData object containing visibility data
    pt_dec : astropy.Quantity
        Pointing declination
    ra : astropy.Quantity
        Phase center RA
    dec : astropy.Quantity
        Phase center DEC
    flux_Jy : float, optional
        Source flux in Jy for primary beam model
    """
    logger.info("Setting MODEL_DATA column")
    
    if flux_Jy is not None:
        logger.debug("Applying flux-weighted model: flux=%s Jy", flux_Jy)
        # Generate primary beam model
        fobs = uvdata.freq_array.squeeze() / 1e9  # Convert to GHz
        lst = uvdata.lst_array
        model = amplitude_sky_model(ra, dec, flux_Jy, lst, pt_dec, fobs)
        model = np.tile(model[:, :, np.newaxis], (1, 1, uvdata.Npols)).astype(np.complex64)
    else:
        logger.debug("No flux provided; writing unity model")
        # Simple unity response model
        model = np.ones((uvdata.Nblts, uvdata.Nfreqs, uvdata.Npols), dtype=np.complex64)
    
    # Write model data to the measurement set
    with table(f'{msname}.ms', readonly=False) as tb:
        # Get data shape; MS DATA is typically (npol, nchan, nrow)
        data_shape = tb.getcol('DATA').shape
        # model is (nrow, nchan, npol) -> transpose to (npol, nchan, nrow)
        model_transposed = np.transpose(model, (2, 1, 0))
        
        if model_transposed.shape != data_shape:
            logger.warning(
                "Model shape %s does not match DATA shape %s. Skipping MODEL_DATA write.",
                model_transposed.shape, data_shape
            )
        else:
            tb.putcol('MODEL_DATA', model_transposed)
        
        # Copy DATA to CORRECTED_DATA if column exists and is all zeros
        if 'CORRECTED_DATA' in tb.colnames():
            try:
                corr = tb.getcol('CORRECTED_DATA')
                if not np.any(corr):
                    tb.putcol('CORRECTED_DATA', tb.getcol('DATA'))
            except Exception:
                pass
        
        # 3. Reconstruct WEIGHT_SPECTRUM
        if 'WEIGHT_SPECTRUM' in tb.colnames():
            flags = tb.getcol('FLAG')
            weights = tb.getcol('WEIGHT')
            ncorr = weights.shape[0]
            nchan = flags.shape[0]
            
            wspec = np.repeat(weights[np.newaxis, :, :], nchan, axis=0)
            wspec[flags] = 0.0
            tb.putcol("WEIGHT_SPECTRUM", wspec.astype(np.float32))
            logger.info("Reconstructed WEIGHT_SPECTRUM column.")
    
    logger.info("MODEL_DATA column set successfully")


def convert_subband_groups_to_ms(input_dir: str, output_dir: str, start_time: str, end_time: str,
                                 antenna_list: Optional[List[str]] = None,
                                 duration: Optional[float] = None,
                                 refmjd: Optional[float] = None,
                                 flux: Optional[float] = None,
                                 fringestop: bool = True,
                                 phase_ra: Optional[u.Quantity] = None,
                                 phase_dec: Optional[u.Quantity] = None,
                                 checkpoint_dir: Optional[str] = None,
                                 scratch_dir: Optional[str] = None,
                                 direct_ms: bool = False) -> None:
    """
    Main function to convert DSA-110 subband file groups to CASA Measurement Sets.
    
    Parameters:
    -----------
    input_dir : str
        Directory containing HDF5 subband files
    output_dir : str
        Directory to write Measurement Sets
    start_time : str
        Start time in 'YYYY-MM-DD HH:MM:SS' format
    end_time : str
        End time in 'YYYY-MM-DD HH:MM:SS' format
    antenna_list : list, optional
        List of antenna names to include
    duration : float, optional
        Duration in minutes to extract from each file
    refmjd : float, optional
        Reference MJD for fringestopping geometric delay calculations
        (default: 59215.0)
    flux : float, optional
        Calibrator flux in Jy for MODEL_DATA primary beam model (default: None)
    fringestop : bool, optional
        Whether to apply fringestopping (default: True)
    phase_ra : astropy.Quantity, optional
        Phase center RA in radians (default: None, uses meridian)
    phase_dec : astropy.Quantity, optional
        Phase center Dec in radians (default: None, uses pointing declination)
    checkpoint_dir : str, optional
        Persistent directory to store/load checkpoints. When omitted and scratch_dir is
        provided, checkpoints are staged under the scratch directory.
    scratch_dir : str, optional
        Directory to stage temporary UVFITS/Measurement Sets before syncing to output.
    """
    logger.info("=" * 60)
    logger.info("DSA-110 Subband to CASA Measurement Set Converter")
    logger.info("=" * 60)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Output directory: %s", output_dir)
    
    # Find subband file groups within time range
    subband_groups = find_subband_groups(input_dir, start_time, end_time)
    
    if not subband_groups:
        logger.warning("No subband file groups found within the specified time range")
        return
    
    # Convert duration to astropy Quantity if provided
    dt = None
    if duration is not None:
        dt = duration * u.minute
    
    checkpoint_dir_path: Optional[str] = None
    scratch_dir_path: Optional[str] = None
    if scratch_dir is not None:
        scratch_dir_path = os.path.abspath(scratch_dir)
        os.makedirs(scratch_dir_path, exist_ok=True)

    if checkpoint_dir is not None:
        checkpoint_dir_path = os.path.abspath(checkpoint_dir)
        os.makedirs(checkpoint_dir_path, exist_ok=True)
    elif scratch_dir_path is not None:
        checkpoint_dir_path = os.path.join(scratch_dir_path, "checkpoints")
        os.makedirs(checkpoint_dir_path, exist_ok=True)

    # Process each subband group
    for i, subband_files in enumerate(subband_groups):
        logger.info(
            "Processing group %s/%s: %s subband files",
            i + 1,
            len(subband_groups),
            len(subband_files)
        )
        logger.debug("Group files: %s", [os.path.basename(f) for f in subband_files])

        def _subband_sort_key(path: str) -> Tuple[int, str]:
            """Sort by numeric subband suffix, then full path for stability."""
            base = os.path.splitext(os.path.basename(path))[0]
            if '_sb' in base:
                try:
                    sb_idx = int(base.split('_sb', maxsplit=1)[1])
                except ValueError:
                    sb_idx = -1
            else:
                sb_idx = -1
            return sb_idx, base

        subband_files = sorted(subband_files, key=_subband_sort_key)
        
        try:
            first_file = subband_files[0]
            base_name = os.path.splitext(os.path.basename(first_file))[0].split('_sb')[0]
            msname = os.path.join(output_dir, base_name)

            if direct_ms:
                group_start = time.perf_counter()
                total_subbands = len(subband_files)
                t_load0 = time.perf_counter()
                uvdata = _load_subband_uvdata(first_file, antenna_list)
                t_load1 = time.perf_counter()
                first_sb_idx = _extract_subband_index(os.path.basename(first_file))
                logger.info(
                    "Loaded subband sb%02d (%d/%d) in %.2f s",
                    first_sb_idx if first_sb_idx is not None else -1,
                    1,
                    total_subbands,
                    t_load1 - t_load0,
                )

                # Log correlator provenance if present, with normalized path & existence flag
                try:
                    ek = getattr(uvdata, 'extra_keywords', {}) or {}
                    if 'fs_table' in ek or 'applied_delays_ns' in ek:
                        fs_table_val = str(ek.get('fs_table', 'None'))
                        fs_norm = os.path.normpath(fs_table_val) if fs_table_val not in ('None', '', 'null') else None
                        fs_exists = os.path.exists(fs_norm) if fs_norm else False
                        fs_disp = os.path.basename(fs_norm) if fs_norm else fs_table_val
                        missing_note = '' if fs_exists else ' (missing locally)'
                        logger.info(
                            "Correlator provenance: fs_table=%s%s delays_present=%s",
                            fs_disp, missing_note, 'applied_delays_ns' in ek
                        )
                except Exception:
                    pass

                nblts = uvdata.Nblts
                nfreq_per_subband = uvdata.Nfreqs
                npols = uvdata.Npols
                nfreq_total = nfreq_per_subband * total_subbands

                # Allocate arrays for all subbands in one shot and copy sb00 contents in place.
                data_dtype = uvdata.data_array.dtype
                flag_dtype = uvdata.flag_array.dtype
                nsample_dtype = uvdata.nsample_array.dtype

                combined_data = np.empty((nblts, nfreq_total, npols), dtype=data_dtype)
                combined_flag = np.empty((nblts, nfreq_total, npols), dtype=flag_dtype)
                combined_nsample = np.empty((nblts, nfreq_total, npols), dtype=nsample_dtype)

                combined_freq = np.empty((uvdata.freq_array.shape[0], nfreq_total), dtype=uvdata.freq_array.dtype)
                if uvdata.channel_width.ndim == 2:
                    combined_chan_width = np.empty((uvdata.channel_width.shape[0], nfreq_total), dtype=uvdata.channel_width.dtype)
                else:
                    combined_chan_width = np.empty(nfreq_total, dtype=uvdata.channel_width.dtype)

                combined_data[:, :nfreq_per_subband, :] = uvdata.data_array
                combined_flag[:, :nfreq_per_subband, :] = uvdata.flag_array
                combined_nsample[:, :nfreq_per_subband, :] = uvdata.nsample_array
                combined_freq[:, :nfreq_per_subband] = uvdata.freq_array
                if uvdata.channel_width.ndim == 2:
                    combined_chan_width[:, :nfreq_per_subband] = uvdata.channel_width
                else:
                    combined_chan_width[:nfreq_per_subband] = uvdata.channel_width

                freq_offset = nfreq_per_subband

                reference_ant1 = uvdata.ant_1_array.copy()
                reference_ant2 = uvdata.ant_2_array.copy()
                reference_time = uvdata.time_array.copy()
                reference_uvw = uvdata.uvw_array.copy()
                reference_lst = uvdata.lst_array.copy()

                for sb_count, sb_path in enumerate(subband_files[1:], start=2):
                    t_load_sub = time.perf_counter()
                    uv_next = _load_subband_uvdata(sb_path, antenna_list)
                    t_load_sub_done = time.perf_counter()
                    sb_idx = _extract_subband_index(os.path.basename(sb_path))
                    logger.info(
                        "Loaded subband sb%02d (%d/%d) in %.2f s",
                        sb_idx if sb_idx is not None else -1,
                        sb_count,
                        total_subbands,
                        t_load_sub_done - t_load_sub,
                    )

                    if uv_next.Nblts != nblts or uv_next.Nfreqs != nfreq_per_subband or uv_next.Npols != npols:
                        raise ValueError(
                            f"Subband dimensions mismatch for {os.path.basename(sb_path)}"
                        )

                    if not (np.array_equal(reference_ant1, uv_next.ant_1_array) and
                            np.array_equal(reference_ant2, uv_next.ant_2_array)):
                        raise ValueError("Antenna ordering differs between subbands")
                    if not np.allclose(reference_time, uv_next.time_array):
                        raise ValueError("Time arrays differ between subbands")
                    if not np.allclose(reference_uvw, uv_next.uvw_array):
                        raise ValueError("UVW arrays differ between subbands")
                    if not np.allclose(reference_lst, uv_next.lst_array):
                        raise ValueError("LST arrays differ between subbands")

                    combined_data[:, freq_offset:freq_offset + nfreq_per_subband, :] = uv_next.data_array
                    combined_flag[:, freq_offset:freq_offset + nfreq_per_subband, :] = uv_next.flag_array
                    combined_nsample[:, freq_offset:freq_offset + nfreq_per_subband, :] = uv_next.nsample_array
                    combined_freq[:, freq_offset:freq_offset + nfreq_per_subband] = uv_next.freq_array
                    if uv_next.channel_width.ndim == 2:
                        combined_chan_width[:, freq_offset:freq_offset + nfreq_per_subband] = uv_next.channel_width
                    else:
                        combined_chan_width[freq_offset:freq_offset + nfreq_per_subband] = uv_next.channel_width

                    freq_offset += nfreq_per_subband
                    del uv_next

                # Replace the UVData arrays with the combined views.
                uvdata.data_array = combined_data[:, np.newaxis, :, :]
                uvdata.flag_array = combined_flag[:, np.newaxis, :, :]
                uvdata.nsample_array = combined_nsample[:, np.newaxis, :, :]
                uvdata.freq_array = combined_freq
                uvdata.channel_width = combined_chan_width
                uvdata.Nfreqs = nfreq_total

                # Ensure core metadata arrays are float64 once at the end.
                _coerce_uvdata_float64(uvdata)

                pt_dec = uvdata.extra_keywords.get('phase_center_dec', 0.0) * u.rad
                if refmjd is not None:
                    group_refmjd = refmjd
                else:
                    group_refmjd = float(Time(np.mean(uvdata.time_array), format='jd').mjd)

                if phase_ra is not None and phase_dec is not None:
                    group_phase_ra = phase_ra
                    group_phase_dec = phase_dec
                else:
                    phase_time = Time(np.mean(uvdata.time_array), format='jd')
                    group_phase_ra, group_phase_dec = get_meridian_coords(pt_dec, phase_time.mjd)

                if dt is not None:
                    extract_times_dsacalib(uvdata, group_phase_ra, dt)

                set_antenna_positions(uvdata)
                _ensure_antenna_diameters(uvdata)

                if uvdata.phase_center_catalog:
                    for idx, (cat_id, entry) in enumerate(uvdata.phase_center_catalog.items()):
                        entry["cat_type"] = "sidereal"
                        entry["cat_frame"] = "icrs"
                        entry["cat_epoch"] = 2000.0
                        entry.setdefault("cat_name", f"phase{idx}")

                t_phase0 = time.perf_counter()
                phase_visibilities(uvdata, group_phase_ra, group_phase_dec, fringestop=fringestop,
                                  refmjd=group_refmjd)
                t_phase1 = time.perf_counter()
                logger.info("Phasing complete in %.2f s", t_phase1 - t_phase0)

                t_freq0 = time.perf_counter()
                fix_descending_missing_freqs(uvdata)
                t_freq1 = time.perf_counter()
                logger.info("Frequency fixes completed in %.2f s", t_freq1 - t_freq0)

                try:
                    uvdata.check(check_extra=False)
                except Exception as e:
                    logger.warning("UVData validation (direct) reported issues: %s", e)

                if checkpoint_path is not None:
                    logger.info("Writing checkpoint to %s", checkpoint_path)
                    uvdata.write_uvh5(
                        checkpoint_path,
                        run_check=False,
                        fix_autos=False,
                        check_extra=False,
                    )

                ms_full_path = f"{msname}.ms"
                if os.path.exists(ms_full_path):
                    shutil.rmtree(ms_full_path)
                t_ms0 = time.perf_counter()
                uvdata.write_ms(
                    ms_full_path,
                    clobber=True,
                    run_check=False,
                    check_extra=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                    check_autos=False,
                    fix_autos=False,
                )
                t_ms1 = time.perf_counter()
                logger.info("Direct write via pyuvdata completed in %.2f s", t_ms1 - t_ms0)

                try:
                    addImagingColumns(ms_full_path)
                except Exception:
                    pass

                if flux is not None:
                    set_model_column(msname, uvdata, pt_dec, group_phase_ra, group_phase_dec, flux_Jy=flux)

                group_end = time.perf_counter()
                logger.info("Successfully converted group to %s.ms in %.2f s", msname, group_end - group_start)
                continue

            group_start = time.perf_counter()
            first_file = subband_files[0]
            base_name = os.path.splitext(os.path.basename(first_file))[0].split('_sb')[0]
            msname = os.path.join(output_dir, base_name)
            checkpoint_path = None
            if checkpoint_dir_path is not None:
                checkpoint_path = os.path.join(checkpoint_dir_path, f"{base_name}.checkpoint.uvh5")

            group_scratch_dir: Optional[str] = None
            if scratch_dir_path is not None:
                group_scratch_dir = os.path.join(scratch_dir_path, base_name)
                os.makedirs(group_scratch_dir, exist_ok=True)

            # Load and combine subband files manually so we can fix dtypes
            uvdata: Optional[UVData] = None
            loaded_from_checkpoint = False

            if checkpoint_path is not None and os.path.exists(checkpoint_path):
                logger.info("Loading checkpointed UVData from %s", checkpoint_path)
                uvdata = UVData()
                uvdata.read(
                    checkpoint_path,
                    file_type='uvh5',
                    run_check=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                    check_extra=False,
                )
                _coerce_uvdata_float64(uvdata)
                loaded_from_checkpoint = True
            else:
                t_read0 = time.perf_counter()
                logger.info("Reading and concatenating %d subband files...", len(subband_files))

                uvdata = UVData()
                read_kwargs = dict(
                    file_type='uvh5',
                    run_check=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                    check_extra=False,
                )
                if antenna_list is not None:
                    read_kwargs['antenna_names'] = antenna_list
                
                # Read all files at once for efficiency
                uvdata.read(subband_files, **read_kwargs)

                t_read1 = time.perf_counter()
                logger.info("Loaded and concatenated %d subbands in %.2f s", len(subband_files), t_read1 - t_read0)

                # Coerce dtypes on the final combined object
                _coerce_uvdata_float64(uvdata)

            # Now run the check after fixing data types
            logger.info("Running pyuvdata validation after assembling group...")
            try:
                uvdata.check()
                logger.info("UVData validation passed")
            except Exception as e:
                logger.warning("UVData validation failed after fixes: %s", e)

            # Get pointing information for DSA-110 processing
            pt_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad

            # Determine phase centre for this group without mutating caller state
            group_phase_ra: Optional[u.Quantity] = phase_ra
            group_phase_dec: Optional[u.Quantity] = phase_dec
            if not loaded_from_checkpoint:
                if group_phase_ra is None or group_phase_dec is None:
                    phase_time = Time(np.mean(uvdata.time_array), format='jd')
                    group_phase_ra, group_phase_dec = get_meridian_coords(pt_dec, phase_time.mjd)

                # Apply time filtering if specified using DSA-110 approach
                if dt is not None:
                    extract_times_dsacalib(uvdata, group_phase_ra, dt)

                logger.debug(
                    "Group %s phase centre: RA=%.8f rad, Dec=%.8f rad",
                    i + 1,
                    group_phase_ra.to_value(u.rad),
                    group_phase_dec.to_value(u.rad)
                )

                if refmjd is not None:
                    group_refmjd = refmjd
                else:
                    group_refmjd = float(Time(np.mean(uvdata.time_array), format='jd').mjd)
                    logger.debug("Derived refmjd %.6f from UVData time header", group_refmjd)

                # Set antenna positions using DSA-110 positions
                t_antpos0 = time.perf_counter()
                antenna_positions = set_antenna_positions(uvdata)
                _ensure_antenna_diameters(uvdata)
                t_antpos1 = time.perf_counter()
                logger.info("Antenna positions/diameters set in %.2f s", t_antpos1 - t_antpos0)

                # Phase visibilities using DSA-110 approach
                t_phase0 = time.perf_counter()
                phase_visibilities(uvdata, group_phase_ra, group_phase_dec, fringestop=fringestop,
                                  refmjd=group_refmjd)
                t_phase1 = time.perf_counter()
                logger.info("Phasing complete in %.2f s", t_phase1 - t_phase0)

                # Fix frequency arrays using DSA-110 approach
                t_freq0 = time.perf_counter()
                fix_descending_missing_freqs(uvdata)
                t_freq1 = time.perf_counter()
                logger.info("Frequency fixes completed in %.2f s", t_freq1 - t_freq0)

                # Update phase-center metadata for UVFITS sidereal requirement
                if uvdata.phase_center_catalog:
                    for idx, (cat_id, entry) in enumerate(uvdata.phase_center_catalog.items()):
                        entry["cat_type"] = "sidereal"
                        entry["cat_frame"] = "icrs"
                        entry["cat_epoch"] = 2000.0
                        entry["cat_name"] = f"{base_name}_phase{idx}"

                if checkpoint_path is not None:
                    logger.info("Writing checkpoint to %s", checkpoint_path)
                    t_chk0 = time.perf_counter()
                    uvdata.write_uvh5(
                        checkpoint_path,
                        run_check=False,
                        fix_autos=False,
                        check_extra=False,
                    )
                    t_chk1 = time.perf_counter()
                    logger.info("Checkpoint write completed in %.2f s", t_chk1 - t_chk0)
            else:
                if uvdata.phase_center_catalog:
                    for idx, (cat_id, entry) in enumerate(uvdata.phase_center_catalog.items()):
                        entry.setdefault("cat_type", "sidereal")
                        entry.setdefault("cat_frame", "icrs")
                        entry.setdefault("cat_epoch", 2000.0)
                        entry.setdefault("cat_name", f"{base_name}_phase{idx}")
                        # ensure values are correct even if present
                        entry["cat_type"] = "sidereal"
                        entry["cat_frame"] = "icrs"
                        entry["cat_epoch"] = 2000.0
                        entry["cat_name"] = f"{base_name}_phase{idx}"

                # Re-establish DSA antenna positions to align with current environment
                antenna_positions = set_antenna_positions(uvdata)
                _ensure_antenna_diameters(uvdata)

                if refmjd is not None:
                    group_refmjd = refmjd
                else:
                    group_refmjd = float(Time(np.mean(uvdata.time_array), format='jd').mjd)
                    logger.debug("Derived refmjd %.6f from UVData time header (checkpointed)", group_refmjd)

                # Derive phase centre if not provided in args
                if group_phase_ra is None or group_phase_dec is None:
                    phase_time = Time(np.mean(uvdata.time_array), format='jd')
                    group_phase_ra, group_phase_dec = get_meridian_coords(pt_dec, phase_time.mjd)

            # Convert to Measurement Set
            if group_phase_ra is None or group_phase_dec is None:
                # Try to fall back to UVData attrs if present; otherwise derive from meridian
                fallback_done = False
                ra_attr = getattr(uvdata, 'phase_center_ra', None)
                dec_attr = getattr(uvdata, 'phase_center_dec', None)
                if ra_attr is not None and dec_attr is not None:
                    group_phase_ra = ra_attr * u.rad
                    group_phase_dec = dec_attr * u.rad
                    fallback_done = True
                if not fallback_done:
                    phase_time = Time(np.mean(uvdata.time_array), format='jd')
                    group_phase_ra, group_phase_dec = get_meridian_coords(pt_dec, phase_time.mjd)

            # Direct write via pyuvdata.write_ms when requested
            ms_full_path = f"{msname}.ms"
            if direct_ms:
                if os.path.exists(ms_full_path):
                    shutil.rmtree(ms_full_path)
                t_ms0 = time.perf_counter()
                uvdata.write_ms(
                    ms_full_path,
                    clobber=True,
                    run_check=False,
                    check_extra=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                    check_autos=False,
                    fix_autos=False,
                )
                t_ms1 = time.perf_counter()
                logger.info("pyuvdata.write_ms completed in %.2f s", t_ms1 - t_ms0)
                # Ensure imaging columns exist
                try:
                    addImagingColumns(ms_full_path)
                except Exception:
                    pass
            else:
                t_ms0 = time.perf_counter()
                write_uvdata_to_ms(uvdata, msname, antenna_positions, scratch_dir=group_scratch_dir)
                t_ms1 = time.perf_counter()
                logger.info("MS creation pipeline (UVFITS+CASA) completed in %.2f s", t_ms1 - t_ms0)

            # Populate MODEL_DATA only when an explicit flux is provided
            if flux is not None:
                set_model_column(msname, uvdata, pt_dec, group_phase_ra, group_phase_dec,
                                 flux_Jy=flux)
            
            group_end = time.perf_counter()
            logger.info("Successfully converted group to %s.ms in %.2f s", msname, group_end - group_start)
            
        except Exception as e:
            logger.exception("Error converting subband group")
            continue
    
    logger.info("Conversion complete! Measurement Sets saved to %s", output_dir)


def main():
    """Command-line interface for the UVH5 to MS converter."""
    parser = argparse.ArgumentParser(
        description="Convert DSA-110 subband files to CASA Measurement Sets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python uvh5_to_ms_converter.py /path/to/subband/files /path/to/output "2024-01-01 00:00:00" "2024-01-01 23:59:59"
  python uvh5_to_ms_converter.py /data/hdf5 /data/ms "2024-01-01 00:00:00" "2024-01-01 01:00:00" --duration 30

Note:
  This script expects DSA-110 subband files with pattern *sb??.hdf5 (e.g., 2024-01-01T12:30:45_sb01.hdf5)
  and groups them by timestamp to form complete observations. Each group is converted to a single MS.
        """
    )
    
    parser.add_argument('input_dir', help='Directory containing HDF5 subband files (*sb??.hdf5)')
    parser.add_argument('output_dir', help='Directory to write Measurement Sets')
    parser.add_argument('start_time', help='Start time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('end_time', help='End time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--antennas', nargs='+', help='List of antenna names to include')
    parser.add_argument('--duration', type=float, help='Duration in minutes to extract from each file')
    parser.add_argument('--refmjd', type=float, default=None,
                        help='Reference MJD for fringestopping (default: derive from data)')
    parser.add_argument('--flux', type=float,
                        help='Calibrator flux in Jy for MODEL_DATA primary beam model')
    parser.add_argument('--no-fringestop', action='store_false', dest='fringestop',
                        help='Disable fringestopping')
    parser.add_argument('--ra', type=str,
                        help='Phase center RA (e.g., "12h34m56.7s" or "185.5deg")')
    parser.add_argument('--dec', type=str,
                        help='Phase center Dec (e.g., "+45d12m34.5s" or "45.2deg")')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Logging level (default: INFO)')
    parser.add_argument('--checkpoint-dir',
                        help='Directory to store/load UVData checkpoints between phases')
    parser.add_argument('--scratch-dir',
                        help='Scratch directory for staging UVFITS/checkpoints before syncing outputs')
    parser.add_argument('--direct-ms', action='store_true',
                        help='Write MS directly with casacore (bypass UVFITS path)')
    
    args = parser.parse_args()

    setup_logging(args.log_level)
    
    # Validate input directory
    if not os.path.isdir(args.input_dir):
        logger.error("Input directory %s does not exist", args.input_dir)
        return 1
    
    # Validate time format
    try:
        datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S')
        datetime.strptime(args.end_time, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        logger.error("Time format must be 'YYYY-MM-DD HH:MM:SS'")
        return 1
    
    # Parse RA/Dec coordinates if provided
    phase_ra = None
    phase_dec = None
    if args.ra is not None or args.dec is not None:
        if args.ra is None or args.dec is None:
            logger.error("Both --ra and --dec must be provided when specifying phase center")
            return 1
        
        try:
            from astropy.coordinates import Angle
            phase_ra = Angle(args.ra).to(u.rad)
            phase_dec = Angle(args.dec).to(u.rad)
        except Exception as e:
            logger.error("Error parsing coordinates: %s", e)
            return 1
    
    # Run conversion
    convert_subband_groups_to_ms(
        args.input_dir,
        args.output_dir,
        args.start_time,
        args.end_time,
        args.antennas,
        args.duration,
        args.refmjd,
        args.flux,
        args.fringestop,
        phase_ra,
        phase_dec,
        args.checkpoint_dir,
        args.scratch_dir,
        args.direct_ms
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
