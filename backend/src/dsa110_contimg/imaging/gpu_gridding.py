"""
GPU-accelerated visibility gridding using CuPy.

This module implements UV-plane gridding on GPU for radio interferometry imaging.
It processes visibility data and grids it onto a 2D UV plane, followed by FFT
to produce dirty images.

Gridding Methods:
    - Nearest-neighbor: Simple, fast, lower quality
    - Convolutional: Uses gridding convolution function (GCF) for better quality
    - W-projection: Handles non-coplanar baselines (wide-field imaging)

Note: We use CuPy instead of Numba CUDA due to driver constraints
(Driver 455.23.05 limits PTX version, blocking Numba CUDA compilation).
CuPy's RawKernel provides similar performance with better compatibility.

Memory Safety:
    All GPU operations use safe_gpu_context from gpu_safety module to prevent
    OOM conditions that could crash the system.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from dsa110_contimg.utils.gpu_safety import (
    check_system_memory_available,
    safe_gpu_context,
    gpu_safe,
)

logger = logging.getLogger(__name__)

# Try to import CuPy - graceful fallback if unavailable
try:
    import cupy as cp
    from cupy import RawKernel
    CUPY_AVAILABLE = True
except ImportError:
    cp = None
    RawKernel = None
    CUPY_AVAILABLE = False
    logger.warning("CuPy not available - GPU gridding disabled")


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class GriddingConfig:
    """Configuration for GPU gridding.

    Attributes:
        image_size: Output image size in pixels (default 512)
        cell_size_arcsec: Cell size in arcseconds (default 12.0)
        gpu_id: GPU device ID to use (default 0)
        support: Convolution support size in pixels (default 3)
        oversampling: Oversampling factor for convolution (default 128)
        w_planes: Number of W-projection planes (default 1, no W-projection)
        use_w_projection: Enable W-projection for wide-field imaging (default False)
        normalize: Normalize output by weight sum (default True)
    """
    image_size: int = 512
    cell_size_arcsec: float = 12.0
    gpu_id: int = 0
    support: int = 3
    oversampling: int = 128
    w_planes: int = 1
    use_w_projection: bool = False
    normalize: bool = True

    @property
    def cell_size_rad(self) -> float:
        """Cell size in radians."""
        return self.cell_size_arcsec * np.pi / (180.0 * 3600.0)


@dataclass
class GriddingResult:
    """Result of GPU gridding operation.

    Attributes:
        image: Output image array (image_size x image_size)
        grid: UV-plane grid before FFT (if requested)
        weight_sum: Sum of weights used in gridding
        n_vis: Number of visibilities gridded
        n_flagged: Number of flagged visibilities skipped
        processing_time_s: Processing time in seconds
        gpu_id: GPU device used
        error: Error message if gridding failed (None if successful)
    """
    image: Optional[np.ndarray] = None
    grid: Optional[np.ndarray] = None
    weight_sum: float = 0.0
    n_vis: int = 0
    n_flagged: int = 0
    processing_time_s: float = 0.0
    gpu_id: int = 0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if gridding completed successfully."""
        return self.error is None and self.image is not None


# =============================================================================
# CUDA Kernels (CuPy RawKernel)
# =============================================================================

