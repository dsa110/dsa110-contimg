"""
Photometry validation module.

Validates forced photometry accuracy and consistency across images.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits

from dsa110_contimg.qa.base import (
    ValidationContext,
    ValidationError,
    ValidationInputError,
    ValidationResult,
)
from dsa110_contimg.qa.config import PhotometryConfig, get_default_config

logger = logging.getLogger(__name__)


@dataclass
class PhotometryValidationResult(ValidationResult):
    """Result of photometry validation."""

    # Photometry-specific metrics
    n_sources_validated: int = 0
    n_sources_passed: int = 0
    n_sources_failed: int = 0

    # Accuracy metrics
    mean_flux_error_fraction: float = 0.0
    rms_flux_error_fraction: float = 0.0
    max_flux_error_fraction: float = 0.0

    # Position accuracy
    mean_position_offset_arcsec: float = 0.0
    rms_position_offset_arcsec: float = 0.0

    # Consistency metrics (if multiple images)
    flux_consistency_rms: Optional[float] = None

    # Per-source results
    source_results: List[Dict[str, any]] = field(default_factory=list)  # type: ignore

    def __post_init__(self):
        """Initialize defaults."""
        super().__post_init__()
        if self.source_results is None:
            self.source_results = []

    def calculate_pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.n_sources_validated == 0:
            return 0.0
        return self.n_sources_passed / self.n_sources_validated


def validate_forced_photometry(
    image_path: str,
    catalog_path: Optional[str] = None,
    catalog_sources: Optional[List[Dict]] = None,
    photometry_results: Optional[List[Dict]] = None,
    config: Optional[PhotometryConfig] = None,
) -> PhotometryValidationResult:
    """Validate forced photometry accuracy.

    Compares forced photometry measurements with catalog fluxes to validate
    accuracy and consistency.

    Args:
        image_path: Path to FITS image
        catalog_path: Path to catalog file (optional if catalog_sources provided)
        catalog_sources: List of catalog sources with 'ra', 'dec', 'flux' keys
        photometry_results: List of photometry results with 'ra', 'dec', 'flux', 'flux_err' keys
        config: Photometry validation configuration

    Returns:
        PhotometryValidationResult with validation status and metrics

    Raises:
        ValidationInputError: If inputs are invalid
        ValidationError: If validation fails
    """
    if config is None:
        config = get_default_config().photometry

    # Validate inputs
    image_path_obj = Path(image_path)
    if not image_path_obj.exists():
        raise ValidationInputError(f"Image file not found: {image_path}")

    if catalog_sources is None and catalog_path is None:
        raise ValidationInputError(
            "Either catalog_path or catalog_sources must be provided"
        )

    if photometry_results is None:
        raise ValidationInputError("photometry_results must be provided")

    try:
        # Load image header for WCS
        with fits.open(image_path) as hdul:
            header = hdul[0].header
            wcs = None  # Would need to create WCS from header

        # Match photometry results with catalog sources
        matched_results = _match_photometry_to_catalog(
            photometry_results=photometry_results,
            catalog_sources=catalog_sources or _load_catalog(catalog_path),
            match_radius_arcsec=config.max_position_offset_arcsec,
        )

        if len(matched_results) == 0:
            return PhotometryValidationResult(
                passed=False,
                message="No sources matched between photometry and catalog",
                details={
                    "n_photometry": len(photometry_results),
                    "n_catalog": len(catalog_sources or []),
                },
            )

        # Validate flux accuracy
        flux_errors = []
        position_offsets = []
        passed_sources = []
        failed_sources = []

        for match in matched_results:
            phot_flux = match["photometry"]["flux"]
            cat_flux = match["catalog"]["flux"]
            phot_ra = match["photometry"]["ra"]
            phot_dec = match["photometry"]["dec"]
            cat_ra = match["catalog"]["ra"]
            cat_dec = match["catalog"]["dec"]

            # Calculate flux error fraction
            if cat_flux > 0:
                flux_error_frac = abs(phot_flux - cat_flux) / cat_flux
            else:
                flux_error_frac = float("inf") if phot_flux > 0 else 0.0

            # Calculate position offset
            coord_phot = SkyCoord(phot_ra, phot_dec, unit="deg")
            coord_cat = SkyCoord(cat_ra, cat_dec, unit="deg")
            position_offset = coord_phot.separation(coord_cat).arcsec

            flux_errors.append(flux_error_frac)
            position_offsets.append(position_offset)

            # Check if source passes
            source_passed = (
                flux_error_frac <= config.max_flux_error_fraction
                and position_offset <= config.max_position_offset_arcsec
            )

            source_result = {
                "source_id": match.get("source_id", "unknown"),
                "flux_error_fraction": flux_error_frac,
                "position_offset_arcsec": position_offset,
                "photometry_flux": phot_flux,
                "catalog_flux": cat_flux,
                "passed": source_passed,
            }

            if source_passed:
                passed_sources.append(source_result)
            else:
                failed_sources.append(source_result)

        # Calculate overall metrics
        n_validated = len(matched_results)
        n_passed = len(passed_sources)
        n_failed = len(failed_sources)

        mean_flux_error = np.mean(flux_errors) if flux_errors else 0.0
        rms_flux_error = np.std(flux_errors) if flux_errors else 0.0
        max_flux_error = np.max(flux_errors) if flux_errors else 0.0

        mean_position_offset = np.mean(position_offsets) if position_offsets else 0.0
        rms_position_offset = np.std(position_offsets) if position_offsets else 0.0

        # Determine overall pass status
        pass_rate = n_passed / n_validated if n_validated > 0 else 0.0
        overall_passed = pass_rate >= config.min_match_fraction

        result = PhotometryValidationResult(
            passed=overall_passed,
            message=f"Photometry validation: {n_passed}/{n_validated} sources passed ({pass_rate:.1%})",
            details={
                "n_validated": n_validated,
                "n_passed": n_passed,
                "n_failed": n_failed,
                "pass_rate": pass_rate,
            },
            metrics={
                "mean_flux_error_fraction": mean_flux_error,
                "rms_flux_error_fraction": rms_flux_error,
                "max_flux_error_fraction": max_flux_error,
                "mean_position_offset_arcsec": mean_position_offset,
                "rms_position_offset_arcsec": rms_position_offset,
            },
            n_sources_validated=n_validated,
            n_sources_passed=n_passed,
            n_sources_failed=n_failed,
            mean_flux_error_fraction=mean_flux_error,
            rms_flux_error_fraction=rms_flux_error,
            max_flux_error_fraction=max_flux_error,
            mean_position_offset_arcsec=mean_position_offset,
            rms_position_offset_arcsec=rms_position_offset,
            source_results=passed_sources + failed_sources,
        )

        # Add warnings for sources that failed
        if n_failed > 0:
            result.add_warning(f"{n_failed} sources failed validation")

        # Add errors if overall validation failed
        if not overall_passed:
            result.add_error(
                f"Pass rate {pass_rate:.1%} below threshold {config.min_match_fraction:.1%}"
            )

        return result

    except Exception as e:
        logger.exception("Photometry validation failed")
        raise ValidationError(f"Photometry validation failed: {e}") from e


def validate_photometry_consistency(
    photometry_results_list: List[List[Dict]],
    source_ids: Optional[List[str]] = None,
    config: Optional[PhotometryConfig] = None,
) -> PhotometryValidationResult:
    """Validate photometry consistency across multiple images.

    Checks that photometry measurements for the same sources are consistent
    across different images.

    Args:
        photometry_results_list: List of photometry result lists (one per image)
        source_ids: Optional list of source IDs to validate
        config: Photometry validation configuration

    Returns:
        PhotometryValidationResult with consistency metrics
    """
    if config is None:
        config = get_default_config().photometry

    # Group photometry by source
    source_fluxes = {}
    for results in photometry_results_list:
        for result in results:
            source_id = result.get("source_id", f"{result['ra']}_{result['dec']}")
            if source_id not in source_fluxes:
                source_fluxes[source_id] = []
            source_fluxes[source_id].append(result["flux"])

    # Calculate consistency metrics
    consistency_rms = []
    for source_id, fluxes in source_fluxes.items():
        if len(fluxes) > 1:
            flux_rms = np.std(fluxes) / np.mean(fluxes) if np.mean(fluxes) > 0 else 0.0
            consistency_rms.append(flux_rms)

    mean_consistency_rms = np.mean(consistency_rms) if consistency_rms else 0.0

    # Determine pass status
    passed = mean_consistency_rms <= config.max_flux_error_fraction

    return PhotometryValidationResult(
        passed=passed,
        message=f"Photometry consistency: RMS={mean_consistency_rms:.3f}",
        details={
            "n_sources": len(source_fluxes),
            "mean_consistency_rms": mean_consistency_rms,
        },
        metrics={
            "flux_consistency_rms": mean_consistency_rms,
        },
        flux_consistency_rms=mean_consistency_rms,
    )


def _match_photometry_to_catalog(
    photometry_results: List[Dict],
    catalog_sources: List[Dict],
    match_radius_arcsec: float,
) -> List[Dict]:
    """Match photometry results to catalog sources.

    Args:
        photometry_results: List of photometry results
        catalog_sources: List of catalog sources
        match_radius_arcsec: Maximum separation for matching

    Returns:
        List of matched results with 'photometry' and 'catalog' keys
    """
    matched = []

    for phot_result in photometry_results:
        phot_ra = phot_result["ra"]
        phot_dec = phot_result["dec"]
        phot_coord = SkyCoord(phot_ra, phot_dec, unit="deg")

        best_match = None
        best_separation = float("inf")

        for cat_source in catalog_sources:
            cat_ra = cat_source["ra"]
            cat_dec = cat_source["dec"]
            cat_coord = SkyCoord(cat_ra, cat_dec, unit="deg")

            separation = phot_coord.separation(cat_coord).arcsec
            if separation < match_radius_arcsec and separation < best_separation:
                best_match = cat_source
                best_separation = separation

        if best_match:
            matched.append(
                {
                    "photometry": phot_result,
                    "catalog": best_match,
                    "separation_arcsec": best_separation,
                    "source_id": best_match.get(
                        "source_id", f"{best_match['ra']}_{best_match['dec']}"
                    ),
                }
            )

    return matched


def _load_catalog(catalog_path: str) -> List[Dict]:
    """Load catalog from file.

    Args:
        catalog_path: Path to catalog file

    Returns:
        List of catalog sources
    """
    # This would load from actual catalog format
    # For now, return empty list
    logger.warning(f"Catalog loading not yet implemented for {catalog_path}")
    return []
