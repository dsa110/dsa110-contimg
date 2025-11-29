#!/usr/bin/env bash
# Health Check Script for Absurd Worker Service
#
# Usage:
#   ./health_check_absurd.sh [--json] [--quiet]
#
# Exit codes:
#   0 - All checks passed (healthy)
#   1 - One or more checks failed (unhealthy)
#   2 - Critical failure (service down)
#
# Designed for use with monitoring systems (Prometheus, Nagios, etc.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SYSTEMD_DIR="${PROJECT_ROOT}/ops/systemd"
ENV_FILE="${SYSTEMD_DIR}/contimg.env"
SERVICE_NAME="contimg-absurd-worker"
PYTHON="/opt/miniforge/envs/casa6/bin/python"

# Parse arguments
JSON_OUTPUT=false
QUIET=false
for arg in "$@"; do
    case $arg in
        --json) JSON_OUTPUT=true ;;
        --quiet|-q) QUIET=true ;;
    esac
done

# Initialize result
OVERALL_STATUS="healthy"
CHECKS=()

log() {
    if [[ "${QUIET}" == "false" ]]; then
        echo "$1"
    fi
}

add_check() {
    local name="$1"
    local status="$2"
    local message="$3"
    
    CHECKS+=("{\"name\":\"${name}\",\"status\":\"${status}\",\"message\":\"${message}\"}")
    
    if [[ "${status}" == "fail" ]]; then
        OVERALL_STATUS="unhealthy"
    elif [[ "${status}" == "critical" ]]; then
        OVERALL_STATUS="critical"
    fi
}

# Check 1: Service Status
check_service_status() {
    log "Checking service status..."
    
    if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
        add_check "service_active" "pass" "Service is running"
    else
        add_check "service_active" "critical" "Service is not running"
        return 1
    fi
    
    # Check for recent restarts (more than 3 in last 10 minutes indicates issues)
    local restart_count
    restart_count=$(journalctl -u "${SERVICE_NAME}.service" --since "10 minutes ago" 2>/dev/null | grep -c "Started" || echo "0")
    
    if [[ "${restart_count}" -gt 3 ]]; then
        add_check "service_stability" "fail" "Service restarted ${restart_count} times in last 10 minutes"
    else
        add_check "service_stability" "pass" "Service stable (${restart_count} restarts in 10m)"
    fi
}

# Check 2: Database Connection
check_database() {
    log "Checking database connection..."
    
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    
    if ${PYTHON} -c "
import asyncio
import sys
sys.path.insert(0, '${PROJECT_ROOT}/backend/src')

from dsa110_contimg.absurd import AbsurdClient

async def check():
    client = AbsurdClient('${ABSURD_DATABASE_URL}')
    await client.connect()
    await client.close()

asyncio.run(check())
" 2>/dev/null; then
        add_check "database_connection" "pass" "Database connection OK"
    else
        add_check "database_connection" "critical" "Cannot connect to database"
    fi
}

