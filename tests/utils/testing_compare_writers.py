#!/usr/bin/env python3
"""
testing_compare_writers.py — compare MS writer paths on a trimmed dataset.

Pipeline variants:
  A) Direct pyuvdata.write_ms (current default)
  B) UVFITS -> CASA importuvfits (legacy helper)

Both run on the same tiny selection (1 time, few chans/ants) across all 16
subbands. Times each write and reports resulting MS size.

Usage (run in casa6 env):
  /opt/miniforge/envs/casa6/bin/python testing_compare_writers.py \
      --in /data/incoming_test/2025-09-05T03-12-56_HDF5 \
      --out /data/output/ms_compare \
      --start "2025-09-05 03:12:00" --end "2025-09-05 03:13:30" \
      --times 1 --chans 16 --ants 8 --scratch /dev/shm
"""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

import astropy.units as u
import h5py
import numpy as np
from astropy.time import Time
from pyuvdata import UVData

# type: ignore[import]
from dsa110_contimg.conversion.helpers import (
    _ensure_antenna_diameters,
    get_meridian_coords,
    set_antenna_positions,
)
from dsa110_contimg.conversion.strategies import (
    hdf5_orchestrator as orch,  # type: ignore[import]
)

# type: ignore[import]
from dsa110_contimg.utils.fringestopping import calc_uvw_blt

SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("CASACORE_TABLE_LOCKING", "FALSE")


ARCHIVE_ROOT = Path(__file__).resolve().parents[1] / "archive"
if str(ARCHIVE_ROOT) not in sys.path:
    sys.path.insert(0, str(ARCHIVE_ROOT))

try:
    from legacy.core_conversion.uvh5_to_ms_converter import write_uvdata_to_ms
except Exception:  # pragma: no cover - legacy optional
    write_uvdata_to_ms = None


def dir_size_bytes(path: str) -> int:
    total = 0
    for dp, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except Exception:
                pass
    return total


def first_unique_time_jd(uvh5_path: str) -> float:
    with h5py.File(uvh5_path, "r") as f:
        tarr = f["Header"]["time_array"][()]
    u = np.unique(tarr)
    return float(u[0])


def partial_read_merge(files, n_times_keep=1, n_chan_keep=16, n_ants_keep=8) -> UVData:
    jd0 = first_unique_time_jd(files[0])
    time_rng = (jd0 - 1e-9, jd0 + 1e-9)

    uv = UVData()
    first = True
    acc = []
    keep_ants = None

    for _, path in enumerate(sorted(files)):
        tmp = UVData()
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
        try:
            tmp.uvw_array = tmp.uvw_array.astype(np.float64)
        except Exception:
            pass
        if first:
            ant_ids = np.unique(
                np.r_[tmp.ant_1_array[: tmp.Nbls], tmp.ant_2_array[: tmp.Nbls]]
            ).astype(int)
            keep_ants = ant_ids[: min(n_ants_keep, ant_ids.size)]
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

    if acc:
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


def ms_write_direct(uv: UVData, out_ms: str) -> float:
    if os.path.exists(out_ms):
        shutil.rmtree(out_ms)
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
    return time.time() - t0


def ms_write_uvfits(
    uv: UVData, out_base: str, abs_positions: np.ndarray, scratch_dir: str | None = None
) -> float:
    # out_base without .ms; write_uvdata_to_ms adds suffix internally via paths
    out_ms = out_base + ".ms"
    if os.path.exists(out_ms):
        shutil.rmtree(out_ms)
    t0 = time.time()
    if write_uvdata_to_ms is None:
        return float("nan")
    write_uvdata_to_ms(uv, out_base, abs_positions, scratch_dir=scratch_dir)
    return time.time() - t0


