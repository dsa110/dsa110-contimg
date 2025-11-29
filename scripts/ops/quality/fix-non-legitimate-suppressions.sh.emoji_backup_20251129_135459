#!/bin/bash
# Script to identify and suggest fixes for non-legitimate output suppressions
# This helps identify suppressions that should be removed or fixed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

WHITELIST_FILE="$PROJECT_ROOT/.output-suppression-whitelist"

echo "Identifying non-legitimate output suppressions..."
echo ""

# Find all suppressions
PATTERNS=("2>/dev/null" ">/dev/null" "&>/dev/null")

FOUND_ISSUES=0
FIXES_NEEDED=()

for pattern in "${PATTERNS[@]}"; do
    # Find all occurrences in shell scripts
    while IFS=: read -r file line_num line_content; do
        # Skip if it's a comment
        if [[ "$line_content" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        # Skip if it's in the whitelist
        if [ -f "$WHITELIST_FILE" ]; then
            if grep -qE "^${file}:${line_num}:" "$WHITELIST_FILE" 2>/dev/null; then
                continue
            fi
        fi
        
        # Check for common problematic patterns
        ISSUE_TYPE=""
        SUGGESTED_FIX=""
        
        # Pattern 1: Test output suppression
        if [[ "$line_content" == *"pytest"* ]] || [[ "$line_content" == *"test"* ]] && [[ "$line_content" == *"$pattern"* ]]; then
            ISSUE_TYPE="test-output"
            SUGGESTED_FIX="Use ./scripts/pytest-safe.sh instead of suppressing test output"
        # Pattern 2: Log file creation suppression
        elif [[ "$line_content" == *">"* ]] && [[ "$line_content" == *"log"* ]] && [[ "$line_content" == *"$pattern"* ]]; then
            ISSUE_TYPE="log-creation"
            SUGGESTED_FIX="Handle errors explicitly: if ! echo 'log' > logfile.txt 2>&1; then echo 'ERROR: Failed to create log' >&2; exit 1; fi"
        # Pattern 3: Error hiding in production code
        elif [[ "$line_content" =~ ^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*.*\$pattern ]] && [[ "$file" != *"test"* ]] && [[ "$file" != *"example"* ]]; then
            ISSUE_TYPE="error-hiding"
            SUGGESTED_FIX="Remove suppression and handle errors properly with explicit error checking"
        fi
        
        if [ -n "$ISSUE_TYPE" ]; then
            echo "ISSUE: $file:$line_num [$ISSUE_TYPE]"
            echo "  Line: $line_content"
            echo "  Fix: $SUGGESTED_FIX"
            echo ""
            FOUND_ISSUES=$((FOUND_ISSUES + 1))
            FIXES_NEEDED+=("$file:$line_num:$ISSUE_TYPE")
        fi
        
    done < <(grep -rn "$pattern" --include="*.sh" . 2>/dev/null | grep -v ".git" | grep -v "node_modules" | grep -v ".output-suppression-whitelist" | head -50)
done

if [ $FOUND_ISSUES -eq 0 ]; then
    echo ":check: No obvious non-legitimate suppressions found"
    echo "  (All suppressions are either whitelisted or need manual review)"
else
    echo "=========================================="
    echo "Summary: $FOUND_ISSUES issues found"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  1. Review each issue above"
    echo "  2. Apply suggested fixes"
    echo "  3. Or add to whitelist if legitimate"
    echo ""
fi

