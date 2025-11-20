"""
Runtime Safeguards for Common Pitfalls

This module provides decorators, validators, and runtime checks to prevent
common mistakes identified during development.

Usage:
    from dsa110_contimg.utils.runtime_safeguards import (
        require_casa6_python,
        validate_wcs_4d,
        filter_non_finite,
        log_progress,
        validate_image_shape,
    )

    @require_casa6_python
    def my_function():
        ...

    wcs = validate_wcs_4d(wcs)
    data = filter_non_finite(data, min_points=10)
"""

import functools
import os
import sys
import time
import warnings
from typing import Callable, Optional, Tuple

import numpy as np
from astropy.wcs import WCS

# ============================================================================
# Python Environment Safeguards
# ============================================================================


def check_casa6_python() -> bool:
    """Check if running in casa6 Python environment.

    Returns:
        True if casa6 Python detected, False otherwise
    """
    python_path = sys.executable
    expected_paths = [
        "/opt/miniforge/envs/casa6/bin/python",
        "casa6",
    ]

    # Check if path contains casa6
    is_casa6 = any("casa6" in python_path.lower() for expected_path in expected_paths)

    # Also check for CASA availability
    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path

    ensure_casa_path()

    try:
        import casatools

        is_casa6 = True
    except ImportError:
        pass

    return is_casa6


