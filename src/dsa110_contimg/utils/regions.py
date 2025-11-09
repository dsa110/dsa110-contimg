"""
Region management utilities for DSA-110 pipeline.

Supports CASA and DS9 region formats, coordinate transformations, and region-based statistics.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

try:
    from astropy.regions import (
        CircleSkyRegion,
        RectangleSkyRegion,
        PolygonSkyRegion,
        Region,
    )
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    HAVE_ASTROPY_REGIONS = True
except ImportError:
    HAVE_ASTROPY_REGIONS = False

LOG = logging.getLogger(__name__)


@dataclass
class RegionData:
    """Region data structure."""
    name: str
    type: str  # 'circle', 'rectangle', 'polygon'
    coordinates: Dict[str, Any]  # JSON-serializable coordinate data
    image_path: str
    created_at: Optional[float] = None
    created_by: Optional[str] = None


def parse_casa_region(region_text: str) -> Optional[RegionData]:
    """Parse CASA region format (.crtf or .rgn).

    Args:
        region_text: CASA region file content or path

    Returns:
        RegionData object or None if parsing fails
    """
    # If it's a file path, read it
    if Path(region_text).exists():
        with open(region_text, 'r') as f:
            region_text = f.read()

    # CASA region format is typically:
    # #CRTFv0
    # circle[[12h34m56.7s, +42d03m12.3s], 0.5arcmin]
    # or
    # circle[[188.5deg, 42.05deg], 0.5arcmin]

    lines = region_text.strip().split('\n')
    regions = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Parse circle
        if line.startswith('circle'):
            # Extract coordinates
            import re
            match = re.search(r'circle\[\[(.*?)\],\s*(.*?)\]', line)
            if match:
                coords_str = match.group(1)
                size_str = match.group(2)

                # Parse coordinates (handle both sexagesimal and decimal)
                coords = coords_str.split(',')
                if len(coords) == 2:
                    ra = parse_coordinate(coords[0].strip())
                    dec = parse_coordinate(coords[1].strip())

                    # Parse size (radius)
                    radius = parse_size(size_str)

                    if ra is not None and dec is not None and radius is not None:
                        regions.append(RegionData(
                            name=f"circle_{len(regions)}",
                            type="circle",
                            coordinates={
                                "ra_deg": ra,
                                "dec_deg": dec,
                                "radius_deg": radius,
                            },
                            image_path="",  # Will be set by caller
                        ))

        # Parse rectangle/box
        elif line.startswith('box') or line.startswith('rectangle'):
            # Similar parsing for box/rectangle
            # Implementation similar to circle
            pass

    return regions[0] if regions else None


def parse_ds9_region(region_text: str) -> Optional[List[RegionData]]:
    """Parse DS9 region format (.reg).

    Args:
        region_text: DS9 region file content or path

    Returns:
        List of RegionData objects
    """
    # If it's a file path, read it
    if Path(region_text).exists():
        with open(region_text, 'r') as f:
            region_text = f.read()

    lines = region_text.strip().split('\n')
    regions = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # DS9 format: circle(188.5,42.05,0.5) # color=red
        # or: circle(12:34:56.7,+42:03:12.3,0.5)
        import re

        # Parse circle
        match = re.search(r'circle\((.*?)\)', line)
        if match:
            coords_str = match.group(1)
            parts = [p.strip() for p in coords_str.split(',')]

            if len(parts) >= 3:
                ra = parse_coordinate(parts[0])
                dec = parse_coordinate(parts[1])
                radius = parse_size(parts[2])

                if ra is not None and dec is not None and radius is not None:
                    regions.append(RegionData(
                        name=f"circle_{len(regions)}",
                        type="circle",
                        coordinates={
                            "ra_deg": ra,
                            "dec_deg": dec,
                            "radius_deg": radius,
                        },
                        image_path="",  # Will be set by caller
                    ))

        # Parse box/rectangle
        match = re.search(r'box\((.*?)\)', line)
        if match:
            coords_str = match.group(1)
            parts = [p.strip() for p in coords_str.split(',')]

            if len(parts) >= 4:
                ra = parse_coordinate(parts[0])
                dec = parse_coordinate(parts[1])
                width = parse_size(parts[2])
                height = parse_size(parts[3])
                angle = float(parts[4]) if len(parts) > 4 else 0.0

                if ra is not None and dec is not None:
                    regions.append(RegionData(
                        name=f"rectangle_{len(regions)}",
                        type="rectangle",
                        coordinates={
                            "ra_deg": ra,
                            "dec_deg": dec,
                            "width_deg": width or 0.01,
                            "height_deg": height or 0.01,
                            "angle_deg": angle,
                        },
                        image_path="",  # Will be set by caller
                    ))

    return regions


def parse_coordinate(coord_str: str) -> Optional[float]:
    """Parse coordinate string to degrees.

    Supports:
    - Decimal degrees: "188.5"
    - Sexagesimal: "12:34:56.7" or "12h34m56.7s"
    - Degrees with units: "188.5deg"
    """
    coord_str = coord_str.strip().lower()

    # Remove units
    coord_str = coord_str.replace('deg', '').replace('d', '')

    # Try decimal first
    try:
        return float(coord_str)
    except ValueError:
        pass

    # Try sexagesimal (HH:MM:SS or HHhMMmSSs)
    import re

    # Handle HH:MM:SS format
    match = re.match(r'([+-]?\d+):(\d+):([\d.]+)', coord_str)
    if match:
        h, m, s = map(float, match.groups())
        return h + m / 60.0 + s / 3600.0

    # Handle HHhMMmSSs format
    match = re.match(r'([+-]?\d+)h(\d+)m([\d.]+)s', coord_str)
    if match:
        h, m, s = map(float, match.groups())
        return h + m / 60.0 + s / 3600.0

    return None


def parse_size(size_str: str) -> Optional[float]:
    """Parse size string to degrees.

    Supports: "0.5arcmin", "30arcsec", "0.5deg", "0.5"
    """
    size_str = size_str.strip().lower()

    # Remove units and convert
    if 'arcmin' in size_str or "'" in size_str:
        size_str = size_str.replace('arcmin', '').replace("'", '')
        try:
            return float(size_str) / 60.0
        except ValueError:
            pass

    if 'arcsec' in size_str or '"' in size_str:
        size_str = size_str.replace('arcsec', '').replace('"', '')
        try:
            return float(size_str) / 3600.0
        except ValueError:
            pass

    if 'deg' in size_str or 'd' in size_str:
        size_str = size_str.replace('deg', '').replace('d', '')

    try:
        return float(size_str)
    except ValueError:
        return None


def region_to_json(region: RegionData) -> Dict[str, Any]:
    """Convert RegionData to JSON-serializable dict."""
    return asdict(region)


def json_to_region(data: Dict[str, Any]) -> RegionData:
    """Convert JSON dict to RegionData."""
    return RegionData(**data)


def calculate_region_statistics(
    image_path: str,
    region: RegionData,
) -> Dict[str, float]:
    """Calculate statistics for pixels within a region.

    Args:
        image_path: Path to FITS image
        region: RegionData object

    Returns:
        Dictionary with statistics: mean, rms, peak, sum, pixel_count
    """
    try:
        from astropy.io import fits
        import numpy as np

        # Load FITS image
        with fits.open(image_path) as hdul:
            data = hdul[0].data
            if data is None:
                return {"error": "No data in FITS file"}

            # Get WCS if available
            header = hdul[0].header
            try:
                from astropy.wcs import WCS
                wcs = WCS(header)
            except (ImportError, ValueError, RuntimeError) as e:
                # WCS creation failed - fallback to None
                LOG.debug("Could not create WCS from header: %s", e)
                wcs = None

            # Create mask for region
            mask = create_region_mask(data.shape, region, wcs, header)

            # Calculate statistics
            masked_data = data[mask]
            if len(masked_data) == 0:
                return {"error": "No pixels in region"}

            return {
                "mean": float(np.mean(masked_data)),
                "rms": float(np.std(masked_data)),
                "peak": float(np.max(masked_data)),
                "min": float(np.min(masked_data)),
                "sum": float(np.sum(masked_data)),
                "pixel_count": int(np.sum(mask)),
            }
    except Exception as e:
        LOG.error(f"Error calculating region statistics: {e}")
        return {"error": str(e)}


def create_region_mask(
    shape: Tuple[int, ...],
    region: RegionData,
    wcs: Optional[Any],
    header: Optional[Any],
) -> Any:
    """Create a boolean mask for pixels within a region.

    Args:
        shape: Image shape (ny, nx)
        region: RegionData object
        wcs: WCS object (optional)
        header: FITS header (optional)

    Returns:
        Boolean numpy array mask
    """
    import numpy as np

    ny, nx = shape[:2]
    mask = np.zeros((ny, nx), dtype=bool)

    # Get region center in pixel coordinates
    if wcs:
        # Use WCS to convert RA/Dec to pixels
        try:
            ra = region.coordinates.get("ra_deg", 0)
            dec = region.coordinates.get("dec_deg", 0)

            # Handle 4D WCS (common in radio astronomy: RA, Dec, Frequency, Stokes)
            if hasattr(wcs, 'naxis') and wcs.naxis == 4:
                # Use all_pix2world for 4D WCS
                # For world2pix, we need to provide all 4 dimensions
                # Use frequency=0, stokes=0 as defaults
                pixel_coords = wcs.all_world2pix([[ra, dec, 0, 0]], 0)[0]
                x, y = float(pixel_coords[0]), float(pixel_coords[1])
            else:
                # Standard 2D WCS
                x, y = wcs.wcs_world2pix([[ra, dec]], 0)[0]
                x, y = float(x), float(y)

            x, y = int(x), int(y)
        except (ValueError, RuntimeError, AttributeError) as e:
            # Fallback to center if WCS conversion fails
            import logging
            logging.warning(
                "Could not convert WCS coordinates: %s, using image center",
                e,
            )
            x, y = nx // 2, ny // 2
    else:
        # Fallback to center
        x, y = nx // 2, ny // 2

    # Create mask based on region type
    if region.type == "circle":
        radius_pix = region.coordinates.get(
            "radius_deg", 0.01) * 3600.0 / get_pixel_scale(header)
        y_coords, x_coords = np.ogrid[:ny, :nx]
        mask = (x_coords - x)**2 + (y_coords - y)**2 <= radius_pix**2

    elif region.type == "rectangle":
        width_pix = region.coordinates.get(
            "width_deg", 0.01) * 3600.0 / get_pixel_scale(header)
        height_pix = region.coordinates.get(
            "height_deg", 0.01) * 3600.0 / get_pixel_scale(header)
        angle = region.coordinates.get("angle_deg", 0.0)

        # Simple rectangular mask (ignoring rotation for now)
        x_min = max(0, int(x - width_pix / 2))
        x_max = min(nx, int(x + width_pix / 2))
        y_min = max(0, int(y - height_pix / 2))
        y_max = min(ny, int(y + height_pix / 2))
        mask[y_min:y_max, x_min:x_max] = True

    elif region.type == "polygon":
        # Polygon mask (simplified - would need proper polygon rasterization)
        # For now, return empty mask
        pass

    return mask


def get_pixel_scale(header: Optional[Any]) -> float:
    """Get pixel scale in arcseconds from FITS header."""
    if header is None:
        return 1.0  # Default

    # Try CDELT or CDELT1/CDELT2
    if 'CDELT1' in header:
        return abs(header['CDELT1']) * 3600.0
    elif 'CDELT' in header:
        return abs(header['CDELT']) * 3600.0

    return 1.0  # Default
