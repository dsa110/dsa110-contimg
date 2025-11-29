#!/bin/bash
# Quick environment check for frontend development
# Validates Node.js version and critical dependencies

set -e

# Auto-detect project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(dirname "$SCRIPT_DIR")}"

echo "=== Environment Check ==="
echo "Project root: $PROJECT_ROOT"

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo ":check: Node.js: $NODE_VERSION"
else
    echo ":cross: Node.js not found!"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo ":check: npm: $NPM_VERSION"
else
    echo ":cross: npm not found!"
    exit 1
fi

# Check if we're in casa6 environment (recommended)
if [[ "$PATH" == */miniforge/envs/casa6/* ]]; then
    echo ":check: Using casa6 environment"
else
    echo ":warning: Not using casa6 environment (recommended: conda activate casa6)"
fi

# Check node_modules
if [ -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo ":check: node_modules exists"
else
    echo ":warning: node_modules missing - run 'npm install' in $PROJECT_ROOT/frontend"
fi

echo ""
echo "Environment OK!"
