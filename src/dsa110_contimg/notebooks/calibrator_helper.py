"""Helpers for calibrator search notebooks.

This module provides interactive tools for calibrator selection and analysis
in the DSA-110 continuum imaging pipeline. It supports both MS and UVH5 data
formats and provides comprehensive scoring based on primary beam response,
flux, and timing considerations.

Key Features:
- Dual format support (MS and UVH5)
- Primary beam response calculation
- Altitude track plotting
- Calibrator scoring and ranking
- CLI command generation
- JSON summary output

Example:
    >>> info = load_pointing('/path/to/data.ms')
    >>> cal_df = candidates_near_pointing(np.radians(info['dec_deg']))
    >>> scored = score_calibrators(cal_df, pointing_ra_deg=info['ra_deg'], 
    ...                           pointing_dec_deg=info['dec_deg'])
    >>> track_df = plot_altitude_tracks(scored, '2025-10-08')
"""
from __future__ import annotations

import logging
import functools
from pathlib import Path
from typing import Iterable, Optional, Dict, Any, Union

import h5py
import numpy as np
import pandas as pd
from astropy.coordinates import AltAz, SkyCoord
from astropy.time import Time
import astropy.units as u
from casacore.tables import table

import matplotlib.pyplot as plt

from dsa110_contimg.calibration.catalogs import (
    airy_primary_beam_response,
    read_vla_calibrator_catalog,
)
from dsa110_contimg.calibration.schedule import DSA110_LOCATION

# Configure logging
logger = logging.getLogger(__name__)

# Cache for catalog operations
_catalog_cache: Dict[str, pd.DataFrame] = {}


DEFAULT_CATALOG = \
    "/data/dsa110-contimg/data-samples/catalogs/vlacalibrators.txt"


def _get_cached_catalog(catalog_path: Union[str, Path]) -> pd.DataFrame:
    """Get catalog with caching to improve performance.
    
    Args:
        catalog_path: Path to catalog file
        
    Returns:
        Cached DataFrame of catalog entries
    """
    catalog_path = str(catalog_path)
    if catalog_path not in _catalog_cache:
        try:
            _catalog_cache[catalog_path] = read_vla_calibrator_catalog(catalog_path)
            logger.info(f"Loaded catalog from {catalog_path} ({len(_catalog_cache[catalog_path])} entries)")
        except Exception as e:
            logger.error(f"Failed to load catalog {catalog_path}: {e}")
            raise RuntimeError(f"Failed to load catalog {catalog_path}: {e}") from e
    return _catalog_cache[catalog_path]


def _time_from_seconds(seconds: Optional[np.ndarray]) -> Optional[Time]:
    """Convert seconds-since-MJD0 array to Time.
    
    Args:
        seconds: Array of seconds since MJD 0, or None
        
    Returns:
        Time object or None if input is invalid
        
    Raises:
        ValueError: If seconds array contains invalid values
    """
    if seconds is None or seconds.size == 0:
        return None
    
    # Validate input
    if not isinstance(seconds, np.ndarray):
        seconds = np.asarray(seconds)
    
    if not np.all(np.isfinite(seconds)):
        raise ValueError("Seconds array contains non-finite values")
    
    try:
        if seconds.size == 1:
            sec = float(seconds[0])
        else:
            sec = float(0.5 * (seconds[0] + seconds[-1]))
        jd = sec / 86400.0 + 2400000.5
        return Time(jd, format="jd", scale="utc")
    except Exception as e:
        logger.error(f"Failed to convert seconds to Time: {e}")
        raise ValueError(f"Invalid time conversion: {e}") from e


