#!/bin/bash
# Safe frontend dev server startup with automatic duplicate prevention
# This script should be used instead of directly running "npm run dev"

set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_DIR="$(cd "$FRONTEND_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cd "$FRONTEND_DIR"

echo -e "${GREEN}=== Safe Frontend Dev Server Startup ===${NC}"
echo ""

# Step 1: Check for and clean up duplicates
echo "Step 1: Checking for duplicate instances..."
if [ -f "$PROJECT_DIR/scripts/prevent-duplicate-services.sh" ]; then
    AUTO_CLEANUP_DUPLICATES=1 "$PROJECT_DIR/scripts/prevent-duplicate-services.sh" frontend
    prevention_result=$?
    
    if [ $prevention_result -eq 2 ]; then
        echo -e "${YELLOW}Frontend dev server already running - exiting${NC}"
        exit 0
    elif [ $prevention_result -ne 0 ]; then
        echo -e "${RED}Failed to prevent duplicates${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Warning: prevent-duplicate-services.sh not found, skipping check${NC}"
fi

echo ""

# Step 2: Acquire service lock
echo "Step 2: Acquiring service lock..."
if [ -f "$PROJECT_DIR/scripts/service-lock.sh" ]; then
    if ! "$PROJECT_DIR/scripts/service-lock.sh" frontend-dev acquire; then
        echo -e "${RED}ERROR: Could not acquire lock - another instance may be starting${NC}"
        echo "  Wait a moment and try again, or check: $PROJECT_DIR/scripts/check-duplicate-services.sh"
        exit 1
    fi
    echo -e "${GREEN}:check_mark: Lock acquired${NC}"
else
    echo -e "${YELLOW}Warning: service-lock.sh not found, skipping lock${NC}"
fi

echo ""

# Step 3: Verify port is free
DEV_PORT="${CONTIMG_FRONTEND_DEV_PORT:-3210}"
echo "Step 3: Verifying port $DEV_PORT is available..."
if lsof -ti :$DEV_PORT >/dev/null 2>&1; then
    echo -e "${RED}ERROR: Port $DEV_PORT is already in use${NC}"
    lsof -i :$DEV_PORT | head -3
    "$PROJECT_DIR/scripts/service-lock.sh" frontend-dev release 2>/dev/null || true
    exit 1
fi
echo -e "${GREEN}:check_mark: Port $DEV_PORT is free${NC}"

echo ""

# Step 4: Start the dev server
echo "Step 4: Starting frontend dev server..."
echo -e "${GREEN}Starting: vite (direct)${NC}"
echo ""

# Trap to release lock on exit
trap 'if [ -f "$PROJECT_DIR/scripts/service-lock.sh" ]; then "$PROJECT_DIR/scripts/service-lock.sh" frontend-dev release; fi' EXIT

# Start vite directly (not via npm run dev to avoid recursion)
npx vite

