#!/bin/bash
# Setup script to ensure correct Python environment for dsa110-contimg
# Source this in your shell: source ./scripts/setup-python-env.sh

set -euo pipefail

# CASA6 Python path
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"
CASA6_BIN_DIR="/opt/miniforge/envs/casa6/bin"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔧 Setting up Python environment for dsa110-contimg..."

# Verify CASA6 Python exists
if [ ! -x "$CASA6_PYTHON" ]; then
    echo -e "${RED}❌ ERROR: CASA6 Python not found at $CASA6_PYTHON${NC}"
    echo "   Please ensure the casa6 conda environment is installed."
    return 1 2>/dev/null || exit 1
fi

# Check CASA6 Python version
CASA6_VERSION=$("$CASA6_PYTHON" --version 2>&1)
if echo "$CASA6_VERSION" | grep -q "Python 3.11"; then
    echo -e "${GREEN}✅ CASA6 Python found:${NC} $CASA6_VERSION"
else
    echo -e "${YELLOW}⚠️  WARNING: CASA6 Python version may not be 3.11.x${NC}"
    echo "   Version: $CASA6_VERSION"
fi

# Add CASA6 bin to PATH (prepend so it takes precedence)
if [[ ":$PATH:" != *":$CASA6_BIN_DIR:"* ]]; then
    export PATH="$CASA6_BIN_DIR:$PATH"
    echo -e "${GREEN}✅ Added CASA6 bin to PATH${NC}"
else
    echo -e "${GREEN}✅ CASA6 bin already in PATH${NC}"
fi

# Set CASA6_PYTHON environment variable
export CASA6_PYTHON
echo -e "${GREEN}✅ Set CASA6_PYTHON=$CASA6_PYTHON${NC}"

# Verify python3 now points to CASA6
if command -v python3 >/dev/null 2>&1; then
    ACTUAL_PYTHON3=$(which python3)
    ACTUAL_VERSION=$(python3 --version 2>&1)
    
    if [ "$ACTUAL_PYTHON3" = "$CASA6_PYTHON" ]; then
        echo -e "${GREEN}✅ python3 now points to CASA6:${NC} $ACTUAL_VERSION"
    else
        echo -e "${YELLOW}⚠️  WARNING: python3 points to:${NC} $ACTUAL_PYTHON3"
        echo "   Version: $ACTUAL_VERSION"
        echo "   Use \$CASA6_PYTHON or full path to ensure correct Python"
    fi
fi

# Check for forbidden Python versions in PATH
echo ""
echo "🔍 Checking for forbidden Python versions..."
FORBIDDEN_FOUND=0

for py in python2 python2.7 python3.6; do
    if command -v "$py" >/dev/null 2>&1; then
        PY_PATH=$(which "$py")
        PY_VERSION=$("$py" --version 2>&1)
        
        # Only warn if it's in a system location (not in our PATH)
        if [[ "$PY_PATH" == /usr/bin/* ]]; then
            echo -e "${YELLOW}⚠️  System $py found:${NC} $PY_PATH ($PY_VERSION)"
            echo "   This is OK for system tools, but don't use it for dsa110-contimg"
        fi
    fi
done

echo ""
echo -e "${GREEN}✅ Python environment setup complete!${NC}"
echo ""
echo "Usage:"
echo "  • Use: \$CASA6_PYTHON script.py"
echo "  • Or: python3 script.py (if PATH is set correctly)"
echo "  • Verify: python3 --version (should show 3.11.x)"
echo ""
echo "To make this permanent, add to your ~/.bashrc:"
echo "  source /data/dsa110-contimg/scripts/setup-python-env.sh"

