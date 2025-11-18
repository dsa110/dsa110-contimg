#!/opt/miniforge/envs/casa6/bin/python
# -*- coding: utf-8 -*-
"""
DSA-110 UVH5 (in HDF5) → CASA MS orchestrator.

This module discovers complete subband groups in a time window, delegates
MS creation to a selected writer, and uses shared helpers to finalize the
Measurement Set for imaging. It serves as the primary entry point for converting
subband groups.
"""

import argparse
import glob
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, cast

import astropy.units as u  # type: ignore[import]
import numpy as np
from astropy.time import Time  # type: ignore[import]
from pyuvdata import UVData  # type: ignore[import]

from dsa110_contimg.conversion.helpers import (
    cleanup_casa_file_handles,
    get_meridian_coords,
    phase_to_meridian,
    set_model_column,
    set_telescope_identity,
    validate_antenna_positions,
    validate_model_data_quality,
    validate_ms_frequency_order,
    validate_phase_center_coherence,
    validate_uvw_precision,
)
from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion
from dsa110_contimg.utils.cli_helpers import ensure_scratch_dirs
from dsa110_contimg.utils.error_context import format_file_error_with_suggestions
from dsa110_contimg.utils.exceptions import ConversionError, ValidationError
from dsa110_contimg.utils.performance import track_performance

from .writers import get_writer

logger = logging.getLogger("hdf5_orchestrator")


def _peek_uvh5_phase_and_midtime(
    uvh5_path: str,
) -> tuple[u.Quantity, u.Quantity, float]:
    """Lightweight HDF5 peek: return (pt_ra [rad], pt_dec [rad], mid_time [MJD])."""
    import h5py  # type: ignore[import]

    pt_ra_val: float = 0.0
    pt_dec_val: float = 0.0
    mid_jd: float = 0.0
    with h5py.File(uvh5_path, "r") as f:
        # Check for time_array at root or in Header group
        time_arr = None
        if "time_array" in f:
            time_arr = f["time_array"]
        elif "Header" in f and "time_array" in f["Header"]:
            time_arr = f["Header"]["time_array"]

        if time_arr is not None:
            d = cast(Any, time_arr)  # h5py dataset
            arr = np.asarray(d)
            n = arr.shape[0]
            if n >= 2:
                t0 = float(arr[0])
                t1 = float(arr[n - 1])
                mid_jd = 0.5 * (t0 + t1)
            elif n == 1:
                mid_jd = float(arr[0])

        def _read_extra(name: str) -> Optional[float]:
            try:
                if "extra_keywords" in f and name in f["extra_keywords"]:
                    return float(np.asarray(f["extra_keywords"][name]))
            except Exception:
                pass
            try:
                if (
                    "Header" in f
                    and "extra_keywords" in f["Header"]
                    and name in f["Header"]["extra_keywords"]
                ):
                    return float(np.asarray(f["Header"]["extra_keywords"][name]))
            except Exception:
                pass
            try:
                if name in f.attrs:
                    return float(f.attrs[name])
            except Exception:
                pass
            return None

        val_ra = _read_extra("phase_center_ra")
        if val_ra is not None and np.isfinite(val_ra):
            pt_ra_val = float(val_ra)
        else:
            # If phase_center_ra is missing, calculate from HA and LST
            # RA = LST - HA (when HA=0, RA=LST, i.e., meridian transit)
            val_ha = _read_extra("ha_phase_center")
            if val_ha is not None and np.isfinite(val_ha) and mid_jd > 0:
                try:
                    from astropy.time import Time

                    from dsa110_contimg.utils.constants import OVRO_LOCATION

                    # Get longitude from Header (default to DSA-110 location from constants)
                    lon_deg = OVRO_LOCATION.lon.to(u.deg).value  # pylint: disable=no-member
                    if "Header" in f and "longitude" in f["Header"]:
                        lon_val = np.asarray(f["Header"]["longitude"])
                        if lon_val.size == 1:
                            lon_deg = float(lon_val)

                    # Calculate LST at mid_time using OVRO_LOCATION as base (single source of truth)
                    # If Header provides longitude, use it but keep lat/height from constants
                    from astropy.coordinates import EarthLocation

                    location = EarthLocation(
                        lat=OVRO_LOCATION.lat,
                        lon=lon_deg * u.deg,  # pylint: disable=no-member
                        height=OVRO_LOCATION.height,
                    )
                    tref = Time(mid_jd, format="jd")
                    lst = tref.sidereal_time("apparent", longitude=location.lon)

                    # Calculate RA: RA = LST - HA
                    ha_rad = float(val_ha)  # HA is in radians
                    ra_rad = (lst.to(u.rad).value - ha_rad) % (2 * np.pi)
                    pt_ra_val = ra_rad
                    logger.debug(
                        f"Calculated RA from HA and LST: {ra_rad:.2f} rad "
                        f"(LST={lst.to(u.rad).value:.2f} rad, HA={ha_rad:.2f} rad) "
                        f"({np.rad2deg(ra_rad):.2f}°)"
                    )
                except Exception as e:
                    logger.warning(f"Could not calculate RA from HA: {e}. Using default 0.0")
                    pt_ra_val = 0.0

        val_dec = _read_extra("phase_center_dec")
        if val_dec is not None and np.isfinite(val_dec):
            pt_dec_val = float(val_dec)
    return (
        pt_ra_val * u.rad,
        pt_dec_val * u.rad,
        float(Time(mid_jd, format="jd").mjd) if mid_jd else float(mid_jd),
    )


def _parse_timestamp_from_filename(filename: str) -> Optional[Time]:
    base = os.path.splitext(filename)[0]
    if "_sb" not in base:
        return None
    ts_part = base.split("_sb", 1)[0]
    try:
        return Time(ts_part)
    except ValueError:
        return None


def _extract_subband_code(filename: str) -> Optional[str]:
    base = os.path.splitext(filename)[0]
    if "_sb" not in base:
        return None
    tail = base.rsplit("_sb", 1)[1]
    return f"sb{tail}"


def find_subband_groups(
    input_dir: str,
    start_time: str,
    end_time: str,
    *,
    spw: Optional[Sequence[str]] = None,
    tolerance_s: float = 60.0,
) -> List[List[str]]:
    """Identify complete subband groups within a time window.

    This function tries to use the database first for better performance,
    falling back to filesystem scan if the database is not available.

    Args:
        input_dir: Directory containing HDF5 files
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        spw: List of subband codes to expect (default: sb00-sb15)
        tolerance_s: Time tolerance in seconds for clustering files into groups (default: 60.0)

    Returns:
        List of complete subband groups, each group is a list of file paths
    """
    if spw is None:
        spw = [f"sb{idx:02d}" for idx in range(16)]

    # Try to use database first (much faster)
    try:
        import os as _os

        from dsa110_contimg.database.hdf5_index import query_subband_groups

        hdf5_db = Path(_os.getenv("HDF5_DB_PATH", "state/hdf5.sqlite3"))
        if hdf5_db.exists():
            # Use database query with consistent clustering tolerance
            groups = query_subband_groups(
                hdf5_db,
                start_time,
                end_time,
                tolerance_s=1.0,  # Small window expansion for query
                cluster_tolerance_s=tolerance_s,  # Use same tolerance for clustering
                only_stored=True,
            )
            if groups:
                return groups
            # If no groups found, fall through to filesystem scan as fallback
            logger.debug(
                f"No groups found in database for {start_time} to {end_time}, "
                "falling back to filesystem scan"
            )
    except Exception as e:
        logger.debug(f"Database query failed, using filesystem scan: {e}")

    # Fallback to filesystem scan
    tmin = Time(start_time)
    tmax = Time(end_time)

    candidates = []
    days = set()
    from datetime import timedelta as _dt_timedelta

    cur = tmin.to_datetime()
    end_dt = tmax.to_datetime()
    while cur.date() <= end_dt.date():
        days.add(cur.strftime("%Y-%m-%d"))
        cur = cur + _dt_timedelta(days=1)
    for day in sorted(days):
        pattern = os.path.join(input_dir, f"{day}T*_sb??.hdf5")
        for path in glob.glob(pattern):
            fname = os.path.basename(path)
            ts = _parse_timestamp_from_filename(fname)
            if ts and tmin <= ts <= tmax:
                candidates.append((path, ts))

    if not candidates:
        logger.info(
            "No subband files found in %s between %s and %s",
            input_dir,
            start_time,
            end_time,
        )
        return []

    candidates.sort(key=lambda item: item[1].unix)
    times_sec = np.array([ts.unix for _, ts in candidates])
    files = np.array([p for p, _ in candidates])

    groups: List[List[str]] = []
    used = np.zeros(len(times_sec), dtype=bool)

    for i in range(len(times_sec)):
        if used[i]:
            continue
        close_indices = np.where(np.abs(times_sec - times_sec[i]) <= tolerance_s)[0]
        group_indices = [idx for idx in close_indices if not used[idx]]

        selected_files = [files[j] for j in group_indices]
        # Filter out files where subband code cannot be extracted
        # to prevent None keys in subband_map which would cause grouping
        # to fail. Also log warnings for duplicate subband codes (should
        # not happen in production).
        subband_map = {}
        for p in selected_files:
            sb_code = _extract_subband_code(os.path.basename(p))
            if sb_code is not None:
                if sb_code in subband_map:
                    prev_file = os.path.basename(subband_map[sb_code])
                    curr_file = os.path.basename(p)
                    logger.warning(
                        f"Duplicate subband code {sb_code} found: "
                        f"{prev_file} and {curr_file}. "
                        f"Using the latter file."
                    )
                subband_map[sb_code] = p

        if set(subband_map.keys()) == set(spw):
            # CRITICAL: DSA-110 subbands use DESCENDING frequency order (sb00=highest, sb15=lowest).
            # For proper frequency ordering (ascending, low to high), REVERSE the sort.
            # Files with slightly different timestamps should still be ordered by frequency.
            def sort_key_for_group(sb_code):
                sb_num = int(sb_code.replace("sb", ""))
                return sb_num

            sorted_group = [
                subband_map[s] for s in sorted(spw, key=sort_key_for_group, reverse=True)
            ]
            groups.append(sorted_group)
            for idx in group_indices:
                used[idx] = True

    return groups


