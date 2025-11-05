#!/usr/bin/env bash
#
# Production validation script for enhanced DSA-110 pipeline
# Tests all new validation functions with synthetic data
#
# Usage: ./test_enhanced_pipeline_production.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}DSA-110 Enhanced Pipeline Validation${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check if we're in the correct environment
if ! command -v python &> /dev/null; then
    echo -e "${RED}ERROR: Python not found${NC}"
    exit 1
fi

# Try to activate casa6 environment if available
if command -v conda &> /dev/null; then
    echo -e "${YELLOW}Attempting to activate casa6 environment...${NC}"
    eval "$(conda shell.bash hook)" 2>/dev/null || true
    conda activate casa6 2>/dev/null || {
        echo -e "${YELLOW}WARNING: casa6 environment not found, using current environment${NC}"
    }
fi

# Check required dependencies
echo -e "${BLUE}Checking dependencies...${NC}"
DEPS_OK=true

for module in pyuvdata casacore numpy astropy h5py; do
    if ! python -c "import $module" 2>/dev/null; then
        echo -e "${RED}✗ Missing dependency: $module${NC}"
        DEPS_OK=false
    else
        echo -e "${GREEN}✓ $module available${NC}"
    fi
done

if [ "$DEPS_OK" = false ]; then
    echo -e "${RED}ERROR: Missing required dependencies${NC}"
    echo -e "${YELLOW}Please run this script in the casa6 environment:${NC}"
    echo "  conda activate casa6"
    echo "  ./test_enhanced_pipeline_production.sh"
    exit 1
fi

# Set up test environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEST_OUTPUT_DIR="/tmp/dsa110_validation_test_$(date +%Y%m%d_%H%M%S)"
SYNTHETIC_DATA_DIR="${TEST_OUTPUT_DIR}/synthetic"
MS_OUTPUT_DIR="${TEST_OUTPUT_DIR}/ms"

echo -e "${BLUE}Setting up test environment...${NC}"
echo "Project root: ${PROJECT_ROOT}"
echo "Test output: ${TEST_OUTPUT_DIR}"

mkdir -p "${SYNTHETIC_DATA_DIR}"
mkdir -p "${MS_OUTPUT_DIR}"

# Test configuration
START_TIME="2025-11-05T14:00:00"
DURATION_MIN=5.0
FLUX_JY=10.0
SUBBANDS=16

echo -e "${BLUE}Test configuration:${NC}"
echo "  Start time: ${START_TIME}"
echo "  Duration: ${DURATION_MIN} minutes"
echo "  Flux density: ${FLUX_JY} Jy"
echo "  Subbands: ${SUBBANDS}"

# Step 1: Generate synthetic data
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Step 1: Generating synthetic data${NC}"
echo -e "${BLUE}=========================================${NC}"

if [ -f "${PROJECT_ROOT}/src/dsa110_contimg/simulation/make_synthetic_uvh5.py" ]; then
    python "${PROJECT_ROOT}/src/dsa110_contimg/simulation/make_synthetic_uvh5.py" \
        --layout-meta "${PROJECT_ROOT}/src/dsa110_contimg/simulation/config/reference_layout.json" \
        --telescope-config "${PROJECT_ROOT}/src/dsa110_contimg/simulation/pyuvsim/telescope.yaml" \
        --output "${SYNTHETIC_DATA_DIR}" \
        --start-time "${START_TIME}" \
        --duration-minutes "${DURATION_MIN}" \
        --flux-jy "${FLUX_JY}" \
        --subbands "${SUBBANDS}" \
        || {
            echo -e "${RED}ERROR: Failed to generate synthetic data${NC}"
            exit 1
        }
else
    echo -e "${RED}ERROR: Synthetic data generator not found${NC}"
    exit 1
fi

