"""aa_imaging: ApertureArray image tools submodule."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    from ..aperture_array import ApertureArray

import healpy as hp
import numpy as np
import xarray as xr
from astropy.constants import c

from ..aa_module import AaBaseModule
from ..coords.coord_utils import (
    generate_lmn_grid,
    hpix2sky,
    phase_vector,
    sky2hpix,
    skycoord_to_lmn,
)

SPEED_OF_LIGHT = c.value


def generate_weight_grid(aa, n_pix: int, abs_max: int = 1, nan_below_horizon: bool = True):
    """Generate a grid of direction cosine pointing weights.

    Generates a square lmn grid across l=(-abs_max, abs_max), m=(-abs_max, abs_max).

    Notes:
        For unit pointing vector, l^2 + m^2 + n^2 = 1

    Args:
        aa (ApertureArray): Aperture array 'parent' object to use
        n_pix (int): Number of pixels in image
        abs_max (int): Maximum absolute values for l and m (default 1).
        nan_below_horizon (bool): If True, n is NaN below horizon.
                                    If False, n is 0 below horizon


    Notes:
        Generates a 2D array of coefficients (used internally).
    """
    # Generate grid of (l, m, n) coordinates
    lmn = generate_lmn_grid(n_pix, abs_max, nan_below_horizon)

    # Compute Geometric delay t_g
    # lmn shape: (n_pix, n_pix, n_lmn=3)
    # xyz_enu shape: (n_antenna, n_xyz=3)
    # i, j: pix idx
    # d: direction cosine lmn, and baseline XYZ (dot product)
    # a: antenna idx
    t_g = np.einsum('ijd,ad', lmn, aa.xyz_enu, optimize=True) / SPEED_OF_LIGHT

    # Convert geometric delay to phase weight vectors
    # t_g shape: (n_pix, n_pix, n_ant)
    pv_grid = phase_vector(t_g, aa._ws('f').to('Hz').value)
    if aa._in_workspace('c0'):
        pv_grid *= aa._ws('c0')

    # if nan_below_horizon:
    #    # Apply n=sqrt(1 - l2 - m2) factor to account for projection
    #    # See Carozzi and Woan (2009)
    #    pv_grid = np.einsum('ij,aij->aij', 1/lmn[..., 2], pv_grid, optimize=True)

    # Store in workspace
    aa._to_workspace('lmn_grid', lmn)
    aa._to_workspace('pv_grid', pv_grid)
    aa._to_workspace('pv_grid_conj', np.conj(pv_grid))

    return pv_grid, lmn


def instrumental_to_stokes(B: np.ndarray) -> np.ndarray:
    """Convert instrumental polarization to Stokes parameters.

    Args:
        B (np.ndarray): Input array of shape (..., 4) with XX/Re(XY)/Im(XY)/YY polarization components.

    Returns:
        np.ndarray: Output array of shape (..., 4) with Stokes parameters.
    """
    # Convert linear polarization to Stokes parameters
    S = np.zeros_like(B, dtype='float32')
    S[..., 0] = B[..., 0] + B[..., 3]  # I
    S[..., 1] = B[..., 0] - B[..., 3]  # Q
    S[..., 2] = 2 * B[..., 1]  # U
    S[..., 3] = 2 * B[..., 2]  # V
    return S


def make_image(
    aa: ApertureArray,
    n_pix: int = 128,
    update: bool = True,
    vis: str = 'data',
    mode: str = 'linear',
    include_autos: bool = True,
) -> np.array:
    """Make an image out of a beam grid.

    Args:
        aa (ApertureArray): Aperture array 'parent' object to use
        n_pix (int): Image size in pixels (N_pix x N_pix)
        update (bool): Rerun the grid generation (needed when image size changes).
        mode (str): Image mode, either 'linear' or 'stokes'. Defaults to 'linear'.
        vis (str): Select visibilities to be either real data or model visibilities ('data' or 'model').
                   Can also pass a numpy array of visibilities directly.
        include_autos (bool): Include autocorrelations in image.

    Returns:
        B (np.array): Image array in (x_pix, y_pix, pol), where pol is XX/Re(XY)/Im(XY)/YY or Stokes I/Q/U/V.
    """
    if update:
        generate_weight_grid(aa, n_pix)
    w = aa.workspace

    if isinstance(vis, (np.ndarray, xr.DataArray)):
        V = vis
    else:
        V = aa.generate_vis_matrix(vis=vis, include_autos=include_autos)

    # For some reason, breaking into four pols is signifcantly quicker
    # Than adding 'x' as pol axis and using one-liner pij,pqx,qij->ijx
    # fmt: off
    B = np.zeros(shape=(w['pv_grid'].shape[1], w['pv_grid'].shape[2], V.shape[2]), dtype='float32')
    B[..., 0] = np.real(np.einsum('pij,pq,qij->ij', w['pv_grid'], V[..., 0], w['pv_grid_conj'], optimize='greedy'))
    XY = np.einsum('pij,pq,qij->ij', w['pv_grid'], V[..., 1], w['pv_grid_conj'], optimize='greedy')
    B[..., 1] = np.real(XY)
    B[..., 2] = np.imag(XY)
    B[..., 3] = np.real(np.einsum('pij,pq,qij->ij', w['pv_grid'], V[..., 3], w['pv_grid_conj'], optimize='greedy'))
    # fmt: on

    if mode == 'stokes':
        B = instrumental_to_stokes(B)

    return B


def make_healpix(
    aa,
    n_side: int = 128,
    fov: float = np.pi / 2,
    update: bool = True,
    apply_mask: bool = True,
    vis: str = 'data',
    mode: str = 'linear',
    include_autos: bool = True,
    mask_fill_value: float = np.nan,
) -> np.array:
    """Generate a grid of beams on healpix coordinates.

    Args:
        aa (ApertureArray): Aperture array 'parent' object to use
        n_side (int): Healpix NSIDE array size
        fov (float): Field of view in radians, within which to generate healpix beams. Defaults to pi/2.
        apply_mask (bool): Apply mask for pixels that are below the horizon (default True)
        update (bool): Update pre-computed pixel and coordinate data. Defaults to True.
                        Setting to False gives a speedup, but requires that pre-computed coordinates are still accurate.
        vis (str): Select visibilities to be either real data or model visibilities ('data' or 'model')
        mode (str): Image mode, either 'linear' or 'stokes'. Defaults to 'linear'.
        include_autos (bool): Include autocorrelations in image. Default True
        mask_fill_value (float): Masked data fill value, defaults to np.nan

    Returns:
        hpdata (np.array): Array of healpix data, ready for hp.mollview() and other healpy routines.
    """
    # fmt: off
    NSIDE = n_side
    NPIX  = hp.nside2npix(NSIDE)

    ws = aa._ws('hpx')
    if ws.get('n_side', 0) != NSIDE:
        ws['n_side'] = NSIDE
        ws['n_pix']  = NPIX
        ws['pix0']   = np.arange(NPIX)
        ws['sc']     = hpix2sky(NSIDE, ws['pix0'])

    if ws.get('fov', 0) != fov:
        ws['fov'] = fov

    NPIX = ws['n_pix']
    sc   = ws['sc']     # SkyCoord coordinates array
    pix0 = ws['pix0']   # Pixel coordinate array

    if update:
        sc_zen  = aa.coords.get_zenith()
        pix_zen = sky2hpix(NSIDE, sc_zen)
        vec_zen = hp.pix2vec(NSIDE, pix_zen)

        mask = np.ones(shape=NPIX, dtype='bool')

        if apply_mask:
            pix_visible = hp.query_disc(NSIDE, vec=vec_zen, radius=fov)
            mask[pix_visible] = False
        else:
            mask = np.zeros_like(mask)
            pix_visible = pix0

        lmn = skycoord_to_lmn(sc[pix_visible], sc_zen)
        t_g = np.einsum('id,pd', lmn, aa.xyz_enu, optimize=True) / SPEED_OF_LIGHT
        c   = phase_vector(t_g, aa._ws('f').to('Hz').value)

        ws['mask']       = mask
        ws['lmn']        = lmn
        ws['phs_vector'] = c  # Correct for vis phase center (i.e.the Sun)

    mask = ws['mask']  # Horizon mask
    c = ws['phs_vector']  # Pointing phase vector

    V = aa.generate_vis_matrix(vis=vis, include_autos=include_autos)

    # For some reason, breaking into four pols is signifcantly quicker
    # Than adding 'x' as pol axis and using one-liner pij,pqx,qij->ijx
    B = np.zeros(shape=(ws['lmn'].shape[0], 4), dtype='float32')
    B[..., 0] = np.real(np.einsum('ip,pq,iq->i', c, V[..., 0], np.conj(c), optimize=True))
    XY = np.einsum('ip,pq,iq->i', c, V[..., 1], np.conj(c), optimize=True)
    B[..., 1] = np.real(XY)
    B[..., 2] = np.imag(XY)
    B[..., 3] = np.real(np.einsum('ip,pq,iq->i', c, V[..., 3], np.conj(c), optimize=True))

    if mode == 'stokes':
        B = instrumental_to_stokes(B)

    # Create a hpx array with shape (NPIX, 4) and insert above-horizon data
    hpdata = np.zeros((ws['pix0'].shape[0], 4), dtype='float32')
    hpdata[pix0[~mask]] = B

    # Now create a mask for the output healpix map
    hpx_data_mask = np.ones_like(hpdata, dtype='bool')
    hpx_data_mask[pix0[~mask]] = 0

    if apply_mask:
        hpdata = np.ma.array(hpdata)
        hpdata.mask = hpx_data_mask
        hpdata.fill_value = mask_fill_value
    # fmt: on
    return hpdata


####################
## AA_IMAGER CLASS
####################

imager_funcs = {'make_image': make_image, 'make_healpix': make_healpix}


class AaImager(AaBaseModule):
    """ApertureArray Imaging module."""

    def __init__(self, aa: ApertureArray):
        """Setup AaImager.

        Args:
            aa (ApertureArray): Aperture array 'parent' object to use
        """
        self.aa = aa
        self.__setup('imaging')

    def __setup(self, name):
        self.__name__ = name
        self.name = name
        self._attach_funcs(imager_funcs)
