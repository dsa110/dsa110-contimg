#!/bin/bash
# Enable CARTA in Production Dashboard
# This script configures CARTA environment variables and rebuilds the dashboard

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
ENV_PROD="${FRONTEND_DIR}/.env.production"

# CARTA configuration
CARTA_BACKEND_URL="${VITE_CARTA_BACKEND_URL:-ws://localhost:9002}"
CARTA_FRONTEND_URL="${VITE_CARTA_FRONTEND_URL:-http://localhost:9003}"

echo "=== Enabling CARTA in Production Dashboard ==="
echo ""

# Step 1: Update .env.production
echo "Step 1: Configuring CARTA environment variables..."

# Check if CARTA config already exists
if grep -q "VITE_CARTA_BACKEND_URL" "${ENV_PROD}" 2>/dev/null; then
    echo "  CARTA configuration already exists in .env.production"
    echo "  Updating existing values..."
    
    # Update existing values
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        sed -i '' "s|^VITE_CARTA_BACKEND_URL=.*|VITE_CARTA_BACKEND_URL=${CARTA_BACKEND_URL}|" "${ENV_PROD}"
        sed -i '' "s|^VITE_CARTA_FRONTEND_URL=.*|VITE_CARTA_FRONTEND_URL=${CARTA_FRONTEND_URL}|" "${ENV_PROD}"
    else
        # Linux
        sed -i "s|^VITE_CARTA_BACKEND_URL=.*|VITE_CARTA_BACKEND_URL=${CARTA_BACKEND_URL}|" "${ENV_PROD}"
        sed -i "s|^VITE_CARTA_FRONTEND_URL=.*|VITE_CARTA_FRONTEND_URL=${CARTA_FRONTEND_URL}|" "${ENV_PROD}"
    fi
else
    echo "  Adding CARTA configuration to .env.production..."
    cat >> "${ENV_PROD}" << EOF

# CARTA Integration Configuration
# CARTA Backend WebSocket URL
VITE_CARTA_BACKEND_URL=${CARTA_BACKEND_URL}

# CARTA Frontend URL (for iframe integration)
VITE_CARTA_FRONTEND_URL=${CARTA_FRONTEND_URL}
EOF
fi

echo "  ✓ CARTA environment variables configured:"
echo "    VITE_CARTA_BACKEND_URL=${CARTA_BACKEND_URL}"
echo "    VITE_CARTA_FRONTEND_URL=${CARTA_FRONTEND_URL}"
echo ""

# Step 2: Rebuild dashboard
echo "Step 2: Rebuilding production dashboard..."
echo "  (This may take a few minutes...)"
echo ""

"${SCRIPT_DIR}/build-dashboard-production.sh"

echo ""
echo "Step 3: Dashboard rebuild complete!"
echo ""
echo "Next steps:"
echo "  1. Restart the production dashboard service:"
echo "     - systemd: sudo systemctl restart contimg-dashboard"
echo "     - Docker: docker compose restart dashboard"
echo "     - Manual: ./scripts/serve-dashboard-production.sh"
echo ""
echo "  2. Verify CARTA is enabled:"
echo "     - Navigate to http://localhost:3210/carta"
echo "     - Check that CARTA URLs are configured (not default localhost)"
echo ""
echo "  3. (Optional) Start CARTA backend:"
echo "     docker run -d --name carta-backend -p 9002:3002 -p 9003:3000 cartavis/carta-backend:latest"
echo ""
echo "✓ CARTA configuration complete!"

