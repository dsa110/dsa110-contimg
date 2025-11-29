#!/bin/bash
# Start Vite dev server for DSA-110 Frontend
# Used by systemd vite-dev.service

set -e

cd /data/dsa110-contimg/frontend

# Kill any existing vite processes on port 3000
lsof -ti:3000 | xargs -r kill -9 2>/dev/null || true
sleep 1

# Run vite using npm (respects vite.config.ts settings)
exec npm run dev