# Nearest-neighbor gridding kernel
_GRID_NN_KERNEL = """
extern "C" __global__
void grid_nearest_neighbor(
    const float* uvw,           // (N, 3) UVW coordinates in wavelengths
    const float* vis_real,      // (N,) real part of visibilities
    const float* vis_imag,      // (N,) imaginary part of visibilities
    const float* weights,       // (N,) weights
    const int* flags,           // (N,) flags (1 = flagged, skip)
    float* grid_real,           // (size, size) real part of grid
    float* grid_imag,           // (size, size) imaginary part of grid
    float* weight_grid,         // (size, size) weight accumulator
    const int n_vis,            // Number of visibilities
    const int grid_size,        // Grid size in pixels
    const float cell_size       // Cell size in radians
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (idx >= n_vis) return;
    
    // Skip flagged data
    if (flags[idx] != 0) return;
    
    // Get UV coordinates (ignore W for now)
    float u = uvw[idx * 3 + 0];
    float v = uvw[idx * 3 + 1];
    
    // Convert to pixel coordinates
    // UV are in wavelengths, need to convert to pixel indices
    // u_pix = u / cell_size_rad + grid_size/2
    float u_pix_f = u * cell_size + grid_size / 2.0f;
    float v_pix_f = v * cell_size + grid_size / 2.0f;
    
    int u_pix = (int)(u_pix_f + 0.5f);  // Round to nearest
    int v_pix = (int)(v_pix_f + 0.5f);
    
    // Bounds check
    if (u_pix < 0 || u_pix >= grid_size || v_pix < 0 || v_pix >= grid_size) return;
    
    // Grid index
    int grid_idx = v_pix * grid_size + u_pix;
    
    // Weighted visibility
    float w = weights[idx];
    float vr = vis_real[idx] * w;
    float vi = vis_imag[idx] * w;
    
    // Atomic add to grid (handles race conditions)
    atomicAdd(&grid_real[grid_idx], vr);
    atomicAdd(&grid_imag[grid_idx], vi);
    atomicAdd(&weight_grid[grid_idx], w);
}
"""

# Convolutional gridding kernel with spheroidal function
_GRID_CONV_KERNEL = """
extern "C" __global__
void grid_convolutional(
    const float* uvw,           // (N, 3) UVW coordinates
    const float* vis_real,      // (N,) real part
    const float* vis_imag,      // (N,) imaginary part
    const float* weights,       // (N,) weights
    const int* flags,           // (N,) flags
    const float* gcf,           // (oversampling, support*2+1) gridding conv function
    float* grid_real,           // (size, size) real grid
    float* grid_imag,           // (size, size) imaginary grid
    float* weight_grid,         // (size, size) weight grid
    const int n_vis,
    const int grid_size,
    const float cell_size,
    const int support,
    const int oversampling
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (idx >= n_vis) return;
    if (flags[idx] != 0) return;
    
    float u = uvw[idx * 3 + 0];
    float v = uvw[idx * 3 + 1];
    
    // Convert to pixel coordinates
    float u_pix_f = u * cell_size + grid_size / 2.0f;
    float v_pix_f = v * cell_size + grid_size / 2.0f;
    
    int u_pix = (int)floorf(u_pix_f);
    int v_pix = (int)floorf(v_pix_f);
    
    // Fractional part for oversampling
    float u_frac = u_pix_f - u_pix;
    float v_frac = v_pix_f - v_pix;
    
    int u_off = (int)(u_frac * oversampling);
    int v_off = (int)(v_frac * oversampling);
    
    float w = weights[idx];
    float vr = vis_real[idx];
    float vi = vis_imag[idx];
    
    int gcf_width = 2 * support + 1;
    
    // Convolve onto grid
    for (int dv = -support; dv <= support; dv++) {
        int vv = v_pix + dv;
        if (vv < 0 || vv >= grid_size) continue;
        
        int gcf_v_idx = (dv + support) + v_off * gcf_width;
        float gcf_v = gcf[gcf_v_idx];
        
        for (int du = -support; du <= support; du++) {
            int uu = u_pix + du;
            if (uu < 0 || uu >= grid_size) continue;
            
            int gcf_u_idx = (du + support) + u_off * gcf_width;
            float gcf_u = gcf[gcf_u_idx];
            
            float conv_weight = gcf_u * gcf_v * w;
            
            int grid_idx = vv * grid_size + uu;
            
            atomicAdd(&grid_real[grid_idx], vr * conv_weight);
            atomicAdd(&grid_imag[grid_idx], vi * conv_weight);
            atomicAdd(&weight_grid[grid_idx], conv_weight);
        }
    }
}
"""

# Weight normalization kernel
_NORMALIZE_KERNEL = """
extern "C" __global__
void normalize_grid(
    float* grid_real,
    float* grid_imag,
    const float* weight_grid,
    const int size,
    const float epsilon
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (idx >= size * size) return;
    
    float w = weight_grid[idx];
    if (w > epsilon) {
        grid_real[idx] /= w;
        grid_imag[idx] /= w;
    }
}
"""


