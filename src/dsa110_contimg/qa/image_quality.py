"""
Image quality assessment for DSA-110 continuum imaging pipeline.

Evaluates quality of CASA image products to ensure scientific validity.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()
import numpy as np

from dsa110_contimg.utils.runtime_safeguards import filter_non_finite_2d

try:
    from casacore.images import image as casaimage

    HAVE_CASACORE_IMAGES = True
except ImportError:
    HAVE_CASACORE_IMAGES = False
    logger = logging.getLogger(__name__)
    logger.warning(
        "casacore.images not available, image quality checks will be limited"
    )

logger = logging.getLogger(__name__)


@dataclass
class ImageQualityMetrics:
    """Quality metrics for CASA image products."""

    # Image info
    image_path: str
    image_type: str  # 'image', 'residual', 'psf', 'pb', etc.
    image_size_mb: float
    nx: int
    ny: int
    n_channels: int
    n_stokes: int

    # Pixel statistics
    median_pixel: float
    rms_pixel: float
    min_pixel: float
    max_pixel: float
    dynamic_range: float  # max / rms

    # Source detection (simple peak finding)
    peak_value: float
    peak_snr: float
    n_pixels_above_5sigma: int

    # Residual statistics (if residual image)
    residual_rms: Optional[float] = None
    residual_mean: Optional[float] = None

    # Quality flags
    has_issues: bool = False
    has_warnings: bool = False
    issues: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "image_path": self.image_path,
            "image_type": self.image_type,
            "image_size_mb": self.image_size_mb,
            "dimensions": {
                "nx": self.nx,
                "ny": self.ny,
                "n_channels": self.n_channels,
                "n_stokes": self.n_stokes,
            },
            "pixel_statistics": {
                "median": self.median_pixel,
                "rms": self.rms_pixel,
                "min": self.min_pixel,
                "max": self.max_pixel,
                "dynamic_range": self.dynamic_range,
            },
            "sources": {
                "peak_value": self.peak_value,
                "peak_snr": self.peak_snr,
                "n_pixels_above_5sigma": self.n_pixels_above_5sigma,
            },
            "residuals": (
                {
                    "rms": self.residual_rms,
                    "mean": self.residual_mean,
                }
                if self.residual_rms is not None
                else None
            ),
            "quality": {
                "has_issues": self.has_issues,
                "has_warnings": self.has_warnings,
                "issues": self.issues,
                "warnings": self.warnings,
            },
        }


def validate_image_quality(image_path: str) -> ImageQualityMetrics:
    """
    Validate quality of a CASA image.

    Args:
        image_path: Path to CASA image

    Returns:
        ImageQualityMetrics object
    """
    logger.info(f"Validating image quality: {image_path}")

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    issues = []
    warnings = []

    # Get image size
    image_size_bytes = sum(
        os.path.getsize(os.path.join(dirpath, filename))
        for dirpath, dirnames, filenames in os.walk(image_path)
        for filename in filenames
    )
    image_size_mb = image_size_bytes / (1024**2)

    # Infer image type from filename
    basename = os.path.basename(image_path).lower()
    if "residual" in basename:
        image_type = "residual"
    elif "psf" in basename:
        image_type = "psf"
    elif "pb" in basename and "pbcor" not in basename:
        image_type = "pb"
    elif "pbcor" in basename:
        image_type = "pbcor"
    elif "model" in basename:
        image_type = "model"
    else:
        image_type = "image"

    try:
        if HAVE_CASACORE_IMAGES:
            img = casaimage(image_path)

            # Get image shape
            # CASA images are typically [stokes, channel, ny, nx] or similar
            shape = img.shape()
            full_data = img.getdata()

            if len(shape) == 2:
                nx, ny = shape
                n_channels = 1
                n_stokes = 1
                pixels = full_data
            elif len(shape) == 3:
                # Could be [ny, nx, channel] or [stokes, ny, nx]
                # Assume spatial dimensions are largest
                sorted_dims = sorted(enumerate(shape), key=lambda x: x[1], reverse=True)
                spatial_indices = [sorted_dims[0][0], sorted_dims[1][0]]
                nx, ny = sorted_dims[0][1], sorted_dims[1][1]
                n_channels = shape[sorted_dims[2][0]]
                n_stokes = 1
                # Extract first non-spatial slice
                if sorted_dims[2][0] == 2:
                    pixels = full_data[:, :, 0]
                else:
                    pixels = full_data[0, :, :]
            elif len(shape) == 4:
                # Typical: [stokes, channel, ny, nx] or [nx, ny, stokes, channel]
                # Spatial dimensions are typically the largest two
                sorted_dims = sorted(enumerate(shape), key=lambda x: x[1], reverse=True)
                spatial_idx = [sorted_dims[0][0], sorted_dims[1][0]]
                nx, ny = sorted_dims[0][1], sorted_dims[1][1]

                # Other two are stokes/channel
                other_idx = [i for i in range(4) if i not in spatial_idx]
                n_stokes = shape[other_idx[0]]
                n_channels = shape[other_idx[1]]

                # Extract first stokes, first channel, all spatial
                # The spatial dimensions should be preserved
                pixels = (
                    full_data[0, 0, :, :]
                    if spatial_idx == [2, 3]
                    else full_data[:, :, 0, 0]
                )
            else:
                nx = ny = n_channels = n_stokes = 0
                pixels = np.array([])
                warnings.append(f"Unexpected image shape: {shape}")

            try:
                img.close()
            except AttributeError:
                # Some casacore versions don't have close()
                del img
        else:
            # Fallback: try to read with CASA table interface
            import casacore.tables as casatables
            table = casatables.table  # noqa: N816

            with table(image_path, readonly=True, ack=False) as tb:
                shape_col = tb.getcol("shape") if "shape" in tb.colnames() else None
                if shape_col is not None and len(shape_col) > 0:
                    shape = tuple(shape_col[0])
                    if len(shape) >= 2:
                        nx, ny = shape[:2]
                        n_channels = shape[2] if len(shape) > 2 else 1
                        n_stokes = shape[3] if len(shape) > 3 else 1
                    else:
                        nx = ny = n_channels = n_stokes = 0
                else:
                    nx = ny = n_channels = n_stokes = 0

                # Try to get pixels
                if "map" in tb.colnames():
                    pixels = tb.getcol("map")[0]
                else:
                    pixels = np.array([])
                    issues.append("Cannot read pixel data from table")

        # Compute statistics
        if pixels.size > 0:
            # Remove NaN and Inf
            # Filter non-finite values before statistics
            valid_pixels = pixels[np.isfinite(pixels)]

            if len(valid_pixels) == 0:
                issues.append("All pixels are NaN or Inf")
                # Set defaults to avoid errors
                median_pixel = rms_pixel = min_pixel = max_pixel = 0.0
                dynamic_range = 0.0
                peak_value = peak_snr = 0.0
                n_pixels_above_5sigma = 0
            else:
                median_pixel = float(np.median(valid_pixels))
                rms_pixel = float(np.sqrt(np.mean(valid_pixels**2)))
                min_pixel = float(np.min(valid_pixels))
                max_pixel = float(np.max(valid_pixels))

                # Dynamic range
                if rms_pixel > 0:
                    dynamic_range = abs(max_pixel) / rms_pixel
                else:
                    dynamic_range = 0.0

                # Peak finding
                peak_value = float(np.max(np.abs(valid_pixels)))
                if rms_pixel > 0:
                    peak_snr = peak_value / rms_pixel
                else:
                    peak_snr = 0.0

                # Count pixels above 5-sigma
                if rms_pixel > 0:
                    n_pixels_above_5sigma = int(
                        np.sum(np.abs(valid_pixels) > 5 * rms_pixel)
                    )
                else:
                    n_pixels_above_5sigma = 0

                # Quality checks
                if image_type in ["image", "pbcor"]:
                    if dynamic_range < 5:
                        warnings.append(f"Low dynamic range: {dynamic_range:.1f}")

                    if peak_snr < 5:
                        warnings.append(f"Low peak SNR: {peak_snr:.1f}")

                    if n_pixels_above_5sigma < 10:
                        warnings.append(
                            f"Few pixels above 5-sigma: {n_pixels_above_5sigma}"
                        )

                # Check for all-zero image
                if np.all(np.abs(valid_pixels) < 1e-20):
                    issues.append("Image is all zeros")
        else:
            issues.append("No valid pixels found")
            median_pixel = rms_pixel = min_pixel = max_pixel = 0.0
            dynamic_range = 0.0
            peak_value = 0.0
            peak_snr = 0.0
            n_pixels_above_5sigma = 0

        # Residual-specific checks
        residual_rms = None
        residual_mean = None
        if image_type == "residual" and pixels.size > 0:
            valid_pixels = pixels[np.isfinite(pixels)]
            if len(valid_pixels) > 0:
                residual_rms = float(np.std(valid_pixels))
                residual_mean = float(np.mean(valid_pixels))

                # Residuals should have mean close to zero
                if abs(residual_mean) > 3 * residual_rms:
                    warnings.append(
                        f"Residual mean far from zero: {residual_mean:.3e} (rms={residual_rms:.3e})"
                    )

    except Exception as e:
        logger.error(f"Error validating image: {e}")
        issues.append(f"Exception during validation: {e}")
        nx = ny = n_channels = n_stokes = 0
        median_pixel = rms_pixel = min_pixel = max_pixel = 0.0
        dynamic_range = 0.0
        peak_value = 0.0
        peak_snr = 0.0
        n_pixels_above_5sigma = 0
        residual_rms = None
        residual_mean = None

    metrics = ImageQualityMetrics(
        image_path=image_path,
        image_type=image_type,
        image_size_mb=image_size_mb,
        nx=nx,
        ny=ny,
        n_channels=n_channels,
        n_stokes=n_stokes,
        median_pixel=median_pixel,
        rms_pixel=rms_pixel,
        min_pixel=min_pixel,
        max_pixel=max_pixel,
        dynamic_range=dynamic_range,
        peak_value=peak_value,
        peak_snr=peak_snr,
        n_pixels_above_5sigma=n_pixels_above_5sigma,
        residual_rms=residual_rms,
        residual_mean=residual_mean,
        has_issues=len(issues) > 0,
        has_warnings=len(warnings) > 0,
        issues=issues,
        warnings=warnings,
    )

    # Log results
    if metrics.has_issues:
        logger.error(f"Image has issues: {', '.join(issues)}")
    if metrics.has_warnings:
        logger.warning(f"Image has warnings: {', '.join(warnings)}")
    if not metrics.has_issues and not metrics.has_warnings:
        logger.info(
            f"Image passed quality checks: peak_snr={peak_snr:.1f}, dynamic_range={dynamic_range:.1f}"
        )

    return metrics


def quick_image_check(image_path: str) -> Tuple[bool, str]:
    """
    Quick sanity check for image quality.

    Returns:
        (passed, message) tuple
    """
    try:
        if not os.path.exists(image_path):
            return False, "Image does not exist"

        # Check for minimum size (CASA images are directories)
        image_size_bytes = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, dirnames, filenames in os.walk(image_path)
            for filename in filenames
        )

        if image_size_bytes < 1024:
            return False, "Image is too small (likely corrupted)"

        return True, "Image passed quick check"

    except Exception as e:
        return False, f"Exception during check: {e}"
