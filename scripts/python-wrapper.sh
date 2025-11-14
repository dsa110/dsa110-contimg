#!/bin/bash
# Python wrapper that enforces casa6 usage
# This script intercepts 'python' and 'python3' calls and redirects to casa6

# Get the actual command name (python or python3)
CMD_NAME=$(basename "$0")

# If called as 'python' or 'python3', redirect to casa6
if [ "$CMD_NAME" = "python" ] || [ "$CMD_NAME" = "python3" ]; then
    CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"
    
    if [ ! -x "$CASA6_PYTHON" ]; then
        echo "ERROR: casa6 Python not found at $CASA6_PYTHON" >&2
        echo "This project REQUIRES casa6 Python environment." >&2
        echo "System Python (3.6.9) lacks CASA dependencies and will cause failures." >&2
        exit 1
    fi
    
    # Execute with casa6 Python
    exec "$CASA6_PYTHON" "$@"
else
    # If called as something else, just pass through
    exec "$@"
fi

