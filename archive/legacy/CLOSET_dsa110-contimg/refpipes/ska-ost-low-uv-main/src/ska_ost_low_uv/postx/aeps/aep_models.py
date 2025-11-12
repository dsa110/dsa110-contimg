"""AEP (Antenna Element Pattern) models and loading utilities.

This module provides functions to load and manipulate AEP data from HDF5 files,
including spherical harmonic representations and beam pattern generation.
"""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    pass

import h5py
import healpy as hp
import numpy as np
import numpy.typing as npt
from astropy.coordinates import Angle, SkyCoord

# from pyuvdata import UVBeam
from pyuvdata.analytic_beam import UnpolarizedAnalyticBeam

from ska_ost_low_uv.postx.coords.coord_utils import generate_lmn_grid, lmn_to_altaz
from ska_ost_low_uv.postx.imaging import instrumental_to_stokes
from ska_ost_low_uv.utils import get_resource_path


class SimpleCosSqBeam(UnpolarizedAnalyticBeam):
    """A zenith pointed cos-squared beam."""

    def _power_eval(
        self,
        *,
        az_grid: npt.NDArray[float],  # type: ignore
        za_grid: npt.NDArray[float],  # type: ignore
        f_grid: npt.NDArray[float],  # type: ignore
    ) -> npt.NDArray[float]:  # type: ignore
        """Evaluate the power at the given coordinates."""
        data_array = self._get_empty_data_array(az_grid.shape, beam_type='power')
        for pol_i in np.arange(self.Npols):
            data_array[0, pol_i, :, :] = np.cos(za_grid) ** 2
        return data_array


def create_station_rotator(rot_angle: float | Angle):
    """Create a hp.rotator.Rotator to apply station rotation.

    Notes:
        Station rotation is defined as a clockwise rotation angle in degrees away from N-E.
        Healpy uses right-hand rule rotations. A positive rotation about the X-axis will tilt
        the north pole toward -y.

    Args:
        rot_angle (float): Rotation angle in degrees.

    Returns:
        r0r (hp.rotator.Rotator): The healpy rotator, with r0r.rotate_map_alms() to use.
    """
    # Station rotation
    # A positive angle moves toward –y
    if isinstance(rot_angle, Angle):
        xx = rot_angle.to('deg').value + 90
    else:
        xx = rot_angle + 90

    # First rotation: station rotation
    r0r = hp.rotator.Rotator(rot=[xx, 0, 0], coord=None, eulertype='X')

    return r0r


def load_aep_coeffs(
    freq: float,
    aep: str = 'ska_low',
) -> dict[np.ndarray]:
    """Load AEP from HDF5 file to a healpix map.

    Generates a beam map using spherical harmonics, centred on sky_coord

    Args:
        freq (float): Frequency in MHz.
        aep (str): AEP to load (currently only 'ska_low' supported)

    Returns:
        aep_coeffs (dict): Dictionary with keys xx, yy, re_xy, im_xy.
                           Each entry is a 1D numpy array of SHC coefficients
                           that can be loaded with hp.sphtfunc.alm2map()
    """
    fn = get_resource_path(f'postx/data/aeps/{aep}.h5')

    with h5py.File(fn, 'r') as h5:
        lmax = h5['xx'].attrs['lmax']
        f0 = h5['xx'].attrs['start_frequency']
        idx = int(freq - f0)

        aep_dict = {
            'xx': h5['xx'][idx].astype('complex128'),
            'yy': h5['yy'][idx].astype('complex128'),
            're_xy': h5['re_xy'][idx].astype('complex128'),
            'im_xy': h5['im_xy'][idx].astype('complex128'),
            'lmax': lmax,
            'f0': f0,
        }

    return aep_dict


