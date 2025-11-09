"""
Mosaic validation and quality checks for DSA-110 continuum imaging pipeline.

Provides comprehensive validation functions for pre-mosaicking quality checks,
following professional radio astronomy standards.

Uses caching to avoid redundant expensive operations.
"""

import logging
import os
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from .cache import get_cache

try:
    from casacore.images import image as casaimage
    from casatasks import imhead
    HAVE_CASACORE = True
except ImportError:
    HAVE_CASACORE = False

logger = logging.getLogger(__name__)


@dataclass
class TileQualityMetrics:
    """Quality metrics for a single mosaic tile."""

    tile_path: str
    pbcor_path: Optional[str] = None
    pb_path: Optional[str] = None

    # Image quality
    rms_noise: Optional[float] = None
    dynamic_range: Optional[float] = None
    has_artifacts: bool = False

    # Primary beam
    pbcor_applied: bool = False
    pb_response_min: Optional[float] = None
    pb_response_max: Optional[float] = None

    # Calibration
    ms_path: Optional[str] = None
    calibration_applied: bool = False

    # Astrometry
    ra_center: Optional[float] = None
    dec_center: Optional[float] = None

    # Quality flags
    issues: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.warnings is None:
            self.warnings = []


def _find_pbcor_path(tile_path: str) -> Optional[str]:
    """Find primary beam corrected image path."""
    # Try common suffixes
    for suffix in ['.pbcor', '.image.pbcor']:
        pbcor_path = tile_path.replace('.image', suffix)
        if os.path.exists(pbcor_path):
            return pbcor_path

    # Try adding suffix
    if not tile_path.endswith('.pbcor'):
        pbcor_path = tile_path + '.pbcor'
        if os.path.exists(pbcor_path):
            return pbcor_path

    return None


def _find_pb_path(tile_path: str) -> Optional[str]:
    """Find primary beam image path.

    Supports both CASA (`.pb`) and WSClean (`-beam-0.fits`) naming conventions.

    Args:
        tile_path: Path to tile image (CASA directory or FITS file)

    Returns:
        Path to PB image if found, None otherwise
    """
    # Handle CASA images (directory)
    if os.path.isdir(tile_path):
        # Try .pb suffix
        pb_path = tile_path.replace('.image', '.pb')
        if os.path.exists(pb_path):
            return pb_path

        # Try .image.pb
        if tile_path.endswith('.image'):
            pb_path = tile_path + '.pb'
            if os.path.exists(pb_path):
                return pb_path

    # Handle WSClean FITS outputs
    # WSClean pattern: {base}-{channel}-{type}.fits
    # PB images: {base}-{channel}-beam-0.fits or {base}-MFS-beam-0.fits

    # Try WSClean MFS pattern: {base}-MFS-beam-0.fits
    if tile_path.endswith('.fits'):
        # Try replacing -image-pb.fits with -beam-0.fits
        pb_path = tile_path.replace('-image-pb.fits', '-beam-0.fits')
        if os.path.exists(pb_path):
            return pb_path

        # Try replacing -image.fits with -beam-0.fits
        pb_path = tile_path.replace('-image.fits', '-beam-0.fits')
        if os.path.exists(pb_path):
            return pb_path

        # Try replacing -MFS-image-pb.fits with -MFS-beam-0.fits
        pb_path = tile_path.replace('-MFS-image-pb.fits', '-MFS-beam-0.fits')
        if os.path.exists(pb_path):
            return pb_path

        # Try replacing -MFS-image.fits with -MFS-beam-0.fits
        pb_path = tile_path.replace('-MFS-image.fits', '-MFS-beam-0.fits')
        if os.path.exists(pb_path):
            return pb_path

    # Try FITS file in same directory (CASA export)
    if tile_path.endswith('.fits'):
        base = tile_path.rsplit('.fits', 1)[0]
        pb_path = base + '.pb.fits'
        if os.path.exists(pb_path):
            return pb_path

    return None


