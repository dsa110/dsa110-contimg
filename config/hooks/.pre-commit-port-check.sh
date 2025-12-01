#!/bin/bash
# Pre-commit hook to validate port configuration
# This can be added to .git/hooks/pre-commit or used in CI

cd "$(git rev-parse --show-toplevel)"

# Run port validation
if [ -f "scripts/validate-port-config.py" ]; then
    /opt/miniforge/envs/casa6/bin/python scripts/validate-port-config.py
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo ""
        echo "Port configuration validation failed."
        echo "See docs/operations/port_organization_recommendations.md for details"
        exit $exit_code
    fi
fi

exit 0

