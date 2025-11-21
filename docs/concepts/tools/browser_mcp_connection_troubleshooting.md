# Browser MCP Connection Troubleshooting Guide

## Overview

This document provides a **step-by-step debugging process** for resolving
Browser MCP connection issues. It documents the exact troubleshooting steps used
to resolve connection problems between the Browser MCP server, browser
extension, and Cursor IDE.

**Who is this for?** Anyone encountering Browser MCP connection issues, even if
you've never worked with this system before.

**What you'll learn:**

- How to verify each component is working
- How to identify the exact problem
- How to fix common issues
- How to verify the fix worked

## Architecture Overview (Understanding the System)

Before troubleshooting, understand how the components connect:

```
Cursor IDE (your editor)
    │
    │ HTTP (port 3111) - MCP protocol
    ▼
Browser MCP Server (Node.js process)
    │
    │ WebSocket (port 9009) - Browser automation protocol
    ▼
Browser MCP Extension (Chrome extension)
    │
    │ Playwright API
    ▼
Chrome Browser (running on Chrome Remote Desktop)
```

**Key Points:**

- **Cursor** talks to the **server** via HTTP (port 3111)
- **Server** talks to the **extension** via WebSocket (port 9009)
- **Extension** controls **Chrome** via Playwright
- All components must be running and connected for tools to work

**Why HTTP for Cursor but WebSocket for Extension?**

- **HTTP (Cursor ↔ Server):** Cursor uses the MCP (Model Context Protocol)
  which supports HTTP transport. This is more reliable than stdio and works
  across network boundaries. Each request/response is independent.

- **WebSocket (Server ↔ Extension):** The browser extension needs a persistent,
  bidirectional connection to receive commands and send responses. WebSocket
  allows the server to push commands to the extension and receive responses
  asynchronously.

**Important:** These are two separate protocols on two separate ports. The HTTP
connection (3111) is for Cursor, the WebSocket connection (9009) is for the
extension. Both must be working for tools to function.

## File Locations (Where Everything Lives)

**Server code:**

- Location: `/home/ubuntu/proj/mcps/browser-mcp/mcp/`
- Config file: `src/local-deps/config/mcp.config.ts` (defines WebSocket port)
- Message handler: `src/local-deps/r2r/messaging/ws/sender.ts` (handles
  extension responses)
- HTTP server: `src/http-server.ts` (creates WebSocket server and HTTP endpoint)
- Build output: `dist/index.js` (compiled server)

**Cursor configuration:**

- Location: `/data/dsa110-contimg/.cursor/mcp.json`
- Defines: How Cursor connects to the server

**Server logs:**

- Location: `/tmp/browsermcp.log`
- Contains: Server startup, WebSocket connections, errors

**Extension location:**

- Chrome extension directory:
  `~/.config/google-chrome/Default/Extensions/bjfgambnhccakkhmkepdoekmckoijdlc/`
- Background script: `background.js` (contains hardcoded port 9009)
- Manifest: `manifest.json` (extension permissions)

## Critical Configuration Values

Before troubleshooting, verify these **critical values** match:

1. **WebSocket Port**: Extension expects `9009` (hardcoded in extension)
2. **HTTP Port**: Cursor connects to `3111` (configurable in `mcp.json`)
3. **Message Format**: Extension sends
   `{id, type: "messageResponse", payload: {requestId, result, error}}`

## Quick Diagnostic Checklist

Run this command to check all components at once:

```bash
/data/dsa110-contimg/scripts/check_browser_mcp.sh
```

Or manually check each component:

```bash
# 1. HTTP Server (port 3111)
lsof -i :3111 | grep LISTEN

# 2. WebSocket Server (port 9009) - CRITICAL: Must be 9009, not 3000
lsof -i :9009 | grep LISTEN

# 3. Active WebSocket connections
netstat -an 2>/dev/null | grep ":9009.*ESTABLISHED" || ss -an 2>/dev/null | grep ":9009.*ESTAB"

# 4. Server process
ps aux | grep "dist/index.js.*--http.*3111" | grep -v grep

# 5. Server logs
tail -30 /tmp/browsermcp.log | grep -E "WebSocket|connection|connected|9009"
```

## Step-by-Step Troubleshooting Process

### Step 1: Verify Server is Running

**Check HTTP server:**