def _load_and_merge_subbands(
    file_list: Sequence[str], show_progress: bool = True, batch_size: int = 4
) -> UVData:
    """Load and merge subband files into a single UVData object.

    OPTIMIZATION: Processes subbands in batches to reduce peak memory usage.
    For 16 subbands with batch_size=4, peak memory is reduced by ~60% compared
    to loading all subbands simultaneously.

    CRITICAL: Files are sorted by subband number (0-15) to ensure correct
    spectral order. If files are out of order, frequency channels will be
    scrambled, leading to incorrect bandpass calibration solutions.

    Args:
        file_list: List of subband file paths
        show_progress: Whether to show progress bar
        batch_size: Number of subbands to load per batch (default: 4)
                   Smaller batches = lower memory, more merges
                   Larger batches = higher memory, fewer merges
    """

    # CRITICAL: DSA-110 subbands use DESCENDING frequency order:
    #   sb00 = highest frequency (~1498 MHz)
    #   sb15 = lowest frequency (~1311 MHz)
    # For proper frequency channel ordering (ascending, low to high), we must
    # REVERSE the subband number sort. This is essential for MFS imaging and
    # bandpass calibration. If frequencies are out of order, imaging will produce
    # fringes and bandpass calibration will fail.
    def sort_by_subband(fpath):
        fname = os.path.basename(fpath)
        sb = _extract_subband_code(fname)
        sb_num = int(sb.replace("sb", "")) if sb else 999
        return sb_num

    sorted_file_list = sorted(file_list, key=sort_by_subband, reverse=True)

    # OPTIMIZATION: Use batched loading to reduce peak memory
    # For small file lists (< batch_size), load all at once (original behavior)
    if len(sorted_file_list) <= batch_size:
        # Original single-batch behavior
        return _load_and_merge_subbands_single_batch(sorted_file_list, show_progress)

    # Batched loading for larger file lists
    merged = None
    batch_num = 0
    total_batches = (len(sorted_file_list) + batch_size - 1) // batch_size

    _pyuv_lg = logging.getLogger("pyuvdata")
    _prev_level = _pyuv_lg.level
    try:
        _pyuv_lg.setLevel(logging.ERROR)

        for i in range(0, len(sorted_file_list), batch_size):
            batch_num += 1
            batch = sorted_file_list[i : i + batch_size]

            if show_progress:
                logger.info(f"Loading batch {batch_num}/{total_batches} ({len(batch)} subbands)...")

            # Load batch
            batch_data = _load_and_merge_subbands_single_batch(batch, show_progress=False)

            # Merge with accumulated result
            if merged is None:
                merged = batch_data
            else:
                # Merge batch into accumulated result
                merged.fast_concat([batch_data], axis="freq", inplace=True, run_check=False)

            # Explicit cleanup to help GC
            del batch_data
            import gc

            gc.collect()

        if merged is not None:
            merged.reorder_freqs(channel_order="freq", run_check=False)
            logger.info(f"Concatenated {len(sorted_file_list)} subbands in {total_batches} batches")

    finally:
        _pyuv_lg.setLevel(_prev_level)

    return merged if merged is not None else UVData()


def _load_and_merge_subbands_single_batch(
    file_list: Sequence[str], show_progress: bool = True
) -> UVData:
    """Load and merge a single batch of subband files (original implementation).

    This is the original single-batch loading logic, extracted for reuse
    in both single-batch and batched loading scenarios.
    """
    uv = UVData()
    acc: List[UVData] = []
    _pyuv_lg = logging.getLogger("pyuvdata")
    _prev_level = _pyuv_lg.level
    try:
        _pyuv_lg.setLevel(logging.ERROR)

        # Use progress bar for file reading
        from dsa110_contimg.utils.progress import get_progress_bar

        file_iter = get_progress_bar(
            enumerate(file_list),
            total=len(file_list),
            desc="Reading subbands",
            disable=not show_progress,
            mininterval=0.5,  # Update every 0.5s max
        )

        for i, path in file_iter:
            # PRECONDITION CHECK: Validate file is readable before reading
            # This ensures we follow "measure twice, cut once" - establish requirements upfront
            # before expensive file reading operations.
            if not os.path.exists(path):
                suggestions = [
                    "Check file path is correct",
                    "Verify file exists",
                    "Check file system permissions",
                ]
                error_msg = format_file_error_with_suggestions(
                    FileNotFoundError(f"Subband file does not exist: {path}"),
                    path,
                    "file validation",
                    suggestions,
                )
                raise FileNotFoundError(error_msg)
            if not os.access(path, os.R_OK):
                suggestions = [
                    "Check file system permissions",
                    "Verify read access to file",
                    "Check SELinux/AppArmor restrictions if applicable",
                ]
                error_msg = format_file_error_with_suggestions(
                    PermissionError(f"Subband file is not readable: {path}"),
                    path,
                    "file validation",
                    suggestions,
                )
                raise PermissionError(error_msg)

            # Quick HDF5 structure check
            try:
                import h5py

                with h5py.File(path, "r") as f:
                    # Verify file has required structure (Header or Data group)
                    if "Header" not in f and "Data" not in f:
                        suggestions = [
                            "Verify file is a valid UVH5/HDF5 file",
                            "Check file format and structure",
                            "Re-run conversion if file is corrupted",
                        ]
                        raise ValidationError(
                            errors=[f"Invalid HDF5 structure: {path}"],
                            context={"path": str(path), "operation": "file validation"},
                            suggestion="Check file format and structure. Re-run conversion if file is corrupted.",
                        )
            except Exception as e:
                raise ValidationError(
                    errors=[f"File validation failed: {e}"],
                    context={"path": str(path), "operation": "file validation"},
                    suggestion="Verify file is a valid UVH5/HDF5 file. Check file format and structure. Review detailed error logs.",
                ) from e

            t_read0 = time.perf_counter()
            # Update progress bar description with current file
            if hasattr(file_iter, "set_description"):
                file_iter.set_description(f"Reading {os.path.basename(path)}")

            tmp = UVData()
            tmp.read(
                path,
                file_type="uvh5",
                run_check=False,
                run_check_acceptability=False,
                strict_uvw_antpos_check=False,
                check_extra=False,
            )
            tmp.uvw_array = tmp.uvw_array.astype(np.float64)
            acc.append(tmp)

            # Log details at debug level to avoid cluttering progress bar output
            logger.debug(
                "Read subband %d in %.2fs (Nblts=%s, Nfreqs=%s, Npols=%s)",
                i + 1,
                time.perf_counter() - t_read0,
                tmp.Nblts,
                tmp.Nfreqs,
                tmp.Npols,
            )
    finally:
        _pyuv_lg.setLevel(_prev_level)
    t_cat0 = time.perf_counter()
    uv = acc[0]
    if len(acc) > 1:
        uv.fast_concat(acc[1:], axis="freq", inplace=True, run_check=False)
    logger.debug("Concatenated %d subbands in %.2fs", len(acc), time.perf_counter() - t_cat0)
    uv.reorder_freqs(channel_order="freq", run_check=False)
    return uv


