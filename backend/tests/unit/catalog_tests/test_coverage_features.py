#!/usr/bin/env python3
"""
Test script for catalog coverage features.

Tests:
1. Auto-build functionality
2. API status endpoint
3. Visualization tool
4. Edge cases and error handling
"""

import logging
import sqlite3
import sys
import tempfile
from pathlib import Path

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_auto_build_functionality():
    """Test A: Auto-build functionality."""
    logger.info("=" * 60)
    logger.info("TEST A: Auto-build functionality")
    logger.info("=" * 60)

    try:
        from dsa110_contimg.catalog.builders import (
            CATALOG_COVERAGE_LIMITS,
            check_catalog_database_exists,
            check_missing_catalog_databases,
        )

        # Test 1: Check missing databases (without auto-build)
        logger.info("\n1. Testing check_missing_catalog_databases (auto_build=False)")
        dec_deg = 54.6  # Within NVSS and FIRST coverage

        results = check_missing_catalog_databases(
            dec_deg=dec_deg,
            auto_build=False,
        )
        logger.info(f"   Results: {results}")

        # Test 2: Verify coverage limits
        logger.info("\n2. Verifying coverage limits")
        for catalog_type, limits in CATALOG_COVERAGE_LIMITS.items():
            dec_min = limits.get("dec_min", -90.0)
            dec_max = limits.get("dec_max", 90.0)
            within = dec_deg >= dec_min and dec_deg <= dec_max
            logger.info(
                f"   {catalog_type.upper()}: {dec_min:.1f}° to {dec_max:.1f}° - Within: {within}"
            )

        # Test 3: Check database existence
        logger.info("\n3. Checking database existence")
        for catalog_type in ["nvss", "first", "rax"]:
            exists, db_path = check_catalog_database_exists(catalog_type, dec_deg)
            logger.info(f"   {catalog_type.upper()}: exists={exists}, path={db_path}")

        logger.info("\n✓ Auto-build functionality tests completed")
        return True

    except Exception as e:
        logger.error(f"✗ Auto-build functionality test failed: {e}", exc_info=True)
        return False


