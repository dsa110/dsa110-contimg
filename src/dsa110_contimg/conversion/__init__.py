"""Conversion stage for the DSA-110 continuum imaging pipeline.

This package provides a public API for the main conversion entry points.

- `convert_single_uvh5`: convert a single UVH5 file or directory of files.
- `convert_subband_groups_to_ms`: discover and convert complete subband groups.
- `configure_ms_for_imaging`: prepare a Measurement Set for imaging.
"""

from .uvh5_to_ms import convert_single_file
from .strategies.hdf5_orchestrator import convert_subband_groups_to_ms
from .ms_utils import configure_ms_for_imaging
from .merge_spws import merge_spws, merge_spws_simple, get_spw_count

__all__ = [
    "convert_single_file",
    "convert_subband_groups_to_ms",
    "configure_ms_for_imaging",
    "merge_spws",
    "merge_spws_simple",
    "get_spw_count",
]
