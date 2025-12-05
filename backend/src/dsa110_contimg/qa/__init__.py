"""Quality Assurance and validation utilities for DSA-110 imaging pipeline.

This module provides catalog-based validation for verifying flux scale accuracy,
astrometric precision, and source completeness in pipeline-generated images.

Main Functions:
    validate_flux_scale: Validate flux scale against reference catalog
    run_full_validation: Run all validation types (astrometry, flux, counts)
    extract_sources_from_image: Extract source positions from FITS image

Example:
    >>> from dsa110_contimg.qa import validate_flux_scale
    >>> result = validate_flux_scale("image.fits", catalog="nvss", min_snr=5.0)
    >>> print(f"Flux scale error: {result.flux_scale_error * 100:.1f}%")
"""

from dsa110_contimg.qa.catalog_validation import (
    AstrometryResult,
    FluxScaleResult,
    SourceCountsResult,
    extract_sources_from_image,
    run_full_validation,
    validate_flux_scale,
)

__all__ = [
    "AstrometryResult",
    "FluxScaleResult",
    "SourceCountsResult",
    "extract_sources_from_image",
    "run_full_validation",
    "validate_flux_scale",
]
