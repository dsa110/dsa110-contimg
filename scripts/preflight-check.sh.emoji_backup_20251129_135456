#!/bin/bash
# Preflight check - validates all services and dependencies before starting
# Run this before any deployment or after any refactor

set -e
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

check() {
    if eval "$2" >/dev/null 2>&1; then  # suppress-output-check
        echo -e "${GREEN}:check:${NC} $1"
    else
        echo -e "${RED}:cross:${NC} $1"
        ((ERRORS++))
    fi
}

warn() {
    if eval "$2" >/dev/null 2>&1; then  # suppress-output-check
        echo -e "${GREEN}:check:${NC} $1"
    else
        echo -e "${YELLOW}:warning:${NC} $1 (optional)"
        ((WARNINGS++))
    fi
}

echo "=== DSA-110 Preflight Check ==="
echo ""

echo "--- Environment ---"
check "conda casa6 environment exists" "conda env list | grep -q casa6"
check "Node.js available in casa6" "test -x /opt/miniforge/envs/casa6/bin/node"
check "Python 3.11 in casa6" "/opt/miniforge/envs/casa6/bin/python --version | grep -q '3.11'"

echo ""
echo "--- Frontend Scripts ---"
check "scripts/dev/start-dev.sh exists" "test -f /data/dsa110-contimg/frontend/scripts/dev/start-dev.sh"
check "scripts/dev/restart-dev.sh exists" "test -f /data/dsa110-contimg/frontend/scripts/dev/restart-dev.sh"
check "package.json dev script valid" "grep -q 'scripts/dev/start-dev.sh' /data/dsa110-contimg/frontend/package.json"

echo ""
echo "--- Production Scripts ---"
check "build-dashboard-production.sh exists" "test -x /data/dsa110-contimg/scripts/build-dashboard-production.sh"
check "serve-dashboard-production.sh exists" "test -x /data/dsa110-contimg/scripts/serve-dashboard-production.sh"

echo ""
echo "--- Systemd Services ---"
check "contimg-api.service installed" "systemctl list-unit-files | grep -q contimg-api.service"
check "dsa110-contimg-dashboard.service installed" "systemctl list-unit-files | grep -q dsa110-contimg-dashboard.service"
warn "contimg-api running" "systemctl is-active --quiet contimg-api"
warn "dashboard running" "systemctl is-active --quiet dsa110-contimg-dashboard"

echo ""
echo "--- Ports ---"
warn "Port 8000 (API) available or in use by our service" "! lsof -i :8000 >/dev/null 2>&1 || systemctl is-active --quiet contimg-api"  # suppress-output-check
warn "Port 3210 (Dashboard) available or in use by our service" "! lsof -i :3210 >/dev/null 2>&1 || systemctl is-active --quiet dsa110-contimg-dashboard"  # suppress-output-check
warn "Port 3111 (Dev) available" "! lsof -i :3111 >/dev/null 2>&1"  # suppress-output-check

echo ""
echo "--- Frontend Build ---"
check "node_modules exists" "test -d /data/dsa110-contimg/frontend/node_modules"
check "vite installed" "test -f /data/dsa110-contimg/frontend/node_modules/.bin/vite"
warn "dist/ exists (production build)" "test -d /data/dsa110-contimg/frontend/dist"

echo ""
echo "--- Backend ---"
check "dsa110_contimg package exists" "test -d /data/dsa110-contimg/backend/src/dsa110_contimg"
check "API module exists" "test -f /data/dsa110-contimg/backend/src/dsa110_contimg/api/__init__.py"

echo ""
echo "=== Summary ==="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All critical checks passed!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}$WARNINGS optional checks need attention${NC}"
    fi
    exit 0
else
    echo -e "${RED}$ERRORS critical checks failed!${NC}"
    exit 1
fi

