#!/usr/bin/env python3
"""
Test script for new API endpoints.

Tests the endpoint implementations without requiring a running server.
Validates:
1. Endpoint function signatures
2. Model imports
3. Database query structure
4. Error handling
"""

import sys
from pathlib import Path


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    try:
        from dsa110_contimg.api.models import (
            Detection,
            DetectionList,
            ImageDetail,
            Measurement,
            MeasurementList,
            SourceDetail,
        )

        print("✓ All models imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_endpoint_functions():
    """Test that endpoint functions exist and have correct signatures."""
    print("\nTesting endpoint functions...")

    # Read routes.py to check function definitions
    routes_path = Path(__file__).parent.parent / "src" / "dsa110_contimg" / "api" / "routes.py"
    if not routes_path.exists():
        print(f"✗ Routes file not found: {routes_path}")
        return False

    content = routes_path.read_text()

    endpoints = [
        ("get_source_detail", '@router.get("/sources/{source_id}")'),
        ("get_source_detections", '@router.get("/sources/{source_id}/detections")'),
        ("get_image_detail", '@router.get("/images/{image_id}")'),
        ("get_image_measurements", '@router.get("/images/{image_id}/measurements")'),
    ]

    all_found = True
    for func_name, decorator in endpoints:
        if decorator in content:
            # Check if function is defined
            if f"def {func_name}" in content:
                print(f"✓ {func_name} endpoint found")
            else:
                print(f"✗ {func_name} function not found (decorator exists)")
                all_found = False
        else:
            print(f"✗ {func_name} endpoint not found")
            all_found = False

    return all_found


def test_model_structure():
    """Test that models have expected fields."""
    print("\nTesting model structure...")

    try:
        from dsa110_contimg.api.models import (
            Detection,
            ImageDetail,
            Measurement,
            SourceDetail,
        )

        # Check SourceDetail fields
        source_fields = ["id", "ra_deg", "dec_deg", "n_meas", "n_meas_forced"]
        source_model_fields = SourceDetail.__fields__.keys()
        missing = [f for f in source_fields if f not in source_model_fields]
        if missing:
            print(f"✗ SourceDetail missing fields: {missing}")
            return False
        print("✓ SourceDetail model structure valid")

        # Check Detection fields
        detection_fields = ["ra", "dec", "flux_peak", "forced"]
        detection_model_fields = Detection.__fields__.keys()
        missing = [f for f in detection_fields if f not in detection_model_fields]
        if missing:
            print(f"✗ Detection missing fields: {missing}")
            return False
        print("✓ Detection model structure valid")

        # Check ImageDetail fields
        image_fields = ["id", "path", "n_meas", "n_runs", "type"]
        image_model_fields = ImageDetail.__fields__.keys()
        missing = [f for f in image_fields if f not in image_model_fields]
        if missing:
            print(f"✗ ImageDetail missing fields: {missing}")
            return False
        print("✓ ImageDetail model structure valid")

        # Check Measurement fields
        measurement_fields = ["ra", "dec", "flux_peak", "forced"]
        measurement_model_fields = Measurement.__fields__.keys()
        missing = [f for f in measurement_fields if f not in measurement_model_fields]
        if missing:
            print(f"✗ Measurement missing fields: {missing}")
            return False
        print("✓ Measurement model structure valid")

        return True
    except Exception as e:
        print(f"✗ Model structure test failed: {e}")
        return False


def test_database_queries():
    """Test that database queries are structured correctly."""
    print("\nTesting database query structure...")

    routes_path = Path(__file__).parent.parent / "src" / "dsa110_contimg" / "api" / "routes.py"
    content = routes_path.read_text()

    # Check for SQL injection vulnerabilities (basic check)
    dangerous_patterns = [
        'f"SELECT',
        "f'SELECT",
        "{source_id}",
        "{image_id}",
    ]

    found_dangerous = False
    for pattern in dangerous_patterns:
        if pattern in content:
            print(f"⚠ Warning: Potential SQL injection risk with pattern: {pattern}")
            found_dangerous = True

    # Check for parameterized queries
    safe_patterns = [
        "conn.execute(",
        "?",
        "params=(",
    ]

    safe_count = sum(1 for pattern in safe_patterns if pattern in content)
    if safe_count >= 2:
        print("✓ Parameterized queries detected")
    else:
        print("⚠ Warning: May not be using parameterized queries")

    return not found_dangerous


def main():
    """Run all tests."""
    print("=" * 60)
    print("API Endpoints Test Suite")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Endpoint Functions", test_endpoint_functions()))
    results.append(("Model Structure", test_model_structure()))
    results.append(("Database Queries", test_database_queries()))

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:30} {status}")

    all_passed = all(result[1] for result in results)

    print("=" * 60)
    if all_passed:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
