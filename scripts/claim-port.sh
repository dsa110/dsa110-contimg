#!/bin/bash
# claim-port.sh - Forcefully free a port before service startup
# Usage: ./claim-port.sh <port> [--dry-run]

PORT="${1:-}"
DRY_RUN="${2:-}"

if [ -z "$PORT" ]; then
    echo "Usage: $0 <port> [--dry-run]"
    exit 1
fi

if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "Error: Port must be a number"
    exit 1
fi

# Check if port has a listener (not just connections)
check_listener() {
    lsof -i ":$PORT" -sTCP:LISTEN -t 2>/dev/null || true
}

# Get process info for logging
get_process_info() {
    local pid="$1"
    ps -p "$pid" -o pid=,comm=,user= 2>/dev/null || echo "$pid unknown unknown"
}

PIDS=$(check_listener)

if [ -z "$PIDS" ]; then
    echo "Port $PORT is free (no listeners)"
    exit 0
fi

echo "Port $PORT has listeners:"
for pid in $PIDS; do
    get_process_info "$pid"
done

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "[DRY RUN] Would kill listener processes and free port $PORT"
    exit 0
fi

echo "Attempting graceful shutdown (SIGTERM)..."
for pid in $PIDS; do
    if kill -0 "$pid" 2>/dev/null; then
        echo "  Sending SIGTERM to $pid"
        kill -TERM "$pid" 2>/dev/null || true
    fi
done

# Wait up to 5 seconds for graceful shutdown
for i in {1..10}; do
    sleep 0.5
    PIDS=$(check_listener)
    if [ -z "$PIDS" ]; then
        echo "Port $PORT freed gracefully"
        exit 0
    fi
done

# Force kill remaining processes
echo "Graceful shutdown incomplete, using SIGKILL..."
PIDS=$(check_listener)
if [ -n "$PIDS" ]; then
    for pid in $PIDS; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Sending SIGKILL to $pid"
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
fi

# Final wait
sleep 1
PIDS=$(check_listener)
if [ -z "$PIDS" ]; then
    echo "Port $PORT freed"
    exit 0
else
    echo "ERROR: Failed to free port $PORT"
    exit 1
fi