# =============================================================================
# Compiled Kernels (lazy initialization)
# =============================================================================

_compiled_kernels = {}


def _get_kernel(name: str) -> "RawKernel":
    """Get or compile a CUDA kernel."""
    if not CUPY_AVAILABLE:
        raise RuntimeError("CuPy not available for GPU gridding")

    if name not in _compiled_kernels:
        kernel_code = {
            "grid_nn": _GRID_NN_KERNEL,
            "grid_conv": _GRID_CONV_KERNEL,
            "normalize": _NORMALIZE_KERNEL,
        }

        if name not in kernel_code:
            raise ValueError(f"Unknown kernel: {name}")

        kernel_name = {
            "grid_nn": "grid_nearest_neighbor",
            "grid_conv": "grid_convolutional",
            "normalize": "normalize_grid",
        }[name]

        _compiled_kernels[name] = cp.RawKernel(
            kernel_code[name],
            kernel_name,
            options=("-std=c++11",),
        )

    return _compiled_kernels[name]


# =============================================================================
# Gridding Convolution Function (GCF)
# =============================================================================


def _compute_spheroidal_gcf(
    support: int = 3,
    oversampling: int = 128,
) -> np.ndarray:
    """Compute prolate spheroidal wave function for gridding.

    The spheroidal function minimizes aliasing in the image plane.

    Args:
        support: Half-width of convolution function in pixels
        oversampling: Oversampling factor

    Returns:
        GCF array of shape (oversampling, 2*support+1)
    """
    width = 2 * support + 1
    gcf = np.zeros((oversampling, width), dtype=np.float32)

    # Approximation using Gaussian (simpler, still effective)
    # True spheroidal requires scipy.special.pro_ang1
    sigma = support / 2.5

    for i in range(oversampling):
        frac = i / oversampling
        for j in range(width):
            x = j - support + frac
            gcf[i, j] = np.exp(-0.5 * (x / sigma) ** 2)

        # Normalize each row
        gcf[i] /= gcf[i].sum()

    return gcf


# =============================================================================
# Memory Estimation
# =============================================================================


def estimate_gridding_memory_gb(
    n_vis: int,
    image_size: int,
    support: int = 3,
    oversampling: int = 128,
) -> Tuple[float, float]:
    """Estimate GPU and system memory required for gridding.

    Args:
        n_vis: Number of visibilities
        image_size: Image size in pixels
        support: Convolution support
        oversampling: Oversampling factor

    Returns:
        Tuple of (gpu_gb, system_gb) memory estimates
    """
    bytes_per_gb = 1024**3

    # GPU memory:
    # - UVW: n_vis * 3 * 4 bytes (float32)
    # - vis_real, vis_imag: n_vis * 4 bytes each
    # - weights: n_vis * 4 bytes
    # - flags: n_vis * 4 bytes
    # - grid_real, grid_imag, weight_grid: image_size^2 * 4 bytes each
    # - GCF: oversampling * (2*support+1) * 4 bytes
    # - FFT workspace: ~2 * image_size^2 * 8 bytes (complex64)

    input_bytes = n_vis * (3 * 4 + 4 + 4 + 4 + 4)  # UVW, vis_r, vis_i, w, flags
    grid_bytes = image_size * image_size * 4 * 3  # 3 grids
    gcf_bytes = oversampling * (2 * support + 1) * 4
    fft_bytes = image_size * image_size * 8 * 2  # workspace

    gpu_gb = (input_bytes + grid_bytes + gcf_bytes + fft_bytes) / bytes_per_gb

    # System memory: input arrays + output image
    system_gb = (input_bytes + image_size * image_size * 8) / bytes_per_gb

    # Add 20% safety margin
    return gpu_gb * 1.2, system_gb * 1.2


# =============================================================================
# GPU Gridding Functions
# =============================================================================


