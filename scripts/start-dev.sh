#!/bin/bash
#
# DSA-110 Continuum Imaging Pipeline - Development Server Startup
#
# This script starts both the backend API and frontend dev server for local testing.
# Usage: ./scripts/start-dev.sh
#
# Services started:
#   - Backend API (FastAPI/uvicorn) on port 8000
#   - Frontend dev server (Vite) on port 3000
#
# The frontend proxies /api/* requests to the backend automatically.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Shutting down services..."
    
    # Kill background jobs
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        log_info "Stopped backend (PID $BACKEND_PID)"
    fi
    
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        log_info "Stopped frontend (PID $FRONTEND_PID)"
    fi
    
    # Kill any remaining processes on our ports
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    log_success "Cleanup complete"
    exit 0
}

# Set up trap for cleanup on exit
trap cleanup SIGINT SIGTERM EXIT

# =============================================================================
# Pre-flight checks
# =============================================================================

log_info "DSA-110 Development Server Startup"
log_info "=================================="

# Check if we're in the project root
if [ ! -d "$PROJECT_ROOT/frontend" ] || [ ! -d "$PROJECT_ROOT/backend" ]; then
    log_error "Cannot find frontend/ or backend/ directories"
    log_error "Please run this script from the project root"
    exit 1
fi

# Check for required commands
for cmd in python npm lsof; do
    if ! command -v $cmd &> /dev/null; then
        log_error "Required command not found: $cmd"
        exit 1
    fi
done

# =============================================================================
# Kill any existing processes on our ports
# =============================================================================

log_info "Checking for existing processes..."

for port in 8000 3000; do
    pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        log_warn "Killing existing process(es) on port $port: $pids"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
done

# =============================================================================
# Start Backend
# =============================================================================

log_info "Starting backend API server..."

cd "$PROJECT_ROOT/backend"

# Activate conda environment if available
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    if conda activate casa6 2>/dev/null; then
        log_success "Activated conda environment: casa6"
    fi
fi

# Start uvicorn in background
python -m uvicorn src.dsa110_contimg.api.app:app \
    --host 127.0.0.1 \
    --port 8000 \
    --reload \
    --reload-dir src \
    2>&1 | sed 's/^/[backend] /' &

BACKEND_PID=$!
log_success "Backend started (PID $BACKEND_PID)"

# Wait for backend to be ready
log_info "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        log_success "Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "Backend failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# =============================================================================
# Start Frontend
# =============================================================================

log_info "Starting frontend dev server..."

cd "$PROJECT_ROOT/frontend"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    log_info "Installing frontend dependencies..."
    npm install
fi

# Start Vite dev server in background
npm run dev 2>&1 | sed 's/^/[frontend] /' &

FRONTEND_PID=$!
log_success "Frontend started (PID $FRONTEND_PID)"

# Wait for frontend to be ready
log_info "Waiting for frontend to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:3000 > /dev/null 2>&1; then
        log_success "Frontend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        log_warn "Frontend may still be starting..."
    fi
    sleep 1
done

# =============================================================================
# Ready!
# =============================================================================

echo ""
log_success "============================================"
log_success "  Development servers are running!"
log_success "============================================"
echo ""
echo -e "  ${GREEN}Frontend:${NC}  http://127.0.0.1:3000"
echo -e "  ${GREEN}Backend:${NC}   http://127.0.0.1:8000"
echo -e "  ${GREEN}API Docs:${NC}  http://127.0.0.1:8000/api/docs"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services"
echo ""

# Wait for processes
wait
