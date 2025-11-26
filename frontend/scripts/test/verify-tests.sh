#!/bin/bash
# Test verification script with explicit output

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Test Verification Script ==="
echo "Date: $(date)"
echo ""

# Activate casa6
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

echo "Environment:"
echo "  Node: $(which node) ($(node --version))"
echo "  NPM: $(which npm) ($(npm --version))"
echo ""

# Test individual files
echo "=== Testing ImageBrowser ==="
npm test -- --run src/components/Sky/ImageBrowser.test.tsx --reporter=basic 2>&1 | tee /tmp/test-imagebrowser.log
echo ""

echo "=== Testing MSTable ==="
npm test -- --run src/components/MSTable.test.tsx --reporter=basic 2>&1 | tee /tmp/test-mstable.log
echo ""

echo "=== Testing DataBrowserPage ==="
npm test -- --run src/pages/DataBrowserPage.test.tsx --reporter=basic 2>&1 | tee /tmp/test-databrowser.log
echo ""

echo "=== Testing PhotometryPlugin ==="
npm test -- --run src/components/Sky/plugins/PhotometryPlugin.test.tsx --reporter=basic 2>&1 | tee /tmp/test-photometry.log
echo ""

echo "=== Running Full Test Suite ==="
npm test -- --run --reporter=basic 2>&1 | tee /tmp/test-full.log
echo ""

echo "=== Summary ==="
echo "Check log files in /tmp/test-*.log"

