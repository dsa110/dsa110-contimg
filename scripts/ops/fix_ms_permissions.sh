#!/bin/bash
# fix_ms_permissions.sh - Fix permissions for Measurement Set files
# This ensures the current user can read/write MS files that may have been created by root

set -e

MS_PATH="$1"
TARGET_USER="${2:-$USER}"

if [ -z "$MS_PATH" ]; then
    echo "Usage: $0 <ms_path> [target_user]"
    echo "Example: $0 /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms ubuntu"
    exit 1
fi

if [ ! -d "$MS_PATH" ]; then
    echo "ERROR: MS does not exist: $MS_PATH"
    exit 1
fi

echo "Fixing permissions for: $MS_PATH"
echo "Target user: $TARGET_USER"

# Fix ownership recursively
echo "  - Changing ownership to $TARGET_USER..."
sudo chown -R "$TARGET_USER:$TARGET_USER" "$MS_PATH"

# Fix permissions recursively (read/write for owner, read for group/others)
echo "  - Setting permissions (u+rw,g+r,o+r)..."
sudo chmod -R u+rw,g+r,o+r "$MS_PATH"

# Ensure directories are executable
echo "  - Making directories executable..."
sudo find "$MS_PATH" -type d -exec chmod u+x {} \;

echo ":check: Permissions fixed successfully"
ls -lah "$MS_PATH" | head -5
