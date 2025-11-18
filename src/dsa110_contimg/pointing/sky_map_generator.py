"""Generate all-sky radio map in Aitoff projection for pointing visualization.

This module provides utilities to generate or load an all-sky radio map
(e.g., Haslam 408 MHz map) reprojected to Aitoff projection for use
as a background in the pointing visualization.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def get_or_generate_gsm_cache(
    frequency_mhz: float = 1400.0,
    force_regenerate: bool = False,
) -> np.ndarray:
    """Get cached GSM numpy array or generate if not exists.

    This function caches the Global Sky Model as a numpy array for fast loading.
    The GSM generation takes 20-30 seconds, but loading from numpy is instant.

    Args:
        frequency_mhz: Frequency in MHz (default: 1400.0)
        force_regenerate: Force regeneration even if cache exists

    Returns:
        HEALPix sky map numpy array (log10 scale, masked for <= 0 values)
    """
    state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
    cache_dir = state_dir / "pointing" / "gsm_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_file = cache_dir / f"gsm_{int(frequency_mhz)}mhz.npy"

    # Check if cache exists and is valid
    if not force_regenerate and cache_file.exists():
        logger.info(f"Loading cached GSM from {cache_file}")
        try:
            log_sky = np.load(cache_file)
            logger.info(f"Loaded GSM cache: shape={log_sky.shape}, dtype={log_sky.dtype}")
            return log_sky
        except Exception as e:
            logger.warning(f"Failed to load GSM cache: {e}. Regenerating...")

    # Generate GSM
    logger.info(f"Generating GSM at {frequency_mhz} MHz (this may take 20-30 seconds)...")
    import pygdsm

    gsm = pygdsm.GlobalSkyModel16()
    sky_map = gsm.generate(frequency_mhz)

    # Convert to log scale, mask invalid pixels
    log_sky = np.full_like(sky_map, np.nan, dtype=float)
    mask = sky_map > 0
    log_sky[mask] = np.log10(sky_map[mask])

    # Cache for future use
    np.save(cache_file, log_sky)
    logger.info(f"Cached GSM to {cache_file} (size: {cache_file.stat().st_size / 1024:.1f} KB)")

    return log_sky


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
    aitoff_y = (
        -90 + (y_coords / height) * 180
    )  # Flipped: now pixel y=0 → Aitoff y=-90, pixel y=height → Aitoff y=90

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
    # Gamma correction for better visibility
    brightness = np.power(brightness, 0.8)

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
        logger.warning("reproject package not available. Install with: pip install reproject")
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
            hdul[0].data  # pylint: disable=no-member
            WCS(hdul[0].header)  # pylint: disable=no-member

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


def get_sky_map_data_path(
    frequency_mhz: float = 1400.0,
    resolution: int = 90,
    map_type: str = "gsm",
    output_dir: Optional[Path] = None,
    file_format: str = "fits",
) -> Path:
    """Get path to cached sky map data file.

    Args:
        frequency_mhz: Frequency in MHz
        resolution: Grid resolution
        map_type: Type of map ("gsm" or "synthetic")
        output_dir: Directory where cache should be stored
        file_format: File format ("fits", "png", or "json")

    Returns:
        Path to cached file
    """
    if output_dir is None:
        # Use absolute path from project root, not relative to current working directory
        project_root = Path(__file__).parent.parent.parent.parent
        state_dir = Path(os.getenv("PIPELINE_STATE_DIR", str(project_root / "state")))
        output_dir = state_dir / "pointing" / "data"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create cache filename based on parameters
    if file_format == "fits":
        cache_filename = f"sky_map_{map_type}_{frequency_mhz:.1f}mhz_res{resolution}.fits"
    elif file_format == "png":
        cache_filename = f"sky_map_{map_type}_{frequency_mhz:.1f}mhz_res{resolution}.png"
    else:  # json
        cache_filename = f"sky_map_{map_type}_{frequency_mhz:.1f}mhz_res{resolution}.json"
    return output_dir / cache_filename


def load_sky_map_from_fits(fits_path: Path) -> Optional[Dict[str, List]]:
    """Load sky map data from FITS file.

    Args:
        fits_path: Path to FITS file

    Returns:
        Dictionary with keys 'x', 'y', 'z' or None if loading fails
    """
    try:
        from astropy.io import fits
    except ImportError:
        logger.warning("astropy not available, cannot load FITS file")
        return None

    try:
        with fits.open(fits_path) as hdul:
            # Read data from primary HDU
            data = hdul[0].data
            header = hdul[0].header

            # Extract coordinate arrays from header or calculate
            if "NAXIS1" in header and "NAXIS2" in header:
                width = header["NAXIS1"]
                height = header["NAXIS2"]
            else:
                # Infer from data shape
                if len(data.shape) == 2:
                    height, width = data.shape
                else:
                    logger.warning(f"Unexpected FITS data shape: {data.shape}")
                    return None

            # Get coordinate ranges from header (Aitoff projection standard ranges)
            # Aitoff x: -180 to 180, y: -90 to 90
            x_min = header.get("XMIN", -180.0)
            x_max = header.get("XMAX", 180.0)
            y_min = header.get("YMIN", -90.0)
            y_max = header.get("YMAX", 90.0)

            # Generate coordinate arrays
            if width > 1:
                x_coords = [x_min + (x_max - x_min) * j / (width - 1) for j in range(width)]
            else:
                x_coords = [x_min]

            if height > 1:
                y_coords = [y_min + (y_max - y_min) * i / (height - 1) for i in range(height)]
            else:
                y_coords = [y_min]

            # Convert data to list of lists (normalize if needed)
            z_values = data.tolist()

            return {"x": x_coords, "y": y_coords, "z": z_values}
    except Exception as e:
        logger.warning(f"Failed to load FITS file {fits_path}: {e}")
        return None


def save_sky_map_to_fits(
    data: Dict[str, List], fits_path: Path, frequency_mhz: float = 1400.0
) -> bool:
    """Save sky map data to FITS file.

    Args:
        data: Dictionary with keys 'x', 'y', 'z'
        fits_path: Path where FITS file should be saved
        frequency_mhz: Frequency in MHz (for header)

    Returns:
        True if successful, False otherwise
    """
    try:
        from astropy.io import fits
    except ImportError:
        logger.warning("astropy not available, cannot save FITS file")
        return False

    try:
        # Convert z values to numpy array
        z_array = np.array(data["z"])

        # Create FITS header with metadata
        header = fits.Header()
        header["FREQ"] = (frequency_mhz, "Frequency in MHz")
        header["NAXIS"] = 2
        header["NAXIS1"] = len(data["x"])
        header["NAXIS2"] = len(data["y"])
        header["XMIN"] = (min(data["x"]), "Minimum Aitoff X coordinate")
        header["XMAX"] = (max(data["x"]), "Maximum Aitoff X coordinate")
        header["YMIN"] = (min(data["y"]), "Minimum Aitoff Y coordinate")
        header["YMAX"] = (max(data["y"]), "Maximum Aitoff Y coordinate")
        header["CTYPE1"] = "AITOFF_X"
        header["CTYPE2"] = "AITOFF_Y"
        header["COMMENT"] = "GSM sky map in Aitoff projection"

        # Create primary HDU
        hdu = fits.PrimaryHDU(data=z_array, header=header)

        # Write to file
        hdu.writeto(fits_path, overwrite=True)
        logger.info(f"Saved GSM sky map to FITS: {fits_path}")
        return True
    except Exception as e:
        logger.warning(f"Failed to save FITS file {fits_path}: {e}")
        return False


def save_sky_map_to_png(data: Dict[str, List], png_path: Path) -> bool:
    """Save sky map data as PNG image.

    Args:
        data: Dictionary with keys 'x', 'y', 'z'
        png_path: Path where PNG file should be saved

    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert z values to numpy array and normalize to 0-255
        z_array = np.array(data["z"])
        z_min = np.min(z_array)
        z_max = np.max(z_array)
        if z_max > z_min:
            normalized = ((z_array - z_min) / (z_max - z_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(z_array, dtype=np.uint8)

        # Create image (height x width)
        img = Image.fromarray(normalized, mode="L")
        img.save(png_path)
        logger.info(f"Saved GSM sky map to PNG: {png_path}")
        return True
    except Exception as e:
        logger.warning(f"Failed to save PNG file {png_path}: {e}")
        return False


def generate_gsm_sky_map_data(
    frequency_mhz: float = 1400.0,
    resolution: int = 90,
    use_cache: bool = True,
) -> Dict[str, List]:
    """Generate Global Sky Model (GSM) sky map data in Aitoff projection.

    Uses pygdsm to generate a realistic all-sky radio map and projects it
    to Aitoff coordinates for use in the pointing visualization heatmap.
    Results are cached to disk (FITS, PNG, and JSON) to avoid regenerating.

    Args:
        frequency_mhz: Frequency in MHz (default: 1400 MHz / 1.4 GHz)
        resolution: Grid resolution (default: 90, gives 91x181 grid)
        use_cache: If True, use cached data if available (default: True)

    Returns:
        Dictionary with keys 'x', 'y', 'z' containing coordinate arrays and brightness values
    """
    # Check cache first (try FITS, then PNG, then JSON)
    if use_cache:
        # Try FITS first (preserves data best)
        fits_path = get_sky_map_data_path(
            frequency_mhz=frequency_mhz,
            resolution=resolution,
            map_type="gsm",
            file_format="fits",
        )
        if fits_path.exists():
            logger.info(f"Loading cached GSM sky map from FITS: {fits_path}")
            data = load_sky_map_from_fits(fits_path)
            if data is not None:
                return data

        # Try JSON as fallback
        json_path = get_sky_map_data_path(
            frequency_mhz=frequency_mhz,
            resolution=resolution,
            map_type="gsm",
            file_format="json",
        )
        if json_path.exists():
            try:
                logger.info(f"Loading cached GSM sky map from JSON: {json_path}")
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # If we loaded from JSON but FITS doesn't exist, save to FITS/PNG now
                if not fits_path.exists():
                    logger.info("FITS file not found, converting JSON cache to FITS/PNG...")
                    save_sky_map_to_fits(data, fits_path, frequency_mhz=frequency_mhz)
                    png_path = get_sky_map_data_path(
                        frequency_mhz=frequency_mhz,
                        resolution=resolution,
                        map_type="gsm",
                        file_format="png",
                    )
                    save_sky_map_to_png(data, png_path)

                return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load JSON cache, regenerating: {e}")

    try:
        import healpy as hp
        import pygdsm
    except ImportError as e:
        logger.warning(
            f"pygdsm or healpy not available: {e}. " "Install with: pip install pygdsm healpy"
        )
        # Fall back to synthetic data
        return generate_synthetic_sky_map_data(resolution=resolution, use_cache=use_cache)

    try:
        # Generate GSM sky map at specified frequency
        logger.info(f"Generating GSM sky map at {frequency_mhz} MHz...")
        gsm = pygdsm.GlobalSkyModel16()
        sky_map = gsm.generate(frequency_mhz)

        # Get HEALPix resolution
        nside = hp.get_nside(sky_map)
        hp.nside2npix(nside)

        # Convert to log scale for better visualization
        # Add small value to avoid log(0)
        log_sky_map = np.log10(sky_map + 1e-10)

        # Normalize to 0-1 range for heatmap
        min_val = np.min(log_sky_map)
        max_val = np.max(log_sky_map)
        normalized_map = (
            (log_sky_map - min_val) / (max_val - min_val) if max_val > min_val else log_sky_map
        )

        # Create Aitoff coordinate grid
        x_step = 360.0 / resolution
        y_step = 180.0 / resolution

        x_coords: List[float] = []
        y_coords: List[float] = []
        z_values: List[List[float]] = []

        for i in range(resolution + 1):
            aitoff_y = -90.0 + i * y_step
            y_coords.append(aitoff_y)
            row: List[float] = []

            for j in range(resolution + 1):
                aitoff_x = -180.0 + j * x_step
                if i == 0:
                    x_coords.append(aitoff_x)

                # Convert Aitoff coordinates to RA/Dec (approximate)
                # For Aitoff: x = longitude (RA-180), y = latitude (Dec)
                ra_deg = aitoff_x + 180.0
                dec_deg = aitoff_y

                # Convert RA/Dec to HEALPix pixel index
                # HEALPix uses theta (colatitude) and phi (longitude)
                theta = np.radians(90.0 - dec_deg)  # Colatitude
                phi = np.radians(ra_deg)  # Longitude

                # Get pixel index
                pix_idx = hp.ang2pix(nside, theta, phi)

                # Get brightness value from GSM map
                brightness = float(normalized_map[pix_idx])
                row.append(brightness)

            z_values.append(row)

        logger.info(f"Generated GSM sky map data: {len(x_coords)}x{len(y_coords)} grid")
        result = {"x": x_coords, "y": y_coords, "z": z_values}

        # Save to cache in multiple formats
        if use_cache:
            # Save as FITS (best for data preservation)
            fits_path = get_sky_map_data_path(
                frequency_mhz=frequency_mhz,
                resolution=resolution,
                map_type="gsm",
                file_format="fits",
            )
            save_sky_map_to_fits(result, fits_path, frequency_mhz=frequency_mhz)

            # Save as PNG (quick preview/fallback)
            png_path = get_sky_map_data_path(
                frequency_mhz=frequency_mhz,
                resolution=resolution,
                map_type="gsm",
                file_format="png",
            )
            save_sky_map_to_png(result, png_path)

            # Save as JSON (fallback if FITS not available)
            json_path = get_sky_map_data_path(
                frequency_mhz=frequency_mhz,
                resolution=resolution,
                map_type="gsm",
                file_format="json",
            )
            try:
                logger.info(f"Saving GSM sky map data to JSON: {json_path}")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(result, f)
            except IOError as e:
                logger.warning(f"Failed to save JSON cache: {e}")

        return result

    except Exception as e:
        logger.error(f"Failed to generate GSM sky map: {e}")
        # Fall back to synthetic data
        return generate_synthetic_sky_map_data(resolution=resolution, use_cache=use_cache)


def generate_synthetic_sky_map_data(
    resolution: int = 90,
    use_cache: bool = True,
) -> Dict[str, List]:
    """Generate synthetic sky map data in Aitoff projection.

    Fallback function that generates synthetic data matching the synthetic image generator.
    Results are cached to disk to avoid regenerating on every request.

    Args:
        resolution: Grid resolution
        use_cache: If True, use cached data if available (default: True)

    Returns:
        Dictionary with keys 'x', 'y', 'z' containing coordinate arrays and brightness values
    """
    # Check cache first
    if use_cache:
        cache_path = get_sky_map_data_path(
            frequency_mhz=0.0,  # Synthetic doesn't use frequency
            resolution=resolution,
            map_type="synthetic",
        )
        if cache_path.exists():
            try:
                logger.info(f"Loading cached synthetic sky map data from {cache_path}")
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache, regenerating: {e}")
    x_step = 360.0 / resolution
    y_step = 180.0 / resolution

    x_coords: List[float] = []
    y_coords: List[float] = []
    z_values: List[List[float]] = []

    for i in range(resolution + 1):
        aitoff_y = -90.0 + i * y_step
        y_coords.append(aitoff_y)
        row: List[float] = []

        for j in range(resolution + 1):
            aitoff_x = -180.0 + j * x_step
            if i == 0:
                x_coords.append(aitoff_x)

            # Convert Aitoff coordinates to approximate RA/Dec
            ra_deg = aitoff_x + 180.0
            dec_deg = aitoff_y

            # Galactic center is at RA ~266°, Dec ~-29°
            gal_center_ra = 266.0
            gal_center_dec = -29.0

            # Distance from galactic center (handle RA wrap-around)
            ra_diff = ((ra_deg - gal_center_ra + 180) % 360) - 180
            dec_diff = dec_deg - gal_center_dec
            dist_from_center = np.sqrt(ra_diff**2 + dec_diff**2)

            # Distance from galactic plane
            plane_dec = -29.0 + 20 * np.sin(np.radians(ra_deg))
            dist_from_plane = np.abs(dec_deg - plane_dec)

            # Calculate brightness
            center_brightness = max(0.0, 1.0 - dist_from_center / 80.0)
            plane_brightness = max(0.0, 0.8 - dist_from_plane / 40.0)
            brightness = 0.2 + center_brightness * 0.6 + plane_brightness * 0.4
            normalized_brightness = min(1.0, brightness**0.8)

            row.append(normalized_brightness)

        z_values.append(row)

    result = {"x": x_coords, "y": y_coords, "z": z_values}

    # Save to cache
    if use_cache:
        cache_path = get_sky_map_data_path(
            frequency_mhz=0.0,  # Synthetic doesn't use frequency
            resolution=resolution,
            map_type="synthetic",
        )
        try:
            logger.info(f"Saving synthetic sky map data to cache: {cache_path}")
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except IOError as e:
            logger.warning(f"Failed to save cache: {e}")

    return result


def get_sky_map_path(
    map_type: str = "synthetic", state_dir: Optional[Path] = None
) -> Optional[Path]:
    """Get path to generated sky map PNG.

    Args:
        map_type: Map type ('synthetic' or 'haslam')
        state_dir: State directory (defaults to env var PIPELINE_STATE_DIR)

    Returns:
        Path to map PNG file, or None if not available
    """
    if state_dir is None:
        state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))

    maps_dir = state_dir / "pointing" / "maps"

    if map_type == "synthetic":
        path = maps_dir / "synthetic_radio_sky_map.png"
        if not path.exists():
            # Generate on demand
            try:
                maps_dir.mkdir(parents=True, exist_ok=True)
                generate_synthetic_radio_sky_map(path)
            except Exception as e:
                logger.error(f"Failed to generate synthetic sky map: {e}")
                return None
        return path
    elif map_type == "haslam":
        # Haslam 408 MHz map not implemented yet
        logger.warning("Haslam 408 MHz map not yet implemented")
        return None
    else:
        logger.warning(f"Unknown map type: {map_type}")
        return None


