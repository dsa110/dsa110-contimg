# Browser MCP Diagnostics Guide

> **For detailed troubleshooting steps, see:**
> [Browser MCP Connection Troubleshooting](./browser_mcp_connection_troubleshooting.md)

## Quick Status Check

Run this command to check all components:

```bash
echo "=== Browser MCP Status ===" && \
echo "1. MCP Server:" && \
ps aux | grep "dist/index.js.*--http" | grep -v grep && \
echo "" && \
echo "2. WebSocket Server (port 9009):" && \
lsof -i :9009 2>/dev/null | head -2 || echo "  Not listening" && \
echo "" && \
echo "3. HTTP Server (port 3111):" && \
lsof -i :3111 2>/dev/null | head -2 || echo "  Not listening" && \
echo "" && \
echo "4. Chrome Remote Desktop:" && \
ps aux | grep "chrome-remote-desktop-host" | grep -v grep | head -1 || echo "  Not running" && \
echo "" && \
echo "5. Chrome Browser:" && \
ps aux | grep "/opt/google/chrome/chrome" | grep -v grep | head -1 || echo "  Not running" && \
echo "" && \
echo "6. Display:" && \
echo "  DISPLAY=$DISPLAY" && \
echo "" && \
echo "7. Active WebSocket Connections:" && \
(netstat -an 2>/dev/null | grep ":9009.*ESTABLISHED" | wc -l || ss -an 2>/dev/null | grep ":9009.*ESTAB" | wc -l) && \
echo "" && \
echo "8. HTTP Server Status:" && \
curl -s http://localhost:3111/mcp | jq -r '.status, .activeSessions' 2>/dev/null || curl -s http://localhost:3111/mcp
```

## Connection Flow Verification

### Step 1: Verify MCP Server is Running

```bash
ps aux | grep "dist/index.js.*--http" | grep -v grep
```

**Expected**: Process running with `--http --port 3111`

### Step 2: Verify Ports are Listening

```bash
lsof -i :9009  # WebSocket (CRITICAL: Must be 9009, not 3000)
lsof -i :3111  # HTTP
```

**Expected**: Both ports show `node` process listening

**IMPORTANT:** The Browser MCP extension is hardcoded to connect to port
**9009**. The server must listen on port 9009, not 3000.

### Step 3: Verify Chrome Remote Desktop

```bash
ps aux | grep "chrome-remote-desktop-host" | grep -v grep
```

**Expected**: `chrome-remote-desktop-host` process running

### Step 4: Verify Chrome Browser

```bash
ps aux | grep "/opt/google/chrome/chrome" | grep -v grep | head -1
```

**Expected**: Chrome process running with `--ozone-platform=x11`

### Step 5: Check Extension Connection

1. Open Chrome browser (via Chrome Remote Desktop)
2. Click Browser MCP extension icon
3. Click "Connect" button
4. Extension popup should show "Connected"

### Step 6: Verify WebSocket Connection

```bash
netstat -an | grep ":9009.*ESTABLISHED" | wc -l
# or
ss -an | grep ":9009.*ESTAB" | wc -l
```

**Expected**: Count > 0 (at least 1 established connection)

**IMPORTANT:** Check port **9009**, not 3000. The extension is hardcoded to
connect to port 9009.

### Step 7: Test HTTP Endpoint

```bash
curl -s http://localhost:3111/mcp | jq .
```

**Expected**: JSON response with `"status": "running"` and `"activeSessions"` >
0

## Common Issues

### Issue: "No connection to browser extension"

**Symptoms**: Tool calls fail with "No connection to browser extension"
**Causes**:

1. Extension not connected (most common)
2. WebSocket server not running
3. Extension connecting to wrong port
4. Firewall blocking WebSocket connection

**Solutions**:

1. Check extension popup shows "Connected"
2. Verify WebSocket server: `lsof -i :9009` (CRITICAL: Must be port 9009,
   not 3000)
