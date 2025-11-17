#!/bin/bash
# Restart script that kills ports and restarts all dev dependencies
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$FRONTEND_DIR/.." && pwd)"

# Ports to kill (frontend dev, API backend, JS9 socket.io, Vite defaults)
PORTS=(3210 8000 2718 5173 5174)

echo "🛑 Stopping processes on ports: ${PORTS[*]}"

# Function to kill process on a port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "   ✓ Killing process(es) on port $port (PIDs: $pids)"
        echo "$pids" | xargs -r kill -9 2>/dev/null || true
        sleep 1
        # Verify it's dead
        local remaining=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$remaining" ]; then
            echo "   ⚠ Warning: Process still running, force killing..."
            echo "$remaining" | xargs -r kill -9 2>/dev/null || true
            sleep 0.5
        fi
    fi
}

# Kill all ports
for port in "${PORTS[@]}"; do
    kill_port "$port"
done

echo ""
echo "🐳 Restarting Docker services (if running)..."

# Start/restart docker-compose services (if docker-compose is available and services exist)
cd "$PROJECT_ROOT"
if [ -f "docker-compose.yml" ]; then
    if command -v docker-compose &> /dev/null; then
        echo "   Starting/restarting api and dashboard-dev services..."
        # Use 'up -d' to start services if stopped, or restart if running
        docker-compose up -d api dashboard-dev 2>/dev/null || {
            echo "   ⚠ Warning: Could not start Docker services (they may need to be built first)"
            echo "   Run: cd /data/dsa110-contimg && docker-compose up -d --build api"
        }
    elif command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
        echo "   Starting/restarting api and dashboard-dev services..."
        # Use 'up -d' to start services if stopped, or restart if running
        docker compose up -d api dashboard-dev 2>/dev/null || {
            echo "   ⚠ Warning: Could not start Docker services (they may need to be built first)"
            echo "   Run: cd /data/dsa110-contimg && docker compose up -d --build api"
        }
    else
        echo "   (Docker Compose not available)"
    fi
else
    echo "   (docker-compose.yml not found, skipping Docker restart)"
fi

echo ""
echo "🚀 Starting frontend dev server..."

# Activate casa6 environment if conda is available
if [ -f "/opt/miniforge/etc/profile.d/conda.sh" ]; then
    echo "   Activating casa6 conda environment..."
    source /opt/miniforge/etc/profile.d/conda.sh
    conda activate casa6 2>/dev/null || {
        echo "   ⚠ Warning: Could not activate casa6, continuing anyway..."
    }
fi

# Start the dev server
cd "$FRONTEND_DIR"
exec bash scripts/start-dev.sh

