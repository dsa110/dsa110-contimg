#!/bin/bash
# Build verification script
# Verifies that the frontend can build without errors
# This catches import errors, type errors, and other build-time issues

set -e

echo "=========================================="
echo "Frontend Build Verification"
echo "=========================================="

cd "$(dirname "$0")/.."

# 1. Type checking
echo ""
echo "1. Type checking with TypeScript..."
npm run build -- --mode production 2>&1 | grep -E "(error|Error)" && exit 1 || true

# 2. Linting
echo ""
echo "2. Linting..."
npm run lint 2>&1 | grep -E "(error|Error)" && exit 1 || true

# 3. Test compilation (without running tests)
echo ""
echo "3. Verifying test files compile..."
npx tsc --noEmit --project tsconfig.json 2>&1 | grep -E "(error|Error)" && exit 1 || true

# 4. Check for missing dependencies
echo ""
echo "4. Checking for missing dependencies..."
if ! npm list dayjs > /dev/null 2>&1; then
  echo "ERROR: dayjs is not installed"
  exit 1
fi

# 5. Verify imports can be resolved
echo ""
echo "5. Verifying imports can be resolved..."
npx vite build --mode production > /dev/null 2>&1 || {
  echo "ERROR: Build failed - check for missing imports or type errors"
  exit 1
}

echo ""
echo "=========================================="
echo "✓ All build checks passed!"
echo "=========================================="

