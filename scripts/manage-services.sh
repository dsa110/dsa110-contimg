#!/bin/bash
# DSA-110 Service Management Script

set -e

# Configuration (override via env: CONTIMG_API_PORT, CONTIMG_DASHBOARD_PORT, CONTIMG_DOCS_PORT)
API_PORT="${CONTIMG_API_PORT:-8000}"
DASHBOARD_PORT="${CONTIMG_DASHBOARD_PORT:-3210}"
DOCS_PORT="${CONTIMG_DOCS_PORT:-8001}"
UVICORN_RELOAD="${UVICORN_RELOAD:-1}"  # Enable auto-reload by default for development
PROJECT_DIR="/data/dsa110-contimg"
LOG_DIR="/var/log/dsa110"
PID_DIR="/var/run/dsa110"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure directories exist
mkdir -p "$LOG_DIR" 2>/dev/null || sudo mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR" 2>/dev/null || sudo mkdir -p "$PID_DIR"

# Check if port is in use
check_port() {
    local port=$1
    # Try without sudo first
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port in use
    fi
    # Try with sudo (needed for root-owned sockets like docker-proxy)
    if sudo lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    fi
    # Fallback to fuser
    # Note: fuser output is suppressed here because we only care about exit code
    # This is an exception: checking port availability, not suppressing errors
    if fuser $port/tcp >/dev/null 2>&1 || sudo fuser $port/tcp >/dev/null 2>&1; then
        return 0
    fi
    return 1  # Port free
}

# Find first free port from a candidate list
find_free_port() {
    local candidates=(3210 3211 3212 3213 3214 3215 3216 3217 3218 3219 3220)
    for p in "${candidates[@]}"; do
        if ! check_port "$p"; then
            echo "$p"
            return 0
        fi
    done
    echo ""
    return 1
}

# Kill process on port
kill_port() {
    local port=$1
    local max_attempts=5
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        # Note: Suppressing lsof errors here is acceptable - we only care if port is in use
        # This is an exception: checking port status, not suppressing actual errors
        local pids=$(lsof -ti:$port 2>/dev/null)
        if [ -z "$pids" ]; then
            pids=$(sudo lsof -ti:$port 2>/dev/null)
        fi
        if [ -z "$pids" ]; then
            # Port is free
            return 0
        fi
        
        if [ $attempt -eq 0 ]; then
            echo -e "${YELLOW}Killing process(es) on port $port: $pids${NC}"
        fi
        # If we still don't have PIDs (docker-proxy), try fuser kill directly
        # Note: Suppressing fuser output here is acceptable - we only care about success
        # This is an exception: killing processes, not suppressing actual errors
        if [ -z "$pids" ]; then
            if [ $attempt -lt 2 ]; then
                sudo fuser -k $port/tcp >/dev/null 2>&1 || true
            else
                sudo fuser -k -9 $port/tcp >/dev/null 2>&1 || true
            fi
        fi

        # Kill the entire process tree (parent and children)
        for pid in $pids; do
            # Find parent process
            local ppid=$(ps -o ppid= -p $pid 2>/dev/null | tr -d ' ')
            
            # Try regular kill first, then force
            if [ $attempt -lt 2 ]; then
                # Kill parent first if it exists and looks like a conda/bash wrapper
                if [ -n "$ppid" ] && [ "$ppid" != "1" ]; then
                    local parent_cmd=$(ps -o cmd= -p $ppid 2>/dev/null)
                    if [[ "$parent_cmd" =~ (conda|bash|tmp) ]]; then
                        sudo kill $ppid 2>/dev/null || kill $ppid 2>/dev/null
                    fi
                fi
                sudo kill $pid 2>/dev/null || kill $pid 2>/dev/null
            else
                # Force kill parent and child
                if [ -n "$ppid" ] && [ "$ppid" != "1" ]; then
                    sudo kill -9 $ppid 2>/dev/null || kill -9 $ppid 2>/dev/null
                fi
                sudo kill -9 $pid 2>/dev/null || kill -9 $pid 2>/dev/null
            fi
        done
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    # Check one more time
    if lsof -ti:$port >/dev/null 2>&1; then
        echo -e "${RED}Failed to free port $port after $max_attempts attempts${NC}"
        return 1
    fi
    return 0
}