```bash
ps aux | grep "dist/index.js.*--http.*3111" | grep -v grep
```

**Expected output:** Process running with `--http --port 3111`

**If not running:**

```bash
cd /home/ubuntu/proj/mcps/browser-mcp/mcp
/opt/miniforge/envs/casa6/bin/node dist/index.js --http --port 3111 > /tmp/browsermcp.log 2>&1 &
```

### Step 2: Verify WebSocket Port Configuration

**CRITICAL:** The Browser MCP extension is **hardcoded** to connect to port
`9009`. The server **must** listen on port `9009`, not `3000`.

**Why is this important?** The extension's code has the port number baked in. If
the server listens on a different port, the extension will try to connect to the
wrong port and fail silently.

**How to verify the extension's hardcoded port:**

You can check what port the extension expects by looking at its background
script:

```bash
# Find the extension directory
find ~/.config/google-chrome -name "background.js" -path "*browsermcp*" -o -name "background.js" -path "*Browser*MCP*" 2>/dev/null | head -1

# Check for the port number (usually shows 9009)
grep -o "defaultWsPort:[0-9]*\|localhost:[0-9]*" ~/.config/google-chrome/Default/Extensions/bjfgambnhccakkhmkepdoekmckoijdlc/*/background.js | head -5
```

**Expected:** Extension code shows port `9009` (or `defaultWsPort:9009`)

**Check server configuration:**

```bash
grep -n "defaultWsPort" /home/ubuntu/proj/mcps/browser-mcp/mcp/src/local-deps/config/mcp.config.ts
```

**Expected:** `defaultWsPort: 9009`

**If wrong (shows `3000`):**

1. Edit the config file:

   ```bash
   cd /home/ubuntu/proj/mcps/browser-mcp/mcp
   # Edit src/local-deps/config/mcp.config.ts
   # Change: defaultWsPort: 3000
   # To:     defaultWsPort: 9009
   ```

2. Rebuild the server:

   ```bash
   /opt/miniforge/envs/casa6/bin/npm run build
   ```

   **Expected output:** Build completes without errors

3. Restart the server (see Step 1 for restart commands)

**Verify port is listening:**

```bash
lsof -i :9009 | grep LISTEN
```

**Expected:** Node.js process listening on port 9009

**If port 9009 not listening:**

1. Check server logs: `tail -20 /tmp/browsermcp.log`
2. Look for: `[MCP HTTP] WebSocket server listening on port 9009`
3. If it says port 3000, rebuild and restart server

### Step 3: Check Extension Connection

**In Chrome (via Chrome Remote Desktop):**

1. Open Chrome browser
2. Click Browser MCP extension icon
3. Click "Connect" button
4. Extension popup should show "Connected"

**If extension shows "Connected" but tools still fail:**

This is a common issue! The popup might show "Connected" but the actual
WebSocket connection might not be established. Here's how to verify:

**Step-by-step: Check Extension Background Script Console**

1. Open Chrome (via Chrome Remote Desktop)
2. Type in address bar: `chrome://extensions/`
3. Find "Browser MCP" extension in the list
4. Look for a link that says:
   - "Inspect views: service worker" (for Manifest V3 extensions)
   - OR "background page" (for Manifest V2 extensions)
5. Click it - this opens Chrome DevTools for the extension
6. Go to the "Console" tab
7. Click "Connect" in the Browser MCP extension popup (if not already connected)
8. Watch the console for messages

**What to look for:**

**Good signs:**

- No errors
- Messages about WebSocket connection
- Messages about connecting to `ws://localhost:9009`

**Bad signs - Common errors:**

1. **CSP (Content Security Policy) Error:**

   ```
   Connecting to 'ws://localhost:3000/' violates Content Security Policy
   ```

   **Meaning:** Extension is trying to connect to port 3000, but should
   use 9009. **Solution:** Check server is listening on port 9009, not 3000.

2. **Connection Refused:**

   ```
   WebSocket connection to 'ws://localhost:9009/' failed: Error in connection establishment
   ```

   **Meaning:** No server listening on port 9009. **Solution:** Start the server
   (see Step 1).

3. **No messages at all:** **Meaning:** Extension might not be trying to
   connect, or connection is silently failing. **Solution:** Disconnect and
   reconnect the extension, watch console while doing so.

**If you see errors:** Note the exact error message - it tells you what's wrong.

