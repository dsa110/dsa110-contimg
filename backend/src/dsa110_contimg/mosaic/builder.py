"""
Core mosaic building function.

This is the ONE function that does mosaicking. No strategies,
no configuration sprawl, no flexibility theater.

~150 lines that do all the work.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from dsa110_contimg.utils.decorators import timed

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


@dataclass
class MosaicResult:
    """Result of mosaic build operation.
    
    Attributes:
        output_path: Path to the output FITS file
        n_images: Number of images combined
        median_rms: Median RMS noise across input images (Jy)
        coverage_sq_deg: Sky coverage in square degrees
        weight_map_path: Path to weight map FITS file (optional)
        effective_noise_jy: Estimated effective noise in mosaic (Jy)
    """
    
    output_path: Path
    n_images: int
    median_rms: float
    coverage_sq_deg: float
    weight_map_path: Path | None = None
    effective_noise_jy: float | None = None


@timed("mosaic.build_mosaic")
def build_mosaic(
    image_paths: list[Path],
    output_path: Path,
    alignment_order: int = 3,
    timeout_minutes: int = 30,  # noqa: ARG001 - Reserved for future async support
    write_weight_map: bool = True,
    apply_pb_correction: bool = False,  # noqa: ARG001 - Reserved for DSA-110 PB models
) -> MosaicResult:
    """Build mosaic from list of FITS images.
    
    This is the ONE function that does mosaicking. No strategies,
    no configuration sprawl, no flexibility theater.
    
    Args:
        image_paths: List of input FITS files
        output_path: Where to write output mosaic
        alignment_order: Polynomial order for reprojection (1=fast, 5=accurate)
        timeout_minutes: Maximum execution time (for future async support)
        write_weight_map: If True, write a weight map for uncertainty estimation
        apply_pb_correction: If True, apply primary beam correction (DSA-110 specific).
            Note: For DSA-110, primary beam correction is typically done at imaging
            stage, so this is optional for mosaicking.
        
    Returns:
        MosaicResult with metadata
        
    Raises:
        ValueError: If no images provided or images are invalid
        FileNotFoundError: If input files don't exist
        
    Example:
        >>> result = build_mosaic(
        ...     image_paths=[Path("img1.fits"), Path("img2.fits")],
        ...     output_path=Path("mosaic.fits"),
        ...     alignment_order=3
        ... )
        >>> print(f"Created mosaic with {result.n_images} images")
    """
    if not image_paths:
        raise ValueError("No images provided for mosaicking")
    
    logger.info(f"Building mosaic from {len(image_paths)} images")
    
    # Validate input files exist
    for path in image_paths:
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
    
    # Read input images and WCS
    hdus = []
    for path in image_paths:
        with fits.open(str(path)) as hdulist:
            # Copy data and header to avoid file handle issues
            hdu = fits.PrimaryHDU(
                data=hdulist[0].data.copy(),
                header=hdulist[0].header.copy()
            )
            hdus.append(hdu)
    
    logger.debug(f"Loaded {len(hdus)} FITS images")
    
    # Compute optimal output WCS (covers all inputs)
    output_wcs, output_shape = compute_optimal_wcs(hdus)
    
    logger.debug(f"Output shape: {output_shape}, WCS center: "
                 f"({output_wcs.wcs.crval[0]:.4f}, {output_wcs.wcs.crval[1]:.4f})")
    
    # Reproject all images to common grid
    arrays = []
    footprints = []
    
    try:
        from reproject import reproject_interp
    except ImportError:
        logger.warning("reproject not available, using simple stacking")
        # Fallback: simple mean without reprojection
        return _build_simple_mosaic(hdus, output_path)
    
    for i, hdu in enumerate(hdus):
        logger.debug(f"Reprojecting image {i+1}/{len(hdus)}")
        array, footprint = reproject_interp(
            hdu,
            output_wcs,
            shape_out=output_shape,
            order=_clamp_order(alignment_order),
        )
        arrays.append(array)
        footprints.append(footprint)
    
    # Compute inverse-variance weights
    weights = compute_weights(hdus)
    
    # Combine with weighted average and get weight map
    combined, weight_map = weighted_combine(arrays, weights, footprints, return_weights=True)
    combined_footprint = np.sum(footprints, axis=0) > 0
    
    # Compute statistics
    rms_values = [compute_rms(arr) for arr in arrays]
    median_rms = float(np.median(rms_values))
    
    # Compute effective noise from weight map (propagated uncertainty)
    # effective_noise = 1 / sqrt(sum_weights) where sum_weights is per-pixel
    with np.errstate(invalid='ignore', divide='ignore'):
        effective_noise_map = np.where(weight_map > 0, 1.0 / np.sqrt(weight_map), np.nan)
    effective_noise_jy = float(np.nanmedian(effective_noise_map[combined_footprint]))
    
    # Handle pixel scale as Quantity or plain value
    pixel_scale_raw = output_wcs.proj_plane_pixel_scales()[0]
    if hasattr(pixel_scale_raw, 'value'):
        pixel_scale = float(pixel_scale_raw.value)
    else:
        pixel_scale = float(pixel_scale_raw)
    coverage_sq_deg = float(np.sum(combined_footprint) * pixel_scale**2)
    
    logger.info(f"Mosaic stats: median_rms={median_rms:.6f} Jy, "
                f"effective_noise={effective_noise_jy:.6f} Jy, "
                f"coverage={coverage_sq_deg:.4f} sq deg")
    
    # Write output FITS
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    output_header = output_wcs.to_header()
    output_header['NIMAGES'] = (len(image_paths), 'Number of images combined')
    output_header['MEDRMS'] = (median_rms, 'Median RMS noise (Jy)')
    output_header['EFFNOISE'] = (effective_noise_jy, 'Effective noise from weights (Jy)')
    output_header['COVERAGE'] = (coverage_sq_deg, 'Sky coverage (sq deg)')
    output_header['BUNIT'] = 'Jy/beam'
    
    output_hdu = fits.PrimaryHDU(data=combined, header=output_header)
    output_hdu.writeto(str(output_path), overwrite=True)
    
    logger.info(f"Wrote mosaic to {output_path}")
    
    # Optionally write weight map for uncertainty propagation
    weight_map_path = None
    if write_weight_map:
        weight_map_path = output_path.with_suffix('.weights.fits')
        weight_header = output_wcs.to_header()
        weight_header['BUNIT'] = '1/Jy^2'
        weight_header['COMMENT'] = 'Inverse-variance weight map for uncertainty estimation'
        weight_header['COMMENT'] = 'Noise = 1/sqrt(weight) at each pixel'
        weight_hdu = fits.PrimaryHDU(data=weight_map.astype(np.float32), header=weight_header)
        weight_hdu.writeto(str(weight_map_path), overwrite=True)
        logger.info(f"Wrote weight map to {weight_map_path}")
    
    return MosaicResult(
        output_path=output_path,
        n_images=len(image_paths),
        median_rms=median_rms,
        coverage_sq_deg=coverage_sq_deg,
        weight_map_path=weight_map_path,
        effective_noise_jy=effective_noise_jy,
    )


def compute_optimal_wcs(hdus: list[fits.PrimaryHDU]) -> tuple[WCS, tuple[int, int]]:
    """Compute WCS that covers all input images.
    
    Args:
        hdus: List of FITS HDUs with valid WCS
        
    Returns:
        Tuple of (output_wcs, (ny, nx)) shape
    """
    # Find min/max RA/Dec across all images
    all_ra = []
    all_dec = []
    pixel_scales = []
    
    for hdu in hdus:
        wcs = WCS(hdu.header, naxis=2)
        ny, nx = hdu.data.shape[-2:]
        
        # Get corner coordinates
        corners_x = [0, nx-1, nx-1, 0]
        corners_y = [0, 0, ny-1, ny-1]
        
        coords = wcs.pixel_to_world(corners_x, corners_y)
        all_ra.extend([c.ra.deg for c in coords])
        all_dec.extend([c.dec.deg for c in coords])
        
        # Track pixel scales (convert from Quantity to float if needed)
        scales = wcs.proj_plane_pixel_scales()
        # Handle both Quantity and plain array returns
        if hasattr(scales[0], 'value'):
            pixel_scales.append(float(np.mean([s.value for s in scales])))
        else:
            pixel_scales.append(float(np.mean(scales)))
    
    # Compute bounding box
    ra_min, ra_max = min(all_ra), max(all_ra)
    dec_min, dec_max = min(all_dec), max(all_dec)
    
    # Handle RA wrap-around near 0/360
    if ra_max - ra_min > 180:
        # Coordinates span the 0/360 boundary
        ra_pos = [r for r in all_ra if r > 180]
        ra_neg = [r for r in all_ra if r <= 180]
        ra_min = min(ra_pos) if ra_pos else 0
        ra_max = max(ra_neg) + 360 if ra_neg else 360
    
    # Use median pixel scale
    pixel_scale = np.median(pixel_scales)
    
    # Compute output grid size
    ra_span = ra_max - ra_min
    dec_span = dec_max - dec_min
    
    nx = int(np.ceil(ra_span / pixel_scale)) + 10  # Add margin
    ny = int(np.ceil(dec_span / pixel_scale)) + 10
    
    # Limit size to prevent memory issues
    max_size = 8192
    if nx > max_size or ny > max_size:
        scale_factor = max(nx, ny) / max_size
        nx = int(nx / scale_factor)
        ny = int(ny / scale_factor)
        pixel_scale *= scale_factor
    
    # Create output WCS
    output_wcs = WCS(naxis=2)
    output_wcs.wcs.crpix = [nx / 2, ny / 2]
    output_wcs.wcs.crval = [(ra_min + ra_max) / 2, (dec_min + dec_max) / 2]
    output_wcs.wcs.cdelt = [-pixel_scale, pixel_scale]  # RA increases left
    output_wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    output_wcs.array_shape = (ny, nx)
    
    return output_wcs, (ny, nx)


def compute_weights(hdus: list[fits.PrimaryHDU]) -> NDArray[np.floating]:
    """Compute inverse-variance weights for images.
    
    Args:
        hdus: List of FITS HDUs
        
    Returns:
        Array of weights (normalized to sum to 1)
    """
    weights = []
    for hdu in hdus:
        rms = compute_rms(hdu.data)
        # Inverse variance weighting
        weight = 1.0 / (rms**2) if rms > 0 else 0.0
        weights.append(weight)
    
    weights = np.array(weights)
    
    # Normalize
    total = np.sum(weights)
    if total > 0:
        weights /= total
    else:
        # Equal weights if all RMS are zero
        weights = np.ones(len(hdus)) / len(hdus)
    
    return weights


def weighted_combine(
    arrays: list[NDArray],
    weights: NDArray[np.floating],
    footprints: list[NDArray],
    return_weights: bool = False,
) -> NDArray[np.floating] | tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Combine reprojected arrays with inverse-variance weighting.
    
    Args:
        arrays: List of reprojected data arrays
        weights: Per-image weights (normalized)
        footprints: Per-image footprint masks
        return_weights: If True, also return the summed weight map
        
    Returns:
        Combined mosaic array, or tuple of (combined, weight_map) if return_weights=True
        
    Note:
        The weight_map can be used for uncertainty propagation:
        - Per-pixel noise = 1 / sqrt(weight_map)
        - This assumes the input weights are inverse-variance (1/sigma^2)
    """
    # Stack arrays
    stack = np.array(arrays)
    fp_stack = np.array(footprints)
    
    # Apply footprint mask
    stack = np.where(fp_stack, stack, np.nan)
    
    # Weighted mean, ignoring NaN
    weights_3d = weights[:, np.newaxis, np.newaxis] * fp_stack
    
    with np.errstate(invalid='ignore', divide='ignore'):
        sum_weights = np.nansum(weights_3d, axis=0)
        combined = np.nansum(stack * weights_3d, axis=0) / sum_weights
    
    # Replace NaN with 0 in regions with no coverage
    combined = np.nan_to_num(combined, nan=0.0)
    sum_weights = np.nan_to_num(sum_weights, nan=0.0)
    
    if return_weights:
        return combined, sum_weights
    return combined


