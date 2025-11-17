#!/opt/miniforge/envs/casa6/bin/python
"""
Verification script for catalog coverage features.

This script verifies that the features are implemented correctly
by checking file contents and structure rather than importing modules.
Works with any Python version.
"""

import os
import re
import sys
from pathlib import Path


def check_file_exists(filepath):
    """Check if a file exists."""
    path = Path(filepath)
    exists = path.exists()
    status = "✓" if exists else "✗"
    print(f"{status} {filepath}: {'EXISTS' if exists else 'MISSING'}")
    return exists


def check_function_exists(filepath, function_name):
    """Check if a function exists in a file."""
    path = Path(filepath)
    if not path.exists():
        return False
    
    content = path.read_text()
    pattern = r'def\s+' + re.escape(function_name) + r'\s*\('
    exists = bool(re.search(pattern, content))
    status = "✓" if exists else "✗"
    print(f"{status} Function '{function_name}' in {filepath}: {'FOUND' if exists else 'NOT FOUND'}")
    return exists


def check_class_exists(filepath, class_name):
    """Check if a class exists in a file."""
    path = Path(filepath)
    if not path.exists():
        return False
    
    content = path.read_text()
    pattern = r'class\s+' + re.escape(class_name) + r'\s*[\(:]'
    exists = bool(re.search(pattern, content))
    status = "✓" if exists else "✗"
    print(f"{status} Class '{class_name}' in {filepath}: {'FOUND' if exists else 'NOT FOUND'}")
    return exists


def check_string_in_file(filepath, search_string):
    """Check if a string exists in a file."""
    path = Path(filepath)
    if not path.exists():
        return False
    
    content = path.read_text()
    exists = search_string in content
    status = "✓" if exists else "✗"
    print(f"{status} String '{search_string[:50]}...' in {filepath}: {'FOUND' if exists else 'NOT FOUND'}")
    return exists


def main():
    """Run verification checks."""
    print("=" * 70)
    print("CATALOG COVERAGE FEATURES - VERIFICATION")
    print("=" * 70)
    print()
    
    all_passed = True
    
    # 1. Auto-build functionality
    print("1. AUTO-BUILD FUNCTIONALITY")
    print("-" * 70)
    
    all_passed &= check_file_exists("dsa110_contimg/catalog/builders.py")
    all_passed &= check_function_exists("dsa110_contimg/catalog/builders.py", "check_missing_catalog_databases")
    all_passed &= check_function_exists("dsa110_contimg/catalog/builders.py", "auto_build_missing_catalog_databases")
    all_passed &= check_string_in_file("dsa110_contimg/catalog/builders.py", "auto_build=True")
    all_passed &= check_string_in_file("dsa110_contimg/calibration/catalogs.py", "auto_build=True")
    all_passed &= check_string_in_file("dsa110_contimg/pointing/auto_calibrator.py", "auto_build=True")
    print()
    
    # 2. API status endpoint
    print("2. API STATUS ENDPOINT")
    print("-" * 70)
    
    all_passed &= check_file_exists("dsa110_contimg/api/models.py")
    all_passed &= check_class_exists("dsa110_contimg/api/models.py", "CatalogCoverageStatus")
    all_passed &= check_string_in_file("dsa110_contimg/api/models.py", "catalog_coverage")
    all_passed &= check_file_exists("dsa110_contimg/api/routers/status.py")
    all_passed &= check_function_exists("dsa110_contimg/api/routers/status.py", "get_catalog_coverage_status")
    all_passed &= check_string_in_file("dsa110_contimg/api/routers/status.py", "catalog_coverage=catalog_coverage")
    print()
    
    # 3. Visualization tool
    print("3. VISUALIZATION TOOL")
    print("-" * 70)
    
    all_passed &= check_file_exists("dsa110_contimg/catalog/visualize_coverage.py")
    all_passed &= check_function_exists("dsa110_contimg/catalog/visualize_coverage.py", "plot_catalog_coverage")
    all_passed &= check_function_exists("dsa110_contimg/catalog/visualize_coverage.py", "plot_coverage_summary_table")
    all_passed &= check_string_in_file("dsa110_contimg/catalog/visualize_coverage.py", "if __name__ == \"__main__\"")
    print()
    
    # 4. Documentation
    print("4. DOCUMENTATION")
    print("-" * 70)
    
    all_passed &= check_file_exists("COVERAGE_FEATURES_IMPLEMENTATION.md")
    print()
    
    # 5. Integration points
    print("5. INTEGRATION POINTS")
    print("-" * 70)
    
    all_passed &= check_string_in_file("dsa110_contimg/catalog/__init__.py", "auto_build_missing_catalog_databases")
    all_passed &= check_string_in_file("dsa110_contimg/catalog/__init__.py", "check_missing_catalog_databases")
    all_passed &= check_string_in_file("dsa110_contimg/catalog/__init__.py", "CATALOG_COVERAGE_LIMITS")
    print()
    
    # Summary
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    if all_passed:
        print("✓ All verification checks PASSED")
        print()
        print("Next steps:")
        print("  1. Run integration tests with Python 3.7+")
        print("  2. Test API endpoint: curl http://localhost:8000/api/status")
        print("  3. Test visualization: python -m dsa110_contimg.catalog.visualize_coverage")
        print("  4. Test auto-build by querying NVSS sources")
        return 0
    else:
        print("✗ Some verification checks FAILED")
        print("  Please review the output above for missing components")
        return 1


if __name__ == "__main__":
    sys.exit(main())

