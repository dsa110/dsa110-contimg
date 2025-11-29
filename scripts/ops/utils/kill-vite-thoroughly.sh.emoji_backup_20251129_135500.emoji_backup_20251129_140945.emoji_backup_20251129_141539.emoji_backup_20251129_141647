#!/bin/bash
# Thoroughly kill all Vite and npm processes, including respawning ones
# This script finds and kills processes in the correct order to prevent respawning

set -e

PROJECT_DIR="/data/dsa110-contimg"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Thorough Vite Process Cleanup ===${NC}"
echo ""

# Step 0: Check for PM2-managed processes
echo -e "${YELLOW}Step 0: Checking for PM2-managed processes...${NC}"
# Find PM2 daemon - check for process with "PM2" in command
pm2_running=$(ps aux | grep -i "PM2.*God\|pm2.*God\|PM2.*Daemon" | grep -v grep | awk '{print $2}' | head -1 || true)
if [ -n "$pm2_running" ]; then
    echo -e "${RED}⚠️  WARNING: PM2 daemon is running!${NC}"
    echo "  PM2 daemon PID: $pm2_running"
    
    # Check if any npm/vite processes have PM2 as parent
    pm2_children=$(ps -eo pid,ppid,cmd | awk -v pm2="$pm2_running" '$2 == pm2 && /npm|vite/ {print $1}' || true)
    if [ -n "$pm2_children" ]; then
        echo "  PM2-managed processes found:"
        for pid in $pm2_children; do
            ps -p "$pid" -o pid,cmd --no-headers 2>/dev/null | sed 's/^/    /'
        done
        echo ""
        echo "  PM2 will automatically restart these processes!"
        echo "  You need to stop PM2 first:"
        echo ""
        
        # Try to find pm2 command
        PM2_CMD=""
        if command -v pm2 >/dev/null 2>&1; then
            PM2_CMD="pm2"
        elif [ -f "$HOME/.npm-global/bin/pm2" ]; then
            PM2_CMD="$HOME/.npm-global/bin/pm2"
        elif [ -f "/usr/local/bin/pm2" ]; then
            PM2_CMD="/usr/local/bin/pm2"
        fi
        
        if [ -n "$PM2_CMD" ]; then
            echo "    $PM2_CMD stop all"
            echo "    $PM2_CMD delete all"
            echo ""
            read -p "Stop PM2 processes now? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                "$PM2_CMD" stop all 2>/dev/null || true
                "$PM2_CMD" delete all 2>/dev/null || true
                sleep 2
                echo -e "${GREEN}✓ PM2 processes stopped${NC}"
            else
                echo -e "${YELLOW}Continuing anyway - PM2 may restart processes${NC}"
                echo "  You may need to kill PM2 daemon: sudo kill $pm2_running"
            fi
        else
            echo "    pm2 command not found in PATH"
            echo ""
            echo -e "${YELLOW}  Since pm2 command is not available, you can:${NC}"
            echo "    1. Kill PM2 daemon directly (recommended)"
            echo "    2. Find pm2 command: find ~ -name pm2 2>/dev/null"
            echo ""
            read -p "Kill PM2 daemon directly? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "  Killing PM2 daemon (PID $pm2_running)..."
                kill "$pm2_running" 2>/dev/null || sudo kill "$pm2_running" 2>/dev/null || true
                sleep 2
                # Verify it's dead
                if ! ps -p "$pm2_running" > /dev/null 2>&1; then
                    echo -e "${GREEN}✓ PM2 daemon killed${NC}"
                else
                    echo -e "${RED}✗ PM2 daemon still running - may need sudo${NC}"
                    echo "  Try: sudo kill $pm2_running"
                fi
            else
                echo -e "${YELLOW}  Skipping PM2 kill - processes may respawn${NC}"
            fi
        fi
        echo ""
    else
        echo -e "${YELLOW}  No PM2-managed Vite processes found, but PM2 daemon is running${NC}"
    fi
else
    echo -e "${GREEN}✓ No PM2 daemon running${NC}"
fi
echo ""

# Step 1: Find all Vite processes and their parents
echo -e "${YELLOW}Step 1: Finding all Vite processes...${NC}"
vite_pids=""
vite_ports=""
for port in 5173 5174 5175 5176 5177 5178 5179; do
    pid=$(lsof -ti :$port 2>/dev/null | head -1)
    if [ -n "$pid" ]; then
        cmd=$(ps -p "$pid" -o cmd --no-headers 2>/dev/null | grep -i vite || true)
        if [ -n "$cmd" ]; then
            vite_pids="$vite_pids $pid"
            vite_ports="$vite_ports $port"
            echo "  Port $port: PID $pid"
        fi
    fi
done

if [ -z "$vite_pids" ]; then
    echo -e "${GREEN}✓ No Vite processes found${NC}"
    exit 0
fi

echo ""

# Step 2: Find all parent npm processes
echo -e "${YELLOW}Step 2: Finding parent npm processes...${NC}"
npm_pids=""
for vite_pid in $vite_pids; do
    parent_pid=$(ps -o ppid= -p "$vite_pid" 2>/dev/null | tr -d ' ')
    if [ -n "$parent_pid" ]; then
        parent_cmd=$(ps -p "$parent_pid" -o cmd --no-headers 2>/dev/null || echo "")
        if echo "$parent_cmd" | grep -qi "npm.*dev\|node.*vite"; then
            npm_pids="$npm_pids $parent_pid"
            echo "  Vite PID $vite_pid -> Parent PID $parent_pid ($(echo $parent_cmd | head -c 60))"
        fi
    fi
