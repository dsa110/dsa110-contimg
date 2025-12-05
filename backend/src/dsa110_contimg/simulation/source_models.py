"""Source modeling helpers for the simulation toolkit."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from dsa110_contimg.simulation.source_selection import SyntheticSource

SPEED_OF_LIGHT = 299_792_458.0  # m/s


def evaluate_flux_density(source: SyntheticSource, freq_hz: np.ndarray) -> np.ndarray:
    """Evaluate the flux density of a source at the requested frequencies."""

    flux = np.full_like(freq_hz, source.flux_ref_jy, dtype=float)

    if source.reference_freq_hz and source.spectral_index is not None:
        # Avoid divide-by-zero if reference frequency is malformed
        if source.reference_freq_hz > 0:
            scale = freq_hz / source.reference_freq_hz
            flux = source.flux_ref_jy * np.power(scale, source.spectral_index)

    return flux


def direction_cosines(
    ra_deg: float,
    dec_deg: float,
    phase_center_ra_deg: float,
    phase_center_dec_deg: float,
) -> tuple[float, float, float]:
    """Compute (l, m, n) direction cosines relative to phase center."""

    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)
    ra0 = math.radians(phase_center_ra_deg)
    dec0 = math.radians(phase_center_dec_deg)

    delta_ra = ra - ra0

    dir_l = math.cos(dec) * math.sin(delta_ra)
    m = math.sin(dec) * math.cos(dec0) - math.cos(dec) * math.cos(delta_ra) * math.sin(dec0)

    # Guard numerical errors inside sqrt
    n_sq = max(0.0, 1.0 - dir_l**2 - m**2)
    n = math.sqrt(n_sq)

    return dir_l, m, n


def multi_source_visibility(
    sources: Sequence[SyntheticSource],
    uvw_m: np.ndarray,
    freq_hz: np.ndarray,
    phase_center_ra_deg: float,
    phase_center_dec_deg: float,
    npols: int,
) -> np.ndarray:
    """Generate visibilities for multiple point sources."""

    if uvw_m.ndim != 2 or uvw_m.shape[1] != 3:
        raise ValueError("uvw_m must have shape (Nblts, 3)")

    nblts = uvw_m.shape[0]
    nfreqs = freq_hz.size
    nspws = 1

    # Pre-compute wavelength-dependent UVW arrays
    wavelengths = SPEED_OF_LIGHT / freq_hz  # shape (nfreqs,)
    u_lambda = uvw_m[:, 0][:, None] / wavelengths[None, :]
    v_lambda = uvw_m[:, 1][:, None] / wavelengths[None, :]
    w_lambda = uvw_m[:, 2][:, None] / wavelengths[None, :]

    vis = np.zeros((nblts, nspws, nfreqs, npols), dtype=np.complex64)

    for source in sources:
        flux_per_freq = evaluate_flux_density(source, freq_hz)
        l, m, n_dir = direction_cosines(
            source.ra_deg, source.dec_deg, phase_center_ra_deg, phase_center_dec_deg
        )
        phase_arg = u_lambda * l + v_lambda * m + w_lambda * (n_dir - 1.0)
        phase = np.exp(-2j * np.pi * phase_arg)
        contribution = flux_per_freq[None, :] * phase

        # Split unpolarized flux equally across correlator polarizations
        for pol in range(npols):
            vis[:, 0, :, pol] += (contribution / 2.0).astype(np.complex64)

    return vis
