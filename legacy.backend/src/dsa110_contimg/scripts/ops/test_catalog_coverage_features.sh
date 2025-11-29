#!/bin/bash
# Test script for catalog coverage features
# Requires: Python 3.7+ (casa6 environment)

set -e

echo "=========================================="
echo "Catalog Coverage Features - Test Script"
echo "=========================================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Check if we're in casa6 environment
if command -v conda &> /dev/null; then
    CONDA_ENV=$(conda info --envs | grep '*' | awk '{print $1}')
    echo "Active conda environment: ${CONDA_ENV:-none}"
    if [ "$CONDA_ENV" != "casa6" ]; then
        echo ":warning_sign::variation_selector-16:  WARNING: Not in casa6 environment. Activate with: conda activate casa6"
        echo "   Some tests may fail due to missing dependencies or Python version."
    fi
else
    echo ":warning_sign::variation_selector-16:  WARNING: conda not found. Ensure Python 3.7+ and required packages are installed."
fi

echo ""
echo "=========================================="
echo "Test 1: Import auto-build functions"
echo "=========================================="
python3 -c "
from dsa110_contimg.catalog.builders import (
    auto_build_missing_catalog_databases,
    check_missing_catalog_databases,
    CATALOG_COVERAGE_LIMITS
)
print(':white_heavy_check_mark: Auto-build functions importable')
print(f':white_heavy_check_mark: Coverage limits defined: {list(CATALOG_COVERAGE_LIMITS.keys())}')
" || echo ":cross_mark: Import failed"

echo ""
echo "=========================================="
echo "Test 2: Import API status function"
echo "=========================================="
python3 -c "
from dsa110_contimg.api.routers.status import get_catalog_coverage_status
print(':white_heavy_check_mark: API status function importable')
" || echo ":cross_mark: Import failed"

echo ""
echo "=========================================="
echo "Test 3: Import visualization function"
echo "=========================================="
python3 -c "
from dsa110_contimg.catalog.visualize_coverage import plot_catalog_coverage
print(':white_heavy_check_mark: Visualization function importable')
" || echo ":cross_mark: Import failed"

echo ""
echo "=========================================="
echo "Test 4: Check coverage limits constants"
echo "=========================================="
python3 -c "
from dsa110_contimg.catalog.builders import CATALOG_COVERAGE_LIMITS
for catalog, limits in CATALOG_COVERAGE_LIMITS.items():
    print(f'  {catalog}: {limits[\"dec_min\"]}° to {limits[\"dec_max\"]}°')
" || echo ":cross_mark: Check failed"

echo ""
echo "=========================================="
echo "Tests complete"
echo "=========================================="
