#!/bin/bash
# Casa6 Environment Enforcement
# Source this script to ensure casa6 is always used for Python and related tools
# This should be sourced by all scripts and can be included in developer-setup.sh

# Define casa6 paths
CASA6_ENV="/opt/miniforge/envs/casa6"
CASA6_PYTHON="${CASA6_ENV}/bin/python"
CASA6_SQLITE3="${CASA6_ENV}/bin/sqlite3"
CASA6_PIP="${CASA6_ENV}/bin/pip"

# Verify casa6 environment exists
if [[ ! -d "$CASA6_ENV" ]]; then
    echo "ERROR: casa6 conda environment not found at $CASA6_ENV" >&2
    echo "Please ensure casa6 conda environment is installed" >&2
    return 1 2>/dev/null || exit 1
fi

# Verify casa6 Python exists
if [[ ! -x "$CASA6_PYTHON" ]]; then
    echo "ERROR: casa6 Python not found at $CASA6_PYTHON" >&2
    echo "Please ensure casa6 conda environment is installed at $CASA6_ENV" >&2
    return 1 2>/dev/null || exit 1
fi

# Export casa6 paths for use in scripts
export CASA6_PYTHON
export CASA6_SQLITE3
export CASA6_PIP
export CASA6_ENV

# Add casa6 bin to PATH (prepend so it takes precedence)
if [[ ":$PATH:" != *":${CASA6_ENV}/bin:"* ]]; then
    export PATH="${CASA6_ENV}/bin:${PATH}"
fi

# Create wrapper functions that enforce casa6 usage
# These override python/python3 commands to always use casa6
# Note: Functions work in both interactive and non-interactive shells (unlike aliases)

# Only create functions if they don't already exist (allows override)
if ! type python | grep -q "function" 2>/dev/null; then
    python() {
        # Force use of casa6 Python
        exec "$CASA6_PYTHON" "$@"
    }
fi

if ! type python3 | grep -q "function" 2>/dev/null; then
    python3() {
        # Force use of casa6 Python
        exec "$CASA6_PYTHON" "$@"
    }
fi

# Wrapper for sqlite3 to use casa6 version
sqlite3() {
    if [[ -x "$CASA6_SQLITE3" ]]; then
        exec "$CASA6_SQLITE3" "$@"
    else
        echo "ERROR: casa6 sqlite3 not found at $CASA6_SQLITE3" >&2
        return 1
    fi
}

# Wrapper for pip to use casa6 version
pip() {
    if [[ -x "$CASA6_PIP" ]]; then
        exec "$CASA6_PIP" "$@"
    else
        echo "ERROR: casa6 pip not found at $CASA6_PIP" >&2
        return 1
    fi
}

# Verify casa6 Python version
CASA6_VERSION=$("$CASA6_PYTHON" --version 2>&1 | awk '{print $2}')
if [[ "$CASA6_VERSION" != "3.11.13" ]]; then
    echo "WARNING: casa6 Python version is $CASA6_VERSION, expected 3.11.13" >&2
fi

# Verify CASA is importable
if ! "$CASA6_PYTHON" -c "import casatools" 2>/dev/null; then
    echo "WARNING: CASA tools not importable in casa6 environment" >&2
    echo "This may indicate a problem with the casa6 installation" >&2
fi

# Set flag to indicate casa6 environment is enforced
export CASA6_ENV_ENFORCED=1

