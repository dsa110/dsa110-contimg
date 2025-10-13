#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSA-110 UVH5 → CASA MS converter (pyuvdata-only).

This tool writes Measurement Sets using pyuvdata only (no dask-ms). It supports
multi–phase-center output so you can generate one FIELD per integration (e.g.,
24 fields over ~5 minutes) to enable robust calibrator search.
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import List, Optional, Sequence

import numpy as np
import astropy.units as u
from astropy.time import Time
from casacore.tables import addImagingColumns
from pyuvdata import UVData

from .helpers import (
    set_antenna_positions,
    _ensure_antenna_diameters,
    get_meridian_coords,
    compute_and_set_uvw,
    set_model_column,
)
from .strategies.uvh5_to_ms_converter import (
    _parse_timestamp_from_filename,
    _extract_subband_code,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert DSA-110 subband UVH5 to MS (pyuvdata-only)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("input_dir", help="Directory containing UVH5 subband files")
    p.add_argument("output_dir", help="Directory to write Measurement Sets")
    p.add_argument("start_time", help="Start of window (YYYY-MM-DD HH:MM:SS)")
    p.add_argument("end_time", help="End of window (YYYY-MM-DD HH:MM:SS)")

    # Common options
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="Logging verbosity")
    p.add_argument("--scratch-dir", help="Scratch directory for intermediate files")
    p.add_argument("--flux", type=float, default=None,
                   help="Optional flux (Jy) to populate MODEL_DATA")

    # Multi-field (per-integration FIELD rows)
    p.add_argument(
        "--field-per-integration",
        action="store_true",
        default=True,
        help="Create one FIELD per unique integration time (multi phase centers)",
    )

    # Compatibility no-ops (accepted, ignored)
    p.add_argument("--tmpfs-path", default=None, help="[Ignored] tmpfs staging path")
    p.add_argument("--no-stage-tmpfs", action="store_true", help="[Ignored] disable tmpfs staging")
    p.add_argument("--daskms-row-chunks", type=int, default=None, help="[Ignored] dask-ms row chunking")
    p.add_argument("--daskms-cube-row-chunks", type=int, default=None, help="[Ignored] dask-ms cube rows")
    
    return p


def _find_subband_groups(
    input_dir: str,
    start_time: str,
    end_time: str,
    *,
    spw: Optional[Sequence[str]] = None,
    tolerance_s: float = 30.0,
) -> List[List[str]]:
    """Identify complete subband groups within a time window (sb00..sb15)."""
    import glob, os
    if spw is None:
        spw = [f"sb{idx:02d}" for idx in range(16)]
    tmin = Time(start_time)
    tmax = Time(end_time)
    candidates = []
    for path in glob.glob(os.path.join(input_dir, "*_sb??.hdf5")):
        ts = _parse_timestamp_from_filename(os.path.basename(path))
        if ts and tmin <= ts <= tmax:
            candidates.append((path, ts))
    if not candidates:
        return []
    candidates.sort(key=lambda it: it[1].unix)
    times_sec = np.array([ts.unix for _, ts in candidates])
    files = np.array([p for p, _ in candidates])
    groups: List[List[str]] = []
    used = np.zeros(len(times_sec), dtype=bool)
    for i in range(len(times_sec)):
        if used[i]:
            continue
        idxs = np.where(np.abs(times_sec - times_sec[i]) <= tolerance_s)[0]
        idxs = [j for j in idxs if not used[j]]
        selected = [files[j] for j in idxs]
        subband_map = { _extract_subband_code(os.path.basename(p)) : p for p in selected }
        if set(subband_map.keys()) == set(spw):
            groups.append([subband_map[s] for s in sorted(spw)])
            for j in idxs: used[j] = True
    return groups


