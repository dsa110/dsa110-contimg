#!/bin/bash
# Pre-commit hook to detect system Python usage in scripts
# Prevents committing scripts that use system Python instead of casa6

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Check staged files for problematic Python usage
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM || true)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

FOUND_ISSUES=0

for file in $STAGED_FILES; do
    # Only check shell scripts and Makefiles
    if [[ "$file" =~ \.(sh|makefile|Makefile)$ ]] || [[ "$file" == "Makefile" ]]; then
        # Check for system Python usage (not casa6)
        if git diff --cached "$file" 2>/dev/null | grep -E "(^\+.*\bpython\s|^\+.*\bpython3\s)" | grep -v "casa6" | grep -v "CASA6_PYTHON" | grep -v "python-wrapper" | grep -v "#.*python" >/dev/null 2>&1; then
            echo "WARNING: Found potential system Python usage in $file:" >&2
            git diff --cached "$file" 2>/dev/null | grep -E "(^\+.*\bpython\s|^\+.*\bpython3\s)" | grep -v "casa6" | grep -v "CASA6_PYTHON" | grep -v "python-wrapper" | grep -v "#.*python" | head -5 >&2
            echo "" >&2
            echo "This project REQUIRES casa6 Python. Use one of:" >&2
            echo "  - /opt/miniforge/envs/casa6/bin/python" >&2
            echo "  - \$(CASA6_PYTHON) (in Makefiles)" >&2
            echo "  - PYTHON_BIN variable (in scripts)" >&2
            echo "  - python-wrapper.sh (automatic redirection)" >&2
            echo "" >&2
            FOUND_ISSUES=1
        fi
    fi
done

if [ $FOUND_ISSUES -eq 1 ]; then
    echo "ERROR: Found system Python usage in staged files!" >&2
    echo "Please use casa6 Python as documented in docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md" >&2
    exit 1
fi

exit 0

