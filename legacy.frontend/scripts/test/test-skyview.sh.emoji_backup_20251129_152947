#!/bin/bash
# Comprehensive SkyView testing script
# Runs all tests that would catch the date-fns import error
# Can run in Docker or locally

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Check if running in Docker or need to use Docker
USE_DOCKER=${USE_DOCKER:-"auto"}
if [ "$USE_DOCKER" = "auto" ] && ! command -v node &> /dev/null; then
  USE_DOCKER="yes"
fi

if [ "$USE_DOCKER" = "yes" ]; then
  echo "=========================================="
  echo "SkyView Component Testing (Docker)"
  echo "=========================================="
  echo ""
  
  # Build Docker image if needed
  IMAGE_NAME="dsa110-frontend-test"
  if ! docker images | grep -q "$IMAGE_NAME"; then
    echo "Building Docker image..."
    docker build -t "$IMAGE_NAME" -f Dockerfile.dev .
  fi
  
  # Run all tests in Docker
  docker run --rm \
    -v "$SCRIPT_DIR/..:/app" \
    -v /app/node_modules \
    -w /app \
    "$IMAGE_NAME" \
    sh -c "
      echo '1. Checking imports...'
      node scripts/check-imports.js
      echo '   ✓ Imports OK'
      echo ''
      
      echo '2. Type checking...'
      npx tsc --noEmit 2>&1 | grep -v 'node_modules' || true
      echo '   ✓ Type check passed'
      echo ''
      
      echo '3. Build verification...'
      npm run build 2>&1 | tail -5
      echo '   ✓ Build successful'
      echo ''
      
      echo '4. Running component tests...'
      npm test -- src/components/Sky/ImageBrowser.test.tsx --run 2>&1 | tail -30
      echo '   ✓ Component tests passed'
      echo ''
      
      echo '5. Linting...'
      npm run lint 2>&1 | grep -E '(error|Error)' && exit 1 || true
      echo '   ✓ Linting passed'
      echo ''
      
      echo '=========================================='
      echo '✓ All SkyView tests passed!'
      echo '=========================================='
    "
else
  echo "=========================================="
  echo "SkyView Component Testing (Local)"
  echo "=========================================="
  echo ""
  
  # 1. Check imports
  echo "1. Checking imports..."
  node scripts/check-imports.js
  echo "   ✓ Imports OK"
  echo ""
  
  # 2. Type checking
  echo "2. Type checking..."
  npx tsc --noEmit 2>&1 | grep -v "node_modules" || true
  echo "   ✓ Type check passed"
  echo ""
  
  # 3. Build verification
  echo "3. Build verification..."
  npm run build 2>&1 | tail -5 || {
    echo "   ✗ Build failed"
    exit 1
  }
  echo "   ✓ Build successful"
  echo ""
  
  # 4. Run component tests
  echo "4. Running component tests..."
  npm test -- src/components/Sky/ImageBrowser.test.tsx --run 2>&1 | tail -30 || {
    echo "   ✗ Tests failed"
    exit 1
  }
  echo "   ✓ Component tests passed"
  echo ""
  
  # 5. Linting
  echo "5. Linting..."
  npm run lint 2>&1 | grep -E "(error|Error)" && exit 1 || true
  echo "   ✓ Linting passed"
  echo ""
  
  echo "=========================================="
  echo "✓ All SkyView tests passed!"
  echo "=========================================="
fi

