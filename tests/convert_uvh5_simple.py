#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple UVH5 to MS converter without circular import dependencies.
"""

import os
import sys
import time
import glob
import logging
import subprocess
# from pathlib import Path  # Not available in Python 2.7
# from typing import Dict, List, Optional, Sequence, Tuple  # Not
# available in Python 2.7

import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord
from pyuvdata import UVData
from casacore.tables import addImagingColumns

# Add the source directory to Python path
sys.path.insert(0, '/data/dsa110-contimg/src')

logger = logging.getLogger("uvh5_to_ms_converter_simple")


def _parse_timestamp_from_filename(filename):
    base = os.path.splitext(filename)[0]
    if "_sb" not in base:
        return None
    ts = base.split("_sb", 1)[0]
    # Expect ISO-like YYYY-MM-DDTHH:MM:SS
    try:
        return Time(ts)
    except Exception:
        return None


def _extract_subband_code(filename):
    """Return subband code in canonical form 'sbXX' from a filename."""
    base = os.path.splitext(filename)[0]
    if "_sb" not in base:
        return None
    tail = base.rsplit("_sb", 1)[1]
    # Normalize to 'sbXX'
    if tail.startswith('sb'):
        return tail
    return "sb" + tail


def find_subband_groups(
    input_dir,
    start_time,
    end_time,
    spw=None,
    same_timestamp_tolerance_s=30.0,
):
    """Identify complete subband groups within a time window using ±30 s tolerance."""
    if spw is None:
        spw = ["sb{:02d}".format(idx) for idx in range(16)]

    tmin = Time(start_time)
    tmax = Time(end_time)

    # Gather candidate files
    candidates = []
    for path in glob.glob(os.path.join(input_dir, "*_sb??.hdf5")):
        fname = os.path.basename(path)
        ts = _parse_timestamp_from_filename(fname)
        if ts is None:
            continue
        if not (tmin <= ts <= tmax):
            continue
        code = _extract_subband_code(fname) or ""
        if code not in spw:
            continue
        candidates.append((path, ts))

    if not candidates:
        logger.info(
            "No subband files found in %s between %s and %s",
            input_dir,
            start_time,
            end_time)
        return []

    # Group by timestamp closeness (±tolerance)
    candidates.sort(key=lambda it: it[1].unix)
    times_sec = np.array([ts.unix for _, ts in candidates], dtype=float)
    files = np.array([p for p, _ in candidates])

    groups = []
    used = np.zeros(len(times_sec), dtype=bool)
    atol = same_timestamp_tolerance_s

    for i in range(len(times_sec)):
        if used[i]:
            continue
        # Close in time to times[i]
        close = np.abs(times_sec - times_sec[i]) <= atol
        idxs = np.where(close & (~used))[0]
        if idxs.size == 0:
            continue
        # Select matching SPWs and order by sbXX suffix
        selected = [files[j] for j in idxs]
        pairs = [(p, _extract_subband_code(os.path.basename(p)) or "")
                 for p in selected]
        # Keep only desired spw set
        pairs = [(p, s) for (p, s) in pairs if s in spw]
        if len(pairs) != len(spw):
            continue
        pairs.sort(key=lambda ps: ps[1])
        groups.append([p for p, _ in pairs])
        used[idxs] = True

    return groups


def _load_and_merge_subbands(file_list):
    """Read a list of UVH5 subband files and merge along frequency (ascending)."""
    uv = UVData()
    first = True
    acc = []
    for i, path in enumerate(file_list):
        t_read0 = time.time()
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
        logger.info(
            "Read subband %d in %.2fs (Nblts=%s, Nfreqs=%s, Npols=%s)",
            i + 1,
            time.time() - t_read0,
            tmp.Nblts,
            tmp.Nfreqs,
            tmp.Npols)
        tmp.uvw_array = tmp.uvw_array.astype(np.float64)
        if first:
            uv = tmp
            first = False
        else:
            acc.append(tmp)

    if acc:
        try:
            t_cat0 = time.time()
            uv.fast_concat(
                acc, axis="freq", inplace=True,
                run_check=False, check_extra=False,
                run_check_acceptability=False, strict_uvw_antpos_check=False,
                ignore_name=True,
            )
            logger.info(
                "Concatenated %d subbands in %.2fs",
                len(acc) + 1,
                time.time() - t_cat0)
        except Exception as e:
            logger.warning(
                "fast_concat across subbands failed (%s). Proceeding with first subband only for this quick run.",
                e,
            )

    # Ensure ascending frequency order
    try:
        uv.reorder_freqs(channel_order="freq", run_check=False)
    except Exception:
        pass

    # CASA works more smoothly with a known telescope name
    try:
        uv.telescope_name = "CARMA"
    except Exception:
        pass

    # Rename antenna names for clarity if needed
    try:
        names = list(getattr(uv, "antenna_names", []))
        if names and not all(str(n).startswith("pad") for n in names):
            uv.antenna_names = [
                "pad" + str(n) if not str(n).startswith("pad") else str(n) for n in names]
    except Exception:
        pass

    return uv


def convert_subband_groups_to_ms(
    input_dir,
    output_dir,
    start_time,
    end_time,
    flux=None,
):
    """Convert all complete subband groups in `input_dir` to MS in `output_dir`."""
    os.makedirs(output_dir, exist_ok=True)

    # Default to canonical 16 if not obvious
    expected = ["sb{:02d}".format(idx) for idx in range(16)]
    try:
        # Probe directory for present sb codes
        present = set()
        for p in glob.glob(os.path.join(input_dir, "*_sb??.hdf5")):
            code = _extract_subband_code(os.path.basename(p))
            if code:
                present.add(code)
        if 0 < len(present) < 16:
            expected = sorted(present)
    except Exception:
        pass

    groups = find_subband_groups(input_dir, start_time, end_time, spw=expected)
    if not groups:
        logger.info("No complete subband groups to convert")
        return

    for file_list in groups:
        first_file = os.path.basename(file_list[0])
        base = os.path.splitext(first_file)[0].split("_sb")[0]
        msname = os.path.join(output_dir, base)
        logger.info("Converting group %s -> %s.ms", base, msname)

        # Load & merge subbands
        t0 = time.time()
        uv = _load_and_merge_subbands(file_list)
        logger.info("Timing: load+merge took %.2fs", time.time() - t0)

        # Paths
        ms_final_path = msname + ".ms"
        if os.path.exists(ms_final_path):
            import shutil
            shutil.rmtree(ms_final_path, ignore_errors=True)

        # Write MS using pyuvdata
        logger.info("Direct pyuvdata.write_ms -> %s", ms_final_path)
        t5 = time.time()
        uv.write_ms(
            ms_final_path,
            clobber=True,
            run_check=False,
            check_extra=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
            check_autos=False,
            fix_autos=False,
            force_phase=True,
        )
        logger.info("Timing: pyuvdata write took %.2fs", time.time() - t5)

        # Ensure imaging columns exist after writing
        try:
            addImagingColumns(ms_final_path)
        except Exception:
            pass

        logger.info("✓ Wrote %s", ms_final_path)


def main():
    import argparse

    p = argparse.ArgumentParser(
        description="Convert DSA-110 subband UVH5 to MS (simple)")
    p.add_argument("input_dir")
    p.add_argument("output_dir")
    p.add_argument("start_time", help="YYYY-MM-DD HH:MM:SS")
    p.add_argument("end_time", help="YYYY-MM-DD HH:MM:SS")
    p.add_argument("--flux", type=float)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    try:
        logging.basicConfig(
            level=getattr(logging, args.log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    except Exception:
        pass

    # Apply safe default environment overrides for stability
    os.environ.setdefault('HDF5_USE_FILE_LOCKING', 'FALSE')
    os.environ.setdefault('OMP_NUM_THREADS', '4')
    os.environ.setdefault('MKL_NUM_THREADS', '4')

    convert_subband_groups_to_ms(
        args.input_dir,
        args.output_dir,
        args.start_time,
        args.end_time,
        flux=args.flux,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
