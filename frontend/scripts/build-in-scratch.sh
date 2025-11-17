#!/bin/bash
# Build script that uses /scratch/ for faster I/O, then copies results back
# This solves the build hang issue caused by slow filesystem I/O on /data/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Script is in frontend/scripts/, so frontend root is one level up
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRATCH_DIR="/scratch/dsa110-contimg-build/frontend"

echo "🔨 Building in /scratch/ for faster I/O..."
echo "   Source: $FRONTEND_DIR"
echo "   Scratch: $SCRATCH_DIR"

# Ensure casa6 Node.js is active
CASA6_NODE="/opt/miniforge/envs/casa6/bin/node"
if [ ! -f "$CASA6_NODE" ]; then
  echo "❌ ERROR: casa6 Node.js not found at $CASA6_NODE"
  echo "   Please activate casa6: conda activate casa6"
  exit 1
fi

# Check Node.js version
CURRENT_VERSION=$("$CASA6_NODE" --version | sed 's/v//')
REQUIRED_VERSION="22.0.0"
if ! printf '%s\n%s\n' "$REQUIRED_VERSION" "$CURRENT_VERSION" | sort -V -C; then
  echo "❌ ERROR: Node.js version $CURRENT_VERSION is too old"
  echo "   Required: >= $REQUIRED_VERSION"
  echo "   Please use casa6 Node.js: conda activate casa6"
  exit 1
fi

# Create scratch directory
mkdir -p "$SCRATCH_DIR"

# Copy source files (excluding node_modules, .vite, dist, .git)
echo "📦 Copying source files to /scratch/..."
rsync -av --delete \
  --exclude 'node_modules' \
  --exclude '.vite' \
  --exclude 'dist' \
  --exclude '.git' \
  --exclude '*.log' \
  "$FRONTEND_DIR/" "$SCRATCH_DIR/"

# Install dependencies in scratch if needed
if [ ! -d "$SCRATCH_DIR/node_modules" ] || [ "$FRONTEND_DIR/package.json" -nt "$SCRATCH_DIR/node_modules" ]; then
  echo "📥 Installing dependencies in /scratch/..."
  cd "$SCRATCH_DIR"
  source /opt/miniforge/etc/profile.d/conda.sh
  conda activate casa6
  npm install
fi

# Build in scratch
echo "🚀 Building in /scratch/..."
cd "$SCRATCH_DIR"
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Set Node.js memory limit
export NODE_OPTIONS="--max-old-space-size=8192"

# Run the build (use build:no-check for speed, or regular build for type checking)
BUILD_CMD="${1:-build:no-check}"
if [ "$BUILD_CMD" = "build" ]; then
  npm run build
elif [ "$BUILD_CMD" = "build:no-check" ]; then
  npm run build:no-check
elif [ "$BUILD_CMD" = "build:fast" ]; then
  npm run build:fast
else
  echo "Running custom build command: $BUILD_CMD"
  npm run "$BUILD_CMD"
fi

# Copy dist back to original location
if [ -d "$SCRATCH_DIR/dist" ]; then
  echo "📤 Copying build output back to $FRONTEND_DIR/dist/..."
  mkdir -p "$FRONTEND_DIR/dist"
  rsync -av --delete "$SCRATCH_DIR/dist/" "$FRONTEND_DIR/dist/"
  echo "✅ Build complete! Output in $FRONTEND_DIR/dist/"
else
  echo "❌ ERROR: Build did not produce dist/ folder"
  exit 1
fi

# Optionally clean up scratch (comment out to keep for faster rebuilds)
# echo "🧹 Cleaning up /scratch/..."
# rm -rf "$SCRATCH_DIR"

echo "✨ Done!"