def load_pointing(path: Union[str, Path], field_id: Optional[int] = None) -> Dict[str, Any]:
    """Return pointing info for an MS or UVH5 file.

    Parameters
    ----------
    path : str or Path
        Measurement Set ``*.ms`` directory or UVH5 ``*.hdf5`` file.
    field_id : int, optional
        When reading an MS, select this FIELD_ID; defaults to the FIELD with
        the largest number of rows.
        
    Returns
    -------
    dict
        Dictionary containing pointing information with keys:
        - source_type: 'ms' or 'uvh5'
        - ra_deg: Right ascension in degrees
        - dec_deg: Declination in degrees
        - mid_time: Observation mid-time as Time object
        - fields: List of field information (MS only)
        - selected_field_id: Selected field ID
        - ms_path: Path to MS (if applicable)
        
    Raises
    ------
    FileNotFoundError
        If the specified path does not exist
    ValueError
        If the file format is not supported or field_id is invalid
    RuntimeError
        If there are issues reading the data
    """

    # Input validation
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    
    # Validate field_id if provided
    if field_id is not None and (not isinstance(field_id, int) or field_id < 0):
        raise ValueError(f"field_id must be a non-negative integer, got: {field_id}")
    
    info: Dict[str, Any] = {
        "input_path": str(path),
        "source_type": None,
        "ra_deg": None,
        "dec_deg": None,
        "mid_time": None,
        "fields": None,
        "selected_field_id": None,
        "ms_path": None,
    }

    if path.suffix == ".ms" or path.name.endswith(".ms"):
        if not path.is_dir():
            raise ValueError(f"MS path must be a directory: {path}")
        info["source_type"] = "ms"
        info["ms_path"] = str(path)

        try:
            with table(str(path) + "::FIELD") as tf:
                phase_dir = tf.getcol("PHASE_DIR")
                if phase_dir.ndim < 3:
                    raise ValueError("PHASE_DIR has unexpected shape")
                ra_list = np.degrees(phase_dir[:, 0, 0])
                dec_list = np.degrees(phase_dir[:, 0, 1])

            with table(str(path)) as tb:
                field_ids = tb.getcol("FIELD_ID")
                times = tb.getcol("TIME")

            unique_ids = np.unique(field_ids)
            fields: list[Dict[str, Any]] = []
            for fid in unique_ids:
                idx = np.where(field_ids == fid)[0]
                if int(fid) >= len(ra_list):
                    logger.warning(f"Field {fid} index out of range for PHASE_DIR")
                    continue
                fields.append({
                    "field_id": int(fid),
                    "rows": int(idx.size),
                    "ra_deg": float(ra_list[int(fid)]),
                    "dec_deg": float(dec_list[int(fid)]),
                })
            info["fields"] = fields

            if not fields:
                raise RuntimeError("No valid fields found in MS")

            if field_id is None:
                fid = max(fields, key=lambda x: x["rows"])["field_id"]
            else:
                fid = field_id
                if fid not in [f["field_id"] for f in fields]:
                    available = [f["field_id"] for f in fields]
                    raise ValueError(f"Field {fid} not present in MS {path}. Available fields: {available}")

            info["selected_field_id"] = int(fid)
            info["ra_deg"] = float(ra_list[int(fid)])
            info["dec_deg"] = float(dec_list[int(fid)])
            info["mid_time"] = _time_from_seconds(times[field_ids == fid])
            return info
            
        except Exception as e:
            logger.error(f"Failed to read MS {path}: {e}")
            raise RuntimeError(f"Error reading MS {path}: {e}") from e

    if path.suffix == ".hdf5" and path.exists():
        if not path.is_file():
            raise ValueError(f"UVH5 path must be a file: {path}")
        info["source_type"] = "uvh5"
        
        try:
            with h5py.File(path, "r") as f:
                header = f.get("Header")
                if header is None:
                    raise ValueError("No Header group found in UVH5 file")
                
                time_arr = np.asarray(header["time_array"]) if "time_array" in header else None
                info["mid_time"] = _time_from_seconds(time_arr)

                dec_val = None
                ha_val = None
                if "extra_keywords" in header:
                    ek = header["extra_keywords"]
                    if "phase_center_dec" in ek:
                        dec_val = float(np.asarray(ek["phase_center_dec"]))
                    if "ha_phase_center" in ek:
                        ha_val = float(np.asarray(ek["ha_phase_center"]))
                
                if dec_val is not None:
                    info["dec_deg"] = np.degrees(dec_val)
                else:
                    logger.warning("No phase_center_dec found in UVH5 extra_keywords")
                
                if info["mid_time"] is not None and ha_val is not None:
                    lst = info["mid_time"].sidereal_time("apparent", longitude=DSA110_LOCATION.lon)
                    ra = (lst - ha_val * u.rad).wrap_at(360 * u.deg)
                    info["ra_deg"] = float(ra.deg)
                else:
                    logger.warning("Cannot compute RA: missing mid_time or ha_phase_center")
                    
            return info
            
        except Exception as e:
            logger.error(f"Failed to read UVH5 {path}: {e}")
            raise RuntimeError(f"Error reading UVH5 {path}: {e}") from e

    raise ValueError(f"Unsupported file format: {path}. Expected .ms directory or .hdf5 file")


