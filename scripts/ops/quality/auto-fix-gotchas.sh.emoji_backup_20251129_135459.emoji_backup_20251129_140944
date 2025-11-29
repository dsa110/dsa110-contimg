#!/usr/bin/env bash
# Auto-fix common gotchas
# Automatically fixes issues that can be fixed without user intervention

set -e

REPO_ROOT="$(cd "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_ROOT"

FIXES_APPLIED=0

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() {
  echo -e "${BLUE}ℹ️${NC} $1"
}

fix() {
  echo -e "${GREEN}✓${NC} $1"
  ((FIXES_APPLIED++))
}

warning() {
  echo -e "${YELLOW}⚠️${NC} $1"
}

echo "Auto-fixing common gotchas..."
echo ""

# 1. Fix git hook permissions
if [ -f ".husky/pre-commit" ] && [ ! -x ".husky/pre-commit" ]; then
  chmod +x .husky/pre-commit
  fix "Made pre-commit hook executable"
fi

if [ -f ".husky/post-commit" ] && [ ! -x ".husky/post-commit" ]; then
  chmod +x .husky/post-commit
  fix "Made post-commit hook executable"
fi

# 2. Install Prettier if missing
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
  cd frontend
  if command -v npx >/dev/null 2>&1; then
    if ! npx prettier --version >/dev/null 2>&1; then
      if [ -f "package.json" ] && grep -q '"prettier"' package.json; then
        info "Installing Prettier..."
        npm install --save-dev prettier 2>/dev/null || warning "Failed to install Prettier (may need npm install first)"
        fix "Installed Prettier"
      fi
    fi
  fi
  cd ..
fi

# 3. Initialize Husky if needed
if command -v npx >/dev/null 2>&1 && [ ! -d ".githooks" ] && [ -d ".husky" ]; then
  info "Initializing Husky..."
  npx husky install 2>/dev/null || warning "Husky initialization failed (may need npm install)"
  fix "Initialized Husky"
fi

# 4. Check and warn about Python (can't auto-fix)
CURRENT_PYTHON=$(which python 2>/dev/null || echo "")
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"

if [ -n "$CURRENT_PYTHON" ] && [ "$CURRENT_PYTHON" != "$CASA6_PYTHON" ]; then
  warning "Python environment issue detected"
  info "   Current: $CURRENT_PYTHON"
  info "   Should be: $CASA6_PYTHON"
  info "   Fix: conda activate casa6"
  info "   Or add to your shell profile:"
  info "   export PATH=\"/opt/miniforge/envs/casa6/bin:\$PATH\""
fi

# Summary
echo ""
if [ $FIXES_APPLIED -gt 0 ]; then
  echo -e "${GREEN}✓ Applied $FIXES_APPLIED fix(es)${NC}"
else
  echo "No fixes needed"
fi

echo ""
echo "Run './scripts/check-environment.sh' to verify everything is correct"

