#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSA-110 UVH5 → CASA MS converter (v2 - Strategy Pattern).

This version of the converter acts as an orchestrator. It finds and prepares
the visibility data, then delegates the final MS creation to a selected
"writer" strategy. This design is extensible and separates concerns.

Available writer strategies:
- 'pyuvdata': Writes the merged UVData object in a single step.
- 'direct-subband': Writes per-subband MS files in parallel and concatenates.
"""

from dsa110_contimg.utils.fringestopping import calc_uvw_blt
from .writers import get_writer
from dsa110_contimg.conversion.helpers import (
    _ensure_antenna_diameters,
    get_meridian_coords,
    set_antenna_positions,
    set_model_column,
)
import argparse
import glob
import logging
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional, Sequence

import astropy.units as u
import numpy as np
from astropy.time import Time
from casacore.tables import addImagingColumns
from pyuvdata import UVData


logger = logging.getLogger("uvh5_to_ms_converter_v2_strat")


def _parse_timestamp_from_filename(filename: str) -> Optional[Time]:
    """Extracts timestamp from a filename like '2022-01-01T12:34:56_sb00.hdf5'."""
    base = os.path.splitext(filename)[0]
    if "_sb" not in base:
        return None
    ts_part = base.split("_sb", 1)[0]
    try:
        return Time(ts_part)
    except ValueError:
        return None


def _extract_subband_code(filename: str) -> Optional[str]:
    """Extracts subband code 'sbXX' from a filename."""
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
    """
    Identify complete subband groups within a time window.

    A group is considered complete if all expected subbands (e.g., sb00-sb15)
    are found with timestamps within `tolerance_s` of each other.

    Args:
        input_dir: Directory to search for UVH5 files.
        start_time: The start of the time window (ISO format).
        end_time: The end of the time window (ISO format).
        spw: A list of expected subband codes (e.g., ['sb00', 'sb01']).
             If None, defaults to sb00-sb15.
        tolerance_s: Time tolerance in seconds for grouping files.

    Returns:
        A list of groups, where each group is a list of file paths sorted by subband index.
    """
    if spw is None:
        spw = [f"sb{idx:02d}" for idx in range(16)]

    tmin = Time(start_time)
    tmax = Time(end_time)

    # Gather candidate files within the time window
    candidates = []
    for path in glob.glob(os.path.join(input_dir, "*_sb??.hdf5")):
        fname = os.path.basename(path)
        ts = _parse_timestamp_from_filename(fname)
        if ts and tmin <= ts <= tmax:
            candidates.append((path, ts))

    if not candidates:
        logger.info(
            "No subband files found in %s between %s and %s",
            input_dir,
            start_time,
            end_time)
        return []

    # Group files by timestamp closeness
    candidates.sort(key=lambda item: item[1].unix)
    times_sec = np.array([ts.unix for _, ts in candidates])
    files = np.array([p for p, _ in candidates])

    groups: List[List[str]] = []
    used = np.zeros(len(times_sec), dtype=bool)

    for i in range(len(times_sec)):
        if used[i]:
            continue
        # Find all files close in time to the current one
        close_indices = np.where(
            np.abs(
                times_sec -
                times_sec[i]) <= tolerance_s)[0]
        group_indices = [idx for idx in close_indices if not used[idx]]

        # Check if this forms a complete group
        selected_files = [files[j] for j in group_indices]
        subband_map = {
            _extract_subband_code(
                os.path.basename(p)): p for p in selected_files}

        if set(subband_map.keys()) == set(spw):
            # Found a complete group, add it, sorted by subband index
            sorted_group = [subband_map[s] for s in sorted(spw)]
            groups.append(sorted_group)
            # Mark these files as used
            for idx in group_indices:
                used[idx] = True

    return groups


def _load_and_merge_subbands(file_list: Sequence[str]) -> UVData:
    """Read a list of UVH5 subband files and merge along the frequency axis."""
    uv = UVData()
    acc: List[UVData] = []
    for i, path in enumerate(file_list):
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
            tmp.Npols)

    t_cat0 = time.perf_counter()
    uv = acc[0]
    if len(acc) > 1:
        uv.fast_concat(acc[1:], axis="freq", inplace=True, run_check=False)
    logger.info("Concatenated %d subbands in %.2fs",
                len(acc), time.perf_counter() - t_cat0)

    # Ensure ascending frequency order for CASA compatibility
    uv.reorder_freqs(channel_order="freq", run_check=False)
    return uv


def _set_phase_and_uvw(
        uv: UVData) -> tuple[u.Quantity, u.Quantity, u.Quantity]:
    """
    Set antenna geometry and recompute phase and UVW coordinates.

    This function sets the antenna positions, calculates the phase center at the
    meridian, and then recomputes the UVW coordinates for the observation.
    """
    # Set antenna positions from the package data
    set_antenna_positions(uv)
    _ensure_antenna_diameters(uv)

    # Determine phase center (meridian at pointing dec)
    pt_dec = uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
    phase_time = Time(float(np.mean(uv.time_array)), format="jd")
    phase_ra, phase_dec = get_meridian_coords(pt_dec, phase_time.mjd)

    # Recompute UVW coordinates for the new phase center
    ant_pos = np.asarray(uv.antenna_positions)
    ant1 = np.asarray(uv.ant_1_array, dtype=int)
    ant2 = np.asarray(uv.ant_2_array, dtype=int)
    blen = ant_pos[ant2, :] - ant_pos[ant1, :]
    times_mjd = Time(uv.time_array, format='jd').mjd.astype(float)

    uv.uvw_array = calc_uvw_blt(
        blen,
        times_mjd,
        'J2000',
        phase_ra,
        phase_dec,
        obs='OVRO_MMA',
    )

    # Update UVData object with new phase info
    uv.phase_type = 'phased'
    uv.phase_center_ra = phase_ra.to_value(u.rad)
    uv.phase_center_dec = phase_dec.to_value(u.rad)
    uv.phase_center_frame = 'icrs'
    uv.phase_center_epoch = 2000.0

    return pt_dec, phase_ra, phase_dec


def convert_subband_groups_to_ms(
    input_dir: str,
    output_dir: str,
    start_time: str,
    end_time: str,
    *,
    flux: Optional[float] = None,
    scratch_dir: Optional[str] = None,
    writer: str = "direct-subband",
    writer_kwargs: Optional[dict] = None,
) -> None:
    """
    Main conversion function. Finds, merges, and converts subband groups to MS.

    Args:
        input_dir: Directory containing UVH5 files.
        output_dir: Directory to save the final Measurement Sets.
        start_time: Start of the processing time window.
        end_time: End of the processing time window.
        flux: Optional flux value in Jy to write to the MODEL_DATA column.
        scratch_dir: Temporary directory for intermediate files.
        writer: The name of the writer strategy to use.
        writer_kwargs: A dictionary of extra arguments for the chosen writer.
    """
    os.makedirs(output_dir, exist_ok=True)
    if scratch_dir:
        os.makedirs(scratch_dir, exist_ok=True)

    groups = find_subband_groups(input_dir, start_time, end_time)
    if not groups:
        logger.info("No complete subband groups to convert.")
        return

    for file_list in groups:
        first_file = os.path.basename(file_list[0])
        base_name = os.path.splitext(first_file)[0].split("_sb")[0]
        ms_path = os.path.join(output_dir, f"{base_name}.ms")
        logger.info("Converting group %s -> %s", base_name, ms_path)

        if os.path.exists(ms_path):
            logger.info("MS already exists, skipping: %s", ms_path)
            continue

        # The 'direct-subband' writer reads files itself, so we pass the list.
        # Other writers expect a merged UVData object.
        uv = None
        if writer != "direct-subband":
            t0 = time.perf_counter()
            uv = _load_and_merge_subbands(file_list)
            logger.info("Loaded and merged %d subbands in %.2fs",
                        len(file_list), time.perf_counter() - t0)

            t1 = time.perf_counter()
            pt_dec, phase_ra, phase_dec = _set_phase_and_uvw(uv)
            logger.info(
                "Phased and updated UVW in %.2fs",
                time.perf_counter() - t1)
        else:
            # Need these for the model column later
            temp_uv = UVData()
            temp_uv.read(file_list[0], read_data=False)
            pt_dec = temp_uv.extra_keywords.get(
                "phase_center_dec", 0.0) * u.rad
            phase_time = Time(float(np.mean(temp_uv.time_array)), format="jd")
            phase_ra, phase_dec = get_meridian_coords(pt_dec, phase_time.mjd)
            del temp_uv

        # Select and execute the writer strategy
        try:
            t_write_start = time.perf_counter()
            # Prepare kwargs for the writer
            current_writer_kwargs = writer_kwargs or {}
            current_writer_kwargs.setdefault("scratch_dir", scratch_dir)
            current_writer_kwargs.setdefault("file_list", file_list)

            writer_instance = get_writer(
                uv, ms_path, writer, **current_writer_kwargs)
            writer_type = writer_instance.write()

            logger.info(
                "Writer '%s' finished in %.2fs",
                writer_type,
                time.perf_counter() - t_write_start,
            )
            print(f"WRITER_TYPE: {writer_type}")

        except Exception as e:
            logger.exception("MS writing failed for group %s", base_name)
            # Clean up partially created MS
            if os.path.exists(ms_path):
                shutil.rmtree(ms_path, ignore_errors=True)
            continue

        # Post-processing steps
        try:
            addImagingColumns(ms_path)
        except Exception as e:
            logger.warning(
                "Failed to add imaging columns to %s: %s", ms_path, e)

        if flux is not None:
            try:
                # We need a UVData object to pass to set_model_column. If the writer
                # didn't use one, load the metadata.
                if uv is None:
                    uv = UVData()
                    uv.read(file_list, read_data=False)
                set_model_column(
                    base_name,
                    uv,
                    pt_dec,
                    phase_ra,
                    phase_dec,
                    flux_Jy=flux)
            except Exception as e:
                logger.warning("Failed to set MODEL_DATA column: %s", e)

        logger.info("✓ Successfully created %s", ms_path)


def create_parser() -> argparse.ArgumentParser:
    """Creates the command-line argument parser."""
    p = argparse.ArgumentParser(
        description="Convert DSA-110 subband UVH5 to MS (v2 Strategy Pattern)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "input_dir",
        help="Directory containing UVH5 subband files.")
    p.add_argument("output_dir", help="Directory to save Measurement Sets.")
    p.add_argument(
        "start_time",
        help="Start of processing window (YYYY-MM-DD HH:MM:SS).")
    p.add_argument(
        "end_time",
        help="End of processing window (YYYY-MM-DD HH:MM:SS).")
    p.add_argument(
        "--writer",
        default="direct-subband",
        choices=["direct-subband", "pyuvdata"],
        help="The MS writing strategy to use.",
    )
    p.add_argument(
        "--flux",
        type=float,
        help="Optional flux in Jy to write to MODEL_DATA.")
    p.add_argument(
        "--scratch-dir",
        help="Scratch directory for temporary files.")
    p.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Number of parallel workers for the 'direct-subband' writer.",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level.",
    )
    return p


def main() -> int:
    """Main command-line entry point."""
    parser = create_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set safe defaults for CASA environment
    os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    os.environ.setdefault("MKL_NUM_THREADS", "4")

    writer_kwargs = {
        "max_workers": args.max_workers,
    }

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
    sys.exit(main())
