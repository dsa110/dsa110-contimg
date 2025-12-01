#!/bin/bash
# =============================================================================
# DSA-110 Development Server Startup
# =============================================================================
#
# Starts frontend and backend development servers. Automatically detects and
# fixes common issues (zombie processes, missing reload, stale servers).
#
# Usage:
#   ./start-dev.sh          # Start everything (default)
#   ./start-dev.sh --stop   # Stop all dev servers
#
# Ports:
#   3000 - Frontend (Vite with HMR)
#   8000 - Backend (Uvicorn with auto-reload)
# =============================================================================

set -e

FRONTEND_PORT=3000
BACKEND_PORT=8000
PROJECT_ROOT="/data/dsa110-contimg"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Handle --stop
if [[ "${1:-}" == "--stop" ]]; then
    echo -e "${BLUE}Stopping development servers...${NC}"
    pkill -f "node.*vite" 2>/dev/null && echo -e "${GREEN}✓${NC} Frontend stopped" || true
    pkill -f "uvicorn.*dsa110_contimg" 2>/dev/null && echo -e "${GREEN}✓${NC} Backend stopped" || true
    sleep 1
    echo -e "${GREEN}Done.${NC}"
    exit 0
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  DSA-110 Development Environment${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# =============================================================================
# Step 1: Clean up any problematic state
# =============================================================================
echo -e "${YELLOW}[1/4] Checking for issues...${NC}"

# Kill zombie npm/vite processes not listening on expected port
ZOMBIE_VITE=$(pgrep -f "node.*vite" 2>/dev/null | while read pid; do
    if ! ss -tlnp 2>/dev/null | grep -q "pid=$pid"; then
        echo $pid
    fi
done)
if [[ -n "$ZOMBIE_VITE" ]]; then
    echo -e "  ${YELLOW}→${NC} Cleaning up zombie Vite processes..."
    echo "$ZOMBIE_VITE" | xargs -r kill 2>/dev/null || true
fi

# Check backend - must have --reload for dev
if ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT}"; then
    if ! pgrep -af "uvicorn.*--reload" 2>/dev/null | grep -q dsa110_contimg; then
        echo -e "  ${YELLOW}→${NC} Backend running without --reload, restarting..."
        pkill -f "uvicorn.*dsa110_contimg" 2>/dev/null || true
        sleep 2
    fi
fi

echo -e "  ${GREEN}✓${NC} Clean"
echo ""

# =============================================================================
# Step 2: Start Backend
# =============================================================================
echo -e "${YELLOW}[2/4] Backend (port $BACKEND_PORT)...${NC}"

if ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT}"; then
    BE_PID=$(ss -tlnp 2>/dev/null | grep ":${BACKEND_PORT}" | grep -oP 'pid=\K\d+' | head -1)
    echo -e "  ${GREEN}✓${NC} Already running (PID: $BE_PID) with auto-reload"
else
    cd "${PROJECT_ROOT}/backend"
    nohup /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app \
        --host 0.0.0.0 --port $BACKEND_PORT --reload \
        > /tmp/uvicorn-dev.log 2>&1 &
    
    # Wait for startup
    for i in {1..10}; do
        if ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT}"; then
            break
        fi
        sleep 1
    done
    
    if ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT}"; then
        echo -e "  ${GREEN}✓${NC} Started with auto-reload"
    else
        echo -e "  ${RED}✗${NC} Failed to start. Check /tmp/uvicorn-dev.log"
        tail -20 /tmp/uvicorn-dev.log 2>/dev/null
        exit 1
    fi
fi
echo ""

# =============================================================================
# Step 3: Start Frontend
# =============================================================================
echo -e "${YELLOW}[3/4] Frontend (port $FRONTEND_PORT)...${NC}"

if ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT}"; then
    FE_PID=$(ss -tlnp 2>/dev/null | grep ":${FRONTEND_PORT}" | grep -oP 'pid=\K\d+' | head -1)
    echo -e "  ${GREEN}✓${NC} Already running (PID: $FE_PID) with HMR"
else
    cd "${PROJECT_ROOT}/frontend"
    nohup npm run dev -- --host 0.0.0.0 > /tmp/vite-dev.log 2>&1 &
    
    # Wait for startup
    for i in {1..15}; do
        if ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT}"; then
            break
        fi
        sleep 1
    done
    
    if ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT}"; then
        echo -e "  ${GREEN}✓${NC} Started with HMR"
    else
        echo -e "  ${RED}✗${NC} Failed to start. Check /tmp/vite-dev.log"
        tail -20 /tmp/vite-dev.log 2>/dev/null
        exit 1
    fi
fi
echo ""

# =============================================================================
# Step 4: Verify everything works
# =============================================================================
echo -e "${YELLOW}[4/4] Verifying Health Dashboard endpoints...${NC}"

ENDPOINTS_OK=true
for endpoint in "/health/system" "/health/pointing" "/health/alerts"; do
    status=$(curl -sw "%{http_code}" -o /dev/null "http://localhost:${BACKEND_PORT}/api/v1${endpoint}" 2>/dev/null || echo "000")
    if [[ "$status" == "200" ]]; then
        echo -e "  ${GREEN}✓${NC} $endpoint"
    else
        echo -e "  ${RED}✗${NC} $endpoint (HTTP $status)"
        ENDPOINTS_OK=false
    fi
done

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"

if $ENDPOINTS_OK; then
    echo -e "${GREEN}Ready!${NC}"
    echo ""
    echo "  Dashboard:  http://localhost:$FRONTEND_PORT"
    echo "  Health:     http://localhost:$FRONTEND_PORT/health"
    echo "  API:        http://localhost:$BACKEND_PORT/api/v1"
    echo ""
    echo "Both servers auto-reload on code changes."
    echo "Stop with: $0 --stop"
else
    echo -e "${YELLOW}Servers running but some endpoints failed.${NC}"
    echo "Check /tmp/uvicorn-dev.log for backend errors."
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
