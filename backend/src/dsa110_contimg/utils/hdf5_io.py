"""Optimized HDF5 I/O utilities for DSA-110 pipeline.

This module provides optimized h5py file access with proper chunk cache settings
to avoid catastrophic performance degradation when reading chunked/compressed data.

Performance Background (from HDF Group documentation):
    - Default h5py chunk cache is 1MB
    - If chunks are larger than cache, each read causes full chunk decompression
    - This can cause 1000x slowdowns for repeated access patterns
    - Solution: Set rdcc_nbytes to hold at least one full chunk

DSA-110 UVH5 File Characteristics:
    - Typical visibility chunk sizes: 2-4 MB
    - Recommended cache size: 16 MB (holds multiple chunks)
    - For metadata-only reads: cache can be disabled (0 bytes)

Usage:
    # For repeated reads (hot path):
    with open_uvh5(path) as f:
        data = f['visdata'][:]

    # For metadata-only reads (cold path):
    with open_uvh5_metadata(path) as f:
        times = f['time_array'][:]

    # For single-pass bulk reads:
    with open_uvh5_streaming(path) as f:
        data = f['visdata'][:]  # Read all at once

Reference:
    https://support.hdfgroup.org/documentation/hdf5/latest/improve_compressed_perf.html
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional, Union

if TYPE_CHECKING:
    import h5py

logger = logging.getLogger(__name__)

# Cache size constants (in bytes)
# Default: 16 MB - holds multiple DSA-110 visibility chunks
HDF5_CACHE_SIZE_DEFAULT = 16 * 1024 * 1024  # 16 MB

# Large cache for intensive I/O operations
HDF5_CACHE_SIZE_LARGE = 64 * 1024 * 1024  # 64 MB

# Metadata-only: small cache sufficient for header data
HDF5_CACHE_SIZE_METADATA = 1 * 1024 * 1024  # 1 MB

# Streaming: disable cache for single-pass reads (saves memory)
HDF5_CACHE_SIZE_STREAMING = 0  # Disabled

# Number of hash table slots (prime number recommended)
# Default h5py is 521; we use larger for better distribution
HDF5_CACHE_SLOTS = 1009


@contextmanager
def open_uvh5(
    path: Union[str, Path],
    mode: str = "r",
    cache_size: int = HDF5_CACHE_SIZE_DEFAULT,
    cache_slots: int = HDF5_CACHE_SLOTS,
) -> Iterator["h5py.File"]:
    """Open UVH5/HDF5 file with optimized chunk cache settings.

    This is the recommended method for opening HDF5 files in the pipeline.
    Uses a 16 MB chunk cache by default, which prevents repeated chunk
    decompression when accessing chunked datasets.

    Args:
        path: Path to HDF5 file
        mode: File mode ('r', 'r+', 'w', 'w-', 'a')
        cache_size: Chunk cache size in bytes (default: 16 MB)
        cache_slots: Number of hash table slots (default: 1009)

    Yields:
        h5py.File object with optimized settings

    Example:
        >>> with open_uvh5("/data/file.hdf5") as f:
        ...     times = f['time_array'][:]
        ...     data = f['visdata'][:]
    """
    import h5py

    # rdcc_nbytes: raw data chunk cache size in bytes
    # rdcc_nslots: number of chunk slots in cache hash table
    # rdcc_w0: preemption policy (0.0 = LRU, 1.0 = evict fully read chunks)
    with h5py.File(
        path,
        mode,
        rdcc_nbytes=cache_size,
        rdcc_nslots=cache_slots,
        rdcc_w0=0.75,  # Balanced preemption
    ) as f:
        yield f


@contextmanager
def open_uvh5_metadata(
    path: Union[str, Path],
    cache_size: int = HDF5_CACHE_SIZE_METADATA,
) -> Iterator["h5py.File"]:
    """Open UVH5/HDF5 file for metadata-only access.

    Uses a smaller cache (1 MB) since metadata datasets are typically small.
    Suitable for operations that only read headers, time arrays, etc.

    Args:
        path: Path to HDF5 file
        cache_size: Chunk cache size in bytes (default: 1 MB)

    Yields:
        h5py.File object

    Example:
        >>> with open_uvh5_metadata("/data/file.hdf5") as f:
        ...     times = f['time_array'][:]
        ...     dec = f['Header/extra_keywords/phase_center_dec'][()]
    """
    import h5py

    with h5py.File(
        path,
        "r",
        rdcc_nbytes=cache_size,
        rdcc_nslots=HDF5_CACHE_SLOTS,
    ) as f:
        yield f


@contextmanager
def open_uvh5_streaming(
    path: Union[str, Path],
    mode: str = "r",
) -> Iterator["h5py.File"]:
    """Open UVH5/HDF5 file for single-pass streaming reads.

    Disables chunk caching entirely since data is read only once.
    This saves memory and is appropriate for bulk data transfers
    where the same chunk is never accessed twice.

    Args:
        path: Path to HDF5 file
        mode: File mode ('r', 'r+', 'w', 'w-', 'a')

    Yields:
        h5py.File object with caching disabled

    Example:
        >>> with open_uvh5_streaming("/data/file.hdf5") as f:
        ...     all_data = f['visdata'][:]  # Read entire dataset at once
    """
    import h5py

    with h5py.File(
        path,
        mode,
        rdcc_nbytes=HDF5_CACHE_SIZE_STREAMING,  # Disable cache
        rdcc_nslots=1,  # Minimal slots
    ) as f:
        yield f


@contextmanager
def open_uvh5_large_cache(
    path: Union[str, Path],
    mode: str = "r",
    cache_size: int = HDF5_CACHE_SIZE_LARGE,
) -> Iterator["h5py.File"]:
    """Open UVH5/HDF5 file with large chunk cache for intensive I/O.

    Uses a 64 MB cache for operations that repeatedly access multiple
    chunks, such as downsampling or reordering data.

    Args:
        path: Path to HDF5 file
        mode: File mode ('r', 'r+', 'w', 'w-', 'a')
        cache_size: Chunk cache size in bytes (default: 64 MB)

    Yields:
        h5py.File object with large cache

    Example:
        >>> with open_uvh5_large_cache("/data/file.hdf5") as f:
        ...     # Intensive random access pattern
        ...     for i in range(1000):
        ...         chunk = f['visdata'][i*100:(i+1)*100]
    """
    import h5py

    with h5py.File(
        path,
        mode,
        rdcc_nbytes=cache_size,
        rdcc_nslots=HDF5_CACHE_SLOTS * 2,  # More slots for large cache
        rdcc_w0=0.5,  # More aggressive eviction
    ) as f:
        yield f


def get_chunk_info(path: Union[str, Path], dataset_name: str) -> Optional[dict]:
    """Get chunk information for a dataset.

    Useful for diagnosing performance issues and choosing optimal
    cache sizes.

    Args:
        path: Path to HDF5 file
        dataset_name: Name of dataset (e.g., 'visdata', 'Header/time_array')

    Returns:
        Dictionary with chunk info, or None if not chunked:
        {
            'chunks': tuple of chunk dimensions,
            'chunk_size_bytes': size of one chunk in bytes,
            'compression': compression filter name or None,
            'dtype': numpy dtype string
        }

    Example:
        >>> info = get_chunk_info("/data/file.hdf5", "visdata")
        >>> print(f"Chunk size: {info['chunk_size_bytes'] / 1024 / 1024:.1f} MB")
    """
    import h5py
    import numpy as np

    with h5py.File(path, "r") as f:
        if dataset_name not in f:
            return None

        ds = f[dataset_name]
        if not ds.chunks:
            return None

        chunk_shape = ds.chunks
        dtype = ds.dtype
        chunk_size = int(np.prod(chunk_shape)) * dtype.itemsize

        # Get compression filter
        compression = None
        if ds.compression:
            compression = ds.compression

        return {
            "chunks": chunk_shape,
            "chunk_size_bytes": chunk_size,
            "compression": compression,
            "dtype": str(dtype),
        }


# Backwards compatibility: simple wrapper for quick migration
def h5py_open(
    path: Union[str, Path],
    mode: str = "r",
    **kwargs,
) -> "h5py.File":
    """Direct h5py.File replacement with optimized defaults.

    This function can be used as a drop-in replacement for h5py.File()
    when you need the file handle outside a context manager.

    WARNING: Caller is responsible for closing the file!

    Args:
        path: Path to HDF5 file
        mode: File mode
        **kwargs: Additional h5py.File arguments

    Returns:
        h5py.File object (must be closed by caller)
    """
    import h5py

    # Set optimized defaults if not specified
    if "rdcc_nbytes" not in kwargs:
        kwargs["rdcc_nbytes"] = HDF5_CACHE_SIZE_DEFAULT
    if "rdcc_nslots" not in kwargs:
        kwargs["rdcc_nslots"] = HDF5_CACHE_SLOTS

    return h5py.File(path, mode, **kwargs)


__all__ = [
    "open_uvh5",
    "open_uvh5_metadata",
    "open_uvh5_streaming",
    "open_uvh5_large_cache",
    "get_chunk_info",
    "h5py_open",
    "HDF5_CACHE_SIZE_DEFAULT",
    "HDF5_CACHE_SIZE_LARGE",
    "HDF5_CACHE_SIZE_METADATA",
    "HDF5_CACHE_SIZE_STREAMING",
]
