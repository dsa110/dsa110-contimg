# This file initializes the strategies module.
"""Conversion strategies for DSA-110 Continuum Imaging Pipeline.

NOTE: This module exists for backwards compatibility. All implementation
files have been flattened to the conversion/ level per the complexity
reduction guide. Import directly from conversion/ for new code.
"""

# Import from flattened location (modules moved up to conversion/)
from dsa110_contimg.conversion.hdf5_orchestrator import (
    convert_subband_groups_to_ms,
)
from dsa110_contimg.conversion.writers import (
    MSWriter,
    DirectSubbandWriter,
    ParallelSubbandWriter,  # Alias for DirectSubbandWriter
    get_writer,
)

__all__ = [
    # Orchestrator
    "convert_subband_groups_to_ms",
    # Writers
    "MSWriter",
    "DirectSubbandWriter",
    "ParallelSubbandWriter",
    "get_writer",
]