#!/bin/bash
# Pre-commit hook to STRICTLY block output suppression patterns
# Version: Strict (100% prevention with whitelist)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Whitelist file for legitimate exceptions
WHITELIST_FILE="$PROJECT_ROOT/.output-suppression-whitelist"

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
BLOCKED_FILES=()

for file in $STAGED_FILES; do
    # Only check shell scripts
    if [[ "$file" =~ \.(sh)$ ]]; then
        # Get line numbers of added/changed lines with suppression patterns
        while IFS=: read -r line_num line_content; do
            # Skip if line is a comment
            if [[ "$line_content" =~ ^[[:space:]]*# ]]; then
                continue
            fi
            
            # Check each suppression pattern
            for pattern in "${SUPPRESSION_PATTERNS[@]}"; do
                if [[ "$line_content" == *"$pattern"* ]]; then
                    # Check if this is whitelisted
                    IS_WHITELISTED=0
                    if [ -f "$WHITELIST_FILE" ]; then
                        # Check if file:line is in whitelist
                        if grep -qE "^${file}:${line_num}:" "$WHITELIST_FILE" 2>/dev/null; then
                            IS_WHITELISTED=1
                        fi
                    fi
                    
                    if [ $IS_WHITELISTED -eq 0 ]; then
                        echo "ERROR: Found output suppression pattern in $file:${line_num}:" >&2
                        echo "  Pattern: $pattern" >&2
                        echo "  Line: $line_content" >&2
                        echo "" >&2
                        echo "This project requires full output for error detection." >&2
                        echo "" >&2
                        echo "To allow this exception, add to .output-suppression-whitelist:" >&2
                        echo "  $file:$line_num:category:reason" >&2
                        echo "" >&2
                        echo "Categories: infrastructure, error-detection, optional-check, cleanup" >&2
                        echo "See docs/dev/OUTPUT_SUPPRESSION_EXCEPTIONS.md for details." >&2
                        echo "" >&2
                        FOUND_ISSUES=1
                        BLOCKED_FILES+=("$file:$line_num")
                    fi
                fi
            done
        done < <(git diff --cached "$file" 2>/dev/null | grep -E "^\+" | grep -v "^+++" | sed 's/^+//' | nl -ba -v "$(git diff --cached "$file" 2>/dev/null | grep -E "^@@" | head -1 | sed 's/.*+\([0-9]*\).*/\1/')" | awk '{print $1":"$0}' | sed 's/^[0-9]*://')
    fi
done

if [ $FOUND_ISSUES -eq 1 ]; then
    echo "==========================================" >&2
    echo "BLOCKED: Output suppression patterns found" >&2
    echo "==========================================" >&2
    echo "" >&2
    echo "Files with issues:" >&2
    for blocked in "${BLOCKED_FILES[@]}"; do
        echo "  - $blocked" >&2
    done
    echo "" >&2
    echo "To fix:" >&2
    echo "  1. Remove the suppression pattern, OR" >&2
    echo "  2. Add to .output-suppression-whitelist with justification" >&2
    echo "" >&2
    echo "See docs/dev/OUTPUT_SUPPRESSION_TO_100_PERCENT.md for details." >&2
    exit 1
fi

exit 0

