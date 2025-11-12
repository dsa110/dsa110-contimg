#!/bin/bash
# Comprehensive error detection wrapper

set -e
set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

error() { echo -e "${RED}[ERROR]${NC} $1" >&2; exit 1; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1" >&2; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# Pre-flight: Check Node.js version
CURRENT_NODE=$(node --version | sed 's/v//')
if [ "$(printf '%s\n' "18.0.0" "$CURRENT_NODE" | sort -V | head -n1)" != "18.0.0" ]; then
  warning "Node.js $CURRENT_NODE may be below recommended 18.0.0"
fi

# Pre-flight: Check dependencies
if [ ! -d "node_modules" ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
  error "node_modules missing - run npm install"
fi

# Pre-flight: Check permissions
[ ! -w "." ] && error "No write permission"

success "Pre-flight checks passed"

# Run command
COMMAND="$@"
OUTPUT=$(eval "$COMMAND" 2>&1)
EXIT_CODE=$?

[ $EXIT_CODE -ne 0 ] && error "Command failed: exit $EXIT_CODE"

# Check for critical patterns
CRITICAL=("failed to resolve" "cannot find module" "out of memory")
for pattern in "${CRITICAL[@]}"; do
  echo "$OUTPUT" | grep -qi "$pattern" && error "Critical: $pattern"
done

success "Command completed"
