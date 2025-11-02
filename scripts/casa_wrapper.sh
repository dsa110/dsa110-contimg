#!/bin/bash
# Wrapper script that sets CASA log directory before running Python commands
# This ensures CASA writes logs to the correct location

# Set CASA log directory - CASA writes logs to current working directory
export CASA_LOG_DIR="${CASA_LOG_DIR:-/data/dsa110-contimg/state/logs}"
mkdir -p "$CASA_LOG_DIR"
cd "$CASA_LOG_DIR" || exit 1

# Execute the original command
exec "$@"