def compute_rms(data: NDArray) -> float:
    """Compute RMS noise in image.
    
    Uses median absolute deviation (MAD) for robust noise estimate.
    
    Args:
        data: Image data array
        
    Returns:
        RMS noise estimate
    """
    finite_data = data[np.isfinite(data)]
    if len(finite_data) == 0:
        return 0.0
    
    # MAD-based robust RMS
    median = np.median(finite_data)
    mad = np.median(np.abs(finite_data - median))
    
    # Convert MAD to standard deviation (for Gaussian)
    return float(mad * 1.4826)


def _clamp_order(order: int) -> str:
    """Convert alignment order to reproject interpolation order.
    
    Args:
        order: Alignment order (1-5)
        
    Returns:
        Interpolation order string for reproject
    """
    if order <= 1:
        return "nearest-neighbor"
    elif order <= 3:
        return "bilinear"
    else:
        return "biquadratic"


def _build_simple_mosaic(
    hdus: list[fits.PrimaryHDU],
    output_path: Path,
) -> MosaicResult:
    """Fallback simple mosaic without reprojection.
    
    Just takes the first image as-is. Used when reproject is not available.
    """
    logger.warning("Building simple mosaic (no reprojection)")
    
    # Just use the first image
    hdu = hdus[0]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rms = compute_rms(hdu.data)
    wcs = WCS(hdu.header, naxis=2)
    pixel_scale_raw = wcs.proj_plane_pixel_scales()
    if hasattr(pixel_scale_raw[0], 'value'):
        pixel_scale = float(np.mean([s.value for s in pixel_scale_raw]))
    else:
        pixel_scale = float(np.mean(pixel_scale_raw))
    coverage = hdu.data.shape[0] * hdu.data.shape[1] * pixel_scale**2
    
    # Add metadata headers (same as full mosaic)
    hdu.header['NIMAGES'] = (len(hdus), 'Number of images combined')
    hdu.header['MEDRMS'] = (rms, 'Median RMS noise (Jy)')
    hdu.header['COVERAGE'] = (coverage, 'Sky coverage (sq deg)')
    hdu.header['BUNIT'] = 'Jy/beam'
    
    hdu.writeto(str(output_path), overwrite=True)
    
    return MosaicResult(
        output_path=output_path,
        n_images=len(hdus),
        median_rms=rms,
        coverage_sq_deg=coverage,
    )
