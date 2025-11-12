# Browser MCP + Chrome Remote Desktop Architecture

## Overview

This document describes how the Browser MCP server interacts with Chrome Remote Desktop and the browser extension.

## Architecture Components

### 1. Chrome Remote Desktop Host
- **Process**: `/opt/google/chrome-remote-desktop/chrome-remote-desktop-host`
- **Purpose**: Manages remote desktop session
- **Display**: Creates virtual X11 display (`DISPLAY=localhost:10.0`)
- **Status**: Running continuously

### 2. Chrome Browser
- **Process**: `/opt/google/chrome/chrome`
- **Display**: Uses Chrome Remote Desktop's virtual display (`--ozone-platform=x11`)
- **Purpose**: Provides the browser environment where the extension runs
- **Note**: Chrome runs on the virtual display, not a physical monitor

### 3. Browser MCP Extension
- **Location**: Installed in Chrome browser
- **Connection**: Connects to `ws://localhost:9009` (WebSocket) - **CRITICAL: Port 9009 is hardcoded in extension**
- **Purpose**: Bridges browser automation (Playwright) with MCP server
- **Status**: User clicks "Connect" in extension popup to establish WebSocket connection

### 4. Browser MCP Server
- **HTTP Endpoint**: `http://localhost:3111/mcp` (Streamable HTTP transport)
- **WebSocket Server**: `ws://localhost:9009` (for browser extension) - **CRITICAL: Must be port 9009, not 3000**
- **Process**: `/opt/miniforge/envs/casa6/bin/node dist/index.js --http --port 3111`
- **Purpose**: 
  - Receives MCP protocol requests from Cursor via HTTP
  - Communicates with browser extension via WebSocket
  - Executes browser automation commands

### 5. Cursor IDE
- **Connection**: Connects to `http://localhost:3111/mcp` (HTTP)
- **Configuration**: `/data/dsa110-contimg/.cursor/mcp.json`
- **Purpose**: Sends MCP tool requests to Browser MCP server

## Connection Flow

```
Cursor IDE
    │
    │ HTTP (JSON-RPC)
    ▼
Browser MCP Server (port 3111)
    │
    │ WebSocket (ws://localhost:9009) - CRITICAL: Must be 9009, not 3000
    ▼
Browser MCP Extension (in Chrome)
    │
    │ Playwright API
    ▼
Chrome Browser (on Chrome Remote Desktop display)
    │
    │ X11
    ▼
Chrome Remote Desktop Host (DISPLAY=localhost:10.0)
```

## Key Points

### X11 Forwarding vs Chrome Remote Desktop

**Old approach (X11 forwarding)**:
- Required SSH with X11 forwarding (`-X` or `-Y`)
- Required `/tmp/.X11-unix` socket mount in Docker
- Required `DISPLAY` environment variable
- **Problem**: Doesn't work well with remote servers, requires active SSH session

**Current approach (Chrome Remote Desktop)**:
- Chrome Remote Desktop manages the display independently
- No SSH X11 forwarding needed
- Browser runs on virtual display (`localhost:10.0`)
- **Advantage**: Works without SSH, persistent session

### WebSocket Connection

The Browser MCP extension connects to `ws://localhost:9009`:
- **CRITICAL:** Port 9009 is **hardcoded** in the extension - server must listen on 9009, not 3000
- This is a **local connection** (extension → server on same machine)
- Chrome Remote Desktop doesn't interfere with this connection
- The extension runs **inside** Chrome, which runs **on** Chrome Remote Desktop's display
- WebSocket connection is independent of the display system
- **Common issue:** Port mismatch - if server listens on 3000 but extension expects 9009, connection will fail

### Why It Works

1. **Chrome Remote Desktop** provides a persistent virtual display
2. **Chrome browser** runs on that display (normal X11 application)
3. **Browser extension** runs inside Chrome (normal Chrome extension)
4. **WebSocket** connects extension to server (normal network connection)
5. **No X11 forwarding needed** because everything runs locally on the server

## Configuration Files

### MCP Server Configuration
- **Location**: `/data/dsa110-contimg/.cursor/mcp.json`
- **Entry**: 
  ```json
  "browsermcp": {
    "url": "http://localhost:3111/mcp",
    "headers": {}
  }
  ```

### WebSocket Port
- **Default**: Port **9009** (configured in `mcp.config.ts` as `defaultWsPort: 9009`)
- **Purpose**: Browser extension connects here
- **CRITICAL**: Port 9009 is **hardcoded** in the Browser MCP extension - server must listen on 9009, not 3000
- **Note**: Must be accessible from Chrome (localhost is fine)

## Troubleshooting

### Extension Not Connecting
1. Check WebSocket server is running: `lsof -i :9009` (CRITICAL: Must be 9009, not 3000)
2. Check extension popup shows "Connected"
3. Check server logs: `tail -f /tmp/browsermcp.log`
4. Verify Chrome is running: `ps aux | grep chrome`

### Display Issues
- Chrome Remote Desktop manages display automatically
- No need to set `DISPLAY` manually
- If Chrome won't start, check Chrome Remote Desktop status

### Port Conflicts
- Port 9009: WebSocket server (must be free) - **CRITICAL: Must be 9009, not 3000**
- Port 3111: HTTP MCP server (must be free)
- Check with: `lsof -i :9009` and `lsof -i :3111`

## Testing Connection

1. **Start MCP server**: 
   ```bash
   cd /home/ubuntu/proj/mcps/browser-mcp/mcp
   /opt/miniforge/envs/casa6/bin/node dist/index.js --http --port 3111
   ```

2. **Check WebSocket server**: 
   ```bash
   lsof -i :9009  # Should show node listening (CRITICAL: Must be 9009, not 3000)
   ```

3. **Connect extension**: Click "Connect" in Browser MCP extension popup

4. **Test from Cursor**: Use `mcp_browsermcp_browser_navigate` tool

## Related Documentation

- [Browser MCP Server Setup](./mcp_browser_server_setup.md)
- [MCP Protocol Documentation](https://modelcontextprotocol.io)

