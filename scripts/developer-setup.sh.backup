#!/bin/bash
# Comprehensive developer environment setup
# This script automates all critical setup steps to prevent common mistakes
# Usage: source scripts/developer-setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 Setting up developer environment..."

# 1. Verify casa6 Python exists
if [ ! -f "/opt/miniforge/envs/casa6/bin/python" ]; then
    echo "❌ ERROR: casa6 Python not found at /opt/miniforge/envs/casa6/bin/python"
    echo "   Please install casa6 environment first"
    return 1 2>/dev/null || exit 1
fi
echo "✅ casa6 Python found"

# 2. Enable error detection
if [ -f "$SCRIPT_DIR/auto-error-detection.sh" ]; then
    source "$SCRIPT_DIR/auto-error-detection.sh"
    echo "✅ Error detection enabled"
else
    echo "⚠️  Warning: auto-error-detection.sh not found"
fi

# 3. Create aliases for common commands
alias pytest-safe="$SCRIPT_DIR/pytest-safe.sh"
alias run-tests="$SCRIPT_DIR/run-tests.sh"

# 4. Override pytest to use safe wrapper
pytest() {
    "$SCRIPT_DIR/pytest-safe.sh" "$@"
}

# 5. Override python/python3 to use casa6 (with warning)
_original_python=$(which python3 2>/dev/null || echo "")
_original_python3=$(which python3 2>/dev/null || echo "")

python() {
    if [[ "$1" == "-m" ]] && [[ "$2" == "pytest" ]]; then
        echo "⚠️  Using pytest-safe wrapper instead of direct python -m pytest"
        "$SCRIPT_DIR/pytest-safe.sh" "${@:3}"
    else
        /opt/miniforge/envs/casa6/bin/python "$@"
    fi
}

python3() {
    if [[ "$1" == "-m" ]] && [[ "$2" == "pytest" ]]; then
        echo "⚠️  Using pytest-safe wrapper instead of direct python3 -m pytest"
        "$SCRIPT_DIR/pytest-safe.sh" "${@:3}"
    else
        /opt/miniforge/envs/casa6/bin/python "$@"
    fi
}

# 6. Set environment variables
export PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"
export DSA110_PROJECT_ROOT="$PROJECT_ROOT"
export DSA110_SCRIPTS_DIR="$SCRIPT_DIR"

# 7. Add scripts to PATH (optional, for convenience)
export PATH="$SCRIPT_DIR:$PATH"

# 8. Verify CASA environment
if python -c "import casacore" 2>/dev/null; then
    echo "✅ CASA environment verified"
else
    echo "⚠️  Warning: casacore not importable, CASA setup may be incomplete"
fi

# 9. Check pre-commit hooks
if [ -f "$PROJECT_ROOT/.githooks/pre-commit" ]; then
    if [ -x "$PROJECT_ROOT/.githooks/pre-commit" ]; then
        echo "✅ Pre-commit hooks configured"
    else
        echo "⚠️  Warning: Pre-commit hook not executable"
    fi
else
    echo "⚠️  Warning: Pre-commit hook not found"
fi

# 10. Display quick reference
echo ""
echo "✅ Developer environment setup complete!"
echo ""
echo "Quick reference:"
echo "  - Run tests: run-tests.sh [category]"
echo "  - Safe pytest: pytest-safe.sh [args]"
echo "  - Python: python/python3 (auto-uses casa6)"
echo ""
echo "For full documentation: docs/how-to/CRITICAL_HANDOVER_WARNINGS.md"