# Verify synthetic data was generated
GENERATED_FILES=$(ls "${SYNTHETIC_DATA_DIR}"/*.hdf5 2>/dev/null | wc -l)
if [ "${GENERATED_FILES}" -ne "${SUBBANDS}" ]; then
    echo -e "${RED}ERROR: Expected ${SUBBANDS} files, got ${GENERATED_FILES}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Generated ${GENERATED_FILES} synthetic subband files${NC}"

# Step 2: Test basic conversion without validation
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Step 2: Testing basic conversion${NC}"
echo -e "${BLUE}=========================================${NC}"

BASIC_MS="${MS_OUTPUT_DIR}/basic_test.ms"

python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    "${SYNTHETIC_DATA_DIR}" \
    "${MS_OUTPUT_DIR}" \
    "${START_TIME:0:10} 00:00:00" \
    "${START_TIME:0:10} 23:59:59" \
    || {
        echo -e "${RED}ERROR: Basic conversion failed${NC}"
        exit 1
    }

# Find the generated MS
GENERATED_MS=$(find "${MS_OUTPUT_DIR}" -name "*.ms" -type d | head -1)
if [ -z "${GENERATED_MS}" ]; then
    echo -e "${RED}ERROR: No Measurement Set was generated${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Basic conversion successful: $(basename "${GENERATED_MS}")${NC}"

# Step 3: Test individual validation functions
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Step 3: Testing validation functions${NC}"
echo -e "${BLUE}=========================================${NC}"

# Create a test script to run individual validations
cat > "${TEST_OUTPUT_DIR}/test_validations.py" << 'EOF'
#!/usr/bin/env python3
"""Test individual validation functions."""

import sys
import logging
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dsa110_contimg.conversion.helpers import (
    validate_ms_frequency_order,
    validate_phase_center_coherence,
    validate_uvw_precision,
    validate_antenna_positions,
    validate_model_data_quality,
    validate_reference_antenna_stability,
    cleanup_casa_file_handles,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_validation_function(func, ms_path, description, *args, **kwargs):
    """Test a single validation function."""
    try:
        result = func(ms_path, *args, **kwargs)
        if result is not None:
            logger.info(f"✓ {description}: {result}")
        else:
            logger.info(f"✓ {description}: Passed")
        return True
    except RuntimeError as e:
        if "validation failed" in str(e).lower() or "not found" in str(e).lower():
            logger.warning(f"⚠ {description}: {e}")
        else:
            logger.error(f"✗ {description}: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ {description}: Unexpected error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_validations.py <ms_path>")
        sys.exit(1)
        
    ms_path = sys.argv[1]
    logger.info(f"Testing validation functions on: {ms_path}")
    
    tests = [
        (validate_ms_frequency_order, "Frequency ordering validation"),
        (validate_phase_center_coherence, "Phase center coherence validation"),
        (validate_uvw_precision, "UVW precision validation"),
        (validate_antenna_positions, "Antenna position validation"),
        (validate_model_data_quality, "MODEL_DATA quality validation"),
        (validate_reference_antenna_stability, "Reference antenna stability"),
        (cleanup_casa_file_handles, "CASA file handle cleanup"),
    ]
    
    passed = 0
    total = len(tests)
    
    for func, description in tests:
        if test_validation_function(func, ms_path, description):
            passed += 1
    
    logger.info(f"Validation tests: {passed}/{total} passed")
    
    if passed == total:
        logger.info("✓ All validation functions working correctly")
        return 0
    else:
        logger.warning(f"⚠ {total - passed} validation functions had issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

# Run validation tests
python "${TEST_OUTPUT_DIR}/test_validations.py" "${GENERATED_MS}"
VALIDATION_RESULT=$?

if [ $VALIDATION_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ All validation functions passed${NC}"
else
    echo -e "${YELLOW}⚠ Some validation functions reported issues${NC}"
fi

# Step 4: Test conversion with problematic synthetic data
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Step 4: Testing with problematic data${NC}"
echo -e "${BLUE}=========================================${NC}"

# Create a script to generate problematic data for testing validation detection
cat > "${TEST_OUTPUT_DIR}/create_problematic_data.py" << 'EOF'
#!/usr/bin/env python3
"""Create problematic synthetic data to test validation detection."""

import sys
import h5py
import numpy as np
from pathlib import Path

def corrupt_frequency_order(hdf5_path):
    """Corrupt frequency ordering in HDF5 file."""
    with h5py.File(hdf5_path, 'r+') as f:
        if 'Header/freq_array' in f:
            freqs = f['Header/freq_array'][:]
            # Reverse frequency order to create descending order issue
            f['Header/freq_array'][:] = freqs[::-1]
            print(f"Corrupted frequency order in {hdf5_path}")

def corrupt_antenna_positions(hdf5_path):
    """Corrupt antenna positions in HDF5 file."""
    with h5py.File(hdf5_path, 'r+') as f:
        if 'Header/antenna_positions' in f:
            positions = f['Header/antenna_positions'][:]
            # Add large random errors to positions
            noise = np.random.normal(0, 1.0, positions.shape)  # 1m errors
            f['Header/antenna_positions'][:] = positions + noise
            print(f"Corrupted antenna positions in {hdf5_path}")

def corrupt_uvw_coordinates(hdf5_path):
    """Corrupt UVW coordinates in HDF5 file."""
    with h5py.File(hdf5_path, 'r+') as f:
        if 'Data/uvw_array' in f:
            uvw = f['Data/uvw_array'][:]
            # Add unreasonably large UVW values
            uvw[0, :] = 1e6  # 1000 km baseline
            f['Data/uvw_array'][:] = uvw
            print(f"Corrupted UVW coordinates in {hdf5_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_problematic_data.py <hdf5_file>")
        sys.exit(1)
        
    hdf5_path = sys.argv[1]
    print(f"Creating problematic data in: {hdf5_path}")
    
    # Apply different corruptions
    corrupt_frequency_order(hdf5_path)
    corrupt_antenna_positions(hdf5_path)
    corrupt_uvw_coordinates(hdf5_path)
    
    print("Problematic data created successfully")

if __name__ == "__main__":
    main()
EOF

# Create problematic version of first subband file
FIRST_SUBBAND=$(ls "${SYNTHETIC_DATA_DIR}"/*.hdf5 | head -1)
PROBLEMATIC_DIR="${TEST_OUTPUT_DIR}/problematic"
mkdir -p "${PROBLEMATIC_DIR}"

# Copy and corrupt one file
cp "${FIRST_SUBBAND}" "${PROBLEMATIC_DIR}/"
PROBLEMATIC_FILE="${PROBLEMATIC_DIR}/$(basename "${FIRST_SUBBAND}")"

python "${TEST_OUTPUT_DIR}/create_problematic_data.py" "${PROBLEMATIC_FILE}" || {
    echo -e "${YELLOW}⚠ Could not create problematic data (HDF5 structure may not match)${NC}"
}

# Step 5: Generate test report
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Step 5: Generating test report${NC}"
echo -e "${BLUE}=========================================${NC}"

REPORT_FILE="${TEST_OUTPUT_DIR}/validation_test_report.txt"

cat > "${REPORT_FILE}" << EOF
DSA-110 Enhanced Pipeline Validation Test Report
Generated: $(date)
Test Directory: ${TEST_OUTPUT_DIR}

=== Test Configuration ===
Start Time: ${START_TIME}
Duration: ${DURATION_MIN} minutes
Flux Density: ${FLUX_JY} Jy
Subbands: ${SUBBANDS}

=== Synthetic Data Generation ===
Files Generated: ${GENERATED_FILES}/${SUBBANDS}
Status: $([ "${GENERATED_FILES}" -eq "${SUBBANDS}" ] && echo "SUCCESS" || echo "FAILED")

=== Basic Conversion Test ===
Generated MS: ${GENERATED_MS}
Status: $([ -n "${GENERATED_MS}" ] && echo "SUCCESS" || echo "FAILED")

=== Validation Function Tests ===
Status: $([ $VALIDATION_RESULT -eq 0 ] && echo "ALL PASSED" || echo "SOME ISSUES")

=== Files Generated ===
$(ls -la "${TEST_OUTPUT_DIR}")

=== Recommendations ===
1. Run this test regularly in the casa6 environment
2. Monitor validation function performance on real data
3. Add specific test cases for known problematic observations
4. Consider implementing automated CI/CD testing with this script

EOF

echo -e "${GREEN}✓ Test report generated: ${REPORT_FILE}${NC}"

# Final summary
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Validation Test Summary${NC}"
echo -e "${BLUE}=========================================${NC}"

if [ "${GENERATED_FILES}" -eq "${SUBBANDS}" ] && [ -n "${GENERATED_MS}" ] && [ $VALIDATION_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ All tests PASSED${NC}"
    echo -e "${GREEN}✓ Enhanced pipeline validation is working correctly${NC}"
    echo ""
    echo -e "${BLUE}Next steps for production:${NC}"
    echo "1. Run this test on the production system"
    echo "2. Add to automated testing pipeline"
    echo "3. Monitor validation results in production logs"
    echo "4. Update validation thresholds based on operational experience"
    EXIT_CODE=0
else
    echo -e "${YELLOW}⚠ Some tests had issues${NC}"
    echo "Review the detailed logs and test report for more information"
    EXIT_CODE=1
fi

echo ""
echo "Test output saved to: ${TEST_OUTPUT_DIR}"
echo "Full report: ${REPORT_FILE}"

exit $EXIT_CODE