def main():
    ap = argparse.ArgumentParser(
        description="Compare pyuvdata.write_ms vs UVFITS import path on a tiny selection"
    )
    ap.add_argument("--in", dest="in_dir", default="/data/incoming_test/2025-09-05T03-12-56_HDF5")
    ap.add_argument("--out", dest="out_dir", default="/data/output/ms_compare")
    ap.add_argument("--start", default="2025-09-05 03:12:00")
    ap.add_argument("--end", default="2025-09-05 03:13:30")
    ap.add_argument("--times", type=int, default=1)
    ap.add_argument("--chans", type=int, default=16)
    ap.add_argument("--ants", type=int, default=8)
    ap.add_argument("--scratch", default=None, help="Scratch dir for UVFITS path (e.g., /dev/shm)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Discover group and build tiny UVData
    groups = orch.find_subband_groups(args.in_dir, args.start, args.end)
    if not groups:
        print("No complete subband groups found.")
        return 1
    files = groups[0]
    base = os.path.splitext(os.path.basename(files[0]))[0].split("_sb")[0]

    uv = partial_read_merge(files, args.times, args.chans, args.ants)

    # Geometry & metadata-only projection: single ICRS center + UVW recompute
    set_antenna_positions(uv)
    _ensure_antenna_diameters(uv)
    # Absolute positions for ANTENNA table in UVFITS path
    # Derive absolute by adding telescope_location (ECEF) back to relative
    # positions
    abs_positions = None
    try:
        tel = np.asarray(uv.telescope_location)  # type: ignore[attr-defined]
        rel = np.asarray(uv.antenna_positions)  # type: ignore[attr-defined]
        if tel.shape and rel.ndim == 2 and rel.shape[1] == 3:
            abs_positions = rel + tel  # (Nants, 3)
    except Exception:
        pass

    pt_dec = uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
    t_mid = Time(float(np.mean(uv.time_array)), format="jd").mjd
    ra_icrs, dec_icrs = get_meridian_coords(pt_dec, t_mid)

    # Reset to one center, set IDs
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

    # Recompute UVW per time
    try:
        uv.uvw_array = uv.uvw_array.astype(np.float64)
    except Exception:
        pass
    nbls = uv.Nbls
    ant_pos = np.asarray(uv.antenna_positions)  # type: ignore[attr-defined]
    ant1 = np.asarray(uv.ant_1_array[:nbls], dtype=int)
    ant2 = np.asarray(uv.ant_2_array[:nbls], dtype=int)
    blen = ant_pos[ant2, :] - ant_pos[ant1, :]
    times = np.unique(uv.time_array)
    for i, tval in enumerate(times):
        row_slice = slice(i * nbls, (i + 1) * nbls)
        time_vec = np.full(nbls, float(Time(tval, format="jd").mjd), dtype=float)
        uv.uvw_array[row_slice, :] = calc_uvw_blt(
            blen,
            time_vec,
            "J2000",
            ra_icrs,
            dec_icrs,
            obs="OVRO_MMA",
        )

    uv.reorder_freqs(channel_order="freq", run_check=False)
    uv.phase_type = "phased"
    uv.phase_center_frame = "icrs"
    uv.phase_center_epoch = 2000.0

    # A) Direct write
    out_ms_direct = os.path.join(args.out_dir, base + "_direct_tiny.ms")
    dt_direct = ms_write_direct(uv, out_ms_direct)
    sz_direct = dir_size_bytes(out_ms_direct)
    print("[direct] time=%.2fs size=%.1f MB -> %s" % (dt_direct, sz_direct / 1e6, out_ms_direct))

    # B) UVFITS -> CASA import path
    out_base_uvfits = os.path.join(args.out_dir, base + "_uvfits_tiny")
    if abs_positions is None:
        # fallback: use relative as-is (writer updates ANTENNA if counts match)
        abs_positions = np.asarray(uv.antenna_positions)  # type: ignore[attr-defined]
    dt_uvfits = ms_write_uvfits(uv, out_base_uvfits, abs_positions, scratch_dir=args.scratch)
    out_ms_uvfits = out_base_uvfits + ".ms"
    sz_uvfits = dir_size_bytes(out_ms_uvfits)
    print("[uvfits] time=%.2fs size=%.1f MB -> %s" % (dt_uvfits, sz_uvfits / 1e6, out_ms_uvfits))

    return 0


if __name__ == "__main__":
    sys.exit(main())
