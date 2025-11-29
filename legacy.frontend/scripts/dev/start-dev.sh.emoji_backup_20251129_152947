#!/bin/bash
# Start dev server with casa6 Node.js check
# Provides clear error messages if casa6 is not activated

set -e

CASA6_NODE="/opt/miniforge/envs/casa6/bin/node"

# Check if casa6 Node.js exists
if [ ! -x "$CASA6_NODE" ]; then
  echo "❌ ERROR: casa6 Node.js not found at $CASA6_NODE" >&2
  echo "   Please activate casa6: conda activate casa6" >&2
  exit 1
fi

# Get current Node.js version
CURRENT_NODE=$(which node)
CURRENT_VERSION=$(node --version | sed 's/v//')

# Check if we're using casa6 Node.js
if [ "$CURRENT_NODE" != "$CASA6_NODE" ]; then
  echo "❌ ERROR: Not using casa6 Node.js" >&2
  echo "   Current: $CURRENT_NODE (v$CURRENT_VERSION)" >&2
  echo "   Required: $CASA6_NODE (v22.6.0)" >&2
  echo "" >&2
  echo "   Fix: source /opt/miniforge/etc/profile.d/conda.sh && conda activate casa6" >&2
  echo "" >&2
  echo "   Then run: npm run dev" >&2
  exit 1
fi

# Check version meets minimum requirement
REQUIRED_VERSION="22.0.0"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$CURRENT_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
  echo "❌ ERROR: Node.js version $CURRENT_VERSION < required $REQUIRED_VERSION" >&2
  echo "   Please use casa6 Node.js v22.6.0" >&2
    exit 1
fi

# Success - clean up port and start Vite
echo "✓ Using casa6 Node.js: $CURRENT_VERSION"

# Clean up any zombie processes on port 3210
if lsof -ti:3210 > /dev/null 2>&1; then
  PIDS=$(lsof -ti:3210)
  echo "⚠️  Found zombie process on port 3210 (PID: $PIDS)"
  echo "🔪 Killing zombie process..."
  lsof -ti:3210 | xargs kill -9 2>/dev/null || true
  sleep 1
  echo "✓ Port 3210 is now free"
fi

echo "🚀 Starting Vite dev server on port 3210..."
echo "   Access at: http://localhost:3210"
exec node -r ./scripts/setup-crypto.cjs node_modules/.bin/vite "$@"
