# core/telescope/__init__.py
"""
DSA-110 telescope specific modules.

This package contains telescope-specific constants, utilities,
and beam models for the DSA-110 array.
"""

from .dsa110 import (
    get_valid_antennas, get_valid_antenna_names, is_valid_antenna,
    get_telescope_location, get_dish_diameter,
    ant_inds_to_names_dsa110, ant_names_to_inds_dsa110
)
from .beam_models import (
    pb_dsa110, pb_dsa110_airy, get_beam_model,
    calculate_beam_fwhm, calculate_beam_hpbw
)

__all__ = [
    'get_valid_antennas', 'get_valid_antenna_names', 'is_valid_antenna',
    'get_telescope_location', 'get_dish_diameter',
    'ant_inds_to_names_dsa110', 'ant_names_to_inds_dsa110',
    'pb_dsa110', 'pb_dsa110_airy', 'get_beam_model',
    'calculate_beam_fwhm', 'calculate_beam_hpbw'
]
