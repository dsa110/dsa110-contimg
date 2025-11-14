#!/bin/bash
# Health check script for CASA Log Daemon
# Returns 0 if healthy, 1 if unhealthy

set -e

SOURCE_ROOT="${1:-/data/dsa110-contimg}"
TARGET_ROOT="${2:-/data/dsa110-contimg/state/logs}"
LOG_FILE="${TARGET_ROOT}/casa_log_daemon_health_$(date +%Y%m%d).log"
STATUS_FILE="${TARGET_ROOT}/.casa_log_daemon_status.json"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Function to write status JSON
write_status() {
    local healthy=$1
    local issues="$2"
    local file_count=$3
    local daemon_running=$4
    
    cat > "$STATUS_FILE" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "healthy": $healthy,
  "issues": $(echo "$issues" | jq -R -s 'split("\n") | map(select(. != ""))'),
  "file_count": $file_count,
  "daemon_running": $daemon_running,
  "target_directory": "$TARGET_ROOT",
  "source_root": "$SOURCE_ROOT"
}
EOF
}

# Check if daemon process is running
check_daemon_running() {
    if pgrep -f "casa_log_daemon_inotify.sh" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check if systemd service is active
check_systemd_service() {
    if systemctl is-active --quiet casa-log-daemon-inotify.service 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Check for accumulating files
check_file_accumulation() {
    local file_count=$(find "$SOURCE_ROOT" -type f -name "casa-*.log" -not -path "$TARGET_ROOT/*" 2>/dev/null | wc -l)
    echo $file_count
}

# Check if log file is being updated (daemon is active)
check_daemon_activity() {
    local log_file="${TARGET_ROOT}/casa_log_daemon_$(date +%Y%m%d).log"
    if [[ ! -f "$log_file" ]]; then
        return 1
    fi
    
    # Check if log was updated in last 10 minutes
    local age=$(($(date +%s) - $(stat -c %Y "$log_file" 2>/dev/null || echo 0)))
    if [[ $age -lt 600 ]]; then
        return 0
    else
        return 1
    fi
}

# Main health check
main() {
    local issues=""
    local healthy=true
    local file_count=0
    local daemon_running=false
    
    # Check daemon process
    if check_daemon_running; then
        daemon_running=true
        log "✓ Daemon process is running"
    else
        healthy=false
        issues="${issues}Daemon process not found\n"
        log "✗ Daemon process not found"
    fi
    
    # Check systemd service
    if check_systemd_service; then
        log "✓ Systemd service is active"
    else
        healthy=false
        issues="${issues}Systemd service not active\n"
        log "✗ Systemd service not active"
    fi
    
    # Check daemon activity
    if check_daemon_activity; then
        log "✓ Daemon log file is recent (active)"
    else
        healthy=false
        issues="${issues}Daemon log file is stale (>10 minutes old)\n"
        log "✗ Daemon log file is stale"
    fi
    
    # Check file accumulation
    file_count=$(check_file_accumulation)
    if [[ $file_count -gt 10 ]]; then
        healthy=false
        issues="${issues}Too many files accumulating: $file_count files\n"
        log "✗ Too many files accumulating: $file_count files"
    elif [[ $file_count -gt 0 ]]; then
        log "⚠ Some files pending: $file_count files (acceptable)"
    else
        log "✓ No files accumulating"
    fi
    
    # Check target directory exists and is writable
    if [[ ! -d "$TARGET_ROOT" ]]; then
        healthy=false
        issues="${issues}Target directory does not exist: $TARGET_ROOT\n"
        log "✗ Target directory does not exist"
    elif [[ ! -w "$TARGET_ROOT" ]]; then
        healthy=false
        issues="${issues}Target directory is not writable: $TARGET_ROOT\n"
        log "✗ Target directory is not writable"
    else
        log "✓ Target directory is accessible"
    fi
    
    # Write status
    write_status "$healthy" "$issues" "$file_count" "$daemon_running"
    
    # Exit with appropriate code
    if [[ "$healthy" == "true" ]]; then
        log "Health check: PASSED"
        exit 0
    else
        log "Health check: FAILED"
        log "Issues:"
        echo -e "$issues" | while read -r line; do
            [[ -n "$line" ]] && log "  - $line"
        done
        exit 1
    fi
}

main "$@"

