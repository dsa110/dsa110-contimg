#!/bin/bash
# Monitor pipeline logs for calibrator-related errors

LOG_DIR="${LOG_DIR:-state/logs}"
DAYS_BACK="${DAYS_BACK:-7}"

echo "=== Pipeline Log Monitoring ==="
echo "Log directory: $LOG_DIR"
echo "Looking back: $DAYS_BACK days"
echo ""

# Find recent log files
echo "Recent log files:"
find "$LOG_DIR" -name "*.log" -type f -mtime -$DAYS_BACK 2>/dev/null | sort -r | head -10
echo ""

# Check for calibrator-related errors
echo "=== Calibrator-related Errors ==="
find "$LOG_DIR" -name "*.log" -type f -mtime -$DAYS_BACK -exec grep -l -iE "(calibrator|bandpass|bpcal)" {} \; 2>/dev/null | while read logfile; do
    echo "Checking: $logfile"
    grep -iE "(error|exception|fail|warning).*calibrator|calibrator.*error|calibrator.*exception|calibrator.*fail" "$logfile" 2>/dev/null | tail -5
done

echo ""
echo "=== Database-related Errors ==="
find "$LOG_DIR" -name "*.log" -type f -mtime -$DAYS_BACK -exec grep -l -iE "(database|sqlite|calibrators\.sqlite)" {} \; 2>/dev/null | while read logfile; do
    echo "Checking: $logfile"
    grep -iE "(error|exception|fail|locked|timeout).*database|database.*error|database.*exception" "$logfile" 2>/dev/null | tail -5
done

echo ""
echo "=== Recent Activity (last 20 lines) ==="
find "$LOG_DIR" -name "*.log" -type f -mtime -1 -exec ls -lt {} \; 2>/dev/null | head -1 | awk '{print $NF}' | xargs tail -20 2>/dev/null || echo "No recent logs found"

