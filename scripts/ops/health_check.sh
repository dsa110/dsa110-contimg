#!/bin/bash
# System health monitoring script
# Sends alerts if critical thresholds are exceeded

set -euo pipefail

PROJECT_ROOT="/data/dsa110-contimg"
LOG_FILE="$PROJECT_ROOT/logs/health_check_$(date +%Y%m%d).log"

# Thresholds
DISK_WARNING=80
DISK_CRITICAL=90
LOAD_WARNING=6.0
LOAD_CRITICAL=10.0

# Alert configuration (modify for your environment)
ALERT_EMAIL="${ALERT_EMAIL:-ops@example.com}"
SEND_EMAIL=false  # Set to true to enable email alerts

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

send_alert() {
    local subject="$1"
    local message="$2"
    
    log "ALERT: $subject - $message"
    
    if [ "$SEND_EMAIL" = true ]; then
        echo "$message" | mail -s "DSA-110: $subject" "$ALERT_EMAIL"
    fi
}

# 1. Check disk space
check_disk() {
    local mount="$1"
    local usage_percent=$(df -h "$mount" | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$usage_percent" -ge "$DISK_CRITICAL" ]; then
        send_alert "CRITICAL: Disk ${mount}" "Disk usage at ${usage_percent}% (critical threshold: ${DISK_CRITICAL}%)"
        return 2
    elif [ "$usage_percent" -ge "$DISK_WARNING" ]; then
        send_alert "WARNING: Disk ${mount}" "Disk usage at ${usage_percent}% (warning threshold: ${DISK_WARNING}%)"
        return 1
    fi
    
    log "Disk ${mount}: ${usage_percent}% - OK"
    return 0
}

# 2. Check system load
check_load() {
    local load=$(cat /proc/loadavg | awk '{print $1}')
    local load_int=${load%.*}
    
    if (( $(echo "$load > $LOAD_CRITICAL" | bc -l) )); then
        send_alert "CRITICAL: System Load" "System load at ${load} (critical threshold: ${LOAD_CRITICAL})"
        return 2
    elif (( $(echo "$load > $LOAD_WARNING" | bc -l) )); then
        send_alert "WARNING: System Load" "System load at ${load} (warning threshold: ${LOAD_WARNING})"
        return 1
    fi
    
    log "System load: ${load} - OK"
    return 0
}

# 3. Check Absurd service
check_absurd() {
    if curl -sf http://localhost:8000/api/absurd/health > /dev/null 2>&1; then
        log "Absurd service: OK"
        return 0
    else
        send_alert "CRITICAL: Absurd Service" "Absurd service not responding at http://localhost:8000/api/absurd/health"
        return 2
    fi
}

# 4. Check database accessibility
check_database() {
    local db_path="$PROJECT_ROOT/state/db/products.sqlite3"
    
    if [ ! -f "$db_path" ]; then
        send_alert "CRITICAL: Database" "Database file not found: $db_path"
        return 2
    fi
    
    if sqlite3 "$db_path" "SELECT 1;" > /dev/null 2>&1; then
        log "Database: OK"
        return 0
    else
        send_alert "CRITICAL: Database" "Database not accessible: $db_path"
        return 2
    fi
}

# Main health check
main() {
    log "=== Health Check Started ==="
    
    local exit_code=0
    
    # Check all systems
    check_disk "/data" || exit_code=$?
    check_disk "/stage" || exit_code=$?
    check_disk "/" || exit_code=$?
    check_load || exit_code=$?
    check_absurd || exit_code=$?
    check_database || exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log "=== Health Check Complete: All systems OK ==="
    elif [ $exit_code -eq 1 ]; then
        log "=== Health Check Complete: Warnings detected ==="
    else
        log "=== Health Check Complete: Critical issues detected ==="
    fi
    
    return $exit_code
}

main
