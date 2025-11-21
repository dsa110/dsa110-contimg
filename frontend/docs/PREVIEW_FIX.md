# Preview Mode Fix

## Problem

When running `npm run preview`, the application showed a blank white screen with
errors:

1. React/Plotly module loading error:
   `Cannot set properties of undefined (setting 'Activity')`
2. CSP violation for socket.io
3. X-Frame-Options meta tag warning

## Root Cause

The production build uses `/ui/` as the base path, but preview mode was serving
from `/`, causing:

- Scripts trying to load from `/ui/assets/...` but served from `/assets/...`
- Module resolution failures
- CSP blocking socket.io connections

## Fixes Applied

### 1. Fixed Preview Base Path

**Updated `vite.config.ts`:**

```typescript
preview: {
  port: parseInt(process.env.VITE_PORT || process.env.PORT || "3210", 10),
  host: "0.0.0.0",
  base: "/ui/", // Always use /ui/ to match production build
},
```

**Updated `package.json`:**

```json
"preview": "vite preview --port ${VITE_PORT:-3210} --host 0.0.0.0 --base /ui/",
```

This ensures preview mode serves from `/ui/` to match the production build.

### 2. Fixed CSP for Socket.IO

**Updated `index.html`:**

```html
connect-src 'self' ws: wss: http://127.0.0.1:8000 http://localhost:8000
http://localhost:2718 ws://localhost:2718;
```

Added `http://localhost:2718` and `ws://localhost:2718` to allow JS9's socket.io
connections.

### 3. Removed X-Frame-Options Meta Tag

**Updated `index.html`:**

- Removed `<meta http-equiv="X-Frame-Options" content="SAMEORIGIN" />`
- Added comment explaining it should be set via HTTP headers

X-Frame-Options can only be set via HTTP headers, not meta tags. The browser
warning was harmless but confusing.

## Usage

### Preview Production Build

```bash
# Preview with /ui/ base path (matches production)
npm run preview

# Access at: http://localhost:3210/ui/
```

**Important**: The URL must include `/ui/` in the path:

- ✅ Correct: `http://localhost:3210/ui/`
- ❌ Wrong: `http://localhost:3210/`

### Development Mode

```bash
# Dev server (uses / base path)
npm run dev

# Access at: http://localhost:3210/
```

## Testing

After these fixes:

1. ✅ Scripts load from correct paths
2. ✅ React/Plotly modules resolve correctly
3. ✅ Socket.io connections allowed by CSP
4. ✅ No X-Frame-Options warnings

## Notes

- Preview mode now matches production base path (`/ui/`)
- CSP allows JS9 socket.io connections
- X-Frame-Options should be set by your web server (nginx, FastAPI, etc.) via
  HTTP headers
