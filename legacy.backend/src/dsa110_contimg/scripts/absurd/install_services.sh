#!/bin/bash
# Installation script for Absurd systemd services
# Run with: sudo ./scripts/absurd/install_services.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/data/dsa110-contimg/src/dsa110_contimg"

echo "════════════════════════════════════════════════════════"
echo "  DSA-110 Absurd Services Installation"
echo "════════════════════════════════════════════════════════"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo ":cross_mark: This script must be run as root (use sudo)"
   exit 1
fi

echo ":check_mark: Running as root"
echo ""

# 1. Install worker service
echo "Installing worker service template..."
cp "$SCRIPT_DIR/dsa110-absurd-worker@.service" /etc/systemd/system/
chmod 644 /etc/systemd/system/dsa110-absurd-worker@.service
echo ":check_mark: Worker service installed: /etc/systemd/system/dsa110-absurd-worker@.service"

# 2. Install daemon service
echo "Installing mosaic daemon service..."
cp "$SCRIPT_DIR/dsa110-mosaic-daemon.service" /etc/systemd/system/
chmod 644 /etc/systemd/system/dsa110-mosaic-daemon.service
echo ":check_mark: Daemon service installed: /etc/systemd/system/dsa110-mosaic-daemon.service"

# 3. Reload systemd
echo ""
echo "Reloading systemd daemon..."
systemctl daemon-reload
echo ":check_mark: Systemd reloaded"

# 4. Show status
echo ""
echo "════════════════════════════════════════════════════════"
echo "  Installation Complete!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Services installed:"
echo "  • dsa110-absurd-worker@.service (template)"
echo "  • dsa110-mosaic-daemon.service"
echo ""
echo "To start services:"
echo "  sudo systemctl start dsa110-mosaic-daemon"
echo "  sudo systemctl start dsa110-absurd-worker@{1..4}"
echo ""
echo "To enable auto-start on boot:"
echo "  sudo systemctl enable dsa110-mosaic-daemon"
echo "  sudo systemctl enable dsa110-absurd-worker@{1..4}"
echo ""
echo "To check status:"
echo "  systemctl status dsa110-mosaic-daemon"
echo "  systemctl list-units 'dsa110-absurd-worker@*'"
echo ""
echo "════════════════════════════════════════════════════════"