### Step 4: Verify WebSocket Connection is Established

**Check for active connections:**

```bash
netstat -an 2>/dev/null | grep ":9009.*ESTABLISHED" || ss -an 2>/dev/null | grep ":9009.*ESTAB"
```

**Expected:** At least one ESTABLISHED connection

**If no connections:**

1. Disconnect and reconnect extension in Chrome
2. Wait 2-3 seconds
3. Check again
4. Check server logs: `tail -20 /tmp/browsermcp.log | grep -i websocket`

**Check server logs for connection:**

```bash
tail -50 /tmp/browsermcp.log | grep -E "WebSocket.*connection|Browser extension connected"
```

**Expected:**
`[MCP HTTP] Browser extension connected via WebSocket (readyState: 1)`

### Step 5: Verify Message Format Handler

**CRITICAL:** The extension sends responses in a specific format that must be
handled correctly. If the handler doesn't recognize this format, tools will
timeout even though the WebSocket connection is established.

**Why this matters:** The server sends a request to the extension and waits for
a response. If the response format doesn't match what the handler expects, the
handler won't recognize it as a response and will timeout.

**Extension response format:** The extension wraps responses in a specific
structure:

```json
{
  "id": "some-uuid",
  "type": "messageResponse",
  "payload": {
    "requestId": "original-request-id",
    "result": {...actual response data...},
    "error": null
  }
}
```

**Standard format (what the handler originally expected):**

```json
{
  "id": "original-request-id",
  "result": {...actual response data...},
  "error": null
}
```

**Check message handler code:**

```bash
grep -A 30 "messageHandler.*data.*Buffer" /home/ubuntu/proj/mcps/browser-mcp/mcp/src/local-deps/r2r/messaging/ws/sender.ts
```

**Expected:** Handler checks both formats. Look for code like:

```typescript
// Check standard format
if (response.id === messageId) {
  // handle response
}

// Check extension format
if (
  response.type === "messageResponse" &&
  response.payload.requestId === messageId
) {
  // handle response from payload
}
```

**If handler doesn't support extension format:**

1. Edit the file:

   ```bash
   cd /home/ubuntu/proj/mcps/browser-mcp/mcp
   # Edit: src/local-deps/r2r/messaging/ws/sender.ts
   ```

2. Find the `messageHandler` function (around line 50-80)

3. Update it to handle both formats. The handler should look like:

   ```typescript
   const messageHandler = (data: Buffer) => {
     try {
       const response = JSON.parse(data.toString());

       // Check standard format
       if (response.id === messageId) {
         clearTimeout(timeout);
         ws.removeListener("message", messageHandler);
         if (response.error) {
           reject(new Error(response.error));
         } else {
           resolve(response.result);
         }
         return;
       }

       // Check extension format
       if (
         response.type === "messageResponse" &&
         response.payload &&
         response.payload.requestId === messageId
       ) {
         clearTimeout(timeout);
         ws.removeListener("message", messageHandler);
         if (response.payload.error) {
           reject(new Error(response.payload.error));
         } else {
           resolve(response.payload.result);
         }
         return;
       }
     } catch (e) {
       // Not our message, ignore
     }
   };
   ```

4. Rebuild:

   ```bash
   /opt/miniforge/envs/casa6/bin/npm run build
   ```

5. Restart server (see Step 1)

### Step 6: Test Browser Tools

**After fixing configuration, test the tools:**

**In Cursor IDE:**

1. Open Cursor
2. Try a simple navigation command:

   ```
   Navigate to https://www.example.com
   ```

   OR use the MCP tool directly:

   ```
   mcp_browsermcp_browser_navigate({"url": "https://www.example.com"})
   ```

3. Try getting a snapshot:
   ```
   mcp_browsermcp_browser_snapshot({})
   ```

**What success looks like:**

**Successful navigation:**

- Returns immediately (no timeout)
- Shows: `Page URL: https://www.example.com/`
- Shows: `Page Title: Example Domain`
- No error messages

**Successful snapshot:**

- Returns immediately (no timeout)
- Shows page structure in YAML format
- Lists elements with references like `[ref=s1e2]`
- No error messages

**What failure looks like:**

**Timeout (30 seconds):**

