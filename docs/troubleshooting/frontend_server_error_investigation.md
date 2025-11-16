# Frontend Server Error Investigation

## Summary

Analysis of server logs (lines 281-1014) reveals multiple issues affecting the
frontend:

1. **WebSocket 403 Forbidden errors** - Missing `websocket.accept()` call
2. **404 Not Found errors** - Frontend calling endpoints without `/api/` prefix
3. **307 Temporary Redirects** - Automatic redirects from non-prefixed to
   prefixed paths

## Issue 1: WebSocket 403 Forbidden (CRITICAL)

### Problem

All WebSocket connection attempts to `/api/ws/status` are being rejected with
403 Forbidden:

```
INFO:     127.0.0.1:44408 - "WebSocket /ws/status" 403
INFO:     connection rejected (403 Forbidden)
INFO:     connection closed
```

### Root Cause

The WebSocket handler in `/src/dsa110_contimg/api/routers/status.py` (line
107-123) is missing the required `await websocket.accept()` call before
attempting to use the connection.

**Current code:**

```python
@router.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates."""
    from dsa110_contimg.api.websocket_manager import manager

    await manager.connect(websocket)  # ❌ Missing websocket.accept() first!
    try:
        while True:
            data = await websocket.receive_text()
            ...
```

### Fix Required

Add `await websocket.accept()` before calling `manager.connect()`:

```python
@router.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates."""
    from dsa110_contimg.api.websocket_manager import manager

    await websocket.accept()  # ✅ Accept connection first
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except (ConnectionError, RuntimeError, ValueError) as e:
        logger.warning("WebSocket error: %s", e)
        await manager.disconnect(websocket)
```

### Impact

- **High**: All real-time status updates via WebSocket are failing
- Frontend falls back to polling, but WebSocket is the primary mechanism
- Multiple connection attempts logged (every few seconds)

---

## Issue 2: 404 Not Found Errors

### Problem

Multiple endpoints are returning 404 because the frontend is calling them
without the `/api/` prefix:

**Endpoints with 404 errors:**

- `/pipeline/executions/active` → Should be `/api/pipeline/executions/active`
- `/pipeline/metrics/summary` → Should be `/api/pipeline/metrics/summary`
- `/streaming/status` → Should be `/api/streaming/status`
- `/streaming/health` → Should be `/api/streaming/health`
- `/streaming/config` → Should be `/api/streaming/config`
- `/streaming/metrics` → Should be `/api/streaming/metrics`
- `/cache/stats` → Should be `/api/cache/stats`
- `/cache/clear` → Should be `/api/cache/clear`
- `/operations/dlq/items` → Should be `/api/operations/dlq/items`
- `/operations/dlq/stats` → Should be `/api/operations/dlq/stats`
- `/ms` → Should be `/api/ms`
- `/data` → Should be `/api/data`
- `/uvh5` → Should be `/api/uvh5`

### Root Cause

The frontend API client is not consistently using the `/api/` prefix for all
endpoints. Some components are calling endpoints directly without the prefix.

### Evidence from Logs

**Before restart (lines 282-324):**

- Multiple 404s for `/pipeline/executions/active`
- 404s for `/ese/candidates` (should be `/api/ese/candidates`)
- 404s for `/pointing-monitor/status` (should be `/api/pointing-monitor/status`)

**After restart (lines 365+):**

- Most endpoints work correctly with `/api/` prefix
- But some endpoints still return 404 (lines 917-938):
  - `/pipeline/executions/active` - 404
  - `/pipeline/metrics/summary` - 404
  - `/operations/dlq/items` - 404
  - `/operations/dlq/stats` - 404
  - `/streaming/*` endpoints - 404
  - `/cache/stats` - 404
  - `/cache/clear` - 404

### Fix Required

1. **Frontend**: Ensure all API calls use the `/api/` prefix
2. **Backend**: Verify all routes are properly registered with `/api/` prefix

### Impact

- **Medium**: Some dashboard features are not working
- Pipeline monitoring, streaming status, cache management affected

---

## Issue 3: 307 Temporary Redirects

### Problem

Many requests are being redirected from paths without `/api/` to paths with
`/api/`:

```
INFO:     127.0.0.1:46922 - "GET /metrics/system HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:46922 - "GET /api/metrics/system HTTP/1.1" 200 OK
```

### Root Cause

There appears to be middleware or route configuration that automatically
redirects non-prefixed paths to prefixed paths. However, this is inefficient and
should be fixed at the source (frontend).

### Impact

- **Low**: Redirects work but add latency
- Better to fix frontend to use correct paths directly

---

## Recommended Actions

### Priority 1: Fix WebSocket 403 Error

1. Add `await websocket.accept()` to the WebSocket handler
2. Test WebSocket connections
3. Verify real-time updates work

### Priority 2: Fix 404 Errors

1. Audit frontend code for API calls missing `/api/` prefix
2. Update all API client calls to use `/api/` prefix
3. Verify all backend routes are registered with `/api/` prefix

### Priority 3: Remove Redirects

1. Once frontend uses correct paths, remove redirect middleware (if any)
2. This will reduce latency

---

## Files to Modify

1. **`/src/dsa110_contimg/api/routers/status.py`** (line 107-123)
   - Add `await websocket.accept()` before `manager.connect()`

2. **Frontend API client files** (to be identified)
   - Ensure all API calls use `/api/` prefix
   - Check files that call:
     - `/pipeline/executions/active`
     - `/pipeline/metrics/summary`
     - `/streaming/*`
     - `/cache/*`
     - `/operations/dlq/*`
     - `/ms`
     - `/data`
     - `/uvh5`

---

## Testing Checklist

After fixes:

- [ ] WebSocket connections succeed (no 403 errors)
- [ ] Real-time status updates work
- [ ] All API endpoints return 200 OK (no 404s)
- [ ] No 307 redirects in logs
- [ ] Dashboard features load correctly
