"""Generate all-sky radio map in Aitoff projection for pointing visualization.

This module provides utilities to generate or load an all-sky radio map
(e.g., Haslam 408 MHz map) reprojected to Aitoff projection for use
as a background in the pointing visualization.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def generate_synthetic_radio_sky_map(
    output_path: Path,
    width: int = 720,
    height: int = 360,
    galactic_plane_brightness: float = 0.8,
    base_brightness: float = 0.2,
) -> Path:
    """Generate a synthetic all-sky radio map in Aitoff projection.
    
    Creates a simple synthetic map showing:
    - Galactic plane (brighter band)
    - Galactic center (brightest region)
    - General sky background
    
    Args:
        output_path: Path where the image will be saved
        width: Image width in pixels (default: 720, matches Aitoff x range -180 to 180)
        height: Image height in pixels (default: 360, matches Aitoff y range -90 to 90)
        galactic_plane_brightness: Brightness of galactic plane (0-1)
        base_brightness: Base sky brightness (0-1)
        
    Returns:
        Path to the generated image file
    """
    # Create coordinate arrays (vectorized for performance)
    y_coords, x_coords = np.mgrid[0:height, 0:width]
    
    # Convert pixel coordinates to Aitoff coordinates
    # Note: Image y=0 (top row) maps to Aitoff y=90, image y=height (bottom row) maps to Aitoff y=-90
    # For Plotly compatibility, we'll flip vertically so pixel y=0 maps to Aitoff y=-90
    aitoff_x = (x_coords / width) * 360 - 180
    aitoff_y = -90 + (y_coords / height) * 180  # Flipped: now pixel y=0 → Aitoff y=-90, pixel y=height → Aitoff y=90
    
    # Convert to RA/Dec (approximate - for synthetic map)
    ra_deg = aitoff_x + 180  # Approximate conversion
    dec_deg = aitoff_y
    
    # Galactic center is at RA ~266°, Dec ~-29°
    gal_center_ra = 266.0
    gal_center_dec = -29.0
    
    # Distance from galactic center (handle RA wrap-around)
    ra_diff = (ra_deg - gal_center_ra + 180) % 360 - 180
    dec_diff = dec_deg - gal_center_dec
    dist_from_center = np.sqrt(ra_diff**2 + dec_diff**2)
    
    # Distance from galactic plane (simplified as a band)
    # Galactic plane is roughly at Dec ~ -29° with some RA variation
    plane_dec = -29.0 + 20 * np.sin(np.radians(ra_deg))
    dist_from_plane = np.abs(dec_deg - plane_dec)
    
    # Calculate brightness
    # Galactic center is brightest
    center_brightness = np.maximum(0, 1.0 - dist_from_center / 80.0)
    # Galactic plane is bright (wider band for visibility)
    plane_brightness = np.maximum(0, galactic_plane_brightness - dist_from_plane / 40.0)
    
    # Combine brightnesses with stronger weighting for visibility
    brightness = base_brightness + center_brightness * 0.6 + plane_brightness * 0.4
    brightness = np.minimum(1.0, brightness)
    
    # Enhance contrast for better visibility
    brightness = np.power(brightness, 0.8)  # Gamma correction for better visibility
    
    # Convert to RGB (grayscale with slight blue tint for radio emission)
    gray = (brightness * 255).astype(np.uint8)
    img_array = np.zeros((height, width, 3), dtype=np.uint8)
    img_array[:, :, 0] = gray  # Red channel
    img_array[:, :, 1] = (gray * 0.9).astype(np.uint8)  # Green channel
    img_array[:, :, 2] = (gray * 0.95).astype(np.uint8)  # Blue channel
    
    # Save as PNG
    img = Image.fromarray(img_array)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    logger.info(f"Generated synthetic radio sky map: {output_path}")
    
    return output_path


def load_haslam_408mhz_map(
    fits_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    width: int = 720,
    height: int = 360,
) -> Optional[Path]:
    """Load and reproject Haslam 408 MHz all-sky map to Aitoff projection.
    
    The Haslam map is a standard all-sky radio map at 408 MHz. This function
    attempts to load it from a FITS file and reproject to Aitoff.
    
    Args:
        fits_path: Path to Haslam 408 MHz FITS file (if None, searches common locations)
        output_path: Path where reprojected image will be saved
        width: Output image width
        height: Output image height
        
    Returns:
        Path to reprojected image, or None if FITS file not found
    """
    try:
        from astropy.io import fits
        from astropy.wcs import WCS
        from reproject import reproject_to_aitoff
    except ImportError:
        logger.warning(
            "reproject package not available. Install with: pip install reproject"
        )
        return None
    
    # Try to find Haslam map if path not provided
    if fits_path is None:
        common_paths = [
            Path("/data/dsa110-contimg/data/haslam_408MHz.fits"),
            Path("data/haslam_408MHz.fits"),
            Path(os.getenv("HASLAM_408MHZ_PATH", "")),
        ]
        for p in common_paths:
            if p.exists():
                fits_path = p
                break
        
        if fits_path is None:
            logger.warning(
                "Haslam 408 MHz FITS file not found. "
                "You can download it from: "
                "https://lambda.gsfc.nasa.gov/product/foreground/haslam_408.cfm"
            )
            return None
    
    if not fits_path.exists():
        logger.warning(f"Haslam FITS file not found: {fits_path}")
        return None
    
    try:
        # Load FITS file
        with fits.open(fits_path) as hdul:
            data = hdul[0].data
            wcs = WCS(hdul[0].header)
        
        # Reproject to Aitoff
        # This is a simplified version - full reprojection requires more setup
        logger.info("Reprojecting Haslam map to Aitoff projection...")
        # Note: Full reprojection implementation would go here
        # For now, return None to indicate it's not fully implemented
        logger.warning("Full Haslam reprojection not yet implemented")
        return None
        
    except Exception as e:
        logger.error(f"Failed to load/reproject Haslam map: {e}")
        return None


def get_sky_map_path(
    map_type: str = "synthetic",
    output_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Get path to all-sky radio map, generating if necessary.
    
    Args:
        map_type: Type of map ("synthetic" or "haslam")
        output_dir: Directory where map should be stored
        
    Returns:
        Path to sky map image, or None if unavailable
    """
    if output_dir is None:
        # Use absolute path from project root, not relative to current working directory
        project_root = Path(__file__).parent.parent.parent.parent
        state_dir = Path(os.getenv("PIPELINE_STATE_DIR", str(project_root / "state")))
        output_dir = state_dir / "pointing"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if map_type == "synthetic":
        output_path = output_dir / "synthetic_radio_sky_map.png"
        if not output_path.exists():
            generate_synthetic_radio_sky_map(output_path)
        return output_path
    elif map_type == "haslam":
        output_path = output_dir / "haslam_408mhz_aitoff.png"
        result = load_haslam_408mhz_map(output_path=output_path)
        if result is None:
            # Fall back to synthetic if Haslam unavailable
            logger.info("Falling back to synthetic map")
            return get_sky_map_path("synthetic", output_dir)
        return result
    else:
        logger.warning(f"Unknown map type: {map_type}")
        return None

