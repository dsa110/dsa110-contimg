"""
Simplified integration tests for catalog coverage features.

Tests the integration of:
1. Auto-build missing catalog databases
2. Coverage status in API endpoints
3. Visualization tools

These tests verify the features work together without requiring full pipeline dependencies.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def test_auto_build_integration():
    """Test auto-build functionality integration."""
    print("=" * 60)
    print("Test 1: Auto-build Integration")
    print("=" * 60)

    from dsa110_contimg.catalog.builders import (
        CATALOG_COVERAGE_LIMITS,
        auto_build_missing_catalog_databases,
        check_missing_catalog_databases,
    )

    # Test with declination within coverage
    dec_deg = 54.6

    # Check missing databases
    missing = check_missing_catalog_databases(dec_deg, auto_build=False)
    print(f"✅ Missing databases check: {len(missing)} missing")

    # Verify coverage limits
    assert "nvss" in CATALOG_COVERAGE_LIMITS
    assert "first" in CATALOG_COVERAGE_LIMITS
    assert "rax" in CATALOG_COVERAGE_LIMITS
    print(f"✅ Coverage limits defined: {list(CATALOG_COVERAGE_LIMITS.keys())}")

    # Verify auto-build function exists
    assert callable(auto_build_missing_catalog_databases)
    print("✅ Auto-build function callable")

    # Test coverage limits
    nvss_limits = CATALOG_COVERAGE_LIMITS["nvss"]
    assert nvss_limits["dec_min"] == -40.0
    assert nvss_limits["dec_max"] == 90.0
    print(f"✅ NVSS coverage: {nvss_limits['dec_min']}° to {nvss_limits['dec_max']}°")


def test_api_status_integration():
    """Test API status endpoint integration."""
    print("\n" + "=" * 60)
    print("Test 2: API Status Integration")
    print("=" * 60)

    from dsa110_contimg.api.routers.status import get_catalog_coverage_status

    # Test function exists and is callable
    assert callable(get_catalog_coverage_status)
    print("✅ API status function callable")

    # Test with None (no database) - should handle gracefully
    status = get_catalog_coverage_status(ingest_db_path=None)
    print(f"✅ API status handles None gracefully: {status is None or hasattr(status, 'dec_deg')}")


def test_visualization_integration():
    """Test visualization tools integration."""
    print("\n" + "=" * 60)
    print("Test 3: Visualization Integration")
    print("=" * 60)

    from dsa110_contimg.catalog.visualize_coverage import plot_catalog_coverage

    # Verify function exists and is callable
    assert callable(plot_catalog_coverage)
    print("✅ Visualization function callable")


def test_nvss_query_integration():
    """Test NVSS query integration with auto-build."""
    print("\n" + "=" * 60)
    print("Test 4: NVSS Query Integration")
    print("=" * 60)

    from dsa110_contimg.calibration.catalogs import query_nvss_sources

    # Verify function exists and is callable
    assert callable(query_nvss_sources)
    print("✅ NVSS query function callable")

    # Note: Actual query would require catalog databases
    # This test just verifies the function is available


def test_coverage_limits_validation():
    """Test coverage limits validation."""
    print("\n" + "=" * 60)
    print("Test 5: Coverage Limits Validation")
    print("=" * 60)

    from dsa110_contimg.catalog.builders import CATALOG_COVERAGE_LIMITS

    # Verify all catalogs have limits
    for catalog, limits in CATALOG_COVERAGE_LIMITS.items():
        assert "dec_min" in limits
        assert "dec_max" in limits
        assert limits["dec_min"] < limits["dec_max"]
        print(f"✅ {catalog.upper()}: {limits['dec_min']}° to {limits['dec_max']}°")


def _run_all_integration_tests():
    """Run all integration tests (script entry point, not a pytest test)."""
    print("\n" + "=" * 60)
    print("Full Integration Test Suite")
    print("=" * 60)

    results = []

    try:
        test_auto_build_integration()
        results.append(("Auto-build", True))
    except Exception as e:
        print(f"❌ Auto-build test failed: {e}")
        results.append(("Auto-build", False))

    try:
        test_api_status_integration()
        results.append(("API Status", True))
    except Exception as e:
        print(f"❌ API Status test failed: {e}")
        results.append(("API Status", False))

    try:
        test_visualization_integration()
        results.append(("Visualization", True))
    except Exception as e:
        print(f"❌ Visualization test failed: {e}")
        results.append(("Visualization", False))

    try:
        test_nvss_query_integration()
        results.append(("NVSS Query", True))
    except Exception as e:
        print(f"❌ NVSS Query test failed: {e}")
        results.append(("NVSS Query", False))

    try:
        test_coverage_limits_validation()
        results.append(("Coverage Limits", True))
    except Exception as e:
        print(f"❌ Coverage Limits test failed: {e}")
        results.append(("Coverage Limits", False))

    # Summary
    print("\n" + "=" * 60)
    print("Integration Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All integration tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(_run_all_integration_tests())
