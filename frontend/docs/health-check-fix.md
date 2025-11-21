# Docker Health Check Fix

**Date:** 2025-11-14

## Issue

The `dashboard-dev` container was showing "unhealthy" status despite the
dashboard being fully functional.

## Root Cause

The health check was using Node.js's `http` module which was returning 404,
while `curl` successfully returned 200.

## Solution

Changed the health check from:

```yaml
test:
  [
    "CMD",
    "node",
    "-e",
    "require('http').get('http://localhost:3210', (r) =>
    process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () =>
    process.exit(1))",
  ]
```

To:

```yaml
test: ["CMD", "curl", "-f", "http://localhost:3210/"]
```

## Additional Improvements

- Added `start_period: 10s` to allow the Vite dev server time to start before
  health checks begin
- This prevents false negatives during container startup

## Verification

- Container now shows "healthy" status
- Health check passes consistently
- Dashboard remains fully functional

## Date

2025-11-11
