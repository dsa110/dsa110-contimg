# testing.py: partial read + tiny MS write
from dsa110_contimg.conversion.helpers import set_antenna_positions, _ensure_antenna_diameters
from dsa110_contimg.conversion import uvh5_to_ms_converter_v2 as v2
import os
import sys
import shutil
import time
import glob
import numpy as np
import h5py
import astropy.units as u
from astropy.time import Time
from pyuvdata import UVData

SRC_ROOT = "/data/dsa110-contimg/src"
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

# Stability envs
os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("CASACORE_TABLE_LOCKING", "FALSE")


IN_DIR = "/data/incoming_test/2025-09-05T03-12-56_HDF5"
OUT_MS = "/data/output/ms_quick_tiny/partial_tiny.ms"
START = "2025-09-05 03:12:00"
END = "2025-09-05 03:13:30"

# Trim parameters
N_TIMES_KEEP = 1
N_CH_KEEP = 16
N_ANTS_KEEP = 8

os.makedirs(os.path.dirname(OUT_MS), exist_ok=True)


def first_unique_time_jd(uvh5_path):
    # Fast metadata read via h5py: read only time_array and derive first
    # unique JD
    with h5py.File(uvh5_path, "r") as f:
        tarr = f["Header"]["time_array"][()]  # shape (Nblts,)
    # Each unique time is repeated Nbls times; take first unique
    u = np.unique(tarr)
    return float(u[0])


def partial_read_merge(files, n_times_keep=1, n_chan_keep=16, n_ants_keep=8):
    # We’ll select 1 time via time_range derived from the first file,
    # and limit channels + antennas at read to avoid pulling full data.
    # Choose time_range around the first unique JD.
    jd0 = first_unique_time_jd(files[0])
    time_rng = (jd0 - 1e-9, jd0 + 1e-9)  # narrow band around first time

    uv = UVData()
    first = True
    acc = []

    # Pre-declare selection for channels; we do antenna selection after first read if needed.
    # For uvh5, freq_chans selection in read() is supported and efficient.
    # We'll also restrict to XX, YY (CASA pol codes -5, -6).
    for i, path in enumerate(sorted(files)):
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
        if first:
            # Now apply antenna selection here (after we have ant arrays) once
            # We will do a second selection pass on tmp to keep identical ants
            # across subbands.
            ant_ids = np.unique(
                np.r_[tmp.ant_1_array[:tmp.Nbls], tmp.ant_2_array[:tmp.Nbls]]).astype(int)
            keep_ants = ant_ids[:min(n_ants_keep, ant_ids.size)]
            tmp.select(antenna_nums=keep_ants, run_check=False)
            uv = tmp
            first = False
        else:
            tmp.select(antenna_nums=keep_ants, run_check=False)
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
            ignore_name=True)

    return uv


def write_tiny_ms(in_dir, out_ms):
    groups = v2.find_subband_groups(in_dir, START, END)
    if not groups:
        raise RuntimeError("No complete subband groups found")
    files = groups[0]

    # Partial read all subbands with selection applied during read (fast)
    uv = partial_read_merge(files, N_TIMES_KEEP, N_CH_KEEP, N_ANTS_KEEP)

    # Geometry and metadata-only projection
    set_antenna_positions(uv)
    _ensure_antenna_diameters(uv)

    # Per-time phase centers + UVW recompute (no DATA rotation)
    # Use the convenience function; it handles per-time UVW and ICRS/J2000
    # coercion
    pt_dec = uv.extra_keywords.get("phase_center_dec", 0.0) * u.rad
    v2.set_per_time_phase_centers(uv, pt_dec)

    # Ascending frequency and mark as phased
    uv.reorder_freqs(channel_order="freq", run_check=False)
    uv.phase_type = "phased"

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
    dt = time.time() - t0
    print(f"Wrote tiny MS: {out_ms} in {dt:.2f} s")
    print(
        "Dims:",
        "Ntimes",
        uv.Ntimes,
        "Nbls",
        uv.Nbls,
        "Nblts",
        uv.Nblts,
        "Nchan",
        uv.Nfreqs,
        "Npols",
        uv.Npols)


# Run
if __name__ == "__main__":
    groups = v2.find_subband_groups(IN_DIR, START, END)
    assert groups, "No groups found"
    write_tiny_ms(IN_DIR, OUT_MS)
