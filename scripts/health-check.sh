#!/bin/bash
# =============================================================================
# DSA-110 Frontend Health Check & Auto-Recovery Script
# =============================================================================
# 
# This script diagnoses why the Health page might show "Failed to load" errors
# and can automatically start missing services.
#
# Usage:
#   ./health-check.sh          # Diagnose only
#   ./health-check.sh --fix    # Diagnose and auto-fix issues
#
# Exit codes:
#   0 - All services healthy
#   1 - Issues found (details in output)
#   2 - Critical failure
# =============================================================================

set -e

# Configuration
FRONTEND_PORT=3000
BACKEND_PORT=8000
API_BASE="http://localhost:${BACKEND_PORT}/api/v1"
FRONTEND_BASE="http://localhost:${FRONTEND_PORT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FIX_MODE=false
if [[ "$1" == "--fix" ]]; then
    FIX_MODE=true
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  DSA-110 Health Dashboard Diagnostic Tool${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

ISSUES_FOUND=0

# -----------------------------------------------------------------------------
# Check 1: Frontend Dev Server (Vite)
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[1/5] Checking Frontend Dev Server (port ${FRONTEND_PORT})...${NC}"

if ! ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT}"; then
    echo -e "  ${RED}✗ Frontend not running on port ${FRONTEND_PORT}${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    
    if $FIX_MODE; then
        echo -e "  ${BLUE}→ Starting frontend dev server...${NC}"
        cd /data/dsa110-contimg/frontend
        nohup npm run dev -- --host 0.0.0.0 > /tmp/frontend.log 2>&1 &
        sleep 5
        if ss -tlnp 2>/dev/null | grep -q ":${FRONTEND_PORT}"; then
            echo -e "  ${GREEN}✓ Frontend started successfully${NC}"
        else
            echo -e "  ${RED}✗ Failed to start frontend${NC}"
        fi
    fi
else
    FRONTEND_PID=$(ss -tlnp 2>/dev/null | grep ":${FRONTEND_PORT}" | grep -oP 'pid=\K\d+' | head -1)
    FRONTEND_START=$(ps -p "$FRONTEND_PID" -o lstart= 2>/dev/null || echo "unknown")
    echo -e "  ${GREEN}✓ Running (PID: ${FRONTEND_PID}, started: ${FRONTEND_START})${NC}"
    
    # Check if it's serving latest code (HMR mode)
    if curl -s "${FRONTEND_BASE}/" 2>/dev/null | grep -q "@vite/client"; then
        echo -e "  ${GREEN}✓ HMR (Hot Module Replacement) active - reflects latest code${NC}"
    else
        echo -e "  ${YELLOW}⚠ May be running in preview/production mode - not reflecting code changes${NC}"
    fi
fi
echo ""

# -----------------------------------------------------------------------------
# Check 2: Backend API Server (Uvicorn)
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[2/5] Checking Backend API Server (port ${BACKEND_PORT})...${NC}"

if ! ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT}"; then
    echo -e "  ${RED}✗ Backend not running on port ${BACKEND_PORT}${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    
    if $FIX_MODE; then
        echo -e "  ${BLUE}→ Starting backend API server...${NC}"
        cd /data/dsa110-contimg/backend
        nohup /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload > /tmp/uvicorn.log 2>&1 &
        sleep 5
        if ss -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT}"; then
            echo -e "  ${GREEN}✓ Backend started successfully${NC}"
        else
            echo -e "  ${RED}✗ Failed to start backend${NC}"
        fi
    fi
else
    BACKEND_PID=$(ss -tlnp 2>/dev/null | grep ":${BACKEND_PORT}" | grep -oP 'pid=\K\d+' | head -1)
    BACKEND_START=$(ps -p "$BACKEND_PID" -o lstart= 2>/dev/null || echo "unknown")
    echo -e "  ${GREEN}✓ Running (PID: ${BACKEND_PID}, started: ${BACKEND_START})${NC}"
    
    # Check for any uvicorn process with --reload (may be parent or sibling)
    if pgrep -af "uvicorn.*--reload" 2>/dev/null | grep -q dsa110_contimg; then
        echo -e "  ${GREEN}✓ Auto-reload enabled - reflects code changes${NC}"
    else
        echo -e "  ${YELLOW}⚠ Auto-reload NOT enabled - restart needed after code changes${NC}"
        
        if $FIX_MODE; then
            echo -e "  ${BLUE}→ Restarting with --reload...${NC}"
            pkill -f "uvicorn.*dsa110_contimg" 2>/dev/null || true
            sleep 2
            cd /data/dsa110-contimg/backend
            nohup /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload > /tmp/uvicorn.log 2>&1 &
            sleep 5
        fi
    fi
fi
echo ""

# -----------------------------------------------------------------------------
# Check 3: API Proxy Configuration
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[3/5] Checking API Proxy (Frontend → Backend)...${NC}"