# Start API
start_api() {
    echo -e "${GREEN}Starting DSA-110 API on port $API_PORT...${NC}"
    
    # Kill existing process if any
    if check_port $API_PORT; then
        echo -e "${YELLOW}Port $API_PORT already in use${NC}"
        if ! kill_port $API_PORT; then
            echo -e "${RED}Cannot start API - port $API_PORT is still in use${NC}"
            return 1
        fi
    fi
    
    # Double-check port is free
    if check_port $API_PORT; then
        echo -e "${RED}Port $API_PORT is still in use after cleanup${NC}"
        return 1
    fi
    
    cd "$PROJECT_DIR"
    
    # Build uvicorn command with optional reload flag
    UVICORN_CMD="uvicorn dsa110_contimg.api.routes:create_app --factory --host 0.0.0.0 --port $API_PORT"
    if [ "$UVICORN_RELOAD" = "1" ]; then
        UVICORN_CMD="$UVICORN_CMD --reload"
        echo -e "${YELLOW}Auto-reload enabled (set UVICORN_RELOAD=0 to disable)${NC}"
    fi
    
    # Start in background (avoid nested conda run if already in casa6)
    if [ "${CONDA_DEFAULT_ENV:-}" = "casa6" ] || [[ "${CONDA_PREFIX:-}" == *"/envs/casa6"* ]]; then
        nohup env PYTHONPATH="$PROJECT_DIR/src" \
            PIPELINE_PRODUCTS_DB="$PROJECT_DIR/state/products.sqlite3" \
            PIPELINE_QUEUE_DB="$PROJECT_DIR/state/ingest.sqlite3" \
            PIPELINE_STATE_DIR="$PROJECT_DIR/state" \
        $UVICORN_CMD \
        > "$LOG_DIR/api.log" 2>&1 &
    else
        nohup conda run -n casa6 \
            env PYTHONPATH="$PROJECT_DIR/src" \
                PIPELINE_PRODUCTS_DB="$PROJECT_DIR/state/products.sqlite3" \
                PIPELINE_QUEUE_DB="$PROJECT_DIR/state/ingest.sqlite3" \
                PIPELINE_STATE_DIR="$PROJECT_DIR/state" \
            $UVICORN_CMD \
            > "$LOG_DIR/api.log" 2>&1 &
    fi
    
    local pid=$!
    echo $pid > "$PID_DIR/api.pid"
    
    # Wait up to ~10s for port to come up
    for i in 1 2 3 4 5 6 7 8 9 10; do
        if check_port $API_PORT; then
            break
        fi
        sleep 1
    done
    
    if check_port $API_PORT; then
        echo -e "${GREEN}✓ API started successfully (PID: $pid)${NC}"
        echo -e "  Logs: $LOG_DIR/api.log"
        echo -e "  URL: http://localhost:$API_PORT"
    else
        echo -e "${RED}✗ API failed to start${NC}"
        tail -20 "$LOG_DIR/api.log"
        return 1
    fi
}

# Start Dashboard
start_dashboard() {
    echo -e "${GREEN}Starting DSA-110 Dashboard on port $DASHBOARD_PORT...${NC}"
    
    # Resolve a free port (prefer configured, else fallback range)
    local chosen_port="$DASHBOARD_PORT"
    if check_port "$chosen_port"; then
        echo -e "${YELLOW}Port $chosen_port already in use, searching for a free port...${NC}"
        local free_port=$(find_free_port)
        if [ -z "$free_port" ]; then
            echo -e "${RED}No free port found in 3000-3010 for dashboard${NC}"
            return 1
        fi
        chosen_port="$free_port"
        echo -e "Using port $chosen_port"
    fi
    
    cd "$PROJECT_DIR/frontend"
    
    # Check if we should use production (vite preview) or dev (vite)
    if [ -d "dist" ]; then
        echo "Using static server for production dist (serve -s)..."
        nohup npx serve -s dist -l tcp://0.0.0.0:$chosen_port \
            > "$LOG_DIR/dashboard.log" 2>&1 &
    elif [ -d "build" ]; then
        echo "Using legacy build directory..."
        nohup npx serve -s build -l tcp://0.0.0.0:$chosen_port \
            > "$LOG_DIR/dashboard.log" 2>&1 &
    else
        echo "Using development server (vite dev)..."
        # Prefer casa6 Node (vite requires Node 20.19+ or 22.12+)
        if command -v conda >/dev/null 2>&1; then
            nohup env VITE_API_URL="http://localhost:$API_PORT" \
                conda run -n casa6 npm run dev -- --host 0.0.0.0 --port $chosen_port \
                > "$LOG_DIR/dashboard.log" 2>&1 &
        else
            nohup env VITE_API_URL="http://localhost:$API_PORT" \
                npm run dev -- --host 0.0.0.0 --port $chosen_port \
                > "$LOG_DIR/dashboard.log" 2>&1 &
        fi
    fi
    
    local pid=$!
    echo $pid > "$PID_DIR/dashboard.pid"
    echo $chosen_port > "$PID_DIR/dashboard.port"
    
    sleep 5
    
    if check_port $chosen_port; then
        echo -e "${GREEN}✓ Dashboard started successfully (PID: $pid)${NC}"
        echo -e "  Logs: $LOG_DIR/dashboard.log"
        echo -e "  URL: http://localhost:$chosen_port/dashboard"
    else
        echo -e "${RED}✗ Dashboard failed to start${NC}"
        tail -20 "$LOG_DIR/dashboard.log"
        return 1
    fi
}

