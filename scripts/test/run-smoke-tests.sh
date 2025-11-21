#!/bin/bash
# Run smoke tests for quick validation
# Usage: ./scripts/test/run-smoke-tests.sh

set -e

cd "$(dirname "$0")/../.."

echo "================================"
echo "Running Smoke Tests"
echo "================================"
echo ""
echo "These tests verify critical system components are operational."
echo "Expected runtime: < 10 seconds"
echo ""

# Ensure we're in casa6 environment
if ! python -c "import casacore" 2>/dev/null; then
    echo "WARNING: casacore not available. Some tests may be skipped."
    echo "Activate casa6 environment: conda activate casa6"
fi

# Run smoke tests
python -m pytest tests/test_smoke.py -v --tb=short

echo ""
echo "================================"
echo "Smoke Tests Complete"
echo "================================"
