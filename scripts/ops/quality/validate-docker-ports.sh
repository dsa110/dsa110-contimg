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
    echo "✓ All Docker Compose files use environment variables for ports"
    exit 0
else
    echo ""
    echo "✗ Found $ERRORS hardcoded port(s)"
    echo "  Use environment variables instead (e.g., \${CONTIMG_API_PORT:-8000})"
    exit 1
fi
