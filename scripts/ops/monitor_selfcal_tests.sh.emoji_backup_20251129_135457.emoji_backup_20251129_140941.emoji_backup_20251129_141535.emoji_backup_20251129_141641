#!/bin/bash
# Monitor running masked self-calibration tests

LOG_DIR=/stage/dsa110-contimg/test_data

echo "========================================"
echo "MASKED SELF-CAL TEST MONITOR"
echo "========================================"
echo ""

# Check for running processes
echo "Running tests:"
ps aux | grep "test_selfcal_masked" | grep -v grep | while read line; do
    pid=$(echo "$line" | awk '{print $2}')
    flux=$(echo "$line" | grep -oP -- '--flux-limit \K[0-9.]+' || echo "unknown")
    echo "  PID $pid: flux-limit=$flux mJy"
done

if ! ps aux | grep "test_selfcal_masked" | grep -v grep > /dev/null; then
    echo "  No tests currently running"
fi

echo ""
echo "Log files:"
for log in "${LOG_DIR}"/selfcal_masked_*.log; do
    if [ -f "$log" ]; then
        size=$(du -h "$log" | cut -f1)
        lines=$(wc -l < "$log")
        last_update=$(stat -c %y "$log" | cut -d'.' -f1)
        echo "  $(basename "$log"): $size, $lines lines, updated: $last_update"
        
        # Show last status line
        if grep -q "✅ SUCCESS\|❌ FAILED" "$log"; then
            status=$(grep -E "✅ SUCCESS|❌ FAILED" "$log" | tail -1)
            echo "    Status: $status"
        elif grep -q "Iteration" "$log"; then
            iter=$(grep "Iteration" "$log" | tail -1)
            echo "    Progress: $iter"
        fi
    fi
done

echo ""
echo "Quick view commands:"
echo "  tail -f ${LOG_DIR}/selfcal_masked_10mJy.log"
echo "  tail -f ${LOG_DIR}/selfcal_masked_1mJy.log"
echo "  tail -f ${LOG_DIR}/selfcal_masked_0.1mJy.log"
echo ""

