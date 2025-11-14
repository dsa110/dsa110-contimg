#!/bin/bash
# Service locking mechanism to prevent duplicate instances
# Uses file-based locking to ensure only one instance of each service runs

set -e

PROJECT_DIR="/data/dsa110-contimg"
LOCK_DIR="/var/run/dsa110/locks"
PID_DIR="/var/run/dsa110"

mkdir -p "$LOCK_DIR" 2>/dev/null || sudo mkdir -p "$LOCK_DIR"
mkdir -p "$PID_DIR" 2>/dev/null || sudo mkdir -p "$PID_DIR"

SERVICE="${1:-}"
ACTION="${2:-}"

acquire_lock() {
    local service=$1
    local lock_file="$LOCK_DIR/${service}.lock"
    local max_wait=10
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        if (set -C; echo $$ > "$lock_file") 2>/dev/null; then
            # Lock acquired
            trap "rm -f '$lock_file'" EXIT
            return 0
        else
            # Lock exists, check if process is still running
            local lock_pid=$(cat "$lock_file" 2>/dev/null || echo "")
            if [ -n "$lock_pid" ]; then
                if ! ps -p "$lock_pid" > /dev/null 2>&1; then
                    # Process is dead, remove stale lock
                    rm -f "$lock_file"
                    continue
                fi
            else
                # Lock file exists but is empty, remove it
                rm -f "$lock_file"
                continue
            fi
        fi
        
        sleep 1
        wait_time=$((wait_time + 1))
    done
    
    echo "ERROR: Could not acquire lock for $service (waited ${max_wait}s)"
    echo "  Lock file: $lock_file"
    echo "  Lock PID: $(cat "$lock_file" 2>/dev/null || echo 'none')"
    return 1
}

release_lock() {
    local service=$1
    local lock_file="$LOCK_DIR/${service}.lock"
    rm -f "$lock_file"
}

check_lock() {
    local service=$1
    local lock_file="$LOCK_DIR/${service}.lock"
    
    if [ -f "$lock_file" ]; then
        local lock_pid=$(cat "$lock_file" 2>/dev/null || echo "")
        if [ -n "$lock_pid" ] && ps -p "$lock_pid" > /dev/null 2>&1; then
            echo "Service $service is locked by PID $lock_pid"
            return 1
        else
            # Stale lock, remove it
            rm -f "$lock_file"
            return 0
        fi
    fi
    return 0
}

case "$ACTION" in
    acquire)
        acquire_lock "$SERVICE"
        ;;
    release)
        release_lock "$SERVICE"
        ;;
    check)
        check_lock "$SERVICE"
        ;;
    *)
        echo "Usage: $0 {service} {acquire|release|check}"
        exit 1
        ;;
esac

