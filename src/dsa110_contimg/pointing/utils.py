"""Utilities for reading pointing information from MS and UVH5 files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import h5py
import numpy as np
from astropy.time import Time
import astropy.units as u
from casacore.tables import table

from dsa110_contimg.calibration.schedule import DSA110_LOCATION

logger = logging.getLogger(__name__)


def _time_from_seconds(seconds: Optional[np.ndarray]) -> Optional[Time]:
    """Convert seconds to astropy Time object with automatic format detection.

    Automatically detects whether seconds are relative to MJD 0 or MJD 51544.0
    by validating the resulting date. This handles both formats:
    - Seconds since MJD 0 (pyuvdata format)
    - Seconds since MJD 51544.0 (CASA standard)

    Parameters
    ----------
    seconds : array-like or None
        Time in seconds (format auto-detected)

    Returns
    -------
    Time or None
        Astropy Time object, or None if input is None or empty
    """
    if seconds is None or len(seconds) == 0:
        return None
    from dsa110_contimg.utils.time_utils import (
        detect_casa_time_format,
        DEFAULT_YEAR_RANGE,
    )

    time_sec = float(np.mean(seconds))
    _, mjd = detect_casa_time_format(time_sec, DEFAULT_YEAR_RANGE)
    return Time(mjd, format="mjd", scale="utc")


def load_pointing(path: str | Path, field_id: Optional[int] = None) -> Dict[str, Any]:
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
                    logger.warning("Field %s index out of range for PHASE_DIR", fid)
                    continue
                fields.append(
                    {
                        "field_id": int(fid),
                        "rows": int(idx.size),
                        "ra_deg": float(ra_list[int(fid)]),
                        "dec_deg": float(dec_list[int(fid)]),
                    }
                )
            info["fields"] = fields

            if not fields:
                raise RuntimeError("No valid fields found in MS")

            if field_id is None:
                fid = max(fields, key=lambda x: x["rows"])["field_id"]
            else:
                fid = field_id
                if fid not in [f["field_id"] for f in fields]:
                    available = [f["field_id"] for f in fields]
                    raise ValueError(
                        f"Field {fid} not present in MS {path}. "
                        f"Available fields: {available}"
                    )

            info["selected_field_id"] = int(fid)
            info["ra_deg"] = float(ra_list[int(fid)])
            info["dec_deg"] = float(dec_list[int(fid)])
            info["mid_time"] = _time_from_seconds(times[field_ids == fid])
            return info

        except Exception as e:
            logger.error("Failed to read MS %s: %s", path, e)
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

                time_arr = (
                    np.asarray(header["time_array"]) if "time_array" in header else None
                )
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
                    lst = info["mid_time"].sidereal_time(
                        "apparent", longitude=DSA110_LOCATION.lon
                    )
                    ra = (lst - ha_val * u.rad).wrap_at(360 * u.deg)
                    info["ra_deg"] = float(ra.deg)
                else:
                    logger.warning(
                        "Cannot compute RA: missing mid_time or " "ha_phase_center"
                    )

            return info

        except Exception as e:
            logger.error("Failed to read UVH5 %s: %s", path, e)
            raise RuntimeError(f"Error reading UVH5 {path}: {e}") from e

    raise ValueError(
        f"Unsupported file format: {path}. " f"Expected .ms directory or .hdf5 file"
    )
