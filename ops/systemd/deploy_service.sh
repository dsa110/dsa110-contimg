#!/bin/bash
# Deploy systemd service file from ops/systemd to /etc/systemd/system/
# Usage: ./deploy_service.sh

set -e

SERVICE_NAME="contimg-pointing-monitor.service"
SOURCE_FILE="/data/dsa110-contimg/ops/systemd/${SERVICE_NAME}"
TARGET_FILE="/etc/systemd/system/${SERVICE_NAME}"

echo "Deploying ${SERVICE_NAME}..."

# Check if source file exists
if [ ! -f "${SOURCE_FILE}" ]; then
    echo "ERROR: Source file not found: ${SOURCE_FILE}"
    exit 1
fi

# Copy to systemd directory
sudo cp "${SOURCE_FILE}" "${TARGET_FILE}"

# Reload systemd
sudo systemctl daemon-reload

echo "✓ Service file deployed successfully"
echo "✓ Systemd configuration reloaded"
echo ""
echo "To restart the service, run:"
echo "  sudo systemctl restart ${SERVICE_NAME}"

