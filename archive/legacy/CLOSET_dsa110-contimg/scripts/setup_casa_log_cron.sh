#!/bin/bash
"""
Setup CASA log monitoring cron job.

This script sets up a cron job to run the CASA log monitor every 5 minutes
to move any CASA log files from the root directory to the casalogs directory.
"""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MONITOR_SCRIPT="$SCRIPT_DIR/casa_log_monitor.py"

echo "Setting up CASA log monitoring cron job..."
echo "Project root: $PROJECT_ROOT"
echo "Monitor script: $MONITOR_SCRIPT"

# Create the cron job entry
CRON_ENTRY="*/5 * * * * cd $PROJECT_ROOT && python $MONITOR_SCRIPT >> $PROJECT_ROOT/logs/casa_log_monitor.log 2>&1"

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "Cron job added successfully!"
echo "CASA log monitor will run every 5 minutes"
echo "Logs will be written to: $PROJECT_ROOT/logs/casa_log_monitor.log"

# Show current crontab
echo ""
echo "Current crontab:"
crontab -l
