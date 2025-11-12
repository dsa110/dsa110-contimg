#!/bin/bash
# Stop DSA-110 Pipeline Services
# Usage: ./scripts/stop_services.sh [service]

set -e

# Default values
SERVICE=${1:-all}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$LOG_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "Stopping $service_name service (PID: $pid)..."
            kill -TERM "$pid"
            
            # Wait for graceful shutdown
            local count=0
            while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                echo "Force killing $service_name service..."
                kill -KILL "$pid"
            fi
            
            echo "$service_name service stopped"
        else
            echo "$service_name service is not running"
        fi
        rm -f "$pid_file"
    else
        echo "$service_name service PID file not found"
    fi
}

# Main execution
echo "DSA-110 Pipeline Service Stopper"
echo "================================"
echo "Service: $SERVICE"
echo

# Change to project directory
cd "$PROJECT_DIR"

# Stop services
if [ "$SERVICE" = "all" ]; then
    echo "Stopping all services..."
    stop_service "service_manager"
    stop_service "variability_analyzer"
    stop_service "ms_processor"
    stop_service "hdf5_watcher"
    echo
    echo "All services stopped!"
else
    echo "Stopping $SERVICE service..."
    stop_service "$SERVICE"
    echo
    echo "$SERVICE service stopped!"
fi
