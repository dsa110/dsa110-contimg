#!/bin/bash
# DSA-110 Continuum Imaging Pipeline - Automated Backup Script
#
# Performs automated backups of:
# - SQLite databases (hourly)
# - Calibration tables (daily)
#
# Usage: Add to crontab:
#   0 * * * * /data/dsa110-contimg/scripts/backup-cron.sh hourly
#   0 3 * * * /data/dsa110-contimg/scripts/backup-cron.sh daily

set -euo pipefail

# Configuration
BACKUP_ROOT="${BACKUP_DIR:-/stage/backups}"
PIPELINE_DB="${PIPELINE_DB:-/data/dsa110-contimg/state/db/pipeline.sqlite3}"
CALTABLES_DIR="${CALTABLES_DIR:-/products/caltables}"
RETENTION_DAYS_HOURLY=7
RETENTION_DAYS_DAILY=30
LOG_DIR="/data/dsa110-contimg/state/logs"
LOG_FILE="${LOG_DIR}/backup-$(date +%Y%m%d).log"

# Ensure directories exist
mkdir -p "${BACKUP_ROOT}/hourly" "${BACKUP_ROOT}/daily" "${LOG_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

backup_database() {
    local backup_dir="$1"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${backup_dir}/pipeline_${timestamp}.sqlite3"
    
    log "Starting database backup to ${backup_file}"
    
    # Use SQLite's online backup API via .backup command
    if sqlite3 "${PIPELINE_DB}" ".backup '${backup_file}'"; then
        # Compress the backup
        gzip "${backup_file}"
        local size
        size=$(du -h "${backup_file}.gz" | cut -f1)
        log "Database backup completed: ${backup_file}.gz (${size})"
        
        # Create latest symlink
        ln -sf "$(basename "${backup_file}.gz")" "${backup_dir}/pipeline_latest.sqlite3.gz"
        return 0
    else
        log "ERROR: Database backup failed!"
        return 1
    fi
}

backup_caltables() {
    local backup_dir="$1"
    local timestamp
    timestamp=$(date +%Y%m%d)
    local backup_file="${backup_dir}/caltables_${timestamp}.tar.gz"
    
    log "Starting caltables backup to ${backup_file}"
    
    if [ -d "${CALTABLES_DIR}" ]; then
        if tar -czf "${backup_file}" -C "$(dirname "${CALTABLES_DIR}")" "$(basename "${CALTABLES_DIR}")"; then
            local size
            size=$(du -h "${backup_file}" | cut -f1)
            log "Caltables backup completed: ${backup_file} (${size})"
            
            # Create latest symlink
            ln -sf "$(basename "${backup_file}")" "${backup_dir}/caltables_latest.tar.gz"
            return 0
        else
            log "ERROR: Caltables backup failed!"
            return 1
        fi
    else
        log "WARNING: Caltables directory ${CALTABLES_DIR} not found, skipping"
        return 0
    fi
}

cleanup_old_backups() {
    local backup_dir="$1"
    local retention_days="$2"
    local pattern="$3"
    
    log "Cleaning up backups older than ${retention_days} days in ${backup_dir}"
    
    find "${backup_dir}" -name "${pattern}" -type f -mtime "+${retention_days}" -delete 2>/dev/null || true
    
    local count
    count=$(find "${backup_dir}" -name "${pattern}" -type f | wc -l)
    log "Remaining ${pattern} backups: ${count}"
}

run_hourly() {
    log "=== Starting hourly backup ==="
    
    local hourly_dir="${BACKUP_ROOT}/hourly"
    backup_database "${hourly_dir}"
    cleanup_old_backups "${hourly_dir}" "${RETENTION_DAYS_HOURLY}" "pipeline_*.sqlite3.gz"
    
    log "=== Hourly backup complete ==="
}

run_daily() {
    log "=== Starting daily backup ==="
    
    local daily_dir="${BACKUP_ROOT}/daily"
    
    # Full database backup (not hourly incremental)
    backup_database "${daily_dir}"
    
    # Caltables backup (only daily)
    backup_caltables "${daily_dir}"
    
    # Cleanup
    cleanup_old_backups "${daily_dir}" "${RETENTION_DAYS_DAILY}" "pipeline_*.sqlite3.gz"
    cleanup_old_backups "${daily_dir}" "${RETENTION_DAYS_DAILY}" "caltables_*.tar.gz"
    
    log "=== Daily backup complete ==="
}

# Main entry point
case "${1:-hourly}" in
    hourly)
        run_hourly
        ;;
    daily)
        run_daily
        ;;
    *)
        echo "Usage: $0 {hourly|daily}"
        exit 1
        ;;
esac
