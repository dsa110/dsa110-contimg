"""
Utilities for coordinate system validation and template creation.

Provides functions to:
- Check if tiles overlap with a template coordinate system
- Compute bounding box of multiple tiles
- Create optimal template coordinate systems
"""

# pylint: disable=no-member  # CASA coordinatesystem dynamic methods

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    from casacore.images import image as casaimage
    from casatools import coordsys

    CASA_AVAILABLE = True
except ImportError:
    CASA_AVAILABLE = False
    casaimage = None
    coordsys = None


def get_tile_coordinate_bounds(tile_path: str) -> Optional[dict]:
    """
    Get coordinate bounds (RA/Dec extent) of a tile.

    Args:
        tile_path: Path to CASA image tile

    Returns:
        Dictionary with keys:
        - ra_min, ra_max: RA bounds in radians
        - dec_min, dec_max: Dec bounds in radians
        - center_ra, center_dec: Center coordinates in radians
        - cell_ra, cell_dec: Cell sizes in radians
        - shape: Image shape (nx, ny)
        None if tile cannot be read
    """
    if not CASA_AVAILABLE:
        return None

    try:
        img = casaimage(str(tile_path))
        coordsys_obj = img.coordinates()
        shape = img.shape()

        # Get direction coordinate
        direction_axis = coordsys_obj.findcoordinate("direction")  # pylint: disable=no-member
        if direction_axis < 0:
            del img
            return None

        direction_info = coordsys_obj.direction(direction_axis)  # pylint: disable=no-member
        ref_val = direction_info["crval"]  # Reference value in radians
        ref_pix = direction_info["crpix"]  # Reference pixel
        inc = direction_info["cdelt"]  # Increment in radians

        # Get image dimensions (last two dimensions are typically spatial)
        if len(shape) >= 2:
            ny, nx = shape[-2], shape[-1]
        else:
            del img
            return None

        # Calculate bounds
        # Pixel coordinates: 0 to nx-1, 0 to ny-1
        # World coordinates: ref_val - (ref_pix - 0) * inc to ref_val + (nx - ref_pix) * inc
        ra_min = ref_val[0] - (ref_pix[0] - 0.5) * abs(inc[0])
        ra_max = ref_val[0] + (nx - ref_pix[0] + 0.5) * abs(inc[0])
        dec_min = ref_val[1] - (ref_pix[1] - 0.5) * abs(inc[1])
        dec_max = ref_val[1] + (ny - ref_pix[1] + 0.5) * abs(inc[1])

        center_ra = (ra_min + ra_max) / 2.0
        center_dec = (dec_min + dec_max) / 2.0

        del img

        return {
            "ra_min": ra_min,
            "ra_max": ra_max,
            "dec_min": dec_min,
            "dec_max": dec_max,
            "center_ra": center_ra,
            "center_dec": center_dec,
            "cell_ra": abs(inc[0]),
            "cell_dec": abs(inc[1]),
            "shape": (nx, ny),
        }
    except Exception as e:
        logger.debug(f"Failed to get coordinate bounds for {tile_path}: {e}")
        return None


