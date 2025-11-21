#!/bin/bash
# Audit all output suppression patterns in codebase
# Categorizes them for whitelist creation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Auditing output suppression patterns in codebase..."
echo ""

# Find all suppression patterns
PATTERNS=("2>/dev/null" ">/dev/null" "&>/dev/null")

TOTAL_COUNT=0
BY_CATEGORY=()

for pattern in "${PATTERNS[@]}"; do
    echo "Searching for: $pattern"
    
    # Find all occurrences
    while IFS=: read -r file line_num line_content; do
        TOTAL_COUNT=$((TOTAL_COUNT + 1))
        
        # Categorize based on context
        CATEGORY="unknown"
        REASON=""
        
        # Check if it's a comment
        if [[ "$line_content" =~ ^[[:space:]]*# ]]; then
            CATEGORY="comment"
            REASON="In comment, not actual suppression"
        # Check for error detection infrastructure
        elif [[ "$file" == *"error-detection"* ]] || [[ "$file" == *"developer-setup"* ]]; then
            CATEGORY="error-detection"
            REASON="Error detection infrastructure - suppresses wrapper errors"
        # Check for environment checks
        elif [[ "$line_content" == *"test"* ]] && [[ "$line_content" == *"-x"* ]] || [[ "$line_content" == *"test"* ]] && [[ "$line_content" == *"-f"* ]]; then
            CATEGORY="optional-check"
            REASON="Optional feature detection - suppresses command-not-found"
        # Check for cleanup scripts
        elif [[ "$file" == *"cleanup"* ]] || [[ "$file" == *"clean"* ]]; then
            CATEGORY="cleanup"
            REASON="Cleanup script - suppresses permission errors"
        # Check for infrastructure
        elif [[ "$file" == *"setup"* ]] || [[ "$file" == *"install"* ]] || [[ "$file" == *"wrapper"* ]]; then
            CATEGORY="infrastructure"
            REASON="Infrastructure script - suppresses setup errors"
        else
            CATEGORY="needs-review"
            REASON="Needs manual review"
        fi
        
        echo "  $file:$line_num [$CATEGORY] $line_content"
        
        # Track by category
        if [ -z "${BY_CATEGORY[$CATEGORY]}" ]; then
            BY_CATEGORY[$CATEGORY]=0
        fi
        BY_CATEGORY[$CATEGORY]=$((${BY_CATEGORY[$CATEGORY]} + 1))
        
    done < <(grep -rn "$pattern" --include="*.sh" . 2>/dev/null | grep -v ".git" | grep -v "node_modules" | head -100)
    
    echo ""
done

echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Total suppressions found: $TOTAL_COUNT"
echo ""
echo "By category:"
for category in "${!BY_CATEGORY[@]}"; do
    echo "  $category: ${BY_CATEGORY[$category]}"
done
echo ""
echo "Next steps:"
echo "  1. Review 'needs-review' category"
echo "  2. Create .output-suppression-whitelist"
echo "  3. Update pre-commit hook to use whitelist"
echo ""

