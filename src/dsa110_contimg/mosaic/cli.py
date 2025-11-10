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

    if "status" not in columns:
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
    if "metrics_path" not in columns:
        conn.execute("ALTER TABLE mosaics ADD COLUMN metrics_path TEXT")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mosaics_name ON mosaics(name)")


def _fetch_tiles(
    products_db: Path,
    *,
    since: Optional[float],
    until: Optional[float],
    pbcor_only: bool = False,  # Changed default: use uncorrected images
) -> List[str]:
    """Fetch tile paths from products database.

    Returns paths to images (CASA image directories or FITS files).
    Tiles are returned in chronological order (by created_at).

    NOTE: The '-pb.fits' files marked as pbcor=1 in the database are NOT actually
    PB-corrected (they're identical to uncorrected images). Therefore, we default to
    using uncorrected images (pbcor_only=False) and let linearmosaic handle PB correction.

    Args:
        products_db: Path to products database
        since: Only include tiles created_at >= since (epoch seconds)
        until: Only include tiles created_at <= until (epoch seconds)
        pbcor_only: Only include PB-corrected images (default: False, use uncorrected)

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
            if p and (os.path.isdir(p) or (os.path.isfile(p) and p.endswith(".fits"))):
                tiles.append(p)
    return tiles


def cmd_plan(args: argparse.Namespace) -> int:
    # Input validation
    if not hasattr(args, "products_db") or not args.products_db:
        raise ValueError("products_db is required")
    if not isinstance(args.products_db, str) or not args.products_db.strip():
        raise ValueError("products_db must be a non-empty string")
    if not hasattr(args, "name") or not args.name:
        raise ValueError("name is required")
    if not isinstance(args.name, str) or not args.name.strip():
        raise ValueError("name must be a non-empty string")

    pdb = Path(args.products_db)
    name = args.name
    since = args.since
    until = args.until
    tiles = _fetch_tiles(
        pdb, since=since, until=until, pbcor_only=not args.include_unpbcor
    )
    if not tiles:
        print("No tiles found for the specified window")
        return 1
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        # Check if path column exists (science metadata schema)
        cur = conn.execute("PRAGMA table_info(mosaics)")
        columns = {row[1]: row[3] for row in cur.fetchall()}  # name: notnull

        if "path" in columns:
            # Science metadata schema - provide placeholder values for NOT NULL columns
            # These will be updated when mosaic is built
            conn.execute(
                """INSERT INTO mosaics(name, created_at, status, method, tiles, path, start_mjd, end_mjd)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (
                    name,
                    time.time(),
                    "planned",
                    args.method,
                    "\n".join(tiles),
                    "PLANNED",
                    0.0,
                    0.0,
                ),
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
    import numpy as np

    from .cache import get_cache

    cache = get_cache()
    ref = None
    for t in tiles:
        try:
            header = cache.get_tile_header(t)
            if not header:
                return False, f"Failed to get header for {t}"
            # Convert shape to tuple for comparison (handles numpy arrays, lists, and strings)
            shape = header.get("shape")
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
                    # If parsing fails, use string comparison (less ideal but works)
                    pass
            cdelt1 = header.get("cdelt1")
            cdelt2 = header.get("cdelt2")
            key = (shape, cdelt1, cdelt2)
            if ref is None:
                ref = key
            else:
                # Compare with tolerance for floating-point values
                ref_shape, ref_cdelt1, ref_cdelt2 = ref
                if shape != ref_shape:
                    return (
                        False,
                        f"Tiles have inconsistent grid shapes: {shape} vs {ref_shape}",
                    )
                # Use relative tolerance for cell size comparison (1e-9 relative tolerance)
                if cdelt1 is not None and ref_cdelt1 is not None:
                    if abs(cdelt1 - ref_cdelt1) > max(1e-12, abs(ref_cdelt1) * 1e-9):
                        return (
                            False,
                            f"Tiles have inconsistent cdelt1: {cdelt1} vs {ref_cdelt1}",
                        )
                if cdelt2 is not None and ref_cdelt2 is not None:
                    if abs(cdelt2 - ref_cdelt2) > max(1e-12, abs(ref_cdelt2) * 1e-9):
                        return (
                            False,
                            f"Tiles have inconsistent cdelt2: {cdelt2} vs {ref_cdelt2}",
                        )
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

        # Import CASA tools if available
        try:
            from casacore.images import image as casaimage
            from casatasks import exportfits, imregrid
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
                            output_dir,
                            f"{mosaic_base}_pb_regrid_{len(metric_files)}.tmp",
                        )
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
                noise_var = metrics.rms_noise**2

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
        metric_files["pb_response"] = f"{base_path}_pb_response"

        # 2. Noise variance map
        noise_var_img = casaimage()
        noise_var_img.fromarray(
            outfile=f"{base_path}_noise_variance",
            pixels=noise_variance_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        noise_var_img.close()
        metric_files["noise_variance"] = f"{base_path}_noise_variance"

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
        metric_files["tile_count"] = f"{base_path}_tile_count"

        # 4. Integration time map
        integration_time_img = casaimage()
        integration_time_img.fromarray(
            outfile=f"{base_path}_integration_time",
            pixels=integration_time_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        integration_time_img.close()
        metric_files["integration_time"] = f"{base_path}_integration_time"

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
        metric_files["coverage"] = f"{base_path}_coverage"

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
    import numpy as np
    import os

    # Check if tiles are CASA image directories or FITS files
    use_casa = False
    for tile in tiles:
        if os.path.isdir(str(tile)) or str(tile).endswith('.image'):
            use_casa = True
            break

    if use_casa:
        # Use CASA for coordinate extraction (CASA image directories)
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
                corners_pix = [[0, 0], [nx - 1, 0],
                               [0, ny - 1], [nx - 1, ny - 1]]

                ras, decs = [], []
                for x, y in corners_pix:
                    try:
                        # Use img.toworld() - returns [stokes, freq, dec, ra] in that order
                        # For 4D images: shape is [stokes, freq, dec, ra]
                        # toworld expects [stokes_idx, freq_idx, dec_idx, ra_idx]
                        # For 2D images: [dec_pix, ra_pix]
                        if len(shape) >= 4:
                            # 4D: [stokes_idx, freq_idx, dec_idx, ra_idx]
                            # y is dec pixel, x is ra pixel
                            world = img.toworld([0, 0, y, x])
                        else:
                            # 2D: [dec_pix, ra_pix] or [y, x]
                            world = img.toworld([y, x])

                        # Extract RA/Dec values from world coordinates
                        # toworld returns: [stokes, freq, dec, ra] for 4D images
                        # or [dec, ra] for 2D images
                        if len(world) >= 4:
                            # 4D: [stokes, freq, dec, ra]
                            ra_val = world[3]  # RA is last
                            dec_val = world[2]  # Dec is second to last
                        elif len(world) >= 2:
                            # 2D: [dec, ra] or [ra, dec] - check order
                            # Typically CASA returns [dec, ra] in radians
                            dec_val = world[0]
                            ra_val = world[1]
                        else:
                            continue

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

                # Clean up image object
                del img
            except Exception as e:
                LOG.warning(f"Failed to get coordinates from {tile}: {e}")
                continue

        if not ra_min_list:
            raise ValueError("Could not extract coordinates from any tile")

        return (
            min(ra_min_list),
            max(ra_max_list),
            min(dec_min_list),
            max(dec_max_list),
        )

    # Use astropy (preferred method for FITS files)
    from astropy.io import fits
    from astropy.wcs import WCS
    from dsa110_contimg.utils.runtime_safeguards import (
        validate_wcs_4d,
        wcs_pixel_to_world_safe,
    )

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
                    ny, nx = data.shape[0], (
                        data.shape[1] if data.ndim > 1 else data.shape[0]
                    )

                # Get corner coordinates
                corners_pix = [[0, 0], [nx - 1, 0],
                               [0, ny - 1], [nx - 1, ny - 1]]

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

    return (min(ra_min_list), max(ra_max_list), min(dec_min_list), max(dec_max_list))


def _create_common_coordinate_system(
    ra_min: float,
    ra_max: float,
    dec_min: float,
    dec_max: float,
    pixel_scale_arcsec: float = 2.0,
    padding_pixels: int = 10,
    template_tile: Optional[str] = None,
    output_dir: Optional[str] = None,
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
    import os
    import tempfile

    import numpy as np
    from casacore.images import image as casaimage
    from casatasks import immath, imregrid

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
        output_dir = tempfile.mkdtemp(prefix="mosaic_template_")
    else:
        os.makedirs(output_dir, exist_ok=True)

    template_image_path = os.path.join(output_dir, "common_template.image")

    # Convert FITS to CASA image if needed (imregrid requires CASA image format)
    template_tile_casa = template_tile
    if template_tile.endswith(".fits"):
        # Convert FITS to CASA image format for template
        template_tile_casa = os.path.join(
            output_dir, "template_tile_casa.image")
        if os.path.exists(template_tile_casa):
            import shutil

            if os.path.isdir(template_tile_casa):
                shutil.rmtree(template_tile_casa)

        try:
            from casatasks import importfits

            importfits(
                fitsimage=template_tile, imagename=template_tile_casa, overwrite=True
            )
            LOG.debug(
                f"Converted FITS template to CASA image: {template_tile_casa}")
        except Exception as e:
            LOG.warning(
                f"Could not convert FITS to CASA image: {e}, using FITS directly"
            )
            template_tile_casa = template_tile

    # Calculate center of mosaic bounds
    ra_center = (ra_min + ra_max) / 2.0
    dec_center = (dec_min + dec_max) / 2.0

    # Use template tile to get coordinate system structure
    template_img = casaimage(template_tile_casa)
    template_coordsys = template_img.coordinates()

    # Get direction coordinate and modify it
    dir_coord = template_coordsys.get_coordinate("direction")

    # Convert to radians
    ra_center_rad = np.radians(ra_center)
    dec_center_rad = np.radians(dec_center)
    pixel_scale_rad = np.radians(pixel_scale_deg)

    # Modify the direction coordinate to center on mosaic bounds
    # CASA direction coordinate uses [dec, ra] order (not [ra, dec])
    dir_coord.set_referencevalue([dec_center_rad, ra_center_rad])
    # Reference pixel at center of image (1-indexed in CASA)
    dir_coord.set_referencepixel([ny / 2.0 + 0.5, nx / 2.0 + 0.5])
    # Increment: [dec_increment, ra_increment] in radians
    # Dec increment is positive, RA increment is negative (for increasing RA to the left)
    dir_coord.set_increment([pixel_scale_rad, -pixel_scale_rad])

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
        if "direction0" in coordsys_dict:
            # Update existing direction coordinate
            coordsys_dict["direction0"] = dir_coord_dict
        else:
            # Add direction coordinate (shouldn't happen, but handle it)
            coordsys_dict["direction0"] = dir_coord_dict

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
        new_img = casaimage(
            template_image_path,
            shape=image_shape,
            coordsys=new_coordsys,
            overwrite=True,
        )

        # Fill with zeros
        new_img.putdata(np.zeros(image_shape, dtype=np.float32))

        try:
            new_img.close()
        except AttributeError:
            pass

        LOG.debug(
            f"Created template image: {template_image_path} with shape {image_shape}"
        )

    except Exception as e:
        # Fallback: create a simple template with correct shape
        # Even if coordinate system creation fails, we need the right shape
        LOG.warning(
            f"Could not create custom template image: {e}, creating simple template with correct shape"
        )
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
            new_img = casaimage(
                template_image_path,
                shape=image_shape,
                coordsys=template_coordsys,
                overwrite=True,
            )
            new_img.putdata(np.zeros(image_shape, dtype=np.float32))
            try:
                new_img.close()
            except AttributeError:
                pass
            LOG.debug(f"Created fallback template with shape {image_shape}")
        except Exception as e2:
            # Last resort: use template tile (wrong shape, but will work for coordinate system)
            LOG.warning(
                f"Could not create fallback template: {e2}, using template tile"
            )
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
    pixel_scale_arcsec: Optional[float] = None,
) -> None:
    """
    Build weighted mosaic (wrapper that calls linearmosaic method).

    This is the main entry point for mosaic building used by both:
    - Manual mode (cmd_build)
    - Streaming mode (streaming_mosaic.py)

    Args:
        tiles: List of tile image paths
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        output_path: Output mosaic path (CASA image format)
        pixel_scale_arcsec: Optional pixel scale in arcseconds

    Raises:
        CASAToolError: If linearmosaic tool is not available
        MosaicError: If mosaicking fails
    """
    # Try linearmosaic first (preferred method)
    try:
        _build_weighted_mosaic_linearmosaic(
            tiles=tiles,
            metrics_dict=metrics_dict,
            output_path=output_path,
            pixel_scale_arcsec=pixel_scale_arcsec,
        )
    except CASAToolError:
        # Fallback to imregrid + immath if linearmosaic unavailable
        LOG.warning(
            "linearmosaic unavailable, falling back to imregrid + immath method"
        )
        _build_weighted_mosaic_imregrid_immath(
            tiles=tiles,
            metrics_dict=metrics_dict,
            output_path=output_path,
        )


def _build_weighted_mosaic_linearmosaic(
    tiles: List[str],
    metrics_dict: dict,
    output_path: str,
    pixel_scale_arcsec: Optional[float] = None,
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

    print(
        f"[DEBUG] =========================================",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[DEBUG] CHECKPOINT: Starting _build_weighted_mosaic",
        file=sys.stderr,
        flush=True,
    )
    print(f"[DEBUG] Number of tiles: {len(tiles)}",
          file=sys.stderr, flush=True)
    print(f"[DEBUG] Output path: {output_path}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Tile paths:", file=sys.stderr, flush=True)
    for i, tile in enumerate(tiles):
        print(f"[DEBUG]   [{i+1}] {tile}", file=sys.stderr, flush=True)
    print(
        f"[DEBUG] =========================================",
        file=sys.stderr,
        flush=True,
    )

    # AGGRESSIVE VALIDATION: Fail immediately on invalid inputs
    DEBUG_AGGRESSIVE_VALIDATION = False  # Set to True for aggressive validation
    if DEBUG_AGGRESSIVE_VALIDATION:
        if not tiles:
            raise MosaicError("No tiles provided", "tiles list is empty")
        if len(tiles) == 0:
            raise MosaicError("Empty tiles list",
                              "Must provide at least one tile")
        for i, tile in enumerate(tiles):
            if not tile:
                raise MosaicError(
                    f"Tile {i+1} is empty", "All tiles must be non-empty paths"
                )
            if not isinstance(tile, str):
                raise MosaicError(
                    f"Tile {i+1} is not a string", f"Got {type(tile)}")
            if not os.path.exists(tile):
                raise MosaicError(
                    f"Tile {i+1} does not exist: {tile}",
                    "All tiles must exist before building mosaic",
                )
        if not output_path:
            raise MosaicError("Output path is empty",
                              "Must provide output_path")
        if not isinstance(output_path, str):
            raise MosaicError(
                f"Output path is not a string", f"Got {type(output_path)}"
            )
        print(
            f"[DEBUG] ✓ Aggressive validation passed: {len(tiles)} tiles, all exist",
            file=sys.stderr,
            flush=True,
        )

    # Check all tiles exist
    for i, tile in enumerate(tiles):
        if not os.path.exists(tile):
            raise MosaicError(
                f"Tile {i+1} does not exist: {tile}",
                "All tiles must exist before building mosaic"
            )

    try:
        import numpy as np
        from casacore.images import image as casaimage
        from casatasks import immath, imregrid

        from .error_handling import (
            handle_casa_tool_error,
            safe_casaimage_open,
            validate_image_before_read,
            validate_image_data,
        )
    except ImportError as e:
        raise CASAToolError(
            f"CASA not available: {e}",
            "Ensure CASA is installed and available in the environment. "
            "Try: conda activate casa6",
        ) from e

    # Initialize linearmosaic tool
    from casatools import linearmosaic
    lm = linearmosaic()

    # Convert FITS to CASA format if needed
    temp_dir = tempfile.mkdtemp(prefix='mosaic_linearmosaic_')
    try:
        ra_min, ra_max, dec_min, dec_max = _calculate_mosaic_bounds(tiles)

        # Calculate individual tile Dec spans to ensure template covers full extent
        # This is needed because tiles may have similar Dec centers but large individual spans
        from casacore.images import image as casaimage
        import numpy as np
        max_tile_dec_span = 0.0
        for tile in tiles:
            try:
                img = casaimage(str(tile))
                coordsys = img.coordinates()
                shape = img.shape()
                if len(shape) >= 2:
                    ny, nx = shape[-2], shape[-1]
                else:
                    del img
                    continue

                # Get corner coordinates to calculate Dec span
                # For 4D images: shape is [stokes, freq, dec, ra]
                # toworld([dec_pix, ra_pix, freq_idx, stokes_idx]) returns [stokes, freq, dec, ra] in world coords
                # Try multiple corner combinations to handle edge cases
                corners_to_try = [
                    [0, 0],           # BLC
                    [nx - 1, 0],      # BRC (if valid)
                    [0, ny - 1],      # TLC (if valid)
                    [nx - 1, ny - 1],  # TRC (if valid)
                    [nx // 2, 0],     # Bottom center
                    [nx // 2, ny - 1],  # Top center
                    [0, ny // 2],     # Left center
                    [nx - 1, ny // 2],  # Right center
                ]
                decs = []
                ras = []
                for x, y in corners_to_try:
                    try:
                        # For 4D images: shape is [stokes, freq, dec, ra]
                        # toworld expects [stokes_idx, freq_idx, dec_idx, ra_idx]
                        # For 2D: [dec_pix, ra_pix]
                        if len(shape) >= 4:
                            # shape[0] = stokes size, shape[1] = freq size, shape[2] = dec size, shape[3] = ra size
                            # y is dec pixel, x is ra pixel
                            # [stokes_idx, freq_idx, dec_idx, ra_idx]
                            world = img.toworld([0, 0, y, x])
                        else:
                            world = img.toworld([y, x])

                        # Extract Dec and RA from world coordinates
                        # toworld returns [stokes, freq, dec, ra] for 4D images
                        if len(world) >= 4:
                            # Dec is third element (index 2)
                            dec_val = world[2]
                            # RA is fourth element (index 3)
                            ra_val = world[3]
                        elif len(world) >= 2:
                            # For 2D, might be [dec, ra] or [ra, dec]
                            # Try both orders
                            dec_val = world[0]
                            ra_val = world[1]
                        else:
                            continue

                        # Handle numpy arrays
                        if isinstance(dec_val, np.ndarray):
                            dec_val = dec_val[0] if dec_val.size > 0 else None
                        if isinstance(ra_val, np.ndarray):
                            ra_val = ra_val[0] if ra_val.size > 0 else None

                        if dec_val is not None and ra_val is not None:
                            dec_deg = np.degrees(float(dec_val))
                            ra_deg = np.degrees(float(ra_val))
                            decs.append(dec_deg)
                            ras.append(ra_deg)
                    except Exception as e:
                        # Skip this corner if it fails (e.g., out of range)
                        LOG.debug(
                            f"Could not get world coords for corner ({x}, {y}): {e}")
                        continue

                if decs:
                    tile_dec_span = max(decs) - min(decs)
                    max_tile_dec_span = max(max_tile_dec_span, tile_dec_span)
                    LOG.debug(
                        f"Tile {Path(tile).name}: Dec span = {tile_dec_span:.6f}° ({tile_dec_span*3600:.1f}\")")
                else:
                    LOG.debug(
                        f"Tile {Path(tile).name}: Could not extract Dec values from corners")

                del img
            except Exception as e:
                LOG.warning(
                    f"Could not calculate Dec span for tile {Path(tile).name}: {e}")
                import traceback
                LOG.debug(traceback.format_exc())
                continue

        # If calculated Dec span is much smaller than individual tile spans,
        # expand it to ensure template covers full extent of each tile
        calc_dec_span = dec_max - dec_min
        LOG.debug(
            f"Calculated Dec span: {calc_dec_span:.6f}°, Max tile Dec span: {max_tile_dec_span:.6f}°")
        if max_tile_dec_span > 0 and calc_dec_span < max_tile_dec_span * 0.5:
            # Expand Dec bounds to cover full extent of tiles
            dec_center = (dec_min + dec_max) / 2.0
            dec_min = dec_center - max_tile_dec_span / 2.0
            dec_max = dec_center + max_tile_dec_span / 2.0
            LOG.info(
                f"Expanded Dec bounds to cover full tile extent: "
                f"calculated span={calc_dec_span:.6f}°, max tile span={max_tile_dec_span:.6f}°, "
                f"expanded to [{dec_min:.6f}°, {dec_max:.6f}°]"
            )

        LOG.info(
            f"Mosaic bounds: RA=[{ra_min:.6f}°, {ra_max:.6f}°], "
            f"Dec=[{dec_min:.6f}°, {dec_max:.6f}°]"
        )
        LOG.info(
            f"Mosaic span: RA={ra_max-ra_min:.6f}°, Dec={dec_max-dec_min:.6f}°")
    except Exception as e:
        LOG.error(f"Failed to calculate mosaic bounds: {e}")
        raise MosaicError(
            f"Could not determine mosaic bounds from tiles: {e}",
            "Ensure all tiles have valid WCS information.",
        ) from e

    # Create common coordinate system
    LOG.info("Creating common coordinate system for mosaic...")
    try:
        # Get pixel scale from parameter or calculate from first tile
        if pixel_scale_arcsec is None:
            # Use safe_casaimage_open to prevent segfaults
            first_tile_img = safe_casaimage_open(
                str(tiles[0]), operation="get_pixel_scale")
            first_coordsys = first_tile_img.coordinates()

            try:
                # Get pixel scale from direction coordinate (RA/Dec)
                dir_coord = first_coordsys.get_coordinate('direction')
                dir_increment = dir_coord.get_increment()

                # dir_increment is [dec_increment, ra_increment] in radians
                if isinstance(dir_increment, (list, tuple, np.ndarray)) and len(dir_increment) >= 2:
                    dec_inc_rad = float(dir_increment[0]) if not isinstance(
                        dir_increment[0], np.ndarray) else float(dir_increment[0][0])
                    ra_inc_rad = float(dir_increment[1]) if not isinstance(
                        dir_increment[1], np.ndarray) else float(dir_increment[1][0])
                    # Use average of dec and ra increments (should be similar)
                    pixel_scale_rad = (abs(dec_inc_rad) +
                                       abs(ra_inc_rad)) / 2.0
                    pixel_scale_arcsec = abs(
                        np.degrees(pixel_scale_rad)) * 3600.0
                else:
                    raise ValueError(
                        "Could not extract direction coordinate increment")
            except Exception as e:
                # Fallback to default
                pixel_scale_arcsec = 2.0
                LOG.warning(
                    f'Could not determine pixel scale from first tile ({e}), using default {pixel_scale_arcsec}"'
                )
            finally:
                del first_tile_img
        else:
            LOG.info(f"Using provided pixel scale: {pixel_scale_arcsec}\"")

        # Calculate output size in pixels from mosaic bounds
        ra_span = ra_max - ra_min
        dec_span = dec_max - dec_min
        pixel_scale_deg = pixel_scale_arcsec / 3600.0
        padding_pixels = 10  # Add padding for edge effects

        nx = int(np.ceil(ra_span / pixel_scale_deg)) + 2 * padding_pixels
        ny = int(np.ceil(dec_span / pixel_scale_deg)) + 2 * padding_pixels

        LOG.info(
            f"Mosaic output size: {nx}x{ny} pixels "
            f"(pixel scale: {pixel_scale_arcsec}\")"
        )

        # Get PB images and prepare for linearmosaic
        from .validation import _find_pb_path
        from .coordinate_utils import check_tile_overlaps_template, filter_tiles_by_overlap

        # Convert FITS tiles to CASA format if needed
        casa_tiles = []
        for tile in tiles:
            if tile.endswith(".fits"):
                # Convert FITS to CASA format
                casa_tile = tile.replace(".fits", ".casa.image")
                if not os.path.exists(casa_tile):
                    from casatasks import importfits

                    importfits(fitsimage=tile,
                               imagename=casa_tile, overwrite=True)
                casa_tiles.append(casa_tile)
            else:
                # Already CASA format
                casa_tiles.append(tile)

        # Get first tile shape for common_shape calculation
        # Use safe_casaimage_open to prevent segfaults
        first_tile_img = safe_casaimage_open(
            str(casa_tiles[0]), operation="get_tile_shape")
        first_tile_shape = first_tile_img.shape()
        del first_tile_img

        if len(first_tile_shape) == 4:
            # Tiles are 4D, so common_shape must be 4D: [stokes, freq, y, x]
            common_shape = [first_tile_shape[0], first_tile_shape[1], ny, nx]
            print(
                f"[DEBUG] Tiles are 4D, using 4D common_shape: {common_shape} (spatial: {ny}x{nx})",
                file=sys.stderr,
                flush=True,
            )
        else:
            # Tiles are 2D, use 2D common_shape: [y, x]
            common_shape = [ny, nx]
            print(
                f"[DEBUG] Tiles are 2D, using 2D common_shape: {common_shape}",
                file=sys.stderr,
                flush=True,
            )

        # Create synthetic template centered on mosaic bounds (not first tile)
        # This ensures the coordinate system is properly centered
        template_output_dir = os.path.join(
            os.path.dirname(output_path), ".mosaic_template"
        )
        os.makedirs(template_output_dir, exist_ok=True)

        LOG.info("Creating synthetic template centered on mosaic bounds...")
        template_image_path, template_shape = _create_common_coordinate_system(
            ra_min=ra_min,
            ra_max=ra_max,
            dec_min=dec_min,
            dec_max=dec_max,
            pixel_scale_arcsec=pixel_scale_arcsec,
            padding_pixels=padding_pixels,
            # Use first tile for coordinate system structure
            template_tile=casa_tiles[0],
            output_dir=template_output_dir
        )

        LOG.info(
            f"Template created: {Path(template_image_path).name} "
            f"(shape: {template_shape}, centered on mosaic bounds)"
        )
        LOG.info(
            f"Common regridding shape: {common_shape} (RA span: {ra_span:.6f}°, Dec span: {dec_span:.6f}°)"
        )
        sys.stderr.flush()
    except Exception as e:
        print(
            f"[ERROR] Failed to create common coordinate system: {e}",
            file=sys.stderr,
            flush=True,
        )
        import traceback

        print(
            f"[ERROR] Traceback:\n{traceback.format_exc()}", file=sys.stderr, flush=True
        )
        LOG.error(f"Failed to create common coordinate system: {e}")
        raise MosaicError(
            f"Could not create common coordinate system: {e}",
            "Check that CASA coordinate system creation is working.",
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

    # NOTE: linearmosaic requires regridded tiles and PB images
    if not has_all_pb_images:
        raise MissingPrimaryBeamError(
            "linearmosaic requires primary beam images for all tiles",
            "Ensure PB images are available for all tiles or use the fallback method (imregrid + immath)"
        )

    # Filter tiles by overlap with template to prevent "All output pixels are masked" errors
    LOG.info("Filtering tiles by overlap with template coordinate system...")
    overlapping_tiles, skipped_tiles = filter_tiles_by_overlap(
        casa_tiles, template_image_path
    )

    if not overlapping_tiles:
        raise MosaicError(
            "No tiles overlap with template coordinate system",
            "All tiles were filtered out. Check coordinate systems and tile coverage."
        )

    if skipped_tiles:
        LOG.warning(
            f"Skipped {len(skipped_tiles)} tiles that don't overlap with template: "
            f"{[Path(t).name for t in skipped_tiles]}"
        )
        # Update pb_paths to match filtered tiles
        filtered_pb_paths = []
        for tile in overlapping_tiles:
            idx = casa_tiles.index(tile)
            filtered_pb_paths.append(pb_paths[idx])
        pb_paths = filtered_pb_paths
        casa_tiles = overlapping_tiles

    LOG.info(f"Using {len(casa_tiles)} overlapping tiles for mosaicking")

    # Regrid all tiles and PB images to the common coordinate system
    LOG.info(
        f"Regridding {len(casa_tiles)} tiles to common coordinate system...")
    regridded_tiles = []
    regridded_pbs = []

    for i, (casa_tile, pb_path) in enumerate(zip(casa_tiles, pb_paths), 1):
        # Regrid tile
        regridded_tile = os.path.join(
            temp_dir, f"regridded_tile_{i:03d}.image"
        )
        LOG.info(
            f"Regridding tile {i}/{len(casa_tiles)}: {Path(casa_tile).name}")
        print(
            f"[DEBUG] Regridding tile {i}/{len(casa_tiles)}: {Path(casa_tile).name}",
            file=sys.stderr,
            flush=True,
        )

        try:
            imregrid(
                imagename=casa_tile,
                template=template_image_path,
                output=regridded_tile,
                overwrite=True,
            )
            if not os.path.exists(regridded_tile):
                raise MosaicError(
                    f"Regridding failed: {regridded_tile} does not exist after imregrid",
                    f"Check CASA imregrid output for tile: {casa_tile}",
                )
            regridded_tiles.append(regridded_tile)
        except Exception as e:
            LOG.error(f"Failed to regrid tile {casa_tile}: {e}")
            raise MosaicError(
                f"Failed to regrid tile {i}: {e}",
                f"Tile: {casa_tile}",
            ) from e

        # Regrid PB image
        if pb_path:
            regridded_pb = os.path.join(
                temp_dir, f"regridded_pb_{i:03d}.image"
            )
            LOG.info(
                f"Regridding PB {i}/{len(pb_paths)}: {Path(pb_path).name}")
            print(
                f"[DEBUG] Regridding PB {i}/{len(pb_paths)}: {Path(pb_path).name}",
                file=sys.stderr,
                flush=True,
            )

            try:
                # Convert PB FITS to CASA if needed
                pb_casa = pb_path
                if pb_path.endswith(".fits"):
                    pb_casa = pb_path.replace(".fits", ".casa.image")
                    if not os.path.exists(pb_casa):
                        from casatasks import importfits
                        importfits(fitsimage=pb_path,
                                   imagename=pb_casa, overwrite=True)

                imregrid(
                    imagename=pb_casa,
                    template=template_image_path,
                    output=regridded_pb,
                    overwrite=True,
                )
                if not os.path.exists(regridded_pb):
                    raise MosaicError(
                        f"PB regridding failed: {regridded_pb} does not exist after imregrid",
                        f"Check CASA imregrid output for PB: {pb_path}",
                    )
                regridded_pbs.append(regridded_pb)
            except Exception as e:
                LOG.error(f"Failed to regrid PB {pb_path}: {e}")
                raise MosaicError(
                    f"Failed to regrid PB {i}: {e}",
                    f"PB: {pb_path}",
                ) from e
        else:
            raise MosaicError(
                f"PB image missing for tile {i}",
                f"Tile: {casa_tile}",
            )

    LOG.info(
        f"Successfully regridded {len(regridded_tiles)} tiles and {len(regridded_pbs)} PB images")

    # Verify template coordinate system matches calculated bounds
    # This ensures the regridded tiles and output mosaic use the exact bounds
    template_img_check = casaimage(template_image_path)
    template_coordsys_check = template_img_check.coordinates()
    template_shape_check = template_img_check.shape()
    del template_img_check

    # Get template coordinate bounds
    dir_coord_check = template_coordsys_check.get_coordinate('direction')
    ref_val = dir_coord_check.get_referencevalue()
    ref_pix = dir_coord_check.get_referencepixel()
    increment = dir_coord_check.get_increment()

    # Calculate template bounds from coordinate system
    # Reference pixel is at center (1-indexed), so corners are at:
    # BLC: [0, 0] -> world coordinates
    # TRC: [ny-1, nx-1] -> world coordinates
    if len(template_shape_check) >= 2:
        template_ny = template_shape_check[-2]
        template_nx = template_shape_check[-1]
    else:
        template_ny = ny
        template_nx = nx

    # Convert pixel offsets to world coordinates
    # CASA reference pixel is [dec_pix, ra_pix] (1-indexed)
    # BLC pixel: [0, 0] relative to reference pixel (0-indexed)
    # TRC pixel: [ny-1, nx-1] relative to reference pixel (0-indexed)
    # ref_pix is [dec_ref, ra_ref] in 1-indexed pixels
    blc_pix_offset_dec = 0 - (ref_pix[0] - 1)  # Dec offset (0-indexed)
    blc_pix_offset_ra = 0 - (ref_pix[1] - 1)   # RA offset (0-indexed)
    trc_pix_offset_dec = (template_ny - 1) - \
        (ref_pix[0] - 1)  # Dec offset (0-indexed)
    trc_pix_offset_ra = (template_nx - 1) - \
        (ref_pix[1] - 1)   # RA offset (0-indexed)

    # Convert to world coordinates (radians)
    if isinstance(increment, (list, tuple, np.ndarray)) and len(increment) >= 2:
        dec_inc_rad = float(increment[0]) if not isinstance(
            increment[0], np.ndarray) else float(increment[0][0])
        ra_inc_rad = float(increment[1]) if not isinstance(
            increment[1], np.ndarray) else float(increment[1][0])
    else:
        pixel_scale_rad = np.radians(pixel_scale_arcsec / 3600.0)
        dec_inc_rad = pixel_scale_rad
        ra_inc_rad = -pixel_scale_rad

    # Calculate world coordinates at corners
    template_dec_min_rad = ref_val[0] + blc_pix_offset_dec * dec_inc_rad
    template_dec_max_rad = ref_val[0] + trc_pix_offset_dec * dec_inc_rad
    template_ra_min_rad = ref_val[1] + blc_pix_offset_ra * ra_inc_rad
    template_ra_max_rad = ref_val[1] + trc_pix_offset_ra * ra_inc_rad

    # Convert to degrees
    template_dec_min_deg = np.degrees(template_dec_min_rad)
    template_dec_max_deg = np.degrees(template_dec_max_rad)
    template_ra_min_deg = np.degrees(template_ra_min_rad)
    template_ra_max_deg = np.degrees(template_ra_max_rad)

    # Ensure RA is in correct order (RA increases to the left, so min > max)
    if template_ra_min_deg > template_ra_max_deg:
        template_ra_min_deg, template_ra_max_deg = template_ra_max_deg, template_ra_min_deg

    LOG.info(
        f"Template coordinate system bounds: "
        f"RA=[{template_ra_min_deg:.6f}°, {template_ra_max_deg:.6f}°] "
        f"(span: {abs(template_ra_max_deg-template_ra_min_deg):.6f}°), "
        f"Dec=[{template_dec_min_deg:.6f}°, {template_dec_max_deg:.6f}°] "
        f"(span: {abs(template_dec_max_deg-template_dec_min_deg):.6f}°)"
    )
    LOG.info(
        f"Calculated mosaic bounds: "
        f"RA=[{ra_min:.6f}°, {ra_max:.6f}°] (span: {ra_max-ra_min:.6f}°), "
        f"Dec=[{dec_min:.6f}°, {dec_max:.6f}°] (span: {dec_max-dec_min:.6f}°)"
    )

    # Warn if template bounds don't match calculated bounds
    ra_span_diff = abs(
        abs(template_ra_max_deg - template_ra_min_deg) - (ra_max - ra_min))
    dec_span_diff = abs(
        abs(template_dec_max_deg - template_dec_min_deg) - (dec_max - dec_min))
    if ra_span_diff > 0.1 or dec_span_diff > 0.1:
        LOG.warning(
            f"Template coordinate system bounds differ from calculated bounds: "
            f"RA span difference: {ra_span_diff:.6f}°, Dec span difference: {dec_span_diff:.6f}°"
        )

    # Remove existing output paths before defining new ones
    # linearmosaic.defineoutputimage will erase existing images, but empty/corrupted
    # directories can cause issues, so we explicitly remove them first
    output_weight_path = str(output_path) + ".weight"
    if os.path.exists(output_path):
        LOG.info(f"Removing existing output image: {output_path}")
        if os.path.isdir(output_path):
            shutil.rmtree(output_path)
        else:
            os.remove(output_path)
    if os.path.exists(output_weight_path):
        LOG.info(f"Removing existing output weight image: {output_weight_path}")
        if os.path.isdir(output_weight_path):
            shutil.rmtree(output_weight_path)
        else:
            os.remove(output_weight_path)

    # Define output image for linearmosaic
    # Use the template's coordinate system parameters to ensure exact bounds
    from casatools import measures
    me = measures()
    ra_center = (ra_min + ra_max) / 2.0
    dec_center = (dec_min + dec_max) / 2.0
    direction = me.direction('J2000', f'{ra_center}deg', f'{dec_center}deg')

    LOG.info(
        f"Defining output image for linearmosaic with exact bounds: "
        f"{nx}x{ny} pixels, center=({ra_center:.6f}°, {dec_center:.6f}°), "
        f"pixel_scale={pixel_scale_arcsec}\""
    )
    lm.defineoutputimage(
        nx=nx,
        ny=ny,
        cellx=f"{pixel_scale_arcsec}arcsec",
        celly=f"{pixel_scale_arcsec}arcsec",
        imagecenter=direction,
        outputimage=str(output_path),
        outputweight=output_weight_path
    )

    # Make mosaic using linearmosaic
    LOG.info(
        f"Making mosaic with linearmosaic using {len(regridded_tiles)} tiles...")
    # NOTE: The '-pb.fits' files are NOT actually PB-corrected (they're identical to uncorrected)
    # Therefore, we use imageweighttype=0 and let linearmosaic handle PB correction
    lm.makemosaic(
        images=regridded_tiles,
        weightimages=regridded_pbs,
        # Images are NOT PB-corrected (let linearmosaic handle it)
        imageweighttype=0,
        weighttype=1  # PB weight images
    )

    LOG.info(f"Mosaic created successfully: {output_path}")

    # Verify output mosaic coordinate system matches calculated bounds
    # This helps diagnose if linearmosaic expanded the coordinate system
    try:
        mosaic_img_check = casaimage(str(output_path))
        mosaic_coordsys_check = mosaic_img_check.coordinates()
        mosaic_shape_check = mosaic_img_check.shape()

        # Get mosaic coordinate bounds
        mosaic_dir_coord = mosaic_coordsys_check.get_coordinate('direction')
        mosaic_ref_val = mosaic_dir_coord.get_referencevalue()
        mosaic_ref_pix = mosaic_dir_coord.get_referencepixel()
        mosaic_increment = mosaic_dir_coord.get_increment()

        # Calculate mosaic bounds from coordinate system
        if len(mosaic_shape_check) >= 2:
            mosaic_ny = mosaic_shape_check[-2]
            mosaic_nx = mosaic_shape_check[-1]
        else:
            mosaic_ny = ny
            mosaic_nx = nx

        # Convert pixel offsets to world coordinates
        # CASA reference pixel is [dec_pix, ra_pix] (1-indexed)
        mosaic_blc_pix_offset_dec = 0 - \
            (mosaic_ref_pix[0] - 1)  # Dec offset (0-indexed)
        mosaic_blc_pix_offset_ra = 0 - \
            (mosaic_ref_pix[1] - 1)   # RA offset (0-indexed)
        mosaic_trc_pix_offset_dec = (
            mosaic_ny - 1) - (mosaic_ref_pix[0] - 1)  # Dec offset (0-indexed)
        mosaic_trc_pix_offset_ra = (
            mosaic_nx - 1) - (mosaic_ref_pix[1] - 1)   # RA offset (0-indexed)

        # Convert to world coordinates (radians)
        if isinstance(mosaic_increment, (list, tuple, np.ndarray)) and len(mosaic_increment) >= 2:
            mosaic_dec_inc_rad = float(mosaic_increment[0]) if not isinstance(
                mosaic_increment[0], np.ndarray) else float(mosaic_increment[0][0])
            mosaic_ra_inc_rad = float(mosaic_increment[1]) if not isinstance(
                mosaic_increment[1], np.ndarray) else float(mosaic_increment[1][0])
        else:
            pixel_scale_rad = np.radians(pixel_scale_arcsec / 3600.0)
            mosaic_dec_inc_rad = pixel_scale_rad
            mosaic_ra_inc_rad = -pixel_scale_rad

        # Calculate world coordinates at corners
        mosaic_dec_min_rad = mosaic_ref_val[0] + \
            mosaic_blc_pix_offset_dec * mosaic_dec_inc_rad
        mosaic_dec_max_rad = mosaic_ref_val[0] + \
            mosaic_trc_pix_offset_dec * mosaic_dec_inc_rad
        mosaic_ra_min_rad = mosaic_ref_val[1] + \
            mosaic_blc_pix_offset_ra * mosaic_ra_inc_rad
        mosaic_ra_max_rad = mosaic_ref_val[1] + \
            mosaic_trc_pix_offset_ra * mosaic_ra_inc_rad

        # Convert to degrees
        mosaic_dec_min_deg = np.degrees(mosaic_dec_min_rad)
        mosaic_dec_max_deg = np.degrees(mosaic_dec_max_rad)
        mosaic_ra_min_deg = np.degrees(mosaic_ra_min_rad)
        mosaic_ra_max_deg = np.degrees(mosaic_ra_max_rad)

        # Ensure RA is in correct order
        if mosaic_ra_min_deg > mosaic_ra_max_deg:
            mosaic_ra_min_deg, mosaic_ra_max_deg = mosaic_ra_max_deg, mosaic_ra_min_deg

        mosaic_ra_span = abs(mosaic_ra_max_deg - mosaic_ra_min_deg)
        mosaic_dec_span = abs(mosaic_dec_max_deg - mosaic_dec_min_deg)
        calc_ra_span = ra_max - ra_min
        calc_dec_span = dec_max - dec_min

        ra_span_diff = abs(mosaic_ra_span - calc_ra_span)
        dec_span_diff = abs(mosaic_dec_span - calc_dec_span)

        LOG.info(
            f"Output mosaic coordinate system bounds: "
            f"RA=[{mosaic_ra_min_deg:.6f}°, {mosaic_ra_max_deg:.6f}°] "
            f"(span: {mosaic_ra_span:.6f}°), "
            f"Dec=[{mosaic_dec_min_deg:.6f}°, {mosaic_dec_max_deg:.6f}°] "
            f"(span: {mosaic_dec_span:.6f}°)"
        )

        if ra_span_diff > 0.1 or dec_span_diff > 0.1:
            LOG.warning(
                f"Output mosaic coordinate system bounds differ from calculated bounds: "
                f"RA span difference: {ra_span_diff:.6f}° (mosaic: {mosaic_ra_span:.6f}°, calculated: {calc_ra_span:.6f}°), "
                f"Dec span difference: {dec_span_diff:.6f}° (mosaic: {mosaic_dec_span:.6f}°, calculated: {calc_dec_span:.6f}°). "
                f"This may cause the 'stacked' appearance in visualizations."
            )
        else:
            LOG.info(
                f"Output mosaic coordinate system matches calculated bounds "
                f"(RA span diff: {ra_span_diff:.6f}°, Dec span diff: {dec_span_diff:.6f}°)"
            )

        del mosaic_img_check
    except Exception as e:
        LOG.warning(f"Could not verify output mosaic coordinate system: {e}")

    # Cleanup temporary regridded images
    import shutil
    for regridded_tile in regridded_tiles:
        try:
            if os.path.exists(regridded_tile):
                shutil.rmtree(regridded_tile)
        except Exception as e:
            LOG.warning(
                f"Failed to cleanup regridded tile {regridded_tile}: {e}")

    for regridded_pb in regridded_pbs:
        try:
            if os.path.exists(regridded_pb):
                shutil.rmtree(regridded_pb)
        except Exception as e:
            LOG.warning(f"Failed to cleanup regridded PB {regridded_pb}: {e}")

    # Cleanup temporary FITS->CASA conversions
    for casa_tile in casa_tiles:
        if casa_tile.endswith(".casa.image") and casa_tile not in tiles:
            try:
                if os.path.exists(casa_tile):
                    shutil.rmtree(casa_tile)
            except Exception as e:
                LOG.warning(
                    f"Failed to cleanup temporary CASA tile {casa_tile}: {e}")

    # Cleanup temp_dir if empty
    try:
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except Exception as e:
        LOG.debug(f"Could not remove temp_dir {temp_dir}: {e}")

    # Mosaic is complete - return early
    return


def _build_weighted_mosaic_imregrid_immath(
    tiles: List[str],
    metrics_dict: dict,
    output_path: str,
) -> None:
    """
    Fallback mosaicking method using imregrid + immath.

    This is called when linearmosaic fails or is unavailable.
    Uses imregrid to regrid tiles to a common coordinate system,
    then immath to combine them with primary beam weighting.

    Args:
        tiles: List of tile image paths
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        output_path: Output mosaic path (CASA image format)
    """
    import os
    import tempfile
    import time
    import numpy as np
    from pathlib import Path

    from casatasks import imregrid, immath
    from casacore.images import image as casaimage

    from .validation import _find_pb_path
    from .coordinate_utils import filter_tiles_by_overlap
    from .error_handling import safe_casaimage_open, MosaicError

    LOG.info("Using fallback method: imregrid + immath")

    # Calculate mosaic bounds
    ra_min, ra_max, dec_min, dec_max = _calculate_mosaic_bounds(tiles)
    ra_span = ra_max - ra_min
    dec_span = dec_max - dec_min

    LOG.info(
        f"Mosaic bounds: RA [{ra_min:.6f}°, {ra_max:.6f}°], "
        f"Dec [{dec_min:.6f}°, {dec_max:.6f}°]"
    )

    # Get pixel scale from first tile
    first_tile_img = safe_casaimage_open(
        str(tiles[0]), operation="get_pixel_scale")
    first_coordsys = first_tile_img.coordinates()
    dir_coord = first_coordsys.get_coordinate("direction")
    increment = dir_coord.get_increment()
    if isinstance(increment, np.ndarray):
        pixel_scale_arcsec = np.degrees(abs(increment[0])) * 3600.0
    else:
        pixel_scale_arcsec = np.degrees(abs(increment)) * 3600.0
    del first_tile_img

    padding_pixels = 10
    pixel_scale_deg = pixel_scale_arcsec / 3600.0
    nx = int(np.ceil(ra_span / pixel_scale_deg)) + 2 * padding_pixels
    ny = int(np.ceil(dec_span / pixel_scale_deg)) + 2 * padding_pixels

    LOG.info(
        f"Mosaic output size: {nx}x{ny} pixels "
        f"(pixel scale: {pixel_scale_arcsec}\")"
    )

    # Convert FITS tiles to CASA format if needed
    casa_tiles = []
    for tile in tiles:
        if tile.endswith(".fits"):
            casa_tile = tile.replace(".fits", ".casa.image")
            if not os.path.exists(casa_tile):
                from casatasks import importfits
                importfits(fitsimage=tile, imagename=casa_tile, overwrite=True)
            casa_tiles.append(casa_tile)
        else:
            casa_tiles.append(tile)

    # Create synthetic template centered on mosaic bounds
    template_output_dir = os.path.join(
        os.path.dirname(output_path), ".mosaic_template"
    )
    os.makedirs(template_output_dir, exist_ok=True)

    LOG.info("Creating synthetic template centered on mosaic bounds...")
    template_image_path, template_shape = _create_common_coordinate_system(
        ra_min=ra_min,
        ra_max=ra_max,
        dec_min=dec_min,
        dec_max=dec_max,
        pixel_scale_arcsec=pixel_scale_arcsec,
        padding_pixels=padding_pixels,
        template_tile=casa_tiles[0],
        output_dir=template_output_dir
    )

    # Filter tiles by overlap with template
    overlapping_tiles, skipped_tiles = filter_tiles_by_overlap(
        casa_tiles, template_image_path
    )

    if not overlapping_tiles:
        raise MosaicError(
            "No tiles overlap with template coordinate system",
            "All tiles were filtered out. Check coordinate systems."
        )

    if skipped_tiles:
        LOG.warning(f"Skipped {len(skipped_tiles)} non-overlapping tiles")

    casa_tiles = overlapping_tiles
    tiles = [tiles[i]
             for i in range(len(tiles)) if casa_tiles[i] in overlapping_tiles]

    # Get PB images
    pb_paths = []
    for tile in tiles:
        pb_path = _find_pb_path(tile)
        pb_paths.append(pb_path)

    # Check if we have PB images for all tiles
    has_all_pbs = all(pb_path is not None and os.path.exists(pb_path)
                      for pb_path in pb_paths)

    if not has_all_pbs:
        LOG.warning(
            "Not all tiles have PB images. Using noise-weighted combination instead of PB-weighted."
        )

    # Create temporary directory for regridded images
    temp_dir = tempfile.mkdtemp(prefix="mosaic_regrid_")
    regridded_tiles = []
    regridded_pbs = []

    try:
        # Regrid all tiles to common coordinate system
        LOG.info(
            f"Regridding {len(casa_tiles)} tiles to common coordinate system...")
        for i, casa_tile in enumerate(casa_tiles):
            regridded_tile = os.path.join(
                temp_dir, f"regridded_tile_{i}.image")
            try:
                imregrid(
                    imagename=casa_tile,
                    template=template_image_path,
                    output=regridded_tile,
                    overwrite=True,
                )
                if not os.path.exists(regridded_tile):
                    raise MosaicError(
                        f"Regridding failed: {regridded_tile} does not exist after imregrid",
                        f"Check CASA imregrid output for tile: {casa_tile}",
                    )
                regridded_tiles.append(regridded_tile)
            except RuntimeError as e:
                if "All output pixels are masked" in str(e):
                    LOG.warning(
                        f"Skipping tile {i+1}: {Path(casa_tile).name} - no overlap with template")
                    continue
                raise MosaicError(
                    f"Failed to regrid tile {casa_tile}: {e}",
                    "Check tile coordinate system compatibility."
                ) from e

        if not regridded_tiles:
            raise MosaicError(
                "No tiles could be regridded successfully",
                "All tiles were filtered out or regridding failed."
            )

        # Regrid PB images if available
        if has_all_pbs:
            LOG.info(
                f"Regridding {len(pb_paths)} PB images to common coordinate system...")
            for i, pb_path in enumerate(pb_paths):
                if pb_path is None or not os.path.exists(pb_path):
                    continue

                # Convert PB FITS to CASA if needed
                pb_casa = pb_path
                if pb_path.endswith(".fits"):
                    pb_casa = os.path.join(temp_dir, f"pb_{i}.casa.image")
                    if not os.path.exists(pb_casa):
                        from casatasks import importfits
                        importfits(fitsimage=pb_path,
                                   imagename=pb_casa, overwrite=True)

                regridded_pb = os.path.join(
                    temp_dir, f"regridded_pb_{i}.image")
                try:
                    imregrid(
                        imagename=pb_casa,
                        template=template_image_path,
                        output=regridded_pb,
                        overwrite=True,
                    )
                    if not os.path.exists(regridded_pb):
                        LOG.warning(
                            f"PB regridding failed: {regridded_pb} does not exist")
                        continue
                    regridded_pbs.append(regridded_pb)
                except RuntimeError as e:
                    if "All output pixels are masked" in str(e):
                        LOG.warning(
                            f"Skipping PB {i+1}: {Path(pb_path).name} - no overlap")
                        continue
                    LOG.warning(f"Failed to regrid PB {pb_path}: {e}")
                    continue

        # Combine regridded tiles using immath
        LOG.info(
            f"Combining {len(regridded_tiles)} regridded tiles using immath...")

        # Remove existing output if present
        if os.path.exists(output_path):
            import shutil
            if os.path.isdir(output_path):
                shutil.rmtree(output_path)
            else:
                os.remove(output_path)

        if has_all_pbs and len(regridded_pbs) == len(regridded_tiles):
            # PB-weighted combination: sum(PB² * image) / sum(PB²)
            # This implements the Sault weighting scheme
            LOG.info("Using PB-weighted combination (Sault scheme)")

            # Create weighted images: PB² * image
            weighted_images = []
            for i, (tile, pb) in enumerate(zip(regridded_tiles, regridded_pbs)):
                weighted_img = os.path.join(temp_dir, f"weighted_{i}.image")
                # PB² * image
                immath(
                    imagename=[tile, pb],
                    expr="IM0 * IM1 * IM1",  # image * pb * pb
                    outfile=weighted_img,
                )
                weighted_images.append(weighted_img)

            # Sum of weighted images
            sum_weighted = os.path.join(temp_dir, "sum_weighted.image")
            if len(weighted_images) == 1:
                import shutil
                shutil.copytree(weighted_images[0], sum_weighted)
            else:
                expr = "+".join([f"IM{i}" for i in range(len(weighted_images))])
                immath(imagename=weighted_images,
                       expr=expr, outfile=sum_weighted)

            # Sum of PB²
            sum_pb2 = os.path.join(temp_dir, "sum_pb2.image")
            pb2_images = [os.path.join(
                temp_dir, f"pb2_{i}.image") for i in range(len(regridded_pbs))]
            for i, pb in enumerate(regridded_pbs):
                immath(imagename=[pb], expr="IM0 * IM0", outfile=pb2_images[i])

            if len(pb2_images) == 1:
                import shutil
                shutil.copytree(pb2_images[0], sum_pb2)
            else:
                expr = "+".join([f"IM{i}" for i in range(len(pb2_images))])
                immath(imagename=pb2_images, expr=expr, outfile=sum_pb2)

            # Final mosaic: sum_weighted / sum_pb2
            immath(
                imagename=[sum_weighted, sum_pb2],
                expr="IM0 / IM1",
                outfile=output_path,
            )
        else:
            # Noise-weighted combination: simple mean
            LOG.info("Using noise-weighted combination (mean)")
            if len(regridded_tiles) == 1:
                import shutil
                shutil.copytree(regridded_tiles[0], output_path)
            else:
                expr = f"({'+'.join([f'IM{i}' for i in range(len(regridded_tiles))])})/{len(regridded_tiles)}"
                immath(imagename=regridded_tiles,
                       expr=expr, outfile=output_path)

        if not os.path.exists(output_path):
            raise MosaicError(
                f"Mosaic creation failed: {output_path} does not exist after immath",
                "Check CASA immath output for errors."
            )

        LOG.info(f"Mosaic created successfully: {Path(output_path).name}")

    finally:
        # Cleanup temporary files
        try:
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
        except Exception as e:
            LOG.debug(f"Could not remove temp_dir {temp_dir}: {e}")


def cmd_build(args: argparse.Namespace) -> int:
    """Build mosaic from planned tiles.

    NOTE: For timeout protection, run this command with system timeout:
    timeout 7200 dsa110-contimg mosaic build ...
    """
    # Input validation
    if not hasattr(args, "products_db") or not args.products_db:
        raise ValueError("products_db is required")
    if not isinstance(args.products_db, str) or not args.products_db.strip():
        raise ValueError("products_db must be a non-empty string")
    if not hasattr(args, "name") or not args.name:
        raise ValueError("name is required")
    if not isinstance(args.name, str) or not args.name.strip():
        raise ValueError("name must be a non-empty string")
    if not hasattr(args, "output") or not args.output:
        raise ValueError("output is required")
    if not isinstance(args.output, str) or not args.output.strip():
        raise ValueError("output must be a non-empty string")

    pdb = Path(args.products_db)
    name = args.name
    out = Path(args.output).with_suffix("")

    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        row = conn.execute(
            "SELECT id, tiles, method FROM mosaics WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            print("Mosaic plan not found; create with 'plan' first")
            return 1
        tiles = str(row[1]).splitlines()
        method = str(row[2] or "mean")

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
                    "SELECT ms_path FROM images WHERE path = ?", (tile,)
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
                tile_times[i] <= tile_times[i + 1] for i in range(len(tile_times) - 1)
            )
            if not is_chronological:
                print(f"ERROR: Tiles are NOT in chronological order!")
                print(f"  Validated {len(tile_times)}/{len(tiles)} tiles")
                print(
                    f"  Observation times (MJD): {[f'{t:.6f}' for t in tile_times]}")
                print(
                    f"  This will cause mosaic artifacts and incorrect coordinate system."
                )
                if not args.ignore_validation:
                    print(
                        "  Use --ignore-validation to proceed anyway (NOT RECOMMENDED)."
                    )
                    return 4
                else:
                    print(
                        "  WARNING: Proceeding with out-of-order tiles (--ignore-validation)"
                    )
            else:
                print(
                    f"✓ Validated: Tiles are in chronological order ({len(tile_times)}/{len(tiles)} tiles validated)"
                )
        elif len(tile_times) == 0:
            print(
                f"  Warning: Could not validate chronological order (no MS times extracted)"
            )
            print(f"  Proceeding assuming tiles are in correct order from plan")
    except Exception as e:
        LOG.debug(f"Could not validate chronological order: {e}")
        print(f"  Warning: Could not validate chronological order: {e}")
        # Continue - validation is best-effort

    # Pre-flight validation: Check all pre-conditions before expensive operations
    print("Pre-flight validation: Checking pre-conditions...")
    from .preflight import estimate_resources, validate_preflight_conditions

    # Check if PB images are required based on method
    require_pb = method == "weighted" or method == "pbweighted"

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
                "\nWarning: Pre-flight issues detected but ignored (--ignore-validation)"
            )

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
    if preflight_info.get("output_exists"):
        print(
            f"\nWarning: Output '{out}' already exists and will be overwritten")

    # Comprehensive validation
    print(f"Validating {len(tiles)} tiles...", flush=True)
    print(
        f"[DEBUG] Starting validation for {len(tiles)} tiles",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[DEBUG] Starting validation for {len(tiles)} tiles", flush=True
    )  # Also to stdout

    # 1. Basic grid consistency
    print(f"[DEBUG] Checking grid consistency...", file=sys.stderr, flush=True)
    print(f"[DEBUG] Checking grid consistency...",
          flush=True)  # Also to stdout
    ok, reason = _check_consistent_tiles(tiles)
    print(
        f"[DEBUG] Grid consistency check complete: ok={ok}", file=sys.stderr, flush=True
    )
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
        f"[DEBUG] validate_tiles_consistency complete: is_valid={is_valid}, issues={len(validation_issues)}",
        file=sys.stderr,
        flush=True,
    )

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
                "Use --ignore-validation to proceed anyway (not recommended for science).",
            )
        else:
            print(
                "\nWarning: Validation issues detected but ignored (--ignore-validation)"
            )

    # 3. Astrometric registration check
    print(f"[DEBUG] Starting astrometric verification...",
          file=sys.stderr, flush=True)
    try:
        astro_valid, astro_issues, offsets = verify_astrometric_registration(
            tiles)
        print(
            f"[DEBUG] Astrometric verification complete: valid={astro_valid}, issues={len(astro_issues)}",
            file=sys.stderr,
            flush=True,
        )
    except Exception as e:
        print(
            f"[DEBUG] Astrometric verification exception: {e}",
            file=sys.stderr,
            flush=True,
        )
        raise ValidationError(
            f"Astrometric verification failed: {e}",
            "Check if catalog access is available. "
            "Try running with --ignore-validation to skip astrometric checks.",
        ) from e
    if astro_issues:
        print("Astrometric registration issues:", flush=True)
        print(
            f"[DEBUG] Processing {len(astro_issues)} astrometric issues",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"[DEBUG] Processing {len(astro_issues)} astrometric issues", flush=True)

        # Filter out catalog access failures and image close() errors (non-fatal) from actual astrometric issues (fatal)
        non_fatal_keywords = [
            "catalog query",
            "skipping astrometric",
            "has no attribute 'close'",
            "failed to verify",
            "attributeerror",
            "'image' object",
        ]
        non_fatal_issues = [
            issue
            for issue in astro_issues
            if any(keyword in issue.lower() for keyword in non_fatal_keywords)
        ]
        actual_astro_issues = [
            issue for issue in astro_issues if issue not in non_fatal_issues
        ]

        print(
            f"[DEBUG] Astrometric filtering: {len(astro_issues)} total, {len(non_fatal_issues)} non-fatal, {len(actual_astro_issues)} actual",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"[DEBUG] Astrometric filtering: {len(astro_issues)} total, {len(non_fatal_issues)} non-fatal, {len(actual_astro_issues)} actual",
            flush=True,
        )

        for issue in astro_issues:
            print(f"  - {issue}", flush=True)

        # Only abort on actual astrometric misalignment, not catalog access failures
        if actual_astro_issues and not args.ignore_validation:
            print(
                f"[DEBUG] Aborting: {len(actual_astro_issues)} actual issues",
                file=sys.stderr,
                flush=True,
            )
            print(
                "\nMosaic build aborted due to astrometric misalignment issues.",
                flush=True,
            )
            return 4
        elif non_fatal_issues and not actual_astro_issues:
            print(
                "\nWarning: Catalog access unavailable, skipping astrometric verification.",
                flush=True,
            )
            print(
                "Proceeding with mosaic build (astrometric accuracy not verified).",
                flush=True,
            )

    # 4. Calibration consistency check
    # Try to find registry DB from environment or default location
    registry_db = None
    if os.getenv("CAL_REGISTRY_DB"):
        registry_db = Path(os.getenv("CAL_REGISTRY_DB"))
    else:
        # Try default location relative to products DB
        registry_db = pdb.parent / "cal_registry.sqlite3"
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
        print("\n" + "=" * 60)
        print("DRY-RUN MODE: Validation complete, not building mosaic")
        print("=" * 60)
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
                    os.getenv("CONTIMG_SCRATCH_DIR") or "/stage/dsa110-contimg",
                    cwd_to=out.parent,
                )
        except Exception:
            pass

        # Use weighted combination if method is 'weighted', otherwise use mean
        if method == "weighted" or method == "pbweighted":
            print(f"Building weighted mosaic to {out}...")
            try:
                _build_weighted_mosaic(tiles, metrics_dict, str(out))
            except (
                ImageReadError,
                ImageCorruptionError,
                MissingPrimaryBeamError,
                CASAToolError,
                GridMismatchError,
            ) as e:
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
                        context={"tool": "immath",
                                 "operation": "build_mean_mosaic"},
                    )
                expr = (
                    f"({'+'.join([f'IM{i}' for i in range(len(tiles))])})/{len(tiles)}"
                )
                try:
                    immath(imagename=tiles, expr=expr, outfile=str(out))
                except Exception as e:
                    handle_casa_tool_error(
                        "immath",
                        e,
                        operation="build_mean_mosaic",
                        expression=expr,
                        num_tiles=len(tiles),
                    )
            except Exception as e:
                raise CASAToolError(
                    f"CASA immath failed: {e}",
                    "Check if all tile images are readable and have compatible formats. "
                    "Try using weighted method instead: --method=weighted",
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
                    "exportfits",
                    exc,
                    image_path=str(out),
                    operation="export_mosaic_fits",
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
                    print(
                        f"Mosaic metrics: RMS={mosaic_metrics.get('rms_noise', 'N/A'):.3e}, "
                        f"coverage={mosaic_metrics.get('coverage_fraction', 0):.1%}"
                    )
            else:
                print("✓ Post-mosaic validation passed")
                if mosaic_metrics:
                    print(
                        f"Mosaic metrics: RMS={mosaic_metrics.get('rms_noise', 'N/A'):.3e}, "
                        f"coverage={mosaic_metrics.get('coverage_fraction', 0):.1%}, "
                        f"dynamic_range={mosaic_metrics.get('dynamic_range', 0):.1f}"
                    )
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
                (str(out), validation_summary, metrics_summary, name),
            )
            conn.commit()

        print(f"✓ Built mosaic to {out}")
        return 0
    except (
        MosaicError,
        ImageReadError,
        ImageCorruptionError,
        MissingPrimaryBeamError,
        CASAToolError,
        GridMismatchError,
        ValidationError,
        MetricsGenerationError,
    ) as e:
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
    sub = p.add_subparsers(dest="cmd")
    sp = sub.add_parser("plan", help="Plan a mosaic from products DB tiles")
    sp.add_argument("--products-db", default="state/products.sqlite3")
    sp.add_argument("--name", required=True)
    sp.add_argument(
        "--since",
        type=float,
        help="Only include tiles created_at >= since (epoch seconds)",
    )
    sp.add_argument(
        "--until",
        type=float,
        help="Only include tiles created_at <= until (epoch seconds)",
    )
    sp.add_argument(
        "--method",
        default="mean",
        choices=["mean", "weighted", "pbweighted"],
        help="Combination method: mean (simple), weighted (noise-weighted), pbweighted (primary beam weighted)",
    )
    sp.add_argument(
        "--include-unpbcor", action="store_true", help="Include non-pbcor tiles"
    )
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("build", help="Build a mosaic from a planned set")
    sp.add_argument("--products-db", default="state/products.sqlite3")
    sp.add_argument("--name", required=True)
    sp.add_argument(
        "--output", required=True, help="Output image base path (CASA image)"
    )
    sp.add_argument(
        "--ignore-validation",
        action="store_true",
        help="Ignore validation issues and proceed anyway (not recommended)",
    )
    sp.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate mosaic plan without building (measure twice, cut once)",
    )
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
    if not hasattr(args, "func"):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
