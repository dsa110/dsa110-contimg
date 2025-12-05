# backend/src/dsa110_contimg/conversion/__init__.py

"""
DSA-110 Continuum Imaging Pipeline - Conversion Module.

This module provides functionality for converting UVH5 subband files to
Measurement Sets (MS).

Entry Points:
    Batch conversion:
        from dsa110_contimg.conversion import convert_subband_groups_to_ms

    ABSURD-based ingestion (replaces old streaming pipeline):
        from dsa110_contimg.absurd import setup_ingestion_schedule
        # See docs/guides/ingestion.md for details

Writers:
    DirectSubbandWriter - Main MS writer for production use
"""

from . import helpers_coordinates  # Make coordinate helpers accessible via the package

# Flattened exports - main conversion API
from .hdf5_orchestrator import convert_subband_groups_to_ms

# Writers
from .writers import (
    DirectSubbandWriter,
    MSWriter,
    ParallelSubbandWriter,
    get_writer,
)

__all__ = [
    # Submodules
    "helpers_coordinates",
    # Batch conversion
    "convert_subband_groups_to_ms",
    # Writers
    "MSWriter",
    "DirectSubbandWriter",
    "ParallelSubbandWriter",
    "get_writer",
]