def validate_tile_quality(
    tile_path: str,
    products_db: Optional[Path] = None,
    *,
    require_pbcor: bool = True,
    min_dynamic_range: float = 5.0,
    max_noise_factor: float = 5.0,
) -> TileQualityMetrics:
    """
    Validate tile quality before mosaicking.

    Uses caching to avoid redundant expensive operations.

    Args:
        tile_path: Path to tile image
        products_db: Optional products database for metadata lookup
        require_pbcor: Require primary beam corrected image
        min_dynamic_range: Minimum acceptable dynamic range
        max_noise_factor: Maximum noise factor relative to median

    Returns:
        TileQualityMetrics object
    """
    cache = get_cache()
    metrics = TileQualityMetrics(tile_path=tile_path)

    if not os.path.exists(tile_path):
        metrics.issues.append(f"Tile does not exist: {tile_path}")
        return metrics

    # Check for primary beam corrected image
    pbcor_path = _find_pbcor_path(tile_path)
    if pbcor_path:
        metrics.pbcor_path = pbcor_path
        metrics.pbcor_applied = True
    elif require_pbcor:
        metrics.issues.append(
            f"Primary beam corrected image not found for {tile_path}"
        )

    # Check for primary beam image (using cache)
    pb_path = cache.get_pb_path(tile_path, _find_pb_path)
    if pb_path:
        metrics.pb_path = pb_path

    # Get image quality metrics using cached statistics
    if HAVE_CASACORE:
        # Use cached statistics
        stats = cache.get_tile_statistics(tile_path)

        if stats:
            metrics.rms_noise = stats.get('rms_noise')
            metrics.dynamic_range = stats.get('dynamic_range')

            # Check for artifacts (would need full image read, but we can skip for now)
            # Can be added later if needed

        # Get WCS information using cached WCS metadata
        wcs_metadata = cache.get_tile_wcs_metadata(tile_path)
        if wcs_metadata:
            metrics.ra_center = wcs_metadata.get('ra_center')
            metrics.dec_center = wcs_metadata.get('dec_center')
    else:
        metrics.warnings.append(
            "casacore.images not available, limited validation")

    # Check primary beam response if PB image exists (using cached PB statistics)
    if metrics.pb_path and HAVE_CASACORE:
        pb_stats = cache.get_pb_statistics(metrics.pb_path)
        if pb_stats:
            metrics.pb_response_min = pb_stats.get('pb_response_min')
            metrics.pb_response_max = pb_stats.get('pb_response_max')

            if metrics.pb_response_min and metrics.pb_response_min < 0.1:
                metrics.warnings.append(
                    f"Low primary beam response: {metrics.pb_response_min:.3f}"
                )

    # Batch database queries (look up all tiles at once if possible)
    # Note: Individual queries still used for calibration check
    if products_db:
        try:
            with sqlite3.connect(str(products_db)) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT ms_path, noise_jy, dynamic_range FROM images WHERE path = ?",
                    (tile_path,)
                ).fetchone()

                if row:
                    metrics.ms_path = row['ms_path']
                    # Check if calibration was applied
                    cal_row = conn.execute(
                        "SELECT cal_applied FROM ms_index WHERE path = ?",
                        (metrics.ms_path,)
                    ).fetchone()
                    if cal_row and cal_row['cal_applied']:
                        metrics.calibration_applied = True
        except Exception as e:
            metrics.warnings.append(f"Failed to query products DB: {e}")

    # Validate quality thresholds
    if metrics.dynamic_range is not None:
        if metrics.dynamic_range < min_dynamic_range:
            metrics.issues.append(
                f"Dynamic range too low: {metrics.dynamic_range:.1f} < {min_dynamic_range:.1f}"
            )

    return metrics


