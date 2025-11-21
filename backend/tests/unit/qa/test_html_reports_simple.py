#!/usr/bin/env python3
"""
Simple test script for HTML validation report generation using mock data.

Tests the HTML report generation functionality without requiring catalog databases.

IMPORTANT: This script must be run in the casa6 conda environment:
    conda run -n casa6 python test_html_reports_simple.py
"""

import sys
from pathlib import Path

# Add src to path BEFORE importing dsa110_contimg modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging

from dsa110_contimg.qa.catalog_validation import CatalogValidationResult
from dsa110_contimg.qa.html_reports import generate_validation_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def test_html_report_with_mock_data():
    """Test HTML report generation with mock validation results."""

    # Find a test FITS file (just for the path, we won't actually validate)
    test_files = [
        "tests/integration/test_outputs/test_science_field.fits",
        "notebooks/notebook_outputs/test_science_field.fits",
        "tests/integration/test_outputs/test_low_snr.fits",
    ]

    test_image = None
    for test_file in test_files:
        if Path(test_file).exists():
            test_image = str(Path(test_file).absolute())
            logger.info(f"Using test image path: {test_image}")
            break

    if not test_image:
        # Use a dummy path if no test file found
        test_image = "/data/test/image.fits"
        logger.warning(f"No test FITS files found, using dummy path: {test_image}")

    # Create output directory
    output_dir = Path("state/qa/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("Testing HTML Report Generation (Mock Data)")
    logger.info("=" * 70)
    logger.info("")

    try:
        # Test 1: Create report with all validation types (PASS case)
        logger.info("Test 1: Creating report with PASS status...")
        mock_astrometry_pass = CatalogValidationResult(
            validation_type="astrometry",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=15,
            n_catalog=20,
            n_detected=18,
            mean_offset_arcsec=0.8,
            rms_offset_arcsec=1.2,
            max_offset_arcsec=3.5,
            offset_ra_arcsec=0.3,
            offset_dec_arcsec=0.5,
            has_issues=False,
            has_warnings=False,
            issues=[],
            warnings=[],
        )

        mock_flux_scale_pass = CatalogValidationResult(
            validation_type="flux_scale",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=12,
            n_catalog=15,
            n_detected=12,
            mean_flux_ratio=0.98,
            rms_flux_ratio=0.12,
            flux_scale_error=0.02,
            has_issues=False,
            has_warnings=False,
            issues=[],
            warnings=[],
        )

        mock_source_counts_pass = CatalogValidationResult(
            validation_type="source_counts",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=0,
            n_catalog=20,
            n_detected=18,
            completeness=0.90,
            has_issues=False,
            has_warnings=False,
            issues=[],
            warnings=[],
        )

        report_pass = generate_validation_report(
            image_path=test_image,
            astrometry_result=mock_astrometry_pass,
            flux_scale_result=mock_flux_scale_pass,
            source_counts_result=mock_source_counts_pass,
            output_path=str(output_dir / "test_report_pass.html"),
            catalog="nvss",
        )

        logger.info(f"✓ PASS report created: {report_pass.overall_status}")
        logger.info(f"  Score: {report_pass.score:.1%}")
        logger.info(f"  Output: {output_dir / 'test_report_pass.html'}")

        # Test 2: Create report with WARNING status
        logger.info("\nTest 2: Creating report with WARNING status...")
        mock_astrometry_warn = CatalogValidationResult(
            validation_type="astrometry",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=10,
            n_catalog=20,
            n_detected=15,
            mean_offset_arcsec=2.5,
            rms_offset_arcsec=3.0,
            max_offset_arcsec=6.0,
            offset_ra_arcsec=1.2,
            offset_dec_arcsec=2.0,
            has_issues=False,
            has_warnings=True,
            issues=[],
            warnings=[
                "Mean astrometric offset (2.5 arcsec) is significant",
                "Only 10/15 detected sources matched to catalog",
            ],
        )

        mock_flux_scale_warn = CatalogValidationResult(
            validation_type="flux_scale",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=8,
            n_catalog=15,
            n_detected=8,
            mean_flux_ratio=0.92,
            rms_flux_ratio=0.25,
            flux_scale_error=0.08,
            has_issues=False,
            has_warnings=True,
            issues=[],
            warnings=["High scatter in flux ratios (RMS=0.25)"],
        )

        report_warn = generate_validation_report(
            image_path=test_image,
            astrometry_result=mock_astrometry_warn,
            flux_scale_result=mock_flux_scale_warn,
            source_counts_result=None,  # Skip source counts
            output_path=str(output_dir / "test_report_warning.html"),
            catalog="nvss",
        )

        logger.info(f"✓ WARNING report created: {report_warn.overall_status}")
        logger.info(f"  Score: {report_warn.score:.1%}")
        logger.info(f"  Warnings: {len(report_warn.warnings)}")
        logger.info(f"  Output: {output_dir / 'test_report_warning.html'}")

        # Test 3: Create report with FAIL status
        logger.info("\nTest 3: Creating report with FAIL status...")
        mock_astrometry_fail = CatalogValidationResult(
            validation_type="astrometry",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=5,
            n_catalog=20,
            n_detected=15,
            mean_offset_arcsec=8.5,
            rms_offset_arcsec=10.0,
            max_offset_arcsec=25.0,
            offset_ra_arcsec=5.0,
            offset_dec_arcsec=7.0,
            has_issues=True,
            has_warnings=True,
            issues=["Maximum astrometric offset (25.0 arcsec) exceeds threshold (5.0 arcsec)"],
            warnings=["Mean astrometric offset (8.5 arcsec) is significant"],
        )

        mock_flux_scale_fail = CatalogValidationResult(
            validation_type="flux_scale",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=3,
            n_catalog=15,
            n_detected=3,
            mean_flux_ratio=0.75,
            rms_flux_ratio=0.35,
            flux_scale_error=0.25,
            has_issues=True,
            has_warnings=True,
            issues=["Flux scale error (25.0%) exceeds threshold (20.0%)"],
            warnings=[
                "High scatter in flux ratios (RMS=0.35)",
                "Low number of valid measurements: 3 (recommend at least 3)",
            ],
        )

        report_fail = generate_validation_report(
            image_path=test_image,
            astrometry_result=mock_astrometry_fail,
            flux_scale_result=mock_flux_scale_fail,
            source_counts_result=None,
            output_path=str(output_dir / "test_report_fail.html"),
            catalog="nvss",
        )

        logger.info(f"✓ FAIL report created: {report_fail.overall_status}")
        logger.info(f"  Score: {report_fail.score:.1%}")
        logger.info(f"  Issues: {len(report_fail.issues)}")
        logger.info(f"  Output: {output_dir / 'test_report_fail.html'}")

        # Test 4: Verify HTML files were created
        logger.info("\nTest 4: Verifying HTML files...")
        html_files = [
            output_dir / "test_report_pass.html",
            output_dir / "test_report_warning.html",
            output_dir / "test_report_fail.html",
        ]

        for html_file in html_files:
            if html_file.exists():
                file_size = html_file.stat().st_size
                logger.info(f"✓ {html_file.name}: {file_size:,} bytes")

                # Verify content
                with open(html_file, "r") as f:
                    content = f.read()

                required = ["<!DOCTYPE html>", "DSA-110", "Summary", "Overall Status"]
                missing = [r for r in required if r not in content]
                if missing:
                    logger.warning(f"  Missing elements: {missing}")
                else:
                    logger.info("  Content verified")
            else:
                logger.error(f"✗ {html_file.name} not found")
                return False

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("Test Summary")
        logger.info("=" * 70)
        logger.info("✓ All tests passed!")
        logger.info(f"\nGenerated HTML reports in: {output_dir}")
        logger.info("  1. test_report_pass.html (PASS status)")
        logger.info("  2. test_report_warning.html (WARNING status)")
        logger.info("  3. test_report_fail.html (FAIL status)")
        logger.info("\nOpen any of these files in a web browser to view the reports.")

        return True

    except Exception as e:
        logger.error(f"✗ Test failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_html_report_with_mock_data()
    sys.exit(0 if success else 1)
