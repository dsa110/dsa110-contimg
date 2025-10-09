#!/usr/bin/env python3
"""
Standalone UVH5 to MS converter script to avoid circular import issues.
"""

import os
import sys
import time
import glob
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord
from pyuvdata import UVData
from casacore.tables import addImagingColumns

# Add the source directory to Python path
sys.path.insert(0, '/data/dsa110-contimg/src')

# Import required modules
from dsa110_contimg.calibration.model import write_point_model_with_ft
from dsa110_contimg.calibration.catalogs import read_vla_parsed_catalog_with_flux, nearest_calibrator_within_radius
from pyuvdata import utils as uvutils
import shutil
import csv

# Import helpers
from dsa110_contimg.conversion.helpers import (
    set_antenna_positions,
    _ensure_antenna_diameters,
    get_meridian_coords,
    set_model_column,
)
from dsa110_contimg.utils.fringestopping import calc_uvw_blt

logger = logging.getLogger("uvh5_to_ms_converter_standalone")

def _parse_timestamp_from_filename(filename: str) -> Optional[Time]:
    base = os.path.splitext(filename)[0]
    if "_sb" not in base:
        return None
    ts = base.split("_sb", 1)[0]
    # Expect ISO-like YYYY-MM-DDTHH:MM:SS
    try:
        return Time(ts)
    except Exception:
        return None

def _extract_subband_code(filename: str) -> Optional[str]:
    """Return subband code in canonical form 'sbXX' from a filename."""
    base = os.path.splitext(filename)[0]
    if "_sb" not in base:
        return None
    tail = base.rsplit("_sb", 1)[1]
    # Normalize to 'sbXX'
    if tail.startswith('sb'):
        return tail
    return f"sb{tail}"

def find_subband_groups(
    input_dir: str,
    start_time: str,
    end_time: str,
    *,
    spw: Optional[Sequence[str]] = None,
    same_timestamp_tolerance_s: float = 30.0,
) -> List[List[str]]:
    """Identify complete subband groups within a time window using ±30 s tolerance."""
    if spw is None:
        spw = [f"sb{idx:02d}" for idx in range(16)]

    tmin = Time(start_time)
    tmax = Time(end_time)

    # Gather candidate files
    candidates: List[Tuple[str, Time]] = []
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
        logger.info("No subband files found in %s between %s and %s", input_dir, start_time, end_time)
        return []

    # Group by timestamp closeness (±tolerance)
    candidates.sort(key=lambda it: it[1].unix)
    times_sec = np.array([ts.unix for _, ts in candidates], dtype=float)
    files = np.array([p for p, _ in candidates])

    groups: List[List[str]] = []
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
        pairs = [(p, _extract_subband_code(os.path.basename(p)) or "") for p in selected]
        # Keep only desired spw set
        pairs = [(p, s) for (p, s) in pairs if s in spw]
        if len(pairs) != len(spw):
            continue
        pairs.sort(key=lambda ps: ps[1])
        groups.append([p for p, _ in pairs])
        used[idxs] = True

    return groups

def _load_and_merge_subbands(file_list: Sequence[str]) -> UVData:
    """Read a list of UVH5 subband files and merge along frequency (ascending)."""
    uv = UVData()
    first = True
    acc: List[UVData] = []
    for i, path in enumerate(file_list):
        t_read0 = time.perf_counter()
        logger.info("Reading subband %d/%d: %s", i + 1, len(file_list), os.path.basename(path))
        tmp = UVData()
        tmp.read(
            path,
            file_type="uvh5",
            run_check=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
            check_extra=False,
        )
        logger.info("Read subband %d in %.2fs (Nblts=%s, Nfreqs=%s, Npols=%s)",
                    i + 1, time.perf_counter() - t_read0, tmp.Nblts, tmp.Nfreqs, tmp.Npols)
        tmp.uvw_array = tmp.uvw_array.astype(np.float64)
        if first:
            uv = tmp
            first = False
        else:
            acc.append(tmp)

    if acc:
        try:
            t_cat0 = time.perf_counter()
            uv.fast_concat(
                acc, axis="freq", inplace=True,
                run_check=False, check_extra=False,
                run_check_acceptability=False, strict_uvw_antpos_check=False,
                ignore_name=True,
            )
            logger.info("Concatenated %d subbands in %.2fs", len(acc) + 1, time.perf_counter() - t_cat0)
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
            uv.antenna_names = [f"pad{str(n)}" if not str(n).startswith("pad") else str(n) for n in names]
    except Exception:
        pass

    return uv

