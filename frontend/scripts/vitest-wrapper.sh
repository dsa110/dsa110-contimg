#!/bin/bash
# Wrapper script for vitest that enforces casa6 Node.js
# Prevents direct vitest execution from bypassing checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Run casa6 Node.js check first
"$FRONTEND_DIR/scripts/check-casa6-node.sh"

# If check passes, run vitest with all arguments
exec vitest "$@"

