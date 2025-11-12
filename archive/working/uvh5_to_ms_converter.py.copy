#!/usr/bin/env python3
"""
UVH5 to CASA Measurement Set Converter for DSA-110 Radio Telescope

This script converts UVH5 (HDF5) visibility files from the DSA-110 radio
telescope into CASA Measurement Sets (MS) for further analysis and calibration.

Author: Jakob T. Faber
Date: October 4, 2025
"""

import os
import glob
import shutil
import argparse
from datetime import datetime
from typing import List, Optional, Union, Tuple
import logging
import warnings

import numpy as np
import astropy.units as u
import astropy.constants as c
from astropy.time import Time
from astropy.coordinates import angular_separation
from pyuvdata import UVData
from casatasks import importuvfits
from casacore.tables import addImagingColumns, table
import casatools as cc
from scipy.special import j1

from antpos_local import get_itrf

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("uvh5_to_ms_converter")


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

# OVRO site coordinates (from dsacalib.constants)
OVRO_LON = -2.1454167  # radians
OVRO_LAT = 0.7106      # radians  
OVRO_ALT = 1200.0      # meters


class Direction:
    """Class for holding sky coordinates and converting between ICRS and FK5.
    
    Based on dsacalib.utils.Direction for coordinate transformations.
    
    Parameters
    ----------
    epoch : str
        'J2000' (for ICRS or J2000 coordinates) or 'HADEC' (for FK5
        coordinates at an equinox of obstime)
    lon : float
        The longitude (right ascension or hour angle) in radians
    lat : float
        The latitude (declination) in radians
    obstime : float
        The observation time in mjd.
    observatory : str
        The name of the observatory
    """
    
    def __init__(self, epoch, lon, lat, obstime=None, observatory="OVRO_MMA"):
        assert epoch in ["J2000", "HADEC"]
        if epoch == "HADEC":
            assert obstime is not None
        self.epoch = epoch
        self.lon = lon
        self.lat = lat
        self.obstime = obstime
        self.observatory = observatory
    
    def J2000(self, obstime=None, observatory=None):
        """Provides direction in J2000 coordinates.
        
        Parameters
        ----------
        obstime : float
            Time of observation in mjd.
        observatory : str
            Name of the observatory.
            
        Returns
        -------
        tuple
            ra, dec at J2000 in units of radians.
        """
        if self.epoch == "J2000":
            return self.lon, self.lat
        
        assert self.epoch == "HADEC"
        if obstime is None:
            assert self.obstime is not None
            obstime = self.obstime
        if observatory is None:
            assert self.observatory is not None
            observatory = self.observatory
        
        me = cc.measures()
        epoch = me.epoch("UTC", f"{obstime}d")
        location = me.observatory(observatory)
        source = me.direction("HADEC", f"{self.lon}rad", f"{self.lat}rad")
        me.doframe(epoch)
        me.doframe(location)
        output = me.measure(source, "J2000")
        assert output["m0"]["unit"] == "rad"
        assert output["m1"]["unit"] == "rad"
        return output["m0"]["value"], output["m1"]["value"]
    
    def hadec(self, obstime=None, observatory=None):
        """Provides direction in HADEC (FK5) at `obstime`.
        
        Parameters
        ----------
        obstime : float
            Time of observation in mjd.
        observatory : str
            Name of the observatory.
            
        Returns
        -------
        tuple
            ha, dec at obstime in units of radians.
        """
        if self.epoch == "HADEC":
            assert obstime is None
            return self.lon, self.lat
        
        assert self.epoch == "J2000"
        if obstime is None:
            assert self.obstime is not None
            obstime = self.obstime
        if observatory is None:
            assert self.observatory is not None
            observatory = self.observatory
        me = cc.measures()
        epoch = me.epoch("UTC", f"{obstime}d")
        location = me.observatory(observatory)
        source = me.direction("J2000", f"{self.lon}rad", f"{self.lat}rad")
        me.doframe(epoch)
        me.doframe(location)
        output = me.measure(source, "HADEC")
        assert output["m0"]["unit"] == "rad"
        assert output["m1"]["unit"] == "rad"
        return output["m0"]["value"], output["m1"]["value"]


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

