# backend/src/dsa110_contimg/conversion/__init__.py

"""
DSA-110 Continuum Imaging Pipeline - Conversion Module.

This module provides functionality for converting UVH5 subband files to 
Measurement Sets (MS). The main entry points are:

- convert_subband_groups_to_ms: Batch conversion of subband groups
- QueueDB: Streaming queue for real-time data ingest

Usage:
    from dsa110_contimg.conversion import convert_subband_groups_to_ms
    results = convert_subband_groups_to_ms(input_dir, output_dir, start_time, end_time)
    
    # Streaming mode
    from dsa110_contimg.conversion import QueueDB
    queue = QueueDB(db_path)

NOTE: Per complexity reduction guide, all implementation files have been
flattened to this level. The streaming/ and strategies/ submodules remain
for backwards compatibility but import from the flattened files.
"""

from . import helpers_coordinates  # Make coordinate helpers accessible via the package

# Flattened exports - main conversion API (direct import from flattened files)
from .hdf5_orchestrator import convert_subband_groups_to_ms

# Flattened exports - streaming API (direct import from flattened file)
from .streaming_converter import (
    QueueDB,
    parse_subband_info,
    get_mosaic_queue_status,
    check_for_complete_group,
)

# Flattened exports - writers (direct import from flattened files)
from .writers import (
    MSWriter,
    DirectSubbandWriter,
    ParallelSubbandWriter,
    get_writer,
)

__all__ = [
    # Submodules
    "helpers_coordinates",
    # Batch conversion
    "convert_subband_groups_to_ms",
    # Streaming
    "QueueDB",
    "parse_subband_info",
    "get_mosaic_queue_status",
    "check_for_complete_group",
    # Writers
    "MSWriter",
    "DirectSubbandWriter",
    "ParallelSubbandWriter",
    "get_writer",
]
