#!/bin/bash
# Validate ports before starting services

set -e

PROJECT_DIR="/data/dsa110-contimg"
cd "$PROJECT_DIR"

PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"
export PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH"

echo "Validating ports before startup..."

if PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH" "$PYTHON_BIN" -c "
from dsa110_contimg.config.ports import PortManager
import sys

pm = PortManager()
results = pm.validate_all()

errors = []
for service, (is_valid, error) in results.items():
    if not is_valid:
        errors.append(f'{service}: {error}')

if errors:
    print('Port validation failed:')
    for error in errors:
        print(f'  - {error}')
    sys.exit(1)
else:
    print('All ports validated successfully')
    sys.exit(0)
" 2>/dev/null; then
    echo "✓ Port validation passed"
    exit 0
else
    echo "✗ Port validation failed"
    exit 1
fi
