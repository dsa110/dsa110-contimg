#!/usr/bin/env bash
# Auto-fix code quality issues where possible

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

echo "Auto-fixing code quality issues..."
echo ""

# 1. Fix Python shebangs (can't auto-fix, but can suggest)
echo "1. Checking Python shebangs..."
FIXED_SHEBANGS=0
find scripts src tests -name "*.py" -type f 2>/dev/null | while read -r file; do
  FIRST_LINE=$(head -1 "$file" 2>/dev/null || echo "")
  if echo "$FIRST_LINE" | grep -qE "^#!/usr/bin/env python$|^#!/usr/bin/python$"; then
    if [ "$FIXED_SHEBANGS" -eq 0 ]; then
      info "Found Python files with incorrect shebangs"
      info "   These should be updated to use casa6 Python"
      info "   Example: #!/opt/miniforge/envs/casa6/bin/python"
      FIXED_SHEBANGS=1
    fi
    # Don't auto-fix - requires manual review
    warning "   Needs manual fix: $file"
  fi
done

# 2. Move markdown files from root (with confirmation prompt would be better, but auto for now)
echo ""
echo "2. Checking for markdown files in root..."
ROOT_MARKDOWN=$(find . -maxdepth 1 -name "*.md" -type f ! -name "README.md" 2>/dev/null)
if [ -n "$ROOT_MARKDOWN" ]; then
  info "Found markdown files in root directory"
  echo "$ROOT_MARKDOWN" | while read -r file; do
    BASENAME=$(basename "$file")
    # Suggest moving to docs/dev/status/YYYY-MM/ (using current date)
    YEAR_MONTH=$(date +%Y-%m)
    TARGET_DIR="docs/dev/status/${YEAR_MONTH}"
    TARGET="${TARGET_DIR}/${BASENAME}"
    
    info "   Found: $file"
    info "   Should be moved to: $TARGET"
    info "   (Not auto-moving - requires review)"
    warning "   Manual action needed: mv '$file' '$TARGET'"
  done
else
  fix "No markdown files in root (except README.md)"
fi

# Summary
echo ""
if [ $FIXES_APPLIED -gt 0 ]; then
  echo -e "${GREEN}✓ Applied $FIXES_APPLIED fix(es)${NC}"
else
  echo "No automatic fixes available"
  echo "   (Most code quality issues require manual review)"
fi

echo ""
echo "Run './scripts/check-code-quality.sh' to see all issues"