# Check 3: Queue Health
check_queue_health() {
    log "Checking queue health..."
    
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    
    local stats
    stats=$(${PYTHON} -c "
import asyncio
import json
import sys
sys.path.insert(0, '${PROJECT_ROOT}/backend/src')

from dsa110_contimg.absurd import AbsurdClient

async def check():
    client = AbsurdClient('${ABSURD_DATABASE_URL}')
    await client.connect()
    stats = await client.get_queue_stats('${ABSURD_QUEUE_NAME:-dsa110-pipeline}')
    await client.close()
    print(json.dumps(stats))

asyncio.run(check())
" 2>/dev/null) || stats="{}"
    
    local pending claimed failed
    pending=$(echo "${stats}" | ${PYTHON} -c "import json,sys; d=json.load(sys.stdin); print(d.get('pending',0))" 2>/dev/null || echo "0")
    claimed=$(echo "${stats}" | ${PYTHON} -c "import json,sys; d=json.load(sys.stdin); print(d.get('claimed',0))" 2>/dev/null || echo "0")
    failed=$(echo "${stats}" | ${PYTHON} -c "import json,sys; d=json.load(sys.stdin); print(d.get('failed',0))" 2>/dev/null || echo "0")
    
    # Check for queue backlog (>100 pending is warning)
    if [[ "${pending}" -gt 100 ]]; then
        add_check "queue_backlog" "fail" "High backlog: ${pending} pending tasks"
    else
        add_check "queue_backlog" "pass" "Queue backlog OK (${pending} pending)"
    fi
    
    # Check for stuck tasks (claimed but not completing)
    if [[ "${claimed}" -gt 20 ]]; then
        add_check "stuck_tasks" "fail" "Possible stuck tasks: ${claimed} claimed"
    else
        add_check "stuck_tasks" "pass" "No stuck tasks (${claimed} claimed)"
    fi
    
    # Check failed task rate
    if [[ "${failed}" -gt 50 ]]; then
        add_check "failed_tasks" "fail" "High failure count: ${failed} failed"
    else
        add_check "failed_tasks" "pass" "Failure count OK (${failed} failed)"
    fi
}

# Check 4: Log Health
check_logs() {
    log "Checking log health..."
    
    local log_file="${PROJECT_ROOT}/state/logs/absurd-worker.err"
    
    if [[ ! -f "${log_file}" ]]; then
        add_check "error_log" "pass" "No error log (good)"
        return
    fi
    
    # Check for recent errors (last 5 minutes)
    local recent_errors
    recent_errors=$(find "${log_file}" -mmin -5 -exec wc -l {} \; 2>/dev/null | awk '{print $1}' || echo "0")
    
    if [[ "${recent_errors}" -gt 100 ]]; then
        add_check "error_rate" "fail" "High error rate: ${recent_errors} errors in 5 minutes"
    else
        add_check "error_rate" "pass" "Error rate OK (${recent_errors} in 5m)"
    fi
}

# Check 5: Disk Space
check_disk_space() {
    log "Checking disk space..."
    
    local usage
    usage=$(df "${PROJECT_ROOT}" | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [[ "${usage}" -gt 95 ]]; then
        add_check "disk_space" "critical" "Critical: ${usage}% disk used"
    elif [[ "${usage}" -gt 85 ]]; then
        add_check "disk_space" "fail" "Warning: ${usage}% disk used"
    else
        add_check "disk_space" "pass" "Disk OK (${usage}% used)"
    fi
}

# Check 6: Memory Usage
check_memory() {
    log "Checking memory usage..."
    
    local mem_used
    mem_used=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
    
    if [[ "${mem_used}" -gt 95 ]]; then
        add_check "memory" "critical" "Critical: ${mem_used}% memory used"
    elif [[ "${mem_used}" -gt 85 ]]; then
        add_check "memory" "fail" "Warning: ${mem_used}% memory used"
    else
        add_check "memory" "pass" "Memory OK (${mem_used}% used)"
    fi
}

# Run all checks
run_checks() {
    check_service_status || true
    check_database || true
    check_queue_health || true
    check_logs || true
    check_disk_space || true
    check_memory || true
}

# Output results
output_results() {
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    if [[ "${JSON_OUTPUT}" == "true" ]]; then
        # Join checks array
        local checks_json
        checks_json=$(IFS=,; echo "${CHECKS[*]}")
        
        cat << EOF
{
  "timestamp": "${timestamp}",
  "status": "${OVERALL_STATUS}",
  "service": "${SERVICE_NAME}",
  "checks": [${checks_json}]
}
EOF
    else
        echo ""
        echo "=== Absurd Worker Health Check ==="
        echo "Timestamp: ${timestamp}"
        echo "Status: ${OVERALL_STATUS}"
        echo ""
        echo "Checks:"
        for check in "${CHECKS[@]}"; do
            local name status message
            name=$(echo "${check}" | ${PYTHON} -c "import json,sys; print(json.load(sys.stdin)['name'])")
            status=$(echo "${check}" | ${PYTHON} -c "import json,sys; print(json.load(sys.stdin)['status'])")
            message=$(echo "${check}" | ${PYTHON} -c "import json,sys; print(json.load(sys.stdin)['message'])")
            
            case "${status}" in
                pass) echo "  :check: ${name}: ${message}" ;;
                fail) echo "  :cross: ${name}: ${message}" ;;
                critical) echo "  :cross::cross: ${name}: ${message}" ;;
            esac
        done
        echo ""
    fi
}

# Main
run_checks
output_results

# Exit with appropriate code
case "${OVERALL_STATUS}" in
    healthy) exit 0 ;;
    unhealthy) exit 1 ;;
    critical) exit 2 ;;
esac
