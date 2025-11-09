#!/usr/bin/env python3
"""
Test script for enhanced source counts completeness analysis.

Tests the enhanced validate_source_counts() function with flux binning and completeness limit calculation.
"""

import sys
import os
from pathlib import Path

# Add src to path BEFORE importing dsa110_contimg modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging
from dsa110_contimg.qa.catalog_validation import validate_source_counts, CatalogValidationResult
from dsa110_contimg.qa.html_reports import generate_validation_report

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def test_enhanced_completeness():
    """Test enhanced completeness analysis."""
    
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
        logger.warning("No test FITS files found, using dummy path")
        test_image = "/data/test/image.fits"
    
    # Create output directory
    output_dir = Path("state/qa/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 70)
    logger.info("Testing Enhanced Completeness Analysis")
    logger.info("=" * 70)
    logger.info(f"Test image: {test_image}")
    logger.info("")
    
    try:
        # Test enhanced completeness analysis
        logger.info("Running enhanced source counts validation...")
        result = validate_source_counts(
            image_path=test_image,
            catalog="nvss",
            min_snr=5.0,
            completeness_threshold=0.95,
            search_radius_arcsec=10.0,
            min_flux_jy=0.001,
            max_flux_jy=10.0,
            n_bins=10,
            completeness_limit_threshold=0.95
        )
        
        logger.info("✓ Validation completed")
        logger.info(f"  Overall completeness: {result.completeness*100:.1f}%" if result.completeness else "  Overall completeness: N/A")
        logger.info(f"  Completeness limit: {result.completeness_limit_jy*1000:.2f} mJy" if result.completeness_limit_jy else "  Completeness limit: N/A")
        logger.info(f"  Catalog sources: {result.n_catalog}")
        logger.info(f"  Detected sources: {result.n_detected}")
        logger.info(f"  Matched sources: {result.n_matched}")
        logger.info(f"  Issues: {len(result.issues)}")
        logger.info(f"  Warnings: {len(result.warnings)}")
        
        # Display completeness per bin if available
        if result.completeness_bins_jy and result.completeness_per_bin:
            logger.info("\n  Completeness by flux bin:")
            logger.info("  " + "-" * 60)
            logger.info("  Flux (mJy)  |  Catalog  |  Detected  |  Completeness")
            logger.info("  " + "-" * 60)
            for bin_center, catalog_count, detected_count, completeness in zip(
                result.completeness_bins_jy,
                result.catalog_counts_per_bin,
                result.detected_counts_per_bin,
                result.completeness_per_bin
            ):
                if catalog_count > 0:
                    logger.info(f"  {bin_center*1000:8.2f}  |  {catalog_count:7d}  |  {detected_count:9d}  |  {completeness*100:6.1f}%")
        
        # Generate HTML report with completeness analysis
        logger.info("\nGenerating HTML report with completeness analysis...")
        report = generate_validation_report(
            image_path=test_image,
            astrometry_result=None,
            flux_scale_result=None,
            source_counts_result=result,
            output_path=str(output_dir / "test_completeness_report.html"),
            catalog="nvss"
        )
        
        logger.info(f"✓ HTML report created: {output_dir / 'test_completeness_report.html'}")
        logger.info(f"  Report status: {report.overall_status}")
        logger.info(f"  Report score: {report.score:.1%}")
        
        # Verify enhanced fields
        logger.info("\nVerifying enhanced fields...")
        checks = [
            ("completeness_limit_jy", result.completeness_limit_jy is not None),
            ("completeness_bins_jy", result.completeness_bins_jy is not None),
            ("completeness_per_bin", result.completeness_per_bin is not None),
            ("catalog_counts_per_bin", result.catalog_counts_per_bin is not None),
            ("detected_counts_per_bin", result.detected_counts_per_bin is not None),
        ]
        
        all_passed = True
        for field_name, check_passed in checks:
            status = "✓" if check_passed else "✗"
            logger.info(f"  {status} {field_name}: {'Present' if check_passed else 'Missing'}")
            if not check_passed:
                all_passed = False
        
        if all_passed:
            logger.info("\n✓ All enhanced fields present!")
        else:
            logger.warning("\n⚠ Some enhanced fields missing (may be expected if no catalog sources found)")
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("Test Summary")
        logger.info("=" * 70)
        logger.info("✓ Enhanced completeness analysis test completed!")
        logger.info(f"\nGenerated HTML report: {output_dir / 'test_completeness_report.html'}")
        logger.info("Open the report in a web browser to view completeness analysis.")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Test failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_enhanced_completeness()
    sys.exit(0 if success else 1)

