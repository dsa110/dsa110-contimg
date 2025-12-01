#!/bin/bash
# Install Cron Jobs for DSA-110 Continuum Imaging Pipeline
#
# This script sets up scheduled tasks for:
# 1. Daily storage reconciliation (2am)
# 2. Hourly health checks (every hour at :15)
#
# Usage:
#   ./install-cron-jobs.sh [--dry-run]

set -e

CRON_USER="${CRON_USER:-ubuntu}"
SCRIPT_DIR="/data/dsa110-contimg/scripts"
LOG_DIR="/data/dsa110-contimg/state/logs"
CONDA_INIT="/opt/miniforge/etc/profile.d/conda.sh"

DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
fi

echo "Installing cron jobs for DSA-110 Continuum Imaging Pipeline..."
echo ""

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Define cron entries
CRON_ENTRIES="
# DSA-110 Continuum Imaging Pipeline - Storage Reconciliation
# Run daily at 2am to validate and reconcile HDF5 database
0 2 * * * ${SCRIPT_DIR}/storage-reconciliation.sh >> ${LOG_DIR}/storage-reconciliation.log 2>&1

# DSA-110 Continuum Imaging Pipeline - Health Check
# Run hourly at :15 to check service health and trigger alerts
15 * * * * source ${CONDA_INIT} && conda activate casa6 && curl -s -X POST http://localhost:8000/api/calibrator-imaging/alerts/evaluate >> ${LOG_DIR}/health-check.log 2>&1
"

echo "Proposed cron entries:"
echo "========================"
echo "$CRON_ENTRIES"
echo "========================"
echo ""

if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY-RUN] Would install the above cron entries for user: $CRON_USER"
    exit 0
fi

# Get existing crontab (if any)
EXISTING_CRONTAB=$(crontab -l -u "$CRON_USER" 2>/dev/null || true)

# Check if our entries already exist
if echo "$EXISTING_CRONTAB" | grep -q "storage-reconciliation.sh"; then
    echo "Storage reconciliation cron job already exists, skipping..."
else
    echo "Adding storage reconciliation cron job..."
fi

# Create new crontab with our entries (avoiding duplicates)
{
    # Keep existing entries that are NOT our jobs
    echo "$EXISTING_CRONTAB" | grep -v "storage-reconciliation.sh" | grep -v "alerts/evaluate" || true
    # Add our entries
    echo "$CRON_ENTRIES"
} | crontab -u "$CRON_USER" -

echo "✓ Cron jobs installed successfully"
echo ""
echo "To verify, run: crontab -l"
echo "To view logs: tail -f ${LOG_DIR}/storage-reconciliation.log"