def validate_tiles_consistency(
    tiles: List[str],
    products_db: Optional[Path] = None,
) -> Tuple[bool, List[str], Dict[str, TileQualityMetrics]]:
    """
    Validate consistency across all tiles.

    Uses caching and batch database queries for efficiency.

    Args:
        tiles: List of tile paths
        products_db: Optional products database

    Returns:
        (is_valid, issues, metrics_dict)
    """
    cache = get_cache()
    all_issues = []
    metrics_dict = {}

    # Batch database query for all tiles
    db_data = {}
    ms_paths = set()
    if products_db:
        try:
            with sqlite3.connect(str(products_db)) as conn:
                conn.row_factory = sqlite3.Row
                placeholders = ','.join(['?'] * len(tiles))
                rows = conn.execute(
                    f"SELECT path, ms_path, noise_jy, dynamic_range FROM images WHERE path IN ({placeholders})",
                    tiles
                ).fetchall()

                db_data = {row['path']: row for row in rows}
                ms_paths = {row['ms_path'] for row in rows if row['ms_path']}

            # Batch query for calibration status
            cal_status = {}
            if ms_paths:
                with sqlite3.connect(str(products_db)) as conn:
                    conn.row_factory = sqlite3.Row
                    ms_placeholders = ','.join(['?'] * len(ms_paths))
                    cal_rows = conn.execute(
                        f"SELECT path, cal_applied FROM ms_index WHERE path IN ({ms_placeholders})",
                        list(ms_paths)
                    ).fetchall()
                    cal_status = {row['path']: row['cal_applied']
                                  for row in cal_rows}
        except Exception as e:
            logger.debug(f"Batch DB query failed: {e}")

    # Validate each tile
    for tile in tiles:
        metrics = validate_tile_quality(
            tile, products_db=None)  # Skip DB query here

        # Update with batch DB data if available
        if tile in db_data:
            row = db_data[tile]
            metrics.ms_path = row['ms_path']
            if metrics.ms_path and metrics.ms_path in cal_status:
                metrics.calibration_applied = bool(cal_status[metrics.ms_path])

        metrics_dict[tile] = metrics

        if metrics.issues:
            all_issues.extend([f"{tile}: {issue}" for issue in metrics.issues])

    # Check consistency
    if not HAVE_CASACORE:
        all_issues.append(
            "casacore.images not available, cannot check consistency")
        return False, all_issues, metrics_dict

    # Check grid consistency using cached headers
    ref_header = None
    ref_tile = None
    for tile in tiles:
        try:
            header = cache.get_tile_header(tile)
            if header:
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

                key = (shape, header.get('cdelt1'), header.get('cdelt2'))
                if ref_header is None:
                    ref_header = key
                    ref_tile = tile
                else:
                    # Compare with tolerance for floating-point values
                    ref_shape, ref_cdelt1, ref_cdelt2 = ref_header
                    if shape != ref_shape:
                        all_issues.append(
                            f"Grid inconsistency: {tile} shape {shape} differs from {ref_tile} shape {ref_shape}"
                        )
                    # Use relative tolerance for cell size comparison
                    cdelt1 = header.get('cdelt1')
                    cdelt2 = header.get('cdelt2')
                    if cdelt1 is not None and ref_cdelt1 is not None:
                        if abs(cdelt1 - ref_cdelt1) > max(1e-12, abs(ref_cdelt1) * 1e-9):
                            all_issues.append(
                                f"Grid inconsistency: {tile} cdelt1 {cdelt1} differs from {ref_tile} cdelt1 {ref_cdelt1}"
                            )
                    if cdelt2 is not None and ref_cdelt2 is not None:
                        if abs(cdelt2 - ref_cdelt2) > max(1e-12, abs(ref_cdelt2) * 1e-9):
                            all_issues.append(
                                f"Grid inconsistency: {tile} cdelt2 {cdelt2} differs from {ref_tile} cdelt2 {ref_cdelt2}"
                            )
        except Exception as e:
            all_issues.append(f"Failed to read header for {tile}: {e}")

    # Check noise consistency
    noise_values = [m.rms_noise for m in metrics_dict.values()
                    if m.rms_noise is not None]
    if len(noise_values) > 1:
        median_noise = np.median(noise_values)
        for tile, metrics in metrics_dict.items():
            if metrics.rms_noise is not None:
                noise_factor = metrics.rms_noise / median_noise
                if noise_factor > 5.0:
                    all_issues.append(
                        f"Unusually high noise in {tile}: "
                        f"{metrics.rms_noise:.3e} (median: {median_noise:.3e})"
                    )

    # Check primary beam correction consistency
    pbcor_counts = sum(1 for m in metrics_dict.values() if m.pbcor_applied)
    if pbcor_counts > 0 and pbcor_counts < len(metrics_dict):
        all_issues.append(
            f"Primary beam correction inconsistent: "
            f"{pbcor_counts}/{len(metrics_dict)} tiles have PB correction"
        )

    # Check synthesized beam consistency using cached headers
    beam_majors = []
    beam_minors = []
    beam_info = {}
    for tile in tiles:
        try:
            header = cache.get_tile_header(tile)
            if not header:
                continue

            # Try to get beam information
            try:
                # CASA imhead returns beam in various formats
                beam_major = header.get('beammajor')
                beam_minor = header.get('beamminor')
                beam_pa = header.get('beampa')

                if beam_major is not None and beam_minor is not None:
                    # Convert to arcseconds if needed
                    if isinstance(beam_major, dict):
                        maj_val = beam_major.get('value', 0)
                        maj_unit = beam_major.get('unit', 'arcsec')
                    else:
                        maj_val = beam_major
                        maj_unit = 'arcsec'

                    if isinstance(beam_minor, dict):
                        min_val = beam_minor.get('value', 0)
                        min_unit = beam_minor.get('unit', 'arcsec')
                    else:
                        min_val = beam_minor
                        min_unit = 'arcsec'

                    # Convert to arcseconds
                    if maj_unit == 'deg':
                        maj_val *= 3600.0
                    elif maj_unit == 'rad':
                        maj_val *= 206265.0

                    if min_unit == 'deg':
                        min_val *= 3600.0
                    elif min_unit == 'rad':
                        min_val *= 206265.0

                    if maj_val > 0 and min_val > 0:
                        beam_majors.append(maj_val)
                        beam_minors.append(min_val)
                        beam_info[tile] = {
                            'major': maj_val,
                            'minor': min_val,
                            'pa': beam_pa.get('value') if isinstance(beam_pa, dict) else beam_pa
                        }
            except Exception:
                # Beam info not available or in unexpected format
                logger.debug(f"Could not extract beam info for {tile}")
        except Exception as e:
            logger.debug(f"Failed to check beam for {tile}: {e}")

    # Check beam consistency if we have beam info for multiple tiles
    if len(beam_majors) > 1:
        median_major = np.median(beam_majors)
        median_minor = np.median(beam_minors)

        # Check for outliers (more than 20% difference)
        for tile, info in beam_info.items():
            maj_diff = abs(info['major'] - median_major) / median_major
            min_diff = abs(info['minor'] - median_minor) / median_minor

            if maj_diff > 0.2 or min_diff > 0.2:
                all_issues.append(
                    f"Tile {tile} has unusual synthesized beam: "
                    f"major={info['major']:.2f}\" (median: {median_major:.2f}\"), "
                    f"minor={info['minor']:.2f}\" (median: {median_minor:.2f}\")"
                )

    return len(all_issues) == 0, all_issues, metrics_dict


