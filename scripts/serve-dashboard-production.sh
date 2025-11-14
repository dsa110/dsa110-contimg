#!/bin/bash
# Production serve script for DSA-110 Dashboard
# Serves the built frontend using Python's http.server

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
BUILD_DIR="${FRONTEND_DIR}/dist"

# Use casa6 Python
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"

# Get port from environment or use default
PORT="${CONTIMG_DASHBOARD_PORT:-3210}"

# Verify build exists
if [[ ! -d "${BUILD_DIR}" ]] || [[ -z "$(ls -A "${BUILD_DIR}")" ]]; then
    echo "ERROR: Build directory not found or empty: ${BUILD_DIR}" >&2
    echo "Run build-dashboard-production.sh first" >&2
    exit 1
fi

# Verify Python is available
if [[ ! -x "${CASA6_PYTHON}" ]]; then
    echo "ERROR: casa6 Python not found at ${CASA6_PYTHON}" >&2
    exit 1
fi

echo "Serving DSA-110 Dashboard on port ${PORT}..."
echo "Serving from: ${BUILD_DIR}"

# Use custom dashboard server that handles /ui/ base path
# The production build expects to be served at /ui/, and this server
# properly rewrites paths to support that
exec "${CASA6_PYTHON}" "${SCRIPT_DIR}/dashboard_server.py" --port "${PORT}" --directory "${BUILD_DIR}"