def load_aep(
    freq: float,
    nside: int = 128,
    sky_coord: SkyCoord = None,
    rot_angle: Angle | float = 0,
    fill_value: float = 0,
    mode: str = 'linear',
    aep: str = 'ska_low',
    negate_cross_terms: bool = True,
    rotate_to_astro: bool = True,
) -> np.ndarray:
    """Load AEP from HDF5 file to a healpix map.

    Generates a beam map using spherical harmonics, centred on sky_coord

    Args:
        freq (float): Frequency in MHz.
        nside (int): HEALPix nside parameter.
        aep (str): AEP to load (currently only 'ska_low' supported)
        nside (int): Healpix NSIDE resolution parameter.
        sky_coord (SkyCoord): Celestial coordinates for AEP centroid.
                              If not given, assume zenith at (l=0, b=0)
                              (Middle of orthview / mollview)
        rot_angle (float): Station rotation angle in degrees,
                           clockwise rotation away from N-E.
        fill_value (float): Value to use for filling masked pixels.
                            Defaults to 0, also consider np.nan or 1e+20
        mode (str): Either 'linear' (XX, re(XY), im(XY), YY)
                    or 'stokes' (I, Q, U, V). Defaults to 'linear'.
        rotate_to_astro (bool): If true, rotate (theta, phi) to (alt, az)
        negate_cross_terms (bool): If true, the cross terms will be negated
                                   (i.e. Re(XY) and Im(XY) or Q, U).

    Returns:
        hpx_map (np.ndarray): Numpy array with shape (Npix, Npol=4), where
                              the Npol index is (xx, re_xy, im_xy, yy)
    """
    coeffs = load_aep_coeffs(freq, aep)

    map_dict = {}

    aep_comps = ('xx', 'yy', 're_xy', 'im_xy')
    for k in aep_comps:
        map_dict[k] = np.real(hp.sphtfunc.alm2map(coeffs[k], nside=nside, lmax=coeffs['lmax']))

    # Rotate to sky_coord using Euler angles (ZYX)
    # To convert (theta, phi) antenna coords to (alt, az) astro coords:
    #     az = 90 - phi
    # To convert to Galactic coords (l, b) also requires 90 degree shift:
    #     b = 90 - phi
    if sky_coord is not None:
        ll = sky_coord.galactic.l.to('deg').value
        bb = sky_coord.galactic.b.to('deg').value
        ra = sky_coord.icrs.ra.to('deg').value
        dec = sky_coord.icrs.dec.to('deg').value
    else:
        ll = 0
        bb = 0

    # First: create station rotator and apply to map
    r0r = create_station_rotator(rot_angle)
    for k in aep_comps:
        map_dict[k] = r0r.rotate_map_alms(map_dict[k])

    # Next rotation: from 0->90 lat
    if rotate_to_astro:
        r0 = hp.rotator.Rotator(rot=[0, 90, 0], coord=None, eulertype='Y')
        for k in aep_comps:
            map_dict[k] = r0.rotate_map_alms(map_dict[k])

    # Third rotation - to sky coordinate (RA / DEC)
    if sky_coord is not None:
        r1 = hp.Rotator(rot=[ra, dec], coord=['G', 'C'], inv=True)
        for k in aep_comps:
            map_dict[k] = r1.rotate_map_alms(map_dict[k])
    else:
        ra = 0
        dec = 0

    # Set any negative values in xx/yy to zero
    xx = map_dict['xx']
    xx[xx < 0] = 0
    yy = map_dict['yy']
    yy[yy < 0] = 0

    # Now convert into single healpix array with all four pol products
    hpx = np.zeros((map_dict['xx'].shape[0], 4), dtype='float32')
    hpx[..., 0] = xx
    hpx[..., 1] = map_dict['re_xy']
    hpx[..., 2] = map_dict['im_xy']
    hpx[..., 3] = yy

    if negate_cross_terms:
        hpx[..., 1] *= -1
        hpx[..., 2] *= -1

    # Create a masked array so we can mask below horizon
    mask = np.ones(shape=hpx.shape[0], dtype='bool')

    # Now create below horizon mask
    # ang2vec takes longitude and latitude in degrees when lonlat=True
    vec = hp.ang2vec(ll, bb, lonlat=True)
    ipix = hp.query_disc(nside=nside, vec=vec, radius=0.99 * np.pi / 2)  # Mask very edge pixels
    mask[ipix] = 0

    hpx = np.ma.array(hpx)
    hpx.mask = np.zeros_like(hpx, dtype='bool')
    for ii in range(4):
        hpx.mask[..., ii] = mask
    hpx.fill_value = fill_value

    if mode == 'stokes':
        hpx = instrumental_to_stokes(hpx)

    return hpx


