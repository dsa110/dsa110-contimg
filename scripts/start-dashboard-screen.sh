#!/bin/bash
# Start the DSA-110 dashboard API in a screen session
# This allows the dashboard to persist after SSH disconnection

set -e

# Configuration
SESSION_NAME="dsa110-dashboard"
API_PORT="${CONTIMG_API_PORT:-8000}"
PROJECT_ROOT="/data/dsa110-contimg"
LOG_DIR="${PROJECT_ROOT}/state/logs"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Check if session already exists
if screen -list | grep -q "${SESSION_NAME}"; then
    echo "Session '${SESSION_NAME}' already exists!"
    echo "To attach: screen -r ${SESSION_NAME}"
    echo "To kill: screen -S ${SESSION_NAME} -X quit"
    exit 1
fi

# Source environment if available
if [ -f "${PROJECT_ROOT}/ops/systemd/contimg.env" ]; then
    set -a
    source "${PROJECT_ROOT}/ops/systemd/contimg.env"
    set +a
fi

1q1`    # Determine Python path
# Try casa6 first, then system python
if [ -x "/opt/miniforge/envs/casa6/bin/python" ]; then
    PYTHON_CMD="/opt/miniforge/envs/casa6/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    echo "ERROR: Python not found. Please ensure casa6 environment is available."
    exit 1
fi

# Verify uvicorn is available
if ! ${PYTHON_CMD} -m uvicorn --version >/dev/null 2>&1; then
    echo "ERROR: uvicorn module not found. Please install uvicorn in the Python environment."
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"

# Create screen session and run uvicorn
echo "Starting dashboard in screen session '${SESSION_NAME}'..."
screen -dmS "${SESSION_NAME}" bash -c \
    "cd ${PROJECT_ROOT} && export PYTHONPATH=${PROJECT_ROOT}/src:\${PYTHONPATH:-} && ${PYTHON_CMD} -m uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port ${API_PORT} 2>&1 | tee ${LOG_DIR}/dashboard-screen.log"

# Wait a moment for startup
sleep 2

# Check if session is still running
if screen -list | grep -q "${SESSION_NAME}"; then
    echo "Dashboard started successfully!"
    echo ""
    echo "To attach to the session:"
    echo "  screen -r ${SESSION_NAME}"
    echo ""
    echo "To detach (keep running): Press Ctrl+A, then D"
    echo ""
    echo "To stop the dashboard:"
    echo "  screen -S ${SESSION_NAME} -X quit"
    echo ""
    echo "To view logs:"
    echo "  tail -f ${LOG_DIR}/dashboard-screen.log"
    echo ""
    echo "Dashboard should be accessible at: http://$(hostname):${API_PORT}"
else
    echo "ERROR: Session failed to start. Checking what happened..."
    if [ -f "${LOG_DIR}/dashboard-screen.log" ]; then
        echo "Screen log:"
        tail -20 "${LOG_DIR}/dashboard-screen.log"
    fi
    echo ""
    echo "Try running manually to see the error:"
    echo "  cd ${PROJECT_ROOT}"
    echo "  export PYTHONPATH=${PROJECT_ROOT}/src"
    echo "  ${PYTHON_CMD} -m uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port ${API_PORT}"
    exit 1
fi

