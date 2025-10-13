"""Conversion stage for the DSA-110 continuum imaging pipeline.

This package avoids importing heavy submodules at import time to prevent
runpy warnings when executing modules via ``python -m``.

Import submodules directly, e.g.:
  - ``from dsa110_contimg.conversion import uvh5_to_ms_converter_v2 as v2``
  - ``from dsa110_contimg.conversion import streaming_converter``
  - ``from dsa110_contimg.conversion import downsample_hdf5``
"""

__all__ = []
