#!/bin/bash
# Test Organization Enforcer
# 
# This script provides multiple enforcement mechanisms:
# 1. Pre-commit hook installation
# 2. CI/CD integration check
# 3. Manual validation
#
# Usage:
#   ./scripts/test-organization-enforcer.sh install    # Install pre-commit hook
#   ./scripts/test-organization-enforcer.sh check       # Run validation
#   ./scripts/test-organization-enforcer.sh ci          # CI mode (strict)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

MODE="${1:-check}"

case "$MODE" in
    install)
        echo "Installing pre-commit hook for test organization validation..."
        
        # Check if git is configured to use .githooks/ or .git/hooks/
        HOOKS_PATH=$(git config --get core.hooksPath || echo ".git/hooks")
        if [ "$HOOKS_PATH" = ".githooks" ]; then
            HOOK_FILE=".githooks/pre-commit"
            mkdir -p .githooks
        else
            HOOK_FILE=".git/hooks/pre-commit"
        fi
        HOOK_CONTENT="#!/bin/bash
# Pre-commit hook: Test organization validation
STAGED_TESTS=\$(git diff --cached --name-only --diff-filter=ACM | grep -E 'tests/.*test_.*\.py\$')
if [ -n \"\$STAGED_TESTS\" ]; then
    /opt/miniforge/envs/casa6/bin/python $PROJECT_ROOT/scripts/validate-test-organization.py --staged-only
    if [ \$? -ne 0 ]; then
        echo 'ERROR: Test organization validation failed!'
        echo 'See docs/concepts/TEST_ORGANIZATION.md for rules.'
        exit 1
    fi
fi"
        
        # Check if hook already exists
        if [ -f "$HOOK_FILE" ]; then
            if grep -q "test organization validation" "$HOOK_FILE"; then
                echo "  Pre-commit hook already installed"
            else
                echo "" >> "$HOOK_FILE"
                echo "$HOOK_CONTENT" >> "$HOOK_FILE"
                echo "  Added test organization check to existing pre-commit hook"
            fi
        else
            echo "$HOOK_CONTENT" > "$HOOK_FILE"
            chmod +x "$HOOK_FILE"
            echo "  Pre-commit hook installed"
        fi
        ;;
    
    check)
        echo "Running test organization validation..."
        /opt/miniforge/envs/casa6/bin/python "$PROJECT_ROOT/scripts/validate-test-organization.py"
        ;;
    
    ci)
        echo "Running test organization validation (CI mode - strict)..."
        /opt/miniforge/envs/casa6/bin/python "$PROJECT_ROOT/scripts/validate-test-organization.py" --strict
        ;;
    
    *)
        echo "Usage: $0 {install|check|ci}"
        echo ""
        echo "  install  - Install pre-commit hook"
        echo "  check    - Run validation (default)"
        echo "  ci       - Run validation in CI mode (strict)"
        exit 1
        ;;
esac

