#!/bin/bash
# Check status of background jobs
# Usage: ./check_job_status.sh [job_id]

NOTIFY_DIR="/data/dsa110-contimg/src/.notifications"

if [ $# -eq 0 ]; then
    # List all jobs
    echo "=== All Background Jobs ==="
    for status_file in "$NOTIFY_DIR"/*.status; do
        if [ -f "$status_file" ]; then
            job_id=$(basename "$status_file" .status)
            echo ""
            echo "Job: $job_id"
            cat "$status_file"
            echo "---"
        fi
    done
    
    # Check for recent errors
    if [ -f "$NOTIFY_DIR/error_notifications.log" ]; then
        echo ""
        echo "=== Recent Errors ==="
        tail -10 "$NOTIFY_DIR/error_notifications.log"
    fi
else
    # Check specific job
    JOB_ID="$1"
    STATUS_FILE="$NOTIFY_DIR/${JOB_ID}.status"
    LOG_FILE="$NOTIFY_DIR/${JOB_ID}.log"
    PID_FILE="$NOTIFY_DIR/${JOB_ID}.pid"
    
    if [ ! -f "$STATUS_FILE" ]; then
        echo "Job $JOB_ID not found" >&2
        exit 1
    fi
    
    echo "=== Job Status: $JOB_ID ==="
    cat "$STATUS_FILE"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo ""
            echo "Process is still running (PID: $PID)"
        else
            echo ""
            echo "Process has completed"
        fi
    fi
    
    if [ -f "$LOG_FILE" ]; then
        echo ""
        echo "=== Recent Log Output ==="
        tail -20 "$LOG_FILE"
    fi
fi

