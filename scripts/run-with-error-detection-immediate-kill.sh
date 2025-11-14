#!/bin/bash
# Error Detection Wrapper with Immediate Kill
# Kills command immediately when error is detected (using trap and signal handling)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error() {
  echo -e "${RED}[ERROR-DETECTION]${NC} $1" >&2
}

info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

if [ $# -eq 0 ]; then
  error "No command provided"
  exit 1
fi

# Create log file
LOG_DIR="${LOG_DIR:-/tmp}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/error-detection-${TIMESTAMP}.log"

info "Running command: $*"
info "Log file: $LOG_FILE"

# Error patterns (simplified for shell)
ERROR_PATTERNS=(
  "Error:"
  "ERROR:"
  "Traceback"
  "FAILED"
  "failed"
  "Exception:"
  "FATAL"
  "CRITICAL"
)

# Process ID tracking
CMD_PID=""
ERROR_DETECTED=false

# Function to kill command immediately
kill_command() {
  if [ -n "$CMD_PID" ] && kill -0 "$CMD_PID" 2>/dev/null; then
    error "Killing command immediately (PID: $CMD_PID)..."
    # Try graceful termination first
    kill -TERM "$CMD_PID" 2>/dev/null || true
    sleep 0.1
    # If still alive, force kill
    if kill -0 "$CMD_PID" 2>/dev/null; then
      kill -KILL "$CMD_PID" 2>/dev/null || true
      # Also kill process group
      kill -KILL -"$CMD_PID" 2>/dev/null || true
    fi
  fi
}

# Trap to ensure cleanup
trap 'kill_command; exit 1' ERR INT TERM

# Function to check for errors in a line
check_line_for_errors() {
  local line="$1"
  for pattern in "${ERROR_PATTERNS[@]}"; do
    if echo "$line" | grep -qiE "$pattern"; then
      # Check for false positives
      if ! echo "$line" | grep -qiE "#.*Error|Error: 0|no errors|Error handling"; then
        return 0  # Error found
      fi
    fi
  done
  return 1  # No error
}

# Run command in background, capturing output
{
  # Run command and capture PID
  "$@" &
  CMD_PID=$!
  
  # Monitor output line by line
  while IFS= read -r line; do
    # Output to terminal and log
    echo "$line" | tee -a "$LOG_FILE"
    
    # Check for errors in real-time
    if check_line_for_errors "$line"; then
      error "Error detected in output: $line"
      ERROR_DETECTED=true
      kill_command
      break
    fi
  done < <(stdbuf -oL -eL "$@" 2>&1)
  
  # Wait for command to finish
  wait $CMD_PID 2>/dev/null || true
  EXIT_CODE=$?
} || {
  EXIT_CODE=$?
}

# Final check
if [ "$ERROR_DETECTED" = true ] || [ $EXIT_CODE -ne 0 ]; then
  error "Command execution failed"
  error "Exit code: $EXIT_CODE"
  exit 1
else
  success "Command completed successfully"
  exit 0
fi

