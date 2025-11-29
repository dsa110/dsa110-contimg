#!/bin/bash
# Test runner script with proper output capture

set -euo pipefail

cd "$(dirname "$0")/.."

# Activate casa6 environment
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Verify Node.js version
NODE_VERSION=$(node --version)
NODE_PATH=$(which node)
echo "=== Environment Check ==="
echo "Node.js: $NODE_PATH ($NODE_VERSION)"
echo ""

# Run tests with verbose output
echo "=== Running Test Suite ==="
npm test -- --run --reporter=verbose 2>&1 | tee /tmp/test-results.log

# Extract summary
echo ""
echo "=== Test Summary ==="
tail -50 /tmp/test-results.log | grep -E "(Test Files|Tests|passed|failed|PASS|FAIL|:check_mark:|×)" || echo "No summary found"

# Exit with test exit code
exit ${PIPESTATUS[0]}

