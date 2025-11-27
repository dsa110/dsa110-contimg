"""
Validation utilities for UVH5 files, MS files, and calibrator data.

This module provides validation functions that can be used independently
or as part of the conversion CLI.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import astropy.units as u
import numpy as np
from astropy.time import Time

from dsa110_contimg.calibration.catalogs import read_vla_parsed_catalog_csv
from dsa110_contimg.calibration.schedule import previous_transits
from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
    _peek_uvh5_phase_and_midtime,
    find_subband_groups,
)

logger = logging.getLogger(__name__)


@dataclass
class HDF5ValidationResult:
    """Result of HDF5 file validation."""

    valid: bool
    errors: List[str]
    warnings: List[str]
    file_path: str
    has_time_array: bool = False
    has_data: bool = False
    time_range: Optional[Tuple[Time, Time]] = None
    n_antennas: Optional[int] = None
    n_frequencies: Optional[int] = None
    phase_center_dec_deg: Optional[float] = None


@dataclass
class CalibratorTransitValidationResult:
    """Result of calibrator transit validation."""

    found: bool
    transit_time: Optional[Time] = None
    data_available: bool = False
    files: List[str] = None
    group_id: Optional[str] = None
    dec_match: bool = False
    dec_diff_deg: Optional[float] = None
    errors: List[str] = None
    warnings: List[str] = None


def validate_hdf5_file(file_path: str, check_readable: bool = True) -> HDF5ValidationResult:
    """
    Validate a single UVH5 HDF5 file.

    Args:
        file_path: Path to HDF5 file
        check_readable: Whether to check if file is readable

    Returns:
        HDF5ValidationResult with validation status
    """
    errors = []
    warnings = []

    if not os.path.exists(file_path):
        return HDF5ValidationResult(
            valid=False,
            errors=[f"File does not exist: {file_path}"],
            warnings=[],
            file_path=file_path,
        )

    if check_readable and not os.access(file_path, os.R_OK):
        return HDF5ValidationResult(
            valid=False,
            errors=[f"File is not readable: {file_path}"],
            warnings=[],
            file_path=file_path,
        )

    # Try to read HDF5 structure
    has_time_array = False
    has_data = False
    time_range = None
    n_antennas = None
    n_frequencies = None
    phase_center_dec_deg = None

    try:
        from dsa110_contimg.utils.hdf5_io import open_uvh5_metadata

        with open_uvh5_metadata(file_path) as f:
            # Check for time_array
            if "time_array" in f:
                has_time_array = True
                time_arr = np.asarray(f["time_array"])
                if len(time_arr) > 0:
                    t_min = Time(time_arr.min(), format="jd")
                    t_max = Time(time_arr.max(), format="jd")
                    time_range = (t_min, t_max)
            elif "Header" in f and "time_array" in f["Header"]:
                has_time_array = True
                time_arr = np.asarray(f["Header"]["time_array"])
                if len(time_arr) > 0:
                    t_min = Time(time_arr.min(), format="jd")
                    t_max = Time(time_arr.max(), format="jd")
                    time_range = (t_min, t_max)

            # Check for Data group
            if "Data" in f:
                has_data = True
            elif "Header" in f and "Data" in f["Header"]:
                has_data = True

            # Try to get phase center declination
            try:
                _, pt_dec, mid_time = _peek_uvh5_phase_and_midtime(file_path)
                phase_center_dec_deg = float(pt_dec.to_value(u.deg))
            except Exception as e:
                warnings.append(f"Could not read phase center declination: {e}")

            # Check for antenna information
            if "Header" in f:
                header = f["Header"]
                if "antenna_numbers" in header:
                    n_antennas = len(np.asarray(header["antenna_numbers"]))
                elif "Nants_data" in header:
                    n_antennas = int(np.asarray(header["Nants_data"]))

            # Check for frequency information
            if "freq_array" in f:
                freq_arr = np.asarray(f["freq_array"])
                n_frequencies = len(freq_arr)
            elif "Header" in f and "freq_array" in f["Header"]:
                freq_arr = np.asarray(f["Header"]["freq_array"])
                n_frequencies = len(freq_arr)

    except Exception as e:
        errors.append(f"Failed to read HDF5 structure: {e}")
        return HDF5ValidationResult(
            valid=False,
            errors=errors,
            warnings=warnings,
            file_path=file_path,
            has_time_array=has_time_array,
            has_data=has_data,
        )

    # Validate structure
    if not has_time_array:
        errors.append("Missing time_array (required for UVH5)")
    if not has_data:
        warnings.append("No Data group found (file may be empty or header-only)")

    valid = len(errors) == 0

    return HDF5ValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings,
        file_path=file_path,
        has_time_array=has_time_array,
        has_data=has_data,
        time_range=time_range,
        n_antennas=n_antennas,
        n_frequencies=n_frequencies,
        phase_center_dec_deg=phase_center_dec_deg,
    )


def validate_hdf5_files(file_paths: List[str]) -> Dict[str, HDF5ValidationResult]:
    """
    Validate multiple HDF5 files.

    Args:
        file_paths: List of file paths to validate

    Returns:
        Dictionary mapping file paths to validation results
    """
    results = {}
    for file_path in file_paths:
        results[file_path] = validate_hdf5_file(file_path)
    return results


def validate_calibrator_transit(
    calibrator_name: str,
    input_dir: Path,
    transit_time: Optional[Time] = None,
    window_minutes: int = 60,
    max_days_back: int = 30,
    dec_tolerance_deg: float = 2.0,
    catalogs: Optional[List[Path]] = None,
) -> CalibratorTransitValidationResult:
    """
    Validate that calibrator transit data is available.

    Args:
        calibrator_name: Name of calibrator (e.g., '0834+555')
        input_dir: Directory containing UVH5 files
        transit_time: Optional specific transit time (searches recent if not provided)
        window_minutes: Search window around transit
        max_days_back: Maximum days to search back
        dec_tolerance_deg: Declination tolerance for matching
        catalogs: Optional calibrator catalog paths for lookup

    Returns:
        CalibratorTransitValidationResult with validation status
    """
    errors = []
    warnings = []

    try:
        # Initialize calibrator service
        from dsa110_contimg.conversion.config import CalibratorMSConfig

        config = CalibratorMSConfig(
            input_dir=input_dir,
            output_dir=Path("/tmp"),  # Dummy, not used for validation
            products_db=Path("/tmp/dummy.db"),  # Dummy
            catalogs=catalogs or [],
        )
        service = CalibratorMSGenerator.from_config(config, verbose=False)

        # Find transit
        if transit_time is None:
            # Find most recent transit
            transit_info = service.find_transit(
                calibrator_name,
                window_minutes=window_minutes,
                max_days_back=max_days_back,
            )
        else:
            transit_info = service.find_transit(
                calibrator_name,
                transit_time=transit_time,
                window_minutes=window_minutes,
                max_days_back=max_days_back,
            )

        if not transit_info:
            errors.append(
                f"No transit found for calibrator {calibrator_name} "
                f"(searched last {max_days_back} days)"
            )
            return CalibratorTransitValidationResult(found=False, errors=errors, warnings=warnings)

        # Validate data availability
        files = transit_info.get("files", [])
        if not files:
            errors.append("Transit found but no HDF5 files available")
            return CalibratorTransitValidationResult(
                found=True,
                transit_time=Time(transit_info["transit_iso"]),
                data_available=False,
                errors=errors,
                warnings=warnings,
            )

        # Validate file existence
        missing_files = [f for f in files if not os.path.exists(f)]
        if missing_files:
            errors.append(f"{len(missing_files)} files missing: {missing_files[:3]}...")

        # Check declination match
        dec_match = True
        dec_diff_deg = None
        try:
            # Get expected declination from catalog
            if catalogs:
                catalog_df = read_vla_parsed_catalog_csv(catalogs[0])
                if calibrator_name in catalog_df.index:
                    expected_dec = catalog_df.loc[calibrator_name, "dec_deg"]
                else:
                    # Try to find by pattern
                    matches = catalog_df[catalog_df.index.str.contains(calibrator_name)]
                    if not matches.empty:
                        expected_dec = matches.iloc[0]["dec_deg"]
                    else:
                        expected_dec = None
            else:
                expected_dec = None

            # Get actual declination from first file
            if files and expected_dec is not None:
                _, pt_dec, _ = _peek_uvh5_phase_and_midtime(files[0])
                actual_dec = float(pt_dec.to_value(u.deg))
                dec_diff_deg = abs(actual_dec - expected_dec)
                if dec_diff_deg > dec_tolerance_deg:
                    dec_match = False
                    warnings.append(
                        f"Declination mismatch: expected {expected_dec:.2f}°, "
                        f"actual {actual_dec:.2f}° (diff: {dec_diff_deg:.2f}°)"
                    )
        except Exception as e:
            warnings.append(f"Could not validate declination match: {e}")

        transit_time_obj = Time(transit_info["transit_iso"])

        return CalibratorTransitValidationResult(
            found=True,
            transit_time=transit_time_obj,
            data_available=len(missing_files) == 0,
            files=files,
            group_id=transit_info.get("group_id"),
            dec_match=dec_match,
            dec_diff_deg=dec_diff_deg,
            errors=errors if missing_files else [],
            warnings=warnings,
        )

    except Exception as e:
        errors.append(f"Validation failed: {e}")
        return CalibratorTransitValidationResult(found=False, errors=errors, warnings=warnings)


def find_calibrator_sources_in_data(
    input_dir: Path,
    catalog_path: Optional[Path] = None,
    dec_tolerance_deg: float = 2.0,
    time_range: Optional[Tuple[Time, Time]] = None,
) -> List[Dict]:
    """
    Find calibrator sources that have data available in the input directory.

    Args:
        input_dir: Directory containing UVH5 files
        catalog_path: Path to calibrator catalog CSV
        dec_tolerance_deg: Declination tolerance for matching
        time_range: Optional time range to search (defaults to all available data)

    Returns:
        List of dictionaries with calibrator info and data availability
    """
    results = []

    if catalog_path is None:
        # Try to find default catalog
        default_paths = [
            Path("/data/dsa110-contimg/data/catalogs/vla_calibrators_parsed.csv"),
            Path("/data/dsa110-contimg/data/catalogs/calibrators.csv"),
        ]
        for path in default_paths:
            if path.exists():
                catalog_path = path
                break

        if catalog_path is None:
            logger.warning("No calibrator catalog found, cannot find sources")
            return results

    try:
        catalog_df = read_vla_parsed_catalog_csv(catalog_path)

        # Scan for available data groups
        if time_range:
            time_range[0].iso
            end_time = time_range[1].iso
        else:
            # Scan all available data
            import glob

            files = glob.glob(str(input_dir / "*_sb??.hdf5"))
            if not files:
                return results

            # Get time range from files
            from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                _parse_timestamp_from_filename,
            )

            times = []
            for f in files:
                ts = _parse_timestamp_from_filename(os.path.basename(f))
                if ts:
                    times.append(ts)
            if not times:
                return results

            min(times).iso
            end_time = max(times).iso

        # For each calibrator, check if data exists
        for cal_name in catalog_df.index:
            try:
                ra_deg = catalog_df.loc[cal_name, "ra_deg"]
                dec_deg = catalog_df.loc[cal_name, "dec_deg"]
                flux_jy = catalog_df.loc[cal_name, "flux_jy"]

                # Find transit times in range
                transits = previous_transits(
                    ra_deg,
                    start_time=Time(end_time),
                    n=100,  # Check many transits
                )

                # Filter to time range
                valid_transits = [
                    t
                    for t in transits
                    if time_range is None or (time_range[0] <= t <= time_range[1])
                ]

                # For each transit, check if data exists
                for transit in valid_transits[:10]:  # Limit to first 10
                    groups = find_subband_groups(
                        str(input_dir),
                        (transit - 30 * u.min).iso,
                        (transit + 30 * u.min).iso,
                        spw=[f"sb{i:02d}" for i in range(16)],
                    )

                    if groups:
                        # Check declination match
                        for group_files in groups:
                            try:
                                _, pt_dec, _ = _peek_uvh5_phase_and_midtime(group_files[0])
                                actual_dec = float(pt_dec.to_value(u.deg))
                                dec_diff = abs(actual_dec - dec_deg)

                                if dec_diff <= dec_tolerance_deg:
                                    results.append(
                                        {
                                            "calibrator": cal_name,
                                            "ra_deg": ra_deg,
                                            "dec_deg": dec_deg,
                                            "flux_jy": flux_jy,
                                            "transit_time": transit.iso,
                                            "data_available": True,
                                            "files": group_files,
                                            "dec_diff_deg": dec_diff,
                                        }
                                    )
                                    break  # Found match, move to next calibrator
                            except Exception:
                                continue
                        if any(g for g in groups):
                            break  # Found data for this calibrator
            except Exception as e:
                logger.debug(f"Error checking calibrator {cal_name}: {e}")
                continue

    except Exception as e:
        logger.error(f"Failed to find calibrator sources: {e}")

    return results
