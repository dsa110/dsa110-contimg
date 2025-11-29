#!/opt/miniforge/envs/casa6/bin/python
# -*- coding: utf-8 -*-
"""
Test calibrator queries in production-like scenarios.

This script verifies that calibrator queries work correctly
for various declinations and use cases.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.database.calibrators import (
    get_bandpass_calibrators,
    get_calibrators_db_path,
)
from dsa110_contimg.database.catalog_query import (
    find_calibrators_for_field,
    query_unified_catalog,
)
from dsa110_contimg.pointing.auto_calibrator import check_bp_calibrator_registered


def test_basic_queries(calibrators_db=None):
    """Test basic calibrator queries."""
    print("=" * 70)
    print("Test 1: Basic Calibrator Queries")
    print("=" * 70)

    if calibrators_db is None:
        calibrators_db = get_calibrators_db_path()

    # Test queries at various declinations
    test_cases = [
        (30.0, "Northern sky (3C286 region)"),
        (33.0, "Northern sky (3C48 region)"),
        (50.0, "Mid-northern sky"),
        (55.0, "High northern sky (0834+555 region)"),
        (0.0, "Equatorial"),
        (-5.0, "Southern sky"),
    ]

    all_passed = True
    for dec_deg, description in test_cases:
        calibrators = get_bandpass_calibrators(
            dec_deg=dec_deg, status="active", calibrators_db=calibrators_db
        )

        if calibrators:
            print(f":check: Dec {dec_deg:6.1f}° ({description}): Found {len(calibrators)} calibrator(s)")
            for cal in calibrators[:2]:  # Show first 2
                print(
                    f"   - {cal['calibrator_name']:12s} "
                    f"(RA={cal['ra_deg']:8.4f}, Dec={cal['dec_deg']:7.4f})"
                )
        else:
            print(f":warning:  Dec {dec_deg:6.1f}° ({description}): No calibrators found")
            all_passed = False

    print()
    return all_passed


def test_pipeline_code_compatibility(calibrators_db=None):
    """Test that pipeline code can query calibrators correctly."""
    print("=" * 70)
    print("Test 2: Pipeline Code Compatibility")
    print("=" * 70)

    if calibrators_db is None:
        calibrators_db = get_calibrators_db_path()

    # Test auto_calibrator.py function
    test_decs = [30.0, 33.0, 50.0]
    all_passed = True

    for dec_deg in test_decs:
        result = check_bp_calibrator_registered(
            products_db=None,  # Not used in new implementation
            dec_deg=dec_deg,
            dec_tolerance_deg=5.0,
        )

        if result:
            name, ra, dec = result
            print(f":check: Dec {dec_deg:6.1f}°: Found {name} (RA={ra:.4f}, Dec={dec:.4f})")
        else:
            print(f":warning:  Dec {dec_deg:6.1f}°: No calibrator found")
            all_passed = False

    print()
    return all_passed


def test_unified_catalog_query(calibrators_db=None):
    """Test unified catalog query interface."""
    print("=" * 70)
    print("Test 3: Unified Catalog Query")
    print("=" * 70)

    # Test finding calibrators for a field
    test_fields = [
        (202.7845, 30.5092, "3C286 field"),
        (129.2758, 55.2456, "0834+555 field"),
        (24.4221, 33.1597, "3C48 field"),
    ]

    all_passed = True
    for ra_deg, dec_deg, description in test_fields:
        try:
            bp_cal, gain_cals = find_calibrators_for_field(
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                radius_deg=0.1,
                min_flux_jy=1.0,
            )

            if bp_cal:
                print(f":check: {description}: Found BP calibrator {bp_cal['name']}")
                print(f"   Gain calibrators: {len(gain_cals)}")
            else:
                print(f":warning:  {description}: No BP calibrator found")
                all_passed = False
        except Exception as e:
            print(f":cross: {description}: Error - {e}")
            all_passed = False

    print()
    return all_passed


def test_streaming_mosaic_compatibility(calibrators_db=None):
    """Test streaming_mosaic.py compatibility."""
    print("=" * 70)
    print("Test 4: Streaming Mosaic Compatibility")
    print("=" * 70)

    if calibrators_db is None:
        calibrators_db = get_calibrators_db_path()

    # Simulate what streaming_mosaic.py does
    from dsa110_contimg.database.calibrators import get_bandpass_calibrators

    test_decs = [30.0, 33.0, 50.0]
    all_passed = True

    for dec_deg in test_decs:
        calibrators = get_bandpass_calibrators(
            dec_deg=dec_deg, status="active", calibrators_db=calibrators_db
        )

        if calibrators:
            # Format like streaming_mosaic.py expects
            calibrators.sort(key=lambda x: x.get("registered_at", 0), reverse=True)
            cal = calibrators[0]
            result = {
                "name": cal["calibrator_name"],
                "ra_deg": cal["ra_deg"],
                "dec_deg": cal["dec_deg"],
                "dec_range_min": cal.get("dec_range_min"),
                "dec_range_max": cal.get("dec_range_max"),
                "registered_at": cal.get("registered_at"),
                "notes": cal.get("notes"),
            }

            print(
                f":check: Dec {dec_deg:6.1f}°: {result['name']} "
                f"(RA={result['ra_deg']:.4f}, Dec={result['dec_deg']:.4f})"
            )
        else:
            print(f":warning:  Dec {dec_deg:6.1f}°: No calibrator found")
            all_passed = False

    print()
    return all_passed


def test_query_performance(calibrators_db=None):
    """Test query performance."""
    print("=" * 70)
    print("Test 5: Query Performance")
    print("=" * 70)

    import time

    if calibrators_db is None:
        calibrators_db = get_calibrators_db_path()

    # Test 100 queries
    start_time = time.time()
    for i in range(100):
        dec_deg = 30.0 + (i % 20)  # Vary declination
        get_bandpass_calibrators(dec_deg=dec_deg, calibrators_db=calibrators_db)

    elapsed = time.time() - start_time
    avg_time = elapsed / 100

    print(f":check: 100 queries completed in {elapsed:.3f}s")
    print(f"   Average: {avg_time*1000:.2f}ms per query")

    if avg_time < 0.01:  # Less than 10ms
        print("   :check: Performance: Excellent")
    elif avg_time < 0.05:  # Less than 50ms
        print("   :check: Performance: Good")
    else:
        print("   :warning:  Performance: May need optimization")

    print()
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Test calibrator queries in production-like scenarios"
    )
    parser.add_argument(
        "--calibrators-db",
        type=Path,
        default=None,
        help="Path to calibrators database (default: auto-detect)",
    )
    parser.add_argument(
        "--test",
        choices=["all", "basic", "pipeline", "catalog", "mosaic", "performance"],
        default="all",
        help="Which test to run",
    )

    args = parser.parse_args()

    calibrators_db = args.calibrators_db

    print("Calibrator Query Test Suite")
    print("=" * 70)
    print(f"Database: {calibrators_db or get_calibrators_db_path()}")
    print()

    results = {}

    if args.test in ["all", "basic"]:
        results["basic"] = test_basic_queries(calibrators_db)

    if args.test in ["all", "pipeline"]:
        results["pipeline"] = test_pipeline_code_compatibility(calibrators_db)

    if args.test in ["all", "catalog"]:
        results["catalog"] = test_unified_catalog_query(calibrators_db)

    if args.test in ["all", "mosaic"]:
        results["mosaic"] = test_streaming_mosaic_compatibility(calibrators_db)

    if args.test in ["all", "performance"]:
        results["performance"] = test_query_performance(calibrators_db)

    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    for test_name, passed in results.items():
        status = ":check: PASSED" if passed else ":cross: FAILED"
        print(f"{test_name:20s}: {status}")

    all_passed = all(results.values())

    print()
    if all_passed:
        print(":check: All tests passed!")
        return 0
    else:
        print(":cross: Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
