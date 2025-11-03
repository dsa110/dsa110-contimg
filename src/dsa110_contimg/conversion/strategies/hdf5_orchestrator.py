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
from typing import Any, List, Optional, Sequence, cast

import astropy.units as u  # type: ignore[import]
import numpy as np
from astropy.time import Time  # type: ignore[import]
from pyuvdata import UVData  # type: ignore[import]


logger = logging.getLogger("hdf5_orchestrator")


def _peek_uvh5_phase_and_midtime(uvh5_path: str) -> tuple[u.Quantity, float]:
    """Lightweight HDF5 peek: return (pt_dec [rad], mid_time [MJD])."""
    import h5py  # type: ignore[import]
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

        val = _read_extra("phase_center_dec")
        if val is not None and np.isfinite(val):
            pt_dec_val = float(val)
    return (
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


def _load_and_merge_subbands(file_list: Sequence[str]) -> UVData:
    uv = UVData()
    acc: List[UVData] = []
    _pyuv_lg = logging.getLogger('pyuvdata')
    _prev_level = _pyuv_lg.level
    try:
        _pyuv_lg.setLevel(logging.ERROR)
        for i, path in enumerate(file_list):
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
            logger.info(
                "Reading subband %d/%d: %s",
                i + 1,
                len(file_list),
                os.path.basename(path))
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
            logger.info(
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

    for file_list in groups:
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

        if os.path.exists(ms_path):
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
            uv = _load_and_merge_subbands(file_list)
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
            pt_dec, mid_mjd = _peek_uvh5_phase_and_midtime(file_list[0])
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
    """Add arguments to a parser."""
    p.add_argument(
        "input_dir",
        help="Directory containing UVH5 (HDF5 container) subband files.")
    p.add_argument("output_dir", help="Directory to save Measurement Sets.")
    p.add_argument(
        "start_time",
        help="Start of processing window (YYYY-MM-DD HH:MM:SS).")
    p.add_argument(
        "end_time",
        help="End of processing window (YYYY-MM-DD HH:MM:SS).")
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
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level.",
    )


def create_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert DSA-110 subband UVH5 to MS (Strategy Orchestrator)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_args(p)
    return p


def main(args: argparse.Namespace = None) -> int:
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

    writer_kwargs = {"max_workers": args.max_workers}
    if getattr(args, "stage_to_tmpfs", False):
        writer_kwargs["stage_to_tmpfs"] = True
        writer_kwargs["tmpfs_path"] = getattr(args, "tmpfs_path", "/dev/shm")

    convert_subband_groups_to_ms(
        args.input_dir,
        args.output_dir,
        args.start_time,
        args.end_time,
        flux=args.flux,
        scratch_dir=args.scratch_dir,
        writer=args.writer,
        writer_kwargs=writer_kwargs,
    )
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
