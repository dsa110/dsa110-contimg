#!/bin/bash
# Auto Error Detection Environment Script
# This file is sourced by BASH_ENV for non-interactive shells
# It ensures error detection is always enabled

if [ -f "/data/dsa110-contimg/scripts/auto-error-detection.sh" ]; then
    source "/data/dsa110-contimg/scripts/auto-error-detection.sh" >/dev/null 2>&1
fi
