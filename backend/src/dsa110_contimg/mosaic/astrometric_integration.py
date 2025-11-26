"""Integration helper for astrometric refinement in mosaic workflows.

This module provides a simple interface to apply astrometric calibration
to mosaics as an optional refinement step.
"""

import logging
from pathlib import Path
from typing import Optional

from dsa110_contimg.catalog.astrometric_calibration import (
    apply_wcs_correction,
    calculate_astrometric_offsets,
    mark_solution_applied,
    store_astrometric_solution,
)
from dsa110_contimg.catalog.query import query_sources
from dsa110_contimg.qa.catalog_validation import extract_sources_from_image

logger = logging.getLogger(__name__)


def apply_astrometric_refinement(
    mosaic_fits_path: str,
    mosaic_id: Optional[int] = None,
    reference_catalog: str = "FIRST",
    match_radius_arcsec: float = 5.0,
    min_matches: int = 10,
    flux_weight: bool = True,
    apply_correction: bool = True,
    db_path: str = "/data/dsa110-contimg/state/db/products.sqlite3",
) -> Optional[dict]:
    """Apply astrometric refinement to a mosaic using reference catalog.

    This function:
    1. Extracts sources from the mosaic
    2. Queries high-precision reference catalog (FIRST)
    3. Calculates systematic RA/Dec offsets
    4. Optionally applies WCS correction to FITS header
    5. Stores solution in database

    Args:
        mosaic_fits_path: Path to mosaic FITS file
        mosaic_id: Mosaic product ID for tracking
        reference_catalog: Reference catalog name ('FIRST')
        match_radius_arcsec: Matching radius [arcsec]
        min_matches: Minimum matches required
        flux_weight: Weight offsets by source flux
        apply_correction: Apply WCS correction to FITS
        db_path: Path to products database

    Returns:
        Dictionary with astrometric solution, or None if failed

    Example:
        >>> result = apply_astrometric_refinement(
        ...     mosaic_fits_path="/path/to/mosaic.fits",
        ...     mosaic_id=123,
        ...     apply_correction=True
        ... )
        >>> if result:
        ...     rms = result['rms_residual_mas']
        ...     print(f"Astrometric accuracy: {rms} mas")
    """
    logger.info(f"Applying astrometric refinement to {mosaic_fits_path}")

    mosaic_path = Path(mosaic_fits_path)
    if not mosaic_path.exists():
        logger.error(f"Mosaic file not found: {mosaic_path}")
        return None

    # Extract sources from mosaic
    logger.info("Extracting sources from mosaic...")
    try:
        observed_sources = extract_sources_from_image(str(mosaic_path), min_snr=5.0)
    except Exception as e:
        logger.error(f"Failed to extract sources: {e}")
        return None

    if observed_sources is None or len(observed_sources) == 0:
        logger.warning("No sources extracted from mosaic")
        return None

    logger.info(f"Extracted {len(observed_sources)} sources from mosaic")

    # Get field center and radius
    ra_center = observed_sources["ra_deg"].median()
    dec_center = observed_sources["dec_deg"].median()

    ra_range = observed_sources["ra_deg"].max() - observed_sources["ra_deg"].min()
    dec_range = observed_sources["dec_deg"].max() - observed_sources["dec_deg"].min()
    field_radius_deg = max(ra_range, dec_range) / 2.0 + 0.1

    # Query reference catalog
    logger.info(
        f"Querying {reference_catalog} "
        f"(RA={ra_center:.3f}, Dec={dec_center:.3f}, "
        f"radius={field_radius_deg:.2f} deg)..."
    )

    try:
        reference_sources = query_sources(
            ra=ra_center,
            dec=dec_center,
            radius_arcmin=field_radius_deg * 60.0,
            catalog=reference_catalog.lower(),
        )
    except Exception as e:
        logger.error(f"Failed to query reference catalog: {e}")
        return None

    if reference_sources is None or len(reference_sources) == 0:
        logger.warning(f"No reference sources found in {reference_catalog}")
        return None

    logger.info(f"Found {len(reference_sources)} reference sources")

    # Calculate astrometric offsets
    solution = calculate_astrometric_offsets(
        observed_sources=observed_sources,
        reference_sources=reference_sources,
        match_radius_arcsec=match_radius_arcsec,
        min_matches=min_matches,
        flux_weight=flux_weight,
    )

    if solution is None:
        logger.warning("Failed to compute astrometric solution")
        return None

    logger.info(
        f"Astrometric solution: RA offset = {solution['ra_offset_mas']:.1f} mas, "
        f"Dec offset = {solution['dec_offset_mas']:.1f} mas, "
        f"RMS = {solution['rms_residual_mas']:.1f} mas "
        f"({solution['n_matches']} matches)"
    )

    # Store solution
    if mosaic_id is not None:
        solution_id = store_astrometric_solution(
            solution=solution,
            mosaic_id=mosaic_id,
            reference_catalog=reference_catalog,
            db_path=db_path,
        )
        solution["solution_id"] = solution_id

    # Apply correction to FITS if requested
    if apply_correction:
        logger.info("Applying WCS correction to FITS header...")
        success = apply_wcs_correction(
            ra_offset_mas=solution["ra_offset_mas"],
            dec_offset_mas=solution["dec_offset_mas"],
            fits_path=str(mosaic_path),
        )

        if success:
            logger.info("WCS correction applied successfully")
            if (
                mosaic_id is not None
                and "solution_id" in solution
                and solution["solution_id"] is not None
            ):
                mark_solution_applied(solution["solution_id"], db_path)
        else:
            logger.warning("Failed to apply WCS correction")

    return solution


def should_apply_astrometric_refinement(config) -> bool:
    """Check if astrometric refinement should be applied.

    Args:
        config: Pipeline configuration

    Returns:
        True if refinement should be applied
    """
    # Check if feature is enabled
    if not hasattr(config, "astrometric_calibration"):
        return False

    return config.astrometric_calibration.enabled