# Test direct backend access
BACKEND_DIRECT=$(curl -sw "%{http_code}" -o /dev/null "${API_BASE}/health/system" 2>/dev/null || echo "000")
# Test through frontend proxy
FRONTEND_PROXY=$(curl -sw "%{http_code}" -o /dev/null "${FRONTEND_BASE}/api/v1/health/system" 2>/dev/null || echo "000")

if [[ "$BACKEND_DIRECT" == "200" ]]; then
    echo -e "  ${GREEN}✓ Backend directly accessible (HTTP ${BACKEND_DIRECT})${NC}"
else
    echo -e "  ${RED}✗ Backend not accessible directly (HTTP ${BACKEND_DIRECT})${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

if [[ "$FRONTEND_PROXY" == "200" ]]; then
    echo -e "  ${GREEN}✓ Frontend proxy working (HTTP ${FRONTEND_PROXY})${NC}"
else
    echo -e "  ${RED}✗ Frontend proxy not working (HTTP ${FRONTEND_PROXY})${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi
echo ""

# -----------------------------------------------------------------------------
# Check 4: Health Dashboard API Endpoints
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[4/5] Checking Health Dashboard API Endpoints...${NC}"

declare -A HEALTH_ENDPOINTS=(
    ["/health/system"]="SystemHealthPanel"
    ["/health/pointing"]="TransitWidget"
    ["/health/alerts"]="AlertsPanel"
    ["/health/flux-monitoring"]="CalibratorMonitoringPanel"
    ["/health/validity-windows/timeline?hours_back=24&hours_forward=48"]="ValidityWindowTimeline"
)

for endpoint in "${!HEALTH_ENDPOINTS[@]}"; do
    component="${HEALTH_ENDPOINTS[$endpoint]}"
    response=$(curl -sw "%{http_code}" -o /tmp/health_check_response.json "${API_BASE}${endpoint}" 2>/dev/null || echo "000")
    
    if [[ "$response" == "200" ]]; then
        # Check if response contains error messages
        if grep -q '"message".*not initialized\|"error"' /tmp/health_check_response.json 2>/dev/null; then
            echo -e "  ${YELLOW}⚠ ${endpoint} → HTTP ${response} (${component}) - Data not initialized${NC}"
        else
            echo -e "  ${GREEN}✓ ${endpoint} → HTTP ${response} (${component})${NC}"
        fi
    elif [[ "$response" == "404" ]]; then
        echo -e "  ${RED}✗ ${endpoint} → HTTP ${response} (${component}) - ENDPOINT MISSING${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "  ${RED}✗ ${endpoint} → HTTP ${response} (${component})${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
done
echo ""

# -----------------------------------------------------------------------------
# Check 5: Recent File Changes
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[5/5] Checking for Recent Code Changes...${NC}"

# Get server start times
FRONTEND_PID=$(ss -tlnp 2>/dev/null | grep ":${FRONTEND_PORT}" | grep -oP 'pid=\K\d+' | head -1)
BACKEND_PID=$(ss -tlnp 2>/dev/null | grep ":${BACKEND_PORT}" | grep -oP 'pid=\K\d+' | head -1)

# Check for frontend files modified after server start
if [[ -n "$FRONTEND_PID" ]] && [[ -d /proc/"$FRONTEND_PID" ]]; then
    FE_NEWER=$(find /data/dsa110-contimg/frontend/src -type f \( -name "*.ts" -o -name "*.tsx" \) -newer /proc/"$FRONTEND_PID" 2>/dev/null | wc -l)
    if [[ "$FE_NEWER" -gt 0 ]]; then
        echo -e "  ${GREEN}✓ ${FE_NEWER} frontend files changed since server start (HMR will update)${NC}"
    fi
fi

# Check for backend files modified after server start
if [[ -n "$BACKEND_PID" ]] && [[ -d /proc/"$BACKEND_PID" ]]; then
    BE_NEWER=$(find /data/dsa110-contimg/backend/src -type f -name "*.py" -newer /proc/"$BACKEND_PID" 2>/dev/null | wc -l)
    if [[ "$BE_NEWER" -gt 0 ]]; then
        if pgrep -af "uvicorn.*--reload" 2>/dev/null | grep -q dsa110_contimg; then
            echo -e "  ${GREEN}✓ ${BE_NEWER} backend files changed since server start (auto-reload enabled)${NC}"
        else
            echo -e "  ${YELLOW}⚠ ${BE_NEWER} backend files changed since server start (RESTART NEEDED)${NC}"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    fi
fi
echo ""

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
if [[ $ISSUES_FOUND -eq 0 ]]; then
    echo -e "${GREEN}✓ All checks passed! Health Dashboard should be working.${NC}"
    echo -e ""
    echo -e "Access the Health Dashboard at: ${BLUE}http://localhost:3000/health${NC}"
else
    echo -e "${RED}✗ Found ${ISSUES_FOUND} issue(s)${NC}"
    echo -e ""
    if ! $FIX_MODE; then
        echo -e "Run with ${YELLOW}--fix${NC} to attempt automatic fixes:"
        echo -e "  ${BLUE}./health-check.sh --fix${NC}"
    fi
fi
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"

exit $ISSUES_FOUND
