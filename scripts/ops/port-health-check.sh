#!/bin/bash
# port-health-check.sh - Verify port reservation system is healthy
# Usage: ./port-health-check.sh [--fix]
#
# Checks:
# 1. claim-port.sh exists and is executable
# 2. All configured services have port claiming enabled
# 3. All services are running on their assigned ports
# 4. No port conflicts exist

set -o pipefail

FIX_MODE=false
[ "$1" = "--fix" ] && FIX_MODE=true

ERRORS=0
WARNINGS=0

log_ok() { echo "✓ $1"; }
log_warn() { echo "⚠ $1"; ((WARNINGS++)); }
log_err() { echo "✗ $1"; ((ERRORS++)); }

echo "=== Port Reservation Health Check ==="
echo ""

# 1. Check claim-port.sh exists
echo "--- Script Availability ---"
if [ -x /usr/local/bin/claim-port.sh ]; then
    log_ok "claim-port.sh is installed and executable"
else
    log_err "claim-port.sh not found or not executable"
fi

# 2. Check lsof dependency
if command -v lsof &>/dev/null; then
    log_ok "lsof is available"
else
    log_err "lsof is not installed (required by claim-port.sh)"
fi

# 3. Run self-tests
echo ""
echo "--- Self-Tests ---"
if /usr/local/bin/claim-port.sh --test &>/dev/null; then
    log_ok "claim-port.sh self-tests pass"
else
    log_err "claim-port.sh self-tests failed"
fi

# 4. Check systemd configurations
echo ""
echo "--- Systemd Configuration ---"

declare -A SERVICES=(
    ["dsa110-api"]="8000"
    ["prometheus"]="9090"
    ["grafana-simple"]="3030"
    ["redis-server"]="6379"
)

for svc in "${!SERVICES[@]}"; do
    port="${SERVICES[$svc]}"
    
    # Check if service has claim-port configured
    if systemctl cat "$svc" 2>/dev/null | grep -q "ExecStartPre=.*claim-port.sh $port"; then
        # Check for + prefix (root execution)
        if systemctl cat "$svc" 2>/dev/null | grep -q "ExecStartPre=+.*claim-port.sh"; then
            log_ok "$svc: port $port claiming configured (runs as root)"
        else
            log_warn "$svc: port $port claiming configured but missing + prefix"
        fi
    else
        log_err "$svc: port $port claiming NOT configured"
    fi
done

# 5. Check actual port usage
echo ""
echo "--- Port Status ---"

for svc in "${!SERVICES[@]}"; do
    port="${SERVICES[$svc]}"
    
    # Check if service is active
    if systemctl is-active "$svc" &>/dev/null; then
        # Check if correct process owns the port
        listener_pid=$(lsof -i ":$port" -sTCP:LISTEN -t 2>/dev/null | head -1)
        if [ -n "$listener_pid" ]; then
            listener_cmd=$(ps -p "$listener_pid" -o comm= 2>/dev/null)
            log_ok "Port $port ($svc): listening (PID $listener_pid: $listener_cmd)"
        else
            log_warn "Port $port ($svc): service active but not listening"
        fi
    else
        # Service not running - check if port is free or occupied by something else
        listener_pid=$(lsof -i ":$port" -sTCP:LISTEN -t 2>/dev/null | head -1)
        if [ -n "$listener_pid" ]; then
            listener_cmd=$(ps -p "$listener_pid" -o comm= 2>/dev/null)
            log_warn "Port $port ($svc): service STOPPED but port occupied by $listener_cmd (PID $listener_pid)"
        else
            log_ok "Port $port ($svc): service stopped, port free"
        fi
    fi
done

# 6. Check for conflicts (multiple listeners on same port)
echo ""
echo "--- Conflict Detection ---"

for port in 8000 9090 3030 6379; do
    count=$(lsof -i ":$port" -sTCP:LISTEN -t 2>/dev/null | wc -l)
    if [ "$count" -gt 1 ]; then
        log_err "Port $port has $count listeners (conflict!)"
    elif [ "$count" -eq 1 ]; then
        log_ok "Port $port: single listener (no conflict)"
    else
        log_ok "Port $port: no listeners"
    fi
done

# Summary
echo ""
echo "=== Summary ==="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"

if [ "$ERRORS" -gt 0 ]; then
    exit 1
elif [ "$WARNINGS" -gt 0 ]; then
    exit 2
else
    echo "All checks passed!"
    exit 0
fi
