#!/bin/bash
# Validates output handling rules in shell scripts
# Ensures scripts don't suppress output without explicit justification
#
# See: .cursor/rules/output-suppression.mdc for rules
#
# Exit codes:
#   0 - All validations passed
#   1 - Violations found

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "Validating output handling in scripts..."
echo ""

VIOLATIONS=0
CHECKED_FILES=0

# Patterns that indicate output suppression
# Note: These pattern strings themselves are not violations (suppress-output-check)
SUPPRESSION_PATTERNS=(
    ">/dev/null"      # suppress-output-check
    "2>/dev/null"     # suppress-output-check
    "&>/dev/null"     # suppress-output-check
)

# Directories to exclude from validation
EXCLUDE_DIRS=(
    "*/archive/*"
    "*/node_modules/*"
    "*/.git/*"
    "*/ops/*"
    "*/.local/*"
)

# Build find exclusion arguments
FIND_EXCLUDES=""
for dir in "${EXCLUDE_DIRS[@]}"; do
    FIND_EXCLUDES="$FIND_EXCLUDES ! -path '$dir'"
done

# Find all shell scripts in scripts directory
while IFS= read -r file; do
    CHECKED_FILES=$((CHECKED_FILES + 1))
    FILE_VIOLATIONS=0
    
    for pattern in "${SUPPRESSION_PATTERNS[@]}"; do
        # Find lines with suppression pattern
        while IFS=: read -r line_num content; do
            # Skip empty results
            [ -z "$line_num" ] && continue
            
            # Skip if line is a comment
            trimmed="${content#"${content%%[![:space:]]*}"}"
            if [[ "$trimmed" == "#"* ]]; then
                continue
            fi
            
            # Skip if line has explicit exception marker
            if [[ "$content" == *"# Exception:"* ]] || \
               [[ "$content" == *"# Allowed:"* ]] || \
               [[ "$content" == *"# Justified:"* ]] || \
               [[ "$content" == *"# EXCEPTION:"* ]] || \
               [[ "$content" == *"# suppress-output-check"* ]]; then
                continue
            fi
            
            # This is a violation
            if [ $FILE_VIOLATIONS -eq 0 ]; then
                echo ":cross: Violations in: $file"
            fi
            echo "   Line $line_num: $content"
            FILE_VIOLATIONS=$((FILE_VIOLATIONS + 1))
            VIOLATIONS=$((VIOLATIONS + 1))
            
        done < <(grep -n "$pattern" "$file" 2>/dev/null || true)  # Exception: grep may find nothing
    done
    
    if [ $FILE_VIOLATIONS -gt 0 ]; then
        echo ""
    fi
    
done < <(eval "find scripts -name '*.sh' -type f $FIND_EXCLUDES 2>/dev/null")  # Exception: find exclusions

echo "----------------------------------------"
echo "Checked $CHECKED_FILES script(s)"

if [ $VIOLATIONS -gt 0 ]; then
    echo ""
    echo "Found $VIOLATIONS violation(s)"
    echo ""
    echo "To fix violations, either:"
    echo "  1. Remove the output suppression"
    echo "  2. Add a comment explaining why it's needed:"
    echo "     command 2>/dev/null  # Exception: <reason>"
    echo ""
    exit 1
fi

echo ":check: No output suppression violations found"
exit 0
