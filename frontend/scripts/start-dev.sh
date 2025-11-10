#!/bin/bash
# Start dev server in a persistent way
# Usage: ./scripts/start-dev.sh [screen|tmux|nohup|pm2]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$FRONTEND_DIR"

METHOD="${1:-screen}"

case "$METHOD" in
  screen)
    echo "Starting dev server in screen session 'frontend-dev'..."
    screen -dmS frontend-dev bash -c "cd '$FRONTEND_DIR' && npm run dev"
    echo "Dev server started in screen session 'frontend-dev'"
    echo "To attach: screen -r frontend-dev"
    echo "To detach: Press Ctrl+A then D"
    echo "To kill: screen -X -S frontend-dev quit"
    ;;
  tmux)
    echo "Starting dev server in tmux session 'frontend-dev'..."
    tmux new-session -d -s frontend-dev "cd '$FRONTEND_DIR' && npm run dev"
    echo "Dev server started in tmux session 'frontend-dev'"
    echo "To attach: tmux attach -t frontend-dev"
    echo "To detach: Press Ctrl+B then D"
    echo "To kill: tmux kill-session -t frontend-dev"
    ;;
  nohup)
    echo "Starting dev server with nohup..."
    nohup npm run dev > dev-server.log 2>&1 &
    PID=$!
    echo "Dev server started with PID: $PID"
    echo "Logs: tail -f dev-server.log"
    echo "To stop: kill $PID"
    ;;
  pm2)
    if ! command -v pm2 &> /dev/null; then
      echo "PM2 not installed. Installing..."
      npm install -g pm2
    fi
    echo "Starting dev server with PM2..."
    # Use --cwd to ensure PM2 runs from the correct directory
    pm2 start npm --name "frontend-dev" --cwd "$FRONTEND_DIR" -- run dev
    echo "Dev server started with PM2"
    echo "To view logs: pm2 logs frontend-dev"
    echo "To stop: pm2 stop frontend-dev"
    echo "To restart: pm2 restart frontend-dev"
    echo "To delete: pm2 delete frontend-dev"
    echo ""
    echo "Viewing logs (Ctrl+C to exit)..."
    sleep 2
    pm2 logs frontend-dev --lines 10
    ;;
  *)
    echo "Unknown method: $METHOD"
    echo "Usage: $0 [screen|tmux|nohup|pm2]"
    exit 1
    ;;
esac

