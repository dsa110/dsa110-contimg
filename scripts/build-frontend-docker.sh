#!/bin/bash
# Build the frontend using Node.js from casa6 conda environment (preferred) or Docker (fallback)
# casa6 has Node.js v22.6.0 which meets Vite requirements (20.19+ or 22.12+)
# Falls back to Docker if casa6 Node.js is not available

set -e

PROJECT_ROOT="/data/dsa110-contimg"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
CASA6_NODE="/opt/miniforge/envs/casa6/bin/node"
CASA6_NPM="/opt/miniforge/envs/casa6/bin/npm"

# Check if casa6 Node.js is available and meets version requirements
USE_CASA6=false
if [ -x "${CASA6_NODE}" ] && [ -x "${CASA6_NPM}" ]; then
    NODE_VERSION=$("${CASA6_NODE}" --version 2>/dev/null | sed 's/v//')
    # Check if version is >= 20.19.0 or >= 22.12.0
    MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
    MINOR=$(echo "$NODE_VERSION" | cut -d. -f2)
    if [ "$MAJOR" -ge 22 ] || ([ "$MAJOR" -eq 20 ] && [ "$MINOR" -ge 19 ]) || [ "$MAJOR" -ge 21 ]; then
        USE_CASA6=true
        echo "Using Node.js from casa6 environment: v${NODE_VERSION}"
    fi
fi

cd "${FRONTEND_DIR}"

# Download JS9 files before building (so they're available in public/js9/)
echo "Downloading JS9 files..."
"${FRONTEND_DIR}/scripts/download-js9.sh" || {
    echo "WARNING: Failed to download JS9 files. Continuing build..." >&2
}

if [ "$USE_CASA6" = true ]; then
    # Use casa6 Node.js directly (no Docker, no platform conflicts)
    echo "Building frontend using casa6 Node.js..."
    # Ensure casa6 bin directory is first in PATH
    export PATH="/opt/miniforge/envs/casa6/bin:${PATH}"
    # Verify we're using the right npm
    NPM_PATH=$(which npm)
    echo "Using npm from: ${NPM_PATH}"
    
    echo "Cleaning existing node_modules (if any)..."
    if [ -d node_modules ]; then
        # Try to remove, but don't fail if some directories are locked
        rm -rf node_modules 2>/dev/null || {
            echo "Warning: Some node_modules directories couldn't be removed (may be from Docker build)"
            echo "npm install will handle this..."
        }
    fi
    
    echo "Installing dependencies..."
    # Install without scripts first to avoid patch-package issues
    npm install --ignore-scripts || npm install --ignore-scripts --force
    # Install dev dependencies explicitly (needed for build - TypeScript, etc.)
    # This ensures devDependencies are installed even if NODE_ENV might be set
    npm install --include=dev --ignore-scripts || npm install --include=dev --ignore-scripts --force
    
    echo "Building frontend..."
    export NODE_ENV=production
    # Ensure node_modules/.bin is in PATH for npm scripts
    export PATH="${FRONTEND_DIR}/node_modules/.bin:${PATH}"
    npm run build || {
        echo "ERROR: Build failed!" >&2
        exit 1
    }
else
    # Fallback to Docker
    echo "casa6 Node.js not available or version too old, using Docker..."
    echo "Building frontend using Docker (Node.js 20 Alpine)..."
    
    docker run --rm \
      -v "${FRONTEND_DIR}:/app/frontend" \
      -w /app/frontend \
      -e NODE_ENV=production \
      node:20-alpine \
      sh -c "
        echo 'Cleaning existing node_modules (if any)...'
        if [ -d node_modules ]; then
          find node_modules -mindepth 1 -delete 2>/dev/null || rm -rf node_modules/* 2>/dev/null || true
          rm -rf node_modules 2>/dev/null || true
        fi
        echo 'Installing dependencies (including dev dependencies for build)...'
        npm install
        echo 'Building frontend...'
        export PATH=\$PATH:\$(pwd)/node_modules/.bin
        npm run build || {
          echo 'ERROR: Build failed!' >&2
          exit 1
        }
        echo 'Build complete!'
      "
fi

echo ""
echo "Frontend build complete!"
echo "Built files are in: ${FRONTEND_DIR}/dist"
echo ""
echo "To restart the dashboard with the new build:"
echo "  tmux kill-session -t dsa110-dashboard"
echo "  bash ${PROJECT_ROOT}/scripts/start-dashboard-tmux.sh"

