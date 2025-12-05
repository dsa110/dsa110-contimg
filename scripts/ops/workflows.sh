#!/bin/bash
# Common Workflow Shortcuts
# Source this file or add to your .bashrc for quick access to common workflows

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

# Quick setup for new developers
alias dev-setup="$SCRIPT_DIR/dev/quick-start.sh"

# Test shortcuts
alias test-all="$SCRIPT_DIR/utils/run-tests.sh"
alias test-docker="$SCRIPT_DIR/utils/run-tests-docker.sh"
alias test-playwright="$SCRIPT_DIR/utils/run-playwright-python-tests.sh"

# Quality checks
alias quality-check="$SCRIPT_DIR/quality/check-code-quality.sh"
alias quality-fix="$SCRIPT_DIR/quality/auto-fix-common-issues.sh"
alias error-check="$SCRIPT_DIR/quality/auto-error-detection.sh"

# Service management
alias services="$SCRIPT_DIR/utils/manage-services.sh"
alias services-start="$SCRIPT_DIR/utils/manage-services.sh start"
alias services-stop="$SCRIPT_DIR/utils/manage-services.sh stop"
alias services-status="$SCRIPT_DIR/utils/manage-services.sh status"

# CASA operations
alias casa-cleanup="$SCRIPT_DIR/casa/cleanup_casa_logs.sh"
alias casa-status="sudo systemctl status casa-log-daemon"

# Dashboard
alias dashboard-build="$SCRIPT_DIR/dashboard/build-dashboard-production.sh"
alias dashboard-serve="$SCRIPT_DIR/dashboard/serve-dashboard-production.sh"

# Calibration / Validation
alias ms-validate="python -m dsa110_contimg.validation.ms_validator"

# Monitoring
alias monitor-cal="$SCRIPT_DIR/monitoring/monitor_calibration.py"
alias monitor-pub="$SCRIPT_DIR/monitoring/monitor_publish_status.py"

# Show available shortcuts
workflows-help() {
    echo -e "${CYAN}Available Workflow Shortcuts:${NC}"
    echo ""
    echo -e "${GREEN}Development:${NC}"
    echo "  dev-setup              - Quick start for new developers"
    echo ""
    echo -e "${GREEN}Testing:${NC}"
    echo "  test-all               - Run all tests"
    echo "  test-docker            - Run tests in Docker"
    echo "  test-playwright        - Run Playwright tests"
    echo ""
    echo -e "${GREEN}Quality:${NC}"
    echo "  quality-check          - Run code quality checks"
    echo "  quality-fix            - Auto-fix common issues"
    echo "  error-check            - Run error detection"
    echo ""
    echo -e "${GREEN}Services:${NC}"
    echo "  services [cmd]         - Manage services (start/stop/status)"
    echo "  services-start [svc]  - Start service(s)"
    echo "  services-stop [svc]   - Stop service(s)"
    echo "  services-status       - Show service status"
    echo ""
    echo -e "${GREEN}CASA:${NC}"
    echo "  casa-cleanup           - Cleanup CASA logs"
    echo "  casa-status            - Check CASA daemon status"
    echo ""
    echo -e "${GREEN}Dashboard:${NC}"
    echo "  dashboard-build        - Build dashboard"
    echo "  dashboard-serve        - Serve dashboard"
    echo ""
    echo -e "${GREEN}Calibration:${NC}"
    echo "  cal-check              - Check MS phasing"
    echo ""
    echo -e "${GREEN}Monitoring:${NC}"
    echo "  monitor-cal            - Monitor calibration"
    echo "  monitor-pub            - Monitor publish status"
    echo ""
    echo -e "${CYAN}To use these shortcuts, add to your ~/.bashrc:${NC}"
    echo "  source $SCRIPT_DIR/workflows.sh"
}

# Export functions
export -f workflows-help

