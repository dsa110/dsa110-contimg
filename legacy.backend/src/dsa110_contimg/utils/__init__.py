"""
Utility modules for DSA-110 Continuum Imaging Pipeline.
"""

# Import runtime safeguards for easy access
from dsa110_contimg.utils.runtime_safeguards import (
    check_casa6_python,
    check_performance_threshold,
    ensure_unbuffered_output,
    filter_non_finite,
    filter_non_finite_2d,
    log_progress,
    progress_monitor,
    require_casa6_python,
    validate_image_shape,
    validate_region_mask,
    validate_wcs_4d,
    wcs_pixel_to_world_safe,
    wcs_world_to_pixel_safe,
)

# Fast UVH5 metadata reading (700x faster than UVData.read)
from dsa110_contimg.utils.fast_meta import (
    FastMeta,
    get_uvh5_basic_info,
    get_uvh5_freqs,
    get_uvh5_mid_mjd,
    get_uvh5_times,
)

# Optimized HDF5 I/O with proper chunk cache sizing
from dsa110_contimg.utils.hdf5_io import (
    configure_h5py_cache_defaults,
    get_h5py_cache_info,
    open_uvh5,
    open_uvh5_large_cache,
    open_uvh5_metadata,
    open_uvh5_mmap,
    open_uvh5_streaming,
)

# Numba-accelerated functions (optional, graceful fallback)
try:
    from dsa110_contimg.utils.numba_accel import (
        NUMBA_AVAILABLE,
        angular_separation_jit,
        is_numba_available,
        warm_up_jit,
    )
except ImportError:
    NUMBA_AVAILABLE = False
    angular_separation_jit = None

    def is_numba_available():
        return False

    def warm_up_jit():
        pass

__all__ = [
    "check_casa6_python",
    "require_casa6_python",
    "validate_wcs_4d",
    "wcs_pixel_to_world_safe",
    "wcs_world_to_pixel_safe",
    "filter_non_finite",
    "filter_non_finite_2d",
    "ensure_unbuffered_output",
    "log_progress",
    "progress_monitor",
    "validate_image_shape",
    "validate_region_mask",
    "check_performance_threshold",
    # Fast metadata
    "FastMeta",
    "get_uvh5_times",
    "get_uvh5_mid_mjd",
    "get_uvh5_freqs",
    "get_uvh5_basic_info",
    # HDF5 I/O
    "configure_h5py_cache_defaults",
    "get_h5py_cache_info",
    "open_uvh5",
    "open_uvh5_metadata",
    "open_uvh5_streaming",
    "open_uvh5_large_cache",
    "open_uvh5_mmap",
    # Numba acceleration
    "NUMBA_AVAILABLE",
    "angular_separation_jit",
    "is_numba_available",
    "warm_up_jit",
]
