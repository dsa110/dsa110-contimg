#!/usr/bin/env python3
"""
Comprehensive test of validation system with real FITS image data.

Tests all validation functions end-to-end with a real image to ensure
complete functionality.
"""

import sys
from pathlib import Path

# Add src to path BEFORE importing dsa110_contimg modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging
from dsa110_contimg.qa.catalog_validation import (
    validate_astrometry,
    validate_flux_scale,
    validate_source_counts,
    run_full_validation
)
from dsa110_contimg.qa.html_reports import generate_validation_report

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def find_test_fits_image():
    """Find an available test FITS image."""
    test_files = [
        "tests/integration/test_outputs/test_science_field.fits",
        "notebooks/notebook_outputs/test_science_field.fits",
        "notebooks/notebook_outputs/test_science_field_0834+555.fits",
        "tests/integration/test_outputs/test_low_snr.fits",
        "notebooks/notebook_outputs/test_low_snr.fits",
    ]
    
    for test_file in test_files:
        path = Path(test_file)
        if path.exists():
            return str(path.absolute())
    
    return None


def test_validation_with_real_data():
    """Test validation system with real FITS image."""
    
    logger.info("=" * 70)
    logger.info("Comprehensive Validation System Test with Real Data")
    logger.info("=" * 70)
    logger.info("")
    
    # Find test image
    test_image = find_test_fits_image()
    if not test_image:
        logger.error("✗ No test FITS images found!")
        logger.error("  Please ensure at least one test FITS file exists.")
        logger.error("  Expected locations:")
        logger.error("    - tests/integration/test_outputs/*.fits")
        logger.error("    - notebooks/notebook_outputs/*.fits")
        return False
    
    logger.info(f"✓ Found test image: {test_image}")
    
    # Create output directory
    output_dir = Path("state/qa/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    test_results = {
        "catalog_query": False,
        "astrometry": False,
        "flux_scale": False,
        "source_counts": False,
        "html_report": False,
        "plots": False,
    }
    
    try:
        # Test 1: Catalog Query (via astrometry validation)
        logger.info("\n" + "=" * 70)
        logger.info("Test 1: Catalog Query")
        logger.info("=" * 70)
        try:
            astrometry_result = validate_astrometry(
                image_path=test_image,
                catalog="nvss",
                min_snr=5.0,
                search_radius_arcsec=10.0
            )
            test_results["catalog_query"] = True
            test_results["astrometry"] = True
            logger.info(f"✓ Catalog query successful")
            logger.info(f"  - Matched sources: {astrometry_result.n_matched}")
            logger.info(f"  - Catalog sources: {astrometry_result.n_catalog}")
            logger.info(f"  - Detected sources: {astrometry_result.n_detected}")
            if astrometry_result.rms_offset_arcsec:
                logger.info(f"  - RMS offset: {astrometry_result.rms_offset_arcsec:.2f}\"")
        except Exception as e:
            logger.error(f"✗ Catalog query failed: {e}", exc_info=True)
            return False
        
        # Test 2: Flux Scale Validation
        logger.info("\n" + "=" * 70)
        logger.info("Test 2: Flux Scale Validation")
        logger.info("=" * 70)
        try:
            flux_result = validate_flux_scale(
                image_path=test_image,
                catalog="nvss",
                min_snr=5.0
            )
            test_results["flux_scale"] = True
            logger.info(f"✓ Flux scale validation successful")
            logger.info(f"  - Matched sources: {flux_result.n_matched}")
            if flux_result.mean_flux_ratio:
                logger.info(f"  - Mean flux ratio: {flux_result.mean_flux_ratio:.3f}")
            if flux_result.flux_scale_error:
                logger.info(f"  - Flux scale error: {flux_result.flux_scale_error*100:.1f}%")
        except Exception as e:
            logger.error(f"✗ Flux scale validation failed: {e}", exc_info=True)
            return False
        
        # Test 3: Source Counts Completeness
        logger.info("\n" + "=" * 70)
        logger.info("Test 3: Source Counts Completeness Analysis")
        logger.info("=" * 70)
        try:
            completeness_result = validate_source_counts(
                image_path=test_image,
                catalog="nvss",
                min_snr=5.0,
                completeness_threshold=0.95
            )
            test_results["source_counts"] = True
            logger.info(f"✓ Source counts validation successful")
            logger.info(f"  - Matched sources: {completeness_result.n_matched}")
            logger.info(f"  - Catalog sources: {completeness_result.n_catalog}")
            logger.info(f"  - Detected sources: {completeness_result.n_detected}")
            if completeness_result.completeness:
                logger.info(f"  - Overall completeness: {completeness_result.completeness*100:.1f}%")
            if completeness_result.completeness_limit_jy:
                logger.info(f"  - Completeness limit: {completeness_result.completeness_limit_jy*1000:.2f} mJy")
        except Exception as e:
            logger.error(f"✗ Source counts validation failed: {e}", exc_info=True)
            return False
        
        # Test 4: Full Validation with HTML Report
        logger.info("\n" + "=" * 70)
        logger.info("Test 4: Full Validation with HTML Report")
        logger.info("=" * 70)
        try:
            html_path = str(output_dir / "real_data_validation_report.html")
            astrometry_result, flux_result, completeness_result = run_full_validation(
                image_path=test_image,
                catalog="nvss",
                validation_types=["astrometry", "flux_scale", "source_counts"],
                generate_html=True,
                html_output_path=html_path
            )
            test_results["html_report"] = True
            logger.info(f"✓ Full validation with HTML report successful")
            logger.info(f"  - HTML report: {html_path}")
            
            # Check if HTML file exists and contains expected content
            if Path(html_path).exists():
                with open(html_path, 'r') as f:
                    html_content = f.read()
                
                # Check for plot indicators
                if "data:image/png;base64," in html_content:
                    test_results["plots"] = True
                    plot_count = html_content.count("data:image/png;base64,")
                    logger.info(f"  - Found {plot_count} embedded plots")
                else:
                    logger.warning("  - No plots found in HTML report")
                
                # Check for validation sections
                indicators = [
                    "Astrometry Validation",
                    "Flux Scale Validation",
                    "Source Counts Validation"
                ]
                missing = [ind for ind in indicators if ind not in html_content]
                if missing:
                    logger.warning(f"  - Missing sections: {missing}")
                else:
                    logger.info("  - All validation sections present")
                
                file_size = Path(html_path).stat().st_size
                logger.info(f"  - File size: {file_size:,} bytes")
            else:
                logger.error(f"  - HTML file not created: {html_path}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Full validation failed: {e}", exc_info=True)
            return False
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("Test Summary")
        logger.info("=" * 70)
        
        all_passed = all(test_results.values())
        
        for test_name, passed in test_results.items():
            status = "✓" if passed else "✗"
            logger.info(f"{status} {test_name.replace('_', ' ').title()}: {'PASS' if passed else 'FAIL'}")
        
        if all_passed:
            logger.info("\n✓ All tests passed! Validation system works with real data.")
            logger.info(f"\nView HTML report: {html_path}")
            return True
        else:
            logger.error("\n✗ Some tests failed. See details above.")
            return False
        
    except Exception as e:
        logger.error(f"✗ Test suite failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_validation_with_real_data()
    sys.exit(0 if success else 1)