3. Check server logs: `tail -f /tmp/browsermcp.log`
4. Reconnect extension (disconnect and reconnect)
5. **Most common cause:** Port mismatch - server listening on 3000 but extension
   expects 9009
   - Check:
     `grep defaultWsPort /home/ubuntu/proj/mcps/browser-mcp/mcp/src/local-deps/config/mcp.config.ts`
   - Must be: `defaultWsPort: 9009`
   - See:
     [Connection Troubleshooting Guide](./browser_mcp_connection_troubleshooting.md)

### Issue: WebSocket Server Not Starting

**Symptoms**: Port 9009 not listening (CRITICAL: Must be 9009, not 3000)
**Causes**:

1. Port already in use
2. Server configuration has wrong port (check `mcp.config.ts`:
   `defaultWsPort: 9009`)
3. Server crashed during startup
4. Permission denied

**Solutions**:

1. Check what's using port 9009: `lsof -i :9009`
2. Kill conflicting process or change port
3. Check server logs: `cat /tmp/browsermcp.log`
4. Restart server

### Issue: Chrome Won't Start

**Symptoms**: No Chrome processes running **Causes**:

1. Chrome Remote Desktop not running
2. Display not available
3. Chrome installation issue

**Solutions**:

1. Check Chrome Remote Desktop: `ps aux | grep chrome-remote-desktop-host`
2. Check display: `echo $DISPLAY` (should be `localhost:10.0`)
3. Try starting Chrome manually: `/opt/google/chrome/chrome --no-sandbox`

### Issue: Extension Can't Connect

**Symptoms**: Extension popup shows "Disconnected" or connection error
**Causes**:

1. WebSocket server not running
2. Wrong port configured in extension
3. Network/firewall issue

**Solutions**:

1. Verify WebSocket server: `lsof -i :9009` (CRITICAL: Must be 9009, not 3000)
2. Extension is hardcoded to connect to `ws://localhost:9009` - cannot be
   changed
3. Check server logs for connection attempts: `tail -f /tmp/browsermcp.log`
4. Try restarting both server and extension
5. See
   [Connection Troubleshooting Guide](./browser_mcp_connection_troubleshooting.md)
   for detailed steps

## Architecture Verification

### Component Checklist

- [ ] Chrome Remote Desktop host running
- [ ] Chrome browser running on virtual display
- [ ] Browser MCP extension installed in Chrome
- [ ] MCP server running (HTTP + WebSocket)
- [ ] Extension connected to WebSocket server
- [ ] Cursor connected to HTTP server

### Connection Path Verification

```
Cursor → HTTP (3111) → MCP Server → WebSocket (9009) → Extension → Chrome → Display
```

Each arrow should be verified:

1. **Cursor → HTTP**: Check `mcp.json` configuration
2. **HTTP → MCP Server**: Check server logs for requests
3. **MCP Server → WebSocket**: Check `sharedContext` has WebSocket
4. **WebSocket → Extension**: Check extension connection status
5. **Extension → Chrome**: Extension runs inside Chrome
6. **Chrome → Display**: Chrome uses Chrome Remote Desktop display

## Debugging Commands

### Monitor WebSocket Connections

```bash
watch -n 1 'netstat -an | grep ":9009"'
```

### Monitor Server Logs

```bash
tail -f /tmp/browsermcp.log
```

### Test WebSocket Server Directly

```bash
# Using wscat (if installed)
wscat -c ws://localhost:9009  # CRITICAL: Must be 9009, not 3000

# Or using curl (if compiled with WebSocket support)
curl --include \
     --no-buffer \
     --header "Connection: Upgrade" \
     --header "Upgrade: websocket" \
     --header "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     --header "Sec-WebSocket-Version: 13" \
     http://localhost:3111/mcp  # HTTP endpoint (not WebSocket)
```

### Check MCP Server Configuration

```bash
cat /data/dsa110-contimg/.cursor/mcp.json | jq '.browsermcp'
```

## Next Steps After Diagnosis

1. **If extension not connected**: Reconnect via extension popup
2. **If server not running**: Start server and check logs
3. **If ports in use**: Kill conflicting processes or change ports
4. **If Chrome not running**: Check Chrome Remote Desktop status
5. **If all components running but not working**: Check logs for errors
