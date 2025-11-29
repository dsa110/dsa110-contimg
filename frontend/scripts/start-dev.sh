#!/bin/bash
# Start Vite dev server for DSA-110 Frontend
# Used by systemd vite-dev.service
#
# Port 3000 is claimed by ExecStartPre in the systemd service.
# This script just runs vite with the correct environment.

set -e

cd /data/dsa110-contimg/frontend

# Ensure we use the correct Node.js from casa6 environment
export PATH="/opt/miniforge/envs/casa6/bin:$PATH"

# Run vite using npm (respects vite.config.ts settings)
exec npm run dev
