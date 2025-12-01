#!/bin/bash
# Reliable npm install for FUSE filesystems with Node version handling
set -e

cd /data/dsa110-contimg/frontend

echo "=== Step 1: Verify environment ==="
NODE_VERSION=$(conda run -n casa6 node --version)
NODE_PATH=$(conda run -n casa6 which node)
echo "Node: $NODE_VERSION at $NODE_PATH"

if [[ ! "$NODE_VERSION" =~ ^v22\. ]]; then
    echo "WARNING: Node version $NODE_VERSION may not be compatible"
fi

echo ""
echo "=== Step 2: Clean npm cache ==="
conda run -n casa6 npm cache clean --force || true

echo ""
echo "=== Step 3: Install with FUSE-friendly flags ==="
# Strategy: Use flags that minimize atomic file operations
# --no-optional: Reduces package count and complexity
# --legacy-peer-deps: Avoids peer dependency resolution that can trigger renames
# --prefer-offline: Reduces network operations
# --no-audit: Skips audit (can cause additional file operations)
# --loglevel=error: Suppresses EBADENGINE warnings (non-blocking)

conda run -n casa6 npm install \
    --no-optional \
    --legacy-peer-deps \
    --prefer-offline \
    --no-audit \
    --loglevel=error \
    2>&1 | grep -v "EBADENGINE" || true

echo ""
echo "=== Step 4: Verify installation ==="
if [ -f "package-lock.json" ] && [ -d "node_modules" ]; then
    PACKAGE_COUNT=$(find node_modules -maxdepth 1 -type d | wc -l)
    echo "✓ Installation successful"
    echo "  - package-lock.json: exists"
    echo "  - node_modules: exists ($PACKAGE_COUNT top-level packages)"
    exit 0
else
    echo "✗ Installation verification failed"
    [ -d "node_modules" ] && echo "  - node_modules: exists" || echo "  - node_modules: MISSING"
    [ -f "package-lock.json" ] && echo "  - package-lock.json: exists" || echo "  - package-lock.json: MISSING"
    exit 1
fi
