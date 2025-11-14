#!/bin/bash
# Production build script for DSA-110 Dashboard
# Builds the frontend and prepares it for production serving

set -euo pipefail

# Strict timeout: 15 minutes (900 seconds) for production build
BUILD_TIMEOUT=900

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
BUILD_DIR="${FRONTEND_DIR}/dist"
LOG_DIR="${PROJECT_ROOT}/state/logs"

# Casa6 environment paths
CASA6_BIN="/opt/miniforge/envs/casa6/bin"
CASA6_NODE="${CASA6_BIN}/node"
CASA6_NPM_SCRIPT="/opt/miniforge/envs/casa6/lib/node_modules/npm/bin/npm-cli.js"

# Verify casa6 environment
if [[ ! -x "${CASA6_NODE}" ]]; then
    echo "ERROR: casa6 node not found at ${CASA6_NODE}" >&2
    exit 1
fi

if [[ ! -f "${CASA6_NPM_SCRIPT}" ]]; then
    echo "ERROR: casa6 npm script not found at ${CASA6_NPM_SCRIPT}" >&2
    exit 1
fi

# Verify Node.js version
NODE_VERSION=$("${CASA6_NODE}" --version)
echo "Using Node.js: ${NODE_VERSION} from ${CASA6_NODE}"

# Helper to invoke npm via casa6's node directly
NPM_CMD=("${CASA6_NODE}" "${CASA6_NPM_SCRIPT}")

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

cd "${FRONTEND_DIR}"

echo "Building DSA-110 Dashboard for production..."
echo "Build started at: $(date)"

# Clean previous build
if [[ -d "${BUILD_DIR}" ]]; then
    echo "Cleaning previous build..."
    if rm -rf "${BUILD_DIR}"; then
        echo "Previous build cleaned successfully"
    else
        echo "Warning: Could not remove ${BUILD_DIR}, attempting to clear contents..."
        find "${BUILD_DIR}" -mindepth 1 -delete || true
    fi
fi

# Ensure build directory exists and has correct permissions
mkdir -p "${BUILD_DIR}"
chmod 755 "${BUILD_DIR}" || true

# Install dependencies if needed
if [[ ! -d "node_modules" ]] || [[ "package.json" -nt "node_modules" ]]; then
    echo "Installing/updating dependencies..."
    "${NPM_CMD[@]}" ci --production=false
fi

# Build for production
# Type checking is included to catch errors before production deployment
echo "Running production build with type checking..."
echo "Build timeout: ${BUILD_TIMEOUT} seconds (30 minutes)"
# Increase Node.js heap size to prevent OOM during build
export NODE_OPTIONS="--max-old-space-size=4096"
# Set PATH to ensure all child processes (like vite) use casa6's node
export PATH="${CASA6_BIN}:${PATH}"

# Run build with strict timeout
if timeout "${BUILD_TIMEOUT}" env NODE_ENV=production "${NPM_CMD[@]}" run build; then
    echo "Build completed within timeout"
else
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 124 ]]; then
        echo "ERROR: Build timed out after ${BUILD_TIMEOUT} seconds" >&2
        echo "This may indicate a build hang or performance issue" >&2
    else
        echo "ERROR: Build failed with exit code ${EXIT_CODE}" >&2
    fi
    exit $EXIT_CODE
fi

# Verify build output
if [[ ! -d "${BUILD_DIR}" ]] || [[ -z "$(ls -A "${BUILD_DIR}")" ]]; then
    echo "ERROR: Build failed - dist directory is empty or missing" >&2
    exit 1
fi

echo "Build completed successfully at: $(date)"
echo "Build output: ${BUILD_DIR}"
echo "Build size: $(du -sh "${BUILD_DIR}" | cut -f1)"
