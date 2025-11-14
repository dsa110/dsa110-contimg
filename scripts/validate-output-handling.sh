#!/bin/bash
# Script to validate that output handling follows rules
# Checks for violations of output-suppression rules

set -euo pipefail

VIOLATIONS=0

check_file() {
    local file="$1"
    local line_num=0
    
    while IFS= read -r line; do
        line_num=$((line_num + 1))
        
        # Check for forbidden patterns
        if echo "$line" | grep -qE "2>/dev/null|>/dev/null|&>/dev/null"; then
            # Check if there's an exception comment on this line or previous line
            # Look for exception keywords in comments
            local prev_line=""
            if [ $line_num -gt 1 ]; then
                prev_line=$(sed -n "$((line_num - 1))p" "$file" 2>/dev/null || echo "")
            fi
            
            # Check if exception is documented
            if echo "$line" | grep -qE "#.*exception|#.*acceptable|#.*Note:" || \
               echo "$prev_line" | grep -qE "#.*exception|#.*acceptable|#.*Note:"; then
                # Exception documented, skip
                continue
            fi
            
            echo "❌ VIOLATION in $file:$line_num: Suppression detected"
            echo "   $line"
            echo "   Hint: Add a comment explaining why suppression is acceptable (e.g., '# Note: exception for...')"
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
        
        # Check for 2>&1 used for suppression (not with tee or pipe to command)
        # Allow 2>&1 with tee or pipe to commands (combining streams is OK)
        if echo "$line" | grep -qE "2>&1.*>.*dev/null|2>&1.*>/dev/null"; then
            # Skip if it's a comment explaining the exception
            if ! echo "$line" | grep -qE "#.*exception|#.*acceptable|#.*Note:"; then
                echo "❌ VIOLATION in $file:$line_num: 2>&1 used for suppression"
                echo "   $line"
                echo "   Hint: 2>&1 is only allowed when combining streams (e.g., with tee)"
                VIOLATIONS=$((VIOLATIONS + 1))
            fi
        fi
        
        # Check for filtering without explicit request
        if echo "$line" | grep -qE "\| grep -v|\| grep.*-v"; then
            # Allow if commented or explicitly documented
            if ! echo "$line" | grep -qE "#.*grep -v|#.*filter"; then
                echo "⚠️  WARNING in $file:$line_num: Output filtering detected"
                echo "   $line"
                echo "   (May be OK if explicitly requested)"
            fi
        fi
        
        # Check for head/tail truncation without explicit request
        if echo "$line" | grep -qE "\| head|\| tail"; then
            if ! echo "$line" | grep -qE "#.*head|#.*tail|#.*truncate"; then
                echo "⚠️  WARNING in $file:$line_num: Output truncation detected"
                echo "   $line"
                echo "   (May be OK if explicitly requested)"
            fi
        fi
    done < "$file"
}

echo "Checking output handling rules..."
echo ""

# Check all shell scripts
find scripts -name "*.sh" -type f | while read -r file; do
    if [ -f "$file" ]; then
        check_file "$file"
    fi
done

# Check Python scripts for subprocess calls
find scripts -name "*.py" -type f | while read -r file; do
    if [ -f "$file" ]; then
        # Check for subprocess calls that might suppress output
        if grep -q "subprocess\|Popen\|call\|run" "$file"; then
            if grep -q "stdout.*devnull\|stderr.*devnull\|PIPE.*devnull" "$file"; then
                echo "❌ VIOLATION in $file: Python subprocess suppressing output"
                grep -n "devnull\|PIPE" "$file" | head -5
                VIOLATIONS=$((VIOLATIONS + 1))
            fi
        fi
    fi
done

echo ""
if [ $VIOLATIONS -eq 0 ]; then
    echo "✅ No violations found!"
    exit 0
else
    echo "❌ Found $VIOLATIONS violation(s)"
    exit 1
fi

