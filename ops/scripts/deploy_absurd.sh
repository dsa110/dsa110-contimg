#!/usr/bin/env bash
# Deploy Absurd Worker Service for DSA-110 Continuum Imaging Pipeline
#
# Usage:
#   ./deploy_absurd.sh [install|start|stop|restart|status|logs|uninstall]
#
# This script handles the complete deployment of the Absurd durable workflow
# worker, including:
# - Database schema verification
# - Queue setup
# - Systemd service installation
# - Log rotation setup
# - Health check setup

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SYSTEMD_DIR="${PROJECT_ROOT}/ops/systemd"
SERVICE_NAME="contimg-absurd-worker"
SERVICE_FILE="${SYSTEMD_DIR}/${SERVICE_NAME}.service"
ENV_FILE="${SYSTEMD_DIR}/contimg.env"
LOG_DIR="${PROJECT_ROOT}/state/logs"
PYTHON="/opt/miniforge/envs/casa6/bin/python"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python environment
    if [[ ! -x "${PYTHON}" ]]; then
        log_error "Python not found at ${PYTHON}"
        log_error "Please ensure casa6 conda environment is installed"
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f "${ENV_FILE}" ]]; then
        log_error "Environment file not found: ${ENV_FILE}"
        exit 1
    fi
    
    # Source environment
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    
    # Check Absurd is enabled
    if [[ "${ABSURD_ENABLED:-false}" != "true" ]]; then
        log_error "ABSURD_ENABLED is not true in ${ENV_FILE}"
        exit 1
    fi
    
    # Check database URL
    if [[ -z "${ABSURD_DATABASE_URL:-}" ]]; then
        log_error "ABSURD_DATABASE_URL is not set in ${ENV_FILE}"
        exit 1
    fi
    
    log_info "Prerequisites OK"
}

verify_database() {
    log_info "Verifying Absurd database..."
    
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    
    # Try to connect and verify schema
    if ! ${PYTHON} -c "
import asyncio
import sys
sys.path.insert(0, '${PROJECT_ROOT}/backend/src')

from dsa110_contimg.absurd import AbsurdClient

async def check():
    client = AbsurdClient('${ABSURD_DATABASE_URL}')
    await client.connect()
    stats = await client.get_queue_stats('${ABSURD_QUEUE_NAME:-dsa110-pipeline}')
    print(f'Queue stats: {stats}')
    await client.close()

asyncio.run(check())
" 2>/dev/null; then
        log_error "Cannot connect to Absurd database"
        log_error "Ensure PostgreSQL is running and schema is installed"
        log_info "Run: ./scripts/absurd/setup_absurd_db.sh"
        exit 1
    fi
    
    log_info "Database connection OK"
}

create_directories() {
    log_info "Creating directories..."
    
    # Create log directory
    mkdir -p "${LOG_DIR}"
    chmod 755 "${LOG_DIR}"
    
    # Create tmp directory for CASA
    mkdir -p "${PROJECT_ROOT}/state/tmp"
    chmod 1777 "${PROJECT_ROOT}/state/tmp"
    
    log_info "Directories created"
}

install_service() {
    log_info "Installing systemd service..."
    
    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]]; then
        log_warn "Not running as root, using sudo for systemctl commands"
    fi
    
    # Copy service file
    sudo cp "${SERVICE_FILE}" /etc/systemd/system/
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable service
    sudo systemctl enable "${SERVICE_NAME}.service"
    
    log_info "Service installed and enabled"
}

install_logrotate() {
    log_info "Installing logrotate configuration..."
    
    # Create logrotate config
    cat > /tmp/absurd-worker.logrotate << 'EOF'
/data/dsa110-contimg/state/logs/absurd-worker.out
/data/dsa110-contimg/state/logs/absurd-worker.err
{
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        systemctl reload contimg-absurd-worker.service 2>/dev/null || true
    endscript
}
EOF
    
    sudo mv /tmp/absurd-worker.logrotate /etc/logrotate.d/absurd-worker
    sudo chmod 644 /etc/logrotate.d/absurd-worker
    
    log_info "Logrotate configuration installed"
}

start_service() {
    log_info "Starting ${SERVICE_NAME}..."
    sudo systemctl start "${SERVICE_NAME}.service"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
        log_info "Service started successfully"
    else
        log_error "Service failed to start"
        sudo journalctl -u "${SERVICE_NAME}.service" --no-pager -n 20
        exit 1
    fi
}

stop_service() {
    log_info "Stopping ${SERVICE_NAME}..."
    sudo systemctl stop "${SERVICE_NAME}.service" || true
    log_info "Service stopped"
}

restart_service() {
    log_info "Restarting ${SERVICE_NAME}..."
    sudo systemctl restart "${SERVICE_NAME}.service"
    
    sleep 2
    if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
        log_info "Service restarted successfully"
    else
        log_error "Service failed to restart"
        exit 1
    fi
}

show_status() {
    echo ""
    echo "=== Service Status ==="
    sudo systemctl status "${SERVICE_NAME}.service" --no-pager || true
    
    echo ""
    echo "=== Queue Statistics ==="
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    ${PYTHON} -c "
import asyncio
import sys
sys.path.insert(0, '${PROJECT_ROOT}/backend/src')

from dsa110_contimg.absurd import AbsurdClient

async def stats():
    client = AbsurdClient('${ABSURD_DATABASE_URL}')
    await client.connect()
    stats = await client.get_queue_stats('${ABSURD_QUEUE_NAME:-dsa110-pipeline}')
    print(f'  Pending:   {stats.get(\"pending\", 0)}')
    print(f'  Claimed:   {stats.get(\"claimed\", 0)}')
    print(f'  Completed: {stats.get(\"completed\", 0)}')
    print(f'  Failed:    {stats.get(\"failed\", 0)}')
    await client.close()

asyncio.run(stats())
" 2>/dev/null || echo "  (Could not fetch queue stats)"
}

show_logs() {
    log_info "Showing logs for ${SERVICE_NAME}..."
    sudo journalctl -u "${SERVICE_NAME}.service" -f
}

uninstall_service() {
    log_info "Uninstalling ${SERVICE_NAME}..."
    
    # Stop service if running
    sudo systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true
    
    # Disable service
    sudo systemctl disable "${SERVICE_NAME}.service" 2>/dev/null || true
    
    # Remove service file
    sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    
    # Remove logrotate config
    sudo rm -f /etc/logrotate.d/absurd-worker
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    log_info "Service uninstalled"
}

run_health_check() {
    log_info "Running health check..."
    
    "${SCRIPT_DIR}/health_check_absurd.sh" || exit 1
}

show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install    Install and enable the Absurd worker service"
    echo "  start      Start the service"
    echo "  stop       Stop the service"
    echo "  restart    Restart the service"
    echo "  status     Show service status and queue statistics"
    echo "  logs       Follow service logs"
    echo "  health     Run health check"
    echo "  uninstall  Remove the service"
    echo ""
    echo "Example:"
    echo "  $0 install   # First-time setup"
    echo "  $0 start     # Start worker"
    echo "  $0 status    # Check status"
}

# Main
case "${1:-help}" in
    install)
        check_prerequisites
        verify_database
        create_directories
        install_service
        install_logrotate
        log_info "Installation complete. Run '$0 start' to start the service."
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    health)
        run_health_check
        ;;
    uninstall)
        uninstall_service
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
