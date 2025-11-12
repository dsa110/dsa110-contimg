"""aa_simulation: ApertureArray simulation tools submodule."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    from ..aperture_array import ApertureArray

from ..aa_module import AaBaseModule
from .aa_model import Model
from .beam_sim import plot_beam_cuts, plot_beam_orthview, simulate_beam
from .gsm_sim import simulate_visibilities_gsm
from .simple_sim import simulate_visibilities_pointsrc

func_dict = {
    'sim_station_beam': simulate_beam,
    'orthview_station_beam': plot_beam_orthview,
    'plot_station_beam_cuts': plot_beam_cuts,
}

func_dict_update = {
    'sim_vis_pointsrc': (simulate_visibilities_pointsrc, 'model.visibilities'),
    'sim_vis_gsm': (simulate_visibilities_gsm, 'model.visibilities'),
}


class AaSimulator(AaBaseModule):
    """Simulate visibilities, pygdsm diffuse sky model, and station beam simulation."""

    def __init__(self, aa: ApertureArray):
        """Setup AaSimulator.

        Args:
            aa (ApertureArray): Aperture array 'parent' object to use
        """
        self.aa = aa
        self.model = Model(
            visibilities=None,
            point_source_skymodel=None,
            beam=None,
            gains=None,
            gsm=None,
        )

        self.__setup('simulation')

    def __setup(self, name):
        self.__name__ = name
        self.name = name
        self._attach_funcs(func_dict)
        self._attach_funcs_update(func_dict_update)

    def orthview_gsm(self, *args, **kwargs):
        """View diffuse sky model (Orthographic)."""
        if self.model.gsm.observed_sky is None:
            self.model.gsm.generate()
        self.model.gsm.view(*args, **kwargs)

    def mollview_gsm(self, *args, **kwargs):
        """View diffuse sky model (Mollweide)."""
        if self.model.gsm.observed_sky is None:
            self.model.gsm.generate()
        self.model.gsm.view_observed_gsm(*args, **kwargs)
