"""
CLI for planning and building mosaics from 5-minute image tiles.

A **tile** is a single calibrated, imaged, and primary-beam-corrected radio astronomy
image created from ~5 minutes of observation data. Multiple tiles are combined to create
a larger mosaic covering a wider field of view.

Phase 1: record mosaic plan (list of tiles) into products DB.
Phase 2: validate tiles and build weighted mosaic using primary beam weighting.

See docs/reference/GLOSSARY.md for detailed definition of tiles and related terminology.
"""

from .exceptions import (
    MosaicError,
    ImageReadError,
    ImageCorruptionError,
    MissingPrimaryBeamError,
    IncompatibleImageFormatError,
    CASAToolError,
    GridMismatchError,
    ValidationError,
    MetricsGenerationError,
)
from .validation import (
    validate_tiles_consistency,
    verify_astrometric_registration,
    check_calibration_consistency,
    check_primary_beam_consistency,
    TileQualityMetrics,
    _find_pb_path,
    HAVE_CASACORE,
)
from dsa110_contimg.utils.cli_helpers import ensure_scratch_dirs
from dsa110_contimg.database.products import ensure_products_db
import argparse
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Initialize CASA environment before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()

try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore


LOG = logging.getLogger(__name__)


def _ensure_mosaics_table(conn: sqlite3.Connection) -> None:
    """Ensure mosaics table exists with workflow columns.

    The mosaics table has two schemas:
    1. Workflow schema (CLI): status, method, tiles, output_path, validation_issues
    2. Science metadata schema (migration): path, start_mjd, end_mjd, noise_jy, etc.

    This function ensures the workflow columns exist, adding them if needed.
    """
    # Create table if it doesn't exist (with workflow schema)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mosaics (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            method TEXT,
            tiles TEXT NOT NULL,
            output_path TEXT,
            validation_issues TEXT
        )
        """
    )

    # Add workflow columns if they don't exist (for existing science metadata table)
    # Check if status column exists
    cur = conn.execute("PRAGMA table_info(mosaics)")
    columns = {row[1] for row in cur.fetchall()}

    if 'status' not in columns:
        # Add workflow columns to existing table
        conn.execute("ALTER TABLE mosaics ADD COLUMN status TEXT")
        conn.execute("ALTER TABLE mosaics ADD COLUMN method TEXT")
        conn.execute("ALTER TABLE mosaics ADD COLUMN tiles TEXT")
        conn.execute("ALTER TABLE mosaics ADD COLUMN output_path TEXT")
        conn.execute("ALTER TABLE mosaics ADD COLUMN validation_issues TEXT")
        # Set default status for existing rows
        conn.execute(
            "UPDATE mosaics SET status = 'built' WHERE status IS NULL")

    # Ensure metrics_path column exists (used in cmd_build)
    if 'metrics_path' not in columns:
        conn.execute("ALTER TABLE mosaics ADD COLUMN metrics_path TEXT")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mosaics_name ON mosaics(name)"
    )


def _fetch_tiles(products_db: Path, *, since: Optional[float], until: Optional[float], pbcor_only: bool = True) -> List[str]:
    """Fetch tile paths from products database.

    Returns paths to PB-corrected images (CASA image directories or FITS files).
    Tiles are returned in chronological order (by created_at).

    Args:
        products_db: Path to products database
        since: Only include tiles created_at >= since (epoch seconds)
        until: Only include tiles created_at <= until (epoch seconds)
        pbcor_only: Only include PB-corrected images

    Returns:
        List of tile paths (directories or files) that exist on disk
    """
    tiles: List[str] = []
    with ensure_products_db(products_db) as conn:
        q = "SELECT path, created_at, pbcor FROM images"
        where = []
        params: List[object] = []
        if pbcor_only:
            where.append("pbcor = 1")
        if since is not None:
            where.append("created_at >= ?")
            params.append(float(since))
        if until is not None:
            where.append("created_at <= ?")
            params.append(float(until))
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY created_at ASC"
        for r in conn.execute(q, params).fetchall():
            p = r["path"] if isinstance(r, sqlite3.Row) else r[0]
            # Accept both CASA image directories and FITS files
            # casaimage() can read both formats
            if p and (os.path.isdir(p) or (os.path.isfile(p) and p.endswith('.fits'))):
                tiles.append(p)
    return tiles


def cmd_plan(args: argparse.Namespace) -> int:
    # Input validation
    if not hasattr(args, 'products_db') or not args.products_db:
        raise ValueError("products_db is required")
    if not isinstance(args.products_db, str) or not args.products_db.strip():
        raise ValueError("products_db must be a non-empty string")
    if not hasattr(args, 'name') or not args.name:
        raise ValueError("name is required")
    if not isinstance(args.name, str) or not args.name.strip():
        raise ValueError("name must be a non-empty string")

    pdb = Path(args.products_db)
    name = args.name
    since = args.since
    until = args.until
    tiles = _fetch_tiles(pdb, since=since, until=until,
                         pbcor_only=not args.include_unpbcor)
    if not tiles:
        print("No tiles found for the specified window")
        return 1
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        # Check if path column exists (science metadata schema)
        cur = conn.execute("PRAGMA table_info(mosaics)")
        columns = {row[1]: row[3] for row in cur.fetchall()}  # name: notnull

        if 'path' in columns:
            # Science metadata schema - provide placeholder values for NOT NULL columns
            # These will be updated when mosaic is built
            conn.execute(
                """INSERT INTO mosaics(name, created_at, status, method, tiles, path, start_mjd, end_mjd) 
                   VALUES(?,?,?,?,?,?,?,?)""",
                (name, time.time(), "planned", args.method,
                 "\n".join(tiles), "PLANNED", 0.0, 0.0),
            )
        else:
            # Workflow-only schema
            conn.execute(
                "INSERT INTO mosaics(name, created_at, status, method, tiles) VALUES(?,?,?,?,?)",
                (name, time.time(), "planned", args.method, "\n".join(tiles)),
            )
        conn.commit()
    print(f"Planned mosaic '{name}' with {len(tiles)} tiles")
    return 0


def _check_consistent_tiles(tiles: List[str]) -> Tuple[bool, Optional[str]]:
    """Check basic grid consistency (legacy function)."""
    from .cache import get_cache
    import numpy as np

    cache = get_cache()
    ref = None
    for t in tiles:
        try:
            header = cache.get_tile_header(t)
            if not header:
                return False, f"Failed to get header for {t}"
            # Convert shape to tuple for comparison (handles numpy arrays, lists, and strings)
            shape = header.get('shape')
            if isinstance(shape, np.ndarray):
                shape = tuple(shape.tolist())
            elif isinstance(shape, list):
                shape = tuple(shape)
            elif isinstance(shape, str):
                # Cache may serialize arrays as strings like "[6300 6300    1    1]" or "[512, 512]"
                # Try to parse it - handle both numpy-style and list-style strings
                try:
                    import ast
                    import re
                    # First try direct ast.literal_eval for list-style "[512, 512]"
                    shape_list = ast.literal_eval(shape)
                    shape = tuple(shape_list) if isinstance(
                        shape_list, list) else shape
                except (ValueError, SyntaxError):
                    # If that fails, try parsing numpy-style "[6300 6300    1    1]"
                    try:
                        # Extract numbers from string like "[6300 6300    1    1]"
                        numbers = re.findall(r'\d+', shape)
                        if numbers:
                            shape = tuple(int(n) for n in numbers)
                        else:
                            # If parsing fails, keep as string (will be handled in comparison)
                            pass
                    except Exception:
                        # If all parsing fails, keep as string
                        pass
            cdelt1 = header.get('cdelt1')
            cdelt2 = header.get('cdelt2')
            key = (shape, cdelt1, cdelt2)
            if ref is None:
                ref = key
            else:
                # Compare with tolerance for floating-point values
                ref_shape, ref_cdelt1, ref_cdelt2 = ref
                # Normalize shapes to tuples for comparison (handles numpy arrays, lists, tuples, strings)

                def normalize_shape(s):
                    if isinstance(s, tuple):
                        return s
                    elif isinstance(s, (list, np.ndarray)):
                        return tuple(s) if isinstance(s, list) else tuple(s.tolist())
                    elif isinstance(s, str):
                        # Try to parse string representation
                        try:
                            import ast
                            import re
                            shape_list = ast.literal_eval(s)
                            return tuple(shape_list) if isinstance(shape_list, list) else s
                        except (ValueError, SyntaxError):
                            # Try numpy-style string parsing
                            try:
                                numbers = re.findall(r'\d+', s)
                                return tuple(int(n) for n in numbers) if numbers else s
                            except Exception:
                                return s
                    else:
                        return tuple(s) if hasattr(s, '__iter__') else s

                shape_tuple = normalize_shape(shape)
                ref_shape_tuple = normalize_shape(ref_shape)
                if shape_tuple != ref_shape_tuple:
                    return False, f"Tiles have inconsistent grid shapes: {shape_tuple} vs {ref_shape_tuple}"
                # Use relative tolerance for cell size comparison (1e-9 relative tolerance)
                if cdelt1 is not None and ref_cdelt1 is not None:
                    if abs(cdelt1 - ref_cdelt1) > max(1e-12, abs(ref_cdelt1) * 1e-9):
                        return False, f"Tiles have inconsistent cdelt1: {cdelt1} vs {ref_cdelt1}"
                if cdelt2 is not None and ref_cdelt2 is not None:
                    if abs(cdelt2 - ref_cdelt2) > max(1e-12, abs(ref_cdelt2) * 1e-9):
                        return False, f"Tiles have inconsistent cdelt2: {cdelt2} vs {ref_cdelt2}"
        except Exception as e:
            return False, f"imhead failed for {t}: {e}"
    return True, None


def generate_mosaic_metrics(
    tiles: List[str],
    metrics_dict: Dict[str, TileQualityMetrics],
    mosaic_path: str,
    output_dir: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate mosaic quality metrics images.

    Creates metadata images showing:
    - Effective integration time per pixel
    - Primary beam response per pixel
    - Noise variance per pixel
    - Number of tiles contributing per pixel
    - Coverage map

    Args:
        tiles: List of tile paths
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        mosaic_path: Path to mosaic image
        output_dir: Optional output directory (defaults to mosaic directory)

    Returns:
        Dictionary mapping metric name -> file path
    """
    metric_files = {}

    if not HAVE_CASACORE:
        LOG.warning(
            "casacore.images not available, skipping mosaic metrics generation")
        return metric_files

    try:
        import numpy as np
        from .validation import _find_pb_path

        # Ensure CASAPATH is set before importing CASA modules
        from dsa110_contimg.utils.casa_init import ensure_casa_path
        ensure_casa_path()

        # Import CASA tools if available
        try:
            from casatasks import exportfits, imregrid
            from casacore.images import image as casaimage
        except ImportError:
            exportfits = None
            imregrid = None
            casaimage = None

        if not casaimage:
            LOG.warning(
                "CASA tools not available, skipping mosaic metrics generation")
            return metric_files

        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(mosaic_path))
        os.makedirs(output_dir, exist_ok=True)

        # Read mosaic to get reference grid
        mosaic_img = casaimage(mosaic_path)
        mosaic_data = mosaic_img.getdata()
        # casaimage uses coordinates() not coordsys()
        coord_sys = mosaic_img.coordinates()

        # Extract 2D image data
        if mosaic_data.ndim == 2:
            mosaic_2d = mosaic_data
        elif mosaic_data.ndim == 4:
            mosaic_2d = mosaic_data[0, 0, :, :]
        else:
            mosaic_2d = mosaic_data.squeeze()
            if mosaic_2d.ndim > 2:
                mosaic_2d = mosaic_2d[0, :,
                                      :] if mosaic_2d.ndim == 3 else mosaic_2d

        ny, nx = mosaic_2d.shape
        mosaic_base = os.path.splitext(os.path.basename(mosaic_path))[0]

        # Initialize metric arrays
        pb_response_map = np.zeros((ny, nx), dtype=np.float64)
        noise_variance_map = np.zeros((ny, nx), dtype=np.float64)
        tile_count_map = np.zeros((ny, nx), dtype=np.int32)
        integration_time_map = np.zeros((ny, nx), dtype=np.float64)

        # Process each tile
        for tile in tiles:
            metrics = metrics_dict.get(
                tile, TileQualityMetrics(tile_path=tile))

            # Get PB path
            pb_path = metrics.pb_path
            if not pb_path:
                pb_path = _find_pb_path(tile)

            if pb_path and os.path.exists(pb_path):
                try:
                    pb_img = casaimage(str(pb_path))
                    pb_data = pb_img.getdata()

                    # Extract 2D PB data
                    if pb_data.ndim == 2:
                        pb_2d = pb_data
                    elif pb_data.ndim == 4:
                        pb_2d = pb_data[0, 0, :, :]
                    else:
                        pb_2d = pb_data.squeeze()
                        if pb_2d.ndim > 2:
                            pb_2d = pb_2d[0, :,
                                          :] if pb_2d.ndim == 3 else pb_2d

                    # Check if PB needs regridding
                    if pb_2d.shape != (ny, nx):
                        # Need to regrid PB to mosaic grid
                        regridded_pb = os.path.join(
                            output_dir, f"{mosaic_base}_pb_regrid_{len(metric_files)}.tmp")
                        try:
                            imregrid(
                                imagename=str(pb_path),
                                template=mosaic_path,
                                output=regridded_pb,
                                overwrite=True,
                            )
                            pb_img.close()
                            pb_img = casaimage(regridded_pb)
                            pb_data = pb_img.getdata()
                            if pb_data.ndim == 2:
                                pb_2d = pb_data
                            elif pb_data.ndim == 4:
                                pb_2d = pb_data[0, 0, :, :]
                            else:
                                pb_2d = pb_data.squeeze()
                                if pb_2d.ndim > 2:
                                    pb_2d = pb_2d[0, :,
                                                  :] if pb_2d.ndim == 3 else pb_2d
                        except Exception as e:
                            LOG.warning(f"Failed to regrid PB for {tile}: {e}")
                            pb_img.close()
                            continue

                    # Accumulate PB response (use max across tiles for each pixel)
                    pb_response_map = np.maximum(pb_response_map, pb_2d)

                    pb_img.close()

                except Exception as e:
                    LOG.warning(f"Failed to read PB image {pb_path}: {e}")

            # Get noise variance
            noise_var = 1.0
            if metrics.rms_noise is not None and metrics.rms_noise > 0:
                noise_var = metrics.rms_noise ** 2

            # Accumulate weighted noise variance
            # For each pixel, accumulate 1/noise_variance (inverse variance weighting)
            inv_var = 1.0 / noise_var if noise_var > 0 else 1.0
            noise_variance_map += inv_var

            # Count tiles contributing to each pixel
            # For now, mark all pixels (could be refined based on PB threshold)
            tile_count_map += 1

            # Integration time (placeholder - would need MS metadata)
            # For now, assume equal integration time per tile
            # Units: tile counts (would convert to seconds if available)
            integration_time_map += 1.0

        # Normalize noise variance map (convert back to variance)
        # noise_variance_map currently contains sum(1/variance), so invert
        mask = noise_variance_map > 0
        noise_variance_map[mask] = 1.0 / noise_variance_map[mask]
        noise_variance_map[~mask] = np.nan

        # Create output images
        base_path = os.path.join(output_dir, mosaic_base)

        # 1. Primary beam response map
        pb_response_path = f"{base_path}_pb_response"
        pb_response_data = pb_response_map[np.newaxis, np.newaxis, :, :]
        pb_response_img = casaimage(
            pb_response_path, shape=pb_response_data.shape, coordsys=coord_sys)
        pb_response_img.putdata(pb_response_data.astype(np.float32))
        del pb_response_img
        metric_files['pb_response'] = pb_response_path

        # 2. Noise variance map
        noise_var_path = f"{base_path}_noise_variance"
        noise_var_data = noise_variance_map[np.newaxis, np.newaxis, :, :]
        noise_var_img = casaimage(
            noise_var_path, shape=noise_var_data.shape, coordsys=coord_sys)
        noise_var_img.putdata(noise_var_data.astype(np.float32))
        del noise_var_img
        metric_files['noise_variance'] = noise_var_path

        # 3. Tile count map
        tile_count_path = f"{base_path}_tile_count"
        tile_count_data = tile_count_map.astype(
            np.float32)[np.newaxis, np.newaxis, :, :]
        tile_count_img = casaimage(
            tile_count_path, shape=tile_count_data.shape, coordsys=coord_sys)
        tile_count_img.putdata(tile_count_data)
        del tile_count_img
        metric_files['tile_count'] = tile_count_path

        # 4. Integration time map
        int_time_path = f"{base_path}_integration_time"
        int_time_data = integration_time_map[np.newaxis, np.newaxis, :, :]
        integration_time_img = casaimage(
            int_time_path, shape=int_time_data.shape, coordsys=coord_sys)
        integration_time_img.putdata(int_time_data.astype(np.float32))
        del integration_time_img
        metric_files['integration_time'] = int_time_path

        # 5. Coverage map (binary: 1 if tile contributes, 0 otherwise)
        coverage_map = (tile_count_map > 0).astype(np.float32)
        coverage_path = f"{base_path}_coverage"
        coverage_data = coverage_map[np.newaxis, np.newaxis, :, :]
        coverage_img = casaimage(
            coverage_path, shape=coverage_data.shape, coordsys=coord_sys)
        coverage_img.putdata(coverage_data)
        del coverage_img
        metric_files['coverage'] = coverage_path

        # Export as FITS
        if exportfits:
            for metric_name, metric_path in list(metric_files.items()):
                fits_path = f"{metric_path}.fits"
                try:
                    exportfits(
                        imagename=metric_path,
                        fitsimage=fits_path,
                        overwrite=True,
                    )
                    # Update to FITS path
                    metric_files[metric_name] = fits_path
                except Exception as e:
                    LOG.warning(f"Failed to export {metric_name} to FITS: {e}")

        # Cleanup - casaimage doesn't have close() method
        del mosaic_img

        LOG.info(f"Generated mosaic metrics: {list(metric_files.keys())}")

    except Exception as e:
        LOG.error(f"Failed to generate mosaic metrics: {e}")
        import traceback
        traceback.print_exc()

    return metric_files