# Stop API
stop_api() {
    echo -e "${YELLOW}Stopping DSA-110 API...${NC}"
    
    if [ -f "$PID_DIR/api.pid" ]; then
        local pid=$(cat "$PID_DIR/api.pid")
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid 2>/dev/null || sudo kill $pid 2>/dev/null
            echo -e "${GREEN}✓ API stopped (PID: $pid)${NC}"
        fi
        rm "$PID_DIR/api.pid"
    fi
    
    # Ensure port is free
    kill_port $API_PORT
}

# Stop Dashboard
stop_dashboard() {
    echo -e "${YELLOW}Stopping DSA-110 Dashboard...${NC}"
    
    if [ -f "$PID_DIR/dashboard.pid" ]; then
        local pid=$(cat "$PID_DIR/dashboard.pid")
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid 2>/dev/null || sudo kill $pid 2>/dev/null
            echo -e "${GREEN}✓ Dashboard stopped (PID: $pid)${NC}"
        fi
        rm "$PID_DIR/dashboard.pid"
    fi
    if [ -f "$PID_DIR/dashboard.port" ]; then
        rm "$PID_DIR/dashboard.port"
    fi
    
    # Ensure port is free
    kill_port $DASHBOARD_PORT
}

# Status
status() {
    echo -e "${GREEN}=== DSA-110 Service Status ===${NC}\n"
    
    # API Status
    echo -e "${YELLOW}API (Port $API_PORT):${NC}"
    if check_port $API_PORT; then
        local pid=$(lsof -ti:$API_PORT)
        echo -e "  ${GREEN}✓ Running${NC} (PID: $pid)"
        echo -e "  URL: http://localhost:$API_PORT"
    else
        echo -e "  ${RED}✗ Not running${NC}"
    fi
    
    # Dashboard Status
    echo -e "\n${YELLOW}Dashboard:${NC}"
    local dash_port="$DASHBOARD_PORT"
    if [ -f "$PID_DIR/dashboard.port" ]; then
        dash_port=$(cat "$PID_DIR/dashboard.port")
    fi
    if check_port $dash_port; then
        local pid=$(lsof -ti:$dash_port)
        echo -e "  ${GREEN}✓ Running${NC} (PID: $pid)"
        echo -e "  URL: http://localhost:$dash_port"
    else
        echo -e "  ${RED}✗ Not running${NC}"
    fi

    # Docs Status
    echo -e "\n${YELLOW}Docs (Port $DOCS_PORT):${NC}"
    if check_port $DOCS_PORT; then
        local pid=$(lsof -ti:$DOCS_PORT)
        echo -e "  ${GREEN}✓ Running${NC} (PID: $pid)"
        echo -e "  URL: http://localhost:$DOCS_PORT"
    else
        echo -e "  ${RED}✗ Not running${NC}"
    fi
    
    # Port conflicts
    echo -e "\n${YELLOW}Port Usage:${NC}"
    netstat -tlnp 2>/dev/null | grep -E ":($API_PORT|$DASHBOARD_PORT|$DOCS_PORT)" || echo "  No conflicts"
}