def _grid_visibilities_cupy(
    uvw: np.ndarray,
    vis: np.ndarray,
    weights: np.ndarray,
    flags: Optional[np.ndarray],
    config: GriddingConfig,
) -> Tuple[np.ndarray, np.ndarray, float, int]:
    """Grid visibilities on GPU using CuPy.

    Args:
        uvw: (N, 3) UVW coordinates in wavelengths
        vis: (N,) complex visibilities
        weights: (N,) weights
        flags: (N,) flags (1 = flagged, 0 = valid) or None
        config: Gridding configuration

    Returns:
        Tuple of (image, grid, weight_sum, n_flagged)
    """
    if not CUPY_AVAILABLE:
        raise RuntimeError("CuPy not available for GPU gridding")

    n_vis = len(vis)
    image_size = config.image_size

    # Create flags if not provided
    if flags is None:
        flags = np.zeros(n_vis, dtype=np.int32)
    else:
        flags = flags.astype(np.int32)

    n_flagged = int(np.sum(flags))

    # Prepare visibility data (split complex)
    vis_real = np.real(vis).astype(np.float32)
    vis_imag = np.imag(vis).astype(np.float32)
    weights = weights.astype(np.float32)
    uvw = uvw.astype(np.float32)

    # Use safe GPU context for memory protection
    with safe_gpu_context(gpu_id=config.gpu_id, max_gpu_gb=9.0):
        with cp.cuda.Device(config.gpu_id):
            # Transfer to GPU
            uvw_gpu = cp.asarray(uvw)
            vis_real_gpu = cp.asarray(vis_real)
            vis_imag_gpu = cp.asarray(vis_imag)
            weights_gpu = cp.asarray(weights)
            flags_gpu = cp.asarray(flags)

            # Allocate grids
            grid_real_gpu = cp.zeros(
                (image_size, image_size), dtype=cp.float32
            )
            grid_imag_gpu = cp.zeros(
                (image_size, image_size), dtype=cp.float32
            )
            weight_grid_gpu = cp.zeros(
                (image_size, image_size), dtype=cp.float32
            )

            # Select kernel based on configuration
            if config.support > 0:
                # Convolutional gridding
                gcf = _compute_spheroidal_gcf(config.support, config.oversampling)
                gcf_gpu = cp.asarray(gcf)

                kernel = _get_kernel("grid_conv")
                threads = 256
                blocks = (n_vis + threads - 1) // threads

                kernel(
                    (blocks,),
                    (threads,),
                    (
                        uvw_gpu,
                        vis_real_gpu,
                        vis_imag_gpu,
                        weights_gpu,
                        flags_gpu,
                        gcf_gpu,
                        grid_real_gpu,
                        grid_imag_gpu,
                        weight_grid_gpu,
                        np.int32(n_vis),
                        np.int32(image_size),
                        np.float32(1.0 / config.cell_size_rad),
                        np.int32(config.support),
                        np.int32(config.oversampling),
                    ),
                )
            else:
                # Nearest-neighbor gridding
                kernel = _get_kernel("grid_nn")
                threads = 256
                blocks = (n_vis + threads - 1) // threads

                kernel(
                    (blocks,),
                    (threads,),
                    (
                        uvw_gpu,
                        vis_real_gpu,
                        vis_imag_gpu,
                        weights_gpu,
                        flags_gpu,
                        grid_real_gpu,
                        grid_imag_gpu,
                        weight_grid_gpu,
                        np.int32(n_vis),
                        np.int32(image_size),
                        np.float32(1.0 / config.cell_size_rad),
                    ),
                )

            # Weight sum
            weight_sum = float(cp.sum(weight_grid_gpu))

            # Normalize if requested
            if config.normalize and weight_sum > 0:
                normalize_kernel = _get_kernel("normalize")
                n_pixels = image_size * image_size
                blocks_norm = (n_pixels + threads - 1) // threads

                normalize_kernel(
                    (blocks_norm,),
                    (threads,),
                    (
                        grid_real_gpu,
                        grid_imag_gpu,
                        weight_grid_gpu,
                        np.int32(image_size),
                        np.float32(1e-10),
                    ),
                )

            # Combine to complex grid
            grid_gpu = grid_real_gpu + 1j * grid_imag_gpu

            # FFT to image plane
            image_gpu = cp.fft.ifft2(cp.fft.ifftshift(grid_gpu))
            image_gpu = cp.fft.fftshift(image_gpu)

            # Transfer back to CPU
            image = cp.asnumpy(image_gpu)
            grid = cp.asnumpy(grid_gpu)

            # Cleanup GPU memory
            del uvw_gpu, vis_real_gpu, vis_imag_gpu, weights_gpu, flags_gpu
            del grid_real_gpu, grid_imag_gpu, weight_grid_gpu, grid_gpu, image_gpu
            if config.support > 0:
                del gcf_gpu
            cp.get_default_memory_pool().free_all_blocks()

    return image, grid, weight_sum, n_flagged


