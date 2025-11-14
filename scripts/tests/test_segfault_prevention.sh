#!/bin/bash
#
# Manual test script to verify CASA segfault prevention.
#
# This script tests the problematic import chain that previously caused segfaults
# and verifies that the lazy import fix prevents them.
#
# Usage: ./scripts/test_segfault_prevention.sh

set -e

PYTHON_BIN_BASE="/opt/miniforge/envs/casa6/bin/python"
PYTHON_BIN="${PYTHON_BIN_BASE} -W ignore::DeprecationWarning"
PROJECT_ROOT="/data/dsa110-contimg"
PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH}"

echo "=========================================="
echo "CASA Segfault Prevention Test"
echo "=========================================="
echo ""

# Test 1: Import qa module
echo "Test 1: Importing qa module..."
${PYTHON_BIN} -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/src')
from dsa110_contimg.qa import create_cutout
print('  ✓ Import successful')
" || { echo "  ✗ FAILED"; exit 1; }

# Test 2: Import CasaTable
echo "Test 2: Importing CasaTable..."
${PYTHON_BIN} -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/src')
from dsa110_contimg.qa.visualization import CasaTable
print('  ✓ Import successful')
" || { echo "  ✗ FAILED"; exit 1; }

# Test 3: Verify CASA not initialized on import
echo "Test 3: Verifying CASA not initialized on import..."
${PYTHON_BIN} -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/src')
from dsa110_contimg.qa.visualization.casatable import _CASACORE_AVAILABLE
assert _CASACORE_AVAILABLE is None, 'CASA should not be initialized on import'
print('  ✓ CASA not initialized (as expected)')
" || { echo "  ✗ FAILED"; exit 1; }

# Test 4: Multiple imports
echo "Test 4: Testing multiple imports..."
${PYTHON_BIN} -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/src')
from dsa110_contimg.qa import create_cutout
from dsa110_contimg.qa.visualization import CasaTable
from dsa110_contimg.qa.postage_stamps import create_cutout as ps_create_cutout
print('  ✓ All imports successful')
" || { echo "  ✗ FAILED"; exit 1; }

# Test 5: Subprocess test (catches segfaults that might not be caught in same process)
echo "Test 5: Subprocess import test..."
${PYTHON_BIN} -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/src')
from dsa110_contimg.qa import create_cutout
print('SUCCESS: Import completed without segfault')
" || { echo "  ✗ FAILED"; exit 1; }

# Test 6: Run pytest tests
echo "Test 6: Running pytest unit tests..."
cd ${PROJECT_ROOT}
PYTHONPATH=${PYTHONPATH} ${PYTHON_BIN} -m pytest tests/unit/test_casa_lazy_imports.py -v --tb=short -q || { echo "  ✗ FAILED"; exit 1; }

echo ""
echo "=========================================="
echo "All tests passed! ✓"
echo "=========================================="
echo ""
echo "The lazy import fix successfully prevents CASA segfaults."

