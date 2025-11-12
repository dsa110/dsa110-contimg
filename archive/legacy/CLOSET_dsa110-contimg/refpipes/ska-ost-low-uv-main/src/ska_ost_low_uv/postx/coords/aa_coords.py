"""aa_coords: ApertureArray coordinate tools submodule."""

from __future__ import annotations

import typing

import numpy as np
from astropy.coordinates import AltAz, Angle, SkyCoord
from astropy.coordinates import get_sun as astropy_get_sun

from ska_ost_low_uv.postx.coords.coord_utils import phase_vector, skycoord_to_lmn
from ska_ost_low_uv.postx.imaging.aa_imaging import SPEED_OF_LIGHT

if typing.TYPE_CHECKING:  # pragma: no cover
    from ..aperture_array import ApertureArray

from ..aa_module import AaBaseModule
from .aa_satellites import AaSatellites


def generate_phase_vector(aa, src: SkyCoord, conj: bool = False, coplanar: bool = False):
    """Generate a phase vector for a given source.

    Args:
        aa (ApertureArray): Aperture array 'parent' object to use
        src (astropy.SkyCoord or ephem.FixedBody): Source to compute delays toward
        conj (bool): Conjugate data if True
        coplanar (bool): Treat array as coplanar if True. Sets antenna z-pos to zero

    Returns:
        c (np.array): Per-antenna phase weights
    """
    lmn = skycoord_to_lmn(src, aa.coords.get_zenith())
    ant_pos = aa.xyz_enu
    if coplanar:
        ant_pos[..., 2] = 0

    t_g = np.einsum('id,pd', lmn, aa.xyz_enu, optimize=True) / SPEED_OF_LIGHT
    c = phase_vector(t_g, aa._ws('f').to('Hz').value, conj=conj, dtype='complex64')
    return c


def get_zenith(aa) -> SkyCoord:
    """Return the sky coordinates at zenith.

    Args:
        aa (ApertureArray): Aperture array objecy to use

    Returns:
        zenith (SkyCoord): Zenith SkyCoord object
    """
    zen_aa = AltAz(
        alt=Angle(90, unit='degree'),
        az=Angle(0, unit='degree'),
        obstime=aa._ws('t'),
        location=aa.earthloc,
    )
    zen_sc = SkyCoord(zen_aa).icrs
    return zen_sc


def get_alt_az(aa, sc: SkyCoord) -> SkyCoord:
    """Convert SkyCoord into alt/az coordinates.

    Args:
        aa (ApertureArray): Aperture array object to use
        sc (SkyCoord): Input sky coordinate

    Returns:
        sc_altaz (SkyCoord): Same coordinates, in alt/az frame.
    """
    sc.obstime = aa._ws('t')
    sc.location = aa.earthloc
    return sc.altaz


def get_sun(aa) -> SkyCoord:
    """Return the sky coordinates of the Sun.

    Args:
        aa (ApertureArray): Aperture array object to use

    Returns:
        sun_sc (SkyCoord): sun SkyCoord object
    """
    sun_sc = SkyCoord(astropy_get_sun(aa._ws('t')), location=aa.earthloc)
    return sun_sc


####################
## AA_COORDS CLASS
####################

coord_funcs = {
    'generate_phase_vector': generate_phase_vector,
    'get_sun': get_sun,
    'get_zenith': get_zenith,
    'get_alt_az': get_alt_az,
}


class AaCoords(AaBaseModule):
    """Coordinate utils."""

    def __init__(self, aa: ApertureArray):
        """Setup AaCoords.

        Args:
            aa (ApertureArray): Aperture array 'parent' object to use
        """
        self.aa = aa
        self.__setup('coords')
        self.satellites = AaSatellites(self.aa)

    def __setup(self, name):
        self.__name__ = name
        self.name = name
        self._attach_funcs(coord_funcs)