def _grid_visibilities_cpu(
    uvw: np.ndarray,
    vis: np.ndarray,
    weights: np.ndarray,
    flags: Optional[np.ndarray],
    config: GriddingConfig,
) -> Tuple[np.ndarray, np.ndarray, float, int]:
    """CPU fallback for gridding (numpy implementation).

    Args:
        uvw: (N, 3) UVW coordinates in wavelengths
        vis: (N,) complex visibilities
        weights: (N,) weights
        flags: (N,) flags or None
        config: Gridding configuration

    Returns:
        Tuple of (image, grid, weight_sum, n_flagged)
    """
    n_vis = len(vis)
    image_size = config.image_size
    cell_size = config.cell_size_rad

    # Create flags if not provided
    if flags is None:
        flags = np.zeros(n_vis, dtype=bool)
    else:
        flags = flags.astype(bool)

    n_flagged = int(np.sum(flags))

    # Initialize grids
    grid = np.zeros((image_size, image_size), dtype=np.complex64)
    weight_grid = np.zeros((image_size, image_size), dtype=np.float32)

    # Mask valid data
    valid = ~flags
    u = uvw[valid, 0]
    v = uvw[valid, 1]
    vis_valid = vis[valid]
    w_valid = weights[valid]

    # Convert to pixel coordinates
    u_pix = (u / cell_size + image_size / 2).astype(int)
    v_pix = (v / cell_size + image_size / 2).astype(int)

    # Filter out-of-bounds
    in_bounds = (
        (u_pix >= 0) & (u_pix < image_size) &
        (v_pix >= 0) & (v_pix < image_size)
    )

    u_pix = u_pix[in_bounds]
    v_pix = v_pix[in_bounds]
    vis_valid = vis_valid[in_bounds]
    w_valid = w_valid[in_bounds]

    # Grid using numpy (simple nearest-neighbor)
    for i in range(len(u_pix)):
        grid[v_pix[i], u_pix[i]] += vis_valid[i] * w_valid[i]
        weight_grid[v_pix[i], u_pix[i]] += w_valid[i]

    weight_sum = float(weight_grid.sum())

    # Normalize
    if config.normalize and weight_sum > 0:
        nonzero = weight_grid > 1e-10
        grid[nonzero] /= weight_grid[nonzero]

    # FFT to image plane
    image = np.fft.ifft2(np.fft.ifftshift(grid))
    image = np.fft.fftshift(image)

    return image, grid, weight_sum, n_flagged


# =============================================================================
# Public API
# =============================================================================


