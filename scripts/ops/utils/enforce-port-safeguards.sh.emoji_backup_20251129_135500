#!/bin/bash
# Script to enforce port organization safeguards
# Adds missing safeguards to the port system

set -e

PROJECT_DIR="/data/dsa110-contimg"
cd "$PROJECT_DIR"

echo "=== Enforcing Port Organization Safeguards ==="
echo ""

# 1. Add pre-commit hook
echo "1. Adding pre-commit hook..."
if [ -f ".pre-commit-config.yaml" ]; then
    if ! grep -q "validate-port-config" .pre-commit-config.yaml; then
        # Add port validation hook
        cat >> .pre-commit-config.yaml << 'EOF'

  # Port configuration validation
  - id: validate-port-config
    name: Validate Port Configuration
    entry: scripts/validate-port-config.py
    language: system
    pass_filenames: false
    always_run: true
    stages: [pre-commit]
EOF
        echo "  :check: Added pre-commit hook"
    else
        echo "  :check: Pre-commit hook already exists"
    fi
else
    echo "  :warning: .pre-commit-config.yaml not found, skipping"
fi

# 2. Create CI validation workflow
echo ""
echo "2. Creating CI validation workflow..."
mkdir -p .github/workflows
if [ ! -f ".github/workflows/validate-ports.yml" ]; then
    cat > .github/workflows/validate-ports.yml << 'EOF'
name: Validate Port Configuration

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  validate-ports:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install pyyaml || true
      
      - name: Validate Port Configuration
        run: |
          python3 scripts/validate-port-config.py
      
      - name: Check Ports
        run: |
          chmod +x scripts/check-ports.sh
          ./scripts/check-ports.sh || true
EOF
    echo "  :check: Created .github/workflows/validate-ports.yml"
else
    echo "  :check: CI workflow already exists"
fi

# 3. Create Docker Compose validation script
echo ""
echo "3. Creating Docker Compose validation script..."
cat > scripts/validate-docker-ports.sh << 'EOF'
#!/bin/bash
# Validate docker-compose files use environment variables for ports

set -e

PROJECT_DIR="/data/dsa110-contimg"
cd "$PROJECT_DIR"

ERRORS=0

check_file() {
    local file=$1
    if [ ! -f "$file" ]; then
        return
    fi
    
    # Check for hardcoded ports (not using ${VAR} syntax)
    # Allow comments and allowed hardcoded ports
    while IFS= read -r line; do
        # Skip comments
        if [[ "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        # Check for port patterns that aren't using env vars
        if [[ "$line" =~ :[0-9]{4,5}: ]] && [[ ! "$line" =~ \$\{ ]]; then
            # Check if it's an allowed hardcoded port
            port=$(echo "$line" | grep -oE ":[0-9]{4,5}:" | grep -oE "[0-9]+")
            if [[ "$port" != "9009" ]] && [[ "$port" != "6379" ]] && [[ "$port" != "9222" ]]; then
                echo "ERROR: Hardcoded port $port in $file:"
                echo "  $line"
                ERRORS=$((ERRORS + 1))
            fi
        fi
    done < "$file"
}

echo "Validating Docker Compose files for port usage..."
echo ""

check_file "docker-compose.yml"
check_file "docker/docker-compose.test.yml"
check_file "frontend/docker-compose.test.yml"

if [ $ERRORS -eq 0 ]; then
    echo ":check: All Docker Compose files use environment variables for ports"
    exit 0
else
    echo ""
    echo ":cross: Found $ERRORS hardcoded port(s)"
    echo "  Use environment variables instead (e.g., \${CONTIMG_API_PORT:-8000})"
    exit 1
fi
EOF

chmod +x scripts/validate-docker-ports.sh
echo "  :check: Created scripts/validate-docker-ports.sh"

# 4. Create port health check endpoint helper
echo ""
echo "4. Creating port health check helper..."
cat > scripts/add-port-health-check.py << 'EOF'
#!/usr/bin/env python3
"""Helper to add port health check to API routes."""

import sys
from pathlib import Path

api_routes = Path("src/dsa110_contimg/api/routes.py")

if not api_routes.exists():
    print("API routes file not found")
    sys.exit(1)

# Check if health check already exists
content = api_routes.read_text()
if "/health/ports" in content:
    print("Port health check already exists")
    sys.exit(0)

# Add health check endpoint (would need manual integration)
print("Port health check helper created")
print("Manually add /health/ports endpoint to routes.py")
EOF

chmod +x scripts/add-port-health-check.py
echo "  :check: Created scripts/add-port-health-check.py"

# 5. Create startup validation helper
echo ""
echo "5. Creating startup validation helper..."
cat > scripts/validate-startup-ports.sh << 'EOF'
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
    echo ":check: Port validation passed"
    exit 0
else
    echo ":cross: Port validation failed"
    exit 1
fi
EOF

chmod +x scripts/validate-startup-ports.sh
echo "  :check: Created scripts/validate-startup-ports.sh"

echo ""
echo "=== Safeguards Enforcement Complete ==="
echo ""
echo "Next steps:"
echo "1. Review and test pre-commit hook: pre-commit install"
echo "2. Test CI workflow: git push (will trigger validation)"
echo "3. Run Docker validation: ./scripts/validate-docker-ports.sh"
echo "4. Add startup validation to service scripts"
echo "5. Add port health check endpoint to API"