def candidates_near_pointing(
    pt_dec_rad: float,
    radius_deg: float = 5.0,
    min_flux_mJy: float = 100.0,
    catalog_path: Union[str, Path] = DEFAULT_CATALOG,
) -> pd.DataFrame:
    """Return catalog calibrators within declination band and flux cut.
    
    Args:
        pt_dec_rad: Pointing declination in radians
        radius_deg: Search radius in degrees
        min_flux_mJy: Minimum flux in mJy
        catalog_path: Path to VLA calibrator catalog
        
    Returns:
        DataFrame of calibrators within search criteria
        
    Raises:
        ValueError: If input parameters are invalid
        RuntimeError: If catalog cannot be loaded
    """
    # Input validation
    if not np.isfinite(pt_dec_rad):
        raise ValueError(f"pt_dec_rad must be finite, got: {pt_dec_rad}")
    if not (0 < radius_deg <= 180):
        raise ValueError(f"radius_deg must be in (0, 180], got: {radius_deg}")
    if not (0 <= min_flux_mJy < 1e6):
        raise ValueError(f"min_flux_mJy must be in [0, 1e6), got: {min_flux_mJy}")
    
    try:
        df = _get_cached_catalog(catalog_path)
        if df.empty:
            logger.warning(f"Catalog {catalog_path} is empty")
            return df
            
        df = df.rename(columns={"ra": "ra_deg", "dec": "dec_deg"})
        dec0 = np.degrees(pt_dec_rad)
        
        # Apply declination filter
        sub = df[(df["dec_deg"] >= dec0 - radius_deg) & (df["dec_deg"] <= dec0 + radius_deg)].copy()
        
        # Apply flux filter if column exists
        if "flux_20_cm" in sub.columns:
            flux = pd.to_numeric(sub["flux_20_cm"], errors="coerce")
            sub = sub[flux >= min_flux_mJy]
            logger.info(f"Found {len(sub)} calibrators within {radius_deg}° of dec={dec0:.2f}° with flux >= {min_flux_mJy} mJy")
        else:
            logger.warning("No flux_20_cm column found in catalog")
            
        return sub
        
    except Exception as e:
        logger.error(f"Failed to find candidates near pointing: {e}")
        raise RuntimeError(f"Error finding calibrator candidates: {e}") from e


def score_calibrators(
    cal_df: pd.DataFrame,
    *,
    pointing_ra_deg: Optional[float] = None,
    pointing_dec_deg: Optional[float] = None,
    freq_ghz: float = 1.4,
    obs_time: Optional[Time] = None,
) -> pd.DataFrame:
    """Add PB response, weighted flux, and altitude-at-observation columns.
    
    Args:
        cal_df: DataFrame of calibrator candidates
        pointing_ra_deg: Pointing RA in degrees (optional)
        pointing_dec_deg: Pointing Dec in degrees (optional)
        freq_ghz: Frequency in GHz for PB calculation
        obs_time: Observation time for altitude calculation
        
    Returns:
        DataFrame with additional scoring columns
        
    Raises:
        ValueError: If input parameters are invalid
        RuntimeError: If scoring calculations fail
    """
    if cal_df.empty:
        logger.warning("Empty calibrator DataFrame provided")
        return cal_df.copy()
    
    # Input validation
    if pointing_ra_deg is not None and not (0 <= pointing_ra_deg < 360):
        raise ValueError(f"pointing_ra_deg must be in [0, 360), got: {pointing_ra_deg}")
    if pointing_dec_deg is not None and not (-90 <= pointing_dec_deg <= 90):
        raise ValueError(f"pointing_dec_deg must be in [-90, 90], got: {pointing_dec_deg}")
    if not (0.1 <= freq_ghz <= 100):
        raise ValueError(f"freq_ghz must be in [0.1, 100], got: {freq_ghz}")
    
    try:
        df = cal_df.copy()
        
        # Handle flux conversion
        if "flux_20_cm" in df.columns:
            df["flux_20_cm"] = pd.to_numeric(df["flux_20_cm"], errors="coerce")
            df["flux_jy"] = df["flux_20_cm"] / 1000.0
        else:
            logger.warning("No flux_20_cm column found, setting flux_jy to NaN")
            df["flux_jy"] = np.nan

        # Calculate primary beam response
        if pointing_ra_deg is not None and pointing_dec_deg is not None:
            pr = np.radians(pointing_ra_deg)
            pd_rad = np.radians(pointing_dec_deg)
            
            def calc_pb_response(row):
                try:
                    return airy_primary_beam_response(
                        pr, pd_rad,
                        np.radians(row["ra_deg"]),
                        np.radians(row["dec_deg"]),
                        freq_ghz,
                    )
                except Exception as e:
                    logger.warning(f"PB calculation failed for {row.get('name', 'unknown')}: {e}")
                    return np.nan
            
            df["pb_response"] = df.apply(calc_pb_response, axis=1)
        else:
            logger.warning("No pointing coordinates provided, setting pb_response to NaN")
            df["pb_response"] = np.nan

        df["weighted_flux_jy"] = df["flux_jy"] * df["pb_response"]

        # Calculate altitude at observation time
        if obs_time is not None:
            try:
                altaz_frame = AltAz(obstime=obs_time, location=DSA110_LOCATION)
                
                def calc_altitude(row):
                    try:
                        coord = SkyCoord(row["ra_deg"] * u.deg, row["dec_deg"] * u.deg, frame="icrs")
                        return coord.transform_to(altaz_frame).alt.to_value(u.deg)
                    except Exception as e:
                        logger.warning(f"Altitude calculation failed for {row.get('name', 'unknown')}: {e}")
                        return np.nan
                
                df["alt_at_obs_deg"] = df.apply(calc_altitude, axis=1)
            except Exception as e:
                logger.error(f"Failed to create AltAz frame: {e}")
                df["alt_at_obs_deg"] = np.nan
        else:
            logger.warning("No observation time provided, setting alt_at_obs_deg to NaN")
            df["alt_at_obs_deg"] = np.nan

        return df
        
    except Exception as e:
        logger.error(f"Failed to score calibrators: {e}")
        raise RuntimeError(f"Error scoring calibrators: {e}") from e


