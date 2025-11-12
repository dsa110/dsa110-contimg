"""sky_model: Simple sky model class and tools."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    from .aperture_array import ApertureArray
import numpy as np
from astropy.coordinates import SkyCoord, get_body, get_sun


class RadioSource(SkyCoord):
    """A SkyCoordinate with a magnitude."""

    def __init__(self, *args, mag: float = 1.0, unit: str = None, **kwargs):
        """Create a RadioSource (A SkyCoord with magnitude).

        Args:
            mag (float): Magnitude to attach, default 1.0
            unit (str): Unit for astropy SkyCoord defaults to
                        ('hourangle', 'degree')
            *args: Arguments to pass to SkyCoord
            **kwargs (dict): Keyword args to pass to SkyCoord
        """
        if unit is None:
            unit = ('hourangle', 'degree')
        super().__init__(*args, unit=unit, **kwargs)
        self.mag = mag


def generate_skycat(observer: ApertureArray):
    """Generate a SkyModel for a given observer with major radio sources.

    Args:
        observer (AntArray / ephem.Observer): Observatory instance

    Returns:
        skycat (SkyModel): A sky catalog with the A-team sources
    """
    # fmt: off
    skycat = {
        'Virgo_A':     RadioSource('12h 30m 49s',    '+12:23:28',    ),
        'Hydra_A':     RadioSource('09h 18m 5.6s',   '-12:5:44.0',   ),
        'Centaurus_A': RadioSource('13h 25m 27.6s',  '−43:01:09',    ),
        'Cygnus_A':    RadioSource('19h 59m 28.4s',  '+40:44:02.10', ),
        'Cas_A':       RadioSource('23h 23m 24.0s',  '+58 48 54.00', ),
        'Pictor_A':    RadioSource('05h 19m 49.72s', '−45:46:43.85', ),
        'Hercules_A':  RadioSource('16h 51m 08.15',  '+04:59:33.32', ),
        'Fornax_A':    RadioSource('03h 22m 41.7',   '−37:12:30',    ),
        'Vela':        RadioSource('08h 35m 20.66',  '-45:10:35.2',  ),
        'Taurus_A':    RadioSource('05h 34m 30.9',   '+22:00:53',    ),
        '3C_444':      RadioSource('22h 14m 25.752', '-17:01:36.29'  ),
        'GC':          RadioSource('17h 45m 40.04',  '-29:00:28.1',  ),
        'LMC':         RadioSource('05h 23m 34.6s',  '-69:45:22',    ),
        'SMC':         RadioSource('00h 52m 38.0s',  '-72:48:01',    ),
    }
    # fmt: on
    skycat.update(generate_skycat_solarsys(observer))
    return skycat


def generate_skycat_solarsys(observer: ApertureArray):
    """Generate Sun + Moon for observer."""
    # fmt: off
    sun_gcrs     = get_body('sun', observer._ws('t'))
    moon_gcrs    = get_body('moon', observer._ws('t'))
    jupiter_gcrs = get_body('jupiter', observer._ws('t'))

    skycat = {
        'Sun':     RadioSource(sun_gcrs.ra, sun_gcrs.dec, mag=1.0),
        'Moon':    RadioSource(moon_gcrs.ra, moon_gcrs.dec, mag=1.0),
        'Jupiter': RadioSource(jupiter_gcrs.ra, jupiter_gcrs.dec, mag=1.0),
    }
    # fmt: on
    return skycat


def sun_model(aa: ApertureArray, t_idx: int = 0, scaling: str = 'hi') -> np.array:
    """Generate sun flux model at given frequencies.

    Flux model values taken from Table 2 of Macario et al (2022).
    A 5th order polynomial is used to interpolate between frequencies.

    Args:
        aa (RadioArray): RadioArray to use for ephemeris / freq setup
        t_idx (int): timestep to use
        scaling (str): Scaling for flux density, depends on solar cycle.
                       Can select 'hi' (near solar max), or 'lo'.
                       'hi' returns values ~1.7x higher.

    Returns:
        S (RadioSource): Model flux, in Jy

    Citation:
        Characterization of the SKA1-Low prototype station Aperture Array Verification System 2
        Macario et al (2022)
        JATIS, 8, 011014. doi:10.1117/1.JATIS.8.1.011014
        https://ui.adsabs.harvard.edu/abs/2022JATIS...8a1014M/abstract

        Table is based on measurements in Benz (2009)
        Radio emission of the quiet sun: Datasheet
        https://doi.org/10.1007/978-3-540-88055-4

        Hamini et al (2022) suggests scaling for local maximum
        by factor of 3.29 / 1.94 = 1.69587629x  (based on eqns 2, 4)
        https://doi.org/10.1051/swsc/2021039
    """
    f_i = (50, 100, 150, 200, 300)  # Frequency in MHz
    α_i = (2.15, 1.86, 1.61, 1.50, 1.31)  # Spectral index  # noqa: F841
    S_i = np.array((5400, 24000, 5100, 81000, 149000))  # Flux in Jy

    if scaling == 'hi':
        S_i = 1.69587629 * S_i
    p_S = np.poly1d(np.polyfit(f_i, S_i, 2))

    sun = RadioSource(get_sun(aa._ws('t')), mag=p_S(aa._ws('f').to('MHz').value))

    return sun