def convert_subband_groups_to_ms(
    input_dir: str,
    output_dir: str,
    start_time: str,
    end_time: str,
    *,
    flux: Optional[float] = None,
    cal_catalog: Optional[str] = None,
    cal_search_radius_deg: float = 0.0,
    cal_output_dir: Optional[str] = None,
) -> None:
    """Convert all complete subband groups in `input_dir` to MS in `output_dir`."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Default to canonical 16 if not obvious
    expected = [f"sb{idx:02d}" for idx in range(16)]
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
        logger.info("Converting group %s → %s.ms", base, msname)

        # Load & merge subbands
        t0 = time.perf_counter()
        uv = _load_and_merge_subbands(file_list)
        logger.info("Timing: load+merge took %.2fs", time.perf_counter() - t0)

        # Determine phase center (meridian at pointing dec) if not provided
        pt_dec = uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
        phase_time = Time(float(np.mean(uv.time_array)), format="jd")
        phase_ra_use, phase_dec_use = get_meridian_coords(pt_dec, phase_time.mjd)

        # Antenna geometry metadata
        t1 = time.perf_counter()
        set_antenna_positions(uv)
        _ensure_antenna_diameters(uv)
        logger.info("Timing: antenna setup took %.2fs", time.perf_counter() - t1)

        # Paths
        ms_final_path = f"{msname}.ms"
        if os.path.exists(ms_final_path):
            shutil.rmtree(ms_final_path, ignore_errors=True)

        # Write MS using pyuvdata
        logger.info("Direct pyuvdata.write_ms -> %s", ms_final_path)
        t5 = time.perf_counter()
        uv.write_ms(
            ms_final_path,
            clobber=True,
            run_check=False,
            check_extra=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
            check_autos=False,
            fix_autos=False,
        )
        logger.info("Timing: pyuvdata write took %.2fs", time.perf_counter() - t5)

        # Ensure imaging columns exist after writing
        try:
            addImagingColumns(ms_final_path)
        except Exception:
            pass

        # Optional: populate MODEL_DATA (unity/beam) when a flux is specified
        if flux is not None and pt_dec is not None:
            try:
                set_model_column(msname, uv, pt_dec, phase_ra_use, phase_dec_use, flux_Jy=flux)
            except Exception as e:
                logger.warning("MODEL_DATA write failed: %s", e)

        logger.info("✓ Wrote %s", ms_final_path)

        # Optional: produce a separate calibrator-model MS by searching a VLA catalog
        try:
            if cal_catalog and cal_search_radius_deg and cal_search_radius_deg > 0:
                cal_dir = cal_output_dir or output_dir
                os.makedirs(cal_dir, exist_ok=True)

                # Read VLA catalog and find nearest calibrator
                cdf = read_vla_parsed_catalog_with_flux(cal_catalog, band='20cm')
                pt_ra_deg = float(phase_ra_use.to_value(u.rad) * 180.0 / np.pi)
                pt_dec_deg = float(phase_dec_use.to_value(u.rad) * 180.0 / np.pi)
                match = nearest_calibrator_within_radius(pt_ra_deg, pt_dec_deg, cdf, cal_search_radius_deg)
                if not match:
                    logger.info("No calibrator found within %.2f deg of pointing", cal_search_radius_deg)
                else:
                    cal_name, cra_deg, cdec_deg, cflux = match
                    cal_msname = os.path.join(cal_dir, f"{cal_name}_{base}")
                    cal_mspath = cal_msname + ".ms"
                    # Copy base MS and write MODEL_DATA via CASA ft for correct complex model
                    try:
                        if os.path.exists(cal_mspath):
                            shutil.rmtree(cal_mspath, ignore_errors=True)
                        logger.info("Creating calibrator MS %s via copy", cal_mspath)
                        shutil.copytree(ms_final_path, cal_mspath)
                        addImagingColumns(cal_mspath)
                        # Flux fallback if missing
                        flux_use = float(cflux) if np.isfinite(cflux) else 8.0
                        write_point_model_with_ft(cal_mspath, cra_deg, cdec_deg, flux_use)
                        logger.info("✓ Wrote calibrator MS %s (MODEL_DATA for %s, %.2f Jy)", cal_mspath, cal_name, flux_use)
                    except Exception as e:
                        logger.warning("Calibrator MODEL_DATA write failed: %s", e)
        except Exception as e:
            logger.warning("Calibrator MS generation skipped: %s", e)

def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Convert DSA-110 subband UVH5 to MS (standalone)")
    p.add_argument("input_dir")
    p.add_argument("output_dir")
    p.add_argument("start_time", help="YYYY-MM-DD HH:MM:SS")
    p.add_argument("end_time", help="YYYY-MM-DD HH:MM:SS")
    p.add_argument("--flux", type=float)
    p.add_argument("--cal-catalog", default=None, help="Path to VLA calibrator CSV")
    p.add_argument("--cal-search-radius-deg", type=float, default=0.0, help="Search radius in degrees")
    p.add_argument("--cal-output-dir", default=None, help="Directory for calibrator-model MS")
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
        cal_catalog=args.cal_catalog,
        cal_search_radius_deg=float(args.cal_search_radius_deg or 0.0),
        cal_output_dir=args.cal_output_dir,
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
