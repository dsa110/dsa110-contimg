#!/bin/bash
# Pre-commit hook to detect command output suppression
# Warns about 2>/dev/null, >/dev/null, &>/dev/null patterns

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Check staged files for output suppression patterns
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM || true)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Patterns that indicate output suppression
SUPPRESSION_PATTERNS=(
    "2>/dev/null"
    ">/dev/null"
    "&>/dev/null"
)

FOUND_ISSUES=0

for file in $STAGED_FILES; do
    # Only check shell scripts
    if [[ "$file" =~ \.(sh)$ ]]; then
        for pattern in "${SUPPRESSION_PATTERNS[@]}"; do
            # Check if pattern appears (but allow comments and explicit exceptions)
            if git diff --cached "$file" 2>/dev/null | grep -E "(^\+.*$pattern)" | grep -v "#.*$pattern" | grep -v "Exception:" | grep -v "explicitly" >/dev/null 2>&1; then
                echo "WARNING: Found output suppression pattern in $file:" >&2
                echo "  Pattern: $pattern" >&2
                git diff --cached "$file" 2>/dev/null | grep -E "(^\+.*$pattern)" | grep -v "#.*$pattern" | head -3 >&2
                echo "" >&2
                echo "This project requires full output for error detection." >&2
                echo "If you really need to suppress output, add a comment explaining why." >&2
                echo "See .cursor/rules/command-output-handling.mdc for details." >&2
                echo "" >&2
                FOUND_ISSUES=1
            fi
        done
    fi
done

if [ $FOUND_ISSUES -eq 1 ]; then
    echo "ERROR: Found output suppression patterns in staged files!" >&2
    echo "Please review and add comments if suppression is truly necessary." >&2
    exit 1
fi

exit 0

