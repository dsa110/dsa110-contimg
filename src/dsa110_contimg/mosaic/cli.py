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
import time
from pathlib import Path
from typing import List, Optional, Tuple

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
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mosaics_name ON mosaics(name)"
    )


def _fetch_tiles(products_db: Path, *, since: Optional[float], until: Optional[float], pbcor_only: bool = True) -> List[str]:
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
            if p and os.path.isdir(p):
                tiles.append(p)
    return tiles


def cmd_plan(args: argparse.Namespace) -> int:
    pdb = Path(args.products_db)
    name = args.name
    since = args.since
    until = args.until
    tiles = _fetch_tiles(pdb, since=since, until=until, pbcor_only=not args.include_unpbcor)
    if not tiles:
        print("No tiles found for the specified window")
        return 1
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
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
    
    cache = get_cache()
    ref = None
    for t in tiles:
        try:
            header = cache.get_tile_header(t)
            if not header:
                return False, f"Failed to get header for {t}"
            key = (header.get('shape'), header.get('cdelt1'), header.get('cdelt2'))
        if ref is None:
            ref = key
        elif key != ref:
            return False, "Tiles have inconsistent grids/cell sizes"
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
        LOG.warning("casacore.images not available, skipping mosaic metrics generation")
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
            LOG.warning("CASA tools not available, skipping mosaic metrics generation")
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
                mosaic_2d = mosaic_2d[0, :, :] if mosaic_2d.ndim == 3 else mosaic_2d
        
        ny, nx = mosaic_2d.shape
        mosaic_base = os.path.splitext(os.path.basename(mosaic_path))[0]
        
        # Initialize metric arrays
        pb_response_map = np.zeros((ny, nx), dtype=np.float64)
        noise_variance_map = np.zeros((ny, nx), dtype=np.float64)
        tile_count_map = np.zeros((ny, nx), dtype=np.int32)
        integration_time_map = np.zeros((ny, nx), dtype=np.float64)
        
        # Process each tile
        for tile in tiles:
            metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
            
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
                            pb_2d = pb_2d[0, :, :] if pb_2d.ndim == 3 else pb_2d
                    
                    # Check if PB needs regridding
                    if pb_2d.shape != (ny, nx):
                        # Need to regrid PB to mosaic grid
                        regridded_pb = os.path.join(output_dir, f"{mosaic_base}_pb_regrid_{len(metric_files)}.tmp")
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
                                    pb_2d = pb_2d[0, :, :] if pb_2d.ndim == 3 else pb_2d
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
            integration_time_map += 1.0  # Units: tile counts (would convert to seconds if available)
        
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
            pixels=tile_count_map.astype(np.float32)[np.newaxis, np.newaxis, :, :],
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
                    metric_files[metric_name] = fits_path  # Update to FITS path
                except Exception as e:
                    LOG.warning(f"Failed to export {metric_name} to FITS: {e}")
        
        mosaic_img.close()
        
        LOG.info(f"Generated mosaic metrics: {list(metric_files.keys())}")
        
    except Exception as e:
        LOG.error(f"Failed to generate mosaic metrics: {e}")
        import traceback
        traceback.print_exc()
    
    return metric_files


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
    
    Args:
        tiles: List of tile image paths (should be PB-corrected images)
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        output_path: Output mosaic path
    """
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
            metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
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
    # Step 1: Read PB images and verify they're on the same grid
    LOG.info("Reading primary beam images for pixel-by-pixel weighting...")
    
    pb_images = []
    pb_data_list = []
    ref_shape = None
    ref_coordsys = None
    
    try:
        for i, (tile, pb_path) in enumerate(zip(tiles, pb_paths)):
            try:
                # Pre-validate PB image before reading
                validate_image_before_read(pb_path, operation=f"read_pb_tile_{i}")
                
                # Read PB image with enhanced error handling
                pb_img = safe_casaimage_open(pb_path, operation=f"read_pb_tile_{i}")
                pb_data = pb_img.getdata()
                
                # Validate image data
                validate_image_data(pb_data, pb_path, operation=f"read_pb_tile_{i}")
                
                # Get shape and coordinate system
                shape = pb_img.shape()
                coordsys = pb_img.coordsys()
                
                if ref_shape is None:
                    ref_shape = shape
                    ref_coordsys = coordsys
                else:
                    # Check if shapes match
                    if shape != ref_shape:
                        LOG.warning(
                            f"PB image {pb_path} has different shape {shape} than reference {ref_shape}. "
                            f"Will regrid to reference grid."
                        )
                        # Regrid PB image to reference grid
                        # Use first tile as template (works for both CASA and FITS)
                        template_img = tiles[0] if os.path.isdir(tiles[0]) else None
                        template = template_img or str(pb_paths[0])
                        
                        # Try to use cached regridded image
                        from .cache import get_cache
                        cache = get_cache()
                        
                        def regrid_func(imagename, template, output, overwrite):
                            imregrid(imagename=imagename, template=template, output=output, overwrite=overwrite)
                        
                        regridded_pb = cache.get_regridded_image(
                            source_path=str(pb_path),
                            template_path=template,
                            regrid_func=regrid_func,
                            output_suffix=f"_pb_{i}"
                        )
                        
                        if not regridded_pb:
                            # Fallback to temporary file if caching not available
                            regridded_pb = str(output_path) + f"_pb_regrid_{i}.tmp"
                            try:
                        if template_img:
                            imregrid(
                                imagename=str(pb_path),
                                template=template_img,
                                output=regridded_pb,
                                overwrite=True,
                            )
                        else:
                            # For FITS, use first PB image as template
                            imregrid(
                                imagename=str(pb_path),
                                template=str(pb_paths[0]),
                                output=regridded_pb,
                                overwrite=True,
                            )
                            except Exception as e:
                        pb_img.close()
                                handle_casa_tool_error(
                                    'imregrid', e,
                                    image_path=pb_path,
                                    operation=f"regrid_pb_tile_{i}",
                                    template=template_img or str(pb_paths[0])
                                )
                        else:
                            LOG.debug(f"Using cached regridded PB image: {regridded_pb}")
                        
                        pb_img.close()
                        pb_img = safe_casaimage_open(regridded_pb, operation=f"read_regridded_pb_tile_{i}")
                        pb_data = pb_img.getdata()
                        validate_image_data(pb_data, regridded_pb, operation=f"read_regridded_pb_tile_{i}")
                        shape = pb_img.shape()
                
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
                        pb_response = pb_response[0, :, :] if pb_response.ndim == 3 else pb_response
                
                pb_data_list.append(pb_response.astype(np.float64))
                pb_images.append(pb_img)
                
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
                from .exceptions import ImageReadError
                raise ImageReadError(
                    f"Failed to read primary beam image: {pb_path}",
                    f"Error: {e}. "
                    "Check if the PB image exists and is readable. "
                    "Verify the image format is supported (CASA .pb directory or FITS -beam-0.fits file).",
                    context={'tile': pb_path, 'operation': f'read_pb_tile_{i}'}
                ) from e
    
    # Step 2: Read tile images
    LOG.info("Reading tile images...")
    
    tile_images = []
    tile_data_list = []
    
    for i, tile in enumerate(tiles):
        try:
                # Pre-validate tile image before reading
                validate_image_before_read(tile, operation=f"read_tile_{i}")
                
                # Read tile image with enhanced error handling
                tile_img = safe_casaimage_open(tile, operation=f"read_tile_{i}")
            tile_data = tile_img.getdata()
                
                # Validate image data
                validate_image_data(tile_data, tile, operation=f"read_tile_{i}")
            
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
                    img_data = img_data[0, :, :] if img_data.ndim == 3 else img_data
            
            # Verify shape matches PB image
            if img_data.shape != pb_data_list[i].shape:
                LOG.warning(
                    f"Tile {tile} shape {img_data.shape} doesn't match PB shape {pb_data_list[i].shape}. "
                    f"Regridding tile to PB grid."
                )
                # Regrid tile to PB grid
                # Use corresponding PB image as template
                    # Try to use cached regridded image
                    from .cache import get_cache
                    cache = get_cache()
                    
                    def regrid_func(imagename, template, output, overwrite):
                        imregrid(imagename=imagename, template=template, output=output, overwrite=overwrite)
                    
                    regridded_tile = cache.get_regridded_image(
                        source_path=str(tile),
                        template_path=str(pb_paths[i]),
                        regrid_func=regrid_func,
                        output_suffix=f"_tile_{i}"
                    )
                    
                    if not regridded_tile:
                        # Fallback to temporary file if caching not available
                        regridded_tile = str(output_path) + f"_tile_regrid_{i}.tmp"
                        try:
                imregrid(
                    imagename=str(tile),
                    template=str(pb_paths[i]),
                    output=regridded_tile,
                    overwrite=True,
                )
                        except Exception as e:
                tile_img.close()
                            handle_casa_tool_error(
                                'imregrid', e,
                                image_path=tile,
                                operation=f"regrid_tile_{i}",
                                template=str(pb_paths[i])
                            )
                    else:
                        LOG.debug(f"Using cached regridded tile image: {regridded_tile}")
                    
                    tile_img.close()
                    tile_img = safe_casaimage_open(regridded_tile, operation=f"read_regridded_tile_{i}")
                tile_data = tile_img.getdata()
                    validate_image_data(tile_data, regridded_tile, operation=f"read_regridded_tile_{i}")
                if tile_data.ndim == 2:
                    img_data = tile_data
                elif tile_data.ndim == 4:
                    img_data = tile_data[0, 0, :, :]
                else:
                    img_data = tile_data.squeeze()
                    if img_data.ndim > 2:
                        img_data = img_data[0, :, :] if img_data.ndim == 3 else img_data
            
                tile_data_list.append(img_data.astype(np.float64))
                tile_images.append(tile_img)
                
            except (ImageReadError, ImageCorruptionError, IncompatibleImageFormatError):
                # Re-raise validation errors with context
                raise
            except Exception as e:
                LOG.error(f"Failed to read tile {tile}: {e}")
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
                from .exceptions import ImageReadError
                raise ImageReadError(
                    f"Failed to read tile image: {tile}",
                    f"Error: {e}. "
                    "Check if the file exists and is readable. "
                    "Verify the image format is supported (CASA image directory or FITS file).",
                    context={'tile': tile, 'operation': f'read_tile_{i}'}
                ) from e
        
        # Step 3: Compute per-pixel weights and combine
        LOG.info("Computing pixel-by-pixel PB-weighted combination...")
        
        # Get noise variances
        noise_vars = []
        for tile in tiles:
            metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
            if metrics.rms_noise is not None and metrics.rms_noise > 0:
                noise_var = metrics.rms_noise ** 2
            else:
                # Default noise variance if not available
                noise_var = 1.0
            noise_vars.append(noise_var)
        
        # Compute weights: weight = pb_response^2 / noise_variance
        # For each pixel, combine: mosaic = sum(weight * tile) / sum(weight)
        
        ny, nx = tile_data_list[0].shape
        mosaic_data = np.zeros((ny, nx), dtype=np.float64)
        total_weight = np.zeros((ny, nx), dtype=np.float64)
        
        for i, (tile_data, pb_data, noise_var) in enumerate(zip(tile_data_list, pb_data_list, noise_vars)):
            # Compute weights: pb^2 / noise_variance
            # Clip PB values to avoid division issues
            pb_safe = np.clip(pb_data, 1e-10, None)  # Avoid zero/negative PB
            weights = (pb_safe ** 2) / noise_var
            
            # Accumulate weighted sum
            mosaic_data += weights * tile_data
            total_weight += weights
            
            LOG.debug(f"Tile {i}: min PB={pb_safe.min():.4f}, max PB={pb_safe.max():.4f}, "
                     f"noise_var={noise_var:.3e}")
        
        # Normalize by total weight (avoid division by zero)
        nonzero_mask = total_weight > 1e-10
        mosaic_data[nonzero_mask] /= total_weight[nonzero_mask]
        mosaic_data[~nonzero_mask] = np.nan
        
        LOG.info(
            f"Computed PB-weighted mosaic: "
            f"coverage={nonzero_mask.sum()}/{nonzero_mask.size} pixels "
            f"({100*nonzero_mask.sum()/nonzero_mask.size:.1f}%)"
        )
        
        # Step 4: Write mosaic image
        LOG.info(f"Writing PB-weighted mosaic to {output_path}...")
        
        # Create output image using reference coordinate system
        # Ensure output path is clean (no extensions that might confuse CASA)
        output_path_str = str(output_path)
        if output_path_str.endswith('.image'):
            output_path_str = output_path_str[:-6]
        
        output_img = casaimage()
        # Add stokes and frequency dimensions: [stokes, freq, y, x]
        output_pixels = mosaic_data[np.newaxis, np.newaxis, :, :]
        
        output_img.fromarray(
            outfile=output_path_str,
            pixels=output_pixels,
            csys=ref_coordsys,
            overwrite=True,
        )
        output_img.close()
        
        # Clean up temporary regridded images (ensure cleanup even on errors)
        temp_files_to_cleanup = []
        for i in range(len(tiles)):
            for suffix in [f"_pb_regrid_{i}.tmp", f"_tile_regrid_{i}.tmp"]:
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
                    logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")
        
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
        
        LOG.info(
            f"✓ Built PB-weighted mosaic to {output_path_str} "
            f"(pixel-by-pixel combination using PB^2/noise_variance weighting)"
        )
    
    except (ImageReadError, ImageCorruptionError, MissingPrimaryBeamError, 
            CASAToolError, GridMismatchError) as e:
        # Clean up temporary files even on error
        import shutil
        for i in range(len(tiles)):
            for suffix in [f"_pb_regrid_{i}.tmp", f"_tile_regrid_{i}.tmp"]:
                temp_path = str(output_path) + suffix
                if os.path.exists(temp_path):
                    try:
                        if os.path.isdir(temp_path):
                            shutil.rmtree(temp_path)
                        else:
                            os.remove(temp_path)
                    except Exception:
                        pass
        # Close images if they exist
        try:
            for img in tile_images:
                try:
                    img.close()
                except Exception:
                    pass
        except NameError:
            pass
        try:
            for img in pb_images:
                try:
                    img.close()
                except Exception:
                    pass
        except NameError:
            pass
        # Re-raise specific mosaic errors with their recovery hints
        raise
    except Exception as e:
        raise MosaicError(
            f"Unexpected error during weighted mosaic building: {e}",
            "Check logs for details. Try rebuilding the mosaic with --ignore-validation "
            "if validation issues are blocking the build."
        ) from e


def cmd_build(args: argparse.Namespace) -> int:
    pdb = Path(args.products_db)
    name = args.name
    out = Path(args.output).with_suffix("")
    
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        row = conn.execute("SELECT id, tiles, method FROM mosaics WHERE name = ?", (name,)).fetchone()
        if row is None:
            print("Mosaic plan not found; create with 'plan' first")
            return 1
        tiles = str(row[1]).splitlines()
        method = str(row[2] or 'mean')
    
    if not tiles:
        print("No tiles found in mosaic plan")
        return 1
    
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
            print("\nWarning: Pre-flight issues detected but ignored (--ignore-validation)")
    
    # Report resource estimates
    try:
        estimates = estimate_resources(tiles, str(out))
        print(f"\nResource estimates:")
        print(f"  - Tiles: {estimates['num_tiles']}")
        print(f"  - Estimated disk space: {estimates['estimated_disk_gb']:.1f} GB")
        print(f"  - Estimated operations: {estimates['estimated_operations']}")
        print(f"  - Estimated time: ~{estimates['estimated_time_minutes']:.0f} minutes")
    except Exception as e:
        logger.debug(f"Could not estimate resources: {e}")
    
    # Warn if output exists
    if preflight_info.get('output_exists'):
        print(f"\nWarning: Output '{out}' already exists and will be overwritten")
    
    # Comprehensive validation
    print(f"Validating {len(tiles)} tiles...")
    
    # 1. Basic grid consistency
    ok, reason = _check_consistent_tiles(tiles)
    if not ok:
        print(f"Cannot build mosaic: {reason}")
        return 2
    
    # 2. Tile quality validation (computes metrics_dict)
    is_valid, validation_issues, metrics_dict = validate_tiles_consistency(
        tiles, products_db=pdb
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
                "Use --ignore-validation to proceed anyway (not recommended for science)."
            )
        else:
            print("\nWarning: Validation issues detected but ignored (--ignore-validation)")
    
    # 3. Astrometric registration check
    try:
        astro_valid, astro_issues, offsets = verify_astrometric_registration(tiles)
    except Exception as e:
        raise ValidationError(
            f"Astrometric verification failed: {e}",
            "Check if catalog access is available. "
            "Try running with --ignore-validation to skip astrometric checks."
        ) from e
    if astro_issues:
        print("Astrometric registration issues:")
        for issue in astro_issues:
            print(f"  - {issue}")
        if not args.ignore_validation:
            print("\nMosaic build aborted due to astrometric issues.")
            return 4
    
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
                    os.getenv('CONTIMG_SCRATCH_DIR') or '/scratch/dsa110-contimg',
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
                if not immath:
                    raise CASAToolError(
                        "CASA immath not available",
                        "Ensure CASA is installed: conda activate casa6",
                        context={'tool': 'immath', 'operation': 'build_mean_mosaic'}
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
            exportfits(imagename=str(out), fitsimage=str(out) + ".fits", overwrite=True)
        except Exception as exc:
            from .error_handling import handle_casa_tool_error
            # Don't fail build if export fails, but log it properly
            try:
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
                print(f"✓ Generated {len(metrics_files)} quality metric images")
                for metric_name, metric_path in metrics_files.items():
                    print(f"  - {metric_name}: {metric_path}")
            else:
                print("Warning: No metrics generated (casacore may not be available)")
        except Exception as e:
            LOG.warning(f"Failed to generate mosaic metrics: {e}")
            print(f"Warning: Failed to generate mosaic metrics: {e}")
            # Don't fail the build if metrics generation fails
        
        # Update mosaic status
        validation_summary = "\n".join(validation_issues) if validation_issues else None
        metrics_summary = None
        if metrics_files:
            # Store metrics paths as JSON-like string (simple format)
            metrics_list = [f"{name}:{path}" for name, path in metrics_files.items()]
            metrics_summary = "\n".join(metrics_list)
        
        with ensure_products_db(pdb) as conn:
            # Check if mosaics table has metrics_path column, if not add it
            try:
                conn.execute("SELECT metrics_path FROM mosaics LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                conn.execute("ALTER TABLE mosaics ADD COLUMN metrics_path TEXT")
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
    sp.add_argument('--since', type=float, help='Only include tiles created_at >= since (epoch seconds)')
    sp.add_argument('--until', type=float, help='Only include tiles created_at <= until (epoch seconds)')
    sp.add_argument('--method', default='mean', choices=['mean', 'weighted', 'pbweighted'],
                    help='Combination method: mean (simple), weighted (noise-weighted), pbweighted (primary beam weighted)')
    sp.add_argument('--include-unpbcor', action='store_true', help='Include non-pbcor tiles')
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser('build', help='Build a mosaic from a planned set')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--name', required=True)
    sp.add_argument('--output', required=True, help='Output image base path (CASA image)')
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
