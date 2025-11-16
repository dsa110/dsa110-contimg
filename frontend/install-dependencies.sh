#!/bin/bash
# Reliable npm install for FUSE filesystems
set -e

cd /data/dsa110-contimg/frontend

echo "Cleaning npm cache..."
conda run -n casa6 npm cache clean --force

echo "Installing dependencies with FUSE-friendly flags..."
# --no-optional: Reduces complexity and atomic operations
# --legacy-peer-deps: Avoids peer dependency resolution issues  
# --prefer-offline: Reduces network operations
# --loglevel=error: Suppresses warnings (EBADENGINE is just a warning)
conda run -n casa6 npm install \
    --no-optional \
    --legacy-peer-deps \
    --prefer-offline \
    --loglevel=error \
    2>&1 | grep -v "EBADENGINE" || true

if [ -f "package-lock.json" ] && [ -d "node_modules" ]; then
    echo "✓ Installation successful"
    exit 0
else
    echo "✗ Installation may have failed - checking..."
    [ -d "node_modules" ] && echo "  node_modules exists" || echo "  node_modules missing"
    [ -f "package-lock.json" ] && echo "  package-lock.json exists" || echo "  package-lock.json missing"
    exit 1
fi
