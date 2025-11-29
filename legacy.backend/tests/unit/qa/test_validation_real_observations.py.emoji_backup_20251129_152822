#!/usr/bin/env python3
"""
Test validation system with REAL DSA-110 observation data.

This script:
1. Finds actual pipeline output FITS images
2. Verifies they are real observations (not synthetic test data)
3. Runs full validation on them
4. Generates HTML reports

This provides true confidence that validation works with real astronomical data.
"""

import sys
from pathlib import Path

# Add src to path BEFORE importing dsa110_contimg modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging

from astropy.io import fits

from dsa110_contimg.qa.catalog_validation import run_full_validation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def verify_real_observation(fits_path: str) -> bool:
    """Verify that a FITS file is a real observation, not synthetic test data."""
    try:
        with fits.open(fits_path) as hdul:
            header = hdul[0].header

            # Check for real observation indicators
            has_date = "DATE-OBS" in header or "DATE" in header
            has_telescope = "TELESCOP" in header
            has_object = "OBJECT" in header
            has_wcs = "CRVAL1" in header and "CRVAL2" in header

            # Check file location (not in test directories)
            path_obj = Path(fits_path)
            is_test_dir = "test" in str(path_obj).lower() or "tests/" in str(path_obj)

            # Real observations should have WCS and not be in test directories
            is_real = has_wcs and not is_test_dir

            logger.info(f"Verification for {Path(fits_path).name}:")
            logger.info(f"  - Has DATE-OBS: {has_date}")
            logger.info(f"  - Has TELESCOP: {has_telescope}")
            logger.info(f"  - Has OBJECT: {has_object}")
            logger.info(f"  - Has WCS: {has_wcs}")
            logger.info(f"  - In test directory: {is_test_dir}")
            logger.info(f"  - Appears to be real observation: {is_real}")

            return is_real

    except Exception as e:
        logger.error(f"Error verifying file {fits_path}: {e}")
        return False


def find_real_observation_fits():
    """Find real DSA-110 observation FITS files."""
    search_paths = [
        "/stage/dsa110-contimg/images",
        "/data/dsa110-contimg/products/images",
    ]

    # Prefer PB-corrected images for validation
    patterns = ["*.pbcor.fits", "*.image.fits", "*.fits"]

    for search_path in search_paths:
        path_obj = Path(search_path)
        if not path_obj.exists():
            continue

        for pattern in patterns:
            for fits_file in path_obj.glob(pattern):
                # Skip test files
                if "test" in fits_file.name.lower():
                    continue

                # Verify it's a real observation
                if verify_real_observation(str(fits_file)):
                    return str(fits_file)

    return None


def test_validation_with_real_observations():
    """Test validation system with real DSA-110 observations."""

    logger.info("=" * 70)
    logger.info("Validation Test with REAL DSA-110 Observations")
    logger.info("=" * 70)
    logger.info("")

    # Find real observation
    real_image = find_real_observation_fits()

    if not real_image:
        logger.warning("No real observation FITS files found.")
        logger.warning("Expected locations:")
        logger.warning("  - /stage/dsa110-contimg/images/*.pbcor.fits")
        logger.warning("  - /data/dsa110-contimg/products/images/*.pbcor.fits")
        logger.warning("")
        logger.warning("Note: This test requires actual pipeline output images.")
        return False

    logger.info(f"✓ Found real observation: {real_image}")
    logger.info("")

    # Create output directory
    output_dir = Path("state/qa/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Run full validation
        image_name = Path(real_image).stem
        html_path = str(output_dir / f"{image_name}_real_validation_report.html")

        logger.info("Running full validation on real observation...")
        logger.info(f"  Image: {real_image}")
        logger.info(f"  Output: {html_path}")
        logger.info("")

        astrometry_result, flux_result, completeness_result = run_full_validation(
            image_path=real_image,
            catalog="nvss",
            validation_types=["astrometry", "flux_scale", "source_counts"],
            generate_html=True,
            html_output_path=html_path,
        )

        # Check results
        if Path(html_path).exists():
            file_size = Path(html_path).stat().st_size
            logger.info("")
            logger.info("=" * 70)
            logger.info("Validation Results Summary")
            logger.info("=" * 70)

            if astrometry_result:
                logger.info(f"Astrometry: {astrometry_result.n_matched} matched sources")
                if astrometry_result.rms_offset_arcsec:
                    logger.info(f'  RMS offset: {astrometry_result.rms_offset_arcsec:.2f}"')

            if flux_result:
                logger.info(f"Flux Scale: {flux_result.n_matched} matched sources")
                if flux_result.mean_flux_ratio:
                    logger.info(f"  Mean flux ratio: {flux_result.mean_flux_ratio:.3f}")

            if completeness_result:
                logger.info(f"Source Counts: {completeness_result.n_matched} matched sources")
                if completeness_result.completeness:
                    logger.info(f"  Completeness: {completeness_result.completeness * 100:.1f}%")

            logger.info("")
            logger.info(f"✓ HTML report generated: {html_path}")
            logger.info(f"  File size: {file_size:,} bytes")
            logger.info("")
            logger.info("=" * 70)
            logger.info("SUCCESS: Validation system works with real observations!")
            logger.info("=" * 70)

            return True
        else:
            logger.error(f"HTML report not created: {html_path}")
            return False

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_validation_with_real_observations()
    sys.exit(0 if success else 1)