@gpu_safe(max_gpu_gb=9.0, max_system_gb=6.0)
def gpu_grid_visibilities(
    uvw: np.ndarray,
    vis: np.ndarray,
    weights: np.ndarray,
    *,
    config: Optional[GriddingConfig] = None,
    image_size: Optional[int] = None,
    cell_size_arcsec: Optional[float] = None,
    gpu_id: Optional[int] = None,
    flags: Optional[np.ndarray] = None,
    return_grid: bool = False,
) -> GriddingResult:
    """GPU-accelerated visibility gridding.

    Grids visibility data onto a UV plane and performs FFT to produce
    a dirty image. Uses CuPy for GPU acceleration with automatic
    memory safety guards.

    Args:
        uvw: (N, 3) UVW coordinates in wavelengths
        vis: (N,) complex visibilities
        weights: (N,) weights
        config: Gridding configuration (optional)
        image_size: Override image size from config
        cell_size_arcsec: Override cell size from config
        gpu_id: Override GPU ID from config
        flags: (N,) flags (1 = flagged, 0 = valid) or None
        return_grid: Include UV grid in result

    Returns:
        GriddingResult with image and metadata
    """
    start_time = time.time()

    # Build configuration
    if config is None:
        config = GriddingConfig()
    if image_size is not None:
        config.image_size = image_size
    if cell_size_arcsec is not None:
        config.cell_size_arcsec = cell_size_arcsec
    if gpu_id is not None:
        config.gpu_id = gpu_id

    # Validate inputs
    if uvw.ndim != 2 or uvw.shape[1] != 3:
        return GriddingResult(
            error=f"UVW must be (N, 3), got {uvw.shape}",
            gpu_id=config.gpu_id,
        )

    if len(vis) != len(uvw):
        return GriddingResult(
            error=f"vis length {len(vis)} != uvw length {len(uvw)}",
            gpu_id=config.gpu_id,
        )

    if len(weights) != len(vis):
        return GriddingResult(
            error=f"weights length {len(weights)} != vis length {len(vis)}",
            gpu_id=config.gpu_id,
        )

    n_vis = len(vis)

    # Check memory requirements
    _gpu_gb, sys_gb = estimate_gridding_memory_gb(
        n_vis, config.image_size, config.support, config.oversampling
    )
    del _gpu_gb  # GPU memory checked by @gpu_safe decorator

    is_safe, reason = check_system_memory_available(sys_gb)
    if not is_safe:
        return GriddingResult(
            error=f"Insufficient system memory: {reason}",
            n_vis=n_vis,
            gpu_id=config.gpu_id,
        )

    # Run gridding
    try:
        if CUPY_AVAILABLE:
            logger.info(
                f"GPU gridding {n_vis:,} visibilities to {config.image_size}x"
                f"{config.image_size} image on GPU {config.gpu_id}"
            )
            image, grid, weight_sum, n_flagged = _grid_visibilities_cupy(
                uvw, vis, weights, flags, config
            )
        else:
            logger.warning("CuPy not available, using CPU fallback")
            image, grid, weight_sum, n_flagged = _grid_visibilities_cpu(
                uvw, vis, weights, flags, config
            )

        processing_time = time.time() - start_time

        logger.info(
            f"Gridding complete: {n_vis - n_flagged:,} visibilities gridded "
            f"({n_flagged:,} flagged) in {processing_time:.2f}s"
        )

        return GriddingResult(
            image=np.abs(image),  # Return amplitude image
            grid=grid if return_grid else None,
            weight_sum=weight_sum,
            n_vis=n_vis,
            n_flagged=n_flagged,
            processing_time_s=processing_time,
            gpu_id=config.gpu_id,
        )

    except MemoryError as err:
        logger.error(f"Memory error during gridding: {err}")
        return GriddingResult(
            error=f"Memory error: {err}",
            n_vis=n_vis,
            gpu_id=config.gpu_id,
        )
    except RuntimeError as err:
        logger.error(f"Runtime error during gridding: {err}")
        return GriddingResult(
            error=f"Runtime error: {err}",
            n_vis=n_vis,
            gpu_id=config.gpu_id,
        )


