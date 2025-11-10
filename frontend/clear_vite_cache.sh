#!/bin/sh
# Clear Vite cache (POSIX shell)
# Note: use sh to avoid Bash non-interactive BASH_ENV sourcing issues.

set -eu

# cd to the directory containing this script
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if [ -d "node_modules/.vite" ]; then
    rm -rf node_modules/.vite
    echo "Vite cache cleared successfully"
else
    echo "No Vite cache found (already cleared or doesn't exist)"
fi
