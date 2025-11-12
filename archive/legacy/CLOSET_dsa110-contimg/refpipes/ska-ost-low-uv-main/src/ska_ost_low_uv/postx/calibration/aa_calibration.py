"""aa_calibartion: ApertureArray calibration submodule."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    from ..aperture_array import ApertureArray

from ..aa_module import AaBaseModule
from . import holography, simple_cal

######################
## AA_CALIBRATOR CLASS
######################


class AaCalibrator(AaBaseModule):
    """ApertureArray Calibration module."""

    def __init__(self, aa: ApertureArray):
        """Setup AaCalibrator.

        Args:
            aa (ApertureArray): Aperture array 'parent' object to use
        """
        self.aa = aa
        self.holography = holography.AaHolographer(aa)
        self.stefcal = simple_cal.AaStefcal(aa)

        self.__setup_docstrings('calibration')

    def __setup_docstrings(self, name):
        self.__name__ = name
        self.name = name
