#!/bin/bash
# Serve the frontend dashboard in production mode
# Called by dsa110-contimg-dashboard.service ExecStart

set -e

cd /data/dsa110-contimg/frontend

# Ensure node is available
export PATH="/opt/miniforge/envs/casa6/bin:$PATH"

# Serve the built static files
# Uses vite preview which serves the dist folder
exec npm run preview