def sort_by_weighted_flux(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in df.columns if c not in {"weighted_flux_jy"}]
    return df.sort_values("weighted_flux_jy", ascending=False, na_position="last")[cols + ["weighted_flux_jy"]]


def plot_altitude_tracks(
    cal_df: pd.DataFrame,
    date_utc: str,
    *,
    top_n: int = 5,
    obs_time: Optional[Time] = None,
    location=DSA110_LOCATION,
) -> pd.DataFrame:
    """Plot altitude tracks and return summary DataFrame.
    
    Args:
        cal_df: DataFrame of calibrator candidates
        date_utc: Date string in UTC format (YYYY-MM-DD)
        top_n: Number of top calibrators to plot
        obs_time: Observation time for reference line
        location: Observatory location
        
    Returns:
        DataFrame with transit information
        
    Raises:
        ValueError: If input parameters are invalid
        RuntimeError: If plotting fails
    """
    if cal_df.empty:
        logger.warning("Empty calibrator DataFrame provided for plotting")
        return pd.DataFrame()
    
    # Input validation
    if not isinstance(date_utc, str) or len(date_utc.split('-')) != 3:
        raise ValueError(f"date_utc must be in YYYY-MM-DD format, got: {date_utc}")
    if not (1 <= top_n <= 50):
        raise ValueError(f"top_n must be in [1, 50], got: {top_n}")
    
    try:
        # Create time array for the day
        times = Time(f"{date_utc} 00:00:00") + np.linspace(0, 1, 1441) * u.day
        altaz_frame = AltAz(obstime=times, location=location)
        rows = []
        
        plt.figure(figsize=(12, 6))
        subset = cal_df.head(top_n)
        
        for name, row in subset.iterrows():
            try:
                sc = SkyCoord(row['ra_deg'] * u.deg, row['dec_deg'] * u.deg, frame='icrs')
                alt = sc.transform_to(altaz_frame).alt.to_value(u.deg)
                
                if not np.all(np.isfinite(alt)):
                    logger.warning(f"Non-finite altitude values for {name}")
                    continue
                
                idx = int(np.nanargmax(alt))
                plt.plot(times.datetime, alt, label=str(name), linewidth=1.5)
                
                transit_time = times[idx]
                delta_minutes = float((transit_time - obs_time).to_value(u.min)) if obs_time is not None else np.nan
                
                rows.append({
                    'name': str(name),
                    'ra_deg': float(row['ra_deg']),
                    'dec_deg': float(row['dec_deg']),
                    'transit_utc': transit_time.utc.isot,
                    'max_alt_deg': float(alt[idx]),
                    'delta_minutes': delta_minutes,
                })
                
            except Exception as e:
                logger.warning(f"Failed to plot track for {name}: {e}")
                continue
        
        if obs_time is not None:
            plt.axvline(obs_time.utc.datetime, color='red', linestyle='--', 
                       label='observation', linewidth=2)
        
        plt.axhline(0, color='k', lw=0.5, alpha=0.7)
        plt.axhline(30, color='orange', lw=0.5, alpha=0.7, linestyle=':', 
                   label='30° horizon')
        plt.ylabel('Altitude [deg]')
        plt.xlabel('UTC time')
        plt.title(f'Top {min(top_n, len(subset))} calibrator altitude tracks (DSA-110)')
        plt.legend(loc='best', fontsize=8)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        return pd.DataFrame(rows)
        
    except Exception as e:
        logger.error(f"Failed to plot altitude tracks: {e}")
        raise RuntimeError(f"Error plotting altitude tracks: {e}") from e