def find_subband_groups(input_dir: str, start_time: str, end_time: str) -> List[List[str]]:
    """
    Find all DSA-110 subband file groups in the input directory that fall within
    the specified time range.
    
    Parameters:
    -----------
    input_dir : str
        Path to directory containing HDF5 subband files
    start_time : str
        Start time in 'YYYY-MM-DD HH:MM:SS' format
    end_time : str
        End time in 'YYYY-MM-DD HH:MM:SS' format
        
    Returns:
    --------
    List[List[str]]
        List of subband file groups, where each group contains all subband files
        for one observation
    """
    logger.info("Searching for DSA-110 subband files in %s", input_dir)
    
    # Convert time strings to datetime objects for comparison
    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    
    # Find all HDF5 subband files in the directory
    hdf5_pattern = os.path.join(input_dir, '*sb??.hdf5')
    all_files = glob.glob(hdf5_pattern)
    
    if not all_files:
        logger.info("No HDF5 subband files found in %s", input_dir)
        return []
    
    # Parse all file timestamps and group by time-window clustering (2.5 min window)
    file_times = []
    for file_path in all_files:
        try:
            filename = os.path.basename(file_path)
            # Extract timestamp from filename (e.g., 2024-01-01T12:30:45_sb01.hdf5)
            # Remove subband suffix and file extension
            timestamp_str = filename.replace('.hdf5', '').split('_sb')[0]
            
            # Try different timestamp formats commonly used in DSA-110
            file_dt = None
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S',
                        '%Y%m%d_%H%M%S']:
                try:
                    file_dt = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue
            
            if file_dt is None:
                logger.warning("Could not parse timestamp from %s", filename)
                continue
            
            # Check if file is within time range
            if start_dt <= file_dt <= end_dt:
                file_times.append((file_path, file_dt))
                logger.debug("Found candidate file %s (%s)", filename, file_dt)
                
        except Exception as e:
            logger.warning("Error processing %s: %s", file_path, e)
            continue
    
    if not file_times:
        logger.info("No files found within time range")
        return []
    
    # Group files by time-window clustering (2.5 minute window)
    file_groups = []
    processed_files = set()
    
    # Sort files by timestamp for deterministic grouping
    file_times.sort(key=lambda x: x[1])
    
    for file_path, file_dt in file_times:
        if file_path in processed_files:
            continue
            
        # Find all files within 2.5 minutes of this file
        group_files = []
        file_time_astropy = Time(file_dt)
        
        for other_path, other_dt in file_times:
            if other_path in processed_files:
                continue
                
            other_time_astropy = Time(other_dt)
            time_diff = abs(other_time_astropy - file_time_astropy)
            
            if time_diff < 2.5 * u.minute:
                group_files.append(other_path)
                processed_files.add(other_path)
        
        # Validate group size (1-16 subband files)
        if len(group_files) == 0:
            logger.error("No subband files found for group starting at %s", file_dt)
            raise ValueError(
                f"No subband files found for group starting at {file_dt}"
            )
        if len(group_files) > 16:
            logger.error(
                "Group at %s contains %s files; expected at most 16",
                file_dt,
                len(group_files)
            )
            raise ValueError(
                f"Group at {file_dt} contains {len(group_files)} files; "
                "expected at most 16"
            )
        if len(group_files) < 16:
            logger.warning(
                "Group at %s has only %s files (incomplete observation)",
                file_dt,
                len(group_files)
            )
        
        # Sort files within group for deterministic output
        group_files.sort()
        file_groups.append(group_files)
        logger.info("Identified group at %s with %s subband files", file_dt, len(group_files))
    
    logger.info("Found %s observation groups within time range", len(file_groups))
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
        
        # Calculate meridian coordinates using Direction class (HADEC to J2000)
        pointing = Direction(
            'HADEC',
            0.,  # Hour angle = 0 (meridian)
            pt_dec.to_value(u.rad),
            phase_time.mjd
        )
        phase_ra = pointing.J2000()[0] * u.rad
        phase_dec = pointing.J2000()[1] * u.rad
    
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
        df_itrf = get_itrf(
            latlon_center=(OVRO_LAT * u.rad, OVRO_LON * u.rad, OVRO_ALT * u.m)
        )
    except Exception as exc:
        logger.error("Failed to load antenna coordinates from local catalogue: %s", exc)
        raise

    antenna_positions = np.array([
        df_itrf['dx_m'],
        df_itrf['dy_m'],
        df_itrf['dz_m']
    ]).T

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

    relative_positions = antenna_positions - telescope_location
    _set_relative_antenna_positions(uvdata, relative_positions)

    logger.info(
        "Loaded dynamic antenna positions for %s antennas",
        n_itrf_antennas
    )
    logger.debug("Antenna positions sourced from local catalogue")
    return antenna_positions


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
    Calculate uvw coordinates for baseline-time pairs using CASA.
    
    Uses CASA to calculate the u,v,w coordinates of the baselines towards a
    source or phase center at the specified times and observatory.
    Full implementation based on dsacalib.fringestopping.calc_uvw_blt.
    
    Parameters:
    -----------
    blen : np.ndarray
        The ITRF coordinates of the baselines. Shape (nblt, 3), units of meters.
    time_mjd : np.ndarray
        Array of times in MJD for which to calculate uvw coordinates, shape (nblt).
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
    np.ndarray
        The uvw values for each baseline-time. Shape (nblt, 3), units of meters.
    """
    nblt = time_mjd.shape[0]
    buvw = np.zeros((nblt, 3))
    
    # Define the reference frame
    me = cc.measures()
    qa = cc.quanta()
    
    if obs is not None:
        me.doframe(me.observatory(obs))
    
    # Handle time-varying coordinates
    if not isinstance(ra.ndim, float) and ra.ndim > 0:
        assert ra.ndim == 1
        assert ra.shape[0] == nblt
        assert dec.shape[0] == nblt
        direction_set = False
    else:
        if (frame == 'HADEC') and (nblt > 1):
            raise TypeError('HA and DEC must be specified at each baseline-time in time_mjd.')
        me.doframe(me.direction(
            frame,
            qa.quantity(ra.to_value(u.deg), 'deg'),
            qa.quantity(dec.to_value(u.deg), 'deg')
        ))
        direction_set = True
    
    contains_nans = False
    for i in range(nblt):
        me.doframe(me.epoch('UTC', qa.quantity(time_mjd[i], 'd')))
        if not direction_set:
            me.doframe(me.direction(
                frame,
                qa.quantity(ra[i].to_value(u.deg), 'deg'),
                qa.quantity(dec[i].to_value(u.deg), 'deg')
            ))
        bl = me.baseline('itrf',
                        qa.quantity(blen[i, 0], 'm'),
                        qa.quantity(blen[i, 1], 'm'),
                        qa.quantity(blen[i, 2], 'm'))
        # Get the uvw coordinates
        try:
            buvw[i, :] = me.touvw(bl)[1]['value']
        except KeyError:
            contains_nans = True
            buvw[i, :] = np.ones(3) * np.nan
    
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

    antenna_w_m = uvw_m[refidxs, -1]
    uvw_delays = uvw.reshape((nts, nbls, 3))
    antenna_w = uvw_delays[:, refidxs, -1]
    antenna_dw = antenna_w - antenna_w_m[np.newaxis, :]
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
    
    # Calculate meridian uvw coordinates
    uvw_m = calc_uvw_blt(
        blen, np.tile(refmjd, (uvdata.Nbls)), 'HADEC',
        np.zeros(uvdata.Nbls) * u.rad, np.tile(pt_dec, (uvdata.Nbls))
    )
    
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
    
    logger.info("Frequency array processing complete")


def write_uvdata_to_ms(uvdata: UVData, msname: str, antenna_positions: np.ndarray) -> None:
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
    logger.info("Converting to Measurement Set: %s.ms", msname)
    
    # Remove existing files if they exist
    fits_file = f'{msname}.fits'
    ms_file = f'{msname}.ms'
    
    if os.path.exists(fits_file):
        os.remove(fits_file)
    if os.path.exists(ms_file):
        shutil.rmtree(ms_file)
    
    # Write UVData to UVFITS format
    logger.info("Writing UVFITS intermediate file")
    uvdata.write_uvfits(
        fits_file,
        write_lst=True,
        use_miriad_convention=True,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
        run_check=False,
        check_extra=False,
        check_autos=False
    )
    
    # Convert UVFITS to Measurement Set using CASA
    logger.info("Converting UVFITS to Measurement Set")
    importuvfits(fits_file, ms_file)
    
    # Update antenna positions in the measurement set
    logger.info("Updating antenna positions in Measurement Set")
    with table(f'{ms_file}/ANTENNA', readonly=False) as tb:
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
    addImagingColumns(ms_file)
    
    # Clean up intermediate UVFITS file
    os.remove(fits_file)
    
    logger.info("Successfully created %s", ms_file)


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
        tb.putcol('MODEL_DATA', model)
        # Copy DATA to CORRECTED_DATA
        data = tb.getcol('DATA')
        tb.putcol('CORRECTED_DATA', data)
    
    logger.info("MODEL_DATA column set successfully")


def convert_subband_groups_to_ms(input_dir: str, output_dir: str, start_time: str, end_time: str,
                                 antenna_list: Optional[List[str]] = None,
                                 duration: Optional[float] = None,
                                 refmjd: Optional[float] = None,
                                 flux: Optional[float] = None,
                                 fringestop: bool = True,
                                 phase_ra: Optional[u.Quantity] = None,
                                 phase_dec: Optional[u.Quantity] = None,
                                 checkpoint_dir: Optional[str] = None) -> None:
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
    if checkpoint_dir is not None:
        checkpoint_dir_path = os.path.abspath(checkpoint_dir)
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
            checkpoint_path = None
            if checkpoint_dir_path is not None:
                checkpoint_path = os.path.join(checkpoint_dir_path, f"{base_name}.checkpoint.uvh5")

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
                subband_chunks: List[Tuple[float, UVData]] = []

                for j, subband_file in enumerate(subband_files):
                    logger.debug("Reading subband file %s/%s: %s", j + 1, len(subband_files), os.path.basename(subband_file))
                    tmp_uv = UVData()
                    read_kwargs = dict(
                        file_type='uvh5',
                        run_check=False,
                        run_check_acceptability=False,
                        strict_uvw_antpos_check=False,
                        check_extra=False,
                    )
                    if antenna_list is not None:
                        read_kwargs['antenna_names'] = antenna_list
                    tmp_uv.read(subband_file, **read_kwargs)
                    _coerce_uvdata_float64(tmp_uv)
                    mean_freq = float(np.mean(tmp_uv.freq_array))
                    subband_chunks.append((mean_freq, tmp_uv))

                if not subband_chunks:
                    logger.error("No subband data loaded for group %s", i + 1)
                    continue

                first_chunk_freq = subband_chunks[0][1].freq_array.squeeze()
                freq_diff = np.diff(first_chunk_freq)
                descending = bool(freq_diff.size > 0 and np.median(freq_diff) < 0.0)
                subband_chunks.sort(key=lambda item: item[0], reverse=descending)

                uvdata = subband_chunks[0][1]
                for _, chunk_uv in subband_chunks[1:]:
                    uvdata.fast_concat(chunk_uv, axis='freq', inplace=True)

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
                    pointing = Direction(
                        'HADEC',
                        0.,  # Hour angle = 0 (meridian)
                        pt_dec.to_value(u.rad),
                        phase_time.mjd
                    )
                    group_phase_ra = pointing.J2000()[0] * u.rad
                    group_phase_dec = pointing.J2000()[1] * u.rad

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
                antenna_positions = set_antenna_positions(uvdata)
                _ensure_antenna_diameters(uvdata)

                # Phase visibilities using DSA-110 approach
                phase_visibilities(uvdata, group_phase_ra, group_phase_dec, fringestop=fringestop,
                                  refmjd=group_refmjd)

                # Fix frequency arrays using DSA-110 approach
                fix_descending_missing_freqs(uvdata)

                # Update phase-center metadata for UVFITS sidereal requirement
                if uvdata.phase_center_catalog:
                    for idx, (cat_id, entry) in enumerate(uvdata.phase_center_catalog.items()):
                        entry["cat_type"] = "sidereal"
                        entry["cat_frame"] = "icrs"
                        entry["cat_epoch"] = 2000.0
                        entry["cat_name"] = f"{base_name}_phase{idx}"

                if checkpoint_path is not None:
                    logger.info("Writing checkpoint to %s", checkpoint_path)
                    uvdata.write_uvh5(
                        checkpoint_path,
                        run_check=False,
                        fix_autos=False,
                        check_extra=False,
                    )
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

            # Convert to Measurement Set
            if group_phase_ra is None or group_phase_dec is None:
                group_phase_ra = uvdata.phase_center_ra * u.rad
                group_phase_dec = uvdata.phase_center_dec * u.rad

            write_uvdata_to_ms(uvdata, msname, antenna_positions)

            # Populate MODEL_DATA only when an explicit flux is provided
            if flux is not None:
                set_model_column(msname, uvdata, pt_dec, group_phase_ra, group_phase_dec,
                                 flux_Jy=flux)
            
            logger.info("Successfully converted group to %s.ms", msname)
            
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
        args.checkpoint_dir
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
