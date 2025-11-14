#!/bin/bash
# Example script for running batch conversion
# This demonstrates how to process multiple time windows in batch mode

set -euo pipefail

# CRITICAL: Source casa6 environment enforcement
# This ensures casa6 is always used for Python and related tools
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/casa6-env.sh" ]]; then
    source "${SCRIPT_DIR}/casa6-env.sh"
else
    echo "ERROR: casa6-env.sh not found. Cannot enforce casa6 environment." >&2
    exit 1
fi

# Configuration
INPUT_DIR="/data/incoming"
OUTPUT_DIR="/stage/dsa110-contimg/ms"
PRODUCTS_DB="/data/dsa110-contimg/state/products.sqlite3"

# Use casa6 paths (now set by casa6-env.sh)
PYTHON_BIN="${CASA6_PYTHON}"
SQLITE3_BIN="${CASA6_SQLITE3}"

# Example 1: Process a specific time window (batch processing)
# This will discover and convert all complete subband groups in the time window
echo "=== Example 1: Batch conversion for a time window ==="
echo "Processing time window: 2025-10-02 00:00:00 to 2025-10-02 01:00:00"
echo ""

$PYTHON_BIN -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    "$INPUT_DIR" \
    "$OUTPUT_DIR" \
    "2025-10-02 00:00:00" \
    "2025-10-02 01:00:00" \
    --writer parallel-subband \
    --stage-to-tmpfs \
    --max-workers 4 \
    --log-level INFO

echo ""
echo "=== Conversion complete ==="
echo "MS files written to: $OUTPUT_DIR"
echo ""

# Verify conversion in database (if available)
# Note: sqlite3() function from casa6-env.sh automatically uses casa6's sqlite3
if [[ -f "$PRODUCTS_DB" ]]; then
    echo "=== Checking database for converted files ==="
    sqlite3 "$PRODUCTS_DB" \
        "SELECT path, start_mjd, status FROM ms_index WHERE path LIKE '%2025-10-02%' ORDER BY start_mjd LIMIT 5;" 2>/dev/null || \
        echo "Note: Could not query database (this is OK if database doesn't exist yet)"
    echo ""
fi

# Example 2: Process using calibrator transit mode
# This finds the calibrator transit automatically and processes that window
echo "=== Example 2: Calibrator transit mode (commented out) ==="
echo "# Uncomment to use:"
echo "# $PYTHON_BIN -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \\"
echo "#     \"$INPUT_DIR\" \\"
echo "#     \"$OUTPUT_DIR\" \\"
echo "#     --calibrator 0834+555 \\"
echo "#     --window-minutes 60 \\"
echo "#     --writer parallel-subband \\"
echo "#     --stage-to-tmpfs"
echo ""

# Example 3: Dry run to see what would be processed
echo "=== Example 3: Dry run (check what would be processed) ==="
echo "Run with --dry-run to see what would be converted:"
echo "$PYTHON_BIN -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \\"
echo "    \"$INPUT_DIR\" \\"
echo "    \"$OUTPUT_DIR\" \\"
echo "    \"2025-10-02 00:00:00\" \\"
echo "    \"2025-10-02 01:00:00\" \\"
echo "    --dry-run"
echo ""

