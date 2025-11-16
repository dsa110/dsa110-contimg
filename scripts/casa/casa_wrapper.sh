#!/bin/bash
# Wrapper script that sets CASA log directory before running Python commands
# This ensures CASA writes logs to the correct location

# Safety check: warn if script location doesn't match expected path from contimg.env
if [ -n "${CONTIMG_CASA_WRAPPER}" ]; then
    # Get the actual script path (resolve symlinks)
    ACTUAL_SCRIPT="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
    EXPECTED_SCRIPT="$(readlink -f "${CONTIMG_CASA_WRAPPER}" 2>/dev/null || echo "${CONTIMG_CASA_WRAPPER}")"
    
    if [ "${ACTUAL_SCRIPT}" != "${EXPECTED_SCRIPT}" ]; then
        echo "WARNING: casa_wrapper.sh location mismatch!" >&2
        echo "  Expected: ${CONTIMG_CASA_WRAPPER}" >&2
        echo "  Actual:   ${ACTUAL_SCRIPT}" >&2
        echo "  Please update CONTIMG_CASA_WRAPPER in contimg.env and restart the service" >&2
    fi
    
    # Export the variable so it's available to child processes (like the API)
    export CONTIMG_CASA_WRAPPER
fi

# Set CASA log directory - CASA writes logs to current working directory
export CASA_LOG_DIR="${CASA_LOG_DIR:-/data/dsa110-contimg/state/logs}"
mkdir -p "$CASA_LOG_DIR"
cd "$CASA_LOG_DIR" || exit 1

# Execute the original command
exec "$@"

