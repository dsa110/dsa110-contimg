#!/bin/bash
# Health check script for DSA-110 Dashboard service
# Returns 0 if healthy, non-zero if unhealthy

set -euo pipefail

DASHBOARD_PORT="${CONTIMG_DASHBOARD_PORT:-3210}"
HEALTH_URL="http://localhost:${DASHBOARD_PORT}/index.html"
TIMEOUT=5

# Check if dashboard is serving files
if curl -f -s --max-time "${TIMEOUT}" "${HEALTH_URL}" > /dev/null 2>&1; then
    exit 0
else
    echo "Health check failed: Dashboard not responding at ${HEALTH_URL}" >&2
    exit 1
fi

