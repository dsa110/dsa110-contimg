#!/bin/bash
# Safe command runner with comprehensive error detection
# Usage: ./scripts/run-safe.sh "npm run build"

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"

# Source error detection library
if [ -f "$LIB_DIR/error-detection.sh" ]; then
  source "$LIB_DIR/error-detection.sh"
else
  echo "Error: error-detection.sh not found at $LIB_DIR/error-detection.sh"
  exit 1
fi

# Check if command provided
if [ $# -eq 0 ]; then
  error "Usage: $0 <command>"
  echo "Example: $0 'npm run build'"
  exit 1
fi

COMMAND="$@"

info "Running command with comprehensive error detection: $COMMAND"
echo ""

# Run with comprehensive detection
if run_with_comprehensive_detection "$COMMAND"; then
  success "Command completed successfully with all checks passed"
  exit 0
else
  error "Command failed or validation failed"
  exit 1
fi

