#!/bin/bash
# Preflight check - validates all services and dependencies before starting
# Run this before any deployment or after any refactor

set -e
START_TIME=$(date +%s.%N)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

check() {
    if eval "$2" >/dev/null 2>&1; then  # suppress-output-check
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1"
        ((ERRORS++)) || true
    fi
}

warn() {
    if eval "$2" >/dev/null 2>&1; then  # suppress-output-check
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${YELLOW}⚠${NC} $1 ${DIM}(optional)${NC}"
        ((WARNINGS++)) || true
    fi
}

# Informational check - always shows as info, no warning count
info() {
    if eval "$2" >/dev/null 2>&1; then  # suppress-output-check
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${BLUE}ℹ${NC} $1"
    fi
}

# Show version or value inline
show() {
    local label="$1"
    local value
    value=$(eval "$2" 2>/dev/null) || value="unavailable"
    echo -e "${CYAN}│${NC} $label: ${DIM}$value${NC}"
}

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}     DSA-110 Preflight Check            ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}┌─ Environment ─────────────────────────┐${NC}"
check "conda casa6 environment exists" "conda env list | grep -q casa6"
check "Node.js available in casa6" "test -x /opt/miniforge/envs/casa6/bin/node"
check "Python 3.11 in casa6" "/opt/miniforge/envs/casa6/bin/python --version | grep -q '3.11'"
show "Python" "/opt/miniforge/envs/casa6/bin/python --version 2>&1 | cut -d' ' -f2"
show "Node.js" "/opt/miniforge/envs/casa6/bin/node --version"
show "npm" "/opt/miniforge/envs/casa6/bin/npm --version"

echo ""
echo -e "${CYAN}┌─ Services ────────────────────────────┐${NC}"
check "contimg-api.service installed" "systemctl list-unit-files | grep -q contimg-api.service"
check "dsa110-contimg-dashboard.service installed" "systemctl list-unit-files | grep -q dsa110-contimg-dashboard.service"
check "contimg-api running" "systemctl is-active --quiet contimg-api"
check "dashboard running" "systemctl is-active --quiet dsa110-contimg-dashboard"
info "contimg-stream (streaming converter) running" "systemctl is-active --quiet contimg-stream"

echo ""
echo -e "${CYAN}┌─ Health Checks ───────────────────────┐${NC}"
check "API responds at :8000/api/health" "curl -sf http://localhost:8000/api/health >/dev/null"
check "Dashboard serves at :3210" "curl -sf http://localhost:3210/ >/dev/null"
info "Dev server at :3000 - start with 'npm run dev'" "curl -sf http://localhost:3000/ >/dev/null"

echo ""
echo -e "${CYAN}┌─ Health Dashboard API Endpoints ──────┐${NC}"
# These are the endpoints required by the Health Dashboard page
if curl -sf http://localhost:8000/api/v1/health/system >/dev/null 2>&1; then
    check "/health/system (SystemHealthPanel)" "curl -sf http://localhost:8000/api/v1/health/system"
    check "/health/pointing (TransitWidget)" "curl -sf http://localhost:8000/api/v1/health/pointing"
    check "/health/alerts (AlertsPanel)" "curl -sf http://localhost:8000/api/v1/health/alerts"
    check "/health/flux-monitoring (CalibratorMonitoringPanel)" "curl -sf http://localhost:8000/api/v1/health/flux-monitoring"
    check "/health/validity-windows/timeline (ValidityTimeline)" "curl -sf 'http://localhost:8000/api/v1/health/validity-windows/timeline?hours_back=24&hours_forward=48'"
else
    echo -e "${BLUE}ℹ${NC} API not running - skipping endpoint checks"
fi

echo ""
echo -e "${CYAN}┌─ Databases ───────────────────────────┐${NC}"
check "products.sqlite3 exists" "test -f /data/dsa110-contimg/state/db/products.sqlite3"
check "hdf5.sqlite3 exists" "test -f /data/dsa110-contimg/state/db/hdf5.sqlite3"
warn "ingest.sqlite3 exists" "test -f /data/dsa110-contimg/state/db/ingest.sqlite3"
warn "cal_registry.sqlite3 exists" "test -f /data/dsa110-contimg/state/db/cal_registry.sqlite3"

echo ""
echo -e "${CYAN}┌─ Storage ─────────────────────────────┐${NC}"
check "/data mounted (HDD)" "mountpoint -q /data || test -d /data"
check "/stage mounted (SSD)" "test -d /stage"
check "/scratch available" "test -d /scratch && test -w /scratch"
show "/data usage" "df -h /data 2>/dev/null | tail -1 | awk '{print \$3\"/\"\$2\" (\"\$5\" used)\"}'"
show "/stage usage" "df -h /stage 2>/dev/null | tail -1 | awk '{print \$3\"/\"\$2\" (\"\$5\" used)\"}'"

echo ""
echo -e "${CYAN}┌─ Frontend ────────────────────────────┐${NC}"
check "node_modules exists" "test -d /data/dsa110-contimg/frontend/node_modules"
check "vite installed" "test -f /data/dsa110-contimg/frontend/node_modules/.bin/vite"
check "dist/ exists (production build)" "test -d /data/dsa110-contimg/frontend/dist"
check "build-dashboard-production.sh executable" "test -x /data/dsa110-contimg/scripts/build-dashboard-production.sh"
check "serve-dashboard-production.sh executable" "test -x /data/dsa110-contimg/scripts/serve-dashboard-production.sh"

echo ""
echo -e "${CYAN}┌─ Backend ─────────────────────────────┐${NC}"
check "dsa110_contimg package exists" "test -d /data/dsa110-contimg/backend/src/dsa110_contimg"
check "API module exists" "test -f /data/dsa110-contimg/backend/src/dsa110_contimg/api/__init__.py"
check "conversion module exists" "test -d /data/dsa110-contimg/backend/src/dsa110_contimg/conversion"

echo ""
END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc | xargs printf "%.2f")

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${CYAN}║${NC} ${GREEN}✓ All critical checks passed!${NC}          ${CYAN}║${NC}"
    if [ $WARNINGS -gt 0 ]; then
        printf "${CYAN}║${NC} ${YELLOW}⚠ %d optional check(s) need attention${NC}   ${CYAN}║${NC}\n" $WARNINGS
    fi
else
    printf "${CYAN}║${NC} ${RED}✗ %d critical check(s) failed!${NC}          ${CYAN}║${NC}\n" $ERRORS
fi
echo -e "${CYAN}║${NC} ${DIM}Completed in ${DURATION}s${NC}                     ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"

exit $ERRORS