def require_casa6_python(func: Callable) -> Callable:
    """Decorator to ensure function runs in casa6 Python environment.

    Raises:
        RuntimeError: If not running in casa6 Python environment
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not check_casa6_python():
            raise RuntimeError(
                f"{func.__name__} requires casa6 Python environment. "
                f"Current Python: {sys.executable}. "
                f"Use: /opt/miniforge/envs/casa6/bin/python"
            )
        return func(*args, **kwargs)

    return wrapper


# ============================================================================
# WCS Safeguards
# ============================================================================


def validate_wcs_4d(
    wcs: Optional[WCS], default_freq: float = 0.0, default_stokes: float = 0.0
) -> Tuple[WCS, bool, Tuple[float, float]]:
    """Validate and normalize WCS for 4D compatibility.

    Args:
        wcs: WCS object (may be None)
        default_freq: Default frequency value for 4D WCS
        default_stokes: Default Stokes value for 4D WCS

    Returns:
        Tuple of (wcs, is_4d, defaults) where:
        - wcs: WCS object (unchanged)
        - is_4d: True if 4D WCS detected
        - defaults: (default_freq, default_stokes) tuple
    """
    if wcs is None:
        return None, False, (default_freq, default_stokes)

    is_4d = hasattr(wcs, "naxis") and wcs.naxis == 4
    return wcs, is_4d, (default_freq, default_stokes)


def wcs_pixel_to_world_safe(
    wcs: WCS,
    x: float,
    y: float,
    is_4d: bool = None,
    defaults: Tuple[float, float] = (0.0, 0.0),
) -> Tuple[float, float]:
    """Safely convert pixel to world coordinates, handling 4D WCS.

    Args:
        wcs: WCS object
        x: X pixel coordinate
        y: Y pixel coordinate
        is_4d: Whether WCS is 4D (auto-detected if None)
        defaults: (frequency, stokes) defaults for 4D WCS

    Returns:
        (ra, dec) tuple in degrees
    """
    if wcs is None:
        raise ValueError("WCS is None")

    if is_4d is None:
        _, is_4d, defaults = validate_wcs_4d(wcs)

    if is_4d:
        world_coords = wcs.all_pix2world(x, y, defaults[0], defaults[1], 0)
        return float(world_coords[0]), float(world_coords[1])
    else:
        sky_coord = wcs.pixel_to_world(x, y)
        return float(sky_coord.ra.deg), float(sky_coord.dec.deg)


def wcs_world_to_pixel_safe(
    wcs: WCS,
    ra: float,
    dec: float,
    is_4d: bool = None,
    defaults: Tuple[float, float] = (0.0, 0.0),
) -> Tuple[float, float]:
    """Safely convert world to pixel coordinates, handling 4D WCS.

    Args:
        wcs: WCS object
        ra: RA in degrees
        dec: Dec in degrees
        is_4d: Whether WCS is 4D (auto-detected if None)
        defaults: (frequency, stokes) defaults for 4D WCS

    Returns:
        (x, y) pixel coordinates
    """
    if wcs is None:
        raise ValueError("WCS is None")

    if is_4d is None:
        _, is_4d, defaults = validate_wcs_4d(wcs)

    if is_4d:
        pixel_coords = wcs.all_world2pix([[ra, dec, defaults[0], defaults[1]]], 0)[0]
        return float(pixel_coords[0]), float(pixel_coords[1])
    else:
        pixel_coords = wcs.wcs_world2pix([[ra, dec]], 0)[0]
        return float(pixel_coords[0]), float(pixel_coords[1])


# ============================================================================
# Non-Finite Value Safeguards
# ============================================================================


def filter_non_finite(
    data: np.ndarray, min_points: int = 1, warn: bool = True, return_mask: bool = False
) -> np.ndarray:
    """Filter non-finite values from array, with validation.

    Args:
        data: Input array (may contain NaN/Inf)
        min_points: Minimum number of finite points required
        warn: Whether to warn if filtering occurs
        return_mask: If True, return (filtered_data, mask) tuple

    Returns:
        Filtered array (or tuple if return_mask=True)

    Raises:
        ValueError: If insufficient finite points
    """
    finite_mask = np.isfinite(data)
    n_finite = np.sum(finite_mask)

    if n_finite < min_points:
        raise ValueError(
            f"Insufficient finite values: {n_finite} < {min_points}. " f"Total points: {len(data)}"
        )

    if warn and n_finite < len(data):
        n_filtered = len(data) - n_finite
        warnings.warn(
            f"Filtered {n_filtered} non-finite values ({100 * n_filtered / len(data):.1f}%)",
            UserWarning,
        )

    filtered = data[finite_mask]

    if return_mask:
        return filtered, finite_mask
    return filtered


def filter_non_finite_2d(
    data: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    min_points: int = 1,
    warn: bool = True,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Filter non-finite values from 2D fitting data.

    Args:
        data: Flux values
        x_coords: X coordinates
        y_coords: Y coordinates
        min_points: Minimum number of finite points required
        warn: Whether to warn if filtering occurs

    Returns:
        (filtered_data, filtered_x, filtered_y) tuple

    Raises:
        ValueError: If insufficient finite points
    """
    finite_mask = np.isfinite(data)
    n_finite = np.sum(finite_mask)

    if n_finite < min_points:
        raise ValueError(f"Insufficient finite values for fitting: {n_finite} < {min_points}")

    if warn and n_finite < len(data):
        n_filtered = len(data) - n_finite
        warnings.warn(
            f"Filtered {n_filtered} non-finite values ({100 * n_filtered / len(data):.1f}%) before fitting",
            UserWarning,
        )

    return data[finite_mask], x_coords[finite_mask], y_coords[finite_mask]


# ============================================================================
# Progress Monitoring Safeguards
# ============================================================================


def ensure_unbuffered_output():
    """Ensure stdout/stderr are unbuffered."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)

    # Set environment variable (for subprocesses)
    os.environ["PYTHONUNBUFFERED"] = "1"


def log_progress(message: str, start_time: Optional[float] = None, flush: bool = True):
    """Log progress with timestamp and optional elapsed time.

    Ensures output is flushed immediately.

    Args:
        message: Progress message
        start_time: Start time (from time.time()) for elapsed calculation
        flush: Whether to flush output immediately
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%H:%M:%S")

    if start_time:
        elapsed = time.time() - start_time
        output = f"[{timestamp}] {message} (elapsed: {elapsed:.1f}s)\n"
    else:
        output = f"[{timestamp}] {message}\n"

    sys.stdout.write(output)
    if flush:
        sys.stdout.flush()