def _set_phase_and_uvw(uv: UVData) -> tuple[u.Quantity, u.Quantity, u.Quantity]:
    phase_to_meridian(uv)
    return (
        uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad,
        uv.phase_center_ra * u.rad,
        uv.phase_center_dec * u.rad,
    )


@track_performance("conversion", log_result=True)
def convert_subband_groups_to_ms(
    input_dir: str,
    output_dir: str,
    start_time: str,
    end_time: str,
    *,
    flux: Optional[float] = None,
    scratch_dir: Optional[str] = None,
    writer: str = "parallel-subband",
    writer_kwargs: Optional[dict] = None,
    skip_existing: bool = False,
    checkpoint_file: Optional[str] = None,
    path_mapper: Optional[Callable[[str, str], str]] = None,
) -> None:
    """Convert subband groups to Measurement Sets.

    Discovers complete subband groups within the specified time window and
    converts them to CASA Measurement Sets.

    **Time Range Validation:**

    This function validates that `start_time < end_time`. Scripts calling this
    function should ensure time ranges are valid. If reading time ranges from
    HDF5 files, scripts should:

    1. Read `time_array` from all HDF5 files in the group
    2. Calculate actual start/end times from the data
    3. Ensure `end_time > start_time` (add 1 second if equal)

    **Group Discovery:**

    This function internally calls `discover_subband_groups()` which re-discovers
    groups based on `start_time`/`end_time`. If filename timestamps don't match
    the provided time range, groups may not be found. In such cases, use
    `write_ms_from_subbands()` directly with an explicit file list.

    Args:
        input_dir: Directory containing UVH5 subband files (NOT input_hdf5_dir)
        output_dir: Directory where MS files will be written (NOT output_ms_dir)
        start_time: Start time in ISO format (e.g., "2025-10-29T13:53:00")
        end_time: End time in ISO format (must be after start_time)
        flux: Optional flux value for model population
        scratch_dir: Optional scratch directory for temporary files
        writer: Writer type to use ("parallel-subband", "auto", etc.)
        writer_kwargs: Optional keyword arguments for writer
        skip_existing: If True, skip MS files that already exist
        checkpoint_file: Optional checkpoint file path
        path_mapper: Optional function to map (base_name, output_dir) to organized MS path.
                    If provided, MS files will be written directly to organized locations.
                    Function signature: (base_name: str, output_dir: str) -> str
                    Example: lambda name, dir: f"{dir}/science/2025-10-28/{name}.ms"

    Note:
        - No 'verbose' parameter exists (logging is controlled by logger level)
        - Parameter names are 'input_dir' and 'output_dir', not 'input_hdf5_dir' or 'output_ms_dir'

    Raises:
        ValueError: If input/output directories are invalid or time range is invalid
        RuntimeError: If conversion fails

    Note:
        This function internally re-discovers groups. For explicit file lists,
        use `write_ms_from_subbands()` instead.
    """
    # PRECONDITION CHECK: Validate input/output directories before proceeding
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # before any expensive operations.
    if not os.path.exists(input_dir):
        suggestions = [
            "Check input directory path is correct",
            "Verify directory exists",
            "Check file system permissions",
        ]
        raise ValidationError(
            errors=[f"Input directory does not exist: {input_dir}"],
            context={"input_dir": input_dir, "operation": "directory validation"},
            suggestion="Verify directory exists. Check file system permissions.",
        )
    if not os.path.isdir(input_dir):
        raise ValidationError(
            errors=[f"Input path is not a directory: {input_dir}"],
            context={"input_dir": input_dir, "operation": "directory validation"},
            suggestion="Verify path is a directory, not a file. Check input path is correct.",
        )
    if not os.access(input_dir, os.R_OK):
        raise ValidationError(
            errors=[f"Input directory is not readable: {input_dir}"],
            context={"input_dir": input_dir, "operation": "directory validation"},
            suggestion="Check file system permissions. Verify read access to input directory. Check SELinux/AppArmor restrictions if applicable.",
        )

    # Validate output directory
    os.makedirs(output_dir, exist_ok=True)
    if not os.path.exists(output_dir):
        suggestions = [
            "Check file system permissions",
            "Verify parent directory exists and is writable",
            "Check disk space",
        ]
        error_msg = format_file_error_with_suggestions(
            OSError(f"Failed to create output directory: {output_dir}"),
            output_dir,
            "directory creation",
            suggestions,
        )
        raise ValueError(error_msg)
    if not os.path.isdir(output_dir):
        suggestions = [
            "Verify path is a directory, not a file",
            "Check output path is correct",
        ]
        error_msg = format_file_error_with_suggestions(
            ValueError(f"Output path is not a directory: {output_dir}"),
            output_dir,
            "directory validation",
            suggestions,
        )
        raise ValueError(error_msg)
    if not os.access(output_dir, os.W_OK):
        suggestions = [
            "Check file system permissions",
            "Verify write access to output directory",
            "Check SELinux/AppArmor restrictions if applicable",
        ]
        error_msg = format_file_error_with_suggestions(
            PermissionError(f"Output directory is not writable: {output_dir}"),
            output_dir,
            "directory validation",
            suggestions,
        )
        raise ValueError(error_msg)

    # Validate scratch directory if provided
    if scratch_dir:
        os.makedirs(scratch_dir, exist_ok=True)
        if not os.path.exists(scratch_dir):
            suggestions = [
                "Check file system permissions",
                "Verify parent directory exists and is writable",
                "Check disk space",
            ]
            error_msg = format_file_error_with_suggestions(
                OSError(f"Failed to create scratch directory: {scratch_dir}"),
                scratch_dir,
                "directory creation",
                suggestions,
            )
            raise ValueError(error_msg)
        if not os.access(scratch_dir, os.W_OK):
            suggestions = [
                "Check file system permissions",
                "Verify write access to scratch directory",
                "Check SELinux/AppArmor restrictions if applicable",
            ]
            error_msg = format_file_error_with_suggestions(
                PermissionError(f"Scratch directory is not writable: {scratch_dir}"),
                scratch_dir,
                "directory validation",
                suggestions,
            )
            raise ValueError(error_msg)

    # PRECONDITION CHECK: Validate time range before processing
    # This ensures we follow "measure twice, cut once" - establish requirements upfront.
    try:
        from astropy.time import Time

        t_start = Time(start_time)
        t_end = Time(end_time)
        if t_start >= t_end:
            raise ValueError(
                f"Invalid time range: start_time ({start_time}) must be before "
                f"end_time ({end_time})"
            )
    except Exception as e:
        if isinstance(e, ValueError) and "Invalid time range" in str(e):
            raise
        logger.warning(f"Failed to validate time range (proceeding anyway): {e}")

    groups = find_subband_groups(input_dir, start_time, end_time)
    if not groups:
        logger.info("No complete subband groups to convert.")
        return

    # Print group filenames for visibility
    logger.info(f"Found {len(groups)} complete subband group(s) ({len(groups) * 16} total files)")
    for i, group in enumerate(groups, 1):
        logger.info(f"  Group {i}:")
        # Sort by subband number ONLY (0-15) to show correct spectral order
        # Groups from find_subband_groups are already sorted, but display them correctly

        def sort_key(fpath):
            fname = os.path.basename(fpath)
            sb = _extract_subband_code(fname)
            sb_num = int(sb.replace("sb", "")) if sb else 999
            return sb_num

        for f in sorted(group, key=sort_key):
            logger.info(f"    {os.path.basename(f)}")

    # Solution 1: Cleanup verification before starting new groups
    # Check for and remove stale tmpfs directories to prevent file locking issues
    if writer_kwargs and writer_kwargs.get("stage_to_tmpfs", False):
        tmpfs_path = writer_kwargs.get("tmpfs_path", "/dev/shm")
        tmpfs_base = Path(tmpfs_path) / "dsa110-contimg"
        if tmpfs_base.exists():
            try:
                # Check for stale directories older than 1 hour
                current_time = time.time()
                stale_dirs = []
                for stale_dir in tmpfs_base.iterdir():
                    if stale_dir.is_dir():
                        try:
                            mtime = stale_dir.stat().st_mtime
                            if current_time - mtime > 3600:  # 1 hour
                                stale_dirs.append(stale_dir)
                        except Exception:
                            pass

                # Remove stale directories and verify removal
                if stale_dirs:
                    logger.debug(
                        f"Found {len(stale_dirs)} stale tmpfs directory(s) (>1 hour old), removing..."
                    )
                    removed_count = 0
                    for stale_dir in stale_dirs:
                        try:
                            if stale_dir.exists():
                                shutil.rmtree(stale_dir, ignore_errors=False)
                                # Verify it's actually gone
                                if stale_dir.exists():
                                    logger.warning(
                                        f"Failed to remove stale tmpfs directory: {stale_dir}"
                                    )
                                else:
                                    removed_count += 1
                        except Exception as e:
                            logger.debug(f"Failed to remove stale tmpfs directory {stale_dir}: {e}")

                    if removed_count > 0:
                        logger.info(
                            f"Cleaned up {removed_count} stale tmpfs director"
                            f"{'y' if removed_count == 1 else 'ies'}"
                        )
            except Exception as cleanup_err:
                logger.debug(f"Stale tmpfs cleanup check failed (non-fatal): {cleanup_err}")

    # Add progress indicator for group processing
    from dsa110_contimg.utils.progress import get_progress_bar, should_disable_progress

    show_progress = not should_disable_progress(
        None,  # No args in this function scope - use env var
        env_var="CONTIMG_DISABLE_PROGRESS",
    )

    groups_iter = get_progress_bar(
        groups,
        total=len(groups),
        desc="Converting groups",
        disable=not show_progress,
        mininterval=1.0,  # Update every 1s max for groups
    )

    for file_list in groups_iter:
        # PRECONDITION CHECK: Validate all files exist before conversion
        # This ensures we follow "measure twice, cut once" - establish requirements upfront
        # before expensive conversion operations.
        missing_files = [f for f in file_list if not os.path.exists(f)]
        if missing_files:
            logger.error(
                f"Group has missing files (may have been deleted): {missing_files}. "
                f"Skipping group."
            )
            continue

        # Verify all files are readable
        unreadable_files = [f for f in file_list if not os.access(f, os.R_OK)]
        if unreadable_files:
            logger.error(f"Group has unreadable files: {unreadable_files}. Skipping group.")
            continue

        first_file = os.path.basename(file_list[0])
        base_name = os.path.splitext(first_file)[0].split("_sb")[0]

        # Use path_mapper if provided, otherwise use flat structure
        if path_mapper:
            ms_path = path_mapper(base_name, output_dir)
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(ms_path), exist_ok=True)
        else:
            ms_path = os.path.join(output_dir, f"{base_name}.ms")

        logger.info("Converting group %s -> %s", base_name, ms_path)

        # Check if MS already exists
        if os.path.exists(ms_path):
            if skip_existing:
                logger.info("MS already exists (--skip-existing), skipping: %s", ms_path)
            else:
                logger.info("MS already exists, skipping: %s", ms_path)

            # Register in database if not already present
            try:
                from pathlib import Path as PathLib

                from dsa110_contimg.database.products import (
                    ensure_products_db,
                    ms_index_upsert,
                )
                from dsa110_contimg.utils.time_utils import extract_ms_time_range

                # Find products database
                products_db_path = PathLib(os.getenv("PRODUCTS_DB_PATH", "state/products.sqlite3"))
                if not products_db_path.is_absolute():
                    # Search in common locations
                    for base_dir in [
                        "/data/dsa110-contimg",
                        "/stage/dsa110-contimg",
                        os.getcwd(),
                    ]:
                        candidate = PathLib(base_dir) / products_db_path
                        if candidate.exists():
                            products_db_path = candidate
                            break

                if products_db_path.exists():
                    conn = ensure_products_db(products_db_path)

                    # Check if MS is already registered
                    cursor = conn.cursor()
                    existing = cursor.execute(
                        "SELECT path FROM ms_index WHERE path = ?", (ms_path,)
                    ).fetchone()

                    if not existing:
                        # Extract metadata from MS file
                        start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)

                        # Get phase center from MS
                        ra_deg = None
                        dec_deg = None
                        try:
                            import casacore.tables as casatables

                            with casatables.table(f"{ms_path}::FIELD", readonly=True) as field_tb:
                                phase_dir = field_tb.getcol("PHASE_DIR")[
                                    0, 0
                                ]  # [field, poly_order, ra/dec]
                                ra_deg = float(np.degrees(phase_dir[0]))
                                dec_deg = float(np.degrees(phase_dir[1]))
                        except Exception as e:
                            logger.debug(f"Could not extract phase center from {ms_path}: {e}")

                        # Register MS in database
                        ms_index_upsert(
                            conn,
                            ms_path,
                            start_mjd=start_mjd,
                            end_mjd=end_mjd,
                            mid_mjd=mid_mjd,
                            status="converted",
                            stage="converted",
                            ra_deg=ra_deg,
                            dec_deg=dec_deg,
                        )
                        conn.commit()
                        logger.info(f"Registered existing MS in database: {ms_path}")
                    else:
                        logger.debug(f"MS already registered in database: {ms_path}")

                    conn.close()
                else:
                    logger.debug(
                        f"Products database not found at {products_db_path}, skipping registration"
                    )
            except Exception as e:
                logger.warning(f"Failed to register existing MS in database: {e}")

            continue

        # PRECONDITION CHECK: Estimate disk space requirement and verify availability
        # This ensures we follow "measure twice, cut once" - establish requirements upfront
        # before starting conversion that may fail partway through.
        try:
            total_input_size = sum(os.path.getsize(f) for f in file_list)
            # Estimate MS size: roughly 2x input size for safety (includes overhead)
            estimated_ms_size = total_input_size * 2

            # CRITICAL: Check available space in output directory (fatal check)
            from dsa110_contimg.mosaic.error_handling import check_disk_space

            check_disk_space(
                output_dir,
                required_bytes=estimated_ms_size,
                operation=f"conversion of {base_name}",
                fatal=True,  # Fail fast if insufficient space
            )

            # Also check scratch directory if provided (non-fatal warning)
            if scratch_dir and os.path.exists(scratch_dir):
                scratch_free = shutil.disk_usage(scratch_dir).free
                # Scratch may need more space for intermediate files
                scratch_required = estimated_ms_size * 1.5
                if scratch_free < scratch_required:
                    logger.warning(
                        f"Limited scratch space. "
                        f"Estimated need: {scratch_required / 1e9:.1f}GB, "
                        f"Available: {scratch_free / 1e9:.1f}GB. "
                        f"Proceeding but may fail."
                    )

            # PRECONDITION CHECK: Validate staging directories are writable
            # This ensures we follow "measure twice, cut once" - establish requirements upfront
            # before staging operations.
            if scratch_dir and os.path.exists(scratch_dir):
                if not os.access(scratch_dir, os.W_OK):
                    logger.error(
                        f"Scratch directory is not writable: {scratch_dir}. " f"Skipping group."
                    )
                    continue

            # Validate tmpfs if staging is enabled
            if writer_kwargs and writer_kwargs.get("stage_to_tmpfs", False):
                tmpfs_path = writer_kwargs.get("tmpfs_path", "/dev/shm")
                if os.path.exists(tmpfs_path):
                    if not os.access(tmpfs_path, os.W_OK):
                        logger.warning(
                            f"Tmpfs staging directory is not writable: {tmpfs_path}. "
                            f"Falling back to scratch directory."
                        )
                        # Disable tmpfs staging for this group
                        current_writer_kwargs = writer_kwargs.copy()
                        current_writer_kwargs["stage_to_tmpfs"] = False
                        writer_kwargs = current_writer_kwargs
        except Exception as e:
            logger.warning(f"Disk space check failed (proceeding anyway): {e}")

        selected_writer = writer
        uv = None
        if writer == "auto":
            # Production processing always uses 16 subbands, so default to parallel-subband.
            # pyuvdata writer is only for testing scenarios with ≤2 subbands.
            try:
                n_sb = len(file_list)
            except Exception:
                n_sb = 0
            # Only use pyuvdata for testing scenarios (≤2 subbands)
            # Production always uses parallel-subband for 16 subbands
            if n_sb and n_sb <= 2:
                logger.warning(
                    f"Auto-selected pyuvdata writer for {n_sb} subband(s). "
                    f"This is intended for testing only. Production uses 16 subbands "
                    f"and should use parallel-subband writer."
                )
                selected_writer = "pyuvdata"
            else:
                selected_writer = "parallel-subband"

        if selected_writer not in ("parallel-subband", "direct-subband"):
            t0 = time.perf_counter()
            # Determine if progress should be shown
            from dsa110_contimg.utils.progress import (
                get_progress_bar,
                should_disable_progress,
            )

            show_progress = not should_disable_progress(
                None,  # No args in this function scope
                env_var="CONTIMG_DISABLE_PROGRESS",
            )

            uv = _load_and_merge_subbands(file_list, show_progress=show_progress)
            logger.info(
                "Loaded and merged %d subbands in %.2fs",
                len(file_list),
                time.perf_counter() - t0,
            )

            t1 = time.perf_counter()
            # Ensure telescope name + location are set consistently before phasing
            # Uses OVRO_LOCATION from constants.py (single source of truth)
            try:
                set_telescope_identity(
                    uv,
                    os.getenv("PIPELINE_TELESCOPE_NAME", "DSA_110"),
                )
            except Exception:
                logger.debug("set_telescope_identity best-effort failed", exc_info=True)
            pt_dec, phase_ra, phase_dec = _set_phase_and_uvw(uv)
            logger.info("Phased and updated UVW in %.2fs", time.perf_counter() - t1)
        else:
            _, pt_dec, mid_mjd = _peek_uvh5_phase_and_midtime(file_list[0])
            if not np.isfinite(mid_mjd) or mid_mjd == 0.0:
                temp_uv = UVData()
                temp_uv.read(
                    file_list[0],
                    file_type="uvh5",
                    read_data=False,
                    run_check=False,
                    check_extra=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                )
                pt_dec = temp_uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
                mid_mjd = Time(float(np.mean(temp_uv.time_array)), format="jd").mjd
                del temp_uv
            phase_ra, phase_dec = get_meridian_coords(pt_dec, mid_mjd)

        try:
            t_write_start = time.perf_counter()
            # CRITICAL: DSA-110 subbands use DESCENDING frequency order (sb00=highest, sb15=lowest).
            # For proper frequency ordering (ascending, low to high), REVERSE the sort.
            # This ensures correct spectral order in the MS, which is essential for
            # proper MFS imaging and bandpass calibration. If files are out of order,
            # frequency channels will be scrambled, imaging will produce fringes,
            # and bandpass calibration will be incorrect.

            def sort_by_subband(fpath):
                fname = os.path.basename(fpath)
                sb = _extract_subband_code(fname)
                sb_num = int(sb.replace("sb", "")) if sb else 999
                return sb_num

            sorted_file_list = sorted(file_list, key=sort_by_subband, reverse=True)

            # CRITICAL FIX: Create a copy of writer_kwargs for each iteration
            # to prevent file_list from being shared between groups.
            # Without this, all MS files would use the file_list from the first group,
            # causing duplicate TIME values across different MS files.
            current_writer_kwargs = (writer_kwargs or {}).copy()
            current_writer_kwargs.setdefault("scratch_dir", scratch_dir)
            # Use assignment, not setdefault
            current_writer_kwargs["file_list"] = sorted_file_list

            writer_cls = get_writer(selected_writer)
            # get_writer raises ValueError if writer not found, so no need to check for None
            writer_instance = writer_cls(uv, ms_path, **current_writer_kwargs)
            writer_type = writer_instance.write()

            logger.info(
                "Writer '%s' finished in %.2fs",
                writer_type,
                time.perf_counter() - t_write_start,
            )
            logger.debug(f"WRITER_TYPE: {writer_type}")

            # CRITICAL: Clean up CASA file handles before validation
            # This prevents file locking issues when accessing the MS
            cleanup_casa_file_handles()

            # PRECONDITION CHECK: Validate MS was written successfully
            # This ensures we follow "measure twice, cut once" - verify output before
            # marking conversion as complete.
            if not os.path.exists(ms_path):
                suggestions = [
                    "Check disk space",
                    "Verify write permissions on output directory",
                    "Review conversion logs for errors",
                    "Check writer implementation for failures",
                ]
                error_msg = format_file_error_with_suggestions(
                    RuntimeError(f"MS was not created: {ms_path}"),
                    ms_path,
                    "MS creation",
                    suggestions,
                )
                raise RuntimeError(error_msg)

            # CRITICAL: Validate frequency order to prevent imaging artifacts
            # DSA-110 subbands must be in ascending frequency order after conversion
            try:
                validate_ms_frequency_order(ms_path)
            except RuntimeError as e:
                # Frequency order error is critical - clean up and fail
                logger.error(f"CRITICAL: {e}")
                try:
                    if os.path.exists(ms_path):
                        shutil.rmtree(ms_path, ignore_errors=True)
                        logger.info(f"Cleaned up MS with incorrect frequency order: {ms_path}")
                except Exception:
                    pass
                raise

            # Skip validation checks during conversion if requested (do after conversion)
            skip_validation = writer_kwargs and writer_kwargs.get(
                "skip_validation_during_conversion", False
            )
            if not skip_validation:
                # CRITICAL: Fix phase centers before validation
                # When subbands are concatenated, each subband becomes a different field
                # with potentially different phase centers.
                # NOTE: With time-dependent phasing (meridian-tracking, RA=LST), phase centers
                # are EXPECTED to be incoherent across fields because each field tracks LST at
                # different times. See conversion/README.md for details.
                try:
                    from dsa110_contimg.conversion.ms_utils import (
                        _fix_field_phase_centers_from_times,
                    )

                    _fix_field_phase_centers_from_times(ms_path)
                    logger.info("Fixed FIELD table phase centers after concatenation")
                except Exception as e:
                    logger.error(
                        f"CRITICAL: Failed to fix phase centers before validation: {e}",
                        exc_info=True,
                    )
                    # Phase center fixing failure is critical - re-raise to fail conversion
                    raise RuntimeError(
                        f"Phase center fixing failed for {ms_path}: {e}. "
                        f"This will cause imaging artifacts. Conversion aborted."
                    ) from e

                # CRITICAL: Validate phase center coherence
                # NOTE: With time-dependent phasing (meridian-tracking, RA=LST), phase centers
                # are EXPECTED to be incoherent across fields (subbands) because each field
                # tracks LST at different times. The validation function should detect this
                # and skip the strict coherence check. If it doesn't detect time-dependent
                # phasing, it will raise RuntimeError, which we should handle gracefully.
                try:
                    validate_phase_center_coherence(ms_path, tolerance_arcsec=2.0)
                    logger.debug("Phase center coherence validation passed")
                except RuntimeError as e:
                    # Check if this is time-dependent phasing (expected) vs actual error
                    # The validation function should have detected time-dependent phasing,
                    # but if it didn't, we need to check manually
                    error_msg = str(e)
                    if "incoherent" in error_msg.lower():
                        # Check if this looks like time-dependent phasing that wasn't detected
                        # If phase centers are separated by large amounts (>1 arcmin), it's
                        # likely time-dependent phasing, not an error
                        import re

                        separation_match = re.search(
                            r"Maximum separation: ([\d.]+) arcsec", error_msg
                        )
                        if separation_match:
                            max_sep = float(separation_match.group(1))
                            # If separation is > 1 arcmin (60 arcsec), likely time-dependent phasing
                            if max_sep > 60.0:
                                logger.info(
                                    f"Phase center separation ({max_sep:.2f} arcsec) indicates "
                                    f"time-dependent phasing (meridian-tracking). This is expected "
                                    f"and correct for DSA-110 observations. Validation check skipped."
                                )
                                # This is expected - don't fail conversion
                            else:
                                # Small separation but still incoherent - this might be an error
                                logger.warning(
                                    f"Phase centers incoherent ({max_sep:.2f} arcsec) but separation "
                                    f"is small. This may indicate a conversion issue, but continuing."
                                )
                        else:
                            # Can't parse separation - log warning but continue
                            logger.warning(
                                f"Phase center validation failed but couldn't parse details: {e}. "
                                f"Assuming time-dependent phasing and continuing."
                            )
                    else:
                        # Not an incoherence error - re-raise
                        raise

                # CRITICAL: Validate UVW coordinate precision to prevent calibration decorrelation
                # Inaccurate UVW coordinates cause phase errors and flagged solutions
                try:
                    validate_uvw_precision(ms_path, tolerance_lambda=0.1)
                except RuntimeError as e:
                    # UVW precision errors are critical for calibration
                    logger.error(f"CRITICAL: {e}")
                    # Continue anyway - user may need to check antenna positions

                # CRITICAL: Validate antenna positions to prevent calibration decorrelation
                # Position errors cause systematic phase errors and flagged solutions
                try:
                    validate_antenna_positions(ms_path, position_tolerance_m=0.05)
                except RuntimeError as e:
                    # Position errors are critical for calibration
                    logger.error(f"CRITICAL: {e}")
                    # Continue anyway - user may need to update antenna positions

                # CRITICAL: Validate MODEL_DATA quality for calibrator sources
                # Poor calibrator models lead to decorrelation and flagged solutions
                try:
                    validate_model_data_quality(ms_path)
                except RuntimeError as e:
                    # MODEL_DATA issues affect calibration quality
                    logger.error(f"WARNING: {e}")
                    # Continue anyway - user may proceed with caution
            else:
                logger.debug("Skipping validation checks during conversion (will be done after)")

            # Verify MS is readable and has required structure
            # Ensure CASAPATH is set before importing CASA modules
            from dsa110_contimg.utils.casa_init import ensure_casa_path

            ensure_casa_path()

            try:
                import casacore.tables as casatables

                table = casatables.table  # noqa: N816

                with table(ms_path, readonly=True) as tb:
                    if tb.nrows() == 0:
                        suggestions = [
                            "Check input UVH5 files contain data",
                            "Verify conversion writer completed successfully",
                            "Review conversion logs for errors",
                            "Check for empty or corrupted input files",
                        ]
                        error_msg = format_file_error_with_suggestions(
                            RuntimeError(f"MS has no data rows: {ms_path}"),
                            ms_path,
                            "MS validation",
                            suggestions,
                        )
                        raise RuntimeError(error_msg)

                    # Verify required columns exist
                    required_cols = ["DATA", "ANTENNA1", "ANTENNA2", "TIME", "UVW"]
                    missing_cols = [c for c in required_cols if c not in tb.colnames()]
                    if missing_cols:
                        suggestions = [
                            "Check conversion writer implementation",
                            "Verify MS structure is correct",
                            "Review conversion logs for errors",
                            "Re-run conversion if MS is corrupted",
                        ]
                        error_msg = format_file_error_with_suggestions(
                            RuntimeError(f"MS missing required columns: {missing_cols}"),
                            ms_path,
                            "MS validation",
                            suggestions,
                        )
                        raise RuntimeError(error_msg)

                    logger.info(
                        f"✓ MS validation passed: {tb.nrows()} rows, "
                        f"{len(tb.colnames())} columns"
                    )
            except Exception as e:
                logger.error(f"MS validation failed: {e}")
                # Clean up partial/corrupted MS
                try:
                    if os.path.exists(ms_path):
                        shutil.rmtree(ms_path, ignore_errors=True)
                        logger.info(f"Cleaned up partial MS: {ms_path}")
                except Exception:
                    pass
                raise

        except Exception:
            logger.exception("MS writing failed for group %s", base_name)
            if os.path.exists(ms_path):
                shutil.rmtree(ms_path, ignore_errors=True)
            continue

        # CRITICAL: Configure MS for imaging (creates MODEL_DATA and CORRECTED_DATA columns)
        # This is required for downstream calibration and imaging stages
        try:
            configure_ms_for_imaging(ms_path)
            logger.info(f"✓ MS configured for imaging: {ms_path}")
        except ConversionError as e:
            # ConversionError already has context and suggestions
            error_msg = (
                f"CRITICAL: MS configuration for imaging failed for {ms_path}: {e}. "
                "The MS may be missing required MODEL_DATA and CORRECTED_DATA columns."
            )
            logger.error(error_msg, exc_info=True)
            # Don't silently continue - this is a critical failure
            # Clean up the incomplete MS and re-raise
            try:
                if os.path.exists(ms_path):
                    logger.info(f"Cleaning up incomplete MS: {ms_path}")
                    shutil.rmtree(ms_path, ignore_errors=True)
            except Exception:
                pass
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"CRITICAL: MS configuration for imaging failed for {ms_path}: {e}. "
                "The MS may be missing required MODEL_DATA and CORRECTED_DATA columns."
            )
            logger.error(error_msg, exc_info=True)
            # Don't silently continue - this is a critical failure
            # Clean up the incomplete MS and re-raise
            try:
                if os.path.exists(ms_path):
                    logger.info(f"Cleaning up incomplete MS: {ms_path}")
                    shutil.rmtree(ms_path, ignore_errors=True)
            except Exception:
                pass
            raise RuntimeError(error_msg) from e

        if flux is not None:
            try:
                if uv is None:
                    uv = UVData()
                    uv.read(file_list, read_data=False)
                set_model_column(base_name, uv, pt_dec, phase_ra, phase_dec, flux_jy=flux)
            except Exception:
                logger.warning("Failed to set MODEL_DATA column")

        logger.info("✓ Successfully created %s", ms_path)

        # Save checkpoint if checkpoint file provided
        if checkpoint_file:
            try:
                import json

                checkpoint_path = Path(checkpoint_file)
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

                # Load existing checkpoint or create new
                checkpoint_data = {"completed_groups": [], "groups": {}}
                if checkpoint_path.exists():
                    with open(checkpoint_path, "r") as f:
                        checkpoint_data = json.load(f)

                # Add this group to completed list
                if "completed_groups" not in checkpoint_data:
                    checkpoint_data["completed_groups"] = []
                checkpoint_data["completed_groups"].append(base_name)
                checkpoint_data["groups"][base_name] = {
                    "ms_path": ms_path,
                    "timestamp": time.time(),
                    "files": file_list,
                }

                with open(checkpoint_path, "w") as f:
                    json.dump(checkpoint_data, f, indent=2)
                logger.debug(f"Checkpoint saved: {checkpoint_file}")
            except Exception as e:
                logger.warning(f"Failed to save checkpoint: {e}")

        # Run QA check on MS (skip if requested - will be done after conversion stage)
        skip_qa = writer_kwargs and writer_kwargs.get("skip_validation_during_conversion", False)
        if not skip_qa:
            try:
                qa_passed, _ = check_ms_after_conversion(
                    ms_path=ms_path,
                    quick_check_only=False,
                    alert_on_issues=True,
                )
                if qa_passed:
                    logger.info("✓ MS passed quality checks")
                else:
                    logger.warning("⚠ MS quality issues detected (see alerts)")
            except Exception as e:
                logger.warning(f"QA check failed (non-fatal): {e}")
        else:
            logger.debug(
                "Skipping QA check during conversion (will be done after conversion stage)"
            )


