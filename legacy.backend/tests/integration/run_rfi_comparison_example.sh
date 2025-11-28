#!/bin/bash
#
# Example script to run RFI backend comparison test
#
# This compares AOFlagger vs CASA tfcrop+rflag for:
# - Execution speed (efficiency)
# - Flagging statistics (aggressiveness)
# - Calibration success rates (effectiveness)
#

set -e

# Ensure we're in casa6 environment
if [[ -z "$CONDA_DEFAULT_ENV" ]] || [[ "$CONDA_DEFAULT_ENV" != *"casa6"* ]]; then
    echo "Activating casa6 environment..."
    source /opt/miniforge/etc/profile.d/conda.sh
    conda activate /opt/miniforge/envs/casa6
fi

# Configuration
TEST_MS="/stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms"
REFANT="103"
OUTPUT_DIR="/data/dsa110-contimg/tests/integration/rfi_comparison_results"

# Ensure test MS exists
if [[ ! -d "$TEST_MS" ]]; then
    echo "Error: Test MS not found: $TEST_MS"
    echo "Please update TEST_MS variable in this script"
    exit 1
fi

echo "=========================================="
echo "RFI Backend Comparison Test"
echo "=========================================="
echo "Test MS: $TEST_MS"
echo "Reference Antenna: $REFANT"
echo "Output: $OUTPUT_DIR"
echo ""

# Ask user for test type
echo "Select test type:"
echo "1) Basic test - Flagging only (~5-10 minutes)"
echo "2) Full test - Flagging + Calibration (~30-60 minutes)"
read -p "Choice [1/2]: " choice

case $choice in
    1)
        echo "Running basic flagging comparison..."
        python /data/dsa110-contimg/tests/integration/test_rfi_backend_comparison.py \
            "$TEST_MS" \
            --refant "$REFANT" \
            --output-dir "$OUTPUT_DIR"
        ;;
    2)
        echo "Running full pipeline comparison (this will take a while)..."
        python /data/dsa110-contimg/tests/integration/test_rfi_backend_comparison.py \
            "$TEST_MS" \
            --refant "$REFANT" \
            --output-dir "$OUTPUT_DIR" \
            --full-pipeline
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Test completed!"
echo "=========================================="
echo ""
echo "Results saved to:"
LATEST_DIR=$(ls -dt "$OUTPUT_DIR"/test_* 2>/dev/null | head -1)
if [[ -n "$LATEST_DIR" ]]; then
    echo "  $LATEST_DIR"
    echo ""
    echo "Read the report:"
    echo "  cat $LATEST_DIR/comparison_report.txt"
    echo ""
    echo "Or view JSON results:"
    echo "  cat $LATEST_DIR/comparison_results.json | python -m json.tool"
fi

