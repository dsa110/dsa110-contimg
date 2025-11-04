#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSA-110 UVH5 (in HDF5) → CASA MS orchestrator.

This module discovers complete subband groups in a time window, delegates
MS creation to a selected writer, and uses shared helpers to finalize the
Measurement Set for imaging. It serves as the primary entry point for converting
subband groups.
"""

from .writers import get_writer
from dsa110_contimg.conversion.helpers import (
    _ensure_antenna_diameters,
    get_meridian_coords,
    set_antenna_positions,
    compute_and_set_uvw,
    set_model_column,
    phase_to_meridian,
    set_telescope_identity,
)
from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion
import argparse
import glob
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, List, Optional, Sequence, cast

import astropy.units as u  # type: ignore[import]
import numpy as np
from astropy.time import Time  # type: ignore[import]
from pyuvdata import UVData  # type: ignore[import]


logger = logging.getLogger("hdf5_orchestrator")


def _peek_uvh5_phase_and_midtime(uvh5_path: str) -> tuple[u.Quantity, u.Quantity, float]:
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
                if (
                    "extra_keywords" in f
                    and name in f["extra_keywords"]
                ):
                    return float(np.asarray(f["extra_keywords"][name]))
            except Exception:
                pass
            try:
                if (
                    "Header" in f
                    and "extra_keywords" in f["Header"]
                    and name in f["Header"]["extra_keywords"]
                ):
                    return float(
                        np.asarray(f["Header"]["extra_keywords"][name])
                    )
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
                    from astropy.coordinates import EarthLocation
                    from astropy.time import Time
                    # Get longitude from Header (default to DSA-110 location)
                    lon_deg = -118.2817  # DSA-110 default
                    if "Header" in f and "longitude" in f["Header"]:
                        lon_val = np.asarray(f["Header"]["longitude"])
                        if lon_val.size == 1:
                            lon_deg = float(lon_val)
                    
                    # Calculate LST at mid_time
                    location = EarthLocation(lat=37.2314 * u.deg, lon=lon_deg * u.deg, height=1222.0 * u.m)
                    tref = Time(mid_jd, format='jd')
                    lst = tref.sidereal_time('apparent', longitude=location.lon)
                    
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
    tolerance_s: float = 30.0,
) -> List[List[str]]:
    """Identify complete subband groups within a time window."""
    if spw is None:
        spw = [f"sb{idx:02d}" for idx in range(16)]

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
        close_indices = np.where(
            np.abs(
                times_sec -
                times_sec[i]) <= tolerance_s)[0]
        group_indices = [idx for idx in close_indices if not used[idx]]

        selected_files = [files[j] for j in group_indices]
        subband_map = {
            _extract_subband_code(
                os.path.basename(p)): p for p in selected_files}

        if set(subband_map.keys()) == set(spw):
            sorted_group = [subband_map[s] for s in sorted(spw)]
            groups.append(sorted_group)
            for idx in group_indices:
                used[idx] = True

    return groups


def _load_and_merge_subbands(file_list: Sequence[str], 
                             show_progress: bool = True) -> UVData:
    uv = UVData()
    acc: List[UVData] = []
    _pyuv_lg = logging.getLogger('pyuvdata')
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
            mininterval=0.5  # Update every 0.5s max
        )
        
        for i, path in file_iter:
            # PRECONDITION CHECK: Validate file is readable before reading
            # This ensures we follow "measure twice, cut once" - establish requirements upfront
            # before expensive file reading operations.
            if not os.path.exists(path):
                raise FileNotFoundError(f"Subband file does not exist: {path}")
            if not os.access(path, os.R_OK):
                raise PermissionError(f"Subband file is not readable: {path}")
            
            # Quick HDF5 structure check
            try:
                import h5py
                with h5py.File(path, 'r') as f:
                    # Verify file has required structure (Header or Data group)
                    if 'Header' not in f and 'Data' not in f:
                        raise ValueError(f"Invalid HDF5 structure: {path}")
            except Exception as e:
                raise ValueError(f"File {path} is not a valid HDF5 file: {e}") from e
            
            t_read0 = time.perf_counter()
            # Update progress bar description with current file
            if hasattr(file_iter, 'set_description'):
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
    logger.info("Concatenated %d subbands in %.2fs",
                len(acc), time.perf_counter() - t_cat0)
    uv.reorder_freqs(channel_order="freq", run_check=False)
    return uv


def _set_phase_and_uvw(
        uv: UVData) -> tuple[u.Quantity, u.Quantity, u.Quantity]:
    phase_to_meridian(uv)
    return (
        uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad,
        uv.phase_center_ra * u.rad,
        uv.phase_center_dec * u.rad,
    )


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
) -> None:
    # PRECONDITION CHECK: Validate input/output directories before proceeding
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # before any expensive operations.
    if not os.path.exists(input_dir):
        raise ValueError(f"Input directory does not exist: {input_dir}")
    if not os.path.isdir(input_dir):
        raise ValueError(f"Input path is not a directory: {input_dir}")
    if not os.access(input_dir, os.R_OK):
        raise ValueError(f"Input directory is not readable: {input_dir}")
    
    # Validate output directory
    os.makedirs(output_dir, exist_ok=True)
    if not os.path.exists(output_dir):
        raise ValueError(f"Failed to create output directory: {output_dir}")
    if not os.path.isdir(output_dir):
        raise ValueError(f"Output path is not a directory: {output_dir}")
    if not os.access(output_dir, os.W_OK):
        raise ValueError(f"Output directory is not writable: {output_dir}")
    
    # Validate scratch directory if provided
    if scratch_dir:
        os.makedirs(scratch_dir, exist_ok=True)
        if not os.path.exists(scratch_dir):
            raise ValueError(f"Failed to create scratch directory: {scratch_dir}")
        if not os.access(scratch_dir, os.W_OK):
            raise ValueError(f"Scratch directory is not writable: {scratch_dir}")
    
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
                            logger.debug(
                                f"Failed to remove stale tmpfs directory {stale_dir}: {e}"
                            )
                    
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
        env_var="CONTIMG_DISABLE_PROGRESS"
    )
    
    groups_iter = get_progress_bar(
        groups,
        total=len(groups),
        desc="Converting groups",
        disable=not show_progress,
        mininterval=1.0  # Update every 1s max for groups
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
            logger.error(
                f"Group has unreadable files: {unreadable_files}. Skipping group."
            )
            continue
        
        first_file = os.path.basename(file_list[0])
        base_name = os.path.splitext(first_file)[0].split("_sb")[0]
        ms_path = os.path.join(output_dir, f"{base_name}.ms")
        logger.info("Converting group %s -> %s", base_name, ms_path)

        # Check if MS already exists
        if os.path.exists(ms_path):
            if skip_existing:
                logger.info("MS already exists (--skip-existing), skipping: %s", ms_path)
                continue
            else:
                logger.info("MS already exists, skipping: %s", ms_path)
                continue
        
        # PRECONDITION CHECK: Estimate disk space requirement and verify availability
        # This ensures we follow "measure twice, cut once" - establish requirements upfront
        # before starting conversion that may fail partway through.
        try:
            import shutil
            total_input_size = sum(os.path.getsize(f) for f in file_list)
            # Estimate MS size: roughly 2x input size for safety (includes overhead)
            estimated_ms_size = total_input_size * 2
            
            # Check available space in output directory
            free_space = shutil.disk_usage(output_dir).free
            if free_space < estimated_ms_size:
                logger.error(
                    f"Insufficient disk space for conversion. "
                    f"Estimated need: {estimated_ms_size / 1e9:.1f}GB, "
                    f"Available: {free_space / 1e9:.1f}GB. "
                    f"Skipping group."
                )
                continue
            
            # Also check scratch directory if provided
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
                        f"Scratch directory is not writable: {scratch_dir}. "
                        f"Skipping group."
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
            from dsa110_contimg.utils.progress import should_disable_progress
            show_progress = not should_disable_progress(
                None,  # No args in this function scope
                env_var="CONTIMG_DISABLE_PROGRESS"
            )
            
            uv = _load_and_merge_subbands(file_list, show_progress=show_progress)
            logger.info("Loaded and merged %d subbands in %.2fs",
                        len(file_list), time.perf_counter() - t0)

            t1 = time.perf_counter()
            # Ensure telescope name + location are set consistently before phasing
            try:
                set_telescope_identity(
                    uv,
                    os.getenv("PIPELINE_TELESCOPE_NAME", "DSA_110"),
                    -118.2817,
                    37.2314,
                    1222.0,
                )
            except Exception:
                logger.debug("set_telescope_identity best-effort failed", exc_info=True)
            pt_dec, phase_ra, phase_dec = _set_phase_and_uvw(uv)
            logger.info(
                "Phased and updated UVW in %.2fs",
                time.perf_counter() - t1)
        else:
            _, pt_dec, mid_mjd = _peek_uvh5_phase_and_midtime(file_list[0])
            if not np.isfinite(mid_mjd) or mid_mjd == 0.0:
                temp_uv = UVData()
                temp_uv.read(
                    file_list[0],
                    file_type='uvh5',
                    read_data=False,
                    run_check=False,
                    check_extra=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                )
                pt_dec = temp_uv.extra_keywords.get(
                    "phase_center_dec", 0.0) * u.rad
                mid_mjd = Time(
                    float(
                        np.mean(
                            temp_uv.time_array)),
                    format="jd").mjd
                del temp_uv
            phase_ra, phase_dec = get_meridian_coords(pt_dec, mid_mjd)

        try:
            t_write_start = time.perf_counter()
            current_writer_kwargs = writer_kwargs or {}
            current_writer_kwargs.setdefault("scratch_dir", scratch_dir)
            current_writer_kwargs.setdefault("file_list", file_list)

            writer_cls = get_writer(selected_writer)
            # get_writer raises ValueError if writer not found, so no need to check for None
            writer_instance = writer_cls(uv, ms_path, **current_writer_kwargs)
            writer_type = writer_instance.write()

            logger.info(
                "Writer '%s' finished in %.2fs",
                writer_type,
                time.perf_counter() -
                t_write_start)
            print(f"WRITER_TYPE: {writer_type}")
            
            # PRECONDITION CHECK: Validate MS was written successfully
            # This ensures we follow "measure twice, cut once" - verify output before
            # marking conversion as complete.
            if not os.path.exists(ms_path):
                raise RuntimeError(f"MS was not created: {ms_path}")
            
            # Verify MS is readable and has required structure
            try:
                from casacore.tables import table
                with table(ms_path, readonly=True) as tb:
                    if tb.nrows() == 0:
                        raise RuntimeError(f"MS has no data rows: {ms_path}")
                    
                    # Verify required columns exist
                    required_cols = ['DATA', 'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW']
                    missing_cols = [c for c in required_cols if c not in tb.colnames()]
                    if missing_cols:
                        raise RuntimeError(
                            f"MS missing required columns: {missing_cols}. "
                            f"Path: {ms_path}"
                        )
                    
                    logger.info(
                        f"✓ MS validation passed: {tb.nrows()} rows, "
                        f"{len(tb.colnames())} columns"
                    )
            except Exception as e:
                logger.error(f"MS validation failed: {e}")
                # Clean up partial/corrupted MS
                try:
                    import shutil
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

        try:
            configure_ms_for_imaging(ms_path)
        except Exception:
            logger.warning(
                "MS configuration for imaging failed for %s",
                ms_path)

        if flux is not None:
            try:
                if uv is None:
                    uv = UVData()
                    uv.read(file_list, read_data=False)
                set_model_column(
                    base_name,
                    uv,
                    pt_dec,
                    phase_ra,
                    phase_dec,
                    flux_jy=flux)
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
                checkpoint_data = {'completed_groups': [], 'groups': {}}
                if checkpoint_path.exists():
                    with open(checkpoint_path, 'r') as f:
                        checkpoint_data = json.load(f)
                
                # Add this group to completed list
                if 'completed_groups' not in checkpoint_data:
                    checkpoint_data['completed_groups'] = []
                checkpoint_data['completed_groups'].append(base_name)
                checkpoint_data['groups'][base_name] = {
                    'ms_path': ms_path,
                    'timestamp': time.time(),
                    'files': file_list,
                }
                
                with open(checkpoint_path, 'w') as f:
                    json.dump(checkpoint_data, f, indent=2)
                logger.debug(f"Checkpoint saved: {checkpoint_file}")
            except Exception as e:
                logger.warning(f"Failed to save checkpoint: {e}")
        
        # Run QA check on MS
        try:
            qa_passed, qa_metrics = check_ms_after_conversion(
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
    p.add_argument(
        "input_dir",
        help="Directory containing UVH5 (HDF5 container) subband files.")
    p.add_argument(
        "output_dir",
        nargs="?",
        default="/data/dsa110-contimg/ms",
        help="Directory to save Measurement Sets (default: /data/dsa110-contimg/ms)."
    )
    
    # Time window arguments (required unless using calibrator mode)
    time_group = p.add_argument_group(
        "time_window",
        "Time window specification (required unless --calibrator is used)"
    )
    time_group.add_argument(
        "start_time",
        nargs="?",
        help="Start of processing window (YYYY-MM-DD HH:MM:SS). Required unless --calibrator is specified.")
    time_group.add_argument(
        "end_time",
        nargs="?",
        help="End of processing window (YYYY-MM-DD HH:MM:SS). Required unless --calibrator is specified.")
    
    # Calibrator transit mode (alternative to explicit time window)
    calibrator_group = p.add_argument_group(
        "calibrator",
        "Calibrator transit mode (alternative to explicit time window)"
    )
    calibrator_group.add_argument(
        "--calibrator",
        help="Calibrator name (e.g., '0834+555'). When specified, finds transit and calculates time window automatically."
    )
    calibrator_group.add_argument(
        "--transit-date",
        help="Specific transit date (YYYY-MM-DD) or transit time (YYYY-MM-DDTHH:MM:SS). If not specified, uses most recent transit."
    )
    calibrator_group.add_argument(
        "--window-minutes",
        type=int,
        default=60,
        help="Search window in minutes around transit (default: 60, i.e., ±30 minutes)."
    )
    calibrator_group.add_argument(
        "--max-days-back",
        type=int,
        default=30,
        help="Maximum days to search back for transit (default: 30)."
    )
    calibrator_group.add_argument(
        "--min-pb-response",
        type=float,
        default=0.3,
        help=(
            "Minimum primary beam response (0-1) required for calibrator to be in beam. "
            "IRON-CLAD SAFEGUARD: Only converts data where calibrator is actually in primary beam. "
            "Default: 0.3 (30%% PB response)."
        )
    )
    calibrator_group.add_argument(
        "--dec-tolerance-deg",
        type=float,
        default=2.0,
        help="Declination tolerance in degrees for matching observations (default: 2.0)."
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
    p.add_argument(
        "--flux",
        type=float,
        help="Optional flux in Jy to write to MODEL_DATA.")
    p.add_argument(
        "--scratch-dir",
        help="Scratch directory for temporary files.")
    p.add_argument("--max-workers", type=int, default=4,
                   help="Parallel workers for parallel-subband writer.")
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
    p.add_argument(
        "--tmpfs-path",
        default="/dev/shm",
        help="Path to tmpfs (RAM disk).")
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
    utility_group = p.add_argument_group(
        "utility",
        "Utility and debugging options"
    )
    utility_group.add_argument(
        "--find-only",
        action="store_true",
        help="Find transit and list files without converting to MS. Useful for verifying data availability before conversion."
    )
    utility_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate conversion without writing files. Validates inputs and reports what would be converted."
    )
    utility_group.add_argument(
        "--disable-progress",
        action="store_true",
        help="Disable progress bars. Useful for non-interactive environments or scripts."
    )
    utility_group.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip groups that already have MS files. Faster iteration during testing."
    )
    utility_group.add_argument(
        "--checkpoint-file",
        type=str,
        help="Path to checkpoint file for resumable conversion. Saves progress after each group."
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
            from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
            from dsa110_contimg.conversion.config import CalibratorMSConfig
            
            logger.info(f"Finding transit for calibrator: {args.calibrator}")
            
            # Initialize service
            config = CalibratorMSConfig.from_env()
            if hasattr(args, 'input_dir') and args.input_dir:
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
                    if 'T' not in args.transit_date and ':' not in args.transit_date:
                        is_date_only = True
                    elif transit_time_parsed.isot.endswith('T00:00:00.000'):
                        # Check if hours/minutes/seconds are all zero (midnight)
                        is_date_only = True
                except Exception:
                    is_date_only = True
                
                if is_date_only:
                    # Optimize: Calculate transit for specific date instead of searching all dates
                    logger.info(f"Calculating transit for date: {args.transit_date}")
                    
                    # Load RA/Dec for calibrator
                    ra_deg, dec_deg = service._load_radec(args.calibrator)
                    
                    # Calculate transit time for that specific date
                    # Use end of target date as search start, then find previous transit
                    from dsa110_contimg.calibration.schedule import previous_transits
                    target_date_end = Time(f"{args.transit_date}T23:59:59")
                    
                    # Get transit around that date (search a small window)
                    candidate_transits = previous_transits(
                        ra_deg,
                        start_time=target_date_end,
                        n=3  # Check a few transits around the date
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
                        min_pb_response=getattr(args, 'min_pb_response', 0.3)
                    )
                    
                    if transit_info is None:
                        # If find_transit fails, try list_available_transits as fallback
                        logger.warning(
                            f"Direct transit search failed, trying broader search for {args.transit_date}..."
                        )
                        all_transits = service.list_available_transits(
                            args.calibrator,
                            max_days_back=args.max_days_back
                        )
                        for transit in all_transits:
                            if transit['transit_iso'].startswith(args.transit_date):
                                transit_info = {
                                    'transit_iso': transit['transit_iso'],
                                    'group_id': transit['group_id'],
                                    'files': transit['files'],
                                    'delta_minutes': transit['delta_minutes'],
                                    'start_iso': (Time(transit['transit_iso']) - (args.window_minutes // 2) * u.min).isot,
                                    'end_iso': (Time(transit['transit_iso']) + (args.window_minutes // 2) * u.min).isot,
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
                    min_pb_response=getattr(args, 'min_pb_response', 0.3)
                )
                
                if not transit_info:
                    raise ValueError(
                        f"No transit found for calibrator {args.calibrator} "
                        f"(searched last {args.max_days_back} days)"
                    )
            
            # Extract time window from transit info
            start_time = transit_info['start_iso']
            end_time = transit_info['end_iso']
            
            logger.info("Calibrator transit found:")
            logger.info(f"  Transit time: {transit_info['transit_iso']}")
            logger.info(f"  Group ID: {transit_info['group_id']}")
            logger.info(f"  Search window: {start_time} to {end_time}")
            logger.info(f"  Files: {len(transit_info.get('files', []))} subband files")
            
            # If --find-only, print file list and exit without converting
            if getattr(args, 'find_only', False):
                logger.info("\n" + "="*60)
                logger.info("FIND-ONLY MODE: Not converting to MS")
                logger.info("="*60)
                logger.info(f"\nTransit Information:")
                logger.info(f"  Calibrator: {args.calibrator}")
                logger.info(f"  Transit Time: {transit_info['transit_iso']}")
                logger.info(f"  Group ID: {transit_info['group_id']}")
                logger.info(f"  Delta from transit: {transit_info.get('delta_minutes', 'N/A')} minutes")
                logger.info(f"\nHDF5 Files ({len(transit_info.get('files', []))} subbands):")
                for i, fpath in enumerate(sorted(transit_info.get('files', [])), 1):
                    logger.info(f"  {i:2d}. {os.path.basename(fpath)}")
                logger.info(f"\nTime Window:")
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
            "Either explicit time window (start_time end_time) or "
            "--calibrator must be provided."
        )
        return 1
    
    # If --find-only mode and we have transit info, we've already printed it and returned above
    # This check handles the case where explicit time window is used with --find-only
    if getattr(args, 'find_only', False):
        logger.info("\n" + "="*60)
        logger.info("FIND-ONLY MODE: Not converting to MS")
        logger.info("="*60)
        logger.info(f"\nTime Window:")
        logger.info(f"  Start: {start_time}")
        logger.info(f"  End: {end_time}")
        logger.info(f"\nTo convert, run without --find-only flag")
        return 0
    
    # Check for dry-run mode
    if getattr(args, 'dry_run', False):
        logger.info("="*60)
        logger.info("DRY-RUN MODE: No files will be written")
        logger.info("="*60)
        
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
        skip_existing=getattr(args, 'skip_existing', False),
        checkpoint_file=getattr(args, 'checkpoint_file', None),
    )
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
