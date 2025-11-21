#!/bin/bash
set -e

echo "🔄 Restarting DSA-110 Backend API..."
echo ""

# Find and kill the current backend process
BACKEND_PID=$(ps aux | grep "uvicorn.*dsa110" | grep -v grep | awk '{print $2}' | head -1)

if [ -n "$BACKEND_PID" ]; then
    echo "Stopping current backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID
    sleep 2
    
    # Force kill if still running
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "Force stopping..."
        kill -9 $BACKEND_PID
    fi
    echo "✓ Backend stopped"
else
    echo "No backend process found"
fi

echo ""
echo "Starting backend..."
cd /data/dsa110-contimg

# Activate casa6 environment and start backend
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Start in background
nohup uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

echo "✓ Backend started (PID: $BACKEND_PID)"
echo ""
echo "Waiting for backend to be ready..."
sleep 3

# Test if backend is responding
if curl -s -f http://localhost:8000/api/status > /dev/null 2>&1; then
    echo "✓ Backend is responding!"
    echo ""
    echo "Testing disk metrics..."
    curl -s "http://localhost:8000/api/metrics/system" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'✓ {len(data.get(\"disks\", []))} disks reported:')
for disk in data.get('disks', []):
    print(f'  {disk[\"mount_point\"]:20} {disk[\"percent\"]:5.1f}%  ({disk[\"total\"]/1024**3:8.1f} GB total)')
"
else
    echo "⚠ Backend not responding yet. Check logs:"
    echo "  tail -f /tmp/backend.log"
fi
