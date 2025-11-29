#!/bin/bash
#
# Production Setup Validation Script
#
# Validates that the production environment is properly configured
# before deploying the DSA-110 Continuum Imaging Pipeline.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

echo "=== DSA-110 Continuum Imaging Pipeline - Production Setup Validation ==="
echo ""

# Check casa6 Python
echo -n "Checking casa6 Python... "
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"
if [[ -x "$CASA6_PYTHON" ]]; then
    echo -e "${GREEN}:check:${NC}"
    $CASA6_PYTHON --version | head -1
else
    echo -e "${RED}:cross:${NC}"
    echo "  ERROR: casa6 Python not found at $CASA6_PYTHON"
    ERRORS=$((ERRORS + 1))
fi

# Check required directories
echo ""
echo "Checking required directories..."
REQUIRED_DIRS=(
    "/stage/dsa110-contimg"
    "/data/dsa110-contimg/products"
    "/data/dsa110-contimg/state"
    "/data/incoming"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    echo -n "  $dir... "
    if [[ -d "$dir" ]]; then
        echo -e "${GREEN}:check:${NC}"
    else
        echo -e "${YELLOW}:warning:${NC}"
        echo "    WARNING: Directory does not exist (will be created if needed)"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# Check directory permissions
echo ""
echo "Checking directory permissions..."
for dir in "${REQUIRED_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        echo -n "  $dir (writable)... "
        if [[ -w "$dir" ]]; then
            echo -e "${GREEN}:check:${NC}"
        else
            echo -e "${RED}:cross:${NC}"
            echo "    ERROR: Directory is not writable"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

# Check disk space
echo ""
echo "Checking disk space..."
echo -n "  /stage (SSD)... "
STAGE_FREE=$(df -BG /stage/dsa110-contimg 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//' || echo "0")
if [[ "$STAGE_FREE" -ge 500 ]]; then
    echo -e "${GREEN}:check:${NC} (${STAGE_FREE}GB free)"
else
    echo -e "${YELLOW}:warning:${NC} (${STAGE_FREE}GB free, recommended: 500GB+)"
    WARNINGS=$((WARNINGS + 1))
fi

echo -n "  /data (HDD)... "
DATA_FREE=$(df -BG /data/dsa110-contimg 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//' || echo "0")
if [[ "$DATA_FREE" -ge 2000 ]]; then
    echo -e "${GREEN}:check:${NC} (${DATA_FREE}GB free)"
else
    echo -e "${YELLOW}:warning:${NC} (${DATA_FREE}GB free, recommended: 2TB+)"
    WARNINGS=$((WARNINGS + 1))
fi

# Check systemd service files
echo ""
echo "Checking systemd service files..."
SERVICE_FILES=(
    "ops/systemd/contimg-api.service"
    "ops/systemd/contimg-stream.service"
    "ops/systemd/contimg.env"
)

for file in "${SERVICE_FILES[@]}"; do
    echo -n "  $file... "
    if [[ -f "$REPO_ROOT/$file" ]]; then
        echo -e "${GREEN}:check:${NC}"
    else
        echo -e "${RED}:cross:${NC}"
        echo "    ERROR: Service file not found"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check log directory
echo ""
echo "Checking log directory..."
LOG_DIR="/data/dsa110-contimg/state/logs"
echo -n "  $LOG_DIR... "
if [[ -d "$LOG_DIR" ]]; then
    echo -e "${GREEN}:check:${NC}"
elif mkdir -p "$LOG_DIR" 2>/dev/null; then
    echo -e "${GREEN}:check:${NC} (created)"
else
    echo -e "${RED}:cross:${NC}"
    echo "    ERROR: Cannot create log directory"
    ERRORS=$((ERRORS + 1))
fi

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
echo -n "  casacore... "
if $CASA6_PYTHON -c "import casacore" 2>/dev/null; then
    echo -e "${GREEN}:check:${NC}"
else
    echo -e "${RED}:cross:${NC}"
    echo "    ERROR: casacore not available"
    ERRORS=$((ERRORS + 1))
fi

echo -n "  fastapi... "
if $CASA6_PYTHON -c "import fastapi" 2>/dev/null; then
    echo -e "${GREEN}:check:${NC}"
else
    echo -e "${RED}:cross:${NC}"
    echo "    ERROR: fastapi not available"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "=== Validation Summary ==="
if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
    echo -e "${GREEN}:check: All checks passed${NC}"
    exit 0
elif [[ $ERRORS -eq 0 ]]; then
    echo -e "${YELLOW}:warning: Validation passed with $WARNINGS warning(s)${NC}"
    exit 0
else
    echo -e "${RED}:cross: Validation failed with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    exit 1
fi

