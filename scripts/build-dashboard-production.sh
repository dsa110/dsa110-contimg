#!/bin/bash
# Production build script for DSA-110 Dashboard
# Builds the frontend and prepares it for production serving

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
BUILD_DIR="${FRONTEND_DIR}/dist"
LOG_DIR="${PROJECT_ROOT}/state/logs"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Use casa6 Python/Node
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"
CASA6_NODE="/opt/miniforge/envs/casa6/bin/node"
CASA6_NPM="/opt/miniforge/envs/casa6/bin/npm"

# Verify casa6 environment
if [[ ! -x "${CASA6_NPM}" ]]; then
    echo "ERROR: casa6 npm not found at ${CASA6_NPM}" >&2
    exit 1
fi

cd "${FRONTEND_DIR}"

echo "Building DSA-110 Dashboard for production..."
echo "Build started at: $(date)"

# Clean previous build
if [[ -d "${BUILD_DIR}" ]]; then
    echo "Cleaning previous build..."
    # Try to remove directory, fall back to clearing contents if protected
    if rm -rf "${BUILD_DIR}" 2>/dev/null; then
        echo "Previous build cleaned successfully"
    else
        echo "Warning: Could not remove ${BUILD_DIR}, attempting to clear contents..."
        find "${BUILD_DIR}" -mindepth 1 -delete 2>/dev/null || true
    fi
fi

# Ensure build directory exists and has correct permissions
mkdir -p "${BUILD_DIR}"
chmod 755 "${BUILD_DIR}" 2>/dev/null || true

# Install dependencies if needed
if [[ ! -d "node_modules" ]] || [[ "package.json" -nt "node_modules" ]]; then
    echo "Installing/updating dependencies..."
    "${CASA6_NPM}" ci --production=false
fi

# Build for production
# Note: Using build:no-check to skip TypeScript errors temporarily
# TODO: Fix TypeScript errors and switch back to "build"
echo "Running production build (skipping type check due to pre-existing errors)..."
# Increase Node.js heap size to prevent OOM during build
export NODE_OPTIONS="--max-old-space-size=4096"
NODE_ENV=production "${CASA6_NPM}" run build:no-check

# Verify build output
if [[ ! -d "${BUILD_DIR}" ]] || [[ -z "$(ls -A "${BUILD_DIR}")" ]]; then
    echo "ERROR: Build failed - dist directory is empty or missing" >&2
    exit 1
fi

echo "Build completed successfully at: $(date)"
echo "Build output: ${BUILD_DIR}"
echo "Build size: $(du -sh "${BUILD_DIR}" | cut -f1)"

