#!/usr/bin/env python3
"""
UVH5 to CASA Measurement Set Converter.

This module provides a single-file/directory writer for converting UVH5 data
to a CASA Measurement Set (MS). It leverages shared helpers for phasing and
finalization to ensure consistency with the main conversion pipeline.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
from pyuvdata import UVData

from dsa110_contimg.conversion.helpers import (
    phase_to_meridian,
    set_telescope_identity,
)
from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
from dsa110_contimg.utils.exceptions import ConversionError, ValidationError
from dsa110_contimg.utils.runtime_safeguards import (
    log_progress,
    progress_monitor,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _validate_mount_type(mount_type: str) -> str:
    """
    Validate and standardize antenna mount type for CASA compatibility.

    Parameters
    ----------
    mount_type : str
        Input mount type string

    Returns
    -------
    str
        Standardized mount type string recognized by CASA
    """
    if not mount_type:
        return "alt-az"

    # CASA recognized mount types (for reference)
    # valid_types = ["alt-az", "equatorial", "x-y", "spherical"]

    # Normalize the input
    normalized = mount_type.lower().strip()

    # Direct mapping for common variations
    mount_mapping = {
        "alt-az": "alt-az",
        "altaz": "alt-az",
        "alt_az": "alt-az",
        "alt az": "alt-az",
        "az-el": "alt-az",
        "azel": "alt-az",
        "equatorial": "equatorial",
        "eq": "equatorial",
        "x-y": "x-y",
        "xy": "x-y",
        "spherical": "spherical",
        "sphere": "spherical",
    }

    if normalized in mount_mapping:
        return mount_mapping[normalized]

    # Default fallback
    logger.warning(f"Unknown mount type '{mount_type}', defaulting to 'alt-az'")
    return "alt-az"


def _cleanup_temp_files(temp_files: List[str]) -> None:
    """
    Clean up temporary files safely.

    Parameters
    ----------
    temp_files : List[str]
        List of temporary file paths to clean up
    """
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.debug(f"Cleaned up temporary file: {temp_file}")
        except OSError as e:
            logger.warning(f"Could not clean up temporary file {temp_file}: {e}")


def _assess_data_quality(uvd: UVData) -> dict:
    """
    Assess data quality and return recommendations for calibration parameters.

    Parameters
    ----------
    uvd : UVData
        UVData object to assess

    Returns
    -------
    dict
        Dictionary containing quality assessment and parameter recommendations
    """
    quality_info = {
        "total_data_points": uvd.Nblts * uvd.Nfreqs * uvd.Npols,
        "time_span_days": 0.0,
        "freq_span_mhz": 0.0,
        "recommended_solint": "30s",
        "recommended_minsnr": 3.0,
        "data_quality_score": "good",
    }

    # Calculate time span
    if hasattr(uvd, "time_array") and uvd.time_array is not None:
        time_span = np.max(uvd.time_array) - np.min(uvd.time_array)
        quality_info["time_span_days"] = time_span

        # Adjust solution interval based on time span
        if time_span < 0.01:  # Less than ~15 minutes
            quality_info["recommended_solint"] = "12s"
        elif time_span < 0.1:  # Less than ~2.4 hours
            quality_info["recommended_solint"] = "30s"
        else:
            quality_info["recommended_solint"] = "60s"

    # Calculate frequency span
    if hasattr(uvd, "freq_array") and uvd.freq_array is not None:
        freq_span = np.max(uvd.freq_array) - np.min(uvd.freq_array)
        quality_info["freq_span_mhz"] = freq_span / 1e6

        # Adjust SNR threshold based on frequency span
        if freq_span < 50e6:  # Less than 50 MHz
            quality_info["recommended_minsnr"] = 2.0
        elif freq_span < 200e6:  # Less than 200 MHz
            quality_info["recommended_minsnr"] = 3.0
        else:
            quality_info["recommended_minsnr"] = 5.0

    # Assess flagging fraction
    if hasattr(uvd, "flag_array") and uvd.flag_array is not None:
        total_flags = np.sum(uvd.flag_array)
        total_data = uvd.flag_array.size
        flag_fraction = total_flags / total_data if total_data > 0 else 0
        quality_info["flag_fraction"] = flag_fraction

        if flag_fraction > 0.5:
            quality_info["data_quality_score"] = "poor"
            quality_info["recommended_minsnr"] = 2.0
        elif flag_fraction > 0.2:
            quality_info["data_quality_score"] = "fair"
            quality_info["recommended_minsnr"] = 3.0
        else:
            quality_info["data_quality_score"] = "good"

    return quality_info


def _generate_calibration_recommendations(quality_info: dict) -> dict:
    """
    Generate calibration parameter recommendations based on data quality.

    Parameters
    ----------
    quality_info : dict
        Data quality assessment results

    Returns
    -------
    dict
        Dictionary containing recommended calibration parameters
    """
    recommendations = {
        "delay_calibration": {
            "solint": quality_info["recommended_solint"],
            "minsnr": max(2.0, quality_info["recommended_minsnr"] - 1.0),
            "combine": "spw",
            "calmode": "p",
        },
        "bandpass_calibration": {
            "solint": "inf",
            "minsnr": quality_info["recommended_minsnr"],
            "combine": "scan,field",
            "calmode": "bp",
        },
        "gain_calibration": {
            "solint": quality_info["recommended_solint"],
            "minsnr": quality_info["recommended_minsnr"],
            "combine": "scan,field",
            "calmode": "ap",
        },
    }

    # Adjust parameters based on data quality
    if quality_info["data_quality_score"] == "poor":
        recommendations["delay_calibration"]["minsnr"] = 1.5
        recommendations["bandpass_calibration"]["minsnr"] = 2.0
        recommendations["gain_calibration"]["minsnr"] = 2.0
        recommendations["delay_calibration"]["solint"] = "60s"
        recommendations["gain_calibration"]["solint"] = "60s"
    elif quality_info["data_quality_score"] == "fair":
        recommendations["delay_calibration"]["minsnr"] = 2.0
        recommendations["bandpass_calibration"]["minsnr"] = 3.0
        recommendations["gain_calibration"]["minsnr"] = 3.0

    return recommendations


def _write_calibration_recommendations(ms_path: str, recommendations: dict) -> None:
    """
    Write calibration recommendations to a JSON file alongside the MS.

    Parameters
    ----------
    ms_path : str
        Path to the MS file
    recommendations : dict
        Calibration parameter recommendations
    """
    import json

    # Create recommendations file path: write alongside each MS directory
    # If ms_path is a directory (standard for CASA MS), write inside it
    if os.path.isdir(ms_path):
        recommendations_path = os.path.join(ms_path, "calibration_recommendations.json")
    else:
        # Fallback: write next to the file path
        parent_dir = os.path.dirname(ms_path) or "."
        recommendations_path = os.path.join(
            parent_dir, "calibration_recommendations.json"
        )

    try:
        with open(recommendations_path, "w") as f:
            json.dump(recommendations, f, indent=2)
        logger.info(f"Wrote calibration recommendations to: {recommendations_path}")
    except Exception as e:
        logger.warning(f"Could not write calibration recommendations: {e}")


def _phase_data_to_midpoint_reference(
    uvd: UVData,
    reference_time: Optional[float] = None,
    hour_angle_offset_hours: float = 0.0,
) -> UVData:
    """
    Phase the data to RA=LST(t_ref)-H0 and Dec=phase_center_dec at a
    single reference time (default: midpoint of the dump).

    Parameters
    ----------
    uvd : UVData
        UVData object to phase
    reference_time : float, optional
        Reference time in JD. If None, uses the midpoint of time_array.
    hour_angle_offset_hours : float
        Fixed hour-angle offset H0 in hours (default 0 for meridian).

    Returns
    -------
    UVData
        Phased UVData object
    """
    import astropy.units as u
    from astropy.coordinates import EarthLocation, SkyCoord
    from astropy.time import Time

    if uvd.Ntimes == 0:
        return uvd

    # Choose midpoint reference time if not provided
    if reference_time is None:
        tmin = float(np.min(uvd.time_array))
        tmax = float(np.max(uvd.time_array))
        reference_time = 0.5 * (tmin + tmax)

    # Telescope location
    if hasattr(uvd, "telescope_location_lat_lon_alt_deg"):
        lat, lon, alt = uvd.telescope_location_lat_lon_alt_deg
        location = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=alt * u.m)
    else:
        # OVRO fallback - use constants.py (single source of truth)
        from dsa110_contimg.utils.constants import OVRO_LOCATION

        location = OVRO_LOCATION
        logger.warning("Using default OVRO location for phasing")

    tref = Time(reference_time, format="jd")

    # Compute apparent sidereal time at reference time
    lst = tref.sidereal_time("apparent", longitude=location.lon)

    # Phase center declination from UVH5 metadata if available
    dec_rad = None
    if hasattr(uvd, "phase_center_dec") and uvd.phase_center_dec is not None:
        dec_rad = float(uvd.phase_center_dec)
    elif hasattr(uvd, "extra_keywords") and isinstance(uvd.extra_keywords, dict):
        dec_rad = float(uvd.extra_keywords.get("phase_center_dec", 0.0))
    else:
        # Fallback to telescope latitude (not ideal but safe default)
        dec_rad = location.lat.to(u.rad).value

    # Hour angle offset H0 (hours) -> radians
    h0_rad = (hour_angle_offset_hours * u.hourangle).to(u.rad).value
    # Compute apparent-of-date RA at meridian, then convert to ICRS (J2000)
    ra_app = lst.to(u.rad).value - h0_rad
    ra_app = (ra_app + 2 * np.pi) % (2 * np.pi)
    # Transform apparent (CIRS) to ICRS to avoid arcsecond-level offsets
    try:
        cirs = SkyCoord(
            ra=ra_app * u.rad,
            dec=dec_rad * u.rad,
            frame="cirs",
            obstime=tref,
            location=location,
        )
        icrs = cirs.transform_to("icrs")
        ra_rad = icrs.ra.to_value(u.rad)
        dec_rad = icrs.dec.to_value(u.rad)
    except Exception as e:
        logger.warning(
            f"CIRS->ICRS transform failed ({e}); using apparent-of-date coordinates"
        )
        ra_rad = ra_app

    logger.info(
        f"Phasing to reference center at {tref.isot}: RA(ICRS)={ra_rad:.6f} rad, "
        f"Dec(ICRS)={dec_rad:.6f} rad (H0={hour_angle_offset_hours} h)"
    )

    try:
        # pyuvdata expects radians for phase(); cat_name is required
        uvd.phase(ra=ra_rad, dec=dec_rad, epoch="J2000", cat_name="midpoint_ref")
        logger.info("Successfully phased data to midpoint reference")
    except Exception as e:
        logger.warning(f"Explicit phasing failed, leaving original phasing: {e}")

    return uvd


def _fix_mount_type_in_ms(ms_path: str) -> None:
    """
    Fix mount type in MS antenna table to prevent CASA warnings.

    Parameters
    ----------
    ms_path : str
        Path to the MS file
    """
    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path
    ensure_casa_path()

    try:
        import casacore.tables as casatables
        table = casatables.table  # noqa: N816

        # Open the antenna table for read/write
        ant_table = table(ms_path + "/ANTENNA", readonly=False)

        # Get the current mount type values
        mount_types = ant_table.getcol("MOUNT")

        # Fix mount types to CASA-compatible format
        fixed_mount_types = []
        for mount_type in mount_types:
            if mount_type is None or mount_type == "":
                fixed_mount_types.append("alt-az")
            else:
                # Normalize to CASA-compatible format
                normalized = str(mount_type).lower().strip()
                if normalized in [
                    "alt-az",
                    "altaz",
                    "alt_az",
                    "alt az",
                    "az-el",
                    "azel",
                ]:
                    fixed_mount_types.append("alt-az")
                elif normalized in ["equatorial", "eq"]:
                    fixed_mount_types.append("equatorial")
                elif normalized in ["x-y", "xy"]:
                    fixed_mount_types.append("x-y")
                elif normalized in ["spherical", "sphere"]:
                    fixed_mount_types.append("spherical")
                else:
                    fixed_mount_types.append("alt-az")  # Default fallback

        # Update the mount types in the table
        ant_table.putcol("MOUNT", fixed_mount_types)
        ant_table.close()

        logger.info(f"Fixed mount types in MS antenna table: {ms_path}")

    except Exception as e:
        logger.warning(f"Could not fix mount type in MS {ms_path}: {e}")
        # Don't raise exception as this is not critical


def read_uvh5_file(
    filepath: str,
    create_time_binned_fields: bool = False,
    field_time_bin_minutes: float = 5.0,
) -> UVData:
    """
    Read a UVH5 file using pyuvdata.

    Parameters
    ----------
    filepath : str
        Path to the UVH5 file
    create_time_binned_fields : bool
        Whether to create time-binned fields for drift scans
    field_time_bin_minutes : float
        Time bin size in minutes for field creation
        (if create_time_binned_fields=True)

    Returns
    -------
    UVData
        UVData object containing the data

    Raises
    ------
    FileNotFoundError
        If the UVH5 file does not exist
    ValueError
        If the file is not a valid UVH5 file or has critical data issues
    RuntimeError
        If there are unrecoverable errors during processing
    """
    logger.info(f"Reading UVH5 file: {filepath}")

    # Validate input parameters
    validation_errors = []
    if not isinstance(filepath, str) or not filepath.strip():
        validation_errors.append("filepath must be a non-empty string")

    if not isinstance(create_time_binned_fields, bool):
        validation_errors.append("create_time_binned_fields must be a boolean")

    if (
        not isinstance(field_time_bin_minutes, (int, float))
        or field_time_bin_minutes <= 0
    ):
        validation_errors.append("field_time_bin_minutes must be a positive number")

    if validation_errors:
        raise ValidationError(
            errors=validation_errors,
            context={"filepath": filepath, "operation": "read_uvh5"},
            suggestion="Check input parameters and file path",
        )

    # Check if file exists
    if not os.path.exists(filepath):
        raise ConversionError(
            message=f"UVH5 file not found: {filepath}",
            context={"filepath": filepath, "operation": "read"},
            suggestion="Verify the file path is correct and the file exists",
        )

    # Check if file is readable
    if not os.access(filepath, os.R_OK):
        raise ConversionError(
            message=f"Cannot read UVH5 file: {filepath}",
            context={"filepath": filepath, "operation": "read"},
            suggestion="Check file permissions",
        )

    # Check file size (basic sanity check)
    file_size = os.path.getsize(filepath)
    if file_size == 0:
        raise ConversionError(
            message=f"UVH5 file is empty: {filepath}",
            context={"filepath": filepath, "file_size": file_size},
            suggestion="Check that the file was written correctly",
        )

    logger.info(f"File size: {file_size / (1024*1024):.1f} MB")

    # Create UVData object and read the file
    uvd = UVData()

    try:
        # Read with run_check=False to avoid data type validation
        uvd.read_uvh5(filepath, run_check=False)
        logger.info("Successfully loaded UVH5 file into UVData object")
    except Exception as e:
        raise ConversionError(
            message=f"Failed to read UVH5 file: {e}",
            context={"filepath": filepath, "operation": "read_uvh5"},
            suggestion="Check that the file is a valid UVH5 file and not corrupted",
        ) from e

    # Validate basic structure
    structure_errors = []
    if uvd.Nblts == 0:
        structure_errors.append("UVH5 file contains no baseline-time integrations")
    if uvd.Nfreqs == 0:
        structure_errors.append("UVH5 file contains no frequency channels")
    if uvd.Npols == 0:
        structure_errors.append("UVH5 file contains no polarizations")
    if uvd.Ntimes == 0:
        structure_errors.append("UVH5 file contains no time samples")
    if uvd.Nbls == 0:
        structure_errors.append("UVH5 file contains no baselines")

    if structure_errors:
        raise ValidationError(
            errors=structure_errors,
            context={"filepath": filepath, "operation": "validate_structure"},
            suggestion="Check that the UVH5 file contains valid data",
        )

    # Fix common data type issues before validation
    data_type_fixes = 0

    if hasattr(uvd, "uvw_array") and uvd.uvw_array is not None:
        if uvd.uvw_array.dtype != np.float64:
            logger.info(f"Converting uvw_array from {uvd.uvw_array.dtype} to float64")
            uvd.uvw_array = uvd.uvw_array.astype(np.float64)
            data_type_fixes += 1

    # Fix other common float32 issues (do NOT cast flags to float)
    for attr in ["data_array", "nsample_array"]:
        if hasattr(uvd, attr):
            arr = getattr(uvd, attr)
            if arr is not None and arr.dtype == np.float32:
                logger.info(f"Converting {attr} from float32 to float64")
                setattr(uvd, attr, arr.astype(np.float64))
                data_type_fixes += 1
    # Ensure flag_array is boolean
    if hasattr(uvd, "flag_array"):
        arr = getattr(uvd, "flag_array")
        if arr is not None and arr.dtype != np.bool_:
            logger.warning(
                f"Coercing flag_array from {arr.dtype} to boolean; verify upstream writer"
            )
            uvd.flag_array = arr.astype(np.bool_)

    if data_type_fixes > 0:
        logger.info(f"Applied {data_type_fixes} data type fixes")

    # Handle field management for drift scans
    if create_time_binned_fields:
        if hasattr(uvd, "phase_type") and uvd.phase_type == "drift":
            logger.info("Creating time-binned fields for drift scan")
        else:
            logger.info("Creating time-binned fields (assuming drift scan)")

        try:
            uvd = _create_time_binned_fields(uvd, field_time_bin_minutes)
        except Exception as e:
            raise ConversionError(
                message=f"Failed to create time-binned fields: {e}",
                context={
                    "filepath": filepath,
                    "field_time_bin_minutes": field_time_bin_minutes,
                    "operation": "create_time_binned_fields",
                },
                suggestion="Check field_time_bin_minutes parameter and UVData structure",
            ) from e

    # Now run the check with corrected data types
    try:
        uvd.check()
        logger.info("UVData validation passed")
    except Exception as e:
        logger.warning(f"UVData validation failed: {e}")
        # Check if this is a critical error
        error_str = str(e).lower()
        critical_errors = ["no data", "empty", "invalid", "corrupt"]
        if any(crit in error_str for crit in critical_errors):
            raise ValidationError(
                errors=[f"Critical UVData validation error: {e}"],
                context={"filepath": filepath, "operation": "validate_uvdata"},
                suggestion="Check that the UVH5 file contains valid, uncorrupted data",
            ) from e
        # Continue anyway - some issues might not be critical
        logger.warning("Continuing despite validation warnings")

    # Additional data quality checks
    _validate_data_quality(uvd)

    # Assess data quality and get recommendations
    quality_info = _assess_data_quality(uvd)
    calibration_recommendations = _generate_calibration_recommendations(quality_info)

    # Do not modify uvd.telescope_name (observatory id).
    # Mount-type normalization is handled after MS write in
    # _fix_mount_type_in_ms.

    logger.info("Successfully read UVH5 file:")
    logger.info(f"  - Nblts: {uvd.Nblts}")
    logger.info(f"  - Nfreqs: {uvd.Nfreqs}")
    logger.info(f"  - Npols: {uvd.Npols}")
    logger.info(f"  - Ntimes: {uvd.Ntimes}")
    logger.info(f"  - Nbls: {uvd.Nbls}")
    # Some pyuvdata versions do not expose Nfields; attempt a safe fallback
    try:
        nfields = getattr(uvd, "Nfields", None)
        if nfields is None:
            nfields = getattr(uvd, "Nphase", None)
        if nfields is None and hasattr(uvd, "phase_center_catalog"):
            try:
                nfields = len(uvd.phase_center_catalog)
            except Exception:
                nfields = None
        if nfields is not None:
            logger.info(f"  - Nfields: {nfields}")
    except Exception:
        pass

    # Log data quality assessment
    logger.info("Data quality assessment:")
    logger.info(f"  - Quality score: {quality_info['data_quality_score']}")
    logger.info(f"  - Time span: {quality_info['time_span_days']:.3f} days")
    logger.info(f"  - Frequency span: {quality_info['freq_span_mhz']:.1f} MHz")
    logger.info(f"  - Flag fraction: {quality_info.get('flag_fraction', 0):.1%}")

    # Log calibration recommendations
    logger.info("Calibration recommendations:")
    for cal_type, params in calibration_recommendations.items():
        logger.info(
            f"  - {cal_type}: solint={params['solint']}, "
            f"minsnr={params['minsnr']}, combine={params['combine']}"
        )

    return uvd


def _validate_data_quality(uvd: UVData) -> None:
    """
    Perform additional data quality checks on UVData object.

    Parameters
    ----------
    uvd : UVData
        UVData object to validate

    Raises
    ------
    ValueError
        If critical data quality issues are found
    """
    logger.debug("Performing data quality checks...")

    # Check for all flagged data
    if hasattr(uvd, "flag_array") and uvd.flag_array is not None:
        total_flags = np.sum(uvd.flag_array)
        total_data = uvd.flag_array.size
        flag_fraction = total_flags / total_data if total_data > 0 else 0

        if flag_fraction > 0.95:
            logger.warning(f"High flagging fraction: {flag_fraction:.1%}")
        elif flag_fraction == 1.0:
            raise ValidationError(
                errors=["All data is flagged - no usable data"],
                context={
                    "flag_fraction": flag_fraction,
                    "operation": "validate_data_quality",
                },
                suggestion="Check data quality and flagging criteria",
            )

    # Check for NaN or infinite values in data
    if hasattr(uvd, "data_array") and uvd.data_array is not None:
        data = uvd.data_array
        nan_count = np.sum(np.isnan(data))
        inf_count = np.sum(np.isinf(data))

        if nan_count > 0:
            logger.warning(f"Found {nan_count} NaN values in data_array")

        if inf_count > 0:
            logger.warning(f"Found {inf_count} infinite values in data_array")

    # Check for reasonable frequency range
    if hasattr(uvd, "freq_array") and uvd.freq_array is not None:
        freq_min = np.min(uvd.freq_array)
        freq_max = np.max(uvd.freq_array)

        # Check for reasonable radio frequency range (10 MHz to 1 THz)
        if freq_min < 1e7 or freq_max > 1e12:
            logger.warning(
                f"Unusual frequency range: {freq_min/1e6:.1f} - "
                f"{freq_max/1e6:.1f} MHz"
            )

    # Check for reasonable time range
    if hasattr(uvd, "time_array") and uvd.time_array is not None:
        time_span = np.max(uvd.time_array) - np.min(uvd.time_array)

        # Check for reasonable observation duration (1 second to 1 year)
        if time_span < 1 / 86400 or time_span > 365:
            logger.warning(f"Unusual time span: {time_span:.6f} days")

    logger.debug("Data quality checks completed")


def _create_time_binned_fields(uvd: UVData, field_time_bin_minutes: float) -> UVData:
    """
    Create time-binned fields for drift scan data.

    Parameters
    ----------
    uvd : UVData
        UVData object with drift scan data
    field_time_bin_minutes : float
        Time bin size in minutes for field creation

    Returns
    -------
    UVData
        UVData object with time-binned fields
    """
    # from astropy.time import Time
    # from astropy.coordinates import SkyCoord
    # import astropy.units as u

    logger.info(
        f"Creating time-binned fields with {field_time_bin_minutes} minute bins"
    )

    # Robust behavior: Disable custom time-binned FIELD generation until
    # pyuvdata multi-phase center catalog is wired. Returning unmodified UVData
    # avoids writing invalid MS FIELD rows. Use curated grouping and CASA
    # rephasing downstream instead.
    logger.warning(
        "Time-binned FIELD generation is disabled pending proper "
        "phase_center_catalog support; returning original UVData"
    )
    return uvd


def write_ms_file(
    uvd: UVData, output_path: str, add_imaging_columns: bool = True
) -> None:
    """
    Write UVData to CASA Measurement Set.

    Parameters
    ----------
    uvd : UVData
        UVData object to write
    output_path : str
        Path for the output MS file
    add_imaging_columns : bool
        Whether to add imaging columns (MODEL_DATA, CORRECTED_DATA)

    Raises
    ------
    ValueError
        If input parameters are invalid
    RuntimeError
        If MS writing fails
    PermissionError
        If output directory cannot be created or written to
    """
    logger.info(f"Writing MS file: {output_path}")

    # Validate input parameters
    validation_errors = []
    if not isinstance(uvd, UVData):
        validation_errors.append("uvd must be a UVData object")
    if not isinstance(output_path, str) or not output_path.strip():
        validation_errors.append("output_path must be a non-empty string")
    if not isinstance(add_imaging_columns, bool):
        validation_errors.append("add_imaging_columns must be a boolean")

    if validation_errors:
        raise ValidationError(
            errors=validation_errors,
            context={"output_path": output_path, "operation": "write_ms"},
            suggestion="Check input parameters",
        )

    # Validate UVData object
    if uvd.Nblts == 0:
        raise ValidationError(
            errors=["UVData object contains no data to write"],
            context={"output_path": output_path, "operation": "write_ms"},
            suggestion="Ensure the UVData object contains valid data",
        )

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        try:
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Created output directory: {output_dir}")
        except OSError as e:
            raise PermissionError(
                f"Cannot create output directory {output_dir}: {e}"
            ) from e

    # Check if we can write to the output location
    if os.path.exists(output_path):
        if not os.access(output_path, os.W_OK):
            raise PermissionError(f"Cannot write to existing MS: {output_path}")

    # Check available disk space (basic check)
    try:
        statvfs = os.statvfs(output_dir if output_dir else ".")
        free_space = statvfs.f_frsize * statvfs.f_bavail
        # Estimate required space (rough approximation)
        estimated_size = (
            uvd.Nblts * uvd.Nfreqs * uvd.Npols * 8 * 2
        )  # 8 bytes per complex, 2 for safety
        if free_space < estimated_size:
            logger.warning(
                f"Low disk space: {free_space/(1024**3):.1f} GB available, "
                f"estimated need: {estimated_size/(1024**3):.1f} GB"
            )
    except OSError:
        logger.warning("Could not check available disk space")

    # Remove existing MS if it exists
    if os.path.exists(output_path):
        try:
            import shutil

            shutil.rmtree(output_path)
            logger.info(f"Removed existing MS: {output_path}")
        except OSError as e:
            raise PermissionError(
                f"Cannot remove existing MS {output_path}: {e}"
            ) from e

    # Write the MS using pyuvdata
    temp_files: List[str] = []
    try:
        logger.debug("Starting MS write with pyuvdata...")

        # Ensure mount type is properly set for CASA compatibility
        if hasattr(uvd, "telescope_name"):
            # Set mount type to alt-az for CASA compatibility
            original_telescope = getattr(uvd, "telescope_name", "Unknown")
            logger.debug(f"Original telescope name: {original_telescope}")

        uvd.write_ms(output_path, clobber=True, fix_autos=True)
        logger.info(f"Successfully wrote MS: {output_path}")

        # Verify the MS was created successfully
        if not os.path.exists(output_path):
            raise ConversionError(
                message="MS file was not created despite no error",
                context={"output_path": output_path, "operation": "write_ms"},
                suggestion="Check disk space and write permissions",
            )

        # Check MS size
        if os.path.isfile(output_path):
            ms_size = os.path.getsize(output_path)
        else:
            ms_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(output_path)
                for filename in filenames
            )
        logger.info(f"MS file size: {ms_size / (1024*1024):.1f} MB")

    except Exception as e:
        logger.error(f"Failed to write MS: {e}")
        # Clean up partial MS if it exists
        if os.path.exists(output_path):
            try:
                import shutil

                shutil.rmtree(output_path)
                logger.debug("Cleaned up partial MS file")
            except OSError:
                logger.warning("Could not clean up partial MS file")
        # Clean up any temporary files
        _cleanup_temp_files(temp_files)
        raise ConversionError(
            message=f"MS writing failed: {e}",
            context={"output_path": output_path, "operation": "write_ms"},
            suggestion="Check disk space, permissions, and CASA installation",
        ) from e

    finally:
        # Always clean up temporary files
        _cleanup_temp_files(temp_files)

    # Make MS safe for imaging/calibration
    try:
        if add_imaging_columns:
            configure_ms_for_imaging(output_path)
        else:
            # Still ensure FLAG/WEIGHT/WEIGHT_SPECTRUM and mount are sane
            configure_ms_for_imaging(
                output_path,
                ensure_columns=False,
                ensure_flag_and_weight=True,
                do_initweights=True,
                fix_mount=True,
            )
    except Exception as e:
        logger.warning(f"MS imaging configuration warning: {e}")

    # Fix mount type in MS antenna table to prevent CASA warnings
    try:
        _fix_mount_type_in_ms(output_path)
    except Exception as e:
        logger.warning(f"Failed to fix mount type in MS: {e}")
        # This is not critical, so we don't raise an exception


def _ensure_imaging_columns_populated(ms_path: str) -> None:
    """
    Ensure MODEL_DATA and CORRECTED_DATA columns have array values
    for every row, with the same shape/dtype as DATA.

    This is required by CASA concat/ms tools which assume array-valued
    cells in these columns.
    """
    import casacore.tables as casatables
    table = casatables.table  # noqa: N816

    with table(ms_path, readonly=False) as tb:
        nrow = tb.nrows()
        if nrow == 0:
            return
        data0 = tb.getcell("DATA", 0)
        data_shape = data0.shape
        data_dtype = data0.dtype

        for col in ("MODEL_DATA", "CORRECTED_DATA"):
            # If the column does not exist, skip
            if col not in tb.colnames():
                continue
            fixed = 0
            for r in range(nrow):
                try:
                    val = tb.getcell(col, r)
                    # If None or wrong shape, replace
                    if (val is None) or (
                        hasattr(val, "shape") and val.shape != data_shape
                    ):
                        tb.putcell(col, r, np.zeros(data_shape, dtype=data_dtype))
                        fixed += 1
                except Exception:
                    tb.putcell(col, r, np.zeros(data_shape, dtype=data_dtype))
                    fixed += 1
            if fixed > 0:
                logger.debug(f"Populated {fixed} rows in {col} for {ms_path}")


@progress_monitor(operation_name="UVH5 File Conversion", warn_threshold=60.0)
def convert_single_file(
    input_file: str,
    output_file: str,
    add_imaging_columns: bool = True,
    create_time_binned_fields: bool = False,
    field_time_bin_minutes: float = 5.0,
    write_recommendations: bool = True,
    enable_phasing: bool = True,
    phase_reference_time: Optional[float] = None,
) -> None:
    """
    Convert a single UVH5 file to CASA Measurement Set (MS) format.

    This is the main entry point for converting individual UVH5 files to MS
    format. The function handles the complete conversion pipeline including
    phasing, antenna position setup, and MS configuration.

    **Conversion Process:**

    1. Reads UVH5 file using pyuvdata
    2. Sets antenna positions and telescope metadata
    3. Phases data to meridian (if enabled)
    4. Writes to CASA MS format
    5. Configures MS for imaging (if add_imaging_columns=True)

    Parameters
    ----------
    input_file : str
        Path to input UVH5 file. Must exist and be readable.
    output_file : str
        Path to output MS file (directory). Will be created if it doesn't
        exist. Parent directory must exist.
    add_imaging_columns : bool, optional
        Whether to add imaging columns (MODEL_DATA, CORRECTED_DATA) and
        configure MS for imaging. Default: True
    create_time_binned_fields : bool, optional
        Whether to create time-binned fields for drift scans. If True,
        creates separate fields for each time bin. Default: False
    field_time_bin_minutes : float, optional
        Time bin size in minutes for field creation (if
        create_time_binned_fields=True). Default: 5.0
    write_recommendations : bool, optional
        Whether to write conversion recommendations to a file.
        Default: True
    enable_phasing : bool, optional
        Whether to phase data to meridian. Default: True
    phase_reference_time : float, optional
        Reference time for phasing (MJD). If None, uses observation mid-time.
        Default: None

    Raises
    ------
    ValueError
        If input parameters are invalid (e.g., negative time bin size)
    FileNotFoundError
        If input file does not exist
    PermissionError
        If input file is not readable or output directory is not writable
    ConversionError
        If conversion fails (e.g., invalid UVH5 format, write errors)

    Examples
    --------
    Basic conversion:

    >>> from dsa110_contimg.conversion import convert_single_file
    >>> convert_single_file(
    ...     "observation.uvh5",
    ...     "observation.ms"
    ... )

    Convert with time-binned fields for drift scan:

    >>> convert_single_file(
    ...     "drift_scan.uvh5",
    ...     "drift_scan.ms",
    ...     create_time_binned_fields=True,
    ...     field_time_bin_minutes=10.0
    ... )

    Convert without phasing (for testing):

    >>> convert_single_file(
    ...     "test.uvh5",
    ...     "test.ms",
    ...     enable_phasing=False
    ... )

    Notes
    -----
    - The output MS will be a directory, not a single file
    - If the output directory already exists, it will be overwritten
    - For production use, prefer `convert_subband_groups_to_ms()` which
      handles complete subband groups
    - After conversion, the MS is ready for calibration and imaging
    """
    import time

    start_time_sec = time.time()
    log_progress(f"Starting conversion of {input_file}...")
    logger.info(f"Converting {input_file} -> {output_file}")

    # Validate input parameters
    validation_errors = []
    if not isinstance(input_file, str) or not input_file.strip():
        validation_errors.append("input_file must be a non-empty string")
    if not isinstance(output_file, str) or not output_file.strip():
        validation_errors.append("output_file must be a non-empty string")
    if not isinstance(add_imaging_columns, bool):
        validation_errors.append("add_imaging_columns must be a boolean")
    if not isinstance(create_time_binned_fields, bool):
        validation_errors.append("create_time_binned_fields must be a boolean")
    if (
        not isinstance(field_time_bin_minutes, (int, float))
        or field_time_bin_minutes <= 0
    ):
        validation_errors.append("field_time_bin_minutes must be a positive number")

    if validation_errors:
        raise ValidationError(
            errors=validation_errors,
            context={
                "input_file": input_file,
                "output_file": output_file,
                "operation": "convert_single_file",
            },
            suggestion="Check input parameters",
        )

    # Check if input and output are the same file
    if os.path.abspath(input_file) == os.path.abspath(output_file):
        raise ValidationError(
            errors=["Input and output files cannot be the same"],
            context={
                "input_file": input_file,
                "output_file": output_file,
                "operation": "convert_single_file",
            },
            suggestion="Use different paths for input and output files",
        )

    # Track conversion start time
    import time

    start_time = time.time()

    try:
        # Read UVH5 file
        logger.debug("Reading UVH5 file...")
        uvd = read_uvh5_file(
            input_file, create_time_binned_fields, field_time_bin_minutes
        )

        # Ensure telescope name + location are set before any downstream phasing/writes
        try:
            from os import getenv as _getenv

            set_telescope_identity(
                uvd,
                _getenv("PIPELINE_TELESCOPE_NAME", "DSA_110"),
            )
        except Exception:
            logger.debug("set_telescope_identity best-effort failed", exc_info=True)

        # Phase data to meridian with time-dependent phase centers (RA=LST(t), Dec from UVH5)
        if enable_phasing:
            logger.info("Phasing to meridian with time-dependent phase centers")
            phase_to_meridian(uvd)
        else:
            logger.info("Skipping explicit phasing (using original phasing)")

        # Write MS file
        logger.debug("Writing MS file...")
        write_ms_file(uvd, output_file, add_imaging_columns)

        # Write calibration recommendations if requested
        if write_recommendations:
            try:
                quality_info = _assess_data_quality(uvd)
                recommendations = _generate_calibration_recommendations(quality_info)
                _write_calibration_recommendations(output_file, recommendations)
            except Exception as e:
                logger.warning(f"Could not write calibration recommendations: {e}")

        # Calculate conversion time
        conversion_time = time.time() - start_time
        logger.info(
            f"Conversion completed successfully in " f"{conversion_time:.1f} seconds"
        )
        log_progress(
            f"Completed conversion of {input_file} -> {output_file}", start_time_sec
        )

    except Exception as e:
        conversion_time = time.time() - start_time
        logger.error(f"Conversion failed after {conversion_time:.1f} seconds: {e}")
        raise


def find_uvh5_files(input_dir: str, pattern: str = "*.hdf5") -> List[str]:
    """
    Find UVH5 files in a directory.

    Parameters
    ----------
    input_dir : str
        Directory to search
    pattern : str
        File pattern to match

    Returns
    -------
    List[str]
        List of UVH5 file paths
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    # Find files matching pattern
    files = list(input_path.glob(pattern))
    files.sort()  # Sort for consistent ordering

    logger.info(f"Found {len(files)} UVH5 files in {input_dir}")
    return [str(f) for f in files]


