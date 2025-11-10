#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a small synthetic UVH5 calibrator dataset suitable for conversion and calibration tests.

This script creates a minimally valid UVH5 file using pyuvdata for a simple
point-source calibrator located at the phase center. Visibilities are set to a
constant complex amplitude equal to the source flux (Jy), producing high-SNR
data that exercises the conversion and calibration pipeline deterministically.

Notes:
- Antenna layout: a small 1D line array on the x-axis (10 m spacing)
- Times: a short sequence of integrations (default 4) over 60 seconds
- Frequencies: 64 channels centered at 1.4 GHz (1 MHz channel width)
- Polarizations: XX and YY (2 correlations)

Usage:
  python tests/utils/generate_uvh5_calibrator.py \
    --output /tmp/synth_cal.uvh5 \
    --n-ants 16 --n-times 4 --n-chans 64 \
    --ra-deg 202.7845 --dec-deg 30.5089 --flux-jy 5.0
"""

import argparse
import numpy as np
from pyuvdata import UVData


def generate_uvh5(
    output_path: str,
    *,
    n_ants: int = 16,
    n_times: int = 4,
    start_jd: float = 2460000.0,
    int_time_s: float = 15.0,
    n_chans: int = 64,
    f0_hz: float = 1.4e9,
    chan_bw_hz: float = 1.0e6,
    ra_deg: float = 202.7845,
    dec_deg: float = 30.5089,
    flux_jy: float = 5.0,
) -> None:
    uvd = UVData()

    # Antenna metadata
    antenna_numbers = np.arange(n_ants, dtype=int)
    antenna_names = np.array([f"ant{a}" for a in antenna_numbers])
    # Simple linear array along x-axis (10 m spacing)
    ant_pos = np.zeros((n_ants, 3), dtype=float)
    ant_pos[:, 0] = np.arange(n_ants, dtype=float) * 10.0

    # Time/frequency metadata
    times = start_jd + np.arange(n_times, dtype=float) * (int_time_s / 86400.0)
    freqs = f0_hz + (np.arange(n_chans) - n_chans // 2) * chan_bw_hz

    # Build baseline-time order (ant1 < ant2 for cross-corr; exclude autocorr)
    ant_pairs = [(i, j) for i in range(n_ants) for j in range(i + 1, n_ants)]
    n_bls = len(ant_pairs)
    npols = 2  # XX, YY
    nspw = 1

    # Shape definitions
    nblts = n_bls * n_times
    data_array = np.zeros((nblts, nspw, n_chans, npols), dtype=np.complex64)
    flag_array = np.zeros((nblts, nspw, n_chans, npols), dtype=bool)
    nsample_array = np.ones((nblts, nspw, n_chans, npols), dtype=float)
    uvw_array = np.zeros((nblts, 3), dtype=float)
    ant1_array = np.zeros(nblts, dtype=int)
    ant2_array = np.zeros(nblts, dtype=int)
    time_array = np.zeros(nblts, dtype=float)
    # Fill constant complex vis for point source at phase center
    data_array[...] = complex(flux_jy, 0.0)

    # Pack baselines by time
    idx = 0
    for t in times:
        for a1, a2 in ant_pairs:
            ant1_array[idx] = a1
            ant2_array[idx] = a2
            time_array[idx] = t
            # uvw ~ 0 for phase-center model; leave zeros
            idx += 1

    # Populate UVData core fields (set arrays first, properties are computed)
    uvd.antenna_numbers = antenna_numbers
    uvd.antenna_names = antenna_names
    uvd.antenna_positions = ant_pos

    uvd.ant_1_array = ant1_array
    uvd.ant_2_array = ant2_array
    uvd.uvw_array = uvw_array
    uvd.time_array = time_array

    # Frequencies and channel width
    uvd.freq_array = freqs[None, :]
    uvd.channel_width = float(chan_bw_hz)
    uvd.spw_array = np.array([0], dtype=int)

    # Set simple LSTs (monotonic but arbitrary)
    lst0 = 0.0
    uvd.lst_array = (lst0 + (time_array - time_array.min()) * 2 * np.pi) % (2 * np.pi)

    # Data arrays
    uvd.data_array = data_array
    uvd.flag_array = flag_array
    uvd.nsample_array = nsample_array

    # Polarization: XX, YY
    uvd.polarization_array = np.array([-5, -7], dtype=int)

    # Telescope and phase center metadata
    uvd.telescope_name = "DSA_110_SYNTH"
    # ECEF coordinates approx. (OVRO-like); not critical for this synthetic dataset
    uvd.telescope_location = np.array(
        [-2514818.0, -3959582.0, 4389076.0], dtype=float
    )  # OVRO ITRF
    uvd.telescope_location_lat_lon_alt = (
        0.650,
        -2.064,
        1222.0,
    )  # OVRO approx (rad, rad, m)
    uvd.phase_type = "phased"
    uvd.object_name = "SYNTH_CAL"
    uvd.vis_units = "Jy"

    # Minimal extra keywords
    uvd.extra_keywords = {
        "phase_center_ra_deg": float(ra_deg),
        "phase_center_dec_deg": float(dec_deg),
        "source_flux_jy": float(flux_jy),
    }

    # Integration time per visibility
    uvd.integration_time = np.full(nblts, float(int_time_s), dtype=float)

    # Set phase center (ICRS coordinates)
    import astropy.units as u
    from astropy.coordinates import SkyCoord

    coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
    uvd.phase_center_ra = coord.ra.rad
    uvd.phase_center_dec = coord.dec.rad
    uvd.phase_center_frame = "icrs"
    uvd.phase_center_epoch = 2000.0
    uvd.phase_center_id_array = np.zeros(nblts, dtype=int)

    # Basic checks and write
    uvd.history = "Synthetic calibrator UVH5 for DSA-110 pipeline testing"
    uvd.write_uvh5(output_path, clobber=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate synthetic calibrator UVH5 dataset"
    )
    ap.add_argument("--output", required=True, help="Output .uvh5 path")
    ap.add_argument("--n-ants", type=int, default=16)
    ap.add_argument("--n-times", type=int, default=4)
    ap.add_argument("--n-chans", type=int, default=64)
    ap.add_argument("--start-jd", type=float, default=2460000.0)
    ap.add_argument("--int-time", type=float, default=15.0, help="Integration time (s)")
    ap.add_argument("--f0-hz", type=float, default=1.4e9)
    ap.add_argument("--chan-bw-hz", type=float, default=1.0e6)
    ap.add_argument("--ra-deg", type=float, default=202.7845)
    ap.add_argument("--dec-deg", type=float, default=30.5089)
    ap.add_argument("--flux-jy", type=float, default=5.0)
    args = ap.parse_args()

    generate_uvh5(
        args.output,
        n_ants=args.n_ants,
        n_times=args.n_times,
        start_jd=args.start_jd,
        int_time_s=args.int_time,
        n_chans=args.n_chans,
        f0_hz=args.f0_hz,
        chan_bw_hz=args.chan_bw_hz,
        ra_deg=args.ra_deg,
        dec_deg=args.dec_deg,
        flux_jy=args.flux_jy,
    )
    print(f"✓ Wrote synthetic UVH5: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
