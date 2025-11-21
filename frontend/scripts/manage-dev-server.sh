#!/bin/bash
# Manage Vite dev server with stability features
# Usage: ./manage-dev-server.sh [start|stop|restart|status|monitor]

set -e

PID_FILE="/tmp/vite-dev-server.pid"
LOG_FILE="/tmp/vite-dev-server.log"
HEALTH_CHECK_INTERVAL=30
MAX_RESTART_ATTEMPTS=3

cd "$(dirname "$0")/.."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

function error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

function warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARN:${NC} $1"
}

function is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

function get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    fi
}

function health_check() {
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # Use curl with timeout and check for HTTP 200
        if curl -sf --max-time 5 http://localhost:3210/ > /dev/null 2>&1; then
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    return 1
}

function start_server() {
    if is_running; then
        warn "Server is already running (PID: $(get_pid))"
        return 0
    fi
    
    log "Starting Vite dev server..."
    
    # Rotate log if it's too large (>100MB)
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt 104857600 ]; then
        mv "$LOG_FILE" "$LOG_FILE.old"
        log "Rotated large log file"
    fi
    
    # Start server in background with unbuffered output
    stdbuf -oL -eL npm run dev > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"
    
    log "Server starting (PID: $pid)"
    # Wait longer for Vite to fully initialize (can take 10-20 seconds on first start)
    sleep 5
    
    if health_check; then
        log "✅ Server started successfully and responding on port 3210"
        log "Access at: http://localhost:3210/"
        return 0
    else
        # Give it one more chance with longer wait
        log "Initial health check failed, waiting longer for Vite to initialize..."
        sleep 10
        if health_check; then
            log "✅ Server started successfully and responding on port 3210"
            log "Access at: http://localhost:3210/"
            return 0
        else
            error "Server started but health check failed after extended wait"
            error "Check logs: tail -f $LOG_FILE"
            return 1
        fi
    fi
}

function stop_server() {
    if ! is_running; then
        warn "Server is not running"
        return 0
    fi
    
    local pid=$(get_pid)
    log "Stopping server (PID: $pid)..."
    
    # Graceful shutdown with SIGTERM
    kill -TERM "$pid" 2>/dev/null || true
    
    # Wait up to 10 seconds for graceful shutdown
    local timeout=10
    while [ $timeout -gt 0 ] && ps -p "$pid" > /dev/null 2>&1; do
        sleep 1
        ((timeout--))
    done
    
    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        warn "Graceful shutdown failed, force killing..."
        kill -9 "$pid" 2>/dev/null || true
    fi
    
    rm -f "$PID_FILE"
    log "✅ Server stopped"
}

function restart_server() {
    log "Restarting server..."
    stop_server
    sleep 2
    start_server
}

function status() {
    echo "=== Vite Dev Server Status ==="
    echo ""
    
    if is_running; then
        local pid=$(get_pid)
        echo -e "${GREEN}Status:${NC} Running"
        echo "PID: $pid"
        echo "Port: 3210"
        
        if health_check; then
            echo -e "${GREEN}Health:${NC} ✅ Responding"
        else
            echo -e "${RED}Health:${NC} ⚠️ Not responding"
        fi
        
        # Show resource usage
        if command -v ps > /dev/null; then
            echo ""
            echo "Resource Usage:"
            ps -p "$pid" -o pid,ppid,%cpu,%mem,vsz,rss,etime,cmd | tail -1
        fi
    else
        echo -e "${RED}Status:${NC} Not running"
    fi
    
    echo ""
    echo "Log file: $LOG_FILE"
    if [ -f "$LOG_FILE" ]; then
        local log_size=$(du -h "$LOG_FILE" | cut -f1)
        echo "Log size: $log_size"
    fi
}

function monitor() {
    log "Starting monitor mode (checking every ${HEALTH_CHECK_INTERVAL}s)"
    log "Press Ctrl+C to stop monitoring"
    
    local restart_count=0
    
    while true; do
        if is_running; then
            if ! health_check; then
                error "Health check failed!"
                
                if [ $restart_count -lt $MAX_RESTART_ATTEMPTS ]; then
                    ((restart_count++))
                    warn "Attempting restart ($restart_count/$MAX_RESTART_ATTEMPTS)..."
                    restart_server
                else
                    error "Max restart attempts reached. Manual intervention required."
                    exit 1
                fi
            else
                # Reset restart count on successful health check
                restart_count=0
            fi
        else
            error "Server is not running!"
            
            if [ $restart_count -lt $MAX_RESTART_ATTEMPTS ]; then
                ((restart_count++))
                warn "Attempting to start server ($restart_count/$MAX_RESTART_ATTEMPTS)..."
                start_server
            else
                error "Max start attempts reached. Manual intervention required."
                exit 1
            fi
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
    done
}

function watch_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        error "Log file not found: $LOG_FILE"
        exit 1
    fi
    tail -f "$LOG_FILE"
}

# Main command handler
case "${1:-status}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        status
        ;;
    monitor)
        monitor
        ;;
    logs)
        watch_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|monitor|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the dev server"
        echo "  stop     - Stop the dev server"
        echo "  restart  - Restart the dev server"
        echo "  status   - Show server status"
        echo "  monitor  - Start health monitoring with auto-restart"
        echo "  logs     - Watch server logs"
        exit 1
        ;;
esac
