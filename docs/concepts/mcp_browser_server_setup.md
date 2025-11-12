# Browser MCP Server Setup and Troubleshooting

## Overview

The Browser MCP (Model Context Protocol) server enables browser automation capabilities for the DSA-110 pipeline. This document covers setup, configuration, and troubleshooting, particularly the migration from stdio to HTTP transport.

## Architecture

The Browser MCP server runs as a separate HTTP service that Cursor connects to via the MCP protocol. It provides tools for:
- Browser navigation and interaction
- Page snapshots and element access
- Code extraction from web pages
- Clipboard operations

## Transport: HTTP vs Stdio

### Why HTTP Transport?

**Problem with Stdio:**
- Persistent "No server info found" errors during MCP handshake
- Node.js version incompatibilities between system and conda environments
- Communication failures between Cursor client and MCP server
- Difficult to debug stdio-based communication

**Solution: Streamable HTTP Transport**

The server was migrated from stdio transport to Streamable HTTP transport, which:
- ✅ Avoids stdio communication issues entirely
- ✅ More reliable for network-based communication
- ✅ Supports multiple concurrent clients
- ✅ Easier to debug (can use curl/browser)
- ✅ Works consistently regardless of Node.js version differences

## Setup Instructions

### Prerequisites

- Node.js v22.6.0+ (from casa6 conda environment)
- Browser MCP extension installed and connected in Comet browser
- Server code built and ready

### Starting the HTTP Server

1. **Build the server:**
   ```bash
   cd ~/proj/mcps/browser-mcp/mcp
   npm run build
   ```

2. **Start the server:**
   ```bash
   # Option 1: Foreground (for testing)
   /opt/miniforge/envs/casa6/bin/node dist/index.js --http --port 3111
   
   # Option 2: Background (for production)
   nohup /opt/miniforge/envs/casa6/bin/node dist/index.js --http --port 3111 > /tmp/browsermcp.log 2>&1 &
   
   # Option 3: Using startup script
   cd ~/proj/mcps/browser-mcp/mcp
   ./start-http-server.sh 3111
   ```

3. **Stop the server:**
   ```bash
   # Using stop script
   cd ~/proj/mcps/browser-mcp/mcp
   ./stop-http-server.sh 3111
   
   # Or manually
   lsof -ti:3111 | xargs kill
   ```

### Cursor Configuration

Update `~/.cursor/mcp.json` to use HTTP transport:

```json
{
  "mcpServers": {
    "browsermcp": {
      "url": "http://localhost:3111/mcp",
      "headers": {}
    }
  }
}
```

**Important:** After updating `mcp.json`, restart Cursor completely for the changes to take effect.

## Troubleshooting

### "No server info found" Error

**Symptom:** Cursor reports "No server info found" when trying to connect to the MCP server.

**Solution:** Use HTTP transport instead of stdio. This error was caused by stdio communication failures and is resolved by switching to HTTP.

### Server Won't Start

**Check Node.js version:**
```bash
/opt/miniforge/envs/casa6/bin/node --version
# Should be v22.6.0 or higher
```

**Check if port is in use:**
```bash
lsof -i:3111
```

**Check server logs:**
```bash
tail -20 /tmp/browsermcp.log
```

### GET Request Returns Error

**Symptom:** Visiting `http://localhost:3111/mcp` in browser returns `{"error":"Invalid session or request"}`

**Solution:** This was fixed by adding a GET handler that returns server status JSON. Ensure you're running the latest build:
```bash
cd ~/proj/mcps/browser-mcp/mcp
npm run build
./stop-http-server.sh 3111
nohup /opt/miniforge/envs/casa6/bin/node dist/index.js --http --port 3111 > /tmp/browsermcp.log 2>&1 &
```

### Tools Not Available in Cursor

**Checklist:**
1. Server is running: `ps aux | grep "dist/index.js.*--http"`
2. Cursor has been restarted after updating `mcp.json`
3. Server is accessible: `curl http://localhost:3111/mcp`
4. Tools are registered: Test with `tools/list` request

## Testing

### Test GET Endpoint

```bash
curl http://localhost:3111/mcp
```

Should return:
```json
{
  "status": "running",
  "server": "browsermcp",
  "version": "0.1.3",
  "endpoint": "/mcp",
  "transport": "Streamable HTTP",
  "message": "This is an MCP server endpoint. Use POST requests with JSON-RPC messages.",
  "activeSessions": 0
}
```

### Test POST Initialize

```bash
curl -X POST http://localhost:3111/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

Should return SSE response with serverInfo.

### Test Tools List

```bash
# First initialize to get session ID
INIT_RESPONSE=$(curl -s -i -X POST http://localhost:3111/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}')

# Extract session ID from headers
SESSION_ID=$(echo "$INIT_RESPONSE" | grep -i "^mcp-session-id:" | sed 's/^[^:]*: *//' | tr -d '\r\n ')

# List tools
curl -s -X POST http://localhost:3111/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

## Available Tools

The server provides the following browser automation tools:

- `browser_navigate` - Navigate to a URL
- `browser_go_back` - Go back to previous page
- `browser_go_forward` - Go forward to next page
- `browser_snapshot` - Capture accessibility snapshot
- `browser_click` - Click on elements
- `browser_hover` - Hover over elements
- `browser_type` - Type text into elements
- `browser_select_option` - Select dropdown options
- `browser_drag` - Drag elements
- `browser_press_key` - Press keyboard keys
- `browser_wait` - Wait for specified time
- `browser_get_console_logs` - Get browser console logs
- `browser_screenshot` - Take screenshots
- `browser_copy_to_clipboard` - Copy content via clipboard
- `browser_extract_code` - Extract code/text from DOM elements

## Technical Details

### Session Management

The HTTP transport uses session-based communication:
- Each `initialize` request creates a new session
- Session ID is returned in response headers as `mcp-session-id`
- Subsequent requests must include the session ID in headers
- Sessions are stored in memory and cleaned up on disconnect

### Request/Response Format

- **GET requests:** Return server status JSON
- **POST requests:** Handle MCP JSON-RPC protocol
- **Response format:** Server-Sent Events (SSE) for streaming responses
- **Content-Type:** `text/event-stream` for SSE, `application/json` for regular responses

### Code Location

Server code: `/home/ubuntu/proj/mcps/browser-mcp/mcp/`
- Source: `src/http-server.ts` - HTTP server implementation
- Source: `src/index.ts` - Main entry point with CLI options
- Build output: `dist/index.js`

## Related Documentation

- [MCP Specification](https://modelcontextprotocol.io/)
- Browser MCP Server README: `../../../proj/mcps/browser-mcp/mcp/README_HTTP.md` (external file)
- [Directory Architecture](DIRECTORY_ARCHITECTURE.md)

## History

- **2025-11-12:** Migrated from stdio to HTTP transport to resolve "No server info found" errors
- **2025-11-12:** Added GET handler for server status endpoint
- **2025-11-12:** Fixed import warnings (common.navigate vs snapshot.navigate)

