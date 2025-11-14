#!/bin/bash
# Port conflict detection and validation script
# Enforces port organization system

set -e

PROJECT_DIR="/data/dsa110-contimg"
PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cd "$PROJECT_DIR"

echo -e "${BLUE}=== DSA-110 Port Configuration Check ===${NC}\n"

# Check if port manager is available
export PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH"
if ! "$PYTHON_BIN" -c "from dsa110_contimg.config.ports import PortManager" 2>/dev/null; then
    echo -e "${YELLOW}Warning: Port manager not available, using basic checks${NC}\n"
    USE_PORT_MANAGER=false
else
    USE_PORT_MANAGER=true
fi

if [ "$USE_PORT_MANAGER" = true ]; then
    # Use Python port manager
    echo -e "${BLUE}Using centralized port configuration...${NC}\n"
    
    # Validate all ports
    echo -e "${BLUE}Validating port assignments:${NC}"
    PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH" "$PYTHON_BIN" -c "
from dsa110_contimg.config.ports import PortManager
import sys

pm = PortManager()
results = pm.validate_all()

all_valid = True
for service, (is_valid, error) in results.items():
    if is_valid:
        port = pm.get_port(service, check_conflict=False)
        print(f'  ✓ {service:20s} -> {port:5d} (OK)')
    else:
        port = pm.get_port(service, check_conflict=False)
        print(f'  ✗ {service:20s} -> {port:5d} (CONFLICT: {error})')
        all_valid = False

sys.exit(0 if all_valid else 1)
" || echo -e "\n${YELLOW}Some ports have conflicts${NC}"
    
    echo ""
    
    # List all configured ports
    echo -e "${BLUE}All configured ports:${NC}"
    PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH" "$PYTHON_BIN" -c "
from dsa110_contimg.config.ports import PortManager
import json

pm = PortManager()
ports = pm.list_ports(check_conflict=False)

for service, port in sorted(ports.items()):
    config = pm.get_config(service)
    env_var = config.env_var if config.env_var else 'N/A'
    print(f'  {service:20s} -> {port:5d} (env: {env_var})')
"
else
    # Basic checks using environment variables
    echo -e "${BLUE}Checking ports from environment variables:${NC}\n"
    
    check_port_basic() {
        local port=$1
        local service=$2
        local env_var=$3
        
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 || \
           sudo lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "  ${RED}✗${NC} $service (port $port): ${RED}IN USE${NC}"
            lsof -i :$port 2>/dev/null | head -2 || true
            return 1
        else
            echo -e "  ${GREEN}✓${NC} $service (port $port): ${GREEN}FREE${NC}"
            return 0
        fi
    }
    
    # Check common ports
    check_port_basic "${CONTIMG_API_PORT:-8000}" "API" "CONTIMG_API_PORT"
    check_port_basic "${CONTIMG_DOCS_PORT:-8001}" "Docs" "CONTIMG_DOCS_PORT"
    check_port_basic "${CONTIMG_DASHBOARD_PORT:-3210}" "Dashboard" "CONTIMG_DASHBOARD_PORT"
    check_port_basic "${CONTIMG_FRONTEND_DEV_PORT:-5173}" "Frontend Dev" "CONTIMG_FRONTEND_DEV_PORT"
fi

echo ""
echo -e "${BLUE}Port configuration file:${NC}"
if [ -f "$PROJECT_DIR/config/ports.yaml" ]; then
    echo -e "  ${GREEN}✓${NC} $PROJECT_DIR/config/ports.yaml"
else
    echo -e "  ${YELLOW}⚠${NC} $PROJECT_DIR/config/ports.yaml ${YELLOW}(not found, using defaults)${NC}"
    echo -e "    Run: cp config/ports.yaml.example config/ports.yaml"
fi

echo ""
echo -e "${BLUE}Environment variables:${NC}"
env | grep -E "^(CONTIMG_|REDIS_)" | grep -i port | sort || echo "  (none set, using defaults)"

echo ""
echo -e "${BLUE}=== Check Complete ===${NC}"

