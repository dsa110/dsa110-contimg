"""
Post-mosaic validation functions.

Validates the quality of the final mosaic after combination,
checking for artifacts, discontinuities, and statistical consistency.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Ensure CASAPATH is set before importing CASA modules
try:
    from dsa110_contimg.utils.casa_init import ensure_casa_path

    ensure_casa_path()
except ImportError:
    pass  # If casa_init not available, continue anyway

try:
    from casacore.images import image as casaimage

    HAVE_CASACORE = True
except ImportError:
    HAVE_CASACORE = False


def validate_mosaic_quality(
    mosaic_path: str,
    *,
    max_rms_variation: float = 2.0,
    min_coverage_fraction: float = 0.1,
    check_discontinuities: bool = True,
    check_artifacts: bool = True,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate the quality of a completed mosaic.

    Performs checks:
    - RMS noise uniformity across the mosaic
    - Coverage fraction (non-NaN pixels)
    - Discontinuities at tile boundaries
    - Artifacts (negative bowls, extreme values)

    Args:
        mosaic_path: Path to mosaic image
        max_rms_variation: Maximum RMS variation factor (e.g., 2.0 = 2x variation allowed)
        min_coverage_fraction: Minimum fraction of pixels that should be covered
        check_discontinuities: Whether to check for boundary discontinuities
        check_artifacts: Whether to check for imaging artifacts

    Returns:
        (is_valid, issues, metrics_dict) where metrics_dict contains validation metrics
    """
    issues = []
    metrics = {}

    if not HAVE_CASACORE:
        return False, ["casacore.images not available"], metrics

    if not Path(mosaic_path).exists():
        return False, [f"Mosaic not found: {mosaic_path}"], metrics

    try:
        img = casaimage(str(mosaic_path))
        data = img.getdata()

        # Extract 2D image data
        if data.ndim == 2:
            mosaic_data = data
        elif data.ndim == 4:
            mosaic_data = data[0, 0, :, :]
        else:
            mosaic_data = data.squeeze()
            if mosaic_data.ndim > 2:
                mosaic_data = mosaic_data[0, :, :] if mosaic_data.ndim == 3 else mosaic_data

        # Check coverage
        valid_mask = np.isfinite(mosaic_data)
        coverage_fraction = np.sum(valid_mask) / valid_mask.size
        metrics["coverage_fraction"] = coverage_fraction

        if coverage_fraction < min_coverage_fraction:
            issues.append(f"Low coverage: {coverage_fraction:.1%} < {min_coverage_fraction:.1%}")

        # Compute RMS noise statistics
        valid_data = mosaic_data[valid_mask]
        if len(valid_data) > 0:
            rms_noise = float(np.std(valid_data))
            peak_flux = float(np.abs(valid_data).max())
            median_flux = float(np.median(np.abs(valid_data)))

            metrics["rms_noise"] = rms_noise
            metrics["peak_flux"] = peak_flux
            metrics["median_flux"] = median_flux

            if rms_noise > 0:
                dynamic_range = peak_flux / rms_noise
                metrics["dynamic_range"] = dynamic_range

                if dynamic_range < 5.0:
                    issues.append(f"Low dynamic range: {dynamic_range:.1f} < 5.0")

            # Check RMS uniformity by dividing into regions
            if check_discontinuities:
                ny, nx = mosaic_data.shape
                # Divide into 4x4 grid
                n_regions_x = 4
                n_regions_y = 4
                region_rms = []

                for i in range(n_regions_y):
                    for j in range(n_regions_x):
                        y_start = i * ny // n_regions_y
                        y_end = (i + 1) * ny // n_regions_y
                        x_start = j * nx // n_regions_x
                        x_end = (j + 1) * nx // n_regions_x

                        region = mosaic_data[y_start:y_end, x_start:x_end]
                        region_valid = region[np.isfinite(region)]
                        if len(region_valid) > 100:  # Need sufficient pixels
                            region_rms.append(float(np.std(region_valid)))

                if len(region_rms) > 1:
                    median_rms = np.median(region_rms)
                    max_rms = np.max(region_rms)
                    min_rms = np.min(region_rms)

                    metrics["rms_regions"] = {
                        "median": median_rms,
                        "min": min_rms,
                        "max": max_rms,
                        "variation": max_rms / min_rms if min_rms > 0 else float("inf"),
                    }

                    if min_rms > 0:
                        rms_variation = max_rms / min_rms
                        if rms_variation > max_rms_variation:
                            issues.append(
                                f"High RMS variation across mosaic: {rms_variation:.2f}x "
                                f"(max: {max_rms:.3e}, min: {min_rms:.3e})"
                            )

            # Check for artifacts
            if check_artifacts:
                # Check for negative bowls (significant negative pixels)
                negative_pixels = valid_data[valid_data < -5 * rms_noise]
                if len(negative_pixels) > len(valid_data) * 0.01:  # More than 1% negative
                    issues.append(
                        f"Significant negative pixels detected: {len(negative_pixels)} pixels "
                        f"({100 * len(negative_pixels) / len(valid_data):.1f}%)"
                    )

                # Check for extreme outliers
                q99 = np.percentile(np.abs(valid_data), 99)
                outliers = np.abs(valid_data) > 10 * q99
                if np.sum(outliers) > 100:
                    issues.append(
                        f"Extreme outliers detected: {np.sum(outliers)} pixels "
                        f"with flux > 10x 99th percentile"
                    )
        else:
            issues.append("Mosaic contains no valid data (all NaN/Inf)")

        img.close()

    except Exception as e:
        issues.append(f"Failed to validate mosaic: {e}")
        logger.exception(f"Error validating mosaic {mosaic_path}")

    return len(issues) == 0, issues, metrics
