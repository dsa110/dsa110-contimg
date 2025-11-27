#!/bin/bash
# Pre-commit hook validator for pytest usage
# Detects problematic pytest invocations that could cause 2>&1 errors

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Check staged files for problematic pytest patterns
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM || true)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Patterns that indicate problematic pytest usage
PROBLEMATIC_PATTERNS=(
    "pytest.*2>&1[^|]"
    "pytest.*2>&1[^>]"
    "-m pytest.*2>&1"
    "python.*pytest.*2>&1"
)

# Check staged files for problematic patterns
FOUND_ISSUES=0

for file in $STAGED_FILES; do
    # Only check shell scripts, Python files, and Makefiles
    if [[ "$file" =~ \.(sh|py|makefile|Makefile)$ ]] || [[ "$file" == "Makefile" ]]; then
        # Check file content for problematic patterns
        for pattern in "${PROBLEMATIC_PATTERNS[@]}"; do
            if git diff --cached "$file" 2>/dev/null | grep -E "$pattern" >/dev/null 2>&1; then
                echo "WARNING: Found potentially problematic pytest pattern in $file:" >&2
                echo "  Pattern: $pattern" >&2
                echo "  This may cause '2>&1' to be passed as a pytest argument." >&2
                echo "  Use scripts/pytest-safe.sh instead." >&2
                echo "" >&2
                FOUND_ISSUES=1
            fi
        done
    fi
done

if [ $FOUND_ISSUES -eq 1 ]; then
    echo "ERROR: Found problematic pytest usage patterns!" >&2
    echo "Please use scripts/pytest-safe.sh for pytest invocations." >&2
    echo "See docs/dev-notes/PYTEST_REDIRECTION_FIX.md for details." >&2
    exit 1
fi

exit 0

