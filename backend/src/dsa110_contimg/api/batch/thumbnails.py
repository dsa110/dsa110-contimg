"""
Image thumbnail generation utilities.

This module provides functions for generating PNG thumbnails from
CASA images for quick preview and visualization.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def generate_image_thumbnail(
    image_path: str,
    output_path: Optional[str] = None,
    size: int = 512,
) -> Optional[str]:
    """Generate a PNG thumbnail of a CASA image.
    
    Creates a grayscale PNG thumbnail from a CASA image by:
    1. Extracting the first Stokes/channel plane
    2. Normalizing the data using percentile clipping
    3. Resizing to the specified dimensions
    4. Saving as a PNG file
    
    Args:
        image_path: Path to the CASA image
        output_path: Output path for the thumbnail (default: image_path with .thumb.png suffix)
        size: Maximum dimension for the thumbnail (default: 512 pixels)
        
    Returns:
        Path to the generated thumbnail, or None if generation failed
    """
    try:
        import numpy as np
        from casatools import image
        from PIL import Image

        ia = image()
        ia.open(image_path)

        # Get image data (first Stokes, first channel)
        data = ia.getchunk()
        if data.ndim >= 2:
            img_data = (
                data[:, :, 0, 0] if data.ndim == 4
                else data[:, :, 0] if data.ndim == 3
                else data
            )
        else:
            ia.close()
            logger.warning(f"Image {image_path} has unsupported dimensions: {data.ndim}")
            return None

        ia.close()

        # Normalize and convert to 8-bit
        normalized = _normalize_image_data(img_data)
        if normalized is None:
            return None
            
        img_8bit = (normalized * 255).astype(np.uint8)

        # Create PIL image and resize
        pil_img = Image.fromarray(img_8bit, mode="L")
        pil_img.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Save thumbnail
        if output_path is None:
            output_path = str(Path(image_path).with_suffix(".thumb.png"))

        pil_img.save(output_path, "PNG")
        logger.debug(f"Generated thumbnail: {output_path}")
        return output_path
        
    except ImportError as e:
        logger.error(f"Missing dependency for thumbnail generation: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {image_path}: {e}")
        return None


def _normalize_image_data(img_data) -> Optional["numpy.ndarray"]:
    """Normalize image data to [0, 1] range using percentile clipping.
    
    Args:
        img_data: 2D numpy array of image data
        
    Returns:
        Normalized array, or None if normalization failed
    """
    import numpy as np
    
    valid_data = img_data[np.isfinite(img_data)]
    if valid_data.size == 0:
        logger.warning("No valid (finite) data in image")
        return None

    # Use percentile clipping for robust scaling
    vmin = np.percentile(valid_data, 1)
    vmax = np.percentile(valid_data, 99.5)
    
    if vmax <= vmin:
        logger.warning("Image has no dynamic range")
        return None

    normalized = np.clip((img_data - vmin) / (vmax - vmin), 0, 1)
    return normalized


def generate_thumbnails_for_directory(
    directory: str,
    pattern: str = "*.image",
    size: int = 512,
    overwrite: bool = False,
) -> dict:
    """Generate thumbnails for all images in a directory.
    
    Args:
        directory: Path to directory containing CASA images
        pattern: Glob pattern for matching images (default: "*.image")
        size: Maximum thumbnail dimension (default: 512)
        overwrite: Whether to overwrite existing thumbnails (default: False)
        
    Returns:
        Dictionary mapping image paths to thumbnail paths (or None for failures)
    """
    results = {}
    dir_path = Path(directory)
    
    if not dir_path.is_dir():
        logger.error(f"Not a directory: {directory}")
        return results
        
    for image_path in dir_path.glob(pattern):
        output_path = image_path.with_suffix(".thumb.png")
        
        if output_path.exists() and not overwrite:
            logger.debug(f"Thumbnail already exists: {output_path}")
            results[str(image_path)] = str(output_path)
            continue
            
        thumbnail = generate_image_thumbnail(str(image_path), str(output_path), size)
        results[str(image_path)] = thumbnail
        
    return results