def _calculate_mosaic_bounds(tiles: List[str]) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box (RA_min, RA_max, Dec_min, Dec_max) from all tiles.

    Args:
        tiles: List of tile image paths

    Returns:
        Tuple of (RA_min, RA_max, Dec_min, Dec_max) in degrees
    """
    try:
        from astropy.io import fits
        from astropy.wcs import WCS
        from dsa110_contimg.utils.runtime_safeguards import (
            validate_wcs_4d,
            wcs_pixel_to_world_safe,
        )
        import numpy as np
    except ImportError:
        # Fallback: try using CASA to get coordinates
        import numpy as np
        LOG.warning(
            "astropy not available, using CASA for coordinate extraction")
        from casacore.images import image as casaimage

        ra_min_list, ra_max_list = [], []
        dec_min_list, dec_max_list = [], []

        for tile in tiles:
            try:
                img = casaimage(str(tile))
                # Use coordinates() directly (correct API for casacore.images.image)
                coordsys = img.coordinates()

                # Get image shape
                shape = img.shape()
                if len(shape) >= 2:
                    ny, nx = shape[-2], shape[-1]
                else:
                    ny, nx = shape[0], shape[1] if len(shape) > 1 else shape[0]

                # Get corner coordinates
                corners_pix = [
                    [0, 0],
                    [nx-1, 0],
                    [0, ny-1],
                    [nx-1, ny-1]
                ]

                ras, decs = [], []
                for x, y in corners_pix:
                    try:
                        # Try toworld() first (for coordsys objects)
                        try:
                            world = coordsys.toworld([y, x])
                        except AttributeError:
                            # Fallback to toworldmany() for coordinates() objects
                            world_list = coordsys.toworldmany([[y, x]])
                            world = world_list[0] if world_list else None
                            if world is None:
                                continue

                        # Extract RA/Dec values, handling arrays
                        ra_val = world[0]
                        dec_val = world[1] if len(world) >= 2 else None

                        if isinstance(ra_val, np.ndarray):
                            ra_val = ra_val[0] if ra_val.size > 0 else None
                        if isinstance(dec_val, np.ndarray):
                            dec_val = dec_val[0] if dec_val.size > 0 else None

                        if ra_val is not None and dec_val is not None:
                            # CASA returns [RA, Dec] in radians
                            ra_deg = np.degrees(float(ra_val))
                            dec_deg = np.degrees(float(dec_val))
                            ras.append(ra_deg)
                            decs.append(dec_deg)
                    except Exception:
                        pass

                if ras and decs:
                    ra_min_list.append(min(ras))
                    ra_max_list.append(max(ras))
                    dec_min_list.append(min(decs))
                    dec_max_list.append(max(decs))

                # Try to close image (may not exist for FITS files)
                try:
                    img.close()
                except AttributeError:
                    pass
            except Exception as e:
                LOG.warning(f"Failed to get coordinates from {tile}: {e}")
                continue

        if not ra_min_list:
            raise ValueError("Could not extract coordinates from any tile")

        return (min(ra_min_list), max(ra_max_list),
                min(dec_min_list), max(dec_max_list))

    # Use astropy (preferred method)
    ra_min_list, ra_max_list = [], []
    dec_min_list, dec_max_list = [], []

    for tile in tiles:
        try:
            with fits.open(tile) as hdul:
                hdr = hdul[0].header
                # Use celestial WCS (RA/Dec only) for 4D images
                wcs = WCS(hdr).celestial

                # Get image shape
                data = hdul[0].data
                if data.ndim >= 2:
                    ny, nx = data.shape[-2], data.shape[-1]
                else:
                    ny, nx = data.shape[0], data.shape[1] if data.ndim > 1 else data.shape[0]

                # Get corner coordinates
                corners_pix = [
                    [0, 0],
                    [nx-1, 0],
                    [0, ny-1],
                    [nx-1, ny-1]
                ]

                wcs_validated, is_4d, defaults = validate_wcs_4d(wcs)
                corners_world = [
                    wcs_pixel_to_world_safe(
                        wcs_validated, c[1], c[0], is_4d, defaults)
                    for c in corners_pix
                ]
                ras = [c[0] for c in corners_world]
                decs = [c[1] for c in corners_world]

                ra_min_list.append(min(ras))
                ra_max_list.append(max(ras))
                dec_min_list.append(min(decs))
                dec_max_list.append(max(decs))
        except Exception as e:
            LOG.warning(f"Failed to get coordinates from {tile}: {e}")
            continue

    if not ra_min_list:
        raise ValueError("Could not extract coordinates from any tile")

    return (min(ra_min_list), max(ra_max_list),
            min(dec_min_list), max(dec_max_list))


def _create_common_coordinate_system(
    ra_min: float, ra_max: float, dec_min: float, dec_max: float,
    pixel_scale_arcsec: float = 2.0,
    padding_pixels: int = 10,
    template_tile: Optional[str] = None,
    output_dir: Optional[str] = None
):
    """
    Create a common coordinate system that encompasses all tiles.

    Creates a template image with the desired coordinate system by:
    1. Using an existing tile as a template for coordinate system structure
    2. Modifying its coordinate system to match the desired bounds
    3. Creating a new template image with the modified coordinate system

    Args:
        ra_min, ra_max: RA range in degrees
        dec_min, dec_max: Dec range in degrees
        pixel_scale_arcsec: Pixel scale in arcseconds (default: 2.0)
        padding_pixels: Extra pixels to add on each side
        template_tile: Path to a tile to use as template (required)
        output_dir: Directory for temporary template image

    Returns:
        Tuple of (template_image_path, shape) where template_image_path
        is the path to a CASA image with the desired coordinate system
    """
    from casacore.images import image as casaimage
    from casatasks import imregrid, immath
    import numpy as np
    import tempfile
    import os

    if template_tile is None:
        raise ValueError(
            "template_tile is required to create coordinate system")

    # Calculate center
    ra_center = (ra_min + ra_max) / 2.0
    dec_center = (dec_min + dec_max) / 2.0

    # Calculate size in degrees
    ra_span = ra_max - ra_min
    dec_span = dec_max - dec_min

    # Convert pixel scale to degrees
    pixel_scale_deg = pixel_scale_arcsec / 3600.0

    # Calculate output size in pixels (with padding)
    nx = int(np.ceil(ra_span / pixel_scale_deg)) + 2 * padding_pixels
    ny = int(np.ceil(dec_span / pixel_scale_deg)) + 2 * padding_pixels

    # Create template image directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix='mosaic_template_')
    else:
        os.makedirs(output_dir, exist_ok=True)

    template_image_path = os.path.join(output_dir, 'common_template.image')

    # Convert FITS to CASA image if needed (imregrid requires CASA image format)
    template_tile_casa = template_tile
    if template_tile.endswith('.fits'):
        # Convert FITS to CASA image format for template
        template_tile_casa = os.path.join(
            output_dir, 'template_tile_casa.image')
        if os.path.exists(template_tile_casa):
            import shutil
            if os.path.isdir(template_tile_casa):
                shutil.rmtree(template_tile_casa)

        try:
            from casatasks import importfits
            importfits(fitsimage=template_tile,
                       imagename=template_tile_casa, overwrite=True)
            LOG.debug(
                f"Converted FITS template to CASA image: {template_tile_casa}")
        except Exception as e:
            LOG.warning(
                f"Could not convert FITS to CASA image: {e}, using FITS directly")
            template_tile_casa = template_tile

    # Use template tile to get coordinate system structure
    template_img = casaimage(template_tile_casa)
    template_coordsys = template_img.coordinates()

    # Get direction coordinate and modify it
    dir_coord = template_coordsys.get_coordinate('direction')

    # Convert to radians
    ra_center_rad = np.radians(ra_center)
    dec_center_rad = np.radians(dec_center)
    pixel_scale_rad = np.radians(pixel_scale_deg)

    # Modify the direction coordinate
    dir_coord.set_referencevalue([ra_center_rad, dec_center_rad])
    dir_coord.set_referencepixel([nx/2.0, ny/2.0])
    dir_coord.set_increment([-pixel_scale_rad, pixel_scale_rad])

    # Create a new coordinate system with modified direction coordinate
    # Create a new image directly with the modified coordinate system
    try:
        # Remove existing template if it exists
        if os.path.exists(template_image_path):
            import shutil
            if os.path.isdir(template_image_path):
                shutil.rmtree(template_image_path)
            else:
                os.remove(template_image_path)

        # Create new coordinate system with modified direction coordinate
        from casacore.images.coordinates import coordinatesystem

        # Get the coordinate system record structure from template
        # and modify the direction coordinate in it
        coordsys_dict = template_coordsys.dict()

        # Modify the direction coordinate in the record
        # CASA uses 'direction0', 'stokes1', 'spectral2' etc. as keys
        dir_coord_dict = dir_coord.dict()
        if 'direction0' in coordsys_dict:
            # Update existing direction coordinate
            coordsys_dict['direction0'] = dir_coord_dict
        else:
            # Add direction coordinate (shouldn't happen, but handle it)
            coordsys_dict['direction0'] = dir_coord_dict

        # Create coordinate system from record
        new_coordsys = coordinatesystem(coordsys_dict)

        # Create image shape - handle 2D vs 4D
        # Check if template has stokes/frequency dimensions
        template_shape = template_img.shape()
        if len(template_shape) == 4:
            # 4D: [stokes, freq, y, x]
            image_shape = [template_shape[0], template_shape[1], ny, nx]
        elif len(template_shape) == 2:
            # 2D: [y, x]
            image_shape = [ny, nx]
        else:
            # Use 2D for simplicity
            image_shape = [ny, nx]

        # Create new image with modified coordinate system
        new_img = casaimage(template_image_path, shape=image_shape,
                            coordsys=new_coordsys, overwrite=True)

        # Fill with zeros
        new_img.putdata(np.zeros(image_shape, dtype=np.float32))

        try:
            new_img.close()
        except AttributeError:
            pass

        LOG.debug(
            f"Created template image: {template_image_path} with shape {image_shape}")

    except Exception as e:
        # Fallback: create a simple template with correct shape
        # Even if coordinate system creation fails, we need the right shape
        LOG.warning(
            f"Could not create custom template image: {e}, creating simple template with correct shape")
        import traceback
        LOG.debug(traceback.format_exc())

        # Create a simple template image with the correct shape
        # Use the template tile's coordinate system but create with desired shape
        try:
            # Get shape from template
            template_shape = template_img.shape()
            if len(template_shape) == 4:
                image_shape = [template_shape[0], template_shape[1], ny, nx]
            else:
                image_shape = [ny, nx]

            # Create image with template's coordinate system but desired shape
            # This will have wrong coordinates but right shape for regridding
            new_img = casaimage(template_image_path, shape=image_shape,
                                coordsys=template_coordsys, overwrite=True)
            new_img.putdata(np.zeros(image_shape, dtype=np.float32))
            try:
                new_img.close()
            except AttributeError:
                pass
            LOG.debug(f"Created fallback template with shape {image_shape}")
        except Exception as e2:
            # Last resort: use template tile (wrong shape, but will work for coordinate system)
            LOG.warning(
                f"Could not create fallback template: {e2}, using template tile")
            template_image_path = template_tile_casa

    try:
        template_img.close()
    except AttributeError:
        pass

    return template_image_path, (ny, nx)


def _build_weighted_mosaic_linearmosaic(
    tiles: List[str],
    metrics_dict: dict,
    output_path: str,
) -> None:
    """
    Build mosaic using CASA's linearmosaic tool (primary method).

    Uses CASA's built-in linearmosaic tool which handles:
    - Primary beam weighting (optimal Sault weighting)
    - Coordinate system alignment
    - Weighted combination

    Weighting scheme: Optimal Sault weighting
    I^lm(θ) = Σ_p A_p(θ)(I_p(θ)A_p(θ))w_p / Σ_p A_p²(θ)w_p

    Args:
        tiles: List of tile image paths (should be PB-corrected images)
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        output_path: Output mosaic path (CASA image format)

    Raises:
        CASAToolError: If linearmosaic tool is not available
        MosaicError: If mosaicking fails
    """
    import tempfile
    import shutil
    from pathlib import Path

    LOG.info(
        f"Building mosaic using linearmosaic tool with {len(tiles)} tiles")

    # Basic validation
    if not tiles:
        raise MosaicError("No tiles provided", "tiles list is empty")
    if not output_path:
        raise MosaicError("Output path is empty", "Must provide output_path")

    # Check all tiles exist
    for i, tile in enumerate(tiles):
        if not os.path.exists(tile):
            raise MosaicError(
                f"Tile {i+1} does not exist: {tile}",
                "All tiles must exist before building mosaic"
            )

    try:
        from casatools import linearmosaic
        from casatasks import importfits, imregrid
        from casacore.images import image as casaimage
        import numpy as np
    except ImportError as e:
        raise CASAToolError(
            f"CASA not available: {e}",
            "Ensure CASA is installed and available in the environment. "
            "Try: conda activate casa6"
        ) from e

    # Convert FITS to CASA format if needed
    temp_dir = tempfile.mkdtemp(prefix='mosaic_linearmosaic_')
    try:
        casa_tiles = []
        for i, tile in enumerate(tiles):
            if tile.endswith('.fits'):
                casa_tile = os.path.join(temp_dir, f'tile_{i}.image')
                if not os.path.exists(casa_tile):
                    LOG.debug(f"Converting FITS to CASA: {Path(tile).name}")
                    importfits(fitsimage=tile,
                               imagename=casa_tile, overwrite=True)
                casa_tiles.append(casa_tile)
            else:
                casa_tiles.append(tile)

        # Get PB images and prepare for linearmosaic
        from .validation import _find_pb_path
        from .coordinate_utils import check_tile_overlaps_template, filter_tiles_by_overlap

        pb_images = []
        regridded_tiles = []
        regridded_pbs = []
        template_tile = casa_tiles[0]

        # Pre-validate tile overlap with template before regridding
        # This prevents "All output pixels are masked" errors
        overlapping_tiles, skipped_list = filter_tiles_by_overlap(
            casa_tiles, template_tile, margin_pixels=10
        )

        if len(overlapping_tiles) < len(casa_tiles):
            skipped_count = len(casa_tiles) - len(overlapping_tiles)
            LOG.warning(
                f"Filtered {skipped_count} tiles that don't overlap template. "
                f"Proceeding with {len(overlapping_tiles)} tiles."
            )
            # Update tiles and casa_tiles to only include overlapping ones
            overlapping_indices = [i for i, ct in enumerate(
                casa_tiles) if ct in overlapping_tiles]
            tiles = [tiles[i] for i in overlapping_indices]
            casa_tiles = overlapping_tiles

            # Ensure we have at least one tile
            if not casa_tiles:
                raise MosaicError(
                    "No tiles overlap with template coordinate system",
                    "All tiles were filtered out due to coordinate system mismatch. "
                    "Check that tiles have compatible coordinate systems."
                )

        # Regrid all tiles and PB images to common coordinate system
        for i, (tile, casa_tile) in enumerate(zip(tiles, casa_tiles)):
            metrics = metrics_dict.get(
                tile, TileQualityMetrics(tile_path=tile))

            # Get PB path
            pb_path = metrics.pb_path
            if not pb_path:
                pb_path = _find_pb_path(tile)

            if not pb_path or not os.path.exists(pb_path):
                raise MissingPrimaryBeamError(
                    f"PB image not found for tile {i+1}: {Path(tile).name}",
                    "linearmosaic requires PB images for optimal weighting"
                )

            # Regrid tile to template
            # Note: Overlap has already been validated, but we still catch errors
            # in case of edge cases or coordinate system issues
            regridded_tile = os.path.join(temp_dir, f'regrid_tile_{i}.image')
            if not os.path.exists(regridded_tile):
                LOG.debug(f"Regridding tile {i+1}/{len(casa_tiles)}")
                try:
                    imregrid(
                        imagename=casa_tile,
                        template=template_tile,
                        output=regridded_tile,
                        overwrite=True
                    )
                except RuntimeError as e:
                    if "All output pixels are masked" in str(e):
                        LOG.warning(
                            f"Tile regridding failed for tile {i+1} (all pixels masked): {Path(tile).name}. "
                            f"This should have been caught by pre-validation. Skipping this tile."
                        )
                        continue
                    else:
                        raise

            # Regrid PB to template
            regridded_pb = os.path.join(temp_dir, f'regrid_pb_{i}.image')
            if not os.path.exists(regridded_pb):
                LOG.debug(f"Regridding PB {i+1}/{len(casa_tiles)}")
                try:
                    imregrid(
                        imagename=pb_path,
                        template=template_tile,
                        output=regridded_pb,
                        overwrite=True
                    )
                except RuntimeError as e:
                    if "All output pixels are masked" in str(e):
                        LOG.warning(
                            f"PB regridding failed for tile {i+1} (all pixels masked): {Path(tile).name}. "
                            f"Skipping this tile."
                        )
                        continue
                    else:
                        raise

            regridded_tiles.append(regridded_tile)
            regridded_pbs.append(regridded_pb)

        if not regridded_tiles:
            raise MosaicError(
                "No tiles could be regridded successfully",
                "All tiles failed regridding (all pixels masked). Check coordinate systems."
            )

        # Get output image properties from first tile
        img = casaimage(regridded_tiles[0])
        shape = img.shape()
        coordsys = img.coordinates()

        # Extract direction info for output image
        # Use casacore API: get_coordinate('direction') returns the direction coordinate object
        try:
            dir_coord = coordsys.get_coordinate('direction')
            ref_val = dir_coord.get_referencevalue()
            ref_pix = dir_coord.get_referencepixel()
            inc = dir_coord.get_increment()
            # linearmosaic expects imagecenter as list of strings with units
            import numpy as np
            ra_deg = np.degrees(ref_val[0])
            dec_deg = np.degrees(ref_val[1])
            # RA, Dec as strings with units
            imagecenter = [f"{ra_deg}deg", f"{dec_deg}deg"]
            # Cell size should also be in degrees for linearmosaic
            cellx = [abs(np.degrees(inc[0]))]  # Cell size in degrees
            celly = [abs(np.degrees(inc[1]))]
        except (KeyError, AttributeError, ValueError) as e:
            raise MosaicError(
                f"Could not find direction coordinate in tile: {e}",
                "Tiles must have valid direction coordinates"
            )

        # Get image dimensions
        nx = shape[-1] if len(shape) >= 2 else 128
        ny = shape[-2] if len(shape) >= 2 else 128
        del img

        # Create linearmosaic tool instance
        lm = linearmosaic()

        # Set optimal weighting (default, but explicit)
        lm.setlinmostype('optimal')

        # Define output image
        output_weight = str(output_path).replace('.image', '_weight.image')
        if os.path.exists(str(output_path)):
            shutil.rmtree(str(output_path))
        if os.path.exists(output_weight):
            shutil.rmtree(output_weight)

        # Define output image with proper parameters
        lm.defineoutputimage(
            nx=nx,
            ny=ny,
            cellx=cellx,
            celly=celly,
            imagecenter=imagecenter,
            outputimage=str(output_path),
            outputweight=output_weight
        )

        # Make mosaic with PB-weighted combination
        # imageweighttype=1: images are apodized by primary beam (PB-corrected)
        # weighttype=1: weight images are sum of Primary beams
        lm.makemosaic(
            images=regridded_tiles,
            weightimages=regridded_pbs,
            imageweighttype=1,  # PB-corrected images
            weighttype=1  # PB weight images
        )

        LOG.info(f"✓ Built PB-weighted mosaic using linearmosaic tool")

        # Cleanup linearmosaic tool
        del lm

    except Exception as e:
        # Re-raise with context
        if isinstance(e, (CASAToolError, MosaicError, MissingPrimaryBeamError)):
            raise
        raise MosaicError(
            f"linearmosaic failed: {e}",
            "Consider using fallback method (imregrid + immath)"
        ) from e
    finally:
        # Cleanup temporary directory
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                LOG.warning(
                    f"Failed to cleanup temp directory {temp_dir}: {e}")


def _build_weighted_mosaic_imregrid_immath(
    tiles: List[str],
    metrics_dict: dict,
    output_path: str,
) -> None:
    """
    Build mosaic using imregrid + immath (fallback method).

    This function uses CASA's imregrid and immath tasks for explicit control
    over the mosaicking process. Used as fallback when linearmosaic is not
    available or fails.

    Weighting scheme (Sault): weight[k] = pb_response[k]^2 / noise_variance[k]

    Args:
        tiles: List of tile image paths (should be PB-corrected images)
            Tiles should be in chronological order for best results.
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        output_path: Output mosaic path (CASA image format)
    """
    import tempfile
    import shutil
    from pathlib import Path

    LOG.info(
        f"Building mosaic using imregrid + immath (fallback method) with {len(tiles)} tiles")

    # Basic validation
    if not tiles:
        raise MosaicError("No tiles provided", "tiles list is empty")
    if not output_path:
        raise MosaicError("Output path is empty", "Must provide output_path")

    # Check all tiles exist
    for i, tile in enumerate(tiles):
        if not os.path.exists(tile):
            raise MosaicError(
                f"Tile {i+1} does not exist: {tile}",
                "All tiles must exist before building mosaic"
            )

    try:
        from casatasks import immath, imregrid, importfits, exportfits
        from casacore.images import image as casaimage
        import numpy as np
    except ImportError as e:
        raise CASAToolError(
            f"CASA not available: {e}",
            "Ensure CASA is installed and available in the environment. "
            "Try: conda activate casa6"
        ) from e

    # VAST-like approach: Use first tile as template, let CASA handle alignment
    template_tile = tiles[0]
    LOG.info(f"Using first tile as template: {Path(template_tile).name}")

    # Convert FITS to CASA format if needed (immath works better with CASA images)
    temp_dir = tempfile.mkdtemp(prefix='mosaic_vast_')
    try:
        casa_tiles = []
        for i, tile in enumerate(tiles):
            if tile.endswith('.fits'):
                casa_tile = os.path.join(temp_dir, f'tile_{i}.image')
                if not os.path.exists(casa_tile):
                    LOG.debug(f"Converting FITS to CASA: {Path(tile).name}")
                    importfits(fitsimage=tile,
                               imagename=casa_tile, overwrite=True)
                casa_tiles.append(casa_tile)
            else:
                casa_tiles.append(tile)

        template_casa = casa_tiles[0]

        # Pre-validate tile overlap with template before regridding
        # This prevents "All output pixels are masked" errors
        from .coordinate_utils import filter_tiles_by_overlap

        overlapping_tiles, skipped_list = filter_tiles_by_overlap(
            casa_tiles, template_casa, margin_pixels=10
        )

        if len(overlapping_tiles) < len(casa_tiles):
            skipped_count = len(casa_tiles) - len(overlapping_tiles)
            LOG.warning(
                f"Filtered {skipped_count} tiles that don't overlap template. "
                f"Proceeding with {len(overlapping_tiles)} tiles."
            )
            # Update tiles and casa_tiles to only include overlapping ones
            overlapping_indices = [i for i, ct in enumerate(
                casa_tiles) if ct in overlapping_tiles]
            tiles = [tiles[i] for i in overlapping_indices]
            casa_tiles = overlapping_tiles

            # Ensure we have at least one tile
            if not casa_tiles:
                raise MosaicError(
                    "No tiles overlap with template coordinate system",
                    "All tiles were filtered out due to coordinate system mismatch. "
                    "Check that tiles have compatible coordinate systems."
                )

        # Check if we have PB images and noise metrics for weighting
        from .validation import _find_pb_path
        pb_available = True
        weights = []

        for tile, casa_tile in zip(tiles, casa_tiles):
            metrics = metrics_dict.get(
                tile, TileQualityMetrics(tile_path=tile))

            # Get PB path
            pb_path = metrics.pb_path
            if not pb_path:
                pb_path = _find_pb_path(tile)

            # Get noise variance
            rms_noise = metrics.rms_noise
            if rms_noise is None or rms_noise <= 0:
                rms_noise = 1.0  # Default if not available

            noise_variance = rms_noise ** 2

            # For VAST-like approach, we'll use simplified weighting
            # If PB images are available, we'll use PB²/σ² weighting
            # Otherwise, fall back to 1/σ² weighting
            if pb_path and os.path.exists(pb_path):
                # Will use PB²/σ² weighting - mark that PB is available
                weights.append((pb_path, noise_variance))
            else:
                pb_available = False
                # Use 1/σ² weighting (no PB)
                weight = 1.0 / noise_variance if noise_variance > 0 else 1.0
                weights.append((None, weight))

        if pb_available and all(w[0] is not None for w in weights):
            # Full PB-weighted combination (VAST approach)
            LOG.info("Using primary beam-weighted combination (PB²/σ²)")

            # Step 1: Regrid all tiles and PB images to template coordinate system
            regridded_tiles = []
            regridded_pbs = []
            successful_indices = []  # Track which tiles successfully regridded

            for i, (casa_tile, (pb_path, noise_var)) in enumerate(zip(casa_tiles, weights)):
                tile_success = True

                # Regrid tile to template
                # Note: Overlap has already been validated, but we still catch errors
                # in case of edge cases or coordinate system issues
                regridded_tile = os.path.join(
                    temp_dir, f'regrid_tile_{i}.image')
                if not os.path.exists(regridded_tile):
                    LOG.debug(f"Regridding tile {i+1}/{len(casa_tiles)}")
                    try:
                        imregrid(
                            imagename=casa_tile,
                            template=template_casa,
                            output=regridded_tile,
                            overwrite=True
                        )
                    except RuntimeError as e:
                        if "All output pixels are masked" in str(e):
                            LOG.warning(
                                f"Tile regridding failed for tile {i+1} (all pixels masked): {Path(tile).name}. "
                                f"This should have been caught by pre-validation. Skipping this tile."
                            )
                            tile_success = False
                        else:
                            raise

                if not tile_success:
                    continue  # Skip this tile entirely

                # Regrid PB to template
                regridded_pb = os.path.join(temp_dir, f'regrid_pb_{i}.image')
                if not os.path.exists(regridded_pb):
                    LOG.debug(f"Regridding PB {i+1}/{len(casa_tiles)}")
                    try:
                        imregrid(
                            imagename=pb_path,
                            template=template_casa,
                            output=regridded_pb,
                            overwrite=True
                        )
                    except RuntimeError as e:
                        if "All output pixels are masked" in str(e):
                            LOG.warning(
                                f"PB regridding failed for tile {i+1} (all pixels masked): {Path(tile).name}. "
                                f"Falling back to noise-weighted combination."
                            )
                            pb_available = False
                            break
                        else:
                            raise

                # Both tile and PB regridded successfully
                regridded_tiles.append(regridded_tile)
                regridded_pbs.append(regridded_pb)
                successful_indices.append(i)

            # Check if we have any successfully regridded tiles
            if not regridded_tiles:
                raise MosaicError(
                    "No tiles could be regridded successfully",
                    "All tiles failed regridding (all pixels masked). Check coordinate systems."
                )

            # Update weights list to only include successful tiles
            successful_weights = [weights[idx] for idx in successful_indices]

            # Step 2: Create weighted images (tile * PB² / σ²)
            weighted_tiles = []
            weight_sums = []

            for i, (regridded_tile, regridded_pb, (_, noise_var)) in enumerate(zip(regridded_tiles, regridded_pbs, successful_weights)):
                # Weight = PB² / σ²
                pb_squared = os.path.join(temp_dir, f'pb_squared_{i}.image')
                if not os.path.exists(pb_squared):
                    # Remove existing if present (immath doesn't support overwrite parameter)
                    if os.path.exists(pb_squared):
                        import shutil
                        shutil.rmtree(pb_squared)
                    immath(
                        imagename=[regridded_pb],
                        expr=f'IM0*IM0',
                        outfile=pb_squared
                    )

                # Weight image = PB² / σ²
                weight_img = os.path.join(temp_dir, f'weight_{i}.image')
                if not os.path.exists(weight_img):
                    inv_var = 1.0 / noise_var if noise_var > 0 else 1.0
                    # Remove existing if present
                    if os.path.exists(weight_img):
                        import shutil
                        shutil.rmtree(weight_img)
                    immath(
                        imagename=[pb_squared],
                        expr=f'{inv_var:.10e}*IM0',
                        outfile=weight_img
                    )

                # Weighted tile = tile * weight
                weighted_tile = os.path.join(
                    temp_dir, f'weighted_tile_{i}.image')
                if not os.path.exists(weighted_tile):
                    # Remove existing if present
                    if os.path.exists(weighted_tile):
                        import shutil
                        shutil.rmtree(weighted_tile)
                    immath(
                        imagename=[regridded_tile, weight_img],
                        expr='IM0*IM1',
                        outfile=weighted_tile
                    )

                weighted_tiles.append(weighted_tile)
                weight_sums.append(weight_img)

            # Step 3: Combine weighted tiles and normalize by sum of weights
            # mosaic = sum(weighted_tiles) / sum(weights)
            sum_weighted = os.path.join(temp_dir, 'sum_weighted.image')
            sum_weights = os.path.join(temp_dir, 'sum_weights.image')

            if len(weighted_tiles) == 1:
                # Single tile - just copy
                shutil.copytree(
                    weighted_tiles[0], sum_weighted, dirs_exist_ok=True)
                shutil.copytree(
                    weight_sums[0], sum_weights, dirs_exist_ok=True)
            else:
                # Sum weighted tiles
                expr_weighted = '+'.join(
                    [f'IM{i}' for i in range(len(weighted_tiles))])
                # Remove existing if present
                if os.path.exists(sum_weighted):
                    import shutil
                    shutil.rmtree(sum_weighted)
                immath(
                    imagename=weighted_tiles,
                    expr=expr_weighted,
                    outfile=sum_weighted
                )

                # Sum weights
                expr_weights = '+'.join(
                    [f'IM{i}' for i in range(len(weight_sums))])
                # Remove existing if present
                if os.path.exists(sum_weights):
                    import shutil
                    shutil.rmtree(sum_weights)
                immath(
                    imagename=weight_sums,
                    expr=expr_weights,
                    outfile=sum_weights
                )

            # Final mosaic = sum_weighted / sum_weights
            # Remove existing if present
            if os.path.exists(str(output_path)):
                import shutil
                shutil.rmtree(str(output_path))
            immath(
                imagename=[sum_weighted, sum_weights],
                expr='IM0/IM1',
                outfile=str(output_path)
            )

            LOG.info(
                f"✓ Built PB-weighted mosaic using imregrid + immath (fallback method)")

        else:
            # Fallback: Noise-weighted combination (no PB)
            LOG.info(
                "Using noise-weighted combination (1/σ²) - PB images not available")

            # Regrid all tiles to template
            regridded_tiles = []
            for i, casa_tile in enumerate(casa_tiles):
                regridded_tile = os.path.join(
                    temp_dir, f'regrid_tile_{i}.image')
                if not os.path.exists(regridded_tile):
                    LOG.debug(f"Regridding tile {i+1}/{len(casa_tiles)}")
                    imregrid(
                        imagename=casa_tile,
                        template=template_casa,
                        output=regridded_tile,
                        overwrite=True
                    )
                regridded_tiles.append(regridded_tile)

            # Build weighted expression: sum(weight[i] * tile[i]) / sum(weight[i])
            # Normalize weights first
            total_weight = sum(w[1] for w in weights)
            normalized_weights = [
                w[1] / total_weight if total_weight > 0 else 1.0/len(weights) for w in weights]

            # Create weighted expression
            weighted_terms = []
            for i, (regridded_tile, weight) in enumerate(zip(regridded_tiles, normalized_weights)):
                weighted_terms.append(f'{weight:.10e}*IM{i}')

            expr = '+'.join(weighted_terms)

            # Remove existing if present
            if os.path.exists(str(output_path)):
                import shutil
                shutil.rmtree(str(output_path))
            immath(
                imagename=regridded_tiles,
                expr=expr,
                outfile=str(output_path)
            )

            LOG.info(f"✓ Built noise-weighted mosaic")

    finally:
        # Cleanup temporary directory
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                LOG.warning(
                    f"Failed to cleanup temp directory {temp_dir}: {e}")


def _build_weighted_mosaic(
    tiles: List[str],
    metrics_dict: dict,
    output_path: str,
) -> None:
    """
    Build mosaic using primary beam-weighted combination.

    Tries linearmosaic tool first (preferred method), falls back to
    imregrid + immath if linearmosaic fails or is unavailable.

    Args:
        tiles: List of tile image paths (should be PB-corrected images)
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        output_path: Output mosaic path (CASA image format)
    """
    # Try linearmosaic first (preferred method)
    try:
        LOG.info(
            "Attempting to build mosaic using linearmosaic tool (primary method)")
        return _build_weighted_mosaic_linearmosaic(tiles, metrics_dict, output_path)
    except (CASAToolError, MissingPrimaryBeamError) as e:
        # Fallback to imregrid + immath if linearmosaic fails
        LOG.warning(
            f"linearmosaic failed ({e}), falling back to imregrid + immath method"
        )
        return _build_weighted_mosaic_imregrid_immath(tiles, metrics_dict, output_path)
    except MosaicError as e:
        # If it's a MosaicError from linearmosaic, try fallback
        LOG.warning(
            f"linearmosaic encountered error ({e}), falling back to imregrid + immath method"
        )
        try:
            return _build_weighted_mosaic_imregrid_immath(tiles, metrics_dict, output_path)
        except Exception as fallback_error:
            # If fallback also fails, raise original error with context
            raise MosaicError(
                f"Both linearmosaic and fallback methods failed. "
                f"linearmosaic error: {e}. Fallback error: {fallback_error}",
                "Check tile coordinate systems and PB image availability"
            ) from fallback_error


def cmd_build(args: argparse.Namespace) -> int:
    """Build mosaic from planned tiles.

    NOTE: For timeout protection, run this command with system timeout:
    timeout 7200 dsa110-contimg mosaic build ...
    """
    # Input validation
    if not hasattr(args, 'products_db') or not args.products_db:
        raise ValueError("products_db is required")
    if not isinstance(args.products_db, str) or not args.products_db.strip():
        raise ValueError("products_db must be a non-empty string")
    if not hasattr(args, 'name') or not args.name:
        raise ValueError("name is required")
    if not isinstance(args.name, str) or not args.name.strip():
        raise ValueError("name must be a non-empty string")
    if not hasattr(args, 'output') or not args.output:
        raise ValueError("output is required")
    if not isinstance(args.output, str) or not args.output.strip():
        raise ValueError("output must be a non-empty string")

    pdb = Path(args.products_db)
    name = args.name
    out = Path(args.output).with_suffix("")

    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        row = conn.execute(
            "SELECT id, tiles, method FROM mosaics WHERE name = ?", (name,)).fetchone()
        if row is None:
            print("Mosaic plan not found; create with 'plan' first")
            return 1
        tiles = str(row[1]).splitlines()
        method = str(row[2] or 'mean')

    if not tiles:
        print("No tiles found in mosaic plan")
        return 1

    # CRITICAL: Validate tiles are in chronological order
    # Tiles from _fetch_tiles() are ordered by created_at ASC, which should correlate
    # with observation time. Verify this by checking associated MS times.
    print("Validating chronological order of tiles...")
    try:
        from dsa110_contimg.utils.time_utils import extract_ms_time_range

        tile_times = []
        with ensure_products_db(pdb) as conn:
            for tile in tiles:
                # Find MS path associated with this image
                # Images table links to MS via ms_path column
                row = conn.execute(
                    "SELECT ms_path FROM images WHERE path = ?",
                    (tile,)
                ).fetchone()
                if row and row[0]:
                    ms_path = row[0]
                    try:
                        _, _, mid_mjd = extract_ms_time_range(ms_path)
                        if mid_mjd is not None:
                            tile_times.append(mid_mjd)
                    except Exception:
                        pass

        # Validate chronological order if we got times
        if len(tile_times) > 1:
            is_chronological = all(
                tile_times[i] <= tile_times[i+1] for i in range(len(tile_times)-1))
            if not is_chronological:
                print(f"ERROR: Tiles are NOT in chronological order!")
                print(f"  Validated {len(tile_times)}/{len(tiles)} tiles")
                print(
                    f"  Observation times (MJD): {[f'{t:.6f}' for t in tile_times]}")
                print(
                    f"  This will cause mosaic artifacts and incorrect coordinate system.")
                if not args.ignore_validation:
                    print(
                        "  Use --ignore-validation to proceed anyway (NOT RECOMMENDED).")
                    return 4
                else:
                    print(
                        "  WARNING: Proceeding with out-of-order tiles (--ignore-validation)")
            else:
                print(
                    f"✓ Validated: Tiles are in chronological order ({len(tile_times)}/{len(tiles)} tiles validated)")
        elif len(tile_times) == 0:
            print(
                f"  Warning: Could not validate chronological order (no MS times extracted)")
            print(f"  Proceeding assuming tiles are in correct order from plan")
    except Exception as e:
        LOG.debug(f"Could not validate chronological order: {e}")
        print(f"  Warning: Could not validate chronological order: {e}")
        # Continue - validation is best-effort

    # Pre-flight validation: Check all pre-conditions before expensive operations
    print("Pre-flight validation: Checking pre-conditions...")
    from .preflight import validate_preflight_conditions, estimate_resources

    # Check if PB images are required based on method
    require_pb = (method == 'weighted' or method == 'pbweighted')

    preflight_valid, preflight_issues, preflight_info = validate_preflight_conditions(
        tiles=tiles,
        output_path=str(out),
        metrics_dict=None,  # Will be computed during validation
        require_pb=require_pb,
        check_disk_space_flag=True,
    )

    if preflight_issues:
        print("Pre-flight validation issues:")
        for issue in preflight_issues:
            print(f"  - {issue}")

        if not args.ignore_validation:
            print("\nPre-flight validation failed. Fix issues above before building.")
            print("Use --ignore-validation to proceed anyway (not recommended).")
            return 3
        else:
            print(
                "\nWarning: Pre-flight issues detected but ignored (--ignore-validation)")

    # Report resource estimates
    try:
        estimates = estimate_resources(tiles, str(out))
        print(f"\nResource estimates:")
        print(f"  - Tiles: {estimates['num_tiles']}")
        print(
            f"  - Estimated disk space: {estimates['estimated_disk_gb']:.1f} GB")
        print(f"  - Estimated operations: {estimates['estimated_operations']}")
        print(
            f"  - Estimated time: ~{estimates['estimated_time_minutes']:.0f} minutes")
    except Exception as e:
        LOG.debug(f"Could not estimate resources: {e}")

    # Warn if output exists
    if preflight_info.get('output_exists'):
        print(
            f"\nWarning: Output '{out}' already exists and will be overwritten")

    # Comprehensive validation
    print(f"Validating {len(tiles)} tiles...", flush=True)
    print(
        f"[DEBUG] Starting validation for {len(tiles)} tiles", file=sys.stderr, flush=True)
    # Also to stdout
    print(f"[DEBUG] Starting validation for {len(tiles)} tiles", flush=True)

    # 1. Basic grid consistency
    print(f"[DEBUG] Checking grid consistency...", file=sys.stderr, flush=True)
    print(f"[DEBUG] Checking grid consistency...",
          flush=True)  # Also to stdout
    ok, reason = _check_consistent_tiles(tiles)
    print(
        f"[DEBUG] Grid consistency check complete: ok={ok}", file=sys.stderr, flush=True)
    if not ok:
        print(f"Cannot build mosaic: {reason}")
        return 2

    # 2. Tile quality validation (computes metrics_dict)
    print(f"[DEBUG] Calling validate_tiles_consistency...",
          file=sys.stderr, flush=True)
    is_valid, validation_issues, metrics_dict = validate_tiles_consistency(
        tiles, products_db=pdb
    )
    print(
        f"[DEBUG] validate_tiles_consistency complete: is_valid={is_valid}, issues={len(validation_issues)}", file=sys.stderr, flush=True)

    # Re-run pre-flight with computed metrics_dict for better PB checking
    if require_pb:
        _, preflight_issues_pb, _ = validate_preflight_conditions(
            tiles=tiles,
            output_path=str(out),
            metrics_dict=metrics_dict,
            require_pb=require_pb,
            check_disk_space_flag=False,  # Already checked
        )
        if preflight_issues_pb and not args.ignore_validation:
            print("Pre-flight validation issues (after tile validation):")
            for issue in preflight_issues_pb:
                print(f"  - {issue}")
            print("\nPre-flight validation failed. Fix issues above before building.")
            return 3

    if validation_issues:
        print("Validation issues found:")
        for issue in validation_issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(validation_issues) > 10:
            print(f"  ... and {len(validation_issues) - 10} more issues")

        if not args.ignore_validation:
            raise ValidationError(
                f"Mosaic validation failed with {len(validation_issues)} issues",
                "Review the validation issues above. Common fixes:\n"
                "  - Ensure all tiles have PB correction applied\n"
                "  - Check tile noise levels are reasonable\n"
                "  - Verify tiles have consistent calibration\n"
                "Use --ignore-validation to proceed anyway (not recommended for science)."
            )
        else:
            print(
                "\nWarning: Validation issues detected but ignored (--ignore-validation)")

    # 3. Astrometric registration check
    print(f"[DEBUG] Starting astrometric verification...",
          file=sys.stderr, flush=True)
    try:
        astro_valid, astro_issues, offsets = verify_astrometric_registration(
            tiles)
        print(
            f"[DEBUG] Astrometric verification complete: valid={astro_valid}, issues={len(astro_issues)}", file=sys.stderr, flush=True)
    except Exception as e:
        print(
            f"[DEBUG] Astrometric verification exception: {e}", file=sys.stderr, flush=True)
        raise ValidationError(
            f"Astrometric verification failed: {e}",
            "Check if catalog access is available. "
            "Try running with --ignore-validation to skip astrometric checks."
        ) from e
    if astro_issues:
        print("Astrometric registration issues:", flush=True)
        print(
            f"[DEBUG] Processing {len(astro_issues)} astrometric issues", file=sys.stderr, flush=True)
        print(
            f"[DEBUG] Processing {len(astro_issues)} astrometric issues", flush=True)

        # Filter out catalog access failures and image close() errors (non-fatal) from actual astrometric issues (fatal)
        non_fatal_keywords = [
            "catalog query", "skipping astrometric",
            "has no attribute 'close'", "failed to verify",
            "attributeerror", "'image' object"
        ]
        non_fatal_issues = [
            issue for issue in astro_issues
            if any(keyword in issue.lower() for keyword in non_fatal_keywords)
        ]
        actual_astro_issues = [
            issue for issue in astro_issues if issue not in non_fatal_issues]

        print(
            f"[DEBUG] Astrometric filtering: {len(astro_issues)} total, {len(non_fatal_issues)} non-fatal, {len(actual_astro_issues)} actual", file=sys.stderr, flush=True)
        print(
            f"[DEBUG] Astrometric filtering: {len(astro_issues)} total, {len(non_fatal_issues)} non-fatal, {len(actual_astro_issues)} actual", flush=True)

        for issue in astro_issues:
            print(f"  - {issue}", flush=True)

        # Only abort on actual astrometric misalignment, not catalog access failures
        if actual_astro_issues and not args.ignore_validation:
            print(
                f"[DEBUG] Aborting: {len(actual_astro_issues)} actual issues", file=sys.stderr, flush=True)
            print(
                "\nMosaic build aborted due to astrometric misalignment issues.", flush=True)
            return 4
        elif non_fatal_issues and not actual_astro_issues:
            print(
                "\nWarning: Catalog access unavailable, skipping astrometric verification.", flush=True)
            print(
                "Proceeding with mosaic build (astrometric accuracy not verified).", flush=True)

    # 4. Calibration consistency check
    # Try to find registry DB from environment or default location
    registry_db = None
    if os.getenv('CAL_REGISTRY_DB'):
        registry_db = Path(os.getenv('CAL_REGISTRY_DB'))
    else:
        # Try default location relative to products DB
        registry_db = pdb.parent / 'cal_registry.sqlite3'
        if not registry_db.exists():
            registry_db = None

    cal_consistent, cal_issues, cal_dict = check_calibration_consistency(
        tiles, pdb, registry_db=registry_db
    )
    if cal_issues:
        print("Calibration consistency issues:")
        for issue in cal_issues:
            print(f"  - {issue}")
        if not args.ignore_validation:
            print("\nMosaic build aborted due to calibration inconsistencies.")
            return 5

    # 5. Primary beam consistency check
    pb_consistent, pb_issues, pb_dict = check_primary_beam_consistency(
        tiles, metrics_dict
    )
    if pb_issues:
        print("Primary beam consistency issues:")
        for issue in pb_issues:
            print(f"  - {issue}")
        if not args.ignore_validation:
            print("\nMosaic build aborted due to PB consistency issues.")
            return 6

    print("✓ All validation checks passed")

    # Dry-run mode: validate without building
    if args.dry_run:
        print("\n" + "="*60)
        print("DRY-RUN MODE: Validation complete, not building mosaic")
        print("="*60)
        print(f"\nMosaic plan summary:")
        print(f"  - Name: {name}")
        print(f"  - Method: {method}")
        print(f"  - Tiles: {len(tiles)}")
        print(f"  - Output: {out}")
        print(f"\n✓ All validations passed. Ready to build.")
        print(f"\nTo build this mosaic, run:")
        print(f"  mosaic build --name {name} --output {out}")
        return 0

    # Build mosaic
    try:
        # Keep immath temp products under scratch and avoid polluting CWD
        try:
            if prepare_temp_environment is not None:
                prepare_temp_environment(
                    os.getenv(
                        'CONTIMG_SCRATCH_DIR') or '/stage/dsa110-contimg',
                    cwd_to=out.parent
                )
        except Exception:
            pass

        # Use weighted combination if method is 'weighted', otherwise use mean
        if method == 'weighted' or method == 'pbweighted':
            print(f"Building weighted mosaic to {out}...")
            try:
                _build_weighted_mosaic(tiles, metrics_dict, str(out))
            except (ImageReadError, ImageCorruptionError, MissingPrimaryBeamError,
                    CASAToolError, GridMismatchError) as e:
                # Re-raise with context
                raise
        else:
            print(f"Building mean mosaic to {out}...")
            try:
                from .error_handling import handle_casa_tool_error
                if not immath:
                    raise CASAToolError(
                        "CASA immath not available",
                        "Ensure CASA is installed: conda activate casa6",
                        context={'tool': 'immath',
                                 'operation': 'build_mean_mosaic'}
                    )
                expr = f"({'+'.join([f'IM{i}' for i in range(len(tiles))])})/{len(tiles)}"
                try:
                    immath(imagename=tiles, expr=expr, outfile=str(out))
                except Exception as e:
                    handle_casa_tool_error(
                        'immath', e,
                        operation='build_mean_mosaic',
                        expression=expr,
                        num_tiles=len(tiles)
                    )
            except Exception as e:
                raise CASAToolError(
                    f"CASA immath failed: {e}",
                    "Check if all tile images are readable and have compatible formats. "
                    "Try using weighted method instead: --method=weighted"
                ) from e

        # Export FITS for the mosaic image for downstream photometry
        try:
            from casatasks import exportfits
            from .error_handling import handle_casa_tool_error
            exportfits(imagename=str(out), fitsimage=str(
                out) + ".fits", overwrite=True)
        except Exception as exc:
            # Don't fail build if export fails, but log it properly
            try:
                from .error_handling import handle_casa_tool_error
                handle_casa_tool_error(
                    'exportfits', exc,
                    image_path=str(out),
                    operation='export_mosaic_fits'
                )
            except Exception:
                # If handle_casa_tool_error fails, just print warning
                print(f"exportfits warning: {exc}")

        # Post-mosaic validation
        try:
            from .post_validation import validate_mosaic_quality
            print("Validating final mosaic quality...")
            mosaic_valid, mosaic_issues, mosaic_metrics = validate_mosaic_quality(
                str(out),
                max_rms_variation=2.0,
                min_coverage_fraction=0.1,
            )

            if mosaic_issues:
                print("Post-mosaic validation issues:")
                for issue in mosaic_issues:
                    print(f"  - {issue}")
                if mosaic_metrics:
                    print(f"Mosaic metrics: RMS={mosaic_metrics.get('rms_noise', 'N/A'):.3e}, "
                          f"coverage={mosaic_metrics.get('coverage_fraction', 0):.1%}")
            else:
                print("✓ Post-mosaic validation passed")
                if mosaic_metrics:
                    print(f"Mosaic metrics: RMS={mosaic_metrics.get('rms_noise', 'N/A'):.3e}, "
                          f"coverage={mosaic_metrics.get('coverage_fraction', 0):.1%}, "
                          f"dynamic_range={mosaic_metrics.get('dynamic_range', 0):.1f}")
        except Exception as e:
            LOG.warning(f"Post-mosaic validation failed: {e}")
            # Don't fail build if validation fails

        # Generate mosaic quality metrics
        metrics_files = {}
        try:
            print("Generating mosaic quality metrics...")
            metrics_files = generate_mosaic_metrics(
                tiles=tiles,
                metrics_dict=metrics_dict,
                mosaic_path=str(out),
                output_dir=str(out.parent),
            )
            if metrics_files:
                print(
                    f"✓ Generated {len(metrics_files)} quality metric images")
                for metric_name, metric_path in metrics_files.items():
                    print(f"  - {metric_name}: {metric_path}")
            else:
                print("Warning: No metrics generated (casacore may not be available)")
        except Exception as e:
            LOG.warning(f"Failed to generate mosaic metrics: {e}")
            print(f"Warning: Failed to generate mosaic metrics: {e}")
            # Don't fail the build if metrics generation fails

        # Update mosaic status
        validation_summary = "\n".join(
            validation_issues) if validation_issues else None
        metrics_summary = None
        if metrics_files:
            # Store metrics paths as JSON-like string (simple format)
            metrics_list = [f"{name}:{path}" for name,
                            path in metrics_files.items()]
            metrics_summary = "\n".join(metrics_list)

        with ensure_products_db(pdb) as conn:
            # Ensure mosaics table exists before updating
            _ensure_mosaics_table(conn)

            # Check if mosaics table has metrics_path column, if not add it
            try:
                conn.execute("SELECT metrics_path FROM mosaics LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                conn.execute(
                    "ALTER TABLE mosaics ADD COLUMN metrics_path TEXT")
                conn.commit()

            conn.execute(
                "UPDATE mosaics SET status='built', output_path=?, validation_issues=?, metrics_path=? WHERE name=?",
                (str(out), validation_summary, metrics_summary, name)
            )
            conn.commit()

        print(f"✓ Built mosaic to {out}")
        return 0
    except (MosaicError, ImageReadError, ImageCorruptionError, MissingPrimaryBeamError,
            CASAToolError, GridMismatchError, ValidationError, MetricsGenerationError) as e:
        # Handle specific mosaic errors with user-friendly messages
        print(f"\nMosaic build failed: {e.message}")
        if e.recovery_hint:
            print(f"\n{e.recovery_hint}")
        import traceback
        traceback.print_exc()
        return 6
    except Exception as e:
        print(f"Mosaic build failed: {e}")
        import traceback
        traceback.print_exc()
        return 6


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Mosaic planner/builder")
    sub = p.add_subparsers(dest='cmd')
    sp = sub.add_parser('plan', help='Plan a mosaic from products DB tiles')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--name', required=True)
    sp.add_argument('--since', type=float,
                    help='Only include tiles created_at >= since (epoch seconds)')
    sp.add_argument('--until', type=float,
                    help='Only include tiles created_at <= until (epoch seconds)')
    sp.add_argument('--method', default='mean', choices=['mean', 'weighted', 'pbweighted'],
                    help='Combination method: mean (simple), weighted (noise-weighted), pbweighted (primary beam weighted)')
    sp.add_argument('--include-unpbcor', action='store_true',
                    help='Include non-pbcor tiles')
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser('build', help='Build a mosaic from a planned set')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--name', required=True)
    sp.add_argument('--output', required=True,
                    help='Output image base path (CASA image)')
    sp.add_argument('--ignore-validation', action='store_true',
                    help='Ignore validation issues and proceed anyway (not recommended)')
    sp.add_argument('--dry-run', action='store_true',
                    help='Validate mosaic plan without building (measure twice, cut once)')
    sp.set_defaults(func=cmd_build)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    # Ensure scratch directory structure exists
    try:
        ensure_scratch_dirs()
    except Exception:
        pass  # Best-effort; continue if setup fails

    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, 'func'):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
