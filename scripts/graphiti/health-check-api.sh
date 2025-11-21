#!/bin/bash
# Health check script for DSA-110 API service
# Returns 0 if healthy, non-zero if unhealthy

set -euo pipefail

API_PORT="${CONTIMG_API_PORT:-8000}"
HEALTH_URL="http://localhost:${API_PORT}/health"
TIMEOUT=5

# Check if API is responding
if curl -f -s --max-time "${TIMEOUT}" "${HEALTH_URL}" > /dev/null 2>&1; then
    exit 0
else
    echo "Health check failed: API not responding at ${HEALTH_URL}" >&2
    exit 1
fi