def _load_and_merge_subbands(file_list: Sequence[str]) -> UVData:
    """Read subband UVH5 files and merge along frequency into a monolithic UVData."""
    import logging as _lg
    import warnings
    log = _lg.getLogger(__name__)
    acc: List[UVData] = []
    # Quiet pyuvdata warnings during raw reads
    pulog = _lg.getLogger('pyuvdata')
    prev = pulog.level
    try:
        pulog.setLevel(_lg.ERROR)
        for i, path in enumerate(file_list):
            tmp = UVData()
            with warnings.catch_warnings():
                # Suppress UVW consistency warnings during raw reads; we
                # recompute UVW after setting phase centers.
                warnings.filterwarnings(
                    "ignore",
                    message=r".*uvw_array does not match.*",
                    category=Warning,
                )
                tmp.read(
                    path,
                    file_type='uvh5',
                    run_check=False,
                    check_extra=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                )
            tmp.uvw_array = tmp.uvw_array.astype(np.float64)
            acc.append(tmp)
            log.info("Read subband %d/%d: %s", i+1, len(file_list), os.path.basename(path))
    finally:
        try:
            pulog.setLevel(prev)
        except Exception:
            pass
    uv = acc[0]
    if len(acc) > 1:
        uv.fast_concat(acc[1:], axis='freq', inplace=True, run_check=False)
    # Ensure ascending frequency order
    uv.reorder_freqs(channel_order='freq', run_check=False)
    return uv


def _peek_uvh5_phase_and_midtime(uvh5_path: str) -> tuple[u.Quantity, float]:
    """Lightweight HDF5 peek: return (pt_dec [rad], mid_time [MJD])."""
    import h5py
    pt_dec_val: float = 0.0
    mid_jd: float = 0.0
    with h5py.File(uvh5_path, "r") as f:
        # time_array endpoints -> mid
        if "time_array" in f:
            d = f["time_array"]
            n = d.shape[0]
            if n >= 2:
                t0 = float(d[0]); t1 = float(d[n-1])
                mid_jd = 0.5 * (t0 + t1)
            elif n == 1:
                mid_jd = float(d[0])
        # extra_keywords.phase_center_dec may exist
        def _get_extra(name: str):
            try:
                if "extra_keywords" in f and name in f["extra_keywords"]:
                    return float(np.asarray(f["extra_keywords"][name]))
            except Exception:
                pass
            try:
                if "Header" in f and "extra_keywords" in f["Header"] and name in f["Header"]["extra_keywords"]:
                    return float(np.asarray(f["Header"]["extra_keywords"][name]))
            except Exception:
                pass
            try:
                if name in f.attrs:
                    return float(f.attrs[name])
            except Exception:
                pass
            return None
        val = _get_extra("phase_center_dec")
        if val is not None and np.isfinite(val):
            pt_dec_val = float(val)
    return pt_dec_val * u.rad, (Time(mid_jd, format='jd').mjd if mid_jd else 0.0)


