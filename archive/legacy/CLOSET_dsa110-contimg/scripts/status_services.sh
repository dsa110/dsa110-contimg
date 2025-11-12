#!/bin/bash
# Check Status of DSA-110 Pipeline Services
# Usage: ./scripts/status_services.sh [service]

set -e

# Default values
SERVICE=${1:-all}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"

# Function to check service status
check_service() {
    local service_name=$1
    local pid_file="$LOG_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "✓ $service_name service is running (PID: $pid)"
            return 0
        else
            echo "✗ $service_name service is not running (stale PID file)"
            return 1
        fi
    else
        echo "✗ $service_name service is not running (no PID file)"
        return 1
    fi
}

# Function to show service logs
show_logs() {
    local service_name=$1
    local log_file="$LOG_DIR/${service_name}.log"
    
    if [ -f "$log_file" ]; then
        echo "Recent logs for $service_name:"
        echo "----------------------------------------"
        tail -n 20 "$log_file"
        echo "----------------------------------------"
    else
        echo "No log file found for $service_name"
    fi
}

# Main execution
echo "DSA-110 Pipeline Service Status"
echo "==============================="
echo "Service: $SERVICE"
echo

# Change to project directory
cd "$PROJECT_DIR"

# Check services
if [ "$SERVICE" = "all" ]; then
    echo "Checking all services..."
    echo
    
    services=("hdf5_watcher" "ms_processor" "variability_analyzer" "service_manager")
    running_count=0
    
    for service in "${services[@]}"; do
        if check_service "$service"; then
            running_count=$((running_count + 1))
        fi
    done
    
    echo
    echo "Summary: $running_count/${#services[@]} services running"
    
    if [ $running_count -eq 0 ]; then
        echo
        echo "No services are running. To start services:"
        echo "  ./scripts/start_services.sh"
    elif [ $running_count -lt ${#services[@]} ]; then
        echo
        echo "Some services are not running. To restart all services:"
        echo "  ./scripts/stop_services.sh && ./scripts/start_services.sh"
    else
        echo
        echo "All services are running normally!"
    fi
    
else
    echo "Checking $SERVICE service..."
    echo
    
    if check_service "$SERVICE"; then
        echo
        show_logs "$SERVICE"
    else
        echo
        echo "To start $SERVICE service:"
        echo "  ./scripts/start_services.sh development $SERVICE"
    fi
fi

echo
echo "Log directory: $LOG_DIR"
echo "To view all logs: tail -f $LOG_DIR/*.log"
