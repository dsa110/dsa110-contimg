#!/bin/bash
# Setup script to add PYTHONWARNINGS to casa6 conda environment
# This makes warning suppression automatic when the environment is activated

set -e

CASA6_ENV="/opt/miniforge/envs/casa6"
ACTIVATE_DIR="${CASA6_ENV}/etc/conda/activate.d"
SCRIPT_NAME="python_warnings.sh"

# Check if casa6 environment exists
if [ ! -d "$CASA6_ENV" ]; then
    echo ":cross: Error: casa6 conda environment not found at $CASA6_ENV"
    echo "  Please ensure casa6 environment is installed"
    exit 1
fi

# Create activation directory if it doesn't exist
mkdir -p "$ACTIVATE_DIR"

# Check if script already exists
if [ -f "${ACTIVATE_DIR}/${SCRIPT_NAME}" ]; then
    if grep -q "PYTHONWARNINGS.*ignore::DeprecationWarning" "${ACTIVATE_DIR}/${SCRIPT_NAME}" 2>/dev/null; then
        echo ":check: PYTHONWARNINGS already configured in casa6 environment"
        echo "  Location: ${ACTIVATE_DIR}/${SCRIPT_NAME}"
        exit 0
    else
        echo ":warning: Warning: ${SCRIPT_NAME} exists but doesn't contain expected content"
        echo "  Location: ${ACTIVATE_DIR}/${SCRIPT_NAME}"
        exit 1
    fi
fi

# Create activation script
cat > "${ACTIVATE_DIR}/${SCRIPT_NAME}" << 'EOF'
#!/bin/bash
# Conda activation script to suppress SWIG deprecation warnings
# This script runs automatically when the casa6 environment is activated

# Suppress SWIG-generated deprecation warnings from CASA/casacore
# These warnings come from SWIG bindings missing __module__ attributes
# Fixed in SWIG 4.4+ but not yet widely released
# See: https://github.com/swig/swig/issues/2881
export PYTHONWARNINGS="ignore::DeprecationWarning"
EOF

chmod +x "${ACTIVATE_DIR}/${SCRIPT_NAME}"

echo ":check: Added PYTHONWARNINGS to casa6 conda environment"
echo "  Location: ${ACTIVATE_DIR}/${SCRIPT_NAME}"
echo ""
echo "The warning suppression will be active:"
echo "  - When you activate the casa6 environment: conda activate casa6"
echo "  - Automatically if casa6 is your default/base environment"
echo ""
echo "To test, activate the environment:"
echo "  conda activate casa6"
echo "  python -c \"from casatools import linearmosaic; print(':check: No warnings')\""

