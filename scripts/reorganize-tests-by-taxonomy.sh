#!/bin/bash
# Comprehensive test reorganization based on test taxonomy
# See docs/concepts/TEST_ORGANIZATION.md for rationale

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Reorganizing tests based on taxonomy..."
echo "See docs/concepts/TEST_ORGANIZATION.md for rationale"
echo ""

# Create directory structure
mkdir -p tests/smoke
mkdir -p tests/e2e
mkdir -p tests/unit/{api,calibration,catalog,conversion,database,imaging,mosaic,photometry,pipeline,qa,simulation,visualization}

# Analyze and categorize remaining tests in tests/unit/ root
echo "Analyzing remaining tests in tests/unit/..."

# CASA-related tests → unit (infrastructure)
[ -f tests/unit/test_casa_lazy_imports.py ] && echo "  Keeping test_casa_lazy_imports.py in unit/ (infrastructure test)"

# Masking tests → unit/imaging (masking is part of imaging pipeline)
[ -f tests/unit/test_masking.py ] && mv tests/unit/test_masking.py tests/unit/imaging/ && echo "  Moved test_masking.py → tests/unit/imaging/"

# Utility/helper tests → keep in unit root or create utils subdirectory
[ -f tests/unit/test_mermaid_diagram_helpers.py ] && echo "  Keeping test_mermaid_diagram_helpers.py in unit/ (utility test)"
[ -f tests/unit/test_monitoring_script.py ] && echo "  Keeping test_monitoring_script.py in unit/ (utility test)"

# Optimization tests → unit (performance testing)
[ -f tests/unit/test_optimizations.py ] && echo "  Keeping test_optimizations.py in unit/ (performance test)"

# Parallel processing tests → unit (infrastructure)
[ -f tests/unit/test_parallel.py ] && echo "  Keeping test_parallel.py in unit/ (infrastructure test)"

# Pointing tests → unit/pointing (if we create it) or unit/catalog
[ -f tests/unit/test_products_pointing.py ] && mv tests/unit/test_products_pointing.py tests/unit/catalog/ && echo "  Moved test_products_pointing.py → tests/unit/catalog/"

# Source class tests → unit/photometry (sources are used in photometry)
[ -f tests/unit/test_source_class.py ] && mv tests/unit/test_source_class.py tests/unit/photometry/ && echo "  Moved test_source_class.py → tests/unit/photometry/"

# Create smoke tests from critical path tests
echo ""
echo "Identifying smoke tests..."

# Check if test_priority1_quick.py should become a smoke test
if [ -f tests/test_priority1_quick.py ]; then
    # This is already a quick check - make it a smoke test
    mv tests/test_priority1_quick.py tests/smoke/test_priority1_quick.py
    echo "  Moved test_priority1_quick.py → tests/smoke/ (quick sanity check)"
fi

# Check integration tests for end-to-end workflows
echo ""
echo "Checking for end-to-end tests..."

# End-to-end workflow tests should be in e2e
if [ -f tests/integration/test_end_to_end_batch_workflow.py ]; then
    # This is already in integration, which is fine, but could be e2e
    echo "  test_end_to_end_batch_workflow.py is in integration/ (appropriate for workflow test)"
fi

# Update pytest.ini to include smoke tests
echo ""
echo "Updating pytest.ini to include smoke tests..."
if ! grep -q "tests/smoke" tests/pytest.ini; then
    # Add smoke tests to testpaths
    sed -i '/^testpaths =/a\    tests/smoke' tests/pytest.ini
    echo "  Added tests/smoke to pytest.ini"
fi

# Create __init__.py files where needed
echo ""
echo "Creating __init__.py files..."
touch tests/smoke/__init__.py
touch tests/e2e/__init__.py
echo "  Created __init__.py files"

# Summary
echo ""
echo "=== Reorganization Summary ==="
echo ""
echo "Test organization:"
echo "  Unit tests:      $(find tests/unit -name 'test_*.py' -type f | wc -l) files"
echo "  Integration:    $(find tests/integration -name 'test_*.py' -type f | wc -l) files"
echo "  Smoke tests:    $(find tests/smoke -name 'test_*.py' -type f | wc -l) files"
echo "  Science tests:  $(find tests/science -name 'test_*.py' -type f | wc -l) files"
echo "  E2E tests:      $(find tests/e2e -name 'test_*.py' -type f | wc -l) files"
echo ""
echo "Remaining files in tests/ root:"
ls -1 tests/test_*.py 2>/dev/null | wc -l | xargs echo "  Count:"
echo ""
echo "Remaining files in tests/unit/ root:"
ls -1 tests/unit/test_*.py 2>/dev/null | wc -l | xargs echo "  Count:"
if [ $(ls -1 tests/unit/test_*.py 2>/dev/null | wc -l) -gt 0 ]; then
    echo "  Files:"
    ls -1 tests/unit/test_*.py 2>/dev/null | sed 's/^/    /'
fi
echo ""
echo "Reorganization complete!"
echo ""
echo "Next steps:"
echo "  1. Review test markers (@pytest.mark.unit, @pytest.mark.integration, etc.)"
echo "  2. Add markers to tests that don't have them"
echo "  3. Update test runner script (scripts/run-tests.sh)"
echo "  4. Run tests to verify organization: pytest tests/ -v"

