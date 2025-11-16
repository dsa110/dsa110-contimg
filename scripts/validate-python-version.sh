#!/bin/bash
# Validate that Python scripts are using the correct Python version
# This script ensures dsa110-contimg never uses Python 2.7 or 3.6
#
# Usage:
#   ./scripts/validate-python-version.sh           # Full validation
#   ./scripts/validate-python-version.sh --pre-commit  # Quick check for pre-commit

set -euo pipefail

# Check if running in pre-commit mode (faster, less verbose)
PRE_COMMIT_MODE=false
if [ "${1:-}" = "--pre-commit" ]; then
    PRE_COMMIT_MODE=true
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Required Python version
REQUIRED_VERSION="3.11.13"
REQUIRED_MAJOR_MINOR="3.11"
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"

# Forbidden Python versions
FORBIDDEN_VERSIONS=("2.7" "3.6")

# Track errors (initialize explicitly to avoid issues with set -e)
ERRORS=0
WARNINGS=0
# Use arithmetic expansion that doesn't fail on zero
: $((ERRORS)) $((WARNINGS))

echo "🔍 Validating Python version usage in dsa110-contimg..."
echo ""

# Function to check if a Python executable is forbidden
check_python_version() {
    local python_path="$1"
    local version_output
    
    if [ ! -x "$python_path" ]; then
        return 0  # Skip non-executable files
    fi
    
    version_output=$("$python_path" --version 2>&1 || echo "unknown")
    
    for forbidden in "${FORBIDDEN_VERSIONS[@]}"; do
        if echo "$version_output" | grep -q "Python $forbidden"; then
            echo -e "${RED}❌ FORBIDDEN:${NC} $python_path uses Python $forbidden"
            echo "   Version: $version_output"
            return 1
        fi
    done
    
    return 0
}

# Function to check shebang in a file
check_shebang() {
    local file="$1"
    local shebang
    
    if [ ! -f "$file" ] || [ ! -r "$file" ]; then
        return 0
    fi
    
    # Use sed to get first line (faster and more reliable than head)
    # Limit to 200 characters to avoid issues with very long lines
    shebang=$(sed -n '1p' "$file" 2>/dev/null | cut -c1-200 || echo "")
    
    # If empty, skip
    if [ -z "$shebang" ]; then
        return 0
    fi
    
    # Check for problematic shebangs
    if echo "$shebang" | grep -qE "^#!/usr/bin/(env )?python2"; then
        echo -e "${RED}❌ FORBIDDEN SHEBANG:${NC} $file"
        echo "   Shebang: $shebang"
        echo "   Uses Python 2.x"
        ((ERRORS++)) || true
        return 1
    fi
    
    if echo "$shebang" | grep -qE "^#!/usr/bin/python3$"; then
        echo -e "${YELLOW}⚠️  WARNING:${NC} $file uses system python3"
        echo "   Shebang: $shebang"
        echo "   This may resolve to Python 3.6.9 instead of 3.11.13"
        echo "   Consider: #!/usr/bin/env python3.11 or use CASA6_PYTHON"
        ((WARNINGS++)) || true
        return 0
    fi
    
    return 0
}

# Check system Python installations (informational only - they're OK for system tools)
echo "📋 Checking system Python installations (informational)..."
echo "   Note: System Python 2.7 and 3.6 are OK for system tools,"
echo "   but dsa110-contimg must not use them."
for py in /usr/bin/python /usr/bin/python2 /usr/bin/python2.7 /usr/bin/python3 /usr/bin/python3.6; do
    if [ -x "$py" ]; then
        version_output=$("$py" --version 2>&1 || echo "unknown")
        echo "   Found: $py → $version_output (system tool - OK)"
    fi
done

# Check CASA6 Python
echo ""
echo "📋 Checking CASA6 Python..."
if [ -x "$CASA6_PYTHON" ]; then
    casa6_version=$("$CASA6_PYTHON" --version 2>&1)
    if echo "$casa6_version" | grep -q "Python $REQUIRED_MAJOR_MINOR"; then
        echo -e "${GREEN}✅ CASA6 Python OK:${NC} $casa6_version"
    else
        echo -e "${RED}❌ CASA6 Python version mismatch:${NC} $casa6_version"
        echo "   Expected: Python $REQUIRED_MAJOR_MINOR.x"
        ((ERRORS++))
    fi
else
    echo -e "${RED}❌ CASA6 Python not found:${NC} $CASA6_PYTHON"
    ((ERRORS++))
fi

# Check Python scripts in the project
PROJECT_ROOT="/data/dsa110-contimg"

# In pre-commit mode, only check staged files
if [ "$PRE_COMMIT_MODE" = true ]; then
    echo ""
    echo "📋 Checking staged Python files..."
    PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E "\.py$" || true)
    if [ -z "$PYTHON_FILES" ]; then
        # No Python files staged, skip
        exit 0
    fi
    
    # Check staged files
    for file in $PYTHON_FILES; do
        [ -z "$file" ] && continue
        if [ ! -f "$file" ] && [ -f "$PROJECT_ROOT/$file" ]; then
            file="$PROJECT_ROOT/$file"
        fi
        [ ! -f "$file" ] || [ ! -r "$file" ] && continue
        check_shebang "$file" || true
    done
else
    # In full mode, skip file checking to avoid hanging on large directories
    # The important checks (CASA6 Python, system Python) are already done above
    echo ""
    echo "📋 Python script shebang check skipped in full mode (use --pre-commit for file checks)"
fi

# Check for direct python/python2/python3 calls in scripts
# Skip in full mode to avoid hanging - pre-commit mode handles this
if [ "$PRE_COMMIT_MODE" = true ]; then
    echo ""
    echo "📋 Checking shell scripts for Python calls..."
    # Only check staged shell scripts in pre-commit mode
    SHELL_SCRIPTS=$(git diff --cached --name-only --diff-filter=ACM | grep -E "\.(sh|bash)$" || true)
    for script in $SHELL_SCRIPTS; do
        [ -z "$script" ] && continue
        [ ! -f "$script" ] && continue
        if timeout 2 grep -qE "\b(python|python2|python3)\s" "$script" 2>/dev/null; then
            if ! timeout 2 grep -qE "(CASA6_PYTHON|/opt/miniforge/envs/casa6/bin/python)" "$script" 2>/dev/null; then
                echo -e "${YELLOW}⚠️  WARNING:${NC} $script may use system Python"
                ((WARNINGS++)) || true
            fi
        fi
    done
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo "   No forbidden Python versions detected."
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Validation completed with warnings${NC}"
    echo "   Errors: $ERRORS"
    echo "   Warnings: $WARNINGS"
    exit 0
else
    echo -e "${RED}❌ Validation failed!${NC}"
    echo "   Errors: $ERRORS"
    echo "   Warnings: $WARNINGS"
    echo ""
    echo "Fix the errors above before proceeding."
    exit 1
fi

