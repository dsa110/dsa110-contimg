#!/bin/bash
# Run all three masked self-calibration tests in background
# Tests will continue even if terminal is disconnected

set -e

export PYTHONPATH=/data/dsa110-contimg/src/dsa110_contimg/src
cd /data/dsa110-contimg

LOG_DIR=/stage/dsa110-contimg/test_data
mkdir -p "${LOG_DIR}"

echo "========================================"
echo "MASKED SELF-CALIBRATION TEST SUITE"
echo "Running in background with nohup..."
echo "========================================"
echo ""

# Test 1: 10 mJy (fastest)
echo "Starting Test 1: 10 mJy flux limit..."
nohup python -u scripts/test_selfcal_masked.py --flux-limit 10.0 \
    > "${LOG_DIR}/selfcal_masked_10mJy.log" 2>&1 &
PID1=$!
echo "  PID: $PID1"
echo "  Log: ${LOG_DIR}/selfcal_masked_10mJy.log"

# Test 2: 1 mJy (moderate)
echo "Starting Test 2: 1 mJy flux limit..."
nohup python -u scripts/test_selfcal_masked.py --flux-limit 1.0 \
    > "${LOG_DIR}/selfcal_masked_1mJy.log" 2>&1 &
PID2=$!
echo "  PID: $PID2"
echo "  Log: ${LOG_DIR}/selfcal_masked_1mJy.log"

# Test 3: 0.1 mJy (slowest)
echo "Starting Test 3: 0.1 mJy flux limit..."
nohup python -u scripts/test_selfcal_masked.py --flux-limit 0.1 \
    > "${LOG_DIR}/selfcal_masked_0.1mJy.log" 2>&1 &
PID3=$!
echo "  PID: $PID3"
echo "  Log: ${LOG_DIR}/selfcal_masked_0.1mJy.log"

echo ""
echo "========================================"
echo "All tests started in background!"
echo "========================================"
echo ""
echo "Monitor progress:"
echo "  tail -f ${LOG_DIR}/selfcal_masked_10mJy.log"
echo "  tail -f ${LOG_DIR}/selfcal_masked_1mJy.log"
echo "  tail -f ${LOG_DIR}/selfcal_masked_0.1mJy.log"
echo ""
echo "Check status:"
echo "  ps aux | grep test_selfcal_masked"
echo ""
echo "PIDs: $PID1 (10mJy), $PID2 (1mJy), $PID3 (0.1mJy)"
echo ""

