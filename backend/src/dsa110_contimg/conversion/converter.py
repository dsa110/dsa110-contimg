"""
HDF5 Subband Group Converter for DSA-110 Continuum Imaging Pipeline.

This module is the flattened entry point for conversion functionality.
It re-exports from the strategies subpackage for backwards compatibility
during the migration period.

Usage:
    from dsa110_contimg.conversion.converter import convert_subband_groups_to_ms
    # or
    from dsa110_contimg.conversion import convert_subband_groups_to_ms
"""

from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
    convert_subband_groups_to_ms,
    _extract_subband_code,
    _convert_single_group,
    _load_and_combine_subbands,
    _extract_group_id,
    _find_missing_subbands,
)

__all__ = [
    "convert_subband_groups_to_ms",
    # Internal helpers exposed for testing
    "_extract_subband_code",
    "_convert_single_group",
    "_load_and_combine_subbands",
    "_extract_group_id",
    "_find_missing_subbands",
]
