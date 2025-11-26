#!/bin/bash
# Monitor both frontend and backend services
# Usage: ./monitor-services.sh [--interval SECONDS] [--auto-restart]

INTERVAL=30
AUTO_RESTART=false
LOG_FILE="/tmp/services-monitor.log"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --auto-restart)
            AUTO_RESTART=true
            shift
            ;;
        *)
            echo "Usage: $0 [--interval SECONDS] [--auto-restart]"
            exit 1
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

function log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

function check_frontend() {
    if curl -sf --max-time 5 http://localhost:3210/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend (3210): Healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ Frontend (3210): Not responding${NC}"
        return 1
    fi
}

function check_backend() {
    if curl -sf --max-time 5 http://localhost:8000/api/status > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend (8000): Healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ Backend (8000): Not responding${NC}"
        return 1
    fi
}

function restart_frontend() {
    log "${YELLOW}Restarting frontend...${NC}"
    cd /data/dsa110-contimg/frontend
    ./scripts/manage-dev-server.sh restart
}

function restart_backend() {
    log "${YELLOW}Restarting backend...${NC}"
    docker restart dsa110-api
    sleep 10
}

function check_all() {
    echo "=== Service Health Check ==="
    echo ""
    
    local frontend_ok=true
    local backend_ok=true
    
    if ! check_frontend; then
        frontend_ok=false
    fi
    
    if ! check_backend; then
        backend_ok=false
    fi
    
    echo ""
    
    if $frontend_ok && $backend_ok; then
        echo -e "${GREEN}All services healthy${NC}"
        return 0
    else
        if ! $frontend_ok && $AUTO_RESTART; then
            restart_frontend
        fi
        if ! $backend_ok && $AUTO_RESTART; then
            restart_backend
        fi
        return 1
    fi
}

# Monitor mode
if [ "$INTERVAL" != "0" ]; then
    log "Starting service monitor (interval: ${INTERVAL}s, auto-restart: $AUTO_RESTART)"
    log "Press Ctrl+C to stop"
    echo ""
    
    while true; do
        check_all
        echo ""
        sleep $INTERVAL
    done
else
    # Single check
    check_all
fi
