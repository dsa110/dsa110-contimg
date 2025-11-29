#!/bin/bash
# Clean up processes on port 3210 (frontend dev server)

PORT=3210

echo "🔍 Checking for processes on port $PORT..."

if lsof -ti:$PORT > /dev/null 2>&1; then
    PIDS=$(lsof -ti:$PORT)
    echo "⚠️  Found processes on port $PORT: $PIDS"
    echo "🔪 Killing processes..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    echo "✅ Port $PORT is now free"
else
    echo "✅ Port $PORT is already free"
fi
