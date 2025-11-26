#!/usr/bin/env bash
# Wrapper script to ensure casa6 Python is used
# Usage: ./scripts/run-python.sh <script.py> [args...]

set -e

CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"

if [ ! -x "$CASA6_PYTHON" ]; then
  echo "Error: casa6 Python not found at $CASA6_PYTHON" >&2
  echo "  Please ensure casa6 environment is installed" >&2
  exit 1
fi

# Check if script exists
if [ $# -eq 0 ]; then
  echo "Usage: $0 <script.py> [args...]" >&2
  exit 1
fi

SCRIPT="$1"
shift

if [ ! -f "$SCRIPT" ]; then
  echo "Error: Script not found: $SCRIPT" >&2
  exit 1
fi

# Run with casa6 Python
exec "$CASA6_PYTHON" "$SCRIPT" "$@"

