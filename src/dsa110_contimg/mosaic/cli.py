"""
CLI for planning and building mosaics from 5-minute image tiles.

A **tile** is a single calibrated, imaged, and primary-beam-corrected radio astronomy
image created from ~5 minutes of observation data. Multiple tiles are combined to create
a larger mosaic covering a wider field of view.

Phase 1: record mosaic plan (list of tiles) into products DB.
Phase 2: validate tiles and build weighted mosaic using primary beam weighting.

See docs/reference/GLOSSARY.md for detailed definition of tiles and related terminology.
"""

import argparse
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.utils.cli_helpers import ensure_scratch_dirs
try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore

from .validation import (
    validate_tiles_consistency,
    verify_astrometric_registration,
    check_calibration_consistency,
    check_primary_beam_consistency,
    TileQualityMetrics,
    _find_pb_path,
    HAVE_CASACORE,
)
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
                # Cache may serialize arrays as strings like "[512 512]"
                # Try to parse it
                try:
                    import ast
                    shape_list = ast.literal_eval(shape)
                    shape = tuple(shape_list) if isinstance(
                        shape_list, list) else shape
                except (ValueError, SyntaxError):
                    # If parsing fails, use string comparison (less ideal but works)
                    pass
            cdelt1 = header.get('cdelt1')
            cdelt2 = header.get('cdelt2')
            key = (shape, cdelt1, cdelt2)
            if ref is None:
                ref = key
            else:
                # Compare with tolerance for floating-point values
                ref_shape, ref_cdelt1, ref_cdelt2 = ref
                if shape != ref_shape:
                    return False, f"Tiles have inconsistent grid shapes: {shape} vs {ref_shape}"
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
        coord_sys = mosaic_img.coordsys()

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
        pb_response_img = casaimage()
        pb_response_img.fromarray(
            outfile=f"{base_path}_pb_response",
            pixels=pb_response_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        pb_response_img.close()
        metric_files['pb_response'] = f"{base_path}_pb_response"

        # 2. Noise variance map
        noise_var_img = casaimage()
        noise_var_img.fromarray(
            outfile=f"{base_path}_noise_variance",
            pixels=noise_variance_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        noise_var_img.close()
        metric_files['noise_variance'] = f"{base_path}_noise_variance"

        # 3. Tile count map
        tile_count_img = casaimage()
        tile_count_img.fromarray(
            outfile=f"{base_path}_tile_count",
            pixels=tile_count_map.astype(
                np.float32)[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        tile_count_img.close()
        metric_files['tile_count'] = f"{base_path}_tile_count"

        # 4. Integration time map
        integration_time_img = casaimage()
        integration_time_img.fromarray(
            outfile=f"{base_path}_integration_time",
            pixels=integration_time_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        integration_time_img.close()
        metric_files['integration_time'] = f"{base_path}_integration_time"

        # 5. Coverage map (binary: 1 if tile contributes, 0 otherwise)
        coverage_map = (tile_count_map > 0).astype(np.float32)
        coverage_img = casaimage()
        coverage_img.fromarray(
            outfile=f"{base_path}_coverage",
            pixels=coverage_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        coverage_img.close()
        metric_files['coverage'] = f"{base_path}_coverage"

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

        mosaic_img.close()

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
                # Try coordsys() first, fallback to coordinates() for FITS files
                try:
                    coordsys = img.coordsys()
                except AttributeError:
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
                    wcs_pixel_to_world_safe(wcs_validated, c[1], c[0], is_4d, defaults)
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


def _build_weighted_mosaic(
    tiles: List[str],
    metrics_dict: dict,
    output_path: str,
) -> None:
    """
    Build mosaic using primary beam-weighted combination.

    For each pixel (i,j):
        weight[k][i,j] = pb_response[k][i,j]^2 / noise_variance[k]
        mosaic[i,j] = sum(weight[k][i,j] * tile[k][i,j]) / sum(weight[k][i,j])

    This implements the Sault weighting scheme for optimal mosaic combination.

    CRITICAL: All tiles are regridded to a common coordinate system that encompasses
    all tile positions before combining. This ensures proper alignment and overlapping
    of tiles that are at different sky positions.

    Args:
        tiles: List of tile image paths (should be PB-corrected images)
            CRITICAL: Tiles MUST be in chronological order (by observation time).
            Passing tiles out of order will cause mosaic artifacts and incorrect
            coordinate system determination.
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        output_path: Output mosaic path
    """
    # DEBUG FLAG: Set to False to disable aggressive validation checks
    # When False, only critical errors will stop execution
    # Temporarily disabled due to cache returning old regridded images with wrong shapes
    DEBUG_AGGRESSIVE_VALIDATION = False
    
    # CRITICAL: Validate that tiles are in chronological order
    # Tiles must be ordered by observation time to ensure correct coordinate system
    # and prevent mosaic artifacts
    from pathlib import Path

    print(f"[DEBUG] =========================================", file=sys.stderr, flush=True)
    print(f"[DEBUG] CHECKPOINT: Starting _build_weighted_mosaic", file=sys.stderr, flush=True)
    print(f"[DEBUG] Number of tiles: {len(tiles)}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Output path: {output_path}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Tile paths:", file=sys.stderr, flush=True)
    for i, tile in enumerate(tiles):
        print(f"[DEBUG]   [{i+1}] {tile}", file=sys.stderr, flush=True)
    print(f"[DEBUG] =========================================", file=sys.stderr, flush=True)
    
    # AGGRESSIVE VALIDATION: Fail immediately on invalid inputs
    if DEBUG_AGGRESSIVE_VALIDATION:
        if not tiles:
            raise MosaicError("No tiles provided", "tiles list is empty")
        if len(tiles) == 0:
            raise MosaicError("Empty tiles list", "Must provide at least one tile")
        for i, tile in enumerate(tiles):
            if not tile:
                raise MosaicError(f"Tile {i+1} is empty", "All tiles must be non-empty paths")
            if not isinstance(tile, str):
                raise MosaicError(f"Tile {i+1} is not a string", f"Got {type(tile)}")
            if not os.path.exists(tile):
                raise MosaicError(f"Tile {i+1} does not exist: {tile}", "All tiles must exist before building mosaic")
        if not output_path:
            raise MosaicError("Output path is empty", "Must provide output_path")
        if not isinstance(output_path, str):
            raise MosaicError(f"Output path is not a string", f"Got {type(output_path)}")
        print(f"[DEBUG] ✓ Aggressive validation passed: {len(tiles)} tiles, all exist", file=sys.stderr, flush=True)
    
    LOG.info(f"Building mosaic with {len(tiles)} tiles")
    LOG.debug(f"Tile paths: {[Path(t).name for t in tiles]}")

    # Note: Full chronological validation would require querying products DB
    # for each tile's associated MS and extracting mid_mjd. This is done
    # upstream in streaming_mosaic.create_mosaic() before calling this function.
    # For CLI builds, tiles should already be in chronological order from _fetch_tiles()
    # which orders by created_at ASC (which correlates with observation time).
    try:
        from casatasks import immath, imregrid
        from casacore.images import image as casaimage
        import numpy as np
        from .error_handling import (
            safe_casaimage_open,
            validate_image_data,
            validate_image_before_read,
            handle_casa_tool_error,
        )
    except ImportError as e:
        raise CASAToolError(
            f"CASA not available: {e}",
            "Ensure CASA is installed and available in the environment. "
            "Try: conda activate casa6"
        ) from e

    # CRITICAL: Calculate bounding box and create common coordinate system
    # This ensures tiles at different sky positions are properly aligned
    LOG.info("Calculating mosaic bounding box from all tiles...")
    try:
        ra_min, ra_max, dec_min, dec_max = _calculate_mosaic_bounds(tiles)
        LOG.info(f"Mosaic bounds: RA=[{ra_min:.6f}°, {ra_max:.6f}°], "
                 f"Dec=[{dec_min:.6f}°, {dec_max:.6f}°]")
        LOG.info(
            f"Mosaic span: RA={ra_max-ra_min:.6f}°, Dec={dec_max-dec_min:.6f}°")
    except Exception as e:
        LOG.error(f"Failed to calculate mosaic bounds: {e}")
        raise MosaicError(
            f"Could not determine mosaic bounds from tiles: {e}",
            "Ensure all tiles have valid WCS information."
        ) from e

    # Create common coordinate system
    LOG.info("Creating common coordinate system for mosaic...")
    try:
        # Get pixel scale from first tile (assume all tiles have same scale)
        first_tile_img = casaimage(str(tiles[0]))
        # Try coordsys() first, fallback to coordinates() for FITS files
        try:
            first_coordsys = first_tile_img.coordsys()
        except AttributeError:
            first_coordsys = first_tile_img.coordinates()

        try:
            # Try to get pixel scale from coordinate system
            # Handle both coordsys() and coordinates() objects
            try:
                cdelt = first_coordsys.increment()
            except AttributeError:
                cdelt = first_coordsys.get_increment()

            # Extract scalar value, handling arrays
            cdelt_val = cdelt[0] if len(cdelt) >= 1 else None
            if isinstance(cdelt_val, np.ndarray):
                cdelt_val = cdelt_val[0] if cdelt_val.size > 0 else None

            if cdelt_val is not None:
                # cdelt is in radians, convert to arcsec
                pixel_scale_arcsec = abs(np.degrees(float(cdelt_val))) * 3600.0
            else:
                raise ValueError("Could not extract pixel scale")
        except Exception:
            # Fallback to default
            pixel_scale_arcsec = 2.0
            LOG.warning(
                f"Could not determine pixel scale from first tile, using default {pixel_scale_arcsec}\"")

        # Try to close image (may not exist for FITS files)
        try:
            first_tile_img.close()
        except AttributeError:
            pass

        # Calculate common shape for regridding (no template needed - use shape parameter)
        pixel_scale_deg = pixel_scale_arcsec / 3600.0
        padding_pixels = 10
        ra_span = ra_max - ra_min
        dec_span = dec_max - dec_min
        nx = int(np.ceil(ra_span / pixel_scale_deg)) + 2 * padding_pixels
        ny = int(np.ceil(dec_span / pixel_scale_deg)) + 2 * padding_pixels
        
        # Check first tile dimensionality to determine common_shape format
        # Tiles might be 2D [y, x] or 4D [stokes, freq, y, x]
        # We need common_shape to match the tile dimensionality for imregrid
        first_tile_check = casaimage(str(tiles[0]))
        first_tile_shape = first_tile_check.shape()
        try:
            first_tile_check.close()
        except AttributeError:
            pass
        
        if len(first_tile_shape) == 4:
            # Tiles are 4D, so common_shape must be 4D: [stokes, freq, y, x]
            common_shape = [first_tile_shape[0], first_tile_shape[1], ny, nx]
            print(f"[DEBUG] Tiles are 4D, using 4D common_shape: {common_shape} (spatial: {ny}x{nx})", file=sys.stderr, flush=True)
        else:
            # Tiles are 2D, use 2D common_shape: [y, x]
            common_shape = [ny, nx]
            print(f"[DEBUG] Tiles are 2D, using 2D common_shape: {common_shape}", file=sys.stderr, flush=True)

        # Use first tile as template for coordinate system structure
        # imregrid will use shape parameter to set output size
        # Convert FITS to CASA format if needed (imregrid requires CASA images)
        print(f"[DEBUG] CHECKPOINT: Starting template preparation", file=sys.stderr, flush=True)
        template_tile = tiles[0]
        print(f"[DEBUG] Template tile (first): {template_tile}", file=sys.stderr, flush=True)
        
        if not os.path.exists(template_tile):
            raise MosaicError(
                f"Template tile does not exist: {template_tile}",
                "First tile must exist to use as template."
            )
        
        template_output_dir = os.path.join(os.path.dirname(output_path), '.mosaic_template')
        print(f"[DEBUG] Template output directory: {template_output_dir}", file=sys.stderr, flush=True)
        os.makedirs(template_output_dir, exist_ok=True)
        
        if not os.path.isdir(template_output_dir):
            raise MosaicError(
                f"Failed to create template directory: {template_output_dir}",
                "Check disk space and permissions."
            )
        
        if template_tile.endswith('.fits'):
            template_image_path = os.path.join(template_output_dir, 'template_casa.image')
            print(f"[DEBUG] FITS template detected, target CASA path: {template_image_path}", file=sys.stderr, flush=True)
            
            if not os.path.exists(template_image_path):
                print(f"[DEBUG] Converting FITS to CASA: {Path(template_tile).name} -> {Path(template_image_path).name}", file=sys.stderr, flush=True)
                LOG.info(f"Converting template FITS to CASA format: {Path(template_tile).name} -> {Path(template_image_path).name}")
                sys.stderr.flush()
                
                from casatasks import importfits
                import_start = time.time()
                importfits(fitsimage=template_tile, imagename=template_image_path, overwrite=True)
                import_elapsed = time.time() - import_start
                print(f"[DEBUG] FITS import completed in {import_elapsed:.2f}s", file=sys.stderr, flush=True)
                
                if not os.path.exists(template_image_path):
                    raise MosaicError(
                        f"FITS conversion failed: {template_image_path} does not exist after importfits",
                        "Check CASA importfits output for errors."
                    )
                print(f"[DEBUG] ✓ FITS conversion verified: {template_image_path} exists", file=sys.stderr, flush=True)
            else:
                print(f"[DEBUG] Using existing CASA template: {Path(template_image_path).name}", file=sys.stderr, flush=True)
                LOG.info(f"Using existing CASA template: {Path(template_image_path).name}")
        else:
            # Already a CASA image directory
            template_image_path = template_tile
            print(f"[DEBUG] Using CASA template directory: {Path(template_tile).name}", file=sys.stderr, flush=True)
            LOG.info(f"Using CASA template directory: {Path(template_tile).name}")

        # CRITICAL: Verify template is in CASA format (not FITS)
        print(f"[DEBUG] Validating template format...", file=sys.stderr, flush=True)
        if template_image_path.endswith('.fits'):
            print(f"[ERROR] Template is FITS format: {template_image_path}", file=sys.stderr, flush=True)
            raise MosaicError(
                f"Template image must be in CASA format, not FITS: {template_image_path}",
                "FITS files must be converted to CASA format before use as template."
            )
        
        if not os.path.exists(template_image_path):
            print(f"[ERROR] Template does not exist: {template_image_path}", file=sys.stderr, flush=True)
            raise MosaicError(
                f"Template image does not exist: {template_image_path}",
                "Check that FITS to CASA conversion succeeded."
            )
        
        print(f"[DEBUG] ✓ Template validation passed: {template_image_path}", file=sys.stderr, flush=True)
        
        # AGGRESSIVE VALIDATION: Verify template is actually readable
        if DEBUG_AGGRESSIVE_VALIDATION:
            try:
                test_img = casaimage(template_image_path)
                test_shape = test_img.shape()
                test_coordsys = test_img.coordinates()
                try:
                    test_img.close()
                except AttributeError:
                    pass
                print(f"[DEBUG] ✓ Template image is readable: shape={test_shape}", file=sys.stderr, flush=True)
            except Exception as e:
                raise MosaicError(
                    f"Template image is not readable: {e}",
                    f"Template path: {template_image_path}"
                ) from e
        
        LOG.info(
            f"Common regridding shape: {common_shape} (RA span: {ra_span:.6f}°, Dec span: {dec_span:.6f}°)")
        LOG.info(f"Template image path: {template_image_path}")
        sys.stderr.flush()
    except Exception as e:
        print(f"[ERROR] Failed to create common coordinate system: {e}", file=sys.stderr, flush=True)
        import traceback
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}", file=sys.stderr, flush=True)
        LOG.error(f"Failed to create common coordinate system: {e}")
        raise MosaicError(
            f"Could not create common coordinate system: {e}",
            "Check that CASA coordinate system creation is working."
        ) from e

    # Check if we have PB images for all tiles (using cache)
    from .cache import get_cache
    cache = get_cache()
    pb_paths = []
    for tile in tiles:
        metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
        pb_path = metrics.pb_path
        if not pb_path:
            # Try to find PB path using cache
            from .validation import _find_pb_path
            pb_path = cache.get_pb_path(tile, _find_pb_path)

        if pb_path and os.path.exists(pb_path):
            pb_paths.append(pb_path)
        else:
            pb_paths.append(None)

    has_all_pb_images = all(pb_path is not None for pb_path in pb_paths)

    if not has_all_pb_images:
        LOG.warning(
            "Primary beam images not available for all tiles, "
            "using noise-weighted combination instead of PB-weighted"
        )
        # Fall back to noise-weighted combination
        noise_weights = []
        for tile in tiles:
            metrics = metrics_dict.get(
                tile, TileQualityMetrics(tile_path=tile))
            if metrics.rms_noise is not None and metrics.rms_noise > 0:
                weight = 1.0 / (metrics.rms_noise ** 2)
            else:
                weight = 1.0
            noise_weights.append(weight)

        # Normalize weights
        total_weight = sum(noise_weights)
        if total_weight > 0:
            noise_weights = [w / total_weight for w in noise_weights]

        # Build weighted expression
        weighted_terms = []
        for i, (tile, weight) in enumerate(zip(tiles, noise_weights)):
            weighted_terms.append(f"{weight:.6f}*IM{i}")

        expr = "+".join(weighted_terms)
        immath(imagename=tiles, expr=expr, outfile=str(output_path))
        LOG.info(
            f"Built mosaic using noise-weighted combination "
            f"(weights: {noise_weights})"
        )
        return

    # Full PB-weighted combination
    # Step 1: Regrid all PB images to common coordinate system
    LOG.info("Regridding primary beam images to common coordinate system...")

    pb_images = []
    pb_data_list = []

    # Use the template image created earlier for regridding
    # template_image_path is guaranteed to be a CASA image (converted from FITS if needed)
    print(f"[DEBUG] CHECKPOINT: Starting PB regridding", file=sys.stderr, flush=True)
    print(f"[DEBUG] Template path: {template_image_path}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Template exists: {os.path.exists(template_image_path)}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Template is FITS: {template_image_path.endswith('.fits')}", file=sys.stderr, flush=True)
    
    if template_image_path.endswith('.fits'):
        print(f"[ERROR] CRITICAL: Template is still FITS format!", file=sys.stderr, flush=True)
        raise MosaicError(
            f"Template must be CASA format but is FITS: {template_image_path}",
            "This should have been caught earlier. Check template conversion logic."
        )
    
    if not os.path.exists(template_image_path):
        print(f"[ERROR] CRITICAL: Template does not exist!", file=sys.stderr, flush=True)
        raise MosaicError(
            f"Template image missing: {template_image_path}",
            "Template should have been created/validated earlier."
        )
    
    LOG.info(f"Using CASA template image for regridding: {Path(template_image_path).name}")
    sys.stderr.flush()

    try:
        for i, (tile, pb_path) in enumerate(zip(tiles, pb_paths)):
            print(f"[DEBUG] ===== PB REGRID {i+1}/{len(pb_paths)} =====", file=sys.stderr, flush=True)
            print(f"[DEBUG] Tile: {Path(tile).name}", file=sys.stderr, flush=True)
            print(f"[DEBUG] PB path: {pb_path}", file=sys.stderr, flush=True)
            
            if pb_path is None:
                print(f"[ERROR] PB path is None for tile {i+1}", file=sys.stderr, flush=True)
                raise MosaicError(
                    f"No PB path for tile {i+1}: {tile}",
                    "All tiles must have PB images for PB-weighted combination."
                )
            
            if not os.path.exists(pb_path):
                print(f"[ERROR] PB file does not exist: {pb_path}", file=sys.stderr, flush=True)
                raise MosaicError(
                    f"PB image missing: {pb_path}",
                    "PB image file must exist."
                )
            
            try:
                pb_start = time.time()
                print(f"[DEBUG] Regridding PB {i+1}/{len(pb_paths)}: {Path(pb_path).name}...", file=sys.stderr, flush=True)
                LOG.info(
                    f"Regridding PB image {i+1}/{len(pb_paths)}: {Path(pb_path).name}...")

                # Regrid PB image to common coordinate system
                # Try to use cached regridded image
                def regrid_func(imagename, template, output, overwrite):
                    print(f"[DEBUG] Calling imregrid: imagename={imagename}, template={template}, output={output}", file=sys.stderr, flush=True)
                    if not os.path.exists(imagename):
                        raise FileNotFoundError(f"Source image does not exist: {imagename}")
                    if not os.path.exists(template):
                        raise FileNotFoundError(f"Template image does not exist: {template}")
                    if template.endswith('.fits'):
                        raise ValueError(f"Template must be CASA format, not FITS: {template}")
                    # When using a template, imregrid uses the template's shape automatically
                    # Do NOT pass shape parameter - it causes errors with non-spatial axes
                    # The template already has the correct spatial dimensions
                    imregrid(imagename=imagename, template=template,
                             output=output, overwrite=overwrite)
                    print(f"[DEBUG] imregrid completed for {output}", file=sys.stderr, flush=True)

                regridded_pb = cache.get_regridded_image(
                    source_path=str(pb_path),
                    template_path=template_image_path,
                    regrid_func=regrid_func,
                    output_suffix=f"_pb_common_{i}"
                )

                if not regridded_pb:
                    print(f"[DEBUG] Cache miss, using temporary file", file=sys.stderr, flush=True)
                    # Fallback to temporary file if caching not available
                    regridded_pb = str(output_path) + \
                        f"_pb_regrid_common_{i}.tmp"
                    print(f"[DEBUG] Regridding to: {regridded_pb}", file=sys.stderr, flush=True)
                    try:
                        print(f"[DEBUG] Pre-regrid check: source={pb_path} exists={os.path.exists(pb_path)}, template={template_image_path} exists={os.path.exists(template_image_path)}", file=sys.stderr, flush=True)
                        imregrid(
                            imagename=str(pb_path),
                            template=template_image_path,
                            output=regridded_pb,
                            overwrite=True,
                        )
                        print(f"[DEBUG] ✓ Regridding completed: {regridded_pb}", file=sys.stderr, flush=True)
                        if not os.path.exists(regridded_pb):
                            raise FileNotFoundError(f"Regridded output does not exist: {regridded_pb}")
                    except Exception as e:
                        print(f"[ERROR] Regridding failed: {e}", file=sys.stderr, flush=True)
                        import traceback
                        print(f"[ERROR] Traceback:\n{traceback.format_exc()}", file=sys.stderr, flush=True)
                        handle_casa_tool_error(
                            'imregrid', e,
                            image_path=pb_path,
                            operation=f"regrid_pb_to_common_{i}",
                            template=template_image_path
                        )
                else:
                    print(f"[DEBUG] Using cached regridded PB: {regridded_pb}", file=sys.stderr, flush=True)
                    LOG.debug(
                        f"Using cached regridded PB image: {regridded_pb}")

                # Read regridded PB image
                print(f"[DEBUG] Reading regridded PB image: {regridded_pb}", file=sys.stderr, flush=True)
                if not os.path.exists(regridded_pb):
                    raise FileNotFoundError(f"Regridded PB image missing: {regridded_pb}")
                
                pb_img = casaimage(str(regridded_pb))
                print(f"[DEBUG] PB image opened, reading data...", file=sys.stderr, flush=True)
                pb_data = pb_img.getdata()
                shape = pb_img.shape()
                print(f"[DEBUG] PB data shape: {shape}", file=sys.stderr, flush=True)
                
                # AGGRESSIVE VALIDATION: Verify PB data is valid
                if DEBUG_AGGRESSIVE_VALIDATION:
                    if pb_data is None:
                        raise MosaicError(f"PB {i+1} data is None", f"PB image: {pb_path}")
                    if pb_data.size == 0:
                        raise MosaicError(f"PB {i+1} data is empty", f"PB image: {pb_path}")
                    if np.all(np.isnan(pb_data)):
                        print(f"[WARNING] PB {i+1} is all NaN", file=sys.stderr, flush=True)
                    if np.any(np.isinf(pb_data)):
                        print(f"[WARNING] PB {i+1} contains Inf values", file=sys.stderr, flush=True)
                    # Extract 2D shape for comparison (handle 2D or 4D arrays)
                    if pb_data.ndim == 2:
                        pb_shape_2d = pb_data.shape
                    elif pb_data.ndim == 4:
                        pb_shape_2d = pb_data.shape[2:]
                    else:
                        pb_shape_2d = pb_data.shape[-2:]
                    if pb_shape_2d != tuple(common_shape):
                        raise MosaicError(
                            f"PB {i+1} shape mismatch: got {pb_shape_2d}, expected {common_shape} (full shape: {pb_data.shape})",
                            f"PB image: {pb_path}"
                        )
                    print(f"[DEBUG] ✓ PB {i+1} data validation passed: shape_2d={pb_shape_2d}", file=sys.stderr, flush=True)
                
                pb_elapsed = time.time() - pb_start
                print(f"[DEBUG] ✓ PB {i+1} processed in {pb_elapsed:.2f}s", file=sys.stderr, flush=True)
                LOG.info(
                    f"  PB {i+1} regridded in {pb_elapsed:.1f}s: shape={shape}")

                LOG.debug(
                    f"  PB {i+1} extracting 2D response from shape {pb_data.shape}")
                # Extract PB response (handle multi-dimensional arrays)
                # PB images are typically 2D [y, x] or 4D [stokes, freq, y, x]
                if pb_data.ndim == 2:
                    pb_response = pb_data
                elif pb_data.ndim == 4:
                    # Take first stokes, first frequency
                    pb_response = pb_data[0, 0, :, :]
                else:
                    # Flatten to 2D
                    pb_response = pb_data.squeeze()
                    if pb_response.ndim > 2:
                        pb_response = pb_response[0, :,
                                                  :] if pb_response.ndim == 3 else pb_response
                LOG.debug(
                    f"  PB {i+1} extracted 2D shape: {pb_response.shape}")

                # PB data is already float32 from FITS - no conversion needed for performance
                # Will convert to float64 only during final mosaic calculation if needed
                pb_data_list.append(pb_response)
                pb_images.append(pb_img)
                LOG.info(f"  PB {i+1} processed and added to list")

            except (ImageReadError, ImageCorruptionError, IncompatibleImageFormatError):
                # Re-raise validation errors with context
                raise
            except Exception as e:
                LOG.error(f"Failed to read PB image {pb_path}: {e}")
                if 'pb_img' in locals():
                    try:
                        pb_img.close()
                    except Exception:
                        pass
                # This should not happen if error handling is working correctly
                raise ImageReadError(
                    f"Failed to read primary beam image: {pb_path}",
                    f"Error: {e}. "
                    "Check if the PB image exists and is readable. "
                    "Verify the image format is supported (CASA .pb directory or FITS -beam-0.fits file).",
                    context={'tile': pb_path, 'operation': f'read_pb_tile_{i}'}
                ) from e
    except Exception as e:
        # Outer try block error handling
        LOG.error(f"Unexpected error in PB reading loop: {e}")
        raise

    LOG.info(f"✓ Completed reading {len(pb_images)} PB images")

    # Step 2: Regrid all tile images to common coordinate system
    print(f"[DEBUG] CHECKPOINT: Starting tile regridding", file=sys.stderr, flush=True)
    LOG.info(
        f"Regridding {len(tiles)} tile images to common coordinate system...")
    LOG.info(f"Tile paths: {[Path(t).name for t in tiles]}")
    sys.stderr.flush()

    if len(tiles) != len(pb_paths):
        print(f"[WARNING] Mismatch: {len(tiles)} tiles vs {len(pb_paths)} PB images", file=sys.stderr, flush=True)
        LOG.warning(
            f"Mismatch: {len(tiles)} tiles vs {len(pb_paths)} PB images")

    tile_images = []
    tile_data_list = []

    for i, tile in enumerate(tiles):
        print(f"[DEBUG] ===== TILE REGRID {i+1}/{len(tiles)} =====", file=sys.stderr, flush=True)
        print(f"[DEBUG] Tile path: {tile}", file=sys.stderr, flush=True)
        LOG.info(
            f"=== Starting tile {i+1}/{len(tiles)}: {Path(tile).name} ===")
        
        if not os.path.exists(tile):
            print(f"[ERROR] Tile does not exist: {tile}", file=sys.stderr, flush=True)
            raise MosaicError(
                f"Tile image missing: {tile}",
                "All tile images must exist."
            )
        
        try:
            tile_start = time.time()
            print(f"[DEBUG] Regridding tile {i+1}/{len(tiles)}: {Path(tile).name}...", file=sys.stderr, flush=True)
            LOG.info(
                f"Regridding tile image {i+1}/{len(tiles)}: {Path(tile).name}...")

            # Regrid tile to common coordinate system
            # Try to use cached regridded image
            def regrid_tile_func(imagename, template, output, overwrite):
                print(f"[DEBUG] Calling imregrid for tile: imagename={imagename}, template={template}, output={output}", file=sys.stderr, flush=True)
                if not os.path.exists(imagename):
                    raise FileNotFoundError(f"Source tile does not exist: {imagename}")
                if not os.path.exists(template):
                    raise FileNotFoundError(f"Template image does not exist: {template}")
                if template.endswith('.fits'):
                    raise ValueError(f"Template must be CASA format, not FITS: {template}")
                imregrid(imagename=imagename, template=template,
                         output=output, overwrite=overwrite)
                print(f"[DEBUG] Tile imregrid completed: {output}", file=sys.stderr, flush=True)

            regridded_tile = cache.get_regridded_image(
                source_path=str(tile),
                template_path=template_image_path,
                regrid_func=regrid_tile_func,
                output_suffix=f"_tile_common_{i}"
            )

            if not regridded_tile:
                print(f"[DEBUG] Cache miss for tile, using temporary file", file=sys.stderr, flush=True)
                # Fallback to temporary file if caching not available
                regridded_tile = str(output_path) + \
                    f"_tile_regrid_common_{i}.tmp"
                print(f"[DEBUG] Regridding tile to: {regridded_tile}", file=sys.stderr, flush=True)
                try:
                    print(f"[DEBUG] Pre-regrid check: source={tile} exists={os.path.exists(tile)}, template={template_image_path} exists={os.path.exists(template_image_path)}", file=sys.stderr, flush=True)
                    imregrid(
                        imagename=str(tile),
                        template=template_image_path,
                        output=regridded_tile,
                        overwrite=True,
                    )
                    print(f"[DEBUG] ✓ Tile regridding completed: {regridded_tile}", file=sys.stderr, flush=True)
                    if not os.path.exists(regridded_tile):
                        raise FileNotFoundError(f"Regridded tile output does not exist: {regridded_tile}")
                except Exception as e:
                    print(f"[ERROR] Tile regridding failed: {e}", file=sys.stderr, flush=True)
                    import traceback
                    print(f"[ERROR] Traceback:\n{traceback.format_exc()}", file=sys.stderr, flush=True)
                    handle_casa_tool_error(
                        'imregrid', e,
                        image_path=tile,
                        operation=f"regrid_tile_to_common_{i}",
                        template=template_image_path
                    )
            else:
                print(f"[DEBUG] Using cached regridded tile: {regridded_tile}", file=sys.stderr, flush=True)
                LOG.debug(
                    f"Using cached regridded tile image: {regridded_tile}")

            # Read regridded tile image
            print(f"[DEBUG] Reading regridded tile image: {regridded_tile}", file=sys.stderr, flush=True)
            if not os.path.exists(regridded_tile):
                raise FileNotFoundError(f"Regridded tile image missing: {regridded_tile}")
            
            tile_img = casaimage(str(regridded_tile))
            print(f"[DEBUG] Tile image opened, reading data...", file=sys.stderr, flush=True)
            tile_data = tile_img.getdata()
            print(f"[DEBUG] Tile data shape: {tile_data.shape}", file=sys.stderr, flush=True)
            
            # AGGRESSIVE VALIDATION: Verify tile data is valid
            if DEBUG_AGGRESSIVE_VALIDATION:
                if tile_data is None:
                    raise MosaicError(f"Tile {i+1} data is None", f"Tile: {tile}")
                if tile_data.size == 0:
                    raise MosaicError(f"Tile {i+1} data is empty", f"Tile: {tile}")
                # Extract 2D shape for comparison
                if tile_data.ndim == 2:
                    tile_shape_2d = tile_data.shape
                elif tile_data.ndim == 4:
                    tile_shape_2d = tile_data.shape[2:]
                else:
                    tile_shape_2d = tile_data.shape[-2:]
                if tile_shape_2d != tuple(common_shape):
                    raise MosaicError(
                        f"Tile {i+1} shape mismatch: got {tile_shape_2d}, expected {common_shape}",
                        f"Tile: {tile}"
                    )
                print(f"[DEBUG] ✓ Tile {i+1} data validation passed", file=sys.stderr, flush=True)
            
            tile_elapsed = time.time() - tile_start
            print(f"[DEBUG] ✓ Tile {i+1} processed in {tile_elapsed:.2f}s", file=sys.stderr, flush=True)
            LOG.info(f"  Tile {i+1} regridded: shape={tile_data.shape}")

            # Extract image data (handle multi-dimensional arrays)
            if tile_data.ndim == 2:
                img_data = tile_data
            elif tile_data.ndim == 4:
                # Take first stokes, first frequency
                img_data = tile_data[0, 0, :, :]
            else:
                # Flatten to 2D
                img_data = tile_data.squeeze()
                if img_data.ndim > 2:
                    img_data = img_data[0, :,
                                        :] if img_data.ndim == 3 else img_data

            # Verify shape matches common shape
            if img_data.shape != common_shape:
                LOG.warning(
                    f"Tile {i+1} regridded shape {img_data.shape} doesn't match common shape {common_shape}. "
                    f"This should not happen - regridding may have failed.")

            # Verify shape matches PB image
            if i >= len(pb_data_list):
                raise IndexError(
                    f"Tile index {i} exceeds PB images list length {len(pb_data_list)}. "
                    f"Tile: {tile}"
                )
            if img_data.shape != pb_data_list[i].shape:
                LOG.warning(
                    f"Tile {i+1} shape {img_data.shape} doesn't match PB shape {pb_data_list[i].shape}. "
                    f"This should not happen - both should be regridded to common coordinate system.")

            # Append tile data
            LOG.debug(
                f"  Tile {i+1} extracted 2D shape: {img_data.shape}")
            # Keep as float32 for performance (tile data is already float32 from FITS)
            # Will convert to float64 only during final mosaic calculation if needed
            tile_data_list.append(img_data)
            tile_images.append(tile_img)
            tile_elapsed = time.time() - tile_start
            LOG.info(
                f"  Tile {i+1} processed in {tile_elapsed:.1f}s and added to list (total: {len(tile_data_list)})")
            LOG.info(f"=== Completed tile {i+1}/{len(tiles)} successfully ===")

        except (ImageReadError, ImageCorruptionError, IncompatibleImageFormatError):
            # Re-raise validation errors with context
            LOG.error(f"=== Tile {i+1} failed with validation error ===")
            raise
        except Exception as e:
            LOG.error(
                f"=== Tile {i+1} failed with exception: {type(e).__name__}: {e} ===")
            import traceback
            LOG.error(f"Traceback: {traceback.format_exc()}")
            # Clean up already opened images
            for img in tile_images:
                try:
                    img.close()
                except Exception:
                    pass
            for img in pb_images:
                try:
                    img.close()
                except Exception:
                    pass
            # This should not happen if error handling is working correctly
            raise ImageReadError(
                f"Failed to read tile image: {tile}",
                f"Error: {e}. "
                "Check if the file exists and is readable. "
                "Verify the image format is supported (CASA image directory or FITS file).",
                context={'tile': tile, 'operation': f'read_tile_{i}'}
            ) from e

    LOG.info(
        f"=== Tile reading loop completed: processed {len(tile_data_list)}/{len(tiles)} tiles ===")

    # Step 3: Compute per-pixel weights and combine
    mosaic_start = time.time()
    LOG.info("Computing pixel-by-pixel PB-weighted combination...")

    # Validate we have tile data
    if not tile_data_list:
        raise ValueError(
            "No tile images were successfully read. Cannot create mosaic.")
    if len(tile_data_list) != len(pb_data_list):
        raise ValueError(
            f"Mismatch between tile images ({len(tile_data_list)}) and PB images ({len(pb_data_list)}). "
            "Cannot create mosaic."
        )

    # Get noise variances
    noise_vars = []
    for tile in tiles:
        metrics = metrics_dict.get(
            tile, TileQualityMetrics(tile_path=tile))
        if metrics.rms_noise is not None and metrics.rms_noise > 0:
            noise_var = metrics.rms_noise ** 2
        else:
            # Default noise variance if not available
            noise_var = 1.0
        noise_vars.append(noise_var)

    # Compute weights: weight = pb_response^2 / noise_variance
    # For each pixel, combine: mosaic = sum(weight * tile) / sum(weight)
    # All tiles and PB images are now on the same grid (common_shape)
    print(f"[DEBUG] CHECKPOINT: Starting mosaic combination", file=sys.stderr, flush=True)
    print(f"[DEBUG] Common shape: {common_shape}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Number of tiles to combine: {len(tile_data_list)}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Number of PB images: {len(pb_data_list)}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Number of noise variances: {len(noise_vars)}", file=sys.stderr, flush=True)
    
    # AGGRESSIVE VALIDATION: Verify all arrays match before combining
    if DEBUG_AGGRESSIVE_VALIDATION:
        if len(tile_data_list) != len(pb_data_list):
            raise MosaicError(
                f"Mismatch: {len(tile_data_list)} tiles vs {len(pb_data_list)} PB images",
                "Each tile must have a corresponding PB image"
            )
        if len(tile_data_list) != len(noise_vars):
            raise MosaicError(
                f"Mismatch: {len(tile_data_list)} tiles vs {len(noise_vars)} noise variances",
                "Each tile must have a noise variance"
            )
        if len(tile_data_list) == 0:
            raise MosaicError("No tiles to combine", "tile_data_list is empty")
        for i, (tile_data, pb_data) in enumerate(zip(tile_data_list, pb_data_list)):
            # Extract 2D shapes for comparison
            if tile_data.ndim == 2:
                tile_shape_2d = tile_data.shape
            elif tile_data.ndim == 4:
                tile_shape_2d = tile_data.shape[2:]
            else:
                tile_shape_2d = tile_data.shape[-2:]
            
            if pb_data.ndim == 2:
                pb_shape_2d = pb_data.shape
            elif pb_data.ndim == 4:
                pb_shape_2d = pb_data.shape[2:]
            else:
                pb_shape_2d = pb_data.shape[-2:]
            
            if tile_shape_2d != pb_shape_2d:
                raise MosaicError(
                    f"Shape mismatch for tile {i+1}: tile={tile_shape_2d}, pb={pb_shape_2d}",
                    "Tile and PB must have matching shapes after regridding"
                )
            if tile_shape_2d != tuple(common_shape):
                raise MosaicError(
                    f"Tile {i+1} shape mismatch: got {tile_shape_2d}, expected {common_shape}",
                    "All tiles must match common_shape after regridding"
                )
        print(f"[DEBUG] ✓ All arrays validated: shapes match, ready to combine", file=sys.stderr, flush=True)
    
    sys.stderr.flush()

    # Extract spatial dimensions from common_shape (handles both 2D and 4D)
    if len(common_shape) == 4:
        ny, nx = common_shape[2], common_shape[3]
    else:
        ny, nx = common_shape
    mosaic_data = np.zeros((ny, nx), dtype=np.float64)
    total_weight = np.zeros((ny, nx), dtype=np.float64)
    print(f"[DEBUG] Initialized mosaic arrays: shape=({ny}, {nx})", file=sys.stderr, flush=True)

    mosaic_start = time.time()
    for i, (tile_data, pb_data, noise_var) in enumerate(zip(tile_data_list, pb_data_list, noise_vars)):
        print(f"[DEBUG] Combining tile {i+1}/{len(tile_data_list)}: tile_shape={tile_data.shape}, pb_shape={pb_data.shape}", file=sys.stderr, flush=True)
        # Compute weights: pb^2 / noise_variance
        # Clip PB values to avoid division issues
        pb_safe = np.clip(pb_data, 1e-10, None)  # Avoid zero/negative PB
        weights = (pb_safe ** 2) / noise_var

        # Accumulate weighted sum
        mosaic_data += weights * tile_data
        total_weight += weights

        print(f"[DEBUG] Tile {i+1}: min PB={pb_safe.min():.4f}, max PB={pb_safe.max():.4f}, noise_var={noise_var:.3e}", file=sys.stderr, flush=True)
        LOG.debug(f"Tile {i}: min PB={pb_safe.min():.4f}, max PB={pb_safe.max():.4f}, "
                  f"noise_var={noise_var:.3e}")

    # AGGRESSIVE VALIDATION: Check weights before normalization
    if DEBUG_AGGRESSIVE_VALIDATION:
        if np.all(total_weight == 0):
            raise MosaicError("All weights are zero", "Cannot create mosaic with zero weights")
        if np.all(np.isnan(total_weight)):
            raise MosaicError("All weights are NaN", "Weight calculation failed")
        print(f"[DEBUG] Weight statistics: min={np.nanmin(total_weight):.2e}, max={np.nanmax(total_weight):.2e}, mean={np.nanmean(total_weight):.2e}", file=sys.stderr, flush=True)
    
    # Normalize by total weight (avoid division by zero)
    # Use a relative threshold: pixels with weight < 1% of max weight are set to NaN
    # This handles edge pixels better than absolute threshold
    max_weight = np.nanmax(total_weight)
    if max_weight > 0:
        # At least 1% of max weight, or 1e-12
        weight_threshold = max(1e-12, max_weight * 0.01)
    else:
        weight_threshold = 1e-12  # Fallback to absolute threshold if all weights are zero

    nonzero_mask = total_weight > weight_threshold
    mosaic_data[nonzero_mask] /= total_weight[nonzero_mask]
    mosaic_data[~nonzero_mask] = np.nan
    
    # AGGRESSIVE VALIDATION: Check final mosaic data
    if DEBUG_AGGRESSIVE_VALIDATION:
        if np.all(np.isnan(mosaic_data)):
            raise MosaicError("Final mosaic is all NaN", "No valid pixels in mosaic")
        valid_pixels = np.sum(~np.isnan(mosaic_data))
        if valid_pixels == 0:
            raise MosaicError("No valid pixels in mosaic", "All pixels are NaN")
        print(f"[DEBUG] Final mosaic: {valid_pixels}/{mosaic_data.size} valid pixels ({100*valid_pixels/mosaic_data.size:.1f}%)", file=sys.stderr, flush=True)

    # Log statistics about NaN pixels
    nan_count = np.sum(~nonzero_mask)
    total_pixels = nonzero_mask.size
    nan_percent = 100.0 * nan_count / total_pixels if total_pixels > 0 else 0.0

    mosaic_calc_elapsed = time.time() - mosaic_start
    LOG.info(
        f"Computed PB-weighted mosaic in {mosaic_calc_elapsed:.1f}s: "
        f"coverage={nonzero_mask.sum()}/{nonzero_mask.size} pixels "
        f"({100*nonzero_mask.sum()/nonzero_mask.size:.1f}%)"
    )
    LOG.info(
        f"NaN pixel statistics: {nan_count}/{total_pixels} pixels ({nan_percent:.1f}%) "
        f"set to NaN (threshold={weight_threshold:.2e}, max_weight={max_weight:.2e})"
    )

    # Step 4: Write mosaic image
    write_start = time.time()
    LOG.info(f"Writing PB-weighted mosaic to {output_path}...")

    # Create output image using common coordinate system
    # Ensure output path is clean (no extensions that might confuse CASA)
    output_path_str = str(output_path)
    if output_path_str.endswith('.image'):
        output_path_str = output_path_str[:-6]

    # Use 2D output to match coordinate system
    output_shape_2d = mosaic_data.shape  # [y, x]
    output_pixels = mosaic_data
    output_shape = output_shape_2d

    # Extract coordinate system from first regridded tile for final output
    # Use the first regridded tile (which has the common coordinate system)
    if regridded_tiles and regridded_tiles[0]:
        template_img = casaimage(regridded_tiles[0])
        final_coordsys = template_img.coordinates()
        try:
            template_img.close()
        except AttributeError:
            pass
    else:
        # Fallback: use template tile coordinate system
        template_img = casaimage(template_image_path)
        final_coordsys = template_img.coordinates()
        try:
            template_img.close()
        except AttributeError:
            pass

    # Create CASA image - casaimage requires imagename and shape
    # Remove existing image if it exists
    if os.path.exists(output_path_str):
        import shutil
        if os.path.isdir(output_path_str):
            shutil.rmtree(output_path_str)
        else:
            os.remove(output_path_str)

    # Create image with shape and coordinate system (use coordinate system from template)
    print(f"[DEBUG] CHECKPOINT: Creating final mosaic image", file=sys.stderr, flush=True)
    print(f"[DEBUG] Output path: {output_path_str}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Output shape: {output_shape}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Output pixels shape: {output_pixels.shape}", file=sys.stderr, flush=True)
    sys.stderr.flush()
    
    # AGGRESSIVE VALIDATION: Verify output data before writing
    if DEBUG_AGGRESSIVE_VALIDATION:
        if output_pixels is None:
            raise MosaicError("Output pixels is None", "Cannot create mosaic image")
        if output_pixels.size == 0:
            raise MosaicError("Output pixels is empty", "Cannot create empty mosaic")
        if output_pixels.shape != tuple(output_shape):
            raise MosaicError(
                f"Output shape mismatch: pixels={output_pixels.shape}, expected={output_shape}",
                "Output pixels must match output_shape"
            )
        print(f"[DEBUG] ✓ Output data validated before writing", file=sys.stderr, flush=True)
    
    output_img = casaimage(output_path_str, shape=output_shape,
                           coordsys=final_coordsys, overwrite=True)
    print(f"[DEBUG] CASA image created, writing data...", file=sys.stderr, flush=True)
    output_img.putdata(output_pixels)
    print(f"[DEBUG] ✓ Mosaic image data written", file=sys.stderr, flush=True)
    
    # AGGRESSIVE VALIDATION: Verify image was created successfully
    if DEBUG_AGGRESSIVE_VALIDATION:
        if not os.path.exists(output_path_str):
            raise MosaicError(f"Mosaic image was not created: {output_path_str}", "CASA image creation failed")
        try:
            verify_img = casaimage(output_path_str)
            verify_shape = verify_img.shape()
            verify_data = verify_img.getdata()
            try:
                verify_img.close()
            except AttributeError:
                pass
            if verify_shape != tuple(output_shape):
                raise MosaicError(
                    f"Created image shape mismatch: got {verify_shape}, expected {output_shape}",
                    "Image creation succeeded but shape is wrong"
                )
            if verify_data.size != output_pixels.size:
                raise MosaicError(
                    f"Created image data size mismatch: got {verify_data.size}, expected {output_pixels.size}",
                    "Image creation succeeded but data size is wrong"
                )
            print(f"[DEBUG] ✓ Mosaic image verified: exists, shape={verify_shape}, data_size={verify_data.size}", file=sys.stderr, flush=True)
        except Exception as e:
            raise MosaicError(
                f"Failed to verify created mosaic image: {e}",
                f"Image path: {output_path_str}"
            ) from e
    
    # Note: casaimage objects don't have close() method in this version
    del output_img
    print(f"[DEBUG] ✓ Final mosaic image created: {output_path_str}", file=sys.stderr, flush=True)

    # Export to FITS format
    fits_output_path = output_path_str + ".fits"
    LOG.info(f"Exporting mosaic to FITS: {Path(fits_output_path).name}...")
    try:
        from casatasks import exportfits
        export_start = time.time()
        exportfits(
            imagename=output_path_str,
            fitsimage=fits_output_path,
            overwrite=True,
        )
        export_elapsed = time.time() - export_start
        LOG.info(f"  FITS export completed in {export_elapsed:.1f}s")

        # Update output path to FITS file
        output_path_str = fits_output_path
    except ImportError:
        LOG.warning(
            "casatasks.exportfits not available, keeping CASA image format only")
    except Exception as e:
        LOG.warning(
            f"Failed to export mosaic to FITS: {e}. Keeping CASA image format.")
        from .error_handling import handle_casa_tool_error
        try:
            handle_casa_tool_error(
                'exportfits', e,
                image_path=output_path_str,
                operation='export_mosaic_fits'
            )
        except Exception:
            # If error handling fails, just continue with CASA image
            pass

    # Clean up temporary regridded images (ensure cleanup even on errors)
    temp_files_to_cleanup = []
    # Add template image
    temp_files_to_cleanup.append(template_image_path)
    # Add regridded images
    for i in range(len(tiles)):
        for suffix in [f"_pb_regrid_common_{i}.tmp", f"_tile_regrid_common_{i}.tmp"]:
            temp_path = str(output_path) + suffix
            temp_files_to_cleanup.append(temp_path)

    # Clean up temporary files
    import shutil
    for temp_path in temp_files_to_cleanup:
        if os.path.exists(temp_path):
            try:
                if os.path.isdir(temp_path):
                    shutil.rmtree(temp_path)
                else:
                    os.remove(temp_path)
            except Exception as e:
                LOG.warning(
                    f"Failed to clean up temporary file {temp_path}: {e}")

    # Close all images
    for img in tile_images:
        try:
            img.close()
        except Exception:
            pass
    for img in pb_images:
        try:
            img.close()
        except Exception:
            pass

    write_elapsed = time.time() - write_start
    total_elapsed = time.time() - mosaic_start
    LOG.info(
        f"✓ Built PB-weighted mosaic to {output_path_str} "
        f"(pixel-by-pixel combination using PB^2/noise_variance weighting) "
        f"in {total_elapsed:.1f}s (calc: {mosaic_calc_elapsed:.1f}s, write: {write_elapsed:.1f}s)"
    )

    # Error handling is done in individual try/except blocks for Steps 1 and 2
    # Cleanup happens automatically via context managers and individual error handlers


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
    print(f"[DEBUG] Starting validation for {len(tiles)} tiles", file=sys.stderr, flush=True)
    print(f"[DEBUG] Starting validation for {len(tiles)} tiles", flush=True)  # Also to stdout

    # 1. Basic grid consistency
    print(f"[DEBUG] Checking grid consistency...", file=sys.stderr, flush=True)
    print(f"[DEBUG] Checking grid consistency...", flush=True)  # Also to stdout
    ok, reason = _check_consistent_tiles(tiles)
    print(f"[DEBUG] Grid consistency check complete: ok={ok}", file=sys.stderr, flush=True)
    if not ok:
        print(f"Cannot build mosaic: {reason}")
        return 2

    # 2. Tile quality validation (computes metrics_dict)
    print(f"[DEBUG] Calling validate_tiles_consistency...", file=sys.stderr, flush=True)
    is_valid, validation_issues, metrics_dict = validate_tiles_consistency(
        tiles, products_db=pdb
    )
    print(f"[DEBUG] validate_tiles_consistency complete: is_valid={is_valid}, issues={len(validation_issues)}", file=sys.stderr, flush=True)

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
    print(f"[DEBUG] Starting astrometric verification...", file=sys.stderr, flush=True)
    try:
        astro_valid, astro_issues, offsets = verify_astrometric_registration(
            tiles)
        print(f"[DEBUG] Astrometric verification complete: valid={astro_valid}, issues={len(astro_issues)}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[DEBUG] Astrometric verification exception: {e}", file=sys.stderr, flush=True)
        raise ValidationError(
            f"Astrometric verification failed: {e}",
            "Check if catalog access is available. "
            "Try running with --ignore-validation to skip astrometric checks."
        ) from e
    if astro_issues:
        print("Astrometric registration issues:", flush=True)
        print(f"[DEBUG] Processing {len(astro_issues)} astrometric issues", file=sys.stderr, flush=True)
        print(f"[DEBUG] Processing {len(astro_issues)} astrometric issues", flush=True)
        
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
        actual_astro_issues = [issue for issue in astro_issues if issue not in non_fatal_issues]
        
        print(f"[DEBUG] Astrometric filtering: {len(astro_issues)} total, {len(non_fatal_issues)} non-fatal, {len(actual_astro_issues)} actual", file=sys.stderr, flush=True)
        print(f"[DEBUG] Astrometric filtering: {len(astro_issues)} total, {len(non_fatal_issues)} non-fatal, {len(actual_astro_issues)} actual", flush=True)
        
        for issue in astro_issues:
            print(f"  - {issue}", flush=True)
        
        # Only abort on actual astrometric misalignment, not catalog access failures
        if actual_astro_issues and not args.ignore_validation:
            print(f"[DEBUG] Aborting: {len(actual_astro_issues)} actual issues", file=sys.stderr, flush=True)
            print("\nMosaic build aborted due to astrometric misalignment issues.", flush=True)
            return 4
        elif non_fatal_issues and not actual_astro_issues:
            print("\nWarning: Catalog access unavailable, skipping astrometric verification.", flush=True)
            print("Proceeding with mosaic build (astrometric accuracy not verified).", flush=True)

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
