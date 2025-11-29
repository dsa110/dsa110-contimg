#!/usr/bin/env python3
"""
Test script for enhanced source counts completeness analysis using mock data.

Tests the enhanced completeness analysis logic without requiring catalog database access.
"""

import sys
from pathlib import Path

# Add src to path BEFORE importing dsa110_contimg modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging

import numpy as np

from dsa110_contimg.qa.catalog_validation import CatalogValidationResult
from dsa110_contimg.qa.html_reports import generate_validation_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def test_enhanced_completeness_mock():
    """Test enhanced completeness analysis with mock data."""

    test_image = "/data/test/image.fits"

    # Create output directory
    output_dir = Path("state/qa/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("Testing Enhanced Completeness Analysis (Mock Data)")
    logger.info("=" * 70)
    logger.info("")

    try:
        # Create mock completeness analysis result
        # Simulate completeness analysis with flux bins
        n_bins = 10
        flux_bins = np.logspace(np.log10(0.001), np.log10(10.0), n_bins + 1)
        bin_centers = [(flux_bins[i] + flux_bins[i + 1]) / 2 for i in range(n_bins)]

        # Simulate catalog and detected counts per bin
        # Higher completeness at brighter fluxes
        catalog_counts = [50, 40, 30, 25, 20, 15, 10, 8, 5, 3]
        detected_counts = []
        completeness_per_bin = []

        for i, (catalog_count, bin_center) in enumerate(zip(catalog_counts, bin_centers)):
            # Completeness decreases with fainter fluxes
            completeness = max(0.0, min(1.0, 0.98 - (i * 0.08)))
            detected = int(catalog_count * completeness)
            detected_counts.append(detected)
            completeness_per_bin.append(completeness)

        # Calculate completeness limit (95% threshold)
        completeness_limit_jy = None
        for i, completeness in enumerate(completeness_per_bin):
            if completeness >= 0.95:
                completeness_limit_jy = bin_centers[i]

        # Overall completeness
        total_catalog = sum(catalog_counts)
        total_detected = sum(detected_counts)
        overall_completeness = total_detected / total_catalog if total_catalog > 0 else 0.0

        logger.info("Creating mock completeness analysis result...")
        result = CatalogValidationResult(
            validation_type="source_counts",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=total_detected,
            n_catalog=total_catalog,
            n_detected=total_detected + 5,  # Some detected sources not in catalog
            completeness=overall_completeness,
            completeness_limit_jy=completeness_limit_jy,
            completeness_bins_jy=bin_centers,
            completeness_per_bin=completeness_per_bin,
            catalog_counts_per_bin=catalog_counts,
            detected_counts_per_bin=detected_counts,
            has_issues=False,
            has_warnings=False,
            issues=[],
            warnings=[],
        )

        logger.info(":check_mark: Mock result created")
        logger.info(f"  Overall completeness: {result.completeness * 100:.1f}%")
        logger.info(
            f"  Completeness limit: {result.completeness_limit_jy * 1000:.2f} mJy"
            if result.completeness_limit_jy
            else "  Completeness limit: N/A"
        )
        logger.info(f"  Catalog sources: {result.n_catalog}")
        logger.info(f"  Detected sources: {result.n_detected}")
        logger.info(f"  Matched sources: {result.n_matched}")

        # Display completeness per bin
        logger.info("\n  Completeness by flux bin:")
        logger.info("  " + "-" * 60)
        logger.info("  Flux (mJy)  |  Catalog  |  Detected  |  Completeness")
        logger.info("  " + "-" * 60)
        for bin_center, catalog_count, detected_count, completeness in zip(
            result.completeness_bins_jy,
            result.catalog_counts_per_bin,
            result.detected_counts_per_bin,
            result.completeness_per_bin,
        ):
            logger.info(
                f"  {bin_center * 1000:8.2f}  |  {catalog_count:7d}  |  {detected_count:9d}  |  {completeness * 100:6.1f}%"
            )

        # Generate HTML report
        logger.info("\nGenerating HTML report with completeness analysis...")
        report = generate_validation_report(
            image_path=test_image,
            astrometry_result=None,
            flux_scale_result=None,
            source_counts_result=result,
            output_path=str(output_dir / "test_completeness_mock_report.html"),
            catalog="nvss",
        )

        logger.info(f":check_mark: HTML report created: {output_dir / 'test_completeness_mock_report.html'}")
        logger.info(f"  Report status: {report.overall_status}")
        logger.info(f"  Report score: {report.score:.1%}")

        # Verify HTML file
        html_file = output_dir / "test_completeness_mock_report.html"
        if html_file.exists():
            file_size = html_file.stat().st_size
            logger.info(f"  File size: {file_size:,} bytes")

            # Check for completeness table in HTML
            with open(html_file, "r") as f:
                html_content = f.read()

            required_elements = [
                "Completeness Limit",
                "Completeness by Flux Density",
                "Flux Density (mJy)",
                "Catalog Sources",
                "Detected Sources",
            ]

            missing = [e for e in required_elements if e not in html_content]
            if missing:
                logger.warning(f"  Missing HTML elements: {missing}")
            else:
                logger.info("  :check_mark: All completeness analysis elements present in HTML")

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("Test Summary")
        logger.info("=" * 70)
        logger.info(":check_mark: Enhanced completeness analysis test completed!")
        logger.info(f"\nGenerated HTML report: {html_file}")
        logger.info("Open the report in a web browser to view completeness analysis.")

        return True

    except Exception as e:
        logger.error(f":ballot_x: Test failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_enhanced_completeness_mock()
    sys.exit(0 if success else 1)
