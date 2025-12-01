#!/bin/bash
# Storage Reconciliation Cron Script
# 
# This script runs daily to validate and optionally reconcile the HDF5 database
# with the filesystem storage. It:
# 1. Computes storage metrics
# 2. Logs sync status
# 3. Optionally reconciles discrepancies
# 4. Triggers alerts if sync is below threshold
#
# Usage:
#   ./storage-reconciliation.sh [--reconcile] [--threshold PERCENT]
#
# Install cron entry:
#   0 2 * * * /data/dsa110-contimg/scripts/storage-reconciliation.sh >> /data/dsa110-contimg/state/logs/storage-reconciliation.log 2>&1

set -e

# Configuration
HDF5_DB="${HDF5_DB:-/data/dsa110-contimg/state/db/hdf5.sqlite3}"
INCOMING_DIR="${INCOMING_DIR:-/data/incoming}"
LOG_DIR="${LOG_DIR:-/data/dsa110-contimg/state/logs}"
SYNC_THRESHOLD="${SYNC_THRESHOLD:-95.0}"
API_URL="${API_URL:-http://localhost:8000/api/v1/calibrator-imaging}"

# Parse arguments
DO_RECONCILE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --reconcile)
            DO_RECONCILE=true
            shift
            ;;
        --threshold)
            SYNC_THRESHOLD="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Activate conda environment
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Create log directory if needed
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date -Is)
echo "=========================================="
echo "Storage Reconciliation - $TIMESTAMP"
echo "=========================================="

# Run validation
echo "[INFO] Running storage validation..."
METRICS=$(python3 -c "
import json
from dsa110_contimg.database.storage_validator import get_storage_metrics

metrics = get_storage_metrics('$HDF5_DB', '$INCOMING_DIR')
print(json.dumps(metrics, indent=2))
")

echo "$METRICS"

# Extract sync percentage
SYNC_PCT=$(echo "$METRICS" | python3 -c "
import sys, json
m = json.load(sys.stdin)
if m['files_on_disk'] == 0:
    print('100.0')
else:
    print(f\"{(m['files_in_db_stored'] / m['files_on_disk']) * 100:.2f}\")
")

echo "[INFO] Sync percentage: ${SYNC_PCT}%"

# Check if below threshold
BELOW_THRESHOLD=$(python3 -c "print('yes' if float('$SYNC_PCT') < float('$SYNC_THRESHOLD') else 'no')")

if [ "$BELOW_THRESHOLD" = "yes" ]; then
    echo "[WARN] Sync percentage ${SYNC_PCT}% is below threshold ${SYNC_THRESHOLD}%"
    
    # Trigger alert via API
    echo "[INFO] Triggering alert evaluation..."
    curl -s -X POST "$API_URL/alerts/evaluate" -H "Content-Type: application/json" || echo "[WARN] Failed to trigger alert (API may be down)"
fi

# Run reconciliation if requested
if [ "$DO_RECONCILE" = "true" ]; then
    echo "[INFO] Running reconciliation..."
    python3 -c "
from dsa110_contimg.database.storage_validator import reconcile_storage

result = reconcile_storage('$HDF5_DB', '$INCOMING_DIR')
print(f'Indexed {result[\"files_added\"]} new files')
print(f'Marked {result[\"records_marked_removed\"]} records as removed')
"
    echo "[INFO] Reconciliation complete"
fi

echo "[INFO] Done"
echo ""
