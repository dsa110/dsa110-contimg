#!/usr/bin/env python3
"""
Test script for enhanced validation visualization with plots.

Tests the plotting functions and HTML report generation with embedded plots.
"""

import sys
import os
from pathlib import Path

# Add src to path BEFORE importing dsa110_contimg modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging
import numpy as np
from dsa110_contimg.qa.catalog_validation import CatalogValidationResult
from dsa110_contimg.qa.html_reports import generate_validation_report


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def test_validation_plots():
    """Test validation plots with mock data."""

    test_image = "/data/test/image.fits"

    # Create output directory
    output_dir = Path("state/qa/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("Testing Enhanced Validation Visualization")
    logger.info("=" * 70)
    logger.info("")

    try:
        # Create mock astrometry result with matched pairs
        logger.info("Creating mock astrometry result...")
        n_sources = 20
        matched_pairs = []
        for i in range(n_sources):
            # Simulate sources with small random offsets
            catalog_ra = 180.0 + np.random.normal(0, 0.01)
            catalog_dec = 45.0 + np.random.normal(0, 0.01)
            offset_arcsec = np.random.normal(1.5, 0.8)  # Mean 1.5", RMS 0.8"
            offset_ra_arcsec = np.random.normal(0.5, 0.5)
            offset_dec_arcsec = np.random.normal(1.0, 0.5)
            detected_ra = catalog_ra + offset_ra_arcsec / (
                3600.0 * np.cos(np.radians(catalog_dec))
            )
            detected_dec = catalog_dec + offset_dec_arcsec / 3600.0
            matched_pairs.append(
                (detected_ra, detected_dec, catalog_ra, catalog_dec, abs(offset_arcsec))
            )

        astrometry_result = CatalogValidationResult(
            validation_type="astrometry",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=n_sources,
            n_catalog=25,
            n_detected=22,
            mean_offset_arcsec=1.5,
            rms_offset_arcsec=2.0,
            max_offset_arcsec=5.0,
            offset_ra_arcsec=0.5,
            offset_dec_arcsec=1.2,
            has_issues=False,
            has_warnings=True,
            issues=[],
            warnings=["Some sources have offsets > 3 arcsec"],
            matched_pairs=matched_pairs,
        )

        logger.info("✓ Astrometry result created")

        # Create mock flux scale result with matched fluxes
        logger.info("Creating mock flux scale result...")
        matched_fluxes = []
        for i in range(15):
            catalog_flux = np.random.uniform(0.01, 1.0)  # 10 mJy to 1 Jy
            flux_ratio = np.random.normal(0.95, 0.15)  # Mean 0.95, RMS 0.15
            detected_flux = catalog_flux * flux_ratio
            matched_fluxes.append((detected_flux, catalog_flux, flux_ratio))

        flux_scale_result = CatalogValidationResult(
            validation_type="flux_scale",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=15,
            n_catalog=18,
            n_detected=15,
            mean_flux_ratio=0.95,
            rms_flux_ratio=0.15,
            flux_scale_error=0.05,
            has_issues=False,
            has_warnings=False,
            issues=[],
            warnings=[],
            matched_fluxes=matched_fluxes,
        )

        logger.info("✓ Flux scale result created")

        # Create mock completeness result
        logger.info("Creating mock completeness result...")
        n_bins = 10
        flux_bins = np.logspace(np.log10(0.001), np.log10(10.0), n_bins + 1)
        bin_centers = [(flux_bins[i] + flux_bins[i + 1]) / 2 for i in range(n_bins)]
        catalog_counts = [50, 40, 30, 25, 20, 15, 10, 8, 5, 3]
        detected_counts = []
        completeness_per_bin = []

        for i, (catalog_count, bin_center) in enumerate(
            zip(catalog_counts, bin_centers)
        ):
            completeness = max(0.0, min(1.0, 0.98 - (i * 0.08)))
            detected = int(catalog_count * completeness)
            detected_counts.append(detected)
            completeness_per_bin.append(completeness)

        completeness_limit_jy = bin_centers[0]  # First bin meets threshold

        source_counts_result = CatalogValidationResult(
            validation_type="source_counts",
            image_path=test_image,
            catalog_used="nvss",
            n_matched=sum(detected_counts),
            n_catalog=sum(catalog_counts),
            n_detected=sum(detected_counts) + 5,
            completeness=sum(detected_counts) / sum(catalog_counts),
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

        logger.info("✓ Completeness result created")

        # Generate HTML report with all plots
        logger.info("\nGenerating HTML report with plots...")
        report = generate_validation_report(
            image_path=test_image,
            astrometry_result=astrometry_result,
            flux_scale_result=flux_scale_result,
            source_counts_result=source_counts_result,
            output_path=str(output_dir / "test_validation_plots_report.html"),
            catalog="nvss",
        )

        logger.info(
            f"✓ HTML report created: {output_dir / 'test_validation_plots_report.html'}"
        )
        logger.info(f"  Report status: {report.overall_status}")
        logger.info(f"  Report score: {report.score:.1%}")

        # Verify HTML file contains plots
        html_file = output_dir / "test_validation_plots_report.html"
        if html_file.exists():
            file_size = html_file.stat().st_size
            logger.info(f"  File size: {file_size:,} bytes")

            with open(html_file, "r") as f:
                html_content = f.read()

            # Check for plot images (base64 encoded)
            plot_indicators = [
                "data:image/png;base64,",
                "Astrometry Visualization",
                "Flux Scale Visualization",
                "Completeness Visualization",
            ]

            missing = [ind for ind in plot_indicators if ind not in html_content]
            if missing:
                logger.warning(f"  Missing plot indicators: {missing}")
            else:
                logger.info("  ✓ All plot indicators present in HTML")

            # Count base64 images
            plot_count = html_content.count("data:image/png;base64,")
            logger.info(f"  Found {plot_count} embedded plots")

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("Test Summary")
        logger.info("=" * 70)
        logger.info("✓ Enhanced validation visualization test completed!")
        logger.info(f"\nGenerated HTML report: {html_file}")
        logger.info("Open the report in a web browser to view plots.")

        return True

    except Exception as e:
        logger.error(f"✗ Test failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_validation_plots()
    sys.exit(0 if success else 1)
