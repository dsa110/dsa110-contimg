#!/bin/bash
# Validates that all script references in package.json and systemd services exist
# Run as part of pre-commit or CI

set -e

# Auto-detect project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(dirname "$SCRIPT_DIR")}"

ERRORS=0

echo "Validating script references..."
echo "Project root: $PROJECT_ROOT"

# Check package.json script references
echo "--- Checking frontend/package.json ---"
cd "$PROJECT_ROOT/frontend"

# Extract bash script paths from package.json
scripts=$(grep -oE 'bash [^"]+\.sh' package.json 2>/dev/null | sed 's/bash //' || true)

for script in $scripts; do
    if [ ! -f "$script" ]; then
        echo "ERROR: package.json references missing script: $script"
        ((ERRORS++))
    else
        echo "  ✓ $script"
    fi
done

# Check systemd service references
echo "--- Checking systemd services ---"
cd "$PROJECT_ROOT/ops/systemd"

for service in *.service; do
    # Extract ExecStart and ExecStartPre paths
    scripts=$(grep -E '^Exec(Start|StartPre)=' "$service" 2>/dev/null | grep -oE '/[^ ]+\.sh' || true)
    
    for script in $scripts; do
        if [ ! -f "$script" ]; then
            echo "ERROR: $service references missing script: $script"
            ((ERRORS++))
        else
            echo "  ✓ $service → $script"
        fi
    done
done

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "All script references valid!"
    exit 0
else
    echo "Found $ERRORS missing script references!"
    exit 1
fi
