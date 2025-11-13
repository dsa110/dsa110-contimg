#!/bin/bash
# Ensure Error Detection Script
# This script ensures error detection is enabled by setting BASH_ENV
# Can be sourced or executed to set up the environment

export BASH_ENV="/data/dsa110-contimg/scripts/auto-error-detection-env.sh"

# Also source it now if we're in an interactive shell
if [ -n "${PS1:-}" ] || [ "${-}" = *i* ]; then
    if [ -f "/data/dsa110-contimg/scripts/auto-error-detection.sh" ]; then
        source "/data/dsa110-contimg/scripts/auto-error-detection.sh" >/dev/null 2>&1
    fi
fi