def generate_mollweide_sky_map_with_pointing(
    frequency_mhz: float = 1400.0,
    pointing_data: Optional[List[Dict[str, float]]] = None,
    output_path: Optional[Path] = None,
    cmap: str = "inferno",
) -> Path:
    """Generate Mollweide sky map with gridlines and pointing traces.

    All rendering done in backend with healpy's Mollweide projection.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import patheffects

    try:
        import healpy as hp
    except ImportError as e:
        raise ImportError(f"healpy not available: {e}")

    if output_path is None:
        import tempfile

        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        output_path = Path(tmp_path)

    logger.info(f"Generating Mollweide sky map with pointing at {frequency_mhz} MHz...")

    # Load cached GSM numpy array (fast: <1 second)
    log_sky = get_or_generate_gsm_cache(frequency_mhz)

    # Create figure with transparent background
    fig = plt.figure(figsize=(12, 6), dpi=150)
    fig.patch.set_alpha(0)
    fig.patch.set_facecolor("none")

    # Plot sky map with coordinate transformation from Galactic to Celestial
    # GSM is in Galactic coordinates, but we want to display in RA/Dec (Celestial)
    hp.mollview(
        log_sky,
        title="",
        unit="",
        cmap=cmap,
        cbar=False,
        notext=True,
        hold=True,
        fig=fig.number,
        coord=["G", "C"],  # Convert from Galactic (G) to Celestial/Equatorial (C)
    )

    ax = plt.gca()
    ax.set_facecolor("none")
    ax.patch.set_alpha(0)
    ax.patch.set_facecolor("none")

    # Make all axes elements transparent
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)

    # Set the figure background to transparent - more thorough approach
    fig.patch.set_visible(False)
    for item in fig.get_children():
        if hasattr(item, "set_facecolor"):
            try:
                item.set_facecolor("none")
            except (ValueError, AttributeError):
                pass
        if hasattr(item, "set_alpha"):
            try:
                item.set_alpha(0)
            except (ValueError, AttributeError):
                pass

    # Add RA/Dec gridlines using healpy's graticule function
    # This automatically handles the correct coordinate system and projection
    hp.graticule(
        dpar=30,  # Dec gridlines every 30 degrees
        dmer=60,  # RA gridlines every 60 degrees (4 hours)
        coord="C",  # Celestial/Equatorial coordinates
        color="white",
        alpha=0.8,  # Higher alpha for better visibility
        linewidth=1.5,  # Thicker lines for better visibility
        linestyle=":",
    )

    # Add gridline labels for RA and Dec with better visibility
    # RA labels along the equator (Dec=0) - enhanced styling
    for ra in range(0, 360, 60):  # Every 60 degrees (4 hours)
        ra_hours = ra // 15  # Convert to hours (0-23h)
        # Add text with outline/shadow for better visibility
        # Background/outline text (black)
        hp.projtext(
            ra,
            0,  # RA, Dec in degrees
            f"{ra_hours}h",
            lonlat=True,
            coord="C",
            color="black",
            fontsize=12,
            fontweight="bold",
            ha="center",
            va="bottom",
            path_effects=[patheffects.withStroke(linewidth=4, foreground="black")],
        )
        # Foreground text (white)
        hp.projtext(
            ra,
            0,  # RA, Dec in degrees
            f"{ra_hours}h",
            lonlat=True,
            coord="C",
            color="white",
            fontsize=12,
            fontweight="bold",
            ha="center",
            va="bottom",
        )

    # Dec labels along the prime meridian (RA=0) - enhanced styling
    for dec in range(-60, 90, 30):  # Every 30 degrees
        if dec != 0:  # Skip 0 to avoid overlap with RA label
            # Background/outline text (black)
            hp.projtext(
                0,
                dec,  # RA, Dec in degrees
                f"{dec}°",
                lonlat=True,
                coord="C",
                color="black",
                fontsize=12,
                fontweight="bold",
                ha="right",
                va="center",
                path_effects=[patheffects.withStroke(linewidth=4, foreground="black")],
            )
            # Foreground text (white)
            hp.projtext(
                0,
                dec,  # RA, Dec in degrees
                f"{dec}°",
                lonlat=True,
                coord="C",
                color="white",
                fontsize=12,
                fontweight="bold",
                ha="right",
                va="center",
            )

    # Add pointing traces if provided
    # The frontend will now handle rendering of pointing traces dynamically.
    # if pointing_data and len(pointing_data) > 0:
    #     logger.info(f"Adding {len(pointing_data)} pointing points...")

    #     # Extract RA/Dec arrays from pointing data
    #     ra_list = []
    #     dec_list = []
    #     for pt in pointing_data:
    #         ra = pt.get("ra_deg")
    #         dec = pt.get("dec_deg")
    #         if ra is not None and dec is not None:
    #             ra_list.append(ra)
    #             dec_list.append(dec)

    #     if ra_list:
    #         # Convert to numpy arrays
    #         ra_arr = np.array(ra_list)
    #         dec_arr = np.array(dec_list)

    #         # Draw trace line using healpy's projplot
    #         # lonlat=True means input is (lon, lat) = (RA, Dec) in degrees
    #         # coord="C" means Celestial/Equatorial coordinates
    #         # Use thick black outline, white middle, and bright colored center
    #         # for maximum visibility against any background

    #         # Black outline (outermost)
    #         hp.projplot(
    #             ra_arr,
    #             dec_arr,
    #             "-",
    #             lonlat=True,
    #             coord="C",
    #             color="black",
    #             linewidth=7,  # Thick black outline
    #             alpha=1.0,
    #         )
    #         # White middle layer
    #         hp.projplot(
    #             ra_arr,
    #             dec_arr,
    #             "-",
    #             lonlat=True,
    #             coord="C",
    #             color="white",
    #             linewidth=5,  # White outline
    #             alpha=1.0,
    #         )
    #         # Bright cyan center line
    #         hp.projplot(
    #             ra_arr,
    #             dec_arr,
    #             "-",
    #             lonlat=True,
    #             coord="C",
    #             color="cyan",
    #             linewidth=3.5,  # Cyan center
    #             alpha=1.0,
    #         )

    #         # Draw marker at last point (current position)
    #         # Use larger, more visible marker with multiple outlines
    #         hp.projplot(
    #             ra_arr[-1],
    #             dec_arr[-1],
    #             "o",
    #             lonlat=True,
    #             coord="C",
    #             color="lime",
    #             markersize=16,  # Larger marker
    #             markeredgecolor="black",
    #             markeredgewidth=3,  # Black outline
    #             alpha=1.0,
    #         )
    #         # Add inner white ring for better visibility
    #         hp.projplot(
    #             ra_arr[-1],
    #             dec_arr[-1],
    #             "o",
    #             lonlat=True,
    #             coord="C",
    #             color="lime",
    #             markersize=14,
    #             markeredgecolor="white",
    #             markeredgewidth=2,
    #             alpha=1.0,
    #         )

    # Save with transparent background
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=150, transparent=True, facecolor="none")
    plt.close(fig)

    logger.info(f"Generated sky map: {output_path}")
    return output_path


def generate_mollweide_sky_map_image(
    frequency_mhz: float = 1400.0,
    output_path: Optional[Path] = None,
    use_cache: bool = True,
    cmap: str = "inferno",
) -> Path:
    """Generate Mollweide-projected HEALPix sky map image using pygdsm.

    This function follows the user's example:
    ```
    import healpy as hp
    import matplotlib.pyplot as plt
    import numpy as np
    import pygdsm
    sky_map = pygdsm.GlobalSkyModel16().generate(1400)
    hp.mollview(np.log10(sky_map), title="GSM at 1.4 GHz (log10 scale)",
                unit="log$_{10}$(K)", cmap="inferno")
    plt.show()
    ```

    Args:
        frequency_mhz: Frequency in MHz (default: 1400.0)
        output_path: Path to save the image (default: auto-generated in state/pointing/maps/)
        use_cache: If True, use cached image if available (default: True)
        cmap: Colormap for visualization (default: "inferno")

    Returns:
        Path to the generated image file
    """
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend
    import matplotlib.pyplot as plt

    try:
        import healpy as hp
        import pygdsm
    except ImportError as e:
        raise ImportError(
            f"pygdsm or healpy not available: {e}. " "Install with: pip install pygdsm healpy"
        )

    # Generate output path if not provided
    if output_path is None:
        state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        maps_dir = state_dir / "pointing" / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        output_path = maps_dir / f"gsm_mollweide_{int(frequency_mhz)}mhz.png"

    # Check cache
    if use_cache and output_path.exists():
        logger.info(f"Using cached Mollweide sky map: {output_path}")
        return output_path

    logger.info(f"Generating Mollweide HEALPix sky map at {frequency_mhz} MHz...")

    # Generate Global Sky Model at specified frequency
    gsm = pygdsm.GlobalSkyModel16()
    sky_map = gsm.generate(frequency_mhz)

    # Create Mollweide projection with healpy
    # Avoid log10(<=0): mask those pixels
    log_sky = np.full_like(sky_map, np.nan, dtype=float)
    mask = sky_map > 0
    log_sky[mask] = np.log10(sky_map[mask])

    # Create transparent figure for overlay on frontend grid
    fig = plt.figure(figsize=(6, 3), dpi=300)
    fig.patch.set_alpha(0)  # transparent figure background

    hp.mollview(
        log_sky,
        title="",  # no title
        unit="",  # no unit label
        cmap=cmap,
        cbar=False,  # no colorbar
        notext=True,  # no labels on the map
        hold=True,
        fig=fig.number,
    )

    # Make the axes background transparent as well
    ax = plt.gca()
    ax.set_facecolor("none")

    # Save to file with transparent background
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight", dpi=300, transparent=True)
    plt.close(fig)

    logger.info(f"Generated Mollweide sky map: {output_path}")
    return output_path


def get_mollweide_sky_map_data(
    frequency_mhz: float = 1400.0,
    nside: int = 64,
    use_cache: bool = True,
) -> Dict:
    """Get HEALPix sky map data in Mollweide projection for frontend display.

    Returns the HEALPix map data and projection information that can be
    used by the frontend to render the sky map.

    Args:
        frequency_mhz: Frequency in MHz (default: 1400.0)
        nside: HEALPix NSIDE parameter (default: 64)
        use_cache: If True, use cached data if available (default: True)

    Returns:
        Dictionary with:
            - pixels: HEALPix pixel values (log10 scale)
            - nside: HEALPix NSIDE parameter
            - frequency_mhz: Frequency
            - unit: Data unit
            - projection: "mollweide"
    """
    try:
        import healpy as hp
        import pygdsm
    except ImportError as e:
        raise ImportError(
            f"pygdsm or healpy not available: {e}. " "Install with: pip install pygdsm healpy"
        )

    # Check cache
    cache_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state")) / "pointing" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"gsm_healpix_{int(frequency_mhz)}mhz_nside{nside}.npz"

    if use_cache and cache_file.exists():
        try:
            logger.info(f"Loading cached HEALPix sky map: {cache_file}")
            data = np.load(cache_file)
            return {
                "pixels": data["pixels"].tolist(),
                "nside": int(data["nside"]),
                "frequency_mhz": float(data["frequency_mhz"]),
                "unit": "log10(K)",
                "projection": "mollweide",
            }
        except Exception as e:
            logger.warning(f"Failed to load cache, regenerating: {e}")

    logger.info(f"Generating HEALPix sky map at {frequency_mhz} MHz (NSIDE={nside})...")

    # Generate Global Sky Model at specified frequency
    gsm = pygdsm.GlobalSkyModel16()
    sky_map = gsm.generate(frequency_mhz)

    # Resample to desired NSIDE if needed
    sky_map_nside = hp.get_nside(sky_map)
    if sky_map_nside != nside:
        logger.info(f"Resampling from NSIDE={sky_map_nside} to NSIDE={nside}")
        sky_map = hp.ud_grade(sky_map, nside)

    # Convert to log10 scale
    sky_map_log = np.log10(sky_map)

    # Save to cache
    try:
        np.savez_compressed(
            cache_file,
            pixels=sky_map_log,
            nside=nside,
            frequency_mhz=frequency_mhz,
        )
        logger.info(f"Cached HEALPix sky map: {cache_file}")
    except Exception as e:
        logger.warning(f"Failed to cache sky map: {e}")

    return {
        "pixels": sky_map_log.tolist(),
        "nside": nside,
        "frequency_mhz": frequency_mhz,
        "unit": "log10(K)",
        "projection": "mollweide",
    }
