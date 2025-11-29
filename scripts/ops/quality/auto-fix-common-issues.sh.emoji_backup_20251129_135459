#!/bin/bash
# Auto-fix script for common developer issues
# Usage: ./scripts/auto-fix-common-issues.sh [--check-only]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHECK_ONLY="${1:-}"

FIXES_APPLIED=0
ISSUES_FOUND=0

echo ":search: Checking for common issues..."

# 1. Check Git lock file
if [ -f "$PROJECT_ROOT/.git/index.lock" ]; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    if [ "$CHECK_ONLY" != "--check-only" ]; then
        echo ":wrench: Fixing: Removing stale Git lock file..."
        "$SCRIPT_DIR/fix-git-lock.sh"
        FIXES_APPLIED=$((FIXES_APPLIED + 1))
    else
        echo ":warning:  Issue: Stale Git lock file found"
    fi
fi

# 2. Check pre-commit hook
if [ ! -f "$PROJECT_ROOT/.githooks/pre-commit" ]; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    if [ "$CHECK_ONLY" != "--check-only" ]; then
        echo ":wrench: Fixing: Installing pre-commit hook..."
        "$SCRIPT_DIR/test-organization-enforcer.sh"
        FIXES_APPLIED=$((FIXES_APPLIED + 1))
    else
        echo ":warning:  Issue: Pre-commit hook not found"
    fi
fi

# 3. Check if error detection is enabled
if [ -z "${_IN_ERROR_DETECTION:-}" ] && [ -z "$(type -t _run_with_error_detection 2>/dev/null)" ]; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    if [ "$CHECK_ONLY" != "--check-only" ]; then
        echo ":wrench: Fixing: Enabling error detection..."
        source "$SCRIPT_DIR/auto-error-detection.sh"
        FIXES_APPLIED=$((FIXES_APPLIED + 1))
    else
        echo ":warning:  Issue: Error detection not enabled"
    fi
fi

# 4. Check CASA environment
if ! /opt/miniforge/envs/casa6/bin/python -c "import casacore" 2>/dev/null; then
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    if [ "$CHECK_ONLY" != "--check-only" ]; then
        echo ":wrench: Fixing: Setting up CASA environment..."
        /opt/miniforge/envs/casa6/bin/python -c "from dsa110_contimg.utils.casa_init import ensure_casa_path; ensure_casa_path()" 2>/dev/null || true
        FIXES_APPLIED=$((FIXES_APPLIED + 1))
    else
        echo ":warning:  Issue: CASA environment not properly configured"
    fi
fi

# 5. Check for test organization issues
if [ "$CHECK_ONLY" != "--check-only" ]; then
    echo ":search: Checking test organization..."
    if "$SCRIPT_DIR/validate-test-organization.py" --check-only 2>/dev/null; then
        echo ":check: Test organization is valid"
    else
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
        echo ":warning:  Issue: Test organization problems found (run validate-test-organization.py for details)"
    fi
else
    if ! "$SCRIPT_DIR/validate-test-organization.py" --check-only 2>/dev/null; then
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
        echo ":warning:  Issue: Test organization problems found"
    fi
fi

# Summary
echo ""
if [ "$CHECK_ONLY" == "--check-only" ]; then
    if [ $ISSUES_FOUND -eq 0 ]; then
        echo ":check: No issues found!"
        exit 0
    else
        echo ":warning:  Found $ISSUES_FOUND issue(s). Run without --check-only to fix."
        exit 1
    fi
else
    if [ $FIXES_APPLIED -eq 0 ] && [ $ISSUES_FOUND -eq 0 ]; then
        echo ":check: No issues found, everything is configured correctly!"
        exit 0
    else
        echo ":check: Applied $FIXES_APPLIED fix(es)"
        if [ $ISSUES_FOUND -gt $FIXES_APPLIED ]; then
            echo ":warning:  $((ISSUES_FOUND - FIXES_APPLIED)) issue(s) require manual attention"
        fi
        exit 0
    fi
fi