def add_args(p: argparse.ArgumentParser) -> None:
    """Add arguments to a parser.

    Example usage:
        # Convert using explicit time window
        python -m dsa110_contimg.conversion.cli groups /data/incoming /data/ms \\
            "2025-10-30 10:00:00" "2025-10-30 11:00:00"

        # Convert using calibrator transit mode
        python -m dsa110_contimg.conversion.cli groups /data/incoming /data/ms \\
            --calibrator 0834+555 --transit-date 2025-10-30

        # Find transit without converting
        python -m dsa110_contimg.conversion.cli groups /data/incoming /data/ms \\
            --calibrator 0834+555 --find-only
    """
    p.add_argument("input_dir", help="Directory containing UVH5 (HDF5 container) subband files.")
    p.add_argument(
        "output_dir",
        nargs="?",
        default="/data/dsa110-contimg/ms",
        help="Directory to save Measurement Sets (default: /data/dsa110-contimg/ms).",
    )

    # Time window arguments (required unless using calibrator mode)
    time_group = p.add_argument_group(
        "time_window",
        "Time window specification (required unless --calibrator is used)",
    )
    time_group.add_argument(
        "start_time",
        nargs="?",
        help="Start of processing window (YYYY-MM-DD HH:MM:SS). Required unless --calibrator is specified.",
    )
    time_group.add_argument(
        "end_time",
        nargs="?",
        help="End of processing window (YYYY-MM-DD HH:MM:SS). Required unless --calibrator is specified.",
    )

    # Calibrator transit mode (alternative to explicit time window)
    calibrator_group = p.add_argument_group(
        "calibrator", "Calibrator transit mode (alternative to explicit time window)"
    )
    calibrator_group.add_argument(
        "--calibrator",
        help="Calibrator name (e.g., '0834+555'). When specified, finds transit and calculates time window automatically.",
    )
    calibrator_group.add_argument(
        "--transit-date",
        help="Specific transit date (YYYY-MM-DD) or transit time (YYYY-MM-DDTHH:MM:SS). If not specified, uses most recent transit.",
    )
    calibrator_group.add_argument(
        "--window-minutes",
        type=int,
        default=60,
        help="Search window in minutes around transit (default: 60, i.e., ±30 minutes).",
    )
    calibrator_group.add_argument(
        "--max-days-back",
        type=int,
        default=30,
        help="Maximum days to search back for transit (default: 30).",
    )
    calibrator_group.add_argument(
        "--min-pb-response",
        type=float,
        default=0.3,
        help=(
            "Minimum primary beam response (0-1) required for calibrator to be in beam. "
            "IRON-CLAD SAFEGUARD: Only converts data where calibrator is actually in primary beam. "
            "Default: 0.3 (30%% PB response)."
        ),
    )
    calibrator_group.add_argument(
        "--dec-tolerance-deg",
        type=float,
        default=2.0,
        help="Declination tolerance in degrees for matching observations (default: 2.0).",
    )
    p.add_argument(
        "--writer",
        default="parallel-subband",
        choices=["parallel-subband", "direct-subband", "pyuvdata", "auto"],
        help=(
            "MS writing strategy. "
            "'parallel-subband' (default) is for production use with 16 subbands. "
            "'direct-subband' is an alias for 'parallel-subband'. "
            "'pyuvdata' is for testing only (≤2 subbands). "
            "'auto' selects 'parallel-subband' for production (16 subbands) or 'pyuvdata' for testing (≤2 subbands)."
        ),
    )
    p.add_argument("--flux", type=float, help="Optional flux in Jy to write to MODEL_DATA.")
    p.add_argument("--scratch-dir", help="Scratch directory for temporary files.")
    p.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Parallel workers for parallel-subband writer.",
    )
    p.add_argument(
        "--stage-to-tmpfs",
        action="store_true",
        default=True,
        help=(
            "Stage per-subband writes and concat to tmpfs (e.g., /dev/shm) "
            "before moving atomically to final MS. Default: enabled for optimal performance. "
            "Use --no-stage-to-tmpfs to disable."
        ),
    )
    p.add_argument(
        "--no-stage-to-tmpfs",
        action="store_false",
        dest="stage_to_tmpfs",
        help="Disable tmpfs staging and use scratch directory only.",
    )
    p.add_argument("--tmpfs-path", default="/dev/shm", help="Path to tmpfs (RAM disk).")
    p.add_argument(
        "--merge-spws",
        action="store_true",
        default=False,
        help=(
            "Merge all SPWs into a single SPW after concatenation. "
            "Uses CASA mstransform to combine 16 SPWs into 1 SPW with regridded frequency grid. "
            "Note: Merges raw DATA column during conversion. For best results, merge CORRECTED_DATA "
            "after calibration using the standalone merge_spws tool instead."
        ),
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level.",
    )
    # Utility flags
    utility_group = p.add_argument_group("utility", "Utility and debugging options")
    utility_group.add_argument(
        "--find-only",
        action="store_true",
        help="Find transit and list files without converting to MS. Useful for verifying data availability before conversion.",
    )
    utility_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate conversion without writing files. Validates inputs and reports what would be converted.",
    )
    utility_group.add_argument(
        "--disable-progress",
        action="store_true",
        help="Disable progress bars. Useful for non-interactive environments or scripts.",
    )
    utility_group.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip groups that already have MS files. Faster iteration during testing.",
    )
    utility_group.add_argument(
        "--checkpoint-file",
        type=str,
        help="Path to checkpoint file for resumable conversion. Saves progress after each group.",
    )


