#!/bin/bash
set -euo pipefail

# Wrapper helper for cron/CI/automation that ensures CASA log files land in the canonical
# state logs directory (the same behaviour as scripts/casa_wrapper.sh, but easier to reference
# from other scripts without repeating the wrapper invocation logic).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_PATH="$SCRIPT_DIR/casa_wrapper.sh"

if [[ $# -lt 1 ]]; then
    echo "Usage: $(basename "$0") <casa-binary-or-script> [args...]"
    echo "Example: $(basename "$0") /opt/miniforge/envs/casa6/bin/casapy myscript.py"
    exit 1
fi

exec "$WRAPPER_PATH" "$@"