- Tool call hangs for 30 seconds
- Then returns: `Error: WebSocket response timeout after 30000ms`
- **Meaning:** Server sent request to extension but didn't receive response
- **Likely cause:** Message format handler not recognizing extension's response
  format

**"No connection to browser extension":**

- Returns immediately with error
- **Meaning:** No WebSocket connection established
- **Likely cause:** Extension not connected, or server not listening on port
  9009

**"Session not found":**

- Returns immediately with error
- **Meaning:** Cursor's HTTP session expired or server restarted
- **Solution:** Restart Cursor to reconnect

**If tools timeout or fail:**

1. **Check WebSocket connection is still active:**

   ```bash
   netstat -an | grep ":9009.*ESTABLISHED"
   ```

   **Expected:** At least one ESTABLISHED connection

2. **Check server logs for activity:**

   ```bash
   tail -50 /tmp/browsermcp.log
   ```

3. **Look for WebSocket message activity:**

   ```bash
   tail -50 /tmp/browsermcp.log | grep "WebSocket message received"
   ```

   **Expected:** Logs show `[MCP HTTP] WebSocket message received (XXX bytes)`
   when tools are called

   **If you see messages being received:** The connection is working, but
   responses aren't being recognized (message format issue)

   **If you don't see messages:** The extension isn't receiving requests
   (connection issue)

### Step 7: Verify Cursor MCP Connection

**Check Cursor configuration:**

```bash
cat /data/dsa110-contimg/.cursor/mcp.json | jq '.mcpServers.browsermcp'
```

**Expected:**

```json
{
  "url": "http://localhost:3111/mcp",
  "headers": {}
}
```

**If wrong:**

1. Update `mcp.json` to use HTTP transport (not stdio)
2. Restart Cursor completely
3. Wait for Cursor to reconnect

**Test HTTP endpoint:**

```bash
curl -s http://localhost:3111/mcp
```

**Expected:** JSON response (may show "Invalid session" if accessed directly,
but should not error)

## Understanding Error Messages

Before diving into specific issues, here's what common error messages mean:

| Error Message                                | What It Means                                        | Where to Look                       |
| -------------------------------------------- | ---------------------------------------------------- | ----------------------------------- |
| `"No connection to browser extension"`       | No WebSocket connection between server and extension | Check port 9009 connection          |
| `"WebSocket response timeout after 30000ms"` | Server sent request but didn't get response          | Check message format handler        |
| `"Session not found"`                        | Cursor's HTTP session expired                        | Restart Cursor                      |
| `"Stale aria-ref"`                           | Page changed, need fresh snapshot                    | Get new snapshot before interacting |
| `"Invalid session or request"`               | HTTP request format wrong or session expired         | Check Cursor connection             |

## Common Issues and Solutions

### Issue 1: "No connection to browser extension"

**Symptoms:**

- Tool calls fail with "No connection to browser extension"
- Extension popup shows "Connected" but tools don't work

**Root Causes:**

1. **Port mismatch** (most common): Server listening on 3000, extension expects
   9009
2. **WebSocket not established**: Extension not actually connected
3. **Message format mismatch**: Server not handling extension's response format

**Solution:**

1. Verify server is listening on port **9009** (not 3000)
2. Check `mcp.config.ts`: `defaultWsPort: 9009`
3. Rebuild server: `npm run build`
4. Restart server
5. Disconnect and reconnect extension
6. Verify connection: `netstat -an | grep ":9009.*ESTABLISHED"`

### Issue 2: Tools Timeout After 30 Seconds

**Symptoms:**

- WebSocket connection is established (you see ESTABLISHED in `netstat`)
- Extension shows "Connected" in popup
- Tools are called but timeout after exactly 30 seconds
- Server logs show "WebSocket message received" when you call tools
- But no response is processed

**What's happening:**

1. Cursor sends HTTP request to server
2. Server sends WebSocket message to extension
3. Extension processes request and sends response
4. Server receives response but doesn't recognize it
5. Server waits 30 seconds, then times out

**Root Cause:** Message format handler not processing extension's response
format correctly

**How to verify this is the problem:**

```bash
# Check if messages are being received
tail -50 /tmp/browsermcp.log | grep "WebSocket message received"

# If you see messages being received but tools still timeout,
# it's definitely a message format handler issue
```

**Solution:**

