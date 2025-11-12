"""aa_satellites: ApertureArray coordinate tools submodule."""

from __future__ import annotations

import typing

from ska_ost_low_uv.postx.coords.satellites import (
    compute_satellite_altaz,
    compute_satellite_radec,
    load_tles,
    satchecker_above_horizon,
    satchecker_get_tle,
    satchecker_lookup_norad,
)

if typing.TYPE_CHECKING:  # pragma: no cover
    from ..aperture_array import ApertureArray

from ..aa_module import AaBaseModule

####################
## AA_SATELLITE CLASS
####################

# Now, create function mapping

sat_funcs = {
    'compute_satellite_altaz': compute_satellite_altaz,
    'compute_satellite_radec': compute_satellite_radec,
    'load_tles': load_tles,
    'satchecker_get_tle': satchecker_get_tle,
    'satchecker_lookup_norad': satchecker_lookup_norad,
    'satchecker_above_horizon': satchecker_above_horizon,
}


class AaSatellites(AaBaseModule):
    """Satellite coordinate utils."""

    def __init__(self, aa: ApertureArray):
        """Setup AaCoords.

        Args:
            aa (ApertureArray): Aperture array 'parent' object to use
        """
        self.aa = aa
        self.__setup('satellites')

    def __setup(self, name):
        self.__name__ = name
        self.name = name
        self._attach_funcs(sat_funcs)