def cpu_grid_visibilities(
    uvw: np.ndarray,
    vis: np.ndarray,
    weights: np.ndarray,
    *,
    config: Optional[GriddingConfig] = None,
    image_size: Optional[int] = None,
    cell_size_arcsec: Optional[float] = None,
    flags: Optional[np.ndarray] = None,
    return_grid: bool = False,
) -> GriddingResult:
    """CPU-only visibility gridding (no GPU required).

    This is a fallback for systems without GPU support.

    Args:
        uvw: (N, 3) UVW coordinates in wavelengths
        vis: (N,) complex visibilities
        weights: (N,) weights
        config: Gridding configuration (optional)
        image_size: Override image size from config
        cell_size_arcsec: Override cell size from config
        flags: (N,) flags or None
        return_grid: Include UV grid in result

    Returns:
        GriddingResult with image and metadata
    """
    start_time = time.time()

    # Build configuration
    if config is None:
        config = GriddingConfig()
    if image_size is not None:
        config.image_size = image_size
    if cell_size_arcsec is not None:
        config.cell_size_arcsec = cell_size_arcsec

    # Validate inputs
    if uvw.ndim != 2 or uvw.shape[1] != 3:
        return GriddingResult(
            error=f"UVW must be (N, 3), got {uvw.shape}",
        )

    if len(vis) != len(uvw) or len(weights) != len(vis):
        return GriddingResult(
            error="Input array lengths must match",
        )

    n_vis = len(vis)

    try:
        logger.info(
            f"CPU gridding {n_vis:,} visibilities to {config.image_size}x"
            f"{config.image_size} image"
        )

        image, grid, weight_sum, n_flagged = _grid_visibilities_cpu(
            uvw, vis, weights, flags, config
        )

        processing_time = time.time() - start_time

        logger.info(
            f"CPU gridding complete: {n_vis - n_flagged:,} visibilities "
            f"in {processing_time:.2f}s"
        )

        return GriddingResult(
            image=np.abs(image),
            grid=grid if return_grid else None,
            weight_sum=weight_sum,
            n_vis=n_vis,
            n_flagged=n_flagged,
            processing_time_s=processing_time,
            gpu_id=-1,  # Indicates CPU
        )

    except MemoryError as err:
        logger.error(f"Memory error during CPU gridding: {err}")
        return GriddingResult(
            error=f"Memory error: {err}",
            n_vis=n_vis,
        )


# =============================================================================
# MS Integration
# =============================================================================


def grid_ms(
    ms_path: str,
    *,
    config: Optional[GriddingConfig] = None,
    datacolumn: str = "DATA",
) -> GriddingResult:
    """Grid visibilities from a measurement set.

    Args:
        ms_path: Path to measurement set
        config: Gridding configuration
        datacolumn: Data column to grid (DATA, CORRECTED_DATA, MODEL_DATA)

    Returns:
        GriddingResult with image
    """
    from pathlib import Path

    if not Path(ms_path).exists():
        return GriddingResult(
            error=f"MS not found: {ms_path}",
        )

    try:
        from casatools import table as tb
    except ImportError:
        return GriddingResult(
            error="casatools not available for MS reading",
        )

    if config is None:
        config = GriddingConfig()

    start_time = time.time()

    try:
        # Open MS and read data
        tbl = tb()
        tbl.open(ms_path)

        uvw = tbl.getcol("UVW").T  # Transpose to (N, 3)
        vis_data = tbl.getcol(datacolumn)  # (nchan, ncorr, nrow) or similar
        weights = tbl.getcol("WEIGHT")
        flags = tbl.getcol("FLAG")

        tbl.close()

        # Flatten multi-dimensional data
        # Assuming vis_data is (nchan, ncorr, nrow), flatten to (N,)
        if vis_data.ndim == 3:
            # Average channels and polarizations for continuum
            vis = vis_data.mean(axis=(0, 1))
            flag_any = flags.any(axis=(0, 1))
            # Expand UVW for each channel (if needed)
            # For continuum, just use the original UVW
            uvw_flat = uvw
            weights_flat = weights.mean(axis=0) if weights.ndim > 1 else weights
            flags_flat = flag_any.astype(np.int32)
        else:
            vis = vis_data.ravel()
            uvw_flat = uvw
            weights_flat = weights.ravel() if weights.ndim > 1 else weights
            flags_flat = flags.ravel().astype(np.int32) if flags.ndim > 1 else flags

        # Grid
        result = gpu_grid_visibilities(
            uvw_flat,
            vis,
            weights_flat,
            config=config,
            flags=flags_flat,
        )

        # Add MS path to result
        result.processing_time_s = time.time() - start_time

        return result

    except OSError as err:
        return GriddingResult(error=f"Error reading MS: {err}")
    except RuntimeError as err:
        return GriddingResult(error=f"Runtime error: {err}")
