"""Helper utilities for UVH5 → CASA Measurement Set conversion.

This module provides backward-compatible imports from specialized helper modules.
All functions have been split into logical modules for better organization:
- helpers_antenna.py: Antenna position functions
- helpers_coordinates.py: Coordinate and phase functions
- helpers_model.py: Model and UVW functions
- helpers_validation.py: Validation functions
- helpers_telescope.py: Telescope utility functions
"""

import logging

logger = logging.getLogger("dsa110_contimg.conversion.helpers")

# Import all functions from specialized modules for backward compatibility
from .helpers_antenna import (
    _get_relative_antenna_positions,
    _set_relative_antenna_positions,
    set_antenna_positions,
    _ensure_antenna_diameters,
)
from .helpers_coordinates import (
    get_meridian_coords,
    phase_to_meridian,
    compute_and_set_uvw,
)
from .helpers_model import (
    primary_beam_response,
    amplitude_sky_model,
    set_model_column,
)
from .helpers_validation import (
    validate_ms_frequency_order,
    validate_phase_center_coherence,
    validate_uvw_precision,
    validate_antenna_positions,
    validate_model_data_quality,
    validate_reference_antenna_stability,
)
from .helpers_telescope import (
    cleanup_casa_file_handles,
    set_telescope_identity,
)


__all__ = [
    "get_meridian_coords",
    "set_antenna_positions",
    "_ensure_antenna_diameters",
    "set_model_column",
    "amplitude_sky_model",
    "primary_beam_response",
    "phase_to_meridian",
    "validate_ms_frequency_order",
    "cleanup_casa_file_handles",
    "validate_phase_center_coherence",
    "validate_uvw_precision",
    "validate_antenna_positions",
    "validate_model_data_quality",
    "validate_reference_antenna_stability",
    "set_telescope_identity",
    "compute_and_set_uvw",
]
