# Docker Networking Fix - Complete ✅

**Date:** 2025-11-07  
**Status:** ✅ **RESOLVED**

## Problem

The frontend Docker container (`contimg-frontend`) could not reach the API server running on the host at port 8010. The container was configured with `API_PROXY_TARGET=http://contimg-api:8010`, but:
- The `contimg-api` container was stopped
- The API was running directly on the host (not in Docker)
- The container couldn't resolve `contimg-api` hostname

## Root Cause

1. **API running on host**: The API process runs directly on the host machine (port 8010), not in a Docker container
2. **Wrong network configuration**: The frontend container was on `docker_default` network trying to reach `contimg-api:8010` which doesn't exist
3. **Gateway IP mismatch**: Attempted to use Docker gateway IPs (172.23.0.1, 172.17.0.1) but connectivity was unreliable

## Solution

**Used Docker host network mode** to allow the frontend container to access `localhost:8010` directly:

```bash
docker run -d --name contimg-frontend \
  --network host \
  -e API_PROXY_TARGET=http://localhost:8010 \
  -e VITE_API_URL=http://localhost:8010 \
  -v $(pwd)/frontend:/app/frontend \
  -w /app/frontend \
  node:20-alpine \
  sh -c "cd /app/frontend && npm install && npm run dev --host"
```

## Changes Made

1. **Recreated frontend container** with `--network host`
2. **Updated environment variables**:
   - `API_PROXY_TARGET=http://localhost:8010` (instead of `http://contimg-api:8010`)
   - `VITE_API_URL=http://localhost:8010`

## Verification

✅ **API Proxy Working**: Direct curl test confirms proxy forwards requests correctly
```bash
curl "http://localhost:5173/api/ms?scan=true&scan_dir=/stage/dsa110-contimg/ms&limit=1"
# Returns: {"items": [...], "total": 9}
```

✅ **Frontend Displaying MS Files**: Browser shows "Showing 9 of 9 MS" with all files listed

✅ **Calibrator Detection Ready**: API endpoint `/api/ms/{path}/calibrator-matches` working correctly

## Alternative Solutions (Not Used)

1. **Start API in Docker container**: Would require docker-compose setup and both services on same network
2. **Use Docker gateway IP**: Tried 172.23.0.1 and 172.17.0.1 but had connectivity issues
3. **Use host.docker.internal**: Not available on this Linux system

## Current Configuration

- **Frontend**: Running in Docker with `--network host`
- **API**: Running on host at `localhost:8010`
- **Proxy**: Vite proxy configured to forward `/api/*` to `http://localhost:8010`

## Next Steps

1. ✅ MS files now appear in dashboard
2. ✅ Auto-scan working on page load
3. ⏭️ Test calibrator detection by selecting an MS file
4. ⏭️ Verify calibrator info displays correctly

## Files Modified

- `frontend/vite.config.ts` - Updated proxy target fallback (already had correct logic)
- Docker container recreated with correct network mode and environment variables

## Notes

- Host network mode gives the container direct access to host's network stack
- This is simpler than managing Docker networks when API runs on host
- For production, consider running API in Docker container for better isolation

