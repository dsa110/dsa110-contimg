#!/usr/bin/env bash
#
# Basic DSA-110 synthetic data generation example
# Generates a single 5-minute observation with 16 subbands
#

set -e  # Exit on error

# Activate casa6 environment
echo "Activating casa6 environment..."
eval "$(conda shell.bash hook)"
conda activate casa6

# Set paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUTPUT_DIR="/tmp/dsa110_synthetic_test"

# Configuration
START_TIME="2025-10-06T12:00:00"
FLUX_JY=25.0
SUBBANDS=16

echo "========================================="
echo "DSA-110 Synthetic Data Generation"
echo "========================================="
echo "Output directory: ${OUTPUT_DIR}"
echo "Start time: ${START_TIME}"
echo "Flux density: ${FLUX_JY} Jy"
echo "Subbands: ${SUBBANDS}"
echo "========================================="

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Generate synthetic data
echo "Generating synthetic observation..."
python "${PROJECT_ROOT}/simulation/make_synthetic_uvh5.py" \
    --layout-meta "${PROJECT_ROOT}/simulation/config/reference_layout.json" \
    --telescope-config "${PROJECT_ROOT}/simulation/pyuvsim/telescope.yaml" \
    --output "${OUTPUT_DIR}" \
    --start-time "${START_TIME}" \
    --duration-minutes 5.0 \
    --flux-jy "${FLUX_JY}" \
    --subbands "${SUBBANDS}"

echo ""
echo "========================================="
echo "Generation complete!"
echo "========================================="
echo "Generated files:"
ls -lh "${OUTPUT_DIR}"/*.hdf5 | head -5
echo "... (${SUBBANDS} files total)"
echo ""
echo "To convert to Measurement Set:"
echo "  python src/dsa110_contimg/conversion/uvh5_to_ms_converter.py \\"
echo "      ${OUTPUT_DIR} \\"
echo "      /tmp/test_ms \\"
echo "      \"${START_TIME:0:10} 00:00:00\" \\"
echo "      \"${START_TIME:0:10} 23:59:59\""
echo ""
