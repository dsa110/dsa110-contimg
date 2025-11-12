"""gsm_sim.py - Simulate visibilities from global sky model."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    from ska_ost_low_uv.postx import ApertureArray

import healpy as hp
import jax.numpy as jnp
import numpy as np
import xarray as xr
from astropy.constants import c
from pygdsm import init_gsm

from ska_ost_low_uv.postx.aeps import load_aep
from ska_ost_low_uv.postx.coords.coord_utils import (
    hpix2sky,
    phase_vector,
    sky2hpix,
    skycoord_to_lmn,
)

SPEED_OF_LIGHT = c.value


def generate_visibilities_einsum(hpx_sky: np.ndarray, phs_vec: np.ndarray) -> np.ndarray:
    """Generate visibilities from phase vector + Healpix sky.

    Args:
        hpx_sky (np.ndarray): Healpix sky model with shape (Npix, Npol=4), float dtype.
        phs_vec (np.ndarray): Phase vector with shape (Npix, Nant), complex dtype.

    Returns:
        V (np.ndarray): Visibility array with shape (Nant, Npol=4).
    """
    c = phs_vec

    hpx_sky = jnp.array(hpx_sky)

    V = np.zeros(shape=(256, 256, 4), dtype='complex64')
    V[..., 0] = jnp.einsum('ia,i,ib->ab', np.conj(c), hpx_sky[..., 0], c, optimize='greedy')
    V[..., 1] = jnp.einsum('ia,i,ib->ab', np.conj(c), hpx_sky[..., 1], c, optimize='greedy')
    V[..., 2] = jnp.einsum('ia,i,ib->ab', np.conj(c), hpx_sky[..., 2], c, optimize='greedy')
    V[..., 3] = jnp.einsum('ia,i,ib->ab', np.conj(c), hpx_sky[..., 3], c, optimize='greedy')

    return V


def simulate_visibilities_gsm(
    aa: ApertureArray,
    nside: int = 128,
    apply_aep: bool = True,
    sky_model: str = 'gsm08',
    aep: str = 'ska_low',
    mode: str = 'linear',
    as_xarray: bool = True,
):
    """Generate visibilities, based on the Global Sky Model.

    Args:
        aa (ApertureArray): Aperture array object to use. Uses the
                            current freq+time index in aa.idx dict.
        nside (int): Healpix NSIDE parameter for sky.
        apply_aep (bool): Use AEP when generating sky
        aep (str): AEP to use (default 'ska_low')
        sky_model (str): One of gsm08, gsm16, or lfsm.
        mode (str): Coherence mode, one of 'linear' or 'stokes'.
        as_xarray (bool): If true, will return as an xarray object.


    Returns:
        V (np.ndarray): Simulated visibilities
    """
    # fmt: off
    f = aa.f[aa.idx['f']]
    aa.t[aa.idx['t']]

    # Healpix setup
    NPIX  = hp.nside2npix(nside)
    pix0  = np.arange(NPIX)           # Pixel coordinate array
    sc    = hpix2sky(nside, pix0)     # SkyCoord coordinates array

    # Find zenith pixel
    sc_zen  = aa.coords.get_zenith()
    pix_zen = sky2hpix(nside, sc_zen)
    vec_zen = hp.pix2vec(nside, pix_zen)

    # Mask below horizon
    mask = np.ones(shape=NPIX, dtype='bool')
    pix_visible = hp.query_disc(nside, vec=vec_zen, radius=np.pi/2)
    mask[pix_visible] = False

    # Create a grid of sky coordinates
    lmn   = skycoord_to_lmn(sc[pix_visible], sc_zen)
    t_g   = jnp.einsum('id,pd', lmn, aa.xyz_enu, optimize=True) / SPEED_OF_LIGHT
    p_vec = phase_vector(t_g, f.to('Hz').value)

    # Generate a healpix global sky model map
    gsm = init_gsm(sky_model)
    sky = gsm.generate(f.to('MHz').value)
    sky = hp.ud_grade(sky, nside_out=nside)

    sky_visible = jnp.array(sky[pix_visible])

    # Convert sky to a (N_vis, 4) array
    sky_4pol = jnp.broadcast_to(sky_visible, (4, sky_visible.shape[0])).T
    # fmt: on

    if apply_aep:
        aep = load_aep(
            aa.f[0].to('MHz').value,
            nside,
            sky_coord=sc_zen,
            rot_angle=aa.uvx.antennas.array_rotation_angle,
            negate_cross_terms=True,
            aep=aep,
            mode='linear',
            fill_value=0,
        )

        sky_4pol = sky_4pol * jnp.array(aep[pix_visible])
    else:
        # If not using AEP, then
        sky_4pol[..., 1] = 0
        sky_4pol[..., 2] = 0

    V = generate_visibilities_einsum(sky_4pol, p_vec)

    if as_xarray:
        V = np.expand_dims(V, axis=(0, 1))
        V = xr.DataArray(V, dims=('time', 'frequency', 'ant1', 'ant2', 'polarization'))
        return V
    else:
        return V