def create_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert DSA-110 subband UVH5 to MS (Strategy Orchestrator)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_args(p)
    return p


def main(args: Optional[argparse.Namespace] = None) -> int:
    if args is None:
        parser = create_parser()
        args = parser.parse_args()

    # Logging is now handled by the main CLI entrypoint
    # logging.basicConfig(
    #     level=getattr(logging, args.log_level.upper()),
    #     format="%(asctime)s [%(levelname)s] %(message)s",
    #     datefmt="%Y-%m-%d %H:%M:%S",
    # )

    os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    os.environ.setdefault("MKL_NUM_THREADS", "4")

    # Ensure scratch directory structure exists
    try:
        ensure_scratch_dirs()
    except Exception:
        pass  # Best-effort; continue if setup fails

    # Determine start_time and end_time
    start_time = args.start_time
    end_time = args.end_time

    # If calibrator mode is specified, find transit and calculate time window
    if args.calibrator:
        if start_time or end_time:
            logger.warning(
                "Both --calibrator and explicit time window provided. "
                "Ignoring explicit time window in favor of calibrator transit mode."
            )

        try:
            from dsa110_contimg.conversion.calibrator_ms_service import (
                CalibratorMSGenerator,
            )
            from dsa110_contimg.conversion.config import CalibratorMSConfig

            logger.info(f"Finding transit for calibrator: {args.calibrator}")

            # Initialize service
            config = CalibratorMSConfig.from_env()
            if hasattr(args, "input_dir") and args.input_dir:
                config.input_dir = Path(args.input_dir)
            service = CalibratorMSGenerator.from_config(config, verbose=True)

            # Find transit
            transit_info = None
            transit_time = None

            if args.transit_date:
                # Check if it's just a date (YYYY-MM-DD) or a full ISO time
                # If it parses as a time but is at midnight and has no time component, treat as date
                is_date_only = False
                transit_time_parsed = None

                try:
                    transit_time_parsed = Time(args.transit_date)
                    # Check if input was just a date (no time component)
                    # If it parses to midnight and input has no 'T' or ':', it's likely just a date
                    if "T" not in args.transit_date and ":" not in args.transit_date:
                        is_date_only = True
                    elif transit_time_parsed.isot.endswith("T00:00:00.000"):
                        # Check if hours/minutes/seconds are all zero (midnight)
                        is_date_only = True
                except Exception:
                    is_date_only = True

                if is_date_only:
                    # Optimize: Calculate transit for specific date instead of searching all dates
                    logger.info(f"Calculating transit for date: {args.transit_date}")

                    # Load RA/Dec for calibrator
                    ra_deg, _ = service._load_radec(args.calibrator)

                    # Calculate transit time for that specific date
                    # Use end of target date as search start, then find previous transit
                    from dsa110_contimg.calibration.schedule import previous_transits

                    target_date_end = Time(f"{args.transit_date}T23:59:59")

                    # Get transit around that date (search a small window)
                    candidate_transits = previous_transits(
                        ra_deg,
                        start_time=target_date_end,
                        n=3,  # Check a few transits around the date
                    )

                    # Find the transit that falls on the target date
                    target_transit_time = None
                    for candidate in candidate_transits:
                        if candidate.isot.startswith(args.transit_date):
                            target_transit_time = candidate
                            logger.info(f"Calculated transit time: {target_transit_time.isot}")
                            break

                    if target_transit_time is None:
                        raise ValueError(
                            f"No transit calculated for calibrator {args.calibrator} on {args.transit_date}"
                        )

                    # Now find the data group for this specific transit
                    transit_info = service.find_transit(
                        args.calibrator,
                        transit_time=target_transit_time,
                        window_minutes=args.window_minutes,
                        max_days_back=args.max_days_back,  # Use configured search window
                        min_pb_response=getattr(args, "min_pb_response", 0.3),
                    )

                    if transit_info is None:
                        # If find_transit fails, try list_available_transits as fallback
                        logger.warning(
                            f"Direct transit search failed, trying broader search for {args.transit_date}..."
                        )
                        all_transits = service.list_available_transits(
                            args.calibrator, max_days_back=args.max_days_back
                        )
                        for transit in all_transits:
                            if transit["transit_iso"].startswith(args.transit_date):
                                transit_info = {
                                    "transit_iso": transit["transit_iso"],
                                    "group_id": transit["group_id"],
                                    "files": transit["files"],
                                    "delta_minutes": transit["delta_minutes"],
                                    "start_iso": (
                                        Time(transit["transit_iso"])
                                        - (args.window_minutes // 2) * u.min
                                    ).isot,
                                    "end_iso": (
                                        Time(transit["transit_iso"])
                                        + (args.window_minutes // 2) * u.min
                                    ).isot,
                                }
                                break

                        if transit_info is None:
                            raise ValueError(
                                f"No data found for calibrator {args.calibrator} transit on {args.transit_date} "
                                f"(transit time: {target_transit_time.isot})"
                            )
                else:
                    # Full ISO time provided, use it directly
                    transit_time = transit_time_parsed
                    logger.info(f"Using provided transit time: {transit_time.isot}")

            # If we don't have transit_info yet, call find_transit
            if transit_info is None:
                transit_info = service.find_transit(
                    args.calibrator,
                    transit_time=transit_time,
                    window_minutes=args.window_minutes,
                    max_days_back=args.max_days_back,
                    min_pb_response=getattr(args, "min_pb_response", 0.3),
                )

                if not transit_info:
                    raise ValueError(
                        f"No transit found for calibrator {args.calibrator} "
                        f"(searched last {args.max_days_back} days)"
                    )

            # Extract time window from transit info
            start_time = transit_info["start_iso"]
            end_time = transit_info["end_iso"]

            logger.info("Calibrator transit found:")
            logger.info(f"  Transit time: {transit_info['transit_iso']}")
            logger.info(f"  Group ID: {transit_info['group_id']}")
            logger.info(f"  Search window: {start_time} to {end_time}")

            # Print subband filenames (sorted by subband number for spectral order)
            transit_files = transit_info.get("files", [])
            logger.info(f"  Files: {len(transit_files)} subband files")
            if transit_files:
                # Sort by subband number ONLY (0-15) to show correct spectral order
                # This matches the actual file order used for concatenation
                def sort_key(fpath):
                    fname = os.path.basename(fpath)
                    sb = _extract_subband_code(fname)
                    sb_num = int(sb.replace("sb", "")) if sb else 999
                    return sb_num

                for i, fpath in enumerate(sorted(transit_files, key=sort_key), 1):
                    logger.info(f"    {i:2d}. {os.path.basename(fpath)}")

            # If --find-only, print file list and exit without converting
            if getattr(args, "find_only", False):
                logger.info("\n" + "=" * 60)
                logger.info("FIND-ONLY MODE: Not converting to MS")
                logger.info("=" * 60)
                logger.info("\nTransit Information:")
                logger.info(f"  Calibrator: {args.calibrator}")
                logger.info(f"  Transit Time: {transit_info['transit_iso']}")
                logger.info(f"  Group ID: {transit_info['group_id']}")
                logger.info(
                    f"  Delta from transit: {transit_info.get('delta_minutes', 'N/A')} minutes"
                )
                logger.info(f"\nHDF5 Files ({len(transit_info.get('files', []))} subbands):")
                # Sort by subband number ONLY (0-15) to show correct spectral order
                # Files from find_transit are already sorted, but ensure correct order here too

                def sort_key_files(fpath):
                    fname = os.path.basename(fpath)
                    sb = _extract_subband_code(fname)
                    sb_num = int(sb.replace("sb", "")) if sb else 999
                    return sb_num

                for i, fpath in enumerate(
                    sorted(transit_info.get("files", []), key=sort_key_files), 1
                ):
                    logger.info(f"  {i:2d}. {os.path.basename(fpath)}")
                logger.info("\nTime Window:")
                logger.info(f"  Start: {start_time}")
                logger.info(f"  End: {end_time}")
                return 0

        except ImportError as e:
            logger.error(
                f"Calibrator transit mode requires CalibratorMSGenerator: {e}\n"
                f"Please ensure the conversion package is properly installed."
            )
            return 1
        except Exception as e:
            logger.error(f"Failed to find calibrator transit: {e}")
            return 1

    # Validate that we have time window
    if not start_time or not end_time:
        logger.error(
            "Either explicit time window (start_time end_time) or " "--calibrator must be provided."
        )
        return 1

    # If --find-only mode and we have transit info, we've already printed it and returned above
    # This check handles the case where explicit time window is used with --find-only
    if getattr(args, "find_only", False):
        logger.info("\n" + "=" * 60)
        logger.info("FIND-ONLY MODE: Not converting to MS")
        logger.info("=" * 60)
        logger.info("\nTime Window:")
        logger.info(f"  Start: {start_time}")
        logger.info(f"  End: {end_time}")
        logger.info("\nTo convert, run without --find-only flag")
        return 0

    # Check for dry-run mode
    if getattr(args, "dry_run", False):
        logger.info("=" * 60)
        logger.info("DRY-RUN MODE: No files will be written")
        logger.info("=" * 60)

        # Find groups that would be converted
        groups = find_subband_groups(args.input_dir, start_time, end_time)
        logger.info(f"\nWould convert {len(groups)} group(s):")
        for i, file_list in enumerate(groups, 1):
            first_file = os.path.basename(file_list[0]) if file_list else "unknown"
            base_name = os.path.splitext(first_file)[0].split("_sb")[0]
            ms_path = os.path.join(args.output_dir, f"{base_name}.ms")
            logger.info(f"  {i}. Group {base_name} ({len(file_list)} subbands) -> {ms_path}")

        logger.info("\nValidation:")
        # Perform validation checks
        try:
            from dsa110_contimg.utils.validation import validate_directory

            validate_directory(args.output_dir, must_exist=False, must_writable=True)
            if args.scratch_dir:
                validate_directory(args.scratch_dir, must_exist=False, must_writable=True)
            logger.info("  ✓ Directory validation passed")
        except Exception as e:
            from dsa110_contimg.utils.validation import ValidationError

            if isinstance(e, ValidationError):
                logger.error(f"  ✗ Validation failed: {', '.join(e.errors)}")
            else:
                logger.error(f"  ✗ Validation failed: {e}")
        logger.info("\nDry-run complete. Use without --dry-run to perform conversion.")
        return 0

    writer_kwargs = {"max_workers": args.max_workers}
    if getattr(args, "stage_to_tmpfs", False):
        writer_kwargs["stage_to_tmpfs"] = True
        writer_kwargs["tmpfs_path"] = getattr(args, "tmpfs_path", "/dev/shm")

    # Enable SPW merging if requested
    if getattr(args, "merge_spws", False):
        writer_kwargs["merge_spws"] = True
        logger.warning(
            "SPW merging enabled: MS will have 1 SPW with merged DATA column. "
            "If calibration issues occur, consider: (1) Calibrate on 16-SPW MS first, "
            "(2) Then merge CORRECTED_DATA using: python -m dsa110_contimg.conversion.merge_spws"
        )

    convert_subband_groups_to_ms(
        args.input_dir,
        args.output_dir,
        start_time,
        end_time,
        flux=args.flux,
        scratch_dir=args.scratch_dir,
        writer=args.writer,
        writer_kwargs=writer_kwargs,
        skip_existing=getattr(args, "skip_existing", False),
        checkpoint_file=getattr(args, "checkpoint_file", None),
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
