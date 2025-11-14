#!/bin/bash
# Safe pytest wrapper that prevents 2>&1 redirection issues
# This script sanitizes arguments and ensures proper redirection handling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"

# Filter out problematic redirection patterns from arguments
# This prevents 2>&1 from being passed as a test path to pytest
FILTERED_ARGS=()
REDIRECT_STDOUT=""
REDIRECT_STDERR=""
REDIRECT_BOTH=""

for arg in "$@"; do
    case "$arg" in
        "2>&1"|"2>&1|"*"2>&1"*)
            # Found 2>&1 in arguments - this is a redirection, not a test path
            # Convert to proper redirection handling
            REDIRECT_BOTH="2>&1"
            # Don't add to pytest args
            ;;
        ">"*|">>"*)
            # Found stdout redirection
            REDIRECT_STDOUT="$arg"
            # Don't add to pytest args
            ;;
        "2>"*|"2>>"*)
            # Found stderr redirection
            REDIRECT_STDERR="$arg"
            # Don't add to pytest args
            ;;
        *)
            # Normal argument - pass through
            FILTERED_ARGS+=("$arg")
            ;;
    esac
done

# Check if any problematic patterns remain (shouldn't happen, but double-check)
for arg in "${FILTERED_ARGS[@]}"; do
    if [[ "$arg" == *"2>&1"* ]] && [[ "$arg" != "--"* ]]; then
        echo "ERROR: Detected '2>&1' in pytest arguments: $arg" >&2
        echo "This is likely a shell redirection issue." >&2
        echo "" >&2
        echo "Use this script instead, or use proper shell redirection:" >&2
        echo "  $0 tests/ -v 2>&1 | tail" >&2
        echo "  $0 tests/ -v > output.log 2>&1" >&2
        exit 1
    fi
done

# Build pytest command
PYTEST_CMD=("$PYTHON_BIN" "-m" "pytest" "${FILTERED_ARGS[@]}")

# Execute with proper redirection if specified
if [ -n "$REDIRECT_BOTH" ]; then
    # Both stdout and stderr redirected
    "${PYTEST_CMD[@]}" 2>&1
elif [ -n "$REDIRECT_STDOUT" ] && [ -n "$REDIRECT_STDERR" ]; then
    # Both specified separately
    "${PYTEST_CMD[@]}" "$REDIRECT_STDOUT" "$REDIRECT_STDERR"
elif [ -n "$REDIRECT_STDOUT" ]; then
    # Only stdout
    "${PYTEST_CMD[@]}" "$REDIRECT_STDOUT"
elif [ -n "$REDIRECT_STDERR" ]; then
    # Only stderr
    "${PYTEST_CMD[@]}" "$REDIRECT_STDERR"
else
    # No redirection - execute normally
    "${PYTEST_CMD[@]}"
fi