@progress_monitor(operation_name="UVH5 Directory Conversion", warn_threshold=600.0)
def convert_directory(
    input_dir: str,
    output_dir: str,
    pattern: str = "*.hdf5",
    add_imaging_columns: bool = True,
    create_time_binned_fields: bool = False,
    field_time_bin_minutes: float = 5.0,
    write_recommendations: bool = True,
    enable_phasing: bool = True,
    phase_reference_time: Optional[float] = None,
) -> None:
    """
    Convert all UVH5 files in a directory to MS format.

    Parameters
    ----------
    input_dir : str
        Input directory containing UVH5 files
    output_dir : str
        Output directory for MS files
    pattern : str
        File pattern to match
    add_imaging_columns : bool
        Whether to add imaging columns
    create_time_binned_fields : bool
        Whether to create time-binned fields for drift scans
    field_time_bin_minutes : float
        Time bin size in minutes for field creation

    Raises
    ------
    ValueError
        If input parameters are invalid
    FileNotFoundError
        If input directory does not exist
    RuntimeError
        If directory conversion fails
    """
    # Validate input parameters
    validation_errors = []
    if not isinstance(input_dir, str) or not input_dir.strip():
        validation_errors.append("input_dir must be a non-empty string")
    if not isinstance(output_dir, str) or not output_dir.strip():
        validation_errors.append("output_dir must be a non-empty string")
    if not isinstance(pattern, str) or not pattern.strip():
        validation_errors.append("pattern must be a non-empty string")
    if not isinstance(add_imaging_columns, bool):
        validation_errors.append("add_imaging_columns must be a boolean")
    if not isinstance(create_time_binned_fields, bool):
        validation_errors.append("create_time_binned_fields must be a boolean")
    if (
        not isinstance(field_time_bin_minutes, (int, float))
        or field_time_bin_minutes <= 0
    ):
        validation_errors.append("field_time_bin_minutes must be a positive number")

    if validation_errors:
        raise ValidationError(
            errors=validation_errors,
            context={
                "input_dir": input_dir,
                "output_dir": output_dir,
                "operation": "convert_directory",
            },
            suggestion="Check input parameters",
        )

    # Check if input directory exists
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    if not os.path.isdir(input_dir):
        raise ValueError(f"Input path is not a directory: {input_dir}")

    # Find all UVH5 files
    try:
        uvh5_files = find_uvh5_files(input_dir, pattern)
    except Exception as e:
        raise RuntimeError(f"Failed to find UVH5 files: {e}") from e

    import time

    start_time_sec = time.time()
    log_progress(f"Starting directory conversion: {input_dir} -> {output_dir}...")

    if not uvh5_files:
        logger.warning(f"No UVH5 files found in {input_dir} with pattern '{pattern}'")
        return

    logger.info(f"Found {len(uvh5_files)} UVH5 files to convert")

    # Create output directory
    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.debug(f"Created output directory: {output_dir}")
    except OSError as e:
        raise PermissionError(
            f"Cannot create output directory {output_dir}: {e}"
        ) from e

    # Track conversion statistics
    import time

    start_time = time.time()
    successful_conversions = 0
    failed_conversions = 0

    # Convert each file
    for i, uvh5_file in enumerate(uvh5_files, 1):
        logger.info(f"Processing file {i}/{len(uvh5_files)}: {uvh5_file}")

        # Create output filename
        input_path = Path(uvh5_file)
        output_file = os.path.join(output_dir, f"{input_path.stem}.ms")

        try:
            convert_single_file(
                uvh5_file,
                output_file,
                add_imaging_columns,
                create_time_binned_fields,
                field_time_bin_minutes,
                write_recommendations,
                enable_phasing,
                phase_reference_time,
            )
            successful_conversions += 1
            logger.info(f"✓ Successfully converted {uvh5_file}")

        except Exception as e:
            failed_conversions += 1
            logger.error(f"✗ Failed to convert {uvh5_file}: {e}")
            continue

    # Report final statistics
    total_time = time.time() - start_time_sec
    logger.info(f"Directory conversion completed in {total_time:.1f} seconds")
    logger.info(
        f"Successfully converted: {successful_conversions}/" f"{len(uvh5_files)} files"
    )
    log_progress(
        f"Completed directory conversion: {successful_conversions}/{len(uvh5_files)} files processed",
        start_time_sec,
    )

    if failed_conversions > 0:
        logger.warning(
            f"Failed conversions: {failed_conversions}/" f"{len(uvh5_files)} files"
        )
        if failed_conversions == len(uvh5_files):
            raise ConversionError(
                message="All file conversions failed",
                context={
                    "input_dir": input_dir,
                    "total_files": len(uvh5_files),
                    "failed_files": failed_conversions,
                    "operation": "convert_directory",
                },
                suggestion="Check input files, disk space, and CASA installation",
            )

    logger.info(f"Output directory: {output_dir}")


