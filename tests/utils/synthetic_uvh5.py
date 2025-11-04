# -*- coding: utf-8 -*-
"""Synthetic UVH5 generator for basic pipeline validation.

Generates a minimal two-subband UVH5 dataset with a single strong point
source at phase center. Intended for exercising conversion→calibration
without relying on external data.

Note: Requires pyuvdata installed in the active environment.
"""

from pathlib import Path
from typing import Tuple, Union
import numpy as np


def _make_minimal_uvdata(n_ants=4,
                         n_times=4,
                         n_chans=64,
                         start_freq_hz=1.4e9,
                         chan_bw_hz=1.0e6,
                         source_flux_jy=10.0):
    from pyuvdata import UVData
    from astropy.time import Time

    uv = UVData()
    ant_inds = np.arange(n_ants)
    bls = [(i, j) for i in ant_inds for j in ant_inds if i < j]
    n_bls = len(bls)

    # Times
    t0 = Time.now().jd
    time_array = np.linspace(t0, t0 + 1.0/86400.0, n_times)  # ~1 sec span

    # Frequencies
    freq_array = start_freq_hz + np.arange(n_chans) * chan_bw_hz

    # Data arrays
    nblts = n_bls * n_times
    uv.Nblts = nblts
    uv.Nbls = n_bls
    uv.Ntimes = n_times
    uv.Nfreqs = n_chans
    uv.Npols = 2

    uv.ant_1_array = np.repeat([b[0] for b in bls], n_times)
    uv.ant_2_array = np.repeat([b[1] for b in bls], n_times)
    uv.antenna_numbers = ant_inds
    uv.antenna_names = [str(i) for i in ant_inds]
    uv.Nants_data = n_ants
    uv.Nants_telescope = n_ants
    uv.time_array = np.tile(time_array, n_bls)
    uv.integration_time = np.ones(nblts, dtype=float)
    uv.lst_array = np.zeros(nblts, dtype=float)

    uv.freq_array = freq_array[np.newaxis, :]
    uv.channel_width = np.full(n_chans, chan_bw_hz, dtype=float)

    # Simple phase center @ RA=0, Dec=0
    uv.phase_center_ra = 0.0
    uv.phase_center_dec = 0.0
    uv.phase_center_frame = "icrs"

    # Generate visibilities as flat spectrum of a point source at phase center
    data = (source_flux_jy + 0j) * np.ones((nblts, n_chans, uv.Npols), dtype=np.complex64)
    flags = np.zeros((nblts, n_chans, uv.Npols), dtype=bool)
    nsample = np.ones((nblts, n_chans, uv.Npols), dtype=float)

    uv.data_array = data
    uv.flag_array = flags
    uv.nsample_array = nsample

    # UVW zeros (phase center)
    uv.uvw_array = np.zeros((nblts, 3), dtype=float)

    # Telescope metadata
    uv.telescope_name = "SYNTH"
    uv.telescope_location = np.array([0.0, 0.0, 0.0])

    uv.vis_units = "Jy"
    uv.history = "synthetic"
    uv.object_name = "calibrator"
    uv.polarization_array = np.array([1, 2], dtype=int)  # e.g., XX, YY

    return uv


def write_two_subbands(out_dir,  # type: Union[str, Path]
                       basename="synthetic",
                       **uv_kwargs):
    """Write two minimal UVH5 files to out_dir with sb00/sb01 suffixes.

    Returns paths to the two files.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    uv = _make_minimal_uvdata(**uv_kwargs)

    sb0 = out / f"{basename}_sb00.hdf5"
    sb1 = out / f"{basename}_sb01.hdf5"

    # Split channels between two subbands
    mid = uv.Nfreqs // 2

    uv0 = uv.select(freq_chans=np.arange(0, mid), inplace=False)
    uv1 = uv.select(freq_chans=np.arange(mid, uv.Nfreqs), inplace=False)

    uv0.write_uvh5(str(sb0), clobber=True)
    uv1.write_uvh5(str(sb1), clobber=True)

    return sb0, sb1