def verify_astrometric_registration(
    tiles: List[str],
    catalog_path: Optional[str] = None,
    max_offset_arcsec: float = 2.0,
    min_flux_mjy: float = 10.0,
    min_sources: int = 3,
) -> Tuple[bool, List[str], Dict[str, Tuple[float, float]]]:
    """
    Verify astrometric registration of tiles using catalog comparison.

    Uses cached WCS metadata and catalog queries for efficiency.

    Compares source positions in tiles with catalog (NVSS) to detect systematic
    pointing offsets. For each tile:
    1. Queries catalog for sources within tile FoV
    2. Finds peaks in image near catalog positions
    3. Computes offsets between catalog and detected positions
    4. Detects systematic offsets exceeding threshold

    Args:
        tiles: List of tile paths
        catalog_path: Optional explicit catalog path (auto-resolved if None)
        max_offset_arcsec: Maximum acceptable systematic offset
        min_flux_mjy: Minimum catalog flux for source matching
        min_sources: Minimum number of matched sources required per tile

    Returns:
        (is_valid, issues, offsets_dict) where offsets_dict maps tile -> (ra_offset_arcsec, dec_offset_arcsec)
    """
    cache = get_cache()
    issues = []
    offsets_dict = {}

    if not HAVE_CASACORE:
        return False, ["casacore.images not available"], offsets_dict

    # Import catalog query functionality
    try:
        from dsa110_contimg.catalog.query import query_sources
        from astropy.coordinates import SkyCoord
        import astropy.units as u
    except ImportError as e:
        return False, [f"Catalog query module not available: {e}"], offsets_dict

    # Process each tile
    for tile in tiles:
        try:
            # Use cached WCS metadata
            wcs_metadata = cache.get_tile_wcs_metadata(tile)
            if not wcs_metadata:
                issues.append(f"Failed to get WCS metadata for {tile}")
                continue

            ra_center = wcs_metadata.get('ra_center')
            dec_center = wcs_metadata.get('dec_center')
            cdelt_ra = wcs_metadata.get('cdelt_ra')
            cdelt_dec = wcs_metadata.get('cdelt_dec')
            shape = wcs_metadata.get('shape')

            if ra_center is None or dec_center is None:
                issues.append(f"Failed to get center position from {tile}")
                continue

            # Estimate FoV from image dimensions
            # Handle shape as numpy array, list, tuple, or string
            if shape is not None:
                # Convert to tuple if needed
                if isinstance(shape, (list, np.ndarray)):
                    shape = tuple(shape)
                elif isinstance(shape, str):
                    # Parse string representation like "[6300 6300    1    1]"
                    import ast
                    import re
                    try:
                        # Convert space-separated values to comma-separated
                        # e.g., "[6300 6300    1    1]" -> "[6300, 6300, 1, 1]"
                        shape_str = re.sub(r'\s+', ', ', shape.strip())
                        shape = ast.literal_eval(shape_str)
                        if isinstance(shape, (list, np.ndarray)):
                            shape = tuple(shape)
                    except Exception:
                        shape = None

                if shape and len(shape) >= 2:
                    ny, nx = shape[-2], shape[-1]
                else:
                    issues.append(f"Failed to get valid shape for {tile}")
                    continue
            else:
                issues.append(f"Failed to get shape for {tile}")
                continue

            # Fallback pixel scales if not in metadata
            if cdelt_ra is None:
                cdelt_ra = 2.0 / 3600.0  # Assume ~2 arcsec pixels
            if cdelt_dec is None:
                cdelt_dec = 2.0 / 3600.0

            # Ensure cdelt values are scalars (handle cached arrays)
            if isinstance(cdelt_ra, (list, np.ndarray)):
                cdelt_ra = float(cdelt_ra[0] if len(
                    cdelt_ra) > 0 else 2.0 / 3600.0)
            if isinstance(cdelt_dec, (list, np.ndarray)):
                cdelt_dec = float(cdelt_dec[0] if len(
                    cdelt_dec) > 0 else 2.0 / 3600.0)

            # Estimate FoV radius (half diagonal)
            fov_radius_deg = np.sqrt(
                (nx * cdelt_ra)**2 + (ny * cdelt_dec)**2) / 2.0

            # Query catalog sources (cached)
            try:
                def query_func(ra, dec, radius, cat_name):
                    return query_sources(
                        catalog_type=cat_name,
                        ra_center=ra,
                        dec_center=dec,
                        radius_deg=radius,
                        min_flux_mjy=min_flux_mjy,
                        catalog_path=catalog_path,
                    )

                catalog_df = cache.query_catalog_cached(
                    ra_deg=ra_center,
                    dec_deg=dec_center,
                    radius_deg=fov_radius_deg,
                    catalog_name="nvss",
                    query_func=query_func
                )
            except Exception as e:
                issues.append(f"Failed to query catalog for {tile}: {e}")
                continue

            # Ensure catalog_df is a DataFrame
            import pandas as pd
            if not isinstance(catalog_df, pd.DataFrame):
                issues.append(
                    f"Catalog query returned unexpected type ({type(catalog_df)}) "
                    f"for {tile}, skipping astrometric verification"
                )
                continue

            if len(catalog_df) < min_sources:
                issues.append(
                    f"Insufficient catalog sources ({len(catalog_df)} < {min_sources}) "
                    f"for astrometric verification in {tile}"
                )
                continue

            # Need to read image for peak finding (can't cache this easily)
            # But we can use cached coordinate system
            img = casaimage(tile)
            coord_sys = cache.get_tile_coordsys(tile) or img.coordsys()
            data = img.getdata()

            # Extract 2D image data
            if data.ndim == 2:
                img_data = data
            elif data.ndim == 4:
                img_data = data[0, 0, :, :]
            else:
                img_data = data.squeeze()
                if img_data.ndim > 2:
                    img_data = img_data[0, :,
                                        :] if img_data.ndim == 3 else img_data

            # Match catalog sources with image peaks
            offsets_ra_arcsec = []
            offsets_dec_arcsec = []

            # Get reference pixel for coordinate conversion
            # Handle both coordsys() and coordinates() objects
            try:
                ref_pix = coord_sys.referencepixel()
            except AttributeError:
                # Fallback to get_referencepixel() for coordinates() objects (FITS files)
                ref_pix = coord_sys.get_referencepixel()

            if len(ref_pix) >= 2:
                # Extract scalar values, handling arrays
                ref_x_val = ref_pix[0]
                ref_y_val = ref_pix[1]
                if isinstance(ref_x_val, np.ndarray):
                    ref_x = float(ref_x_val[0])
                else:
                    ref_x = float(ref_x_val)
                if isinstance(ref_y_val, np.ndarray):
                    ref_y = float(ref_y_val[0])
                else:
                    ref_y = float(ref_y_val)
            else:
                ref_x = nx / 2.0
                ref_y = ny / 2.0

            for _, cat_row in catalog_df.iterrows():
                cat_ra = float(cat_row['ra_deg'])
                cat_dec = float(cat_row['dec_deg'])

                # Convert catalog position to pixel coordinates
                try:
                    # Use CASA coordinate system to convert sky to pixel
                    try:
                        pixel_coords = coord_sys.topixelmany(
                            [[cat_ra, cat_dec]])[0]
                        pix_x = float(pixel_coords[0])
                        pix_y = float(pixel_coords[1])
                    except (AttributeError, TypeError):
                        # Fallback: manual calculation
                        dra = (cat_ra - ra_center) * \
                            np.cos(np.radians(dec_center))
                        ddec = cat_dec - dec_center
                        pix_x = ref_x + dra / cdelt_ra
                        pix_y = ref_y + ddec / cdelt_dec

                    # Find peak near this position
                    search_radius_pix = 10
                    x_min = max(0, int(pix_x - search_radius_pix))
                    x_max = min(nx, int(pix_x + search_radius_pix))
                    y_min = max(0, int(pix_y - search_radius_pix))
                    y_max = min(ny, int(pix_y + search_radius_pix))

                    if x_max > x_min and y_max > y_min:
                        search_region = img_data[y_min:y_max, x_min:x_max]
                        if search_region.size > 0:
                            peak_idx = np.unravel_index(
                                np.argmax(search_region), search_region.shape)
                            peak_y = y_min + peak_idx[0]
                            peak_x = x_min + peak_idx[1]

                            # Convert peak pixel back to sky coordinates
                            try:
                                world_coords = coord_sys.toworldmany(
                                    [[peak_x, peak_y]])[0]
                                det_ra = float(world_coords[0])
                                det_dec = float(world_coords[1])
                            except (AttributeError, TypeError):
                                # Fallback: manual calculation
                                pix_offset_x = peak_x - ref_x
                                pix_offset_y = peak_y - ref_y
                                det_ra = ra_center + \
                                    (pix_offset_x * cdelt_ra) / \
                                    np.cos(np.radians(dec_center))
                                det_dec = dec_center + pix_offset_y * cdelt_dec

                            # Compute offset (in arcseconds)
                            offset_ra = (det_ra - cat_ra) * \
                                np.cos(np.radians(dec_center)) * 3600.0
                            offset_dec = (det_dec - cat_dec) * 3600.0

                            offsets_ra_arcsec.append(offset_ra)
                            offsets_dec_arcsec.append(offset_dec)

                except Exception as e:
                    logger.debug(
                        f"Failed to match catalog source at ({cat_ra}, {cat_dec}): {e}")
                    continue

            img.close()

            if len(offsets_ra_arcsec) < min_sources:
                issues.append(
                    f"Insufficient matched sources ({len(offsets_ra_arcsec)} < {min_sources}) "
                    f"for astrometric verification in {tile}"
                )
                continue

            # Compute systematic offset
            median_offset_ra = np.median(offsets_ra_arcsec)
            median_offset_dec = np.median(offsets_dec_arcsec)
            offset_magnitude = np.sqrt(
                median_offset_ra**2 + median_offset_dec**2)

            offsets_dict[tile] = (median_offset_ra, median_offset_dec)

            if offset_magnitude > max_offset_arcsec:
                issues.append(
                    f"Systematic astrometric offset detected in {tile}: "
                    f"RA={median_offset_ra:.2f}\", Dec={median_offset_dec:.2f}\" "
                    f"(magnitude={offset_magnitude:.2f}\" > {max_offset_arcsec}\")"
                )

        except Exception as e:
            issues.append(f"Failed to verify astrometry for {tile}: {e}")
            logger.exception(f"Error verifying astrometry for {tile}")

    return len(issues) == 0, issues, offsets_dict