1. Check message handler in `sender.ts` (see Step 5 for exact code)
2. Verify it handles `response.type === "messageResponse"` format
3. Verify it extracts `requestId` from `response.payload.requestId`
4. Rebuild:
   `cd /home/ubuntu/proj/mcps/browser-mcp/mcp && /opt/miniforge/envs/casa6/bin/npm run build`
5. Restart server (kill old process, start new one)
6. Test again

**Expected after fix:** Tools return immediately instead of timing out

### Issue 3: "Session not found" Error

**Symptoms:**

- HTTP endpoint returns `{"error":"Session not found"}`
- Cursor can't connect to MCP server

**Root Cause:** Cursor needs to reconnect after server restart

**Solution:**

1. Restart Cursor completely
2. Wait for Cursor to reconnect (check MCP server status in Cursor)
3. Test again

### Issue 4: Extension Shows "Connected" But No WebSocket Connection

**Symptoms:**

- Extension popup shows "Connected"
- But `netstat` shows no ESTABLISHED connections on port 9009
- Server logs show no connection messages

**Root Cause:** Extension is connecting to wrong port or connection is being
blocked

**Solution:**

1. Check extension's background script console (`chrome://extensions/` → Inspect
   service worker)
2. Look for CSP errors or connection errors
3. Verify server is listening on port 9009: `lsof -i :9009`
4. Check firewall: `sudo iptables -L -n | grep 9009`
5. Try reconnecting extension

### Issue 5: Port Already in Use

**Symptoms:**

- Server won't start: "Port 9009 already in use"
- Or server starts but WebSocket server fails

**Solution:**

```bash
# Find process using port 9009
lsof -i :9009

# Kill it
lsof -ti:9009 | xargs kill -9

# Restart server
cd /home/ubuntu/proj/mcps/browser-mcp/mcp
/opt/miniforge/envs/casa6/bin/node dist/index.js --http --port 3111 > /tmp/browsermcp.log 2>&1 &
```

## Verification After Fixes

After applying fixes, verify everything works:

```bash
# 1. Server running
ps aux | grep "dist/index.js.*--http.*3111" | grep -v grep

# 2. Port 9009 listening
lsof -i :9009 | grep LISTEN

# 3. WebSocket connection established
netstat -an | grep ":9009.*ESTABLISHED" | wc -l
# Should show at least 1

# 4. Server logs show connection
tail -20 /tmp/browsermcp.log | grep -i "connected"

# 5. Test tool in Cursor
# mcp_browsermcp_browser_navigate({"url": "https://www.example.com"})
```

## Key Files to Check

1. **Server configuration:**
   `/home/ubuntu/proj/mcps/browser-mcp/mcp/src/local-deps/config/mcp.config.ts`
   - Must have: `defaultWsPort: 9009`

2. **Message handler:**
   `/home/ubuntu/proj/mcps/browser-mcp/mcp/src/local-deps/r2r/messaging/ws/sender.ts`
   - Must handle: `response.type === "messageResponse"` format

3. **HTTP server:** `/home/ubuntu/proj/mcps/browser-mcp/mcp/src/http-server.ts`
   - Must create WebSocket server on port 9009
   - Must use `sharedContext` for WebSocket connection

4. **Cursor config:** `/data/dsa110-contimg/.cursor/mcp.json`
   - Must use HTTP transport: `"url": "http://localhost:3111/mcp"`

5. **Server logs:** `/tmp/browsermcp.log`
   - Check for connection messages and errors

## Complete Setup from Scratch

If you're starting completely fresh, follow these steps in order:

### Prerequisites Check

1. **Node.js version:**

   ```bash
   /opt/miniforge/envs/casa6/bin/node --version
   ```

   **Expected:** v22.6.0 or higher

2. **Server code exists:**

   ```bash
   ls -la /home/ubuntu/proj/mcps/browser-mcp/mcp/
   ```

   **Expected:** Directory exists with `package.json`, `src/`, etc.

3. **Chrome Remote Desktop running:**

   ```bash
   ps aux | grep chrome-remote-desktop-host | grep -v grep
   ```

   **Expected:** Process running

4. **Chrome browser running:**

   ```bash
   ps aux | grep "/opt/google/chrome/chrome" | grep -v grep
   ```

   **Expected:** Process running

5. **Browser MCP extension installed:**
   - Open Chrome (via Chrome Remote Desktop)
   - Go to `chrome://extensions/`
   - Look for "Browser MCP" extension
   - **Expected:** Extension is installed and enabled

