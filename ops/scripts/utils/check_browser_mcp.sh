#!/bin/bash
# Browser MCP Status Check Script

echo "=== Browser MCP Status ==="
echo ""

echo "1. MCP Server:"
if ps aux | grep "dist/index.js.*--http" | grep -v grep > /dev/null; then
    ps aux | grep "dist/index.js.*--http" | grep -v grep | head -1
else
    echo "  ✗ Not running"
fi
echo ""

echo "2. WebSocket Server (port 3000):"
if lsof -i :3000 2>/dev/null | head -1 > /dev/null; then
    lsof -i :3000 2>/dev/null | head -2
else
    echo "  ✗ Not listening"
fi
echo ""

echo "3. HTTP Server (port 3111):"
if lsof -i :3111 2>/dev/null | head -1 > /dev/null; then
    lsof -i :3111 2>/dev/null | head -2
else
    echo "  ✗ Not listening"
fi
echo ""

echo "4. Chrome Remote Desktop:"
if ps aux | grep "chrome-remote-desktop-host" | grep -v grep > /dev/null; then
    ps aux | grep "chrome-remote-desktop-host" | grep -v grep | head -1 | awk '{print "  ✓ Running (PID: " $2 ")"}'
else
    echo "  ✗ Not running"
fi
echo ""

echo "5. Chrome Browser:"
if ps aux | grep "/opt/google/chrome/chrome" | grep -v grep | head -1 > /dev/null; then
    ps aux | grep "/opt/google/chrome/chrome" | grep -v grep | head -1 | awk '{print "  ✓ Running (PID: " $2 ")"}'
else
    echo "  ✗ Not running"
fi
echo ""

echo "6. Display:"
echo "  DISPLAY=${DISPLAY:-not set}"
echo ""

echo "7. Active WebSocket Connections:"
WS_CONN=$(netstat -an 2>/dev/null | grep ":3000.*ESTABLISHED" | wc -l)
if [ "$WS_CONN" -eq 0 ]; then
    WS_CONN=$(ss -an 2>/dev/null | grep ":3000.*ESTAB" | wc -l)
fi
if [ "$WS_CONN" -gt 0 ]; then
    echo "  ✓ $WS_CONN active connection(s)"
else
    echo "  ✗ No active connections (extension may not be connected)"
fi
echo ""

echo "8. HTTP Server Status:"
HTTP_STATUS=$(curl -s http://localhost:3111/mcp 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$HTTP_STATUS" | jq -r '"  Status: " + .status + "\n  Active Sessions: " + (.activeSessions | tostring)' 2>/dev/null || echo "  $HTTP_STATUS"
else
    echo "  ✗ Cannot reach HTTP server"
fi
echo ""

echo "=== Summary ==="
if [ "$WS_CONN" -gt 0 ] && echo "$HTTP_STATUS" | grep -q "running"; then
    echo "✓ System appears operational"
else
    echo "✗ Issues detected - check above"
fi