def compute_tiles_bounding_box(tile_paths: List[str]) -> Optional[dict]:
    """
    Compute bounding box that encompasses all tiles.

    Args:
        tile_paths: List of tile image paths

    Returns:
        Dictionary with keys:
        - ra_min, ra_max: RA bounds in radians
        - dec_min, dec_max: Dec bounds in radians
        - center_ra, center_dec: Center coordinates in radians
        - cell_ra, cell_dec: Recommended cell sizes in radians
        - nx, ny: Recommended image dimensions
        None if no tiles can be read
    """
    if not tile_paths:
        return None

    bounds_list = []
    for tile_path in tile_paths:
        bounds = get_tile_coordinate_bounds(tile_path)
        if bounds:
            bounds_list.append(bounds)

    if not bounds_list:
        return None

    # Compute overall bounding box
    ra_min = min(b["ra_min"] for b in bounds_list)
    ra_max = max(b["ra_max"] for b in bounds_list)
    dec_min = min(b["dec_min"] for b in bounds_list)
    dec_max = max(b["dec_max"] for b in bounds_list)

    center_ra = (ra_min + ra_max) / 2.0
    center_dec = (dec_min + dec_max) / 2.0

    # Use finest cell size (smallest pixel scale)
    cell_ra = min(b["cell_ra"] for b in bounds_list)
    cell_dec = min(b["cell_dec"] for b in bounds_list)

    # Calculate dimensions needed
    nx = int(np.ceil((ra_max - ra_min) / cell_ra)) + 1
    ny = int(np.ceil((dec_max - dec_min) / cell_dec)) + 1

    # Round to reasonable sizes (prefer powers of 2 or multiples of common sizes)
    # Round up to next multiple of 64 for efficiency
    nx = ((nx + 63) // 64) * 64
    ny = ((ny + 63) // 64) * 64

    return {
        "ra_min": ra_min,
        "ra_max": ra_max,
        "dec_min": dec_min,
        "dec_max": dec_max,
        "center_ra": center_ra,
        "center_dec": center_dec,
        "cell_ra": cell_ra,
        "cell_dec": cell_dec,
        "nx": nx,
        "ny": ny,
    }


def check_tile_overlaps_template(
    tile_path: str, template_path: str, margin_pixels: int = 10
) -> Tuple[bool, Optional[str]]:
    """
    Check if a tile overlaps with a template coordinate system.

    Args:
        tile_path: Path to tile image
        template_path: Path to template image
        margin_pixels: Number of pixels margin to require for overlap

    Returns:
        Tuple of (overlaps: bool, reason: Optional[str])
        If overlaps is False, reason explains why
    """
    if not CASA_AVAILABLE:
        return True, None  # Assume overlap if we can't check

    try:
        tile_bounds = get_tile_coordinate_bounds(tile_path)
        template_bounds = get_tile_coordinate_bounds(template_path)

        if not tile_bounds or not template_bounds:
            return True, None  # Can't determine, assume overlap

        # Check if tile bounds overlap with template bounds
        # Account for margin
        margin_ra = margin_pixels * template_bounds["cell_ra"]
        margin_dec = margin_pixels * template_bounds["cell_dec"]

        ra_overlap = (
            tile_bounds["ra_max"] + margin_ra >= template_bounds["ra_min"]
            and tile_bounds["ra_min"] - margin_ra <= template_bounds["ra_max"]
        )
        dec_overlap = (
            tile_bounds["dec_max"] + margin_dec >= template_bounds["dec_min"]
            and tile_bounds["dec_min"] - margin_dec <= template_bounds["dec_max"]
        )

        if ra_overlap and dec_overlap:
            return True, None
        else:
            reason_parts = []
            if not ra_overlap:
                reason_parts.append("RA range")
            if not dec_overlap:
                reason_parts.append("Dec range")
            reason = f"Tile does not overlap template in {', '.join(reason_parts)}"
            return False, reason

    except Exception as e:
        logger.debug(f"Failed to check overlap for {tile_path}: {e}")
        return True, None  # Assume overlap if check fails


def filter_tiles_by_overlap(
    tile_paths: List[str], template_path: str, margin_pixels: int = 10
) -> Tuple[List[str], List[str]]:
    """
    Filter tiles to only include those that overlap with template.

    Args:
        tile_paths: List of tile paths
        template_path: Path to template image
        margin_pixels: Number of pixels margin to require

    Returns:
        Tuple of (overlapping_tiles: List[str], skipped_tiles: List[str])
    """
    overlapping = []
    skipped = []

    for tile_path in tile_paths:
        overlaps, reason = check_tile_overlaps_template(tile_path, template_path, margin_pixels)
        if overlaps:
            overlapping.append(tile_path)
        else:
            skipped.append((tile_path, reason))
            logger.warning(
                f"Tile {Path(tile_path).name} does not overlap template: {reason}. "
                f"Skipping this tile."
            )

    return overlapping, skipped
