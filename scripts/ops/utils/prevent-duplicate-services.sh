#!/bin/bash
# Proactive prevention of duplicate services
# This script should be called BEFORE starting any service
# It automatically cleans up duplicates and prevents conflicts

set -e

PROJECT_DIR="/data/dsa110-contimg"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_TYPE="${1:-all}"  # api, dashboard, frontend, or all
AUTO_CLEANUP="${AUTO_CLEANUP_DUPLICATES:-1}"  # Set to 0 to disable auto-cleanup

echo -e "${BLUE}=== Proactive Duplicate Prevention ===${NC}"
echo ""

check_and_cleanup_vite() {
    local auto_cleanup=$1
    
    # Check for duplicate Vite instances
    # Check port 3000 (current default) and legacy ports for cleanup
    vite_ports=""
    for port in 3000 3210 5173 5174 5175 5176 5177 5178 5179; do
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
        echo -e "${YELLOW}:warning:  Found $vite_count Vite instances${NC}"
        
        # Keep port 3000 (current default)
        primary_port=3000
        if ! echo "$vite_ports" | grep -q "3000"; then
            primary_port=3210  # fallback to production port
        fi
        duplicates=""
        npm_pids_to_kill=""
        
        for port in $vite_ports; do
            if [ "$port" != "$primary_port" ]; then
                vite_pid=$(lsof -ti :$port 2>/dev/null | head -1)
                if [ -n "$vite_pid" ]; then
                    duplicates="$duplicates $vite_pid"
                    # Find parent npm process
                    npm_pid=$(ps -o ppid= -p "$vite_pid" 2>/dev/null | tr -d ' ')
                    if [ -n "$npm_pid" ]; then
                        npm_cmd=$(ps -p "$npm_pid" -o cmd --no-headers 2>/dev/null | grep -i "npm.*dev" || true)
                        if [ -n "$npm_cmd" ]; then
                            npm_pids_to_kill="$npm_pids_to_kill $npm_pid"
                        fi
                    fi
                fi
            fi
        done
        
        if [ -n "$duplicates" ]; then
            if [ "$auto_cleanup" = "1" ]; then
                echo -e "${YELLOW}Auto-cleaning duplicates...${NC}"
                # Kill Vite processes
                for pid in $duplicates; do
                    kill "$pid" 2>/dev/null || true
                done
                # Kill parent npm processes
                for npm_pid in $npm_pids_to_kill; do
                    kill "$npm_pid" 2>/dev/null || true
                done
                sleep 2
                echo -e "${GREEN}:check: Duplicates cleaned up${NC}"
            else
                echo -e "${RED}:cross: Duplicates found but auto-cleanup disabled${NC}"
                echo "  Run: AUTO_CLEANUP_DUPLICATES=1 $0 frontend"
                return 1
            fi
        fi
    elif [ "$vite_count" -eq 1 ]; then
        port=$(echo "$vite_ports" | head -1)
        if [ "$port" != "5173" ]; then
            echo -e "${YELLOW}:warning:  Vite running on non-standard port $port${NC}"
            if [ "$auto_cleanup" = "1" ]; then
                vite_pid=$(lsof -ti :$port 2>/dev/null | head -1)
                npm_pid=$(ps -o ppid= -p "$vite_pid" 2>/dev/null | tr -d ' ')
                if [ -n "$npm_pid" ]; then
                    kill "$npm_pid" 2>/dev/null || true
                    sleep 1
                    echo -e "${GREEN}:check: Cleaned up${NC}"
                fi
            fi
        else
            echo -e "${GREEN}:check: Vite already running on port 5173${NC}"
            return 2  # Service already running (not an error)
        fi
    else
        echo -e "${GREEN}:check: No Vite instances running${NC}"
    fi
    
    return 0
}

check_and_cleanup_api() {
    local auto_cleanup=$1
    
    # Check for duplicate API instances
    api_pids=$(pgrep -f "uvicorn.*dsa110_contimg" 2>/dev/null || true)
    if [ -n "$api_pids" ]; then
        api_count=$(echo "$api_pids" | wc -w | tr -d ' ')
        
        if [ "$api_count" -gt 1 ]; then
            echo -e "${YELLOW}:warning:  Found $api_count API instances${NC}"
            
            if [ "$auto_cleanup" = "1" ]; then
                echo -e "${YELLOW}Auto-cleaning duplicates...${NC}"
                # Keep first, kill others
                api_pid_array=($api_pids)
                for pid in "${api_pid_array[@]:1}"; do
                    kill "$pid" 2>/dev/null || true
                done
                sleep 1
                echo -e "${GREEN}:check: Duplicates cleaned up${NC}"
            else
                echo -e "${RED}:cross: Duplicates found but auto-cleanup disabled${NC}"
                return 1
            fi
        elif [ "$api_count" -eq 1 ]; then
            api_port=$(lsof -ti -a -p "${api_pids%% *}" -i :8000-8010 2>/dev/null | head -1 || echo "unknown")
            echo -e "${GREEN}:check: API already running on port $api_port${NC}"
            return 2  # Service already running (not an error)
        fi
    else
        echo -e "${GREEN}:check: No API instances running${NC}"
    fi
    
    return 0
}

# Main logic
case "$SERVICE_TYPE" in
    frontend|dashboard)
        check_and_cleanup_vite "$AUTO_CLEANUP"
        exit_code=$?
        if [ $exit_code -eq 2 ]; then
            echo -e "${BLUE}Service already running - skipping start${NC}"
            exit 0
        fi
        exit $exit_code
        ;;
    api)
        check_and_cleanup_api "$AUTO_CLEANUP"
        exit_code=$?
        if [ $exit_code -eq 2 ]; then
            echo -e "${BLUE}Service already running - skipping start${NC}"
            exit 0
        fi
        exit $exit_code
        ;;
    all)
        api_result=0
        vite_result=0
        
        check_and_cleanup_api "$AUTO_CLEANUP" || api_result=$?
        echo ""
        check_and_cleanup_vite "$AUTO_CLEANUP" || vite_result=$?
        
        if [ $api_result -eq 1 ] || [ $vite_result -eq 1 ]; then
            exit 1
        fi
        exit 0
        ;;
    *)
        echo "Usage: $0 {api|dashboard|frontend|all}"
        exit 1
        ;;
esac