def progress_monitor(operation_name: str = None, warn_threshold: float = 10.0):
    """Decorator to monitor operation progress and warn on slow operations.

    Args:
        operation_name: Name of operation (defaults to function name)
        warn_threshold: Warn if operation takes longer than this (seconds)
    """

    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            log_progress(f"Starting {op_name}...")

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                if elapsed > warn_threshold:
                    log_progress(
                        f"Completed {op_name} (slow: {elapsed:.1f}s > {warn_threshold}s)",
                        start_time,
                    )
                else:
                    log_progress(f"Completed {op_name}", start_time)

                return result
            except Exception as e:
                elapsed = time.time() - start_time
                log_progress(f"Failed {op_name} after {elapsed:.1f}s: {e}")
                raise

        return wrapper

    return decorator


# ============================================================================
# Input Validation Safeguards
# ============================================================================


def validate_image_shape(
    data: np.ndarray, min_size: int = 1, max_size: int = None
) -> Tuple[int, int]:
    """Validate image shape and return (ny, nx).

    Args:
        data: Image data array
        min_size: Minimum dimension size
        max_size: Maximum dimension size (None = no limit)

    Returns:
        (ny, nx) tuple

    Raises:
        ValueError: If shape is invalid
    """
    if data.ndim < 2:
        raise ValueError(f"Image data must be at least 2D, got {data.ndim}D")

    # Handle multi-dimensional data (common in radio astronomy)
    if data.ndim > 2:
        # Squeeze out singleton dimensions
        data = data.squeeze()
        if data.ndim > 2:
            # Take first slice if still > 2D
            data = data[0, 0] if data.ndim == 4 else data[0]

    ny, nx = data.shape[:2]

    if ny < min_size or nx < min_size:
        raise ValueError(f"Image dimensions too small: {ny}x{nx} < {min_size}x{min_size}")

    if max_size and (ny > max_size or nx > max_size):
        raise ValueError(f"Image dimensions too large: {ny}x{nx} > {max_size}x{max_size}")

    return ny, nx


def validate_region_mask(mask: Optional[np.ndarray], image_shape: Tuple[int, int]) -> np.ndarray:
    """Validate region mask and ensure it matches image shape.

    Args:
        mask: Region mask (may be None)
        image_shape: (ny, nx) image shape

    Returns:
        Validated mask (or None if input was None)

    Raises:
        ValueError: If mask shape doesn't match image
    """
    if mask is None:
        return None

    ny, nx = image_shape
    if mask.shape != (ny, nx):
        raise ValueError(f"Mask shape {mask.shape} doesn't match image shape ({ny}, {nx})")

    if not np.any(mask):
        warnings.warn("Region mask contains no valid pixels", UserWarning)

    return mask


# ============================================================================
# Performance Safeguards
# ============================================================================


def check_performance_threshold(
    operation_name: str, elapsed_time: float, threshold: float, warn: bool = True
) -> bool:
    """Check if operation exceeded performance threshold.

    Args:
        operation_name: Name of operation
        elapsed_time: Elapsed time in seconds
        threshold: Threshold in seconds
        warn: Whether to warn if threshold exceeded

    Returns:
        True if threshold exceeded, False otherwise
    """
    if elapsed_time > threshold:
        if warn:
            warnings.warn(
                f"{operation_name} took {elapsed_time:.1f}s (threshold: {threshold}s). "
                f"Consider using sub-regions for large images.",
                UserWarning,
            )
        return True
    return False


# ============================================================================
# Module Initialization
# ============================================================================

# Ensure unbuffered output on import
ensure_unbuffered_output()

# Warn if not in casa6 environment (but don't fail)
if not check_casa6_python():
    warnings.warn(
        f"Not running in casa6 Python environment. Current: {sys.executable}. "
        f"Some functionality may not work correctly.",
        RuntimeWarning,
    )
