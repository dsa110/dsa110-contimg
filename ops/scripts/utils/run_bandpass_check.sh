#!/bin/bash
# Script to run bandpass solve and check flagged solutions
# Run this where CASA is available

set -e

MS_PATH="/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.ms"
FIELD="0"
REFANT="103"

cd /data/dsa110-contimg

echo "======================================================================"
echo "Solving Bandpass (NO pre-bandpass phase correction)"
echo "======================================================================"
echo "MS: $MS_PATH"
echo "Field: $FIELD"
echo "Refant: $REFANT"
echo ""

# Run bandpass solve using Python script
python3 scripts/solve_bandpass_only.py \
    --ms "$MS_PATH" \
    --field "$FIELD" \
    --refant "$REFANT" \
    --combine-spw \
    --bp-minsnr 3.0

echo ""
echo "======================================================================"
echo "Bandpass solve complete!"
echo "======================================================================"

