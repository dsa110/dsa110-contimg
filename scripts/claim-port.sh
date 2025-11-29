#!/bin/bash
# claim-port.sh - Forcefully free a port before service startup
# Usage: ./claim-port.sh <port> [--dry-run] [--timeout=<seconds>] [--force]
#
# Designed for systemd ExecStartPre to ensure exclusive port ownership.
# Only kills LISTENING processes, not client connections.
#
# Options:
#   --dry-run         Show what would be killed without actually killing
#   --timeout=N       Seconds to wait for graceful shutdown (default: 5)
#   --force           Skip SIGTERM, go straight to SIGKILL

set -o pipefail

PORT=""
DRY_RUN=false
FORCE=false
TIMEOUT=5

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=true
            ;;
        --force)
            FORCE=true
            ;;
        --timeout=*)
            TIMEOUT="${arg#*=}"
            if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
                echo "Error: --timeout must be a number" >&2
                exit 1
            fi
            ;;
        *)
            if [[ "$arg" =~ ^[0-9]+$ ]]; then
                PORT="$arg"
            else
                echo "Error: Unknown argument: $arg" >&2
                echo "Usage: $0 <port> [--dry-run] [--timeout=<seconds>] [--force]" >&2
                exit 1
            fi
            ;;
    esac
done

if [ -z "$PORT" ]; then
    echo "Usage: $0 <port> [--dry-run] [--timeout=<seconds>] [--force]" >&2
    exit 1
fi

if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: Port must be between 1 and 65535" >&2
    exit 1
fi

# Check dependencies
# Exception: checking if command exists
if ! command -v lsof &>/dev/null; then
    echo "Error: lsof is required but not installed" >&2
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
    
    # Never kill critical system processes
    comm=$(ps -p "$pid" -o comm= 2>/dev/null  # Exception: process may exit || true)
    case "$comm" in
        systemd|systemd-*|journald|sshd|init|dbus-daemon)
            return 0
            ;;
    esac
    
    return 1
}

# Kill a process (SIGTERM or SIGKILL)
kill_process() {
    local pid="$1"
    local signal="$2"
    
    # Exception: checking if process exists
    if kill -0 "$pid" 2>/dev/null; then
        kill "-$signal" "$pid" 2>/dev/null  # Exception: process may exit || true
        return 0
    fi
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

KILLABLE_PIDS=$(echo "$KILLABLE_PIDS" | xargs)  # Trim whitespace

if [ -z "$KILLABLE_PIDS" ]; then
    log "ERROR: All listeners are protected processes"
    exit 1
fi

# Force mode: skip SIGTERM
if $FORCE; then
    log "Force mode: sending SIGKILL immediately..."
    for pid in $KILLABLE_PIDS; do
        if kill_process "$pid" 9; then
            log "  SIGKILL -> $pid"
        fi
    done
    sleep 1
else
    # Graceful shutdown with SIGTERM
    log "Sending SIGTERM..."
    for pid in $KILLABLE_PIDS; do
        kill_process "$pid" TERM
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

    # Force kill remaining
    log "Graceful shutdown timed out, sending SIGKILL..."
    PIDS=$(check_listener)
    for pid in $PIDS; do
        if is_protected "$pid"; then
            continue
        fi
        if kill_process "$pid" 9; then
            log "  SIGKILL -> $pid"
        fi
    done
    sleep 1
fi

# Final check
PIDS=$(check_listener)
if [ -z "$PIDS" ]; then
    log "Port freed"
    exit 0
else
    log "ERROR: Failed to free port. Remaining listeners:"
    for pid in $PIDS; do
        log "  $(get_process_info "$pid")"
    done
    exit 1
fi