def _write_ms_multifield(uv: UVData, ms_out: str, *, flux: Optional[float] = None, pt_dec: Optional[u.Quantity] = None) -> None:
    """Assign per-integration phase centers, recompute UVW, and write MS with many FIELDs."""
    # Antenna metadata
    set_antenna_positions(uv)
    _ensure_antenna_diameters(uv)

    # Unique integration times and mapping
    utime, _, uinvert = np.unique(uv.time_array, return_index=True, return_inverse=True)
    mjd = Time(utime, format='jd').mjd.astype(float)
    # Pointing declination
    if pt_dec is None:
        pt_dec = uv.extra_keywords.get('phase_center_dec', 0.0) * u.rad

    # Build multi phase center catalog: one per unique time
    uv.phase_center_catalog = {}
    pc_ids: List[int] = []
    for i, t in enumerate(mjd):
        ra_icrs, dec_icrs = get_meridian_coords(pt_dec, float(t))
        # Name fields using RA at meridian (J2000 frame), avoiding Time.sidereal_time location requirement
        ra_hms = ra_icrs.to(u.hourangle).to_string(sep=':', precision=3)
        name = f"drift_ra{ra_hms}_t{i:03d}"
        pc_id = uv._add_phase_center(
            cat_name=name,
            cat_type='sidereal',
            cat_lon=float(ra_icrs.to_value(u.rad)),
            cat_lat=float(dec_icrs.to_value(u.rad)),
            cat_frame='icrs',
            cat_epoch=2000.0,
        )
        pc_ids.append(pc_id)
    # Map each row to its phase center id
    if getattr(uv, 'phase_center_id_array', None) is None:
        uv.phase_center_id_array = np.zeros(uv.Nblts, dtype=int)
    uv.phase_center_id_array[:] = np.asarray([pc_ids[k] for k in uinvert], dtype=int)

    # Recompute UVW per row to the (per-time) meridian direction
    compute_and_set_uvw(uv, pt_dec)

    # Mark phased
    uv.phase_type = 'phased'
    uv.phase_center_frame = 'icrs'
    uv.phase_center_epoch = 2000.0

    # Write MS with a multi-field structure
    uv.write_ms(ms_out, clobber=True,
                run_check=False, check_extra=False,
                run_check_acceptability=False,
                strict_uvw_antpos_check=False,
                check_autos=False, fix_autos=False,
                force_phase=True)

    # Add imaging columns and optional MODEL_DATA
    try:
        addImagingColumns(ms_out)
    except Exception:
        pass
    if flux is not None:
        try:
            # For MODEL_DATA we can use a single (mid-time) meridian center
            ra_mid, dec_mid = get_meridian_coords(pt_dec, float(np.mean(mjd)))
            set_model_column(ms_out.rstrip('.ms'), uv, pt_dec, ra_mid, dec_mid, flux_jy=flux)
        except Exception:
            pass


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Silence pyuvdata UVW mismatch noise during raw reads — we recompute UVW later
    import warnings as _warnings
    _warnings.filterwarnings("ignore", message=r".*uvw_array does not match.*", category=Warning)
    try:
        from pyuvdata import warnings as _puw  # type: ignore
        if hasattr(_puw, 'UVDataWarning'):
            _warnings.filterwarnings("ignore", message=r".*uvw_array does not match.*", category=_puw.UVDataWarning)
    except Exception:
        pass
    try:
        logging.getLogger('pyuvdata').setLevel(logging.ERROR)
    except Exception:
        pass

    # CASA/HDF5 stability knobs
    os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

    # Find complete groups in window
    groups = _find_subband_groups(args.input_dir, args.start_time, args.end_time)
    if not groups:
        logging.info("No complete subband groups to convert.")
        return 0

    os.makedirs(args.output_dir, exist_ok=True)
    for file_list in groups:
        base = os.path.splitext(os.path.basename(file_list[0]))[0].split('_sb')[0]
        ms_out = os.path.join(args.output_dir, f"{base}.ms")
        if os.path.isdir(ms_out):
            logging.info("MS exists, skipping: %s", ms_out)
            continue
        # Peek HDF5 for pt_dec (and mid-time if needed) without instantiating UVData
        pt_dec_peek, _mid_mjd = _peek_uvh5_phase_and_midtime(file_list[0])
        # Merge subbands
        uv = _load_and_merge_subbands(file_list)
        if args.field_per_integration:
            _write_ms_multifield(uv, ms_out, flux=args.flux, pt_dec=pt_dec_peek)
        else:
            # Single-field fallback
            # Register single phase center at mid-time meridian and write
            set_antenna_positions(uv); _ensure_antenna_diameters(uv)
            pt_dec = pt_dec_peek if isinstance(pt_dec_peek, u.Quantity) else (uv.extra_keywords.get('phase_center_dec', 0.0) * u.rad)
            ra_mid, dec_mid = get_meridian_coords(pt_dec, float(Time(float(np.mean(uv.time_array)), format='jd').mjd))
            uv.phase_center_catalog = {}
            pc_id = uv._add_phase_center(
                cat_name='meridian_icrs', cat_type='sidereal',
                cat_lon=float(ra_mid.to_value(u.rad)), cat_lat=float(dec_mid.to_value(u.rad)),
                cat_frame='icrs', cat_epoch=2000.0)
            if getattr(uv, 'phase_center_id_array', None) is None:
                uv.phase_center_id_array = np.zeros(uv.Nblts, dtype=int)
            uv.phase_center_id_array[:] = pc_id
            compute_and_set_uvw(uv, pt_dec)
            uv.phase_type='phased'; uv.phase_center_frame='icrs'; uv.phase_center_epoch=2000.0
            uv.write_ms(ms_out, clobber=True, run_check=False, check_extra=False,
                        run_check_acceptability=False, strict_uvw_antpos_check=False,
                        check_autos=False, fix_autos=False, force_phase=True)
            try:
                addImagingColumns(ms_out)
            except Exception:
                pass
            if args.flux is not None:
                try:
                    set_model_column(ms_out.rstrip('.ms'), uv, pt_dec, ra_mid, dec_mid, flux_jy=args.flux)
                except Exception:
                    pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