# Logs
logs() {
    local service=$1
    local lines=${2:-50}
    
    case $service in
        api)
            tail -n $lines -f "$LOG_DIR/api.log"
            ;;
        dashboard)
            tail -n $lines -f "$LOG_DIR/dashboard.log"
            ;;
        *)
            echo "Usage: $0 logs {api|dashboard} [lines]"
            exit 1
            ;;
    esac
}

# Start Docs (mkdocs)
start_docs() {
    echo -e "${GREEN}Starting docs server on port $DOCS_PORT...${NC}"
    if check_port $DOCS_PORT; then
        echo -e "${YELLOW}Port $DOCS_PORT already in use${NC}"
        if ! kill_port $DOCS_PORT; then
            echo -e "${RED}Cannot start docs - port $DOCS_PORT is still in use${NC}"
            return 1
        fi
    fi
    cd "$PROJECT_DIR"
    nohup env PYTHONPATH="$PROJECT_DIR/src" mkdocs serve -a 0.0.0.0:$DOCS_PORT \
        > "$LOG_DIR/docs.log" 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/docs.pid"
    sleep 2
    if check_port $DOCS_PORT; then
        echo -e "${GREEN}✓ Docs started successfully (PID: $pid)${NC}"
        echo -e "  Logs: $LOG_DIR/docs.log"
        echo -e "  URL: http://localhost:$DOCS_PORT"
    else
        echo -e "${RED}✗ Docs failed to start${NC}"
        tail -20 "$LOG_DIR/docs.log"
        return 1
    fi
}

stop_docs() {
    echo -e "${YELLOW}Stopping docs server...${NC}"
    if [ -f "$PID_DIR/docs.pid" ]; then
        local pid=$(cat "$PID_DIR/docs.pid")
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid 2>/dev/null || sudo kill $pid 2>/dev/null
            echo -e "${GREEN}✓ Docs stopped (PID: $pid)${NC}"
        fi
        rm "$PID_DIR/docs.pid"
    fi
    kill_port $DOCS_PORT
}

# Main
case "$1" in
    start)
        case "$2" in
            api)
                start_api
                ;;
            dashboard)
                start_dashboard
                ;;
            docs)
                start_docs
                ;;
            all|"")
                start_api
                start_dashboard
                ;;
            *)
                echo "Usage: $0 start {api|dashboard|docs|all}"
                exit 1
                ;;
        esac
        ;;
    stop)
        case "$2" in
            api)
                stop_api
                ;;
            dashboard)
                stop_dashboard
                ;;
            docs)
                stop_docs
                ;;
            all|"")
                stop_api
                stop_dashboard
                ;;
            *)
                echo "Usage: $0 stop {api|dashboard|docs|all}"
                exit 1
                ;;
        esac
        ;;
    restart)
        case "$2" in
            api)
                stop_api
                sleep 2
                start_api
                ;;
            dashboard)
                stop_dashboard
                sleep 2
                start_dashboard
                ;;
            docs)
                stop_docs
                sleep 2
                start_docs
                ;;
            all|"")
                stop_api
                stop_dashboard
                sleep 2
                start_api
                start_dashboard
                ;;
            *)
                echo "Usage: $0 restart {api|dashboard|docs|all}"
                exit 1
                ;;
        esac
        ;;
    status)
        status
        ;;
    logs)
        logs "$2" "$3"
        ;;
    *)
        echo "DSA-110 Service Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs} [service]"
        echo ""
        echo "Commands:"
        echo "  start [api|dashboard|docs|all]    - Start service(s)"
        echo "  stop [api|dashboard|docs|all]     - Stop service(s)"
        echo "  restart [api|dashboard|docs|all]  - Restart service(s)"
        echo "  status                        - Show service status"
        echo "  logs {api|dashboard} [lines]  - Tail service logs"
        echo ""
        echo "Examples:"
        echo "  $0 start all          # Start both services"
        echo "  $0 stop api           # Stop only API"
        echo "  $0 restart dashboard  # Restart dashboard"
        echo "  $0 start docs         # Start docs server (mkdocs)"
        echo "  $0 status             # Check status"
        echo "  $0 logs api 100       # View last 100 lines of API logs"
        exit 1
        ;;
esac