def check_calibration_consistency(
    tiles: List[str],
    products_db: Path,
    registry_db: Optional[Path] = None,
) -> Tuple[bool, List[str], Dict[str, Dict[str, Any]]]:
    """
    Check calibration consistency across tiles.

    Verifies that:
    1. Calibration tables applied are consistent across tiles
    2. Calibration solution quality metrics are similar
    3. Calibration table validity windows overlap appropriately

    Args:
        tiles: List of tile paths
        products_db: Products database path
        registry_db: Optional calibration registry database path

    Returns:
        (is_consistent, issues, calibration_dict) where calibration_dict maps
        tile -> dict with 'ms_path', 'caltables', 'cal_applied', etc.
    """
    issues = []
    calibration_dict = {}

    try:
        with sqlite3.connect(str(products_db)) as conn:
            conn.row_factory = sqlite3.Row

            # Get MS paths and calibration status for each tile
            ms_paths = []
            tile_to_ms = {}
            for tile in tiles:
                row = conn.execute(
                    "SELECT ms_path FROM images WHERE path = ?",
                    (tile,)
                ).fetchone()
                if row:
                    ms_path = row['ms_path']
                    ms_paths.append(ms_path)
                    tile_to_ms[tile] = ms_path
                    calibration_dict[tile] = {
                        'ms_path': ms_path,
                        'cal_applied': False,
                        'caltables': [],
                        'cal_set_name': None,
                    }

            # Check calibration status from products DB
            for ms_path in ms_paths:
                row = conn.execute(
                    "SELECT cal_applied FROM ms_index WHERE path = ?",
                    (ms_path,)
                ).fetchone()
                if row:
                    cal_applied = bool(row['cal_applied'])
                    # Update calibration_dict for all tiles using this MS
                    for tile, ms in tile_to_ms.items():
                        if ms == ms_path:
                            calibration_dict[tile]['cal_applied'] = cal_applied

            # Query calibration registry for applied tables
            if registry_db and registry_db.exists():
                try:
                    from dsa110_contimg.calibration.apply_service import get_active_caltables
                    from dsa110_contimg.utils.time_utils import extract_ms_time_range

                    # Get calibration tables for each MS
                    for tile, ms_path in tile_to_ms.items():
                        try:
                            # Get observation time range for MS using standardized utility
                            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(
                                ms_path)

                            if mid_mjd is not None:
                                # Get active calibration tables for this observation
                                caltables = get_active_caltables(
                                    ms_path,
                                    registry_db,
                                    mid_mjd=mid_mjd,
                                )

                                calibration_dict[tile]['caltables'] = caltables

                                # Get calibration set name from registry
                                try:
                                    with sqlite3.connect(str(registry_db)) as reg_conn:
                                        reg_conn.row_factory = sqlite3.Row
                                        # Find set_name for these tables
                                        if caltables:
                                            # Get set_name from first table
                                            first_table = caltables[0]
                                            row = reg_conn.execute(
                                                "SELECT set_name FROM caltables WHERE path = ?",
                                                (first_table,)
                                            ).fetchone()
                                            if row:
                                                calibration_dict[tile]['cal_set_name'] = row['set_name']

                                except Exception as e:
                                    logger.debug(
                                        f"Failed to query registry for {tile}: {e}")

                        except Exception as e:
                            logger.debug(
                                f"Failed to get calibration tables for {tile}: {e}")

                except ImportError:
                    logger.debug(
                        "Calibration apply_service not available, skipping registry query")

            # Check consistency
            cal_applied_list = [cal_dict['cal_applied']
                                for cal_dict in calibration_dict.values()]
            if len(cal_applied_list) > 0:
                if not all(cal_applied_list):
                    issues.append(
                        f"Calibration inconsistent: "
                        f"{sum(cal_applied_list)}/{len(cal_applied_list)} tiles have calibration applied"
                    )

            # Compare calibration table sets
            cal_table_sets = {}
            for tile, cal_dict in calibration_dict.items():
                caltables = cal_dict.get('caltables', [])
                if caltables:
                    # Use set_name if available, otherwise use sorted table paths
                    set_name = cal_dict.get('cal_set_name')
                    if set_name:
                        cal_table_sets[tile] = set_name
                    else:
                        # Use sorted table paths as identifier
                        cal_table_sets[tile] = tuple(sorted(caltables))

            if len(cal_table_sets) > 1:
                # Check if all tiles use the same calibration set
                unique_sets = set(cal_table_sets.values())
                if len(unique_sets) > 1:
                    # Group tiles by calibration set
                    set_to_tiles = {}
                    for tile, cal_set in cal_table_sets.items():
                        if cal_set not in set_to_tiles:
                            set_to_tiles[cal_set] = []
                        set_to_tiles[cal_set].append(tile)

                    issues.append(
                        f"Calibration table sets inconsistent across tiles: "
                        f"{len(unique_sets)} different sets found"
                    )
                    for cal_set, tile_list in set_to_tiles.items():
                        set_name = str(cal_set)[:50]  # Truncate long paths
                        issues.append(
                            f"  Set '{set_name}': {len(tile_list)} tiles"
                        )

            # Check calibration table validity windows (if registry available)
            if registry_db and registry_db.exists() and len(cal_table_sets) > 0:
                try:
                    with sqlite3.connect(str(registry_db)) as reg_conn:
                        reg_conn.row_factory = sqlite3.Row

                        # Get validity windows for calibration sets
                        validity_windows = {}
                        for tile, cal_set in cal_table_sets.items():
                            if isinstance(cal_set, str):
                                # Query validity windows for this set
                                rows = reg_conn.execute(
                                    """
                                    SELECT MIN(valid_start_mjd) as start_mjd,
                                           MAX(valid_end_mjd) as end_mjd
                                    FROM caltables
                                    WHERE set_name = ? AND status = 'active'
                                    """,
                                    (cal_set,)
                                ).fetchone()

                                if rows and rows['start_mjd'] and rows['end_mjd']:
                                    validity_windows[cal_set] = (
                                        rows['start_mjd'],
                                        rows['end_mjd']
                                    )

                        # Check if validity windows overlap
                        if len(validity_windows) > 1:
                            windows = list(validity_windows.values())
                            # Check pairwise overlap
                            for i in range(len(windows)):
                                for j in range(i + 1, len(windows)):
                                    start1, end1 = windows[i]
                                    start2, end2 = windows[j]

                                    # Check if windows overlap
                                    if not (end1 >= start2 and end2 >= start1):
                                        issues.append(
                                            f"Calibration validity windows do not overlap: "
                                            f"Set 1: {start1:.2f}-{end1:.2f} MJD, "
                                            f"Set 2: {start2:.2f}-{end2:.2f} MJD"
                                        )

                except Exception as e:
                    logger.debug(f"Failed to check validity windows: {e}")

    except Exception as e:
        issues.append(f"Failed to check calibration consistency: {e}")

    return len(issues) == 0, issues, calibration_dict