def add_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments to the parser."""
    parser.add_argument(
        "input_path",
        help="Path to a UVH5 file or a directory of UVH5 files.",
    )
    parser.add_argument(
        "output_path",
        help="Path to the output Measurement Set.",
    )
    parser.add_argument(
        "--add-imaging-columns",
        action="store_true",
        help="Add MODEL_DATA and CORRECTED_DATA columns.",
    )
    parser.add_argument(
        "--create-time-binned-fields",
        action="store_true",
        help="Create a new FIELD_ID for each 5-minute chunk of data.",
    )
    parser.add_argument(
        "--field-time-bin-minutes",
        type=float,
        default=5.0,
        help="Time bin size in minutes for creating new FIELD_IDs.",
    )
    parser.add_argument(
        "--write-recommendations",
        action="store_true",
        help="Write recommendations to a file.",
    )
    parser.add_argument(
        "--enable-phasing",
        action="store_true",
        help="Enable phasing of the data.",
    )
    parser.add_argument(
        "--phase-reference-time",
        type=str,
        default=None,
        help="Reference time for phasing (YYYY-MM-DDTHH:MM:SS).",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the parser for the converter."""
    parser = argparse.ArgumentParser(
        description="Convert UVH5 to MS",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_args(parser)
    return parser


def main(args: argparse.Namespace = None) -> int:
    """Main function for the converter."""
    if args is None:
        parser = create_parser()
        args = parser.parse_args()

    # Configure logging
    # Note: logging is now handled by the main CLI entrypoint

    convert_single_file(
        args.input_path,
        args.output_path,
        add_imaging_columns=args.add_imaging_columns,
        create_time_binned_fields=args.create_time_binned_fields,
        field_time_bin_minutes=args.field_time_bin_minutes,
        write_recommendations=args.write_recommendations,
        enable_phasing=args.enable_phasing,
        phase_reference_time=args.phase_reference_time,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
