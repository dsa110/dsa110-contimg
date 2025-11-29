#!/usr/bin/env bash
# Development environment setup script
# Ensures hooks are executable and dependencies are installed

set -e

# This script lives under scripts/ops/dev/, so hop three levels to reach repo root
REPO_ROOT="$(cd "$(dirname -- "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "Setting up development environment..."
echo ""

# 1. Make git hooks executable
echo "1. Setting up git hooks..."
if [ -d ".husky" ]; then
  chmod +x .husky/pre-commit 2>/dev/null || true
  chmod +x .husky/post-commit 2>/dev/null || true
  echo "   :check: Git hooks are executable"
else
  echo "   :warning: Warning: .husky directory not found"
fi

# 2. Initialize Husky if needed
if command -v npx >/dev/null 2>&1; then
  echo ""
  echo "2. Initializing Husky..."
  npx husky install 2>/dev/null || echo "   :warning: Warning: Husky initialization failed (may need npm install)"
fi

# 3. Install frontend dependencies
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
  echo ""
  echo "3. Installing frontend dependencies..."
  cd frontend
  if [ -f "package-lock.json" ] || [ -f "yarn.lock" ]; then
    npm install
    echo "   :check: Frontend dependencies installed"
  else
    echo "   :warning: Warning: No lock file found, dependencies may not be pinned"
    npm install
  fi
  cd ..
else
  echo ""
  echo "   :warning: Warning: frontend directory or package.json not found"
fi

# 4. Verify Prettier is installed
echo ""
echo "4. Verifying Prettier installation..."
if [ -d "frontend" ]; then
  cd frontend
  if npx prettier --version >/dev/null 2>&1; then
    PRETTIER_VERSION=$(npx prettier --version)
    echo "   :check: Prettier $PRETTIER_VERSION is installed"
  else
    echo "   :warning: Warning: Prettier not found, installing..."
    npm install --save-dev prettier
    echo "   :check: Prettier installed"
  fi
  cd ..
fi

# 5. Verify hook is executable
echo ""
echo "5. Verifying hook permissions..."
if [ -x ".husky/pre-commit" ]; then
  echo "   :check: Pre-commit hook is executable"
else
  echo "   :warning: Warning: Pre-commit hook is not executable, fixing..."
  chmod +x .husky/pre-commit
  echo "   :check: Fixed"
fi

# 6. Run auto-fix script for any remaining issues
echo ""
echo "6. Running auto-fix for common gotchas..."
if [ -f "${REPO_ROOT}/scripts/auto-fix-gotchas.sh" ]; then
  bash "${REPO_ROOT}/scripts/auto-fix-gotchas.sh"
fi

# 7. Run environment check
echo ""
echo "7. Verifying environment..."
if [ -f "${REPO_ROOT}/scripts/check-environment.sh" ]; then
  bash "${REPO_ROOT}/scripts/check-environment.sh" || {
    echo ""
    echo ":warning:  Some issues remain. Review the output above."
  }
fi

# 8. Run code quality check (informational)
echo ""
echo "8. Checking code quality..."
if [ -f "${REPO_ROOT}/scripts/check-code-quality.sh" ]; then
  bash "${REPO_ROOT}/scripts/check-code-quality.sh" || true
fi

echo ""
echo ":check: Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  - Make a test commit to verify the pre-commit hook works"
echo "  - Run 'cd frontend && npm run format:check' to verify Prettier"
echo "  - Run './scripts/check-environment.sh' anytime to verify setup"
echo "  - Pre-commit runs a docs audit (scripts/doc_audit.py) to catch endpoint/link drift"
echo "    Run 'make doc-audit' anytime to check documentation locally"
echo ""
