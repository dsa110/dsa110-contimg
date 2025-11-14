#!/usr/bin/env python3
"""
Test script for HTML validation report generation.

Tests the HTML report generation functionality with sample images.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging
from dsa110_contimg.qa.catalog_validation import run_full_validation
from dsa110_contimg.qa.html_reports import (
    generate_validation_report,
    ValidationReport,
    CatalogValidationResult,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def test_html_report_generation():
    """Test HTML report generation with a sample image."""

    # Find a test FITS file
    test_files = [
        "tests/integration/test_outputs/test_science_field.fits",
        "notebooks/notebook_outputs/test_science_field.fits",
        "tests/integration/test_outputs/test_low_snr.fits",
    ]

    test_image = None
    for test_file in test_files:
        if Path(test_file).exists():
            test_image = str(Path(test_file).absolute())
            logger.info(f"Found test image: {test_image}")
            break

    if not test_image:
        logger.error("No test FITS files found. Cannot run test.")
        logger.info("Test files checked:")
        for tf in test_files:
            logger.info(f"  - {tf}")
        return False

    # Create output directory
    output_dir = Path("state/qa/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{Path(test_image).stem}_validation_report.html"

    logger.info("=" * 70)
    logger.info("Testing HTML Report Generation")
    logger.info("=" * 70)
    logger.info(f"Test image: {test_image}")
    logger.info(f"Output path: {output_path}")
    logger.info("")

    try:
        # Test 1: Run full validation with HTML generation
        logger.info("Test 1: Running full validation with HTML generation...")
        astrometry_result, flux_scale_result, source_counts_result = (
            run_full_validation(
                image_path=test_image,
                catalog="nvss",
                validation_types=["astrometry", "flux_scale", "source_counts"],
                generate_html=True,
                html_output_path=str(output_path),
            )
        )

        logger.info("✓ Validation completed")
        logger.info(f"  - Astrometry: {'✓' if astrometry_result else '✗'}")
        logger.info(f"  - Flux Scale: {'✓' if flux_scale_result else '✗'}")
        logger.info(f"  - Source Counts: {'✓' if source_counts_result else '✗'}")

        # Check if HTML file was created
        if output_path.exists():
            file_size = output_path.stat().st_size
            logger.info(f"✓ HTML report created: {output_path}")
            logger.info(f"  File size: {file_size:,} bytes")
        else:
            logger.error(f"✗ HTML report not found at {output_path}")
            return False

        # Test 2: Create report from existing results
        logger.info("\nTest 2: Creating report from existing results...")
        report = generate_validation_report(
            image_path=test_image,
            astrometry_result=astrometry_result,
            flux_scale_result=flux_scale_result,
            source_counts_result=source_counts_result,
            output_path=str(output_dir / f"{Path(test_image).stem}_report2.html"),
            catalog="nvss",
        )

        logger.info(f"✓ Report created with status: {report.overall_status}")
        logger.info(f"  Score: {report.score:.1%}")
        logger.info(f"  Issues: {len(report.issues)}")
        logger.info(f"  Warnings: {len(report.warnings)}")

        # Test 3: Test with mock data (no actual validation)
        logger.info("\nTest 3: Testing with mock validation results...")
        mock_astrometry = CatalogValidationResult(
            validation_type="astrometry",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=10,
            n_catalog=15,
            n_detected=12,
            mean_offset_arcsec=1.5,
            rms_offset_arcsec=2.0,
            max_offset_arcsec=5.0,
            offset_ra_arcsec=0.5,
            offset_dec_arcsec=1.2,
            has_issues=False,
            has_warnings=True,
            warnings=["Some sources have offsets > 3 arcsec"],
        )

        mock_flux_scale = CatalogValidationResult(
            validation_type="flux_scale",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=8,
            n_catalog=12,
            n_detected=8,
            mean_flux_ratio=0.95,
            rms_flux_ratio=0.15,
            flux_scale_error=0.05,
            has_issues=False,
            has_warnings=False,
        )

        mock_source_counts = CatalogValidationResult(
            validation_type="source_counts",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=0,
            n_catalog=15,
            n_detected=12,
            completeness=0.8,
            has_issues=False,
            has_warnings=False,
        )

        mock_report = generate_validation_report(
            image_path=test_image,
            astrometry_result=mock_astrometry,
            flux_scale_result=mock_flux_scale,
            source_counts_result=mock_source_counts,
            output_path=str(output_dir / f"{Path(test_image).stem}_mock_report.html"),
            catalog="nvss",
        )

        logger.info(f"✓ Mock report created with status: {mock_report.overall_status}")
        logger.info(f"  Score: {mock_report.score:.1%}")

        # Verify HTML content
        logger.info("\nTest 4: Verifying HTML content...")
        with open(output_path, "r") as f:
            html_content = f.read()

        required_elements = [
            "<!DOCTYPE html>",
            "DSA-110 Continuum Imaging Validation Report",
            "Summary",
            "Overall Status",
            "Validation Score",
        ]

        missing = []
        for element in required_elements:
            if element not in html_content:
                missing.append(element)

        if missing:
            logger.error(f"✗ Missing required HTML elements: {missing}")
            return False

        logger.info("✓ HTML content verified")
        logger.info(f"  HTML length: {len(html_content):,} characters")

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("Test Summary")
        logger.info("=" * 70)
        logger.info(f"✓ All tests passed!")
        logger.info(f"\nGenerated HTML reports:")
        logger.info(f"  1. {output_path}")
        logger.info(f"  2. {output_dir / f'{Path(test_image).stem}_report2.html'}")
        logger.info(f"  3. {output_dir / f'{Path(test_image).stem}_mock_report.html'}")
        logger.info(f"\nOpen any of these files in a web browser to view the reports.")

        return True

    except Exception as e:
        logger.error(f"✗ Test failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_html_report_generation()
    sys.exit(0 if success else 1)
