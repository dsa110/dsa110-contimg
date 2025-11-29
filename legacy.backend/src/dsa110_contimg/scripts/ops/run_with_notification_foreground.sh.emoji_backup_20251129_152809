#!/bin/bash
# Wrapper script to run commands with error notification (foreground version for AI agents)
# This version waits for completion so the AI agent can see the result
# Usage: ./run_with_notification_foreground.sh <script> [args...]

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

# Write initial status
cat > "$STATUS_FILE" <<EOF
Job ID: $JOB_ID
Script: $SCRIPT_PATH
Args: $@
Started: $(date -Iseconds)
Status: RUNNING
PID: $$
EOF

echo "Starting job: $JOB_ID"
echo "Script: $SCRIPT_PATH"
echo "Log: $LOG_FILE"
echo ""

# Run the script, capturing both stdout and stderr
"$SCRIPT_PATH" "$@" > "$LOG_FILE" 2>&1 &
BG_PID=$!

# Save PID
echo "$BG_PID" > "$PID_FILE"

# Wait for the job to complete (this keeps the AI agent "alive")
wait "$BG_PID" 2>/dev/null || true
EXIT_CODE=$?

# Write final status
{
    echo "Exit code: $EXIT_CODE"
    echo "Completed at: $(date -Iseconds)"
} >> "$STATUS_FILE"

# Check log for errors
HAS_ERROR=false
if [ $EXIT_CODE -ne 0 ]; then
    HAS_ERROR=true
elif grep -qiE "(error|exception|traceback|failed|syntaxerror)" "$LOG_FILE" 2>/dev/null; then
    HAS_ERROR=true
    EXIT_CODE=1
fi

# Report results
echo "=========================================="
if [ "$HAS_ERROR" = true ]; then
    echo "✗ JOB FAILED (exit code: $EXIT_CODE)"
    echo ""
    echo "Status: FAILED" >> "$STATUS_FILE"
    echo "ERROR: Job $JOB_ID failed" >> "$STATUS_FILE"
    
    # Write to error notifications log
    echo "[$(date -Iseconds)] Job $JOB_ID FAILED (exit code: $EXIT_CODE)" >> "$NOTIFY_DIR/error_notifications.log"
    echo "  Script: $SCRIPT_PATH" >> "$NOTIFY_DIR/error_notifications.log"
    echo "  Log: $LOG_FILE" >> "$NOTIFY_DIR/error_notifications.log"
    echo "---" >> "$NOTIFY_DIR/error_notifications.log"
    
    echo "Error details:"
    echo "  Log file: $LOG_FILE"
    echo "  Status file: $STATUS_FILE"
    echo ""
    echo "Last 20 lines of log:"
    echo "----------------------------------------"
    tail -20 "$LOG_FILE" | sed 's/^/  /'
    echo "----------------------------------------"
    exit $EXIT_CODE
else
    echo "✓ JOB SUCCEEDED"
    echo ""
    echo "Status: SUCCESS" >> "$STATUS_FILE"
    echo "Log file: $LOG_FILE"
    echo "Status file: $STATUS_FILE"
    exit 0
fi