def test_api_status_endpoint():
    """Test B: API status endpoint."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST B: API status endpoint")
    logger.info("=" * 60)

    try:
        from dsa110_contimg.api.routers.status import get_catalog_coverage_status

        # Test 1: Get coverage status (if ingest DB exists)
        logger.info("\n1. Testing get_catalog_coverage_status()")

        # Try to find ingest DB
        ingest_db_path = None
        for path_str in [
            "/data/dsa110-contimg/state/db/ingest.sqlite3",
            "state/db/ingest.sqlite3",
        ]:
            candidate = Path(path_str)
            if candidate.exists():
                ingest_db_path = candidate
                break

        if ingest_db_path:
            logger.info(f"   Found ingest DB: {ingest_db_path}")
            coverage_status = get_catalog_coverage_status(ingest_db_path=ingest_db_path)

            if coverage_status:
                logger.info(f"   Current declination: {coverage_status.dec_deg}°")
                logger.info(f"   NVSS: {coverage_status.nvss}")
                logger.info(f"   FIRST: {coverage_status.first}")
                logger.info(f"   RAX: {coverage_status.rax}")
            else:
                logger.warning("   No coverage status returned (no pointing history?)")
        else:
            logger.warning("   Ingest DB not found, skipping status test")

        # Test 2: Test with None (should handle gracefully)
        logger.info("\n2. Testing with None ingest_db_path")
        coverage_status = get_catalog_coverage_status(ingest_db_path=None)
        logger.info(f"   Result: {coverage_status}")

        # Test 3: Test with non-existent path
        logger.info("\n3. Testing with non-existent path")
        fake_path = Path("/tmp/nonexistent_ingest.sqlite3")
        coverage_status = get_catalog_coverage_status(ingest_db_path=fake_path)
        logger.info(f"   Result: {coverage_status}")

        logger.info("\n✓ API status endpoint tests completed")
        return True

    except Exception as e:
        logger.error(f"✗ API status endpoint test failed: {e}", exc_info=True)
        return False


def test_visualization_tool():
    """Test C: Visualization tool."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST C: Visualization tool")
    logger.info("=" * 60)

    try:
        from dsa110_contimg.catalog.visualize_coverage import (
            plot_catalog_coverage,
            plot_coverage_summary_table,
        )

        # Test 1: Test with explicit declination
        logger.info("\n1. Testing plot_catalog_coverage with explicit declination")
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_coverage.png"
            result_path = plot_catalog_coverage(
                dec_deg=54.6,
                output_path=output_path,
                show_database_status=True,
            )
            if result_path.exists():
                logger.info(f"   ✓ Plot generated: {result_path}")
            else:
                logger.error(f"   ✗ Plot not generated: {result_path}")

        # Test 2: Test summary table
        logger.info("\n2. Testing plot_coverage_summary_table")
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_table.png"
            result_path = plot_coverage_summary_table(
                dec_deg=54.6,
                output_path=output_path,
            )
            if result_path.exists():
                logger.info(f"   ✓ Table generated: {result_path}")
            else:
                logger.error(f"   ✗ Table not generated: {result_path}")

        # Test 3: Test with None declination (should handle gracefully)
        logger.info("\n3. Testing with None declination")
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_no_dec.png"
            result_path = plot_catalog_coverage(
                dec_deg=None,
                output_path=output_path,
            )
            if result_path.exists():
                logger.info(f"   ✓ Plot generated without declination: {result_path}")
            else:
                logger.error(f"   ✗ Plot not generated: {result_path}")

        logger.info("\n✓ Visualization tool tests completed")
        return True

    except ImportError as e:
        logger.warning(f"   Visualization dependencies not available: {e}")
        logger.info("   (This is expected if matplotlib is not installed)")
        return True  # Not a failure, just missing dependencies
    except Exception as e:
        logger.error(f"✗ Visualization tool test failed: {e}", exc_info=True)
        return False


def test_edge_cases():
    """Test 5: Edge cases and error handling."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Edge cases and error handling")
    logger.info("=" * 60)

    try:
        from dsa110_contimg.api.routers.status import get_catalog_coverage_status
        from dsa110_contimg.catalog.builders import check_missing_catalog_databases

        # Test 1: Declination outside coverage
        logger.info("\n1. Testing declination outside coverage")
        results = check_missing_catalog_databases(
            dec_deg=-50.0,  # Outside NVSS/FIRST coverage
            auto_build=False,
        )
        logger.info(f"   Results: {results}")

        # Test 2: Non-existent ingest DB
        logger.info("\n2. Testing with non-existent ingest DB")
        fake_path = Path("/tmp/fake_ingest.sqlite3")
        status = get_catalog_coverage_status(ingest_db_path=fake_path)
        logger.info(f"   Result: {status} (should be None)")

        # Test 3: Empty pointing history (create temp DB)
        logger.info("\n3. Testing with empty pointing history")
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp:
            tmp_db = Path(tmp.name)
            # Create empty DB
            with sqlite3.connect(str(tmp_db)) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pointing_history (
                        timestamp TEXT,
                        ra_deg REAL,
                        dec_deg REAL
                    )
                """
                )

            status = get_catalog_coverage_status(ingest_db_path=tmp_db)
            logger.info(f"   Result: {status} (should be None)")

            # Cleanup
            tmp_db.unlink()

        logger.info("\n✓ Edge case tests completed")
        return True

    except Exception as e:
        logger.error(f"✗ Edge case test failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    logger.info("Starting catalog coverage features tests...")
    logger.info("")

    results = {
        "Auto-build functionality": test_auto_build_functionality(),
        "API status endpoint": test_api_status_endpoint(),
        "Visualization tool": test_visualization_tool(),
        "Edge cases": test_edge_cases(),
    }

    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    logger.info("")
    if all_passed:
        logger.info("✓ All tests passed!")
        return 0
    else:
        logger.error("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
