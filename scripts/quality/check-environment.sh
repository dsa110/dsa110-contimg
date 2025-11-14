#!/usr/bin/env bash
# Environment validation script
# Checks for common gotchas and provides fixes

set -e

REPO_ROOT="$(cd "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_ROOT"

ERRORS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error() {
  echo -e "${RED}❌ ERROR:${NC} $1" >&2
  ((ERRORS++))
}

warning() {
  echo -e "${YELLOW}⚠️  WARNING:${NC} $1" >&2
  ((WARNINGS++))
}

success() {
  echo -e "${GREEN}✓${NC} $1"
}

info() {
  echo -e "${BLUE}ℹ️${NC} $1"
}

echo "Checking development environment..."
echo ""

# 1. Check Python environment
echo "1. Checking Python environment..."
CURRENT_PYTHON=$(which python 2>/dev/null || echo "")
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"

if [ -z "$CURRENT_PYTHON" ]; then
  error "Python not found in PATH"
elif [ "$CURRENT_PYTHON" != "$CASA6_PYTHON" ]; then
  error "Using wrong Python: $CURRENT_PYTHON"
  info "   Should be: $CASA6_PYTHON"
  info "   Fix: conda activate casa6"
  info "   Or: export PATH=\"/opt/miniforge/envs/casa6/bin:\$PATH\""
else
  success "Using correct Python: $CASA6_PYTHON"
fi

if [ -x "$CASA6_PYTHON" ]; then
  PYTHON_VERSION=$("$CASA6_PYTHON" --version 2>&1)
  success "casa6 Python version: $PYTHON_VERSION"
else
  error "casa6 Python not found at $CASA6_PYTHON"
fi

# 2. Check git hooks
echo ""
echo "2. Checking git hooks..."
if [ ! -d ".husky" ]; then
  error ".husky directory not found"
  info "   Fix: npx husky install"
elif [ ! -x ".husky/pre-commit" ]; then
  warning "Pre-commit hook is not executable"
  info "   Fix: chmod +x .husky/pre-commit"
  info "   Or run: ./scripts/setup-dev.sh"
else
  success "Pre-commit hook is executable"
fi

# 3. Check Prettier
echo ""
echo "3. Checking Prettier..."
if [ -d "frontend" ]; then
  cd frontend
  if command -v npx >/dev/null 2>&1; then
    if npx prettier --version >/dev/null 2>&1; then
      PRETTIER_VERSION=$(npx prettier --version)
      success "Prettier installed: $PRETTIER_VERSION"
    else
      warning "Prettier not found in node_modules"
      info "   Fix: npm install --save-dev prettier"
    fi
  else
    warning "npx not found, cannot check Prettier"
  fi
  cd ..
else
  warning "frontend directory not found, skipping Prettier check"
fi

# 4. Check frontend dependencies
echo ""
echo "4. Checking frontend dependencies..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
  cd frontend
  if [ ! -d "node_modules" ]; then
    warning "node_modules not found"
    info "   Fix: npm install"
  else
    success "node_modules exists"
  fi
  cd ..
else
  warning "frontend directory or package.json not found"
fi

# 5. Check documentation structure
echo ""
echo "5. Checking documentation structure..."
ROOT_MARKDOWN=$(find . -maxdepth 1 -name "*.md" -type f ! -name "README.md" 2>/dev/null | wc -l)
if [ "$ROOT_MARKDOWN" -gt 0 ]; then
  warning "Found $ROOT_MARKDOWN markdown file(s) in root directory"
  info "   Documentation should be in docs/ structure"
  info "   See: docs/DOCUMENTATION_QUICK_REFERENCE.md"
  find . -maxdepth 1 -name "*.md" -type f ! -name "README.md" 2>/dev/null | while read -r file; do
    info "   Found: $file"
  done
else
  success "No markdown files in root (except README.md)"
fi

# 6. Check test organization
echo ""
echo "6. Checking test organization..."
if [ -f "scripts/validate-test-organization.py" ]; then
  if "$CASA6_PYTHON" scripts/validate-test-organization.py >/dev/null 2>&1; then
    success "Test organization is valid"
  else
    warning "Test organization validation failed"
    info "   Run: make test-validate"
  fi
else
  warning "Test organization validator not found"
fi

# 7. Check environment setup script
echo ""
echo "7. Checking setup script..."
if [ -x "scripts/setup-dev.sh" ]; then
  success "Setup script exists and is executable"
else
  warning "Setup script not found or not executable"
  info "   Fix: chmod +x scripts/setup-dev.sh"
fi

# 8. Check error detection setup
echo ""
echo "8. Checking error detection..."
if [ -f "scripts/lib/error-detection.sh" ]; then
  success "Error detection library exists"
else
  warning "Error detection library not found"
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo -e "${GREEN}✓ All checks passed!${NC}"
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo -e "${YELLOW}⚠️  $WARNINGS warning(s) found${NC}"
  echo "   Run './scripts/setup-dev.sh' to fix most issues"
  exit 0
else
  echo -e "${RED}❌ $ERRORS error(s), $WARNINGS warning(s) found${NC}"
  echo ""
  echo "To fix issues:"
  echo "  1. Run: ./scripts/setup-dev.sh"
  echo "  2. Activate casa6: conda activate casa6"
  echo "  3. Re-run this check: ./scripts/check-environment.sh"
  exit 1
fi

