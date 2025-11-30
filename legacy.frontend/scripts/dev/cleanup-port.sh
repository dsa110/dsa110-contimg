#!/bin/bash
# Clean up processes on port 3210 (frontend dev server)

PORT=3210

echo ":left-pointing_magnifying_glass: Checking for processes on port $PORT..."

if lsof -ti:$PORT > /dev/null 2>&1; then
    PIDS=$(lsof -ti:$PORT)
    echo ":warning:  Found processes on port $PORT: $PIDS"
    echo ":hocho: Killing processes..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    echo ":white_heavy_check_mark: Port $PORT is now free"
else
    echo ":white_heavy_check_mark: Port $PORT is already free"
fi
