#!/bin/bash
#
# Start the DSA-110 API backend with port reservation.
# Similar to how the frontend uses predev hooks.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PORT="${API_PORT:-8000}"

echo "[run-api] Ensuring port $PORT is available..."
python3 "$SCRIPT_DIR/ensure_port.py" --port "$PORT"

echo "[run-api] Starting uvicorn on port $PORT..."
cd "$BACKEND_DIR"
exec python -m uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port "$PORT" --reload
