# backend/src/dsa110_contimg/conversion/__init__.py

"""
DSA-110 Continuum Imaging Pipeline - Conversion Module.

This module provides functionality for converting UVH5 subband files to 
Measurement Sets (MS). 

Entry Points:
    Batch conversion:
        from dsa110_contimg.conversion import convert_subband_groups_to_ms
    
    Streaming pipeline (NEW - preferred):
        from dsa110_contimg.conversion.streaming import SubbandQueue, StreamingWorker
        # CLI: dsa110-stream --input-dir /data/incoming --output-dir /data/output
    
    Legacy streaming (DEPRECATED):
        from dsa110_contimg.conversion import QueueDB

Database:
    Both streaming APIs use the `processing_queue` table (see database/schema.sql).
"""

from . import helpers_coordinates  # Make coordinate helpers accessible via the package

# Flattened exports - main conversion API
from .hdf5_orchestrator import convert_subband_groups_to_ms

# Legacy streaming API (DEPRECATED - use dsa110_contimg.conversion.streaming instead)
from .streaming_converter import (
    QueueDB,
    parse_subband_info,
    get_mosaic_queue_status,
    check_for_complete_group,
)

# Writers
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
