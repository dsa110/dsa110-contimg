#!/bin/bash
# Check for duplicate service instances
# Helps identify and clean up duplicate Vite, API, or other service instances

set -e

PROJECT_DIR="/data/dsa110-contimg"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "Checking for duplicate service instances..."
echo ""

# Check for duplicate Vite instances
# Check by port usage - find all processes listening on Vite ports
vite_ports=""
for port in 5173 5174 5175 5176 5177 5178 5179; do
    pid=$(lsof -ti :$port 2>/dev/null | head -1)
    if [ -n "$pid" ]; then
        # Check if this PID is actually a Vite process
        cmd=$(ps -p "$pid" -o cmd --no-headers 2>/dev/null | grep -i vite || true)
        if [ -n "$cmd" ]; then
            vite_ports="$vite_ports $port"
        fi
    fi
done
vite_ports=$(echo "$vite_ports" | tr ' ' '\n' | grep -v '^$' | sort -u)
vite_count=$(echo "$vite_ports" | wc -l | tr -d ' ')

if [ "$vite_count" -gt 1 ]; then
    echo -e "${YELLOW}⚠️  Warning: Multiple Vite instances detected ($vite_count ports in use)${NC}"
    echo ""
    echo "Vite instances by port:"
    for port in $vite_ports; do
        pid=$(lsof -ti :$port 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
            cmd=$(ps -p "$pid" -o cmd --no-headers 2>/dev/null | head -c 80)
            echo "  Port $port: PID $pid ($cmd)"
        fi
    done
    echo ""
    echo "Recommendation: Keep only one Vite instance (preferably on port 5173)"
    echo "  To kill duplicates: pkill -f 'vite.*517[4-9]'"
else
    echo -e "${GREEN}✓ No duplicate Vite instances${NC}"
fi

echo ""

# Check for duplicate API instances
api_pids=$(pgrep -f "uvicorn.*dsa110_contimg" 2>/dev/null || true)
if [ -z "$api_pids" ]; then
    api_count=0
else
    api_count=$(echo "$api_pids" | wc -w | tr -d ' ')
fi

if [ "$api_count" -gt 1 ]; then
    echo -e "${YELLOW}⚠️  Warning: Multiple API instances detected ($api_count)${NC}"
    echo ""
    echo "Running API processes:"
    echo "$api_processes" | while read -r line; do
        pid=$(echo "$line" | awk '{print $1}')
        port=$(echo "$line" | grep -oE "port [0-9]+" | awk '{print $2}' || echo "unknown")
        echo "  PID $pid on port $port"
    done
    echo ""
    echo "Recommendation: Keep only one API instance"
    echo "  To kill duplicates: pkill -f 'uvicorn.*dsa110_contimg'"
else
    echo -e "${GREEN}✓ No duplicate API instances${NC}"
fi

echo ""

# Summary
total_duplicates=0
if [ "$vite_count" -gt 1 ]; then
    total_duplicates=$((total_duplicates + 1))
fi
if [ "$api_count" -gt 1 ]; then
    total_duplicates=$((total_duplicates + 1))
fi

if [ "$total_duplicates" -gt 0 ]; then
    echo -e "${RED}Found $total_duplicates service type(s) with duplicate instances${NC}"
    exit 1
else
    echo -e "${GREEN}✓ No duplicate services detected${NC}"
    exit 0
fi

