#!/usr/bin/env bash
#
# Generate multiple observation groups for testing the streaming converter
# Creates 3 consecutive 5-minute observations (15 minutes total)
#

set -e

# Activate casa6 environment
eval "$(conda shell.bash hook)"
conda activate casa6

# Set paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUTPUT_DIR="/tmp/dsa110_multi_obs"

echo "========================================="
echo "Multi-Observation Generation"
echo "========================================="
echo "Output directory: ${OUTPUT_DIR}"
echo "Creating 3 observation groups (15 minutes total)"
echo "========================================="

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Generate 3 observation groups
for i in 0 5 10; do
    TIMESTAMP=$(printf "2025-10-06T12:%02d:00" ${i})
    echo ""
    echo "Generating observation ${TIMESTAMP}..."
    
    python "${PROJECT_ROOT}/simulation/make_synthetic_uvh5.py" \
        --layout-meta "${PROJECT_ROOT}/simulation/config/reference_layout.json" \
        --telescope-config "${PROJECT_ROOT}/simulation/pyuvsim/telescope.yaml" \
        --output "${OUTPUT_DIR}" \
        --start-time "${TIMESTAMP}" \
        --duration-minutes 5.0 \
        --flux-jy 25.0 \
        --subbands 16
done

echo ""
echo "========================================="
echo "Generation complete!"
echo "========================================="
echo "Total files generated: $(ls -1 ${OUTPUT_DIR}/*.hdf5 | wc -l)"
echo ""
echo "Observation groups:"
for timestamp in "2025-10-06T12:00:00" "2025-10-06T12:05:00" "2025-10-06T12:10:00"; do
    count=$(ls -1 "${OUTPUT_DIR}/${timestamp}"_sb*.hdf5 2>/dev/null | wc -l)
    echo "  ${timestamp}: ${count} subbands"
done
echo ""
echo "To test with streaming converter:"
echo "  python pipeline/pipeline/core/conversion/streaming_converter.py \\"
echo "      --input-dir ${OUTPUT_DIR} \\"
echo "      --output-dir /tmp/test_ms \\"
echo "      --chunk-duration 5.0"
echo ""
