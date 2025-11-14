#!/bin/bash
# Agent Setup Script
# Source this at the start of any agentic session to ensure error detection is enabled

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

echo "✅ Error detection enabled for agentic session"
echo "   BASH_ENV=${BASH_ENV}"
echo "   AUTO_ERROR_DETECTION=${AUTO_ERROR_DETECTION:-not set}"
