#!/bin/bash
# Setup script for CASA Log Daemon monitoring and protection
# This installs the watchdog timer and ensures all monitoring is in place

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/data/dsa110-contimg"

echo "Setting up CASA Log Daemon monitoring and protection..."

# Ensure health check script is executable
chmod +x "$SCRIPT_DIR/casa_log_daemon_health_check.sh"

# Copy service files
echo "Installing systemd service files..."
sudo cp "$SCRIPT_DIR/casa-log-daemon-inotify.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/casa-log-daemon-watchdog.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/casa-log-daemon-watchdog.timer" /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable and start watchdog timer
echo "Enabling watchdog timer..."
sudo systemctl enable casa-log-daemon-watchdog.timer
sudo systemctl start casa-log-daemon-watchdog.timer

# Ensure main service is enabled
echo "Ensuring main service is enabled..."
sudo systemctl enable casa-log-daemon-inotify.service

# Restart main service to apply new configuration
echo "Restarting main service..."
sudo systemctl restart casa-log-daemon-inotify.service

# Wait a moment for service to start
sleep 3

# Run initial health check
echo ""
echo "Running initial health check..."
"$SCRIPT_DIR/casa_log_daemon_health_check.sh" && echo "✓ Health check passed" || echo "⚠ Health check found issues (check logs)"

# Show status
echo ""
echo "=== Service Status ==="
systemctl status casa-log-daemon-inotify.service --no-pager | head -10

echo ""
echo "=== Watchdog Timer Status ==="
systemctl status casa-log-daemon-watchdog.timer --no-pager | head -10

echo ""
echo "=== Next Timer Run ==="
systemctl list-timers casa-log-daemon-watchdog.timer --no-pager

echo ""
echo "✓ Setup complete!"
echo ""
echo "Monitoring is now active:"
echo "  - Health check runs every 5 minutes"
echo "  - Service auto-restarts on failure"
echo "  - Status file: $PROJECT_ROOT/state/logs/.casa_log_daemon_status.json"
echo ""
echo "To check health manually:"
echo "  $SCRIPT_DIR/casa_log_daemon_health_check.sh"
echo ""
echo "To view status:"
echo "  cat $PROJECT_ROOT/state/logs/.casa_log_daemon_status.json | jq ."

