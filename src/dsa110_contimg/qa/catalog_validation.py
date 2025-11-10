"""
Catalog-based validation for image astrometry and flux scale.

Validates image quality by comparing detected sources to reference catalogs
(NVSS, VLASS) to check astrometry, flux scale, and source completeness.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astropy.io import fits
from astropy.wcs import WCS

from dsa110_contimg.catalog.query import query_sources
from dsa110_contimg.photometry.forced import measure_forced_peak
from dsa110_contimg.utils.runtime_safeguards import (
    validate_wcs_4d,
    wcs_pixel_to_world_safe,
    wcs_world_to_pixel_safe,
)

logger = logging.getLogger(__name__)


@dataclass
class CatalogValidationResult:
    """Results from catalog-based validation."""

    validation_type: str  # "astrometry", "flux_scale", "source_counts"
    image_path: str
    catalog_used: str
    n_matched: int
    n_catalog: int
    n_detected: int

    # Astrometry results
    mean_offset_arcsec: Optional[float] = None
    rms_offset_arcsec: Optional[float] = None
    max_offset_arcsec: Optional[float] = None
    offset_ra_arcsec: Optional[float] = None
    offset_dec_arcsec: Optional[float] = None

    # Flux scale results
    mean_flux_ratio: Optional[float] = None
    rms_flux_ratio: Optional[float] = None
    flux_scale_error: Optional[float] = None

    # Source counts results
    completeness: Optional[float] = None
    completeness_limit_jy: Optional[float] = (
        None  # Flux density at which completeness drops below threshold
    )
    completeness_bins_jy: Optional[List[float]] = None  # Flux bin edges (mJy)
    completeness_per_bin: Optional[List[float]] = None  # Completeness fraction per bin
    catalog_counts_per_bin: Optional[List[int]] = None  # Catalog source counts per bin
    detected_counts_per_bin: Optional[List[int]] = (
        None  # Detected source counts per bin
    )

    # Quality flags
    has_issues: bool = False
    has_warnings: bool = False
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Detailed data
    matched_pairs: Optional[List[Tuple]] = None
    matched_fluxes: Optional[List[Tuple]] = None


def scale_flux_to_frequency(
    flux_jy: float,
    source_freq_hz: float,
    target_freq_hz: float,
    spectral_index: float = -0.7,
) -> float:
    """
    Scale flux from one frequency to another using power-law spectrum.

    S_ν2 = S_ν1 * (ν2/ν1)^α

    Args:
        flux_jy: Flux density at source frequency (Jy)
        source_freq_hz: Source frequency (Hz)
        target_freq_hz: Target frequency (Hz)
        spectral_index: Spectral index α (default -0.7 for synchrotron)

    Returns:
        Scaled flux density at target frequency (Jy)
    """
    if source_freq_hz == target_freq_hz:
        return flux_jy

    ratio = (target_freq_hz / source_freq_hz) ** spectral_index
    return flux_jy * ratio


def extract_sources_from_image(
    image_path: str, min_snr: float = 5.0, rms_estimate: Optional[float] = None
) -> pd.DataFrame:
    """
    Extract source positions and fluxes from image using simple threshold method.

    This is a basic implementation. For production use, consider PyBDSF.

    Args:
        image_path: Path to FITS image
        min_snr: Minimum SNR threshold for source detection
        rms_estimate: RMS noise estimate (auto-calculated if None)

    Returns:
        DataFrame with columns: ra_deg, dec_deg, flux_jy, snr
    """
    try:
        with fits.open(image_path) as hdul:
            data = hdul[0].data
            header = hdul[0].header

            # Handle 2D, 3D, or 4D data (remove stokes/freq axes if present)
            if data.ndim > 2:
                # Take first channel/stokes
                data = data[0] if data.ndim == 3 else data[0, 0]

            # Calculate RMS if not provided
            if rms_estimate is None:
                # Use robust RMS (median absolute deviation)
                median = np.nanmedian(data)
                mad = np.nanmedian(np.abs(data - median))
                rms_estimate = 1.4826 * mad  # Convert MAD to RMS

            # Threshold for source detection
            threshold = min_snr * rms_estimate

            # Find pixels above threshold
            above_threshold = data > threshold

            if not np.any(above_threshold):
                logger.warning(f"No sources found above {min_snr}σ threshold")
                return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_jy", "snr"])

            # Get WCS for coordinate conversion
            wcs = WCS(header)

            # Find local maxima (simple peak finding)
            try:
                from scipy.ndimage import label, maximum_filter

                # Find local maxima
                local_maxima = maximum_filter(data, size=5) == data
                peaks = local_maxima & above_threshold

                # Label connected regions
                labeled, n_features = label(peaks)
            except ImportError:
                # Fallback: simple flood-fill clustering without scipy
                logger.warning(
                    "scipy not available, using simple flood-fill clustering"
                )
                # Use a simple flood-fill approach to group nearby pixels
                y_coords, x_coords = np.where(above_threshold)
                if len(x_coords) == 0:
                    return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_jy", "snr"])

                # Simple flood-fill clustering: group pixels within 2 pixels of each other
                labeled = np.zeros_like(data, dtype=int)
                n_features = 0
                visited = set()

                def flood_fill(start_y, start_x, label_id):
                    """Simple flood-fill to group connected pixels."""
                    stack = [(start_y, start_x)]
                    while stack:
                        y, x = stack.pop()
                        if (y, x) in visited or not above_threshold[y, x]:
                            continue
                        visited.add((y, x))
                        labeled[y, x] = label_id
                        # Check 8-connected neighbors
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                if dy == 0 and dx == 0:
                                    continue
                                ny, nx = y + dy, x + dx
                                if (
                                    0 <= ny < data.shape[0]
                                    and 0 <= nx < data.shape[1]
                                    and (ny, nx) not in visited
                                    and above_threshold[ny, nx]
                                ):
                                    stack.append((ny, nx))

                # Find all unvisited pixels above threshold and flood-fill
                for y, x in zip(y_coords, x_coords):
                    if (y, x) not in visited:
                        n_features += 1
                        flood_fill(y, x, n_features)

            sources = []
            for i in range(1, n_features + 1):
                # Get pixel coordinates of this source
                y_coords, x_coords = np.where(labeled == i)

                # Use centroid (weighted by flux)
                if len(x_coords) > 0:
                    x_center = np.average(x_coords, weights=data[y_coords, x_coords])
                    y_center = np.average(y_coords, weights=data[y_coords, x_coords])

                    # Convert to RA/Dec
                    wcs_validated, is_4d, defaults = validate_wcs_4d(wcs)
                    ra, dec = wcs_pixel_to_world_safe(
                        wcs_validated, x_center, y_center, is_4d, defaults
                    )

                    # Integrated flux (sum of pixels above threshold)
                    flux = np.sum(data[y_coords, x_coords])

                    # SNR
                    snr = flux / rms_estimate

                    sources.append(
                        {
                            "ra_deg": float(ra),
                            "dec_deg": float(dec),
                            "flux_jy": float(flux),
                            "snr": float(snr),
                        }
                    )

            return pd.DataFrame(sources)

    except Exception as e:
        logger.error(f"Error extracting sources from image {image_path}: {e}")
        return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_jy", "snr"])


def get_image_frequency(image_path: str) -> Optional[float]:
    """Get image frequency from FITS header."""
    try:
        with fits.open(image_path) as hdul:
            header = hdul[0].header

            # Try common frequency keywords
            if "RESTFRQ" in header:
                return header["RESTFRQ"] * 1e6  # Convert GHz to Hz
            elif "FREQ" in header:
                return header["FREQ"] * 1e6
            elif "CRVAL3" in header and header.get("CTYPE3", "").startswith("FREQ"):
                return header["CRVAL3"] * 1e6

            logger.warning(f"Could not determine frequency from image {image_path}")
            return None
    except Exception as e:
        logger.warning(f"Error reading image frequency: {e}")
        return None


def get_catalog_overlay_pixels(
    image_path: str, catalog_sources: pd.DataFrame
) -> List[Dict]:
    """
    Convert catalog RA/Dec to pixel coordinates using image WCS.

    Args:
        image_path: Path to FITS image
        catalog_sources: DataFrame with catalog sources (must have ra_deg, dec_deg columns)

    Returns:
        List of dicts with pixel coordinates and source info
    """
    try:
        with fits.open(image_path) as hdul:
            wcs = WCS(hdul[0].header)

        sources_pixels = []

        # Ensure we have the right column names
        if (
            "ra_deg" not in catalog_sources.columns
            or "dec_deg" not in catalog_sources.columns
        ):
            logger.warning("Catalog sources missing ra_deg or dec_deg columns")
            return []

        for i, row in catalog_sources.iterrows():
            ra = row["ra_deg"]
            dec = row["dec_deg"]

            # Convert to pixel coordinates
            wcs_validated, is_4d, defaults = validate_wcs_4d(wcs)
            x, y = wcs_world_to_pixel_safe(wcs_validated, ra, dec, is_4d, defaults)

            source_dict = {
                "x": float(x),
                "y": float(y),
                "ra": float(ra),
                "dec": float(dec),
                "flux_jy": float(row.get("flux_jy", row.get("flux_mjy", 0.0) / 1000.0)),
                "name": row.get("name", f"Source_{i}"),
            }

            sources_pixels.append(source_dict)

        return sources_pixels

    except Exception as e:
        logger.error(f"Error converting catalog sources to pixels: {e}")
        return []


def validate_astrometry(
    image_path: str,
    catalog: str = "nvss",
    search_radius_arcsec: float = 10.0,
    min_snr: float = 5.0,
    max_offset_arcsec: float = 5.0,
) -> CatalogValidationResult:
    """
    Validate image astrometry by matching detected sources to reference catalog.

    Args:
        image_path: Path to FITS image
        catalog: Reference catalog ("nvss" or "vlass")
        search_radius_arcsec: Maximum matching radius in arcseconds
        min_snr: Minimum SNR for detected sources
        max_offset_arcsec: Maximum acceptable astrometric offset

    Returns:
        CatalogValidationResult with astrometry metrics
    """
    # Extract sources from image
    detected_sources = extract_sources_from_image(image_path, min_snr=min_snr)
    n_detected = len(detected_sources)

    if n_detected == 0:
        result = CatalogValidationResult(
            validation_type="astrometry",
            image_path=image_path,
            catalog_used=catalog,
            n_matched=0,
            n_catalog=0,
            n_detected=0,
            has_issues=True,
            issues=["No sources detected in image"],
        )
        return result

    # Get image center and size from WCS
    with fits.open(image_path) as hdul:
        header = hdul[0].header
        wcs = WCS(header)

        # Get image center
        nx = header.get("NAXIS1", 0)
        ny = header.get("NAXIS2", 0)
        center_x = nx / 2
        center_y = ny / 2
        wcs_validated, is_4d, defaults = validate_wcs_4d(wcs)
        center_ra, center_dec = wcs_pixel_to_world_safe(
            wcs_validated, center_x, center_y, is_4d, defaults
        )

        # Estimate field size
        radius_deg = max(nx, ny) * abs(header.get("CDELT1", 0.001)) / 2 + 0.01

    # Query catalog
    catalog_sources = query_sources(
        catalog_type=catalog,
        ra_center=center_ra,
        dec_center=center_dec,
        radius_deg=radius_deg,
    )

    # Convert flux from mJy to Jy if needed
    if "flux_mjy" in catalog_sources.columns:
        catalog_sources["flux_jy"] = catalog_sources["flux_mjy"] / 1000.0
    elif "flux_jy" not in catalog_sources.columns:
        logger.warning(f"Catalog {catalog} does not have flux column")
        catalog_sources["flux_jy"] = 0.0

    n_catalog = len(catalog_sources)

    if n_catalog == 0:
        result = CatalogValidationResult(
            validation_type="astrometry",
            image_path=image_path,
            catalog_used=catalog,
            n_matched=0,
            n_catalog=0,
            n_detected=n_detected,
            has_issues=True,
            issues=["No catalog sources found in field"],
        )
        return result

    # Match sources
    detected_coords = SkyCoord(
        detected_sources["ra_deg"].values * u.deg,
        detected_sources["dec_deg"].values * u.deg,
    )
    catalog_coords = SkyCoord(
        catalog_sources["ra_deg"].values * u.deg,
        catalog_sources["dec_deg"].values * u.deg,
    )

    # Find nearest catalog source for each detected source
    idx, sep2d, _ = match_coordinates_sky(detected_coords, catalog_coords)

    # Filter matches within search radius
    sep_arcsec = sep2d.to(u.arcsec).value
    match_mask = sep_arcsec < search_radius_arcsec

    n_matched = np.sum(match_mask)

    if n_matched == 0:
        result = CatalogValidationResult(
            validation_type="astrometry",
            image_path=image_path,
            catalog_used=catalog,
            n_matched=0,
            n_catalog=n_catalog,
            n_detected=n_detected,
            has_issues=True,
            issues=[f"No sources matched within {search_radius_arcsec} arcsec"],
        )
        return result

    # Calculate offsets
    matched_sep = sep_arcsec[match_mask]
    matched_detected = detected_coords[match_mask]
    matched_catalog = catalog_coords[idx[match_mask]]

    # Calculate RA/Dec offsets
    ra_offsets = (matched_detected.ra - matched_catalog.ra).to(u.arcsec).value
    dec_offsets = (matched_detected.dec - matched_catalog.dec).to(u.arcsec).value

    mean_offset = np.mean(matched_sep)
    rms_offset = np.std(matched_sep)
    max_offset = np.max(matched_sep)
    mean_ra_offset = np.mean(ra_offsets)
    mean_dec_offset = np.mean(dec_offsets)

    # Check for issues
    issues = []
    warnings = []

    if max_offset > max_offset_arcsec:
        issues.append(
            f"Maximum astrometric offset ({max_offset:.2f} arcsec) exceeds threshold ({max_offset_arcsec} arcsec)"
        )

    if mean_offset > max_offset_arcsec * 0.5:
        warnings.append(
            f"Mean astrometric offset ({mean_offset:.2f} arcsec) is significant"
        )

    if n_matched < n_detected * 0.3:
        warnings.append(
            f"Only {n_matched}/{n_detected} detected sources matched to catalog"
        )

    matched_pairs = [
        ((det.ra.deg, det.dec.deg), (cat.ra.deg, cat.dec.deg), sep.value)
        for det, cat, sep in zip(
            matched_detected, matched_catalog, matched_sep * u.arcsec
        )
    ]

    result = CatalogValidationResult(
        validation_type="astrometry",
        image_path=image_path,
        catalog_used=catalog,
        n_matched=n_matched,
        n_catalog=n_catalog,
        n_detected=n_detected,
        mean_offset_arcsec=mean_offset,
        rms_offset_arcsec=rms_offset,
        max_offset_arcsec=max_offset,
        offset_ra_arcsec=mean_ra_offset,
        offset_dec_arcsec=mean_dec_offset,
        has_issues=len(issues) > 0,
        has_warnings=len(warnings) > 0,
        issues=issues,
        warnings=warnings,
        matched_pairs=matched_pairs,
    )

    return result


def validate_flux_scale(
    image_path: str,
    catalog: str = "nvss",
    search_radius_arcsec: float = 10.0,
    min_snr: float = 5.0,
    flux_range_jy: Tuple[float, float] = (0.01, 10.0),
    max_flux_ratio_error: float = 0.2,
    box_size_pix: int = 5,
    annulus_pix: Tuple[int, int] = (12, 20),
) -> CatalogValidationResult:
    """
    Validate image flux scale using forced photometry at catalog positions.

    Uses forced photometry (peak flux) at known catalog source positions rather
    than blind source extraction. This is more accurate for variability studies
    of known sources.

    Args:
        image_path: Path to FITS image
        catalog: Reference catalog ("nvss" or "vlass")
        search_radius_arcsec: Not used (kept for API compatibility)
        min_snr: Minimum SNR threshold for accepting measurements
        flux_range_jy: Valid flux range (min, max) in Jy
        max_flux_ratio_error: Maximum acceptable flux ratio error (0.2 = 20%)
        box_size_pix: Pixel box size for forced photometry (default: 5)
        annulus_pix: Annulus radii (inner, outer) for background estimation (default: 12, 20)

    Returns:
        CatalogValidationResult with flux scale metrics
    """
    # Get image metadata
    with fits.open(image_path) as hdul:
        header = hdul[0].header
        wcs = WCS(header)
        nx = header.get("NAXIS1", 0)
        ny = header.get("NAXIS2", 0)
        center_x = nx / 2
        center_y = ny / 2
        wcs_validated, is_4d, defaults = validate_wcs_4d(wcs)
        center_ra, center_dec = wcs_pixel_to_world_safe(
            wcs_validated, center_x, center_y, is_4d, defaults
        )
        radius_deg = max(nx, ny) * abs(header.get("CDELT1", 0.001)) / 2 + 0.01

    # Query catalog sources
    try:
        catalog_sources = query_sources(
            catalog_type=catalog,
            ra_center=center_ra,
            dec_center=center_dec,
            radius_deg=radius_deg,
        )
    except FileNotFoundError as e:
        logger.warning(f"Catalog database not found for {catalog}: {e}")
        return CatalogValidationResult(
            validation_type="flux_scale",
            image_path=image_path,
            catalog_used=catalog,
            n_matched=0,
            n_catalog=0,
            n_detected=0,
            has_issues=True,
            issues=[f"Catalog database not found: {str(e)}"],
        )
    except Exception as e:
        logger.warning(f"Error querying catalog {catalog}: {e}")
        return CatalogValidationResult(
            validation_type="flux_scale",
            image_path=image_path,
            catalog_used=catalog,
            n_matched=0,
            n_catalog=0,
            n_detected=0,
            has_issues=True,
            issues=[f"Catalog query failed: {str(e)}"],
        )

    if len(catalog_sources) == 0:
        return CatalogValidationResult(
            validation_type="flux_scale",
            image_path=image_path,
            catalog_used=catalog,
            n_matched=0,
            n_catalog=0,
            n_detected=0,
            has_issues=True,
            issues=["No catalog sources found in image field"],
        )

    # Convert flux units if needed
    if "flux_mjy" in catalog_sources.columns:
        catalog_sources["flux_jy"] = catalog_sources["flux_mjy"] / 1000.0
    elif "flux_jy" not in catalog_sources.columns:
        catalog_sources["flux_jy"] = 0.0

    # Get image frequency for flux scaling
    image_freq_hz = get_image_frequency(image_path)

    # Catalog frequencies (Hz)
    catalog_freqs = {"nvss": 1.4e9, "vlass": 3.0e9}  # 1.4 GHz  # 3 GHz
    catalog_freq_hz = catalog_freqs.get(catalog, 1.4e9)

    # Perform forced photometry at each catalog source position
    matched_fluxes = []
    flux_ratios = []
    n_valid = 0
    n_failed = 0

    for idx, cat_row in catalog_sources.iterrows():
        catalog_flux = cat_row["flux_jy"]
        catalog_ra = cat_row["ra_deg"]
        catalog_dec = cat_row["dec_deg"]

        # Skip sources with invalid flux
        if catalog_flux <= 0 or not np.isfinite(catalog_flux):
            continue

        # Scale catalog flux to image frequency
        if image_freq_hz and catalog_freq_hz != image_freq_hz:
            catalog_flux_scaled = scale_flux_to_frequency(
                catalog_flux, catalog_freq_hz, image_freq_hz
            )
        else:
            catalog_flux_scaled = catalog_flux

        # Filter by flux range
        if not (flux_range_jy[0] <= catalog_flux_scaled <= flux_range_jy[1]):
            continue

        try:
            # Forced photometry at catalog position
            result = measure_forced_peak(
                image_path,
                catalog_ra,
                catalog_dec,
                box_size_pix=box_size_pix,
                annulus_pix=annulus_pix,
            )

            image_flux = result.peak_jyb

            # Check if measurement is valid
            if not np.isfinite(image_flux) or image_flux <= 0:
                n_failed += 1
                continue

            # Check SNR (using error estimate from annulus)
            if result.peak_err_jyb and result.peak_err_jyb > 0:
                snr = image_flux / result.peak_err_jyb
                if snr < min_snr:
                    n_failed += 1
                    continue

            # Calculate flux ratio
            if catalog_flux_scaled > 0:
                ratio = image_flux / catalog_flux_scaled
                flux_ratios.append(ratio)
                matched_fluxes.append((image_flux, catalog_flux_scaled, ratio))
                n_valid += 1
            else:
                n_failed += 1

        except Exception as e:
            logger.warning(
                f"Failed forced photometry for source at ({catalog_ra:.4f}, {catalog_dec:.4f}): {e}"
            )
            n_failed += 1
            continue

    if len(flux_ratios) == 0:
        return CatalogValidationResult(
            validation_type="flux_scale",
            image_path=image_path,
            catalog_used=catalog,
            n_matched=0,
            n_catalog=len(catalog_sources),
            n_detected=0,
            has_issues=True,
            issues=[
                f"No valid flux measurements for comparison (attempted {len(catalog_sources)}, failed {n_failed})"
            ],
        )

    # Use robust statistics (median instead of mean for flux ratios)
    flux_ratios_arr = np.array(flux_ratios)
    median_flux_ratio = float(np.median(flux_ratios_arr))
    mad = np.median(np.abs(flux_ratios_arr - median_flux_ratio))
    rms_flux_ratio = float(1.4826 * mad)  # Convert MAD to RMS
    mean_flux_ratio = float(np.mean(flux_ratios_arr))  # Keep mean for compatibility
    flux_scale_error = abs(median_flux_ratio - 1.0)

    # Check for issues
    issues = []
    warnings = []

    if flux_scale_error > max_flux_ratio_error:
        issues.append(
            f"Flux scale error ({flux_scale_error*100:.1f}%) exceeds threshold ({max_flux_ratio_error*100:.1f}%)"
        )

    if rms_flux_ratio > 0.3:
        warnings.append(f"High scatter in flux ratios (RMS={rms_flux_ratio:.2f})")

    if n_failed > len(catalog_sources) * 0.5:
        warnings.append(
            f"High failure rate: {n_failed}/{len(catalog_sources)} measurements failed"
        )

    if n_valid < 3:
        warnings.append(
            f"Low number of valid measurements: {n_valid} (recommend at least 3)"
        )

    result = CatalogValidationResult(
        validation_type="flux_scale",
        image_path=image_path,
        catalog_used=catalog,
        n_matched=n_valid,
        n_catalog=len(catalog_sources),
        n_detected=n_valid,  # Forced photometry doesn't "detect", it measures at known positions
        mean_flux_ratio=mean_flux_ratio,  # Keep for API compatibility
        rms_flux_ratio=rms_flux_ratio,
        flux_scale_error=flux_scale_error,
        has_issues=len(issues) > 0,
        has_warnings=len(warnings) > 0,
        issues=issues,
        warnings=warnings,
        matched_fluxes=matched_fluxes,
    )

    return result


def validate_source_counts(
    image_path: str,
    catalog: str = "nvss",
    min_snr: float = 5.0,
    completeness_threshold: float = 0.95,
    search_radius_arcsec: float = 10.0,
    min_flux_jy: float = 0.001,
    max_flux_jy: float = 10.0,
    n_bins: int = 10,
    completeness_limit_threshold: float = 0.95,
) -> CatalogValidationResult:
    """
    Validate source detection completeness by comparing counts to catalog.

    Enhanced version with flux density binning and completeness limit calculation.

    Args:
        image_path: Path to FITS image
        catalog: Reference catalog ("nvss" or "vlass")
        min_snr: Minimum SNR threshold for source detection
        completeness_threshold: Minimum acceptable overall completeness (0.95 = 95%)
        search_radius_arcsec: Radius for matching detected sources to catalog (arcsec)
        min_flux_jy: Minimum flux density to consider (Jy)
        max_flux_jy: Maximum flux density to consider (Jy)
        n_bins: Number of flux bins for completeness analysis
        completeness_limit_threshold: Threshold for completeness limit calculation (0.95 = 95%)

    Returns:
        CatalogValidationResult with completeness metrics including:
        - Overall completeness
        - Completeness limit (flux density at which completeness drops below threshold)
        - Completeness per flux bin
        - Source counts per bin (catalog vs detected)
    """
    # Extract sources
    detected_sources = extract_sources_from_image(image_path, min_snr=min_snr)
    n_detected = len(detected_sources)

    # Get image field and frequency
    with fits.open(image_path) as hdul:
        header = hdul[0].header
        wcs = WCS(header)
        nx = header.get("NAXIS1", 0)
        ny = header.get("NAXIS2", 0)
        center_x = nx / 2
        center_y = ny / 2
        wcs_validated, is_4d, defaults = validate_wcs_4d(wcs)
        center_ra, center_dec = wcs_pixel_to_world_safe(
            wcs_validated, center_x, center_y, is_4d, defaults
        )
        radius_deg = max(nx, ny) * abs(header.get("CDELT1", 0.001)) / 2 + 0.01

    # Get image frequency for flux scaling
    image_freq_hz = get_image_frequency(image_path)
    if image_freq_hz is None:
        image_freq_hz = 1.4e9  # Default to 1.4 GHz

    # Query catalog
    catalog_sources = query_sources(
        catalog_type=catalog,
        ra_center=center_ra,
        dec_center=center_dec,
        radius_deg=radius_deg,
    )

    if len(catalog_sources) == 0:
        logger.warning(f"No catalog sources found in field")
        return CatalogValidationResult(
            validation_type="source_counts",
            image_path=image_path,
            catalog_used=catalog,
            n_matched=0,
            n_catalog=0,
            n_detected=n_detected,
            completeness=0.0,
            has_issues=True,
            issues=["No catalog sources found in field"],
        )

    # Normalize catalog flux to image frequency
    if "flux_mjy" in catalog_sources.columns:
        catalog_sources["flux_jy"] = catalog_sources["flux_mjy"] / 1000.0
    elif "flux_jy" not in catalog_sources.columns:
        logger.warning("Catalog missing flux information")
        catalog_sources["flux_jy"] = 0.01  # Default flux

    # Scale catalog fluxes to image frequency if needed
    # NVSS is at 1.4 GHz, VLASS is at 3 GHz
    catalog_freq_hz = 1.4e9 if catalog == "nvss" else 3.0e9
    if abs(image_freq_hz - catalog_freq_hz) > 1e6:  # More than 1 MHz difference
        catalog_sources["flux_jy"] = catalog_sources["flux_jy"].apply(
            lambda f: scale_flux_to_frequency(f, catalog_freq_hz, image_freq_hz)
        )

    # Filter catalog sources by flux range
    catalog_filtered = catalog_sources[
        (catalog_sources["flux_jy"] >= min_flux_jy)
        & (catalog_sources["flux_jy"] <= max_flux_jy)
    ].copy()

    n_catalog = len(catalog_filtered)

    if n_catalog == 0:
        logger.warning(
            f"No catalog sources in flux range [{min_flux_jy}, {max_flux_jy}] Jy"
        )
        return CatalogValidationResult(
            validation_type="source_counts",
            image_path=image_path,
            catalog_used=catalog,
            n_matched=0,
            n_catalog=0,
            n_detected=n_detected,
            completeness=0.0,
            has_issues=True,
            issues=[
                f"No catalog sources in flux range [{min_flux_jy}, {max_flux_jy}] Jy"
            ],
        )

    # Match detected sources to catalog sources
    if n_detected > 0 and len(detected_sources) > 0:
        # Create SkyCoord objects for matching
        catalog_coords = SkyCoord(
            ra=catalog_filtered["ra_deg"].values * u.deg,
            dec=catalog_filtered["dec_deg"].values * u.deg,
        )
        detected_coords = SkyCoord(
            ra=detected_sources["ra_deg"].values * u.deg,
            dec=detected_sources["dec_deg"].values * u.deg,
        )

        # Match within search radius
        idx, sep2d, _ = match_coordinates_sky(detected_coords, catalog_coords)
        matched_mask = sep2d.arcsec <= search_radius_arcsec

        # Mark which catalog sources were detected
        catalog_filtered = catalog_filtered.copy()
        catalog_filtered["detected"] = False
        matched_catalog_indices = idx[matched_mask]
        if len(matched_catalog_indices) > 0:
            catalog_filtered.iloc[
                matched_catalog_indices, catalog_filtered.columns.get_loc("detected")
            ] = True

        n_matched = matched_mask.sum()
    else:
        catalog_filtered["detected"] = False
        n_matched = 0

    # Calculate overall completeness
    if n_catalog == 0:
        completeness = 0.0
    else:
        completeness = n_matched / n_catalog

    # Create flux bins (logarithmic spacing)
    flux_bins = np.logspace(
        np.log10(max(min_flux_jy, catalog_filtered["flux_jy"].min())),
        np.log10(min(max_flux_jy, catalog_filtered["flux_jy"].max())),
        n_bins + 1,
    )

    # Bin catalog sources
    catalog_filtered["flux_bin"] = pd.cut(
        catalog_filtered["flux_jy"], bins=flux_bins, include_lowest=True
    )

    # Calculate completeness per bin
    bin_stats = (
        catalog_filtered.groupby("flux_bin")
        .agg(
            {
                "flux_jy": "count",  # Total catalog sources in bin
                "detected": "sum",  # Detected catalog sources in bin
            }
        )
        .rename(columns={"flux_jy": "catalog_count", "detected": "detected_count"})
    )

    # Calculate completeness per bin
    bin_stats["completeness"] = bin_stats["detected_count"] / bin_stats["catalog_count"]
    bin_stats = bin_stats.fillna(0.0)

    # Get bin centers for plotting
    bin_centers = []
    for interval in bin_stats.index:
        if pd.notna(interval):
            bin_centers.append((interval.left + interval.right) / 2)
        else:
            bin_centers.append(0.0)

    # Calculate completeness limit (flux at which completeness drops below threshold)
    completeness_limit_jy = None
    if len(bin_stats) > 0:
        # Find highest flux bin where completeness >= threshold
        above_threshold = bin_stats[
            bin_stats["completeness"] >= completeness_limit_threshold
        ]
        if len(above_threshold) > 0:
            # Use the highest flux bin that meets threshold
            highest_bin = above_threshold.index[-1]
            if pd.notna(highest_bin):
                completeness_limit_jy = (highest_bin.left + highest_bin.right) / 2

    # Prepare results
    completeness_bins_jy = bin_centers
    completeness_per_bin = bin_stats["completeness"].tolist()
    catalog_counts_per_bin = bin_stats["catalog_count"].astype(int).tolist()
    detected_counts_per_bin = bin_stats["detected_count"].astype(int).tolist()

    # Check for issues and warnings
    issues = []
    warnings = []

    if completeness < completeness_threshold:
        issues.append(
            f"Overall completeness ({completeness*100:.1f}%) below threshold ({completeness_threshold*100:.1f}%)"
        )

    if n_detected == 0:
        issues.append("No sources detected in image")

    if completeness_limit_jy is None:
        warnings.append(
            "Could not determine completeness limit (no bins meet threshold)"
        )
    elif completeness_limit_jy < min_flux_jy * 2:
        warnings.append(
            f"Completeness limit ({completeness_limit_jy*1000:.1f} mJy) is very low"
        )

    if n_matched < 3:
        warnings.append(
            f"Low number of matched sources ({n_matched}), completeness estimate may be unreliable"
        )

    result = CatalogValidationResult(
        validation_type="source_counts",
        image_path=image_path,
        catalog_used=catalog,
        n_matched=n_matched,
        n_catalog=n_catalog,
        n_detected=n_detected,
        completeness=completeness,
        completeness_limit_jy=completeness_limit_jy,
        completeness_bins_jy=completeness_bins_jy,
        completeness_per_bin=completeness_per_bin,
        catalog_counts_per_bin=catalog_counts_per_bin,
        detected_counts_per_bin=detected_counts_per_bin,
        has_issues=len(issues) > 0,
        has_warnings=len(warnings) > 0,
        issues=issues,
        warnings=warnings,
    )

    return result


def run_full_validation(
    image_path: str,
    catalog: str = "nvss",
    validation_types: Optional[List[str]] = None,
    generate_html: bool = False,
    html_output_path: Optional[str] = None,
) -> Tuple[
    Optional[CatalogValidationResult],
    Optional[CatalogValidationResult],
    Optional[CatalogValidationResult],
]:
    """
    Run all validation tests and optionally generate HTML report.

    Args:
        image_path: Path to FITS image
        catalog: Reference catalog ("nvss" or "vlass")
        validation_types: List of validation types to run. If None, runs all.
            Options: ["astrometry", "flux_scale", "source_counts"]
        generate_html: Whether to generate HTML report
        html_output_path: Path to save HTML report (required if generate_html=True)

    Returns:
        Tuple of CatalogValidationResult objects in order:
        (astrometry_result, flux_scale_result, source_counts_result)
        None values for skipped validation types.
    """
    if validation_types is None:
        validation_types = ["astrometry", "flux_scale", "source_counts"]

    astrometry_result = None
    flux_scale_result = None
    source_counts_result = None

    # Run astrometry validation
    if "astrometry" in validation_types:
        logger.info(f"Running astrometry validation for {image_path}")
        astrometry_result = validate_astrometry(image_path, catalog=catalog)

    # Run flux scale validation
    if "flux_scale" in validation_types:
        logger.info(f"Running flux scale validation for {image_path}")
        flux_scale_result = validate_flux_scale(image_path, catalog=catalog)

    # Run source counts validation
    if "source_counts" in validation_types:
        logger.info(f"Running source counts validation for {image_path}")
        source_counts_result = validate_source_counts(image_path, catalog=catalog)

    # Generate HTML report if requested
    if generate_html:
        if html_output_path is None:
            raise ValueError("html_output_path required when generate_html=True")

        from dsa110_contimg.qa.html_reports import generate_validation_report

        logger.info(f"Generating HTML validation report: {html_output_path}")
        generate_validation_report(
            image_path=image_path,
            astrometry_result=astrometry_result,
            flux_scale_result=flux_scale_result,
            source_counts_result=source_counts_result,
            output_path=html_output_path,
            catalog=catalog,
        )

    return astrometry_result, flux_scale_result, source_counts_result
