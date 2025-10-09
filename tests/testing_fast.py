#!/usr/bin/env python3
"""
testing_fast.py — fast partial-read test + tiny MS write with progress logs.

Reads a tiny slice from all 16 subbands (first time, small channel/antenna
subset), recomputes UVW with metadata-only projection (no DATA rotation),
and writes a small MS. Prints progress for each subband.

Defaults can be overridden via env vars:
  IN_DIR  (default: /data/incoming_test/2025-09-05T03-12-56_HDF5)
  OUT_MS  (default: /data/output/ms_quick_tiny/partial_tiny.ms)
  START   (default: 2025-09-05 03:12:00)
  END     (default: 2025-09-05 03:13:30)

Run with casa6 python for correct deps:
  /opt/miniforge/envs/casa6/bin/python testing_fast.py
"""

from __future__ import print_function

import os
import sys
import time
import shutil
import h5py
import numpy as np
import astropy.units as u
from astropy.time import Time
from pyuvdata import UVData

SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

# Stability envs
os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("CASACORE_TABLE_LOCKING", "FALSE")

from dsa110_contimg.conversion import uvh5_to_ms_converter_v2 as v2
from dsa110_contimg.conversion.helpers import (
    set_antenna_positions,
    _ensure_antenna_diameters,
)

IN_DIR = os.environ.get("IN_DIR", "/data/incoming_test/2025-09-05T03-12-56_HDF5")
OUT_MS = os.environ.get("OUT_MS", "/data/output/ms_quick_tiny/partial_tiny.ms")
START  = os.environ.get("START",  "2025-09-05 03:12:00")
END    = os.environ.get("END",    "2025-09-05 03:13:30")

# Trim parameters
N_TIMES_KEEP = int(os.environ.get("N_TIMES_KEEP", "1"))
N_CH_KEEP    = int(os.environ.get("N_CH_KEEP",    "16"))
N_ANTS_KEEP  = int(os.environ.get("N_ANTS_KEEP",  "8"))


def first_unique_time_jd(uvh5_path):
    with h5py.File(uvh5_path, "r") as f:
        tarr = f["Header"]["time_array"][()]
    u = np.unique(tarr)
    return float(u[0])


def partial_read_merge(files, n_times_keep=1, n_chan_keep=16, n_ants_keep=8):
    # Compute a narrow time_range around the first file's first unique time
    jd0 = first_unique_time_jd(files[0])
    time_rng = (jd0 - 1e-9, jd0 + 1e-9)

    uv = UVData()
    first = True
    acc = []
    keep_ants = None

    for i, path in enumerate(sorted(files)):
        print("[read] %2d/%2d %s" % (i + 1, len(files), os.path.basename(path)))
        tmp = UVData()
        t0 = time.time()
        tmp.read(
            path,
            file_type="uvh5",
            time_range=time_rng,
            freq_chans=np.arange(n_chan_keep),
            polarizations=[-5, -6],
            run_check=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
            check_extra=False,
        )
        # Ensure UVW is float64 to satisfy pyuvdata checks
        try:
            tmp.uvw_array = tmp.uvw_array.astype(np.float64)
        except Exception:
            pass
        if first:
            ant_ids = np.unique(np.r_[tmp.ant_1_array[:tmp.Nbls], tmp.ant_2_array[:tmp.Nbls]]).astype(int)
            keep_ants = ant_ids[:min(n_ants_keep, ant_ids.size)]
            tmp.select(antenna_nums=keep_ants, run_check=False)
            uv = tmp
            first = False
        else:
            tmp.select(antenna_nums=keep_ants, run_check=False)
            try:
                tmp.uvw_array = tmp.uvw_array.astype(np.float64)
            except Exception:
                pass
            acc.append(tmp)
        print("       selected: Ntimes=%d Nchan=%d Nbls=%d" % (tmp.Ntimes, tmp.Nfreqs, tmp.Nbls))
        print("       read dt=%.2fs" % (time.time() - t0))

    if acc:
        print("[merge] concatenating %d extra subbands along freq" % len(acc))
        uv.fast_concat(
            acc,
            axis="freq",
            inplace=True,
            run_check=False,
            check_extra=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
            ignore_name=True,
        )
    return uv


def write_tiny_ms(in_dir, out_ms):
    groups = v2.find_subband_groups(in_dir, START, END)
    if not groups:
        raise RuntimeError("No complete subband groups found")
    files = groups[0]
    print("[group] found %d subbands" % len(files))

    uv = partial_read_merge(files, N_TIMES_KEEP, N_CH_KEEP, N_ANTS_KEEP)

    # Geometry and metadata-only projection
    print("[geom] setting antenna positions/diameters")
    set_antenna_positions(uv)
    _ensure_antenna_diameters(uv)

    print("[phase] single-center ICRS/J2000 + UVW (no DATA rotation)")
    pt_dec = uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
    t_mid_mjd = Time(float(np.mean(uv.time_array)), format="jd").mjd
    ra_icrs, dec_icrs = v2.get_meridian_coords(pt_dec, t_mid_mjd)

    # Reset catalog and assign one equatorial center
    uv.phase_center_catalog = {}
    pc_id = uv._add_phase_center(
        cat_name="FIELD_CENTER",
        cat_type="sidereal",
        cat_lon=float(ra_icrs.to_value(u.rad)),
        cat_lat=float(dec_icrs.to_value(u.rad)),
        cat_frame="icrs",
        cat_epoch=2000.0,
    )
    if not hasattr(uv, "phase_center_id_array") or uv.phase_center_id_array is None:
        uv.phase_center_id_array = np.zeros(uv.Nblts, dtype=int)
    uv.phase_center_id_array[:] = pc_id

    # Recompute UVW for each time bin against this fixed phase center
    try:
        uv.uvw_array = uv.uvw_array.astype(np.float64)
    except Exception:
        pass
    nbls = uv.Nbls
    ant_pos = np.asarray(uv.antenna_positions)
    ant1 = np.asarray(uv.ant_1_array[:nbls], dtype=int)
    ant2 = np.asarray(uv.ant_2_array[:nbls], dtype=int)
    blen = ant_pos[ant2, :] - ant_pos[ant1, :]
    times = np.unique(uv.time_array)
    for i, tval in enumerate(times):
        row_slice = slice(i * nbls, (i + 1) * nbls)
        time_vec = np.full(nbls, float(Time(tval, format="jd").mjd), dtype=float)
        uv.uvw_array[row_slice, :] = v2.calc_uvw_blt(
            blen,
            time_vec,
            'J2000',
            ra_icrs,
            dec_icrs,
            obs='OVRO_MMA',
        )

    # Ascending frequency and MS-friendly metadata
    uv.reorder_freqs(channel_order="freq", run_check=False)
    uv.phase_type = "phased"
    uv.phase_center_frame = "icrs"
    uv.phase_center_epoch = 2000.0

    out_dir = os.path.dirname(out_ms)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(out_ms):
        shutil.rmtree(out_ms)

    print("[write] MS -> %s" % out_ms)
    t0 = time.time()
    uv.write_ms(
        out_ms,
        clobber=True,
        run_check=False,
        check_extra=False,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
        check_autos=False,
        fix_autos=False,
    )
    dt = time.time() - t0
    print("[done] wrote tiny MS in %.2fs" % dt)
    print("Dims: Ntimes=%d Nbls=%d Nblts=%d Nchan=%d Npols=%d" % (uv.Ntimes, uv.Nbls, uv.Nblts, uv.Nfreqs, uv.Npols))


if __name__ == "__main__":
    write_tiny_ms(IN_DIR, OUT_MS)