done

# Also find any standalone npm run dev processes
standalone_npm=$(pgrep -f "npm run dev" 2>/dev/null || true)
for npm_pid in $standalone_npm; do
    if ! echo " $npm_pids " | grep -q " $npm_pid "; then
        npm_pids="$npm_pids $npm_pid"
        cmd=$(ps -p "$npm_pid" -o cmd --no-headers 2>/dev/null | head -c 60)
        echo "  Standalone npm PID $npm_pid ($cmd)"
    fi
done

npm_pids=$(echo "$npm_pids" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')

echo ""

# Step 3: Find process group leaders and session leaders
echo -e "${YELLOW}Step 3: Finding process groups and sessions...${NC}"
pgids=""
sids=""
for pid in $vite_pids $npm_pids; do
    if [ -n "$pid" ]; then
        pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ' || echo "")
        sid=$(ps -o sid= -p "$pid" 2>/dev/null | tr -d ' ' || echo "")
        if [ -n "$pgid" ] && [ "$pgid" != "1" ]; then
            pgids="$pgids $pgid"
        fi
        if [ -n "$sid" ] && [ "$sid" != "1" ]; then
            sids="$sids $sid"
        fi
    fi
done

pgids=$(echo "$pgids" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')
sids=$(echo "$sids" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')

if [ -n "$pgids" ]; then
    echo "  Process groups: $pgids"
fi
if [ -n "$sids" ]; then
    echo "  Sessions: $sids"
fi

echo ""

# Step 4: Find any scripts or wrappers that might restart processes
echo -e "${YELLOW}Step 4: Finding wrapper scripts...${NC}"
wrapper_pids=""
for npm_pid in $npm_pids; do
    parent_pid=$(ps -o ppid= -p "$npm_pid" 2>/dev/null | tr -d ' ')
    if [ -n "$parent_pid" ] && [ "$parent_pid" != "1" ]; then
        parent_cmd=$(ps -p "$parent_pid" -o cmd --no-headers 2>/dev/null | head -c 80 || echo "")
        if echo "$parent_cmd" | grep -qiE "bash.*dev|sh.*dev|start.*dev|run.*dev|script"; then
            wrapper_pids="$wrapper_pids $parent_pid"
            echo "  Wrapper PID $parent_pid ($parent_cmd)"
        fi
    fi
done

wrapper_pids=$(echo "$wrapper_pids" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')

echo ""

# Step 5: Kill in correct order (children first, then parents, then wrappers)
echo -e "${RED}Step 5: Killing processes (in order: Vite -> npm -> wrappers)...${NC}"
echo ""

# Kill Vite processes first
if [ -n "$vite_pids" ]; then
    for pid in $vite_pids; do
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "  Killing Vite PID $pid..."
            kill "$pid" 2>/dev/null || sudo kill "$pid" 2>/dev/null || true
        fi
    done
    sleep 1
fi

# Kill npm processes
if [ -n "$npm_pids" ]; then
    for pid in $npm_pids; do
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "  Killing npm PID $pid..."
            kill "$pid" 2>/dev/null || sudo kill "$pid" 2>/dev/null || true
        fi
    done
    sleep 1
fi

# Kill wrapper scripts
if [ -n "$wrapper_pids" ]; then
    for pid in $wrapper_pids; do
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "  Killing wrapper PID $pid..."
            kill "$pid" 2>/dev/null || sudo kill "$pid" 2>/dev/null || true
        fi
    done
    sleep 1
fi

# Kill by process group if needed
if [ -n "$pgids" ]; then
    for pgid in $pgids; do
        if ps -p "-$pgid" > /dev/null 2>&1 2>/dev/null; then
            echo "  Killing process group $pgid..."
            kill -TERM -"$pgid" 2>/dev/null || sudo kill -TERM -"$pgid" 2>/dev/null || true
        fi
    done
    sleep 2
fi

echo ""

# Step 6: Force kill any remaining processes
echo -e "${YELLOW}Step 6: Force killing any remaining processes...${NC}"
remaining_vite=$(pgrep -f "vite" 2>/dev/null | grep -v "grep" || true)
remaining_npm=$(pgrep -f "npm run dev" 2>/dev/null || true)

if [ -n "$remaining_vite" ] || [ -n "$remaining_npm" ]; then
    for pid in $remaining_vite $remaining_npm; do
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "  Force killing PID $pid..."
            kill -9 "$pid" 2>/dev/null || sudo kill -9 "$pid" 2>/dev/null || true
        fi
    done
    sleep 1
fi

echo ""

# Step 7: Verify cleanup
echo -e "${BLUE}Step 7: Verifying cleanup...${NC}"
remaining=""
for port in 5173 5174 5175 5176 5177 5178 5179; do
    pid=$(lsof -ti :$port 2>/dev/null | head -1)
    if [ -n "$pid" ]; then
        cmd=$(ps -p "$pid" -o cmd --no-headers 2>/dev/null | grep -i vite || true)
        if [ -n "$cmd" ]; then
            remaining="$remaining $port"
        fi
    fi
done

if [ -z "$remaining" ]; then
    echo -e "${GREEN}✓ All Vite processes killed successfully${NC}"
    exit 0
else
    echo -e "${RED}✗ Some processes still running on ports: $remaining${NC}"
    echo ""
    echo "Remaining processes:"
    for port in $remaining; do
        pid=$(lsof -ti :$port 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
            ps -p "$pid" -o pid,ppid,cmd,etime
        fi
    done
    echo ""
    echo "Try running with sudo: sudo $0"
    exit 1
fi

