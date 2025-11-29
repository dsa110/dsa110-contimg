#!/bin/bash
# claim-port.sh - Forcefully free a port before service startup
# Usage: ./claim-port.sh <port> [--dry-run] [--timeout=<seconds>]
#
# Designed for systemd ExecStartPre to ensure exclusive port ownership.
# Only kills LISTENING processes, not client connections.

set -o pipefail

PORT=""
DRY_RUN=false
TIMEOUT=5
PROTECTED_PIDS="1"  # Never kill init

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=true
            ;;
        --timeout=*)
            TIMEOUT="${arg#*=}"
            ;;
        *)
            if [[ "$arg" =~ ^[0-9]+$ ]]; then
                PORT="$arg"
            else
                echo "Error: Unknown argument: $arg" >&2
                exit 1
            fi
            ;;
    esac
done

if [ -z "$PORT" ]; then
    echo "Usage: $0 <port> [--dry-run] [--timeout=<seconds>]" >&2
    exit 1
fi

if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: Port must be between 1 and 65535" >&2
    exit 1
fi

log() {
    echo "[claim-port:$PORT] $*"
}

# Check if port has a TCP listener
check_listener() {
    lsof -i ":$PORT" -sTCP:LISTEN -t 2>/dev/null  # Exception: port check may return empty || true
}

# Get process info for logging
get_process_info() {
    local pid="$1"
    ps -p "$pid" -o pid=,comm=,user=,args= 2>/dev/null  # Exception: process may have exited | head -1 || echo "$pid (exited)"
}

# Check if a PID is protected (should not be killed)
is_protected() {
    local pid="$1"
    local comm
    
    # Never kill PID 1 or kernel threads
    if [ "$pid" -le 2 ]; then
        return 0
    fi
    
    # Never kill systemd or journald
    comm=$(ps -p "$pid" -o comm= 2>/dev/null  # Exception: process may have exited || true)
    case "$comm" in
        systemd|journald|sshd|init)
            return 0
            ;;
    esac
    
    return 1
}

PIDS=$(check_listener)

if [ -z "$PIDS" ]; then
    log "Port is free (no listeners)"
    exit 0
fi

log "Found listeners on port:"
for pid in $PIDS; do
    log "  $(get_process_info "$pid")"
done

if $DRY_RUN; then
    log "[DRY RUN] Would kill listener processes"
    exit 0
fi

# Filter out protected PIDs
KILLABLE_PIDS=""
for pid in $PIDS; do
    if is_protected "$pid"; then
        log "WARNING: Skipping protected process $pid"
    else
        KILLABLE_PIDS="$KILLABLE_PIDS $pid"
    fi
done

if [ -z "$KILLABLE_PIDS" ]; then
    log "ERROR: All listeners are protected processes"
    exit 1
fi

# Graceful shutdown
log "Sending SIGTERM..."
for pid in $KILLABLE_PIDS; do
    if kill -0 "$pid" 2>/dev/null  # Exception: process existence check; then
        kill -TERM "$pid" 2>/dev/null  # Exception: process may have exited || true
    fi
done

# Wait for graceful shutdown
iterations=$((TIMEOUT * 2))
for ((i=1; i<=iterations; i++)); do
    sleep 0.5
    PIDS=$(check_listener)
    if [ -z "$PIDS" ]; then
        log "Port freed gracefully"
        exit 0
    fi
done

# Force kill
log "Graceful shutdown timed out, sending SIGKILL..."
PIDS=$(check_listener)
for pid in $PIDS; do
    if is_protected "$pid"; then
        continue
    fi
    if kill -0 "$pid" 2>/dev/null  # Exception: process existence check; then
        log "  SIGKILL -> $pid"
        kill -9 "$pid" 2>/dev/null  # Exception: process may have exited || true
    fi
done

# Final check
sleep 1
PIDS=$(check_listener)
if [ -z "$PIDS" ]; then
    log "Port freed (forced)"
    exit 0
else
    log "ERROR: Failed to free port. Remaining listeners:"
    for pid in $PIDS; do
        log "  $(get_process_info "$pid")"
    done
    exit 1
fi
