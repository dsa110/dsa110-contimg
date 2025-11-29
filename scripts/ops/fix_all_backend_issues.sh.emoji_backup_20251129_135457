#!/bin/bash
# Master script to fix all backend issues
# Runs all fixes in the correct order

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/fix_all_$(date +%Y%m%d_%H%M%S).log"

# Ensure log directory exists
mkdir -p "$PROJECT_ROOT/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Starting Backend Fixes ==="
log "Log file: $LOG_FILE"
log ""

# Step 1: Disk cleanup
log "Step 1: Disk Space Cleanup"
log "----------------------------------------"
if [ -f "$SCRIPT_DIR/cleanup_disk_space.sh" ]; then
    "$SCRIPT_DIR/cleanup_disk_space.sh" 2>&1 | tee -a "$LOG_FILE"
    log "✓ Disk cleanup complete"
else
    log "✗ cleanup_disk_space.sh not found"
fi
log ""

# Step 2: Schedule automated cleanup
log "Step 2: Schedule Automated Cleanup"
log "----------------------------------------"
if ! crontab -l 2>/dev/null | grep -q cleanup_disk_space; then
    (crontab -l 2>/dev/null; echo "0 2 * * * $SCRIPT_DIR/cleanup_disk_space.sh") | crontab -
    log "✓ Cleanup cron job added"
else
    log "✓ Cleanup cron job already exists"
fi
log ""

# Step 3: Backfill metadata
log "Step 3: Backfill Database Metadata"
log "----------------------------------------"
if [ -f "$SCRIPT_DIR/backfill_metadata.py" ]; then
    if [ -f "$SCRIPT_DIR/developer-setup.sh" ]; then
        source "$SCRIPT_DIR/developer-setup.sh"
    fi
    python "$SCRIPT_DIR/backfill_metadata.py" 2>&1 | tee -a "$LOG_FILE"
    log "✓ Metadata backfill complete"
else
    log "✗ backfill_metadata.py not found"
fi
log ""

# Step 4: Schedule health checks
log "Step 4: Schedule Health Monitoring"
log "----------------------------------------"
if [ -f "$SCRIPT_DIR/health_check.sh" ]; then
    if ! crontab -l 2>/dev/null | grep -q health_check; then
        (crontab -l 2>/dev/null; echo "*/30 * * * * $SCRIPT_DIR/health_check.sh") | crontab -
        log "✓ Health check cron job added"
    else
        log "✓ Health check cron job already exists"
    fi
    
    # Run health check once
    "$SCRIPT_DIR/health_check.sh" 2>&1 | tee -a "$LOG_FILE"
else
    log "✗ health_check.sh not found"
fi
log ""

# Step 5: Verify fixes
log "Step 5: Verification"
log "----------------------------------------"

# Check disk space
DATA_USAGE=$(df -h /data | tail -1 | awk '{print $5}' | sed 's/%//')
log "Disk /data usage: ${DATA_USAGE}%"
if [ "$DATA_USAGE" -lt 85 ]; then
    log "✓ Disk space OK"
else
    log "⚠ Disk space still high"
fi

# Check Absurd
if curl -sf http://localhost:8000/api/absurd/health > /dev/null 2>&1; then
    log "✓ Absurd service responding"
else
    log "⚠ Absurd service not responding (may need manual configuration)"
fi

# Check database
if [ -f "$PROJECT_ROOT/state/db/products.sqlite3" ]; then
    RESULT=$(sqlite3 "$PROJECT_ROOT/state/db/products.sqlite3" "SELECT COUNT(*), COUNT(name) FROM images;" 2>/dev/null || echo "0|0")
    TOTAL=$(echo $RESULT | cut -d'|' -f1)
    WITH_NAME=$(echo $RESULT | cut -d'|' -f2)
    log "Database: $WITH_NAME/$TOTAL images have metadata"
    if [ "$TOTAL" -eq 0 ] || [ "$WITH_NAME" -eq "$TOTAL" ]; then
        log "✓ Database metadata OK"
    else
        log "⚠ Some images missing metadata"
    fi
else
    log "⚠ Database not found"
fi

# Check system load
LOAD=$(cat /proc/loadavg | awk '{print $1}')
log "System load: $LOAD"
if (( $(echo "$LOAD < 6.0" | bc -l) )); then
    log "✓ System load OK"
else
    log "⚠ System load elevated"
fi

log ""
log "=== Backend Fixes Complete ==="
log "Log file: $LOG_FILE"
log ""
log "Next steps:"
log "1. Check Absurd configuration if it's not responding"
log "2. Review dashboard at http://localhost:3210/"
log "3. Monitor logs for any issues"
log "4. See docs/how-to/fix_backend_issues.md for detailed troubleshooting"
