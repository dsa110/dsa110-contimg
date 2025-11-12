#!/bin/bash
# Start DSA-110 Pipeline Services
# Usage: ./scripts/start_services.sh [environment] [service]

set -e

# Default values
ENVIRONMENT=${1:-development}
SERVICE=${2:-all}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/pipeline_config.yaml"
LOG_DIR="$PROJECT_DIR/logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to start a service
start_service() {
    local service_name=$1
    local log_file="$LOG_DIR/${service_name}.log"
    
    echo "Starting $service_name service..."
    
    case $service_name in
        "hdf5_watcher")
            python -m services.hdf5_watcher.hdf5_watcher_service \
                --config "$CONFIG_FILE" \
                --environment "$ENVIRONMENT" \
                > "$log_file" 2>&1 &
            echo $! > "$LOG_DIR/${service_name}.pid"
            ;;
        "ms_processor")
            python -m services.ms_processor.ms_processor_service \
                --config "$CONFIG_FILE" \
                --environment "$ENVIRONMENT" \
                > "$log_file" 2>&1 &
            echo $! > "$LOG_DIR/${service_name}.pid"
            ;;
        "variability_analyzer")
            python -m services.variability_analyzer.variability_analyzer_service \
                --config "$CONFIG_FILE" \
                --environment "$ENVIRONMENT" \
                > "$log_file" 2>&1 &
            echo $! > "$LOG_DIR/${service_name}.pid"
            ;;
        "service_manager")
            python -m services.service_manager \
                --config "$CONFIG_FILE" \
                --environment "$ENVIRONMENT" \
                > "$log_file" 2>&1 &
            echo $! > "$LOG_DIR/${service_name}.pid"
            ;;
        *)
            echo "Unknown service: $service_name"
            exit 1
            ;;
    esac
    
    echo "$service_name service started (PID: $(cat "$LOG_DIR/${service_name}.pid"))"
}

# Function to check if Redis is running
check_redis() {
    if ! command -v redis-cli &> /dev/null; then
        echo "Warning: redis-cli not found. Redis may not be installed."
        return 1
    fi
    
    if ! redis-cli ping &> /dev/null; then
        echo "Error: Redis is not running. Please start Redis first."
        echo "  On Ubuntu/Debian: sudo systemctl start redis"
        echo "  On macOS: brew services start redis"
        echo "  Or run: redis-server"
        exit 1
    fi
    
    echo "Redis is running"
}

# Main execution
echo "DSA-110 Pipeline Service Starter"
echo "================================"
echo "Environment: $ENVIRONMENT"
echo "Service: $SERVICE"
echo "Config: $CONFIG_FILE"
echo "Logs: $LOG_DIR"
echo

# Check Redis
check_redis

# Change to project directory
cd "$PROJECT_DIR"

# Start services
if [ "$SERVICE" = "all" ]; then
    echo "Starting all services..."
    start_service "hdf5_watcher"
    start_service "ms_processor"
    start_service "variability_analyzer"
    start_service "service_manager"
    echo
    echo "All services started!"
    echo "Check logs in: $LOG_DIR"
    echo "To stop services: ./scripts/stop_services.sh"
else
    echo "Starting $SERVICE service..."
    start_service "$SERVICE"
    echo
    echo "$SERVICE service started!"
    echo "Check logs in: $LOG_DIR"
    echo "To stop service: ./scripts/stop_services.sh $SERVICE"
fi
