#!/bin/bash
# Clean up duplicate service instances
# Kills duplicate Vite/API instances, keeping only the primary ones

set -e

PROJECT_DIR="/data/dsa110-contimg"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "Cleaning up duplicate service instances..."
echo ""

# Check for duplicate Vite instances
vite_ports=""
for port in 5173 5174 5175 5176 5177 5178 5179; do
    pid=$(lsof -ti :$port 2>/dev/null | head -1)
    if [ -n "$pid" ]; then
        cmd=$(ps -p "$pid" -o cmd --no-headers 2>/dev/null | grep -i vite || true)
        if [ -n "$cmd" ]; then
            vite_ports="$vite_ports $port"
        fi
    fi
done
vite_ports=$(echo "$vite_ports" | tr ' ' '\n' | grep -v '^$' | sort -u)
vite_count=$(echo "$vite_ports" | wc -l | tr -d ' ')

if [ "$vite_count" -gt 1 ]; then
    echo -e "${YELLOW}Found $vite_count Vite instances${NC}"
    echo ""
    
    # Keep port 5173 (primary), kill others
    primary_port=5173
    duplicates=""
    
    for port in $vite_ports; do
        if [ "$port" != "$primary_port" ]; then
            pid=$(lsof -ti :$port 2>/dev/null | head -1)
            if [ -n "$pid" ]; then
                duplicates="$duplicates $pid"
                echo "  Will kill: Port $port (PID $pid)"
            fi
        else
            pid=$(lsof -ti :$port 2>/dev/null | head -1)
            echo "  Keeping: Port $port (PID $pid) - primary instance"
        fi
    done
    
    if [ -n "$duplicates" ]; then
        echo ""
        echo -e "${YELLOW}Note: Killing parent 'npm run dev' processes to prevent auto-restart${NC}"
        read -p "Kill duplicate Vite instances and their parent npm processes? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Use thorough cleanup script if available
            if [ -f "$PROJECT_DIR/scripts/kill-vite-thoroughly.sh" ]; then
                echo "  Using thorough cleanup script..."
                "$PROJECT_DIR/scripts/kill-vite-thoroughly.sh"
            else
                # Basic cleanup: Kill Vite processes first
                for pid in $duplicates; do
                    echo "  Killing Vite PID $pid..."
                    kill "$pid" 2>/dev/null || sudo kill "$pid" 2>/dev/null || true
                done
                sleep 1
                
                # Find and kill parent npm processes for duplicates
                for port in $vite_ports; do
                    if [ "$port" != "$primary_port" ]; then
                        vite_pid=$(lsof -ti :$port 2>/dev/null | head -1)
                        if [ -n "$vite_pid" ]; then
                            # Find parent npm process
                            npm_pid=$(ps -o ppid= -p "$vite_pid" 2>/dev/null | tr -d ' ')
                            if [ -n "$npm_pid" ]; then
                                npm_cmd=$(ps -p "$npm_pid" -o cmd --no-headers 2>/dev/null | grep -i "npm.*dev" || true)
                                if [ -n "$npm_cmd" ]; then
                                    echo "  Killing parent npm process PID $npm_pid..."
                                    kill "$npm_pid" 2>/dev/null || sudo kill "$npm_pid" 2>/dev/null || true
                                fi
                            fi
                        fi
                    fi
                done
                
                # Also kill any standalone npm run dev processes
                standalone_npm=$(pgrep -f "npm run dev" 2>/dev/null || true)
                if [ -n "$standalone_npm" ]; then
                    for npm_pid in $standalone_npm; do
                        # Check if this npm is parent of a duplicate Vite
                        child_vite=$(pgrep -P "$npm_pid" -f vite 2>/dev/null | head -1 || true)
                        if [ -n "$child_vite" ]; then
                            vite_port=$(lsof -ti -a -p "$child_vite" -i :5173-5179 2>/dev/null | head -1 || true)
                            if [ -n "$vite_port" ] && [ "$vite_port" != "5173" ]; then
                                echo "  Killing npm process PID $npm_pid (parent of duplicate on port $vite_port)..."
                                kill "$npm_pid" 2>/dev/null || sudo kill "$npm_pid" 2>/dev/null || true
                            fi
                        fi
                    done
                fi
                
                sleep 2
                echo -e "${GREEN}✓ Duplicate Vite instances and parent npm processes killed${NC}"
            fi
        else
            echo "Skipped"
        fi
    fi
else
    echo -e "${GREEN}✓ No duplicate Vite instances${NC}"
fi

echo ""

# Check for duplicate API instances
api_pids=$(pgrep -f "uvicorn.*dsa110_contimg" 2>/dev/null || true)
if [ -n "$api_pids" ]; then
    api_count=$(echo "$api_pids" | wc -w | tr -d ' ')
    
    if [ "$api_count" -gt 1 ]; then
        echo -e "${YELLOW}Found $api_count API instances${NC}"
        echo ""
        
        # Keep the first one, kill others
        api_pid_array=($api_pids)
        primary_pid=${api_pid_array[0]}
        
        echo "  Keeping: PID $primary_pid - primary instance"
        for pid in "${api_pid_array[@]:1}"; do
            echo "  Will kill: PID $pid"
        done
        
        echo ""
        read -p "Kill duplicate API instances? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for pid in "${api_pid_array[@]:1}"; do
                echo "  Killing PID $pid..."
                kill "$pid" 2>/dev/null || true
            done
            sleep 1
            echo -e "${GREEN}✓ Duplicate API instances killed${NC}"
        else
            echo "Skipped"
        fi
    else
        echo -e "${GREEN}✓ No duplicate API instances${NC}"
    fi
else
    echo -e "${GREEN}✓ No API instances running${NC}"
fi

echo ""
echo "Cleanup complete. Run './scripts/check-duplicate-services.sh' to verify."

