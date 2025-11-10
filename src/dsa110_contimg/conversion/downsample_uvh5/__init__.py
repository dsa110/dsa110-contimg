"""Downsample UVH5 helpers.

Exports a small, stable API for single-file, fast single-file, and batch downsampling.
"""

from .downsample_hdf5 import downsample_uvh5
from .downsample_hdf5_fast import downsample_uvh5_fast
from .downsample_hdf5_batch import downsample_uvh5_batch

__all__ = [
    "downsample_uvh5",
    "downsample_uvh5_fast",
    "downsample_uvh5_batch",
]
