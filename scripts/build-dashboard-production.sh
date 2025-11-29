#!/bin/bash
# Build the frontend dashboard for production
# Called by dsa110-contimg-dashboard.service ExecStartPre

set -e

cd /data/dsa110-contimg/frontend

# Use scratch SSD for faster builds
export TMPDIR=/scratch

# Ensure node is available
export PATH="/opt/miniforge/envs/casa6/bin:$PATH"

# Increase Node.js memory limit for large builds
export NODE_OPTIONS="--max-old-space-size=4096"

echo "Building frontend for production..."
npm run build:no-check

echo "Build complete: $(ls -la dist/index.html 2>/dev/null || echo 'dist not found')"  # suppress-output-check
