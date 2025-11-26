#!/bin/bash
# Automated disk cleanup script
# Enforces data retention policies from DIRECTORY_ARCHITECTURE.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/disk_cleanup_$(date +%Y%m%d_%H%M%S).log"

# Ensure log directory exists
mkdir -p "$PROJECT_ROOT/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Disk usage before cleanup
log "=== Disk Cleanup Started ==="
log "Disk usage BEFORE cleanup:"
df -h /data /stage / | tee -a "$LOG_FILE"

# 1. Staging data cleanup (7 day retention per DIRECTORY_ARCHITECTURE.md)
log ""
log "Cleaning staging data older than 7 days..."
if [ -d "/stage/dsa110-contimg" ]; then
    DELETED=0
    
    # Measurement sets
    while IFS= read -r -d '' ms; do
        log "Deleting MS: $ms"
        rm -rf "$ms"
        ((DELETED++))
    done < <(find /stage/dsa110-contimg/ms -name "*.ms" -type d -mtime +7 -print0 2>/dev/null || true)
    
    # Image files
    while IFS= read -r -d '' img; do
        log "Deleting image: $img"
        rm -rf "$img"
        ((DELETED++))
    done < <(find /stage/dsa110-contimg/images -name "*.img" -type d -mtime +7 -print0 2>/dev/null || true)
    
    # Temporary files
    find /stage/dsa110-contimg -name "*.tmp" -delete 2>&1 | tee -a "$LOG_FILE"
    
    log "Deleted $DELETED staging items (MS/images)"
else
    log "Staging directory not found: /stage/dsa110-contimg"
fi

# 2. Incoming data cleanup (30 day retention)
log ""
log "Cleaning incoming data older than 30 days..."
if [ -d "/data/incoming" ]; then
    DELETED_HDF5=$(find /data/incoming -name "*.hdf5" -mtime +30 -delete -print 2>/dev/null | wc -l)
    DELETED_UVH5=$(find /data/incoming -name "*.uvh5" -mtime +30 -delete -print 2>/dev/null | wc -l)
    log "Deleted $DELETED_HDF5 HDF5 files and $DELETED_UVH5 UVH5 files"
else
    log "Incoming directory not found: /data/incoming"
fi

# 3. Temporary files cleanup
log ""
log "Cleaning temporary files..."
if [ -d "/dev/shm" ]; then
    DELETED_TMP=$(find /dev/shm -name "dsa110*" -mtime +1 -delete -print 2>/dev/null | wc -l)
    log "Deleted $DELETED_TMP temporary files from /dev/shm"
fi

# 4. Old logs cleanup (90 day retention)
log ""
log "Cleaning old logs (90+ days)..."
if [ -d "$PROJECT_ROOT/logs" ]; then
    DELETED_LOGS=$(find "$PROJECT_ROOT/logs" -name "*.log" -mtime +90 -delete -print 2>/dev/null | wc -l)
    log "Deleted $DELETED_LOGS old log files"
fi

# 5. Clean frontend build artifacts if disk is critically full
DISK_USAGE_PERCENT=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE_PERCENT" -gt 90 ]; then
    log ""
    log "CRITICAL: Root disk > 90% full. Cleaning frontend build artifacts..."
    if [ -d "$PROJECT_ROOT/frontend/node_modules/.cache" ]; then
        rm -rf "$PROJECT_ROOT/frontend/node_modules/.cache"
        log "Deleted frontend cache"
    fi
fi

# 6. Report disk usage after cleanup
log ""
log "Disk usage AFTER cleanup:"
df -h /data /stage / | tee -a "$LOG_FILE"

# 7. Calculate space freed
log ""
log "=== Disk Cleanup Complete ==="
log "Log saved to: $LOG_FILE"

# 8. Alert if still critically full
DATA_USAGE=$(df -h /data | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DATA_USAGE" -gt 90 ]; then
    log "WARNING: /data still at ${DATA_USAGE}% after cleanup!"
    echo "ALERT: /data disk usage at ${DATA_USAGE}% after cleanup" >&2
    exit 1
fi

exit 0
