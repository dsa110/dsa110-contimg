#!/bin/bash
# Check dev server status and logs

echo "=== PM2 Status ==="
pm2 status

echo ""
echo "=== Recent Logs (last 20 lines) ==="
pm2 logs frontend-dev --lines 20 --nostream

echo ""
echo "=== Port Check ==="
lsof -i :5174 2>/dev/null || echo "Port 5174 not in use"

