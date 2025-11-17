#!/bin/bash
# Monitor for CASA log files in workspace root directory
# Exit if any are found

ROOT_DIR="/data/dsa110-contimg/src"
LOG_DIR="/data/dsa110-contimg/state/logs"
MONITOR_INTERVAL=5  # seconds

echo "Monitoring for CASA log files in workspace root..."
echo "Root directory: $ROOT_DIR"
echo "Expected log directory: $LOG_DIR"
echo "Monitoring interval: ${MONITOR_INTERVAL}s"
echo "Press Ctrl+C to stop"
echo ""

# Count initial log files
initial_count=$(find "$ROOT_DIR" -maxdepth 1 -name "casa-*.log" -o -name "casalog.xml" 2>/dev/null | wc -l)
echo "Initial CASA log files in root: $initial_count"

while true; do
    current_count=$(find "$ROOT_DIR" -maxdepth 1 -name "casa-*.log" -o -name "casalog.xml" 2>/dev/null | wc -l)
    
    if [ "$current_count" -gt "$initial_count" ]; then
        echo ""
        echo "⚠️  ALERT: New CASA log file(s) detected in workspace root!"
        echo "Files found:"
        find "$ROOT_DIR" -maxdepth 1 -name "casa-*.log" -o -name "casalog.xml" 2>/dev/null | while read -r file; do
            echo "  - $file"
            ls -lh "$file" 2>/dev/null
        done
        echo ""
        echo "Expected location: $LOG_DIR"
        echo "Files in expected location:"
        find "$LOG_DIR" -name "casa-*.log" -o -name "casalog.xml" 2>/dev/null | head -5
        exit 1
    fi
    
    # Show status every 30 seconds
    if [ $(($(date +%s) % 30)) -eq 0 ]; then
        log_dir_count=$(find "$LOG_DIR" -name "casa-*.log" -o -name "casalog.xml" 2>/dev/null | wc -l)
        echo "[$(date +%H:%M:%S)] Root: $current_count, Log dir: $log_dir_count"
    fi
    
    sleep "$MONITOR_INTERVAL"
done

