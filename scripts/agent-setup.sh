#!/bin/bash
# Agent Setup Script
# Source this at the start of any agentic session to ensure:
# 1. Error detection is enabled
# 2. casa6 environment is enforced for all Python operations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source casa6 environment enforcement FIRST (before error detection)
if [ -f "${SCRIPT_DIR}/casa6-env.sh" ]; then
    source "${SCRIPT_DIR}/casa6-env.sh"
    CASA6_STATUS="✅"
else
    echo "⚠️  WARNING: casa6-env.sh not found at ${SCRIPT_DIR}/casa6-env.sh" >&2
    CASA6_STATUS="❌"
fi

# Set BASH_ENV if not already set
if [ -z "${BASH_ENV:-}" ]; then
    export BASH_ENV="/data/dsa110-contimg/scripts/auto-error-detection-env.sh"
fi

# Source error detection if not already enabled
if [ -z "${AUTO_ERROR_DETECTION:-}" ]; then
    if [ -f "/data/dsa110-contimg/scripts/auto-error-detection.sh" ]; then
        source "/data/dsa110-contimg/scripts/auto-error-detection.sh" >/dev/null 2>&1
    fi
fi

echo "✅ Agent setup complete"
echo "   Error detection: ${AUTO_ERROR_DETECTION:-❌ not enabled}"
echo "   Casa6 enforcement: ${CASA6_ENV_ENFORCED:-❌ not enabled}"
echo "   Casa6 Python: ${CASA6_PYTHON:-❌ not set}"
echo "   BASH_ENV: ${BASH_ENV}"
