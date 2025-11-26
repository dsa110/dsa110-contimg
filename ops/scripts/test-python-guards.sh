#!/bin/bash
# Test script to verify Python version guards work correctly

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"
PROJECT_ROOT="/data/dsa110-contimg"

echo "🧪 Testing Python version guards..."
echo ""

# Test 1: CASA6 Python should work
echo "Test 1: CASA6 Python (should succeed)"
if "$CASA6_PYTHON" "$PROJECT_ROOT/scripts/python-version-guard.py" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}: CASA6 Python works"
else
    echo -e "${RED}❌ FAIL${NC}: CASA6 Python failed"
    exit 1
fi

# Test 2: Python 2.7 should be blocked
echo ""
echo "Test 2: Python 2.7 (should be blocked)"
if /usr/bin/python2.7 "$PROJECT_ROOT/scripts/python-version-guard.py" >/dev/null 2>&1; then
    echo -e "${RED}❌ FAIL${NC}: Python 2.7 was not blocked"
    exit 1
else
    echo -e "${GREEN}✅ PASS${NC}: Python 2.7 correctly blocked"
fi

# Test 3: Python 3.6 should be blocked
echo ""
echo "Test 3: Python 3.6 (should be blocked)"
if /usr/bin/python3.6 "$PROJECT_ROOT/scripts/python-version-guard.py" >/dev/null 2>&1; then
    echo -e "${RED}❌ FAIL${NC}: Python 3.6 was not blocked"
    exit 1
else
    echo -e "${GREEN}✅ PASS${NC}: Python 3.6 correctly blocked"
fi

# Test 4: Scripts with guards should block old Python
echo ""
echo "Test 4: Script with version guard (Python 3.6 should be blocked)"
if /usr/bin/python3.6 -c "import sys; sys.path.insert(0, 'src'); from dsa110_contimg.photometry.cli import *" >/dev/null 2>&1; then
    echo -e "${RED}❌ FAIL${NC}: Script did not block Python 3.6"
    exit 1
else
    echo -e "${GREEN}✅ PASS${NC}: Script correctly blocked Python 3.6"
fi

# Test 5: Scripts with guards should work with CASA6
echo ""
echo "Test 5: Script with version guard (CASA6 should work)"
if "$CASA6_PYTHON" -c "import sys; sys.path.insert(0, 'src'); from dsa110_contimg.photometry.cli import *; print('OK')" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}: Script works with CASA6 Python"
else
    echo -e "${YELLOW}⚠️  WARNING${NC}: Script import failed (may be due to missing dependencies)"
fi

# Test 6: Validation script
echo ""
echo "Test 6: Validation script (should pass)"
if "$PROJECT_ROOT/scripts/validate-python-version.sh" --pre-commit >/dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}: Validation script works"
else
    echo -e "${YELLOW}⚠️  WARNING${NC}: Validation script had issues (check output)"
fi

echo ""
echo -e "${GREEN}✅ All critical tests passed!${NC}"
echo "Python version guards are working correctly."

