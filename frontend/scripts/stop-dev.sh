#!/bin/bash
# Stop dev server
# Usage: ./scripts/stop-dev.sh [screen|tmux|nohup|pm2]

set -e

METHOD="${1:-screen}"

case "$METHOD" in
  screen)
    echo "Stopping screen session 'frontend-dev'..."
    screen -X -S frontend-dev quit 2>/dev/null || echo "Screen session not found"
    ;;
  tmux)
    echo "Stopping tmux session 'frontend-dev'..."
    tmux kill-session -t frontend-dev 2>/dev/null || echo "Tmux session not found"
    ;;
  nohup)
    echo "Stopping nohup dev server..."
    pkill -f "vite" || echo "No vite process found"
    ;;
  pm2)
    echo "Stopping PM2 process 'frontend-dev'..."
    pm2 stop frontend-dev 2>/dev/null || echo "PM2 process not found"
    pm2 delete frontend-dev 2>/dev/null || echo "PM2 process not found"
    ;;
  *)
    echo "Unknown method: $METHOD"
    echo "Usage: $0 [screen|tmux|nohup|pm2]"
    exit 1
    ;;
esac

echo "Dev server stopped."