### Setup Steps

1. **Configure server port:**

   ```bash
   cd /home/ubuntu/proj/mcps/browser-mcp/mcp
   grep "defaultWsPort" src/local-deps/config/mcp.config.ts
   ```

   - If shows `3000`, change to `9009`
   - Edit file, change `defaultWsPort: 3000` to `defaultWsPort: 9009`

2. **Verify message handler:**

   ```bash
   grep -A 30 "messageHandler.*data.*Buffer" src/local-deps/r2r/messaging/ws/sender.ts | grep -E "messageResponse|payload.requestId"
   ```

   - Should show code handling `response.type === "messageResponse"`

3. **Build server:**

   ```bash
   /opt/miniforge/envs/casa6/bin/npm run build
   ```

   - Wait for build to complete
   - Check for errors

4. **Start server:**

   ```bash
   /opt/miniforge/envs/casa6/bin/node dist/index.js --http --port 3111 > /tmp/browsermcp.log 2>&1 &
   ```

5. **Verify server started:**

   ```bash
   sleep 3
   tail -10 /tmp/browsermcp.log
   lsof -i :9009 | grep LISTEN
   lsof -i :3111 | grep LISTEN
   ```

   - Should see server listening on both ports

6. **Configure Cursor:**
   - Edit `/data/dsa110-contimg/.cursor/mcp.json`
   - Ensure `browsermcp` entry uses HTTP transport:
     ```json
     "browsermcp": {
       "url": "http://localhost:3111/mcp",
       "headers": {}
     }
     ```

7. **Restart Cursor:**
   - Completely quit Cursor
   - Restart Cursor
   - Wait for it to reconnect to MCP servers

8. **Connect extension:**
   - Open Chrome (via Chrome Remote Desktop)
   - Click Browser MCP extension icon
   - Click "Connect" button
   - Popup should show "Connected"

9. **Verify connection:**

   ```bash
   netstat -an | grep ":9009.*ESTABLISHED"
   ```

   - Should show at least one ESTABLISHED connection

10. **Test tools:**
    - In Cursor, try:
      `mcp_browsermcp_browser_navigate({"url": "https://www.example.com"})`
    - Should return immediately with page info
    - No timeouts, no errors

## Summary: Critical Values Checklist

Before reporting issues, verify each of these:

- [ ] Server listening on port **9009** (WebSocket), not 3000
  - Check: `lsof -i :9009 | grep LISTEN`
- [ ] `mcp.config.ts` has `defaultWsPort: 9009`
  - Check:
    `grep defaultWsPort /home/ubuntu/proj/mcps/browser-mcp/mcp/src/local-deps/config/mcp.config.ts`
- [ ] WebSocket connection established:
      `netstat -an | grep ":9009.*ESTABLISHED"`
  - Should show at least 1 ESTABLISHED connection
- [ ] Extension shows "Connected" in popup
  - Check in Chrome extension popup
- [ ] Server logs show: `Browser extension connected via WebSocket`
  - Check: `tail -20 /tmp/browsermcp.log | grep "connected"`
- [ ] Message handler supports `response.type === "messageResponse"` format
  - Check:
    `grep -A 20 "messageHandler" /home/ubuntu/proj/mcps/browser-mcp/mcp/src/local-deps/r2r/messaging/ws/sender.ts | grep "messageResponse"`
- [ ] Cursor `mcp.json` uses HTTP transport (not stdio)
  - Check:
    `cat /data/dsa110-contimg/.cursor/mcp.json | jq '.mcpServers.browsermcp'`
  - Should show `"url": "http://localhost:3111/mcp"`
- [ ] Cursor has been restarted after config changes
  - After changing `mcp.json`, must restart Cursor completely
- [ ] Server process is running
  - Check: `ps aux | grep "dist/index.js.*--http.*3111" | grep -v grep`

## Related Documentation

- [Browser MCP Server Setup](./mcp_browser_server_setup.md) - Initial setup and
  configuration
- [Browser MCP Diagnostics](./browser_mcp_diagnostics.md) - Diagnostic commands
  and checks
- [Browser MCP + Chrome Remote Desktop Architecture](./browser_mcp_chrome_remote_desktop_architecture.md) -
  Architecture overview
