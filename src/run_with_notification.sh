#!/bin/bash
# Wrapper script to run commands in background with error notification
# Usage: ./run_with_notification.sh <script> [args...]

set -euo pipefail

SCRIPT_PATH="${1:-}"
if [ -z "$SCRIPT_PATH" ]; then
    echo "Usage: $0 <script> [args...]" >&2
    exit 1
fi

shift  # Remove script path from args

# Create notification directory
NOTIFY_DIR="/data/dsa110-contimg/src/.notifications"
mkdir -p "$NOTIFY_DIR"

# Generate unique job ID
JOB_ID="job_$(date +%s)_$$"
LOG_FILE="$NOTIFY_DIR/${JOB_ID}.log"
STATUS_FILE="$NOTIFY_DIR/${JOB_ID}.status"
PID_FILE="$NOTIFY_DIR/${JOB_ID}.pid"

# Function to check job status and notify on error
check_job() {
    local pid=$1
    local job_id=$2
    
    # Poll for process completion
    while kill -0 "$pid" 2>/dev/null; do
        sleep 2
    done
    
    # Wait for process to finish and get exit code
    wait "$pid" 2>/dev/null || true
    local exit_code=$?
    
    # Write final status
    {
        echo "Exit code: $exit_code"
        echo "Completed at: $(date -Iseconds)"
    } >> "$STATUS_FILE"
    
    # Check log for errors (even if exit code is 0, Python syntax errors might not set it correctly)
    local has_error=false
    if [ $exit_code -ne 0 ]; then
        has_error=true
    elif grep -qiE "(error|exception|traceback|failed|syntaxerror)" "$LOG_FILE" 2>/dev/null; then
        has_error=true
        exit_code=1  # Override exit code if we found errors in log
    fi
    
    # Check for errors
    if [ "$has_error" = true ]; then
        {
            echo "Status: FAILED"
            echo ""
            echo "ERROR: Job $job_id failed with exit code $exit_code"
            echo "Check log: $LOG_FILE"
            echo "Check status: $STATUS_FILE"
        } >> "$STATUS_FILE"
        
        echo "ERROR: Job $job_id failed with exit code $exit_code" | tee -a "$LOG_FILE"
        
        # Write to error notifications log
        echo "[$(date -Iseconds)] Job $job_id FAILED (exit code: $exit_code)" >> "$NOTIFY_DIR/error_notifications.log"
        echo "  Script: $SCRIPT_PATH" >> "$NOTIFY_DIR/error_notifications.log"
        echo "  Log: $LOG_FILE" >> "$NOTIFY_DIR/error_notifications.log"
        echo "  Last 5 lines of log:" >> "$NOTIFY_DIR/error_notifications.log"
        tail -5 "$LOG_FILE" | sed 's/^/    /' >> "$NOTIFY_DIR/error_notifications.log"
        echo "---" >> "$NOTIFY_DIR/error_notifications.log"
        
        return 1
    else
        {
            echo "Status: SUCCESS"
        } >> "$STATUS_FILE"
        echo "SUCCESS: Job $job_id completed successfully" | tee -a "$LOG_FILE"
        return 0
    fi
}

# Start the job in background
echo "Starting job: $JOB_ID"
echo "Script: $SCRIPT_PATH"
echo "Args: $@"
echo "Log: $LOG_FILE"
echo "Status: $STATUS_FILE"
echo "PID: $$"

# Write initial status
cat > "$STATUS_FILE" <<EOF
Job ID: $JOB_ID
Script: $SCRIPT_PATH
Args: $@
Started: $(date -Iseconds)
Status: RUNNING
PID: $$
EOF

# Run the script in background, capturing both stdout and stderr
"$SCRIPT_PATH" "$@" > "$LOG_FILE" 2>&1 &
BG_PID=$!

# Save PID
echo "$BG_PID" > "$PID_FILE"

# Monitor the job in background
check_job "$BG_PID" "$JOB_ID" &
MONITOR_PID=$!

echo "Job running in background (PID: $BG_PID)"
echo "Monitor PID: $MONITOR_PID"
echo ""
echo "To check status:"
echo "  cat $STATUS_FILE"
echo "  tail -f $LOG_FILE"
echo ""
echo "To check for errors:"
echo "  grep -i error $LOG_FILE"
echo "  tail -20 $NOTIFY_DIR/error_notifications.log"