def check_primary_beam_consistency(
    tiles: List[str],
    metrics_dict: Optional[Dict[str, TileQualityMetrics]] = None,
) -> Tuple[bool, List[str], Dict[str, Dict[str, Any]]]:
    """
    Check primary beam pattern consistency across tiles.

    Verifies that:
    1. Primary beam models are consistent across tiles
    2. Frequency-dependent effects are properly handled
    3. PB correction was applied correctly (not double-corrected)

    Args:
        tiles: List of tile paths
        metrics_dict: Optional pre-computed TileQualityMetrics dict

    Returns:
        (is_consistent, issues, pb_info_dict) where pb_info_dict maps
        tile -> dict with 'pb_path', 'freq_ghz', 'pb_pattern', etc.
    """
    issues = []
    pb_info_dict = {}

    if not HAVE_CASACORE:
        return False, ["casacore.images not available"], pb_info_dict

    # Extract PB model information for each tile
    for tile in tiles:
        pb_info = {
            'pb_path': None,
            'freq_ghz': None,
            'bandwidth_mhz': None,
            'pb_pattern': None,
            'pb_response_min': None,
            'pb_response_max': None,
            'pbcor_applied': False,
        }

        try:
            # Get PB path (from metrics_dict or find it using cache)
            cache = get_cache()
            if metrics_dict and tile in metrics_dict:
                pb_path = metrics_dict[tile].pb_path
                pbcor_applied = metrics_dict[tile].pbcor_applied
            else:
                pb_path = cache.get_pb_path(tile, _find_pb_path)
                pbcor_path = _find_pbcor_path(tile)
                pbcor_applied = pbcor_path is not None

            pb_info['pb_path'] = pb_path
            pb_info['pbcor_applied'] = pbcor_applied

            if not pb_path or not os.path.exists(pb_path):
                issues.append(f"Primary beam image not found for {tile}")
                pb_info_dict[tile] = pb_info
                continue

            # Use cached PB statistics
            cache = get_cache()
            pb_stats = cache.get_pb_statistics(str(pb_path))

            if pb_stats:
                pb_info['pb_response_min'] = pb_stats.get('pb_response_min')
                pb_info['pb_response_max'] = pb_stats.get('pb_response_max')

            # Read PB image for additional metadata (frequency, etc.)
            try:
                pb_img = casaimage(str(pb_path))
                pb_data = pb_img.getdata()
                coord_sys = pb_img.coordsys()

                # Extract frequency information from coordinate system
                try:
                    # Try to get frequency from coordinate system
                    freq_info = coord_sys.spectral()
                    if freq_info:
                        # Get reference frequency
                        ref_freq = freq_info.get('restfreq', [None])[0]
                        if ref_freq:
                            pb_info['freq_ghz'] = float(ref_freq) / 1e9

                    # Try to get frequency from image header metadata
                    try:
                        summary = pb_img.summary()
                        if 'refval' in summary:
                            refval = summary['refval']
                            if len(refval) >= 3:  # [stokes, freq, ra, dec]
                                freq_val = refval[1]
                                if freq_val:
                                    pb_info['freq_ghz'] = float(freq_val) / 1e9
                    except Exception:
                        pass

                except Exception:
                    # Frequency extraction failed, try to infer from MS or tile
                    logger.debug(
                        f"Failed to extract frequency from PB image {pb_path}")

                # Extract PB response statistics
                valid_pb = pb_data[np.isfinite(pb_data) & (pb_data > 0)]
                if len(valid_pb) > 0:
                    pb_info['pb_response_min'] = float(valid_pb.min())
                    pb_info['pb_response_max'] = float(valid_pb.max())

                    # Basic pattern check: verify PB has reasonable shape
                    # (should peak near center, decrease toward edges)
                    pb_2d = pb_data.squeeze()
                    if pb_2d.ndim == 2:
                        ny, nx = pb_2d.shape
                        center_y, center_x = ny // 2, nx // 2
                        center_pb = pb_2d[center_y, center_x]

                        # Check edge vs center (should be lower at edges)
                        edge_pb = np.mean([
                            pb_2d[0, :].mean(),
                            pb_2d[-1, :].mean(),
                            pb_2d[:, 0].mean(),
                            pb_2d[:, -1].mean(),
                        ])

                        if center_pb > 0 and edge_pb > 0:
                            edge_ratio = edge_pb / center_pb
                            if edge_ratio > 0.9:
                                issues.append(
                                    f"Unusual PB pattern in {tile}: "
                                    f"edge/center ratio = {edge_ratio:.3f} (expected <0.5)"
                                )

                pb_img.close()

            except Exception as e:
                issues.append(f"Failed to read PB image {pb_path}: {e}")
                logger.debug(f"Error reading PB image {pb_path}: {e}")

            pb_info_dict[tile] = pb_info

        except Exception as e:
            issues.append(f"Failed to check PB consistency for {tile}: {e}")
            logger.debug(f"Error checking PB for {tile}: {e}")

    # Compare PB models across tiles
    if len(pb_info_dict) > 1:
        # Check frequency consistency
        freq_values = [info['freq_ghz'] for info in pb_info_dict.values()
                       if info['freq_ghz'] is not None]

        if len(freq_values) > 1:
            freq_median = np.median(freq_values)
            freq_range = np.max(freq_values) - np.min(freq_values)

            # Warn if frequency spread is large (>50 MHz)
            if freq_range > 0.05:  # 50 MHz
                issues.append(
                    f"Large frequency spread across tiles: "
                    f"{freq_range*1000:.1f} MHz (median: {freq_median:.3f} GHz). "
                    f"Frequency-dependent PB variations may cause flux errors."
                )

            # Check for outliers
            for tile, info in pb_info_dict.items():
                if info['freq_ghz'] is not None:
                    freq_diff = abs(info['freq_ghz'] - freq_median)
                    if freq_diff > 0.05:  # More than 50 MHz difference
                        issues.append(
                            f"Tile {tile} has unusual frequency: "
                            f"{info['freq_ghz']:.3f} GHz (median: {freq_median:.3f} GHz)"
                        )

        # Check PB correction consistency
        pbcor_counts = sum(1 for info in pb_info_dict.values()
                           if info['pbcor_applied'])
        if pbcor_counts > 0 and pbcor_counts < len(pb_info_dict):
            issues.append(
                f"PB correction inconsistent: "
                f"{pbcor_counts}/{len(pb_info_dict)} tiles have PB correction applied"
            )

        # Check PB response range consistency
        pb_mins = [info['pb_response_min'] for info in pb_info_dict.values()
                   if info['pb_response_min'] is not None]
        pb_maxs = [info['pb_response_max'] for info in pb_info_dict.values()
                   if info['pb_response_max'] is not None]

        if len(pb_mins) > 1 and len(pb_maxs) > 1:
            min_median = np.median(pb_mins)
            max_median = np.median(pb_maxs)

            # Check for outliers
            for tile, info in pb_info_dict.items():
                if info['pb_response_min'] is not None and info['pb_response_max'] is not None:
                    if info['pb_response_min'] < min_median * 0.5:
                        issues.append(
                            f"Tile {tile} has unusually low PB response: "
                            f"min={info['pb_response_min']:.3f} (median: {min_median:.3f})"
                        )
                    if info['pb_response_max'] > max_median * 1.5:
                        issues.append(
                            f"Tile {tile} has unusually high PB response: "
                            f"max={info['pb_response_max']:.3f} (median: {max_median:.3f})"
                        )

    return len(issues) == 0, issues, pb_info_dict
