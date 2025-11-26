#!/bin/bash
#
# Container Health Monitoring Script
# Monitors Docker containers and optionally restarts unhealthy ones
#
# Usage:
#   ./monitor-containers.sh [--auto-restart] [--notify]
#
# Options:
#   --auto-restart    Automatically restart unhealthy containers
#   --notify          Send notifications (requires notification setup)
#   --continuous      Run continuously (check every 60s)
#

set -euo pipefail

# Configuration
AUTO_RESTART=false
NOTIFY=false
CONTINUOUS=false
CHECK_INTERVAL=60
LOG_FILE="/data/dsa110-contimg/logs/container-health.log"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --auto-restart)
      AUTO_RESTART=true
      shift
      ;;
    --notify)
      NOTIFY=true
      shift
      ;;
    --continuous)
      CONTINUOUS=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
  local level="$1"
  shift
  local message="$*"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Check container health
check_container_health() {
  local container_name="$1"
  
  # Check if container exists
  if ! docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
    log "WARN" "Container $container_name not found"
    return 1
  fi
  
  # Get container status
  local status=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null || echo "unknown")
  local health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
  
  log "INFO" "Container: $container_name | Status: $status | Health: $health"
  
  # Check if unhealthy
  if [[ "$health" == "unhealthy" ]] || [[ "$status" != "running" ]]; then
    log "ERROR" "Container $container_name is unhealthy or not running!"
    
    # Auto-restart if enabled
    if [[ "$AUTO_RESTART" == true ]]; then
      log "INFO" "Auto-restarting $container_name..."
      docker restart "$container_name"
      log "INFO" "Container $container_name restarted"
    fi
    
    # Send notification if enabled
    if [[ "$NOTIFY" == true ]]; then
      send_notification "$container_name" "$status" "$health"
    fi
    
    return 1
  fi
  
  return 0
}

# Send notification (placeholder - implement your notification method)
send_notification() {
  local container="$1"
  local status="$2"
  local health="$3"
  
  # TODO: Implement notification (email, Slack, etc.)
  log "NOTIFY" "Container $container is unhealthy (Status: $status, Health: $health)"
}

# Main monitoring loop
monitor_containers() {
  local containers=("dsa110-api" "dsa110-redis")
  local all_healthy=true
  
  log "INFO" "Starting container health check..."
  
  for container in "${containers[@]}"; do
    if ! check_container_health "$container"; then
      all_healthy=false
    fi
  done
  
  if [[ "$all_healthy" == true ]]; then
    log "INFO" "All containers are healthy ✓"
  else
    log "WARN" "Some containers are unhealthy!"
  fi
  
  return 0
}

# Main execution
main() {
  log "INFO" "Container Health Monitor Started"
  log "INFO" "Auto-restart: $AUTO_RESTART | Notify: $NOTIFY | Continuous: $CONTINUOUS"
  
  if [[ "$CONTINUOUS" == true ]]; then
    log "INFO" "Running in continuous mode (interval: ${CHECK_INTERVAL}s)"
    while true; do
      monitor_containers
      log "INFO" "Sleeping for ${CHECK_INTERVAL}s..."
      sleep "$CHECK_INTERVAL"
    done
  else
    monitor_containers
  fi
  
  log "INFO" "Container Health Monitor Completed"
}

# Run main
main