def load_aep_orth(
    freq: float,
    npix: int = 128,
    fill_value: float = 0,
    mode: str = 'linear',
    aep: str = 'ska_low',
    rot_angle: Angle | float = 0,
) -> np.ndarray:
    """Load AEP from HDF5 file to a 2D orthographic image.

    Args:
        freq (float): Frequency in MHz.
        npix (int): Image size (npix * npix).
        aep (str): AEP to load (currently only 'ska_low' supported)
        fill_value (float): Value to use for filling masked pixels.
                            Defaults to 0, also consider np.nan or 1e+20
        mode (str): Either 'linear' (XX, re(XY), im(XY), YY)
                    or 'stokes' (I, Q, U, V). Defaults to 'linear'.
        rot_angle (float): Station rotation angle to apply. Default 0.

    Returns:
        hpx_map (np.ndarray): Numpy array with shape (Npix, Npol=4), where
                              the Npol index is (xx, re_xy, im_xy, yy)
    """
    _NSIDE = 128
    # Create empty image, compute direction cosines
    img = np.zeros((npix, npix, 4), dtype='float32')
    lmn = generate_lmn_grid(npix)

    hpx = load_aep(freq, _NSIDE, rotate_to_astro=False, rot_angle=rot_angle, mode='linear', aep=aep)

    # Generate healpix pixel indexes for each direction cosine
    # Remove NaN, flatten, rotate az by 90 degrees
    alt, az = lmn_to_altaz(*lmn.T)
    sel = ~np.isnan(alt)
    phi = az[sel] + np.pi / 2  # Longitude
    theta = np.pi / 2 - alt[sel]  # Colatitude
    pix_idx = hp.ang2pix(_NSIDE, theta=theta, phi=phi, lonlat=False)

    # Grab corresponding pixels to create orthographic image
    # Equivalent to nearest neighbour interpolation
    for ii in range(4):
        _img = np.zeros((npix, npix), dtype='float32')
        _hpx = hpx[..., ii]
        _img[sel] = _hpx[pix_idx]
        _img[~sel] = fill_value
        img[..., ii] = _img

    if mode == 'stokes':
        img = instrumental_to_stokes(img)

    return img


"""def load_aep_uvbeam(aa: ApertureArray, aep: str = 'ska_low', nside: int = 128):
    Load AEP data into pyuvdata UVBeam.

    Args:
        aa (ApertureArray): Parent aperture array object.
        aep (str): AEP to load. Defaults to 'ska_low'.
        nside (int): Healpix NSIDE parameter to use when generating AEP.
    nside = 128
    map_dict = {}

    aep_coeffs = load_aep_coeffs(aa.f[0].to('MHz').value, aep=aep)
    aep_comps = ('xx', 'yy', 're_xy', 'im_xy')
    for k in aep_comps:
        map_dict[k] = np.real(hp.sphtfunc.alm2map(aep_coeffs[k], nside=nside, lmax=aep_coeffs['lmax']))

    d = np.zeros((1, 4, 1, hp.nside2npix(nside)), dtype='complex64')
    d[0, 0, 0] = map_dict['xx']
    d[0, 1, 0] = map_dict['yy']
    d[0, 2, 0] = map_dict['re_xy'] + 1j * map_dict['im_xy']
    d[0, 3, 0] = map_dict['im_xy'] - 1j * map_dict['im_xy']

    np.deg2rad(aa.uvx.antennas.array_rotation_angle.values)

    uvb = UVBeam.new(
        telescope_name=aa.name,
        data_normalization='physical',
        data_array=d,
        freq_array=aa.f.to('MHz').value,
        x_orientation='east',
        # feed_angle = feed_angle,
        # mount_type = "fixed",
        beam_type='power',
        pixel_coordinate_system='healpix',
        polarization_array=[-5, -6, -7, -8],
        nside=nside,
        ordering='ring',
    )
    return uvb"""
