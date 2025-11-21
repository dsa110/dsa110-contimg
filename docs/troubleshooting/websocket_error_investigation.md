# WebSocket Error Investigation and Fix

## Problem Summary

The application was experiencing WebSocket connection errors that were logged as
generic Event objects without useful diagnostic information:

```
[ERROR] WebSocket error: Event {isTrusted: true, type: 'error', target: WebSocket, ...}
```

This generic error message made it impossible to diagnose the root cause of the
connection failures.

## Root Cause Analysis

The WebSocket `onerror` event handler in `websocket.ts` (line 84-88) was only
logging the generic Event object, which doesn't provide:

- The WebSocket URL being connected to
- The connection state (readyState)
- Close codes or reasons
- Reconnection attempt information

Additionally, the `onclose` event handler wasn't capturing the close code and
reason, which are the most diagnostic pieces of information available.

## Solution Implemented

Enhanced the WebSocket error handling in `/frontend/src/api/websocket.ts` to
provide comprehensive diagnostic information:

### 1. Enhanced `onerror` Handler

The error handler now logs:

- **URL**: The WebSocket URL being connected to
- **readyState**: Current connection state (CONNECTING, OPEN, CLOSING, CLOSED)
- **reconnectAttempt**: Current reconnection attempt number
- **message/type**: Any available error message or type from the error object

### 2. Enhanced `onclose` Handler

The close handler now logs:

- **URL**: The WebSocket URL that was connected
- **code**: Close code (numeric)
- **codeDescription**: Human-readable description of the close code
- **reason**: Close reason string (if provided by server)
- **wasClean**: Whether the connection closed cleanly
- **reconnectAttempt**: Current reconnection attempt number

### 3. URL Validation

Added validation to check if the WebSocket URL is valid before attempting
connection, preventing errors from invalid URL formats.

### 4. Helper Methods

Added two helper methods:

- `getReadyStateText()`: Converts numeric readyState to human-readable text
- `getCloseCodeDescription()`: Provides human-readable descriptions for
  WebSocket close codes (1000-1015 and reserved ranges)

## Diagnostic Information Now Available

When a WebSocket error occurs, you will now see structured error information
like:

```javascript
{
  url: "ws://localhost:8000/api/ws/status",
  readyState: 3,
  readyStateText: "CLOSED",
  reconnectAttempt: 2
}
```

And when the connection closes, you'll see:

```javascript
{
  url: "ws://localhost:8000/api/ws/status",
  code: 1006,
  codeDescription: "Abnormal Closure",
  reason: "Connection lost",
  wasClean: false,
  reconnectAttempt: 2
}
```

## Common Close Codes and Their Meanings

- **1000**: Normal Closure - Connection closed intentionally
- **1001**: Going Away - Server is shutting down or client navigating away
- **1002**: Protocol Error - Invalid WebSocket frame received
- **1003**: Unsupported Data - Received unsupported data type
- **1006**: Abnormal Closure - Connection closed without close frame (most
  common for network issues)
- **1007**: Invalid Frame Payload Data - Invalid UTF-8 data received
- **1008**: Policy Violation - Server terminated connection due to policy
  violation
- **1011**: Internal Server Error - Server encountered an error
- **1012**: Service Restart - Server restarting
- **1013**: Try Again Later - Temporary server condition

## How to Diagnose WebSocket Issues

### Step 1: Check the Enhanced Error Logs

Look for the new structured error logs in the browser console. They will show:

- The exact URL being connected to
- The connection state when the error occurred
- Close codes and reasons

### Step 2: Verify WebSocket Server Status

1. Check if the WebSocket server is running
2. Verify the server is listening on the expected port
3. Check server logs for connection attempts

### Step 3: Verify Network Connectivity

1. Open Chrome DevTools → Network tab
2. Filter by "WS" (WebSockets)
3. Look for failed connection attempts
4. Check the handshake request/response

### Step 4: Check URL Configuration

The WebSocket URL is constructed from:

- `VITE_API_URL` environment variable (if set)
- Or defaults to `/api/ws/status` (relative path)

Verify:

- The environment variable is set correctly (if used)
- The relative path resolves to the correct server
- The protocol (ws:// vs wss://) matches the page protocol

### Step 5: Interpret Close Codes

Use the close code descriptions to understand what happened:

- **1006 (Abnormal Closure)**: Usually indicates network issues, firewall
  blocking, or server not running
- **1008 (Policy Violation)**: Server rejected the connection due to policy
  (CORS, authentication, etc.)
- **1011 (Internal Server Error)**: Server-side error occurred

## Example Diagnostic Workflow

1. **Error occurs** → Check console for structured error log
2. **See close code 1006** → Indicates abnormal closure (network/server issue)
3. **Check URL** → Verify it's correct: `ws://localhost:8000/api/ws/status`
4. **Check server** → Verify server is running on port 8000
5. **Check network** → Use DevTools Network tab to see handshake attempt
6. **Check server logs** → Look for connection attempts or errors

## Files Modified

- `/frontend/src/api/websocket.ts`: Enhanced error handling with diagnostic
  information

## Testing

After these changes, when WebSocket errors occur, you should see:

- More informative error messages in the console
- Close codes and reasons that help identify the root cause
- Connection state information for debugging

The enhanced logging will help identify whether the issue is:

- Server not running
- Network connectivity problems
- Invalid URL configuration
- Server-side errors
- Policy violations (CORS, authentication, etc.)
