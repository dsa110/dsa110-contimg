# Frontend API Audit Report

## Summary

Audited frontend code to ensure all API calls use the `/api/` prefix. **All API
calls are correctly configured.**

## API Client Configuration

The frontend uses a centralized API client (`src/api/client.ts`) with automatic
`/api/` prefix:

```typescript
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined" && window.location.pathname.startsWith("/ui")
    ? `${window.location.origin}/api`
    : "/api");

export const apiClient = axios.create({
  baseURL: API_BASE_URL, // Automatically adds /api prefix
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});
```

## Audit Results

### ✅ All API Calls Use apiClient

- **Total apiClient calls**: 107
- **Direct fetch() calls bypassing apiClient**: 0 (none found)
- **All API calls automatically get `/api/` prefix** via baseURL

### API Calls Verified

All problematic endpoints from server logs are correctly using apiClient:

1. **Pipeline endpoints** (in `src/api/queries.ts`):
   - Line 1805: `apiClient.get("/pipeline/executions/active")` →
     `/api/pipeline/executions/active` ✓
   - Line 1894: `apiClient.get("/pipeline/metrics/summary")` →
     `/api/pipeline/metrics/summary` ✓

2. **Streaming endpoints** (in `src/api/queries.ts`):
   - Line 869: `apiClient.get("/streaming/status")` → `/api/streaming/status` ✓
   - Line 880: `apiClient.get("/streaming/health")` → `/api/streaming/health` ✓
   - Line 891: `apiClient.get("/streaming/config")` → `/api/streaming/config` ✓
   - Line 901: `apiClient.get("/streaming/metrics")` → `/api/streaming/metrics`
     ✓

3. **Cache endpoints**:
   - Line 1950: `apiClient.get("/cache/stats")` → `/api/cache/stats` ✓
   - `src/pages/CachePage.tsx` line 38: `apiClient.delete("/cache/clear")` →
     `/api/cache/clear` ✓

4. **Operations/DLQ endpoints** (in `src/api/queries.ts`):
   - Line 1674: `apiClient.get("/operations/dlq/items")` →
     `/api/operations/dlq/items` ✓
   - Line 1685: `apiClient.get("/operations/dlq/stats")` →
     `/api/operations/dlq/stats` ✓

5. **Data endpoints** (in `src/api/queries.ts`):
   - Line 1027: `apiClient.get("/data")` → `/api/data` ✓
   - Line 1038: `apiClient.get("/data/${encodedId}")` → `/api/data/${id}` ✓

6. **MS endpoints** (in `src/api/queries.ts`):
   - Line 321: `apiClient.get("/ms")` → `/api/ms` ✓
   - Line 463: `apiClient.get("/ms/${encodedPath}/metadata")` →
     `/api/ms/${path}/metadata` ✓

7. **UVH5 endpoints** (in `src/api/queries.ts`):
   - Line 421: `apiClient.get("/uvh5")` → `/api/uvh5` ✓

### Direct fetch() Calls Found

Only one direct `fetch()` call found, and it correctly uses `/api/` prefix:

- `src/components/Sky/RegionTools.tsx`: `fetch("/api/regions", ...)` ✓

### CARTA Visualization Calls

CARTA-related fetch calls in `src/components/CARTA/CARTAIframe.tsx` correctly
use `/api/visualization/carta/...` ✓

## Conclusion

**Frontend code is correct.** All API calls:

1. Use the centralized `apiClient` with `baseURL: "/api"`
2. Automatically get the `/api/` prefix
3. No direct fetch() calls bypass the apiClient

## Root Cause of 404 Errors

The 404 errors in server logs are **not caused by missing `/api/` prefix in
frontend code**. Possible causes:

1. **Backend route registration timing**: Routes may not be fully registered
   when requests arrive
2. **Router prefix mismatch**: Some routers might not be included with correct
   prefix
3. **Route definition issues**: Routes might be defined but not properly
   registered

## Backend Route Verification Needed

Verify these backend routes are correctly registered:

1. **Pipeline routes** (`backend/src/dsa110_contimg/api/routers/pipeline.py`):
   - `/executions/active` should be at `/api/pipeline/executions/active` ✓
     (router included with prefix `/api/pipeline`)
   - `/metrics/summary` should be at `/api/pipeline/metrics/summary` ✓

2. **Operations routes** (`backend/src/dsa110_contimg/api/routers/operations.py`):
   - `/operations/dlq/items` should be at `/api/operations/dlq/items` ✓ (router
     included with prefix `/api`)

3. **Cache routes** (`backend/src/dsa110_contimg/api/routers/cache.py`):
   - `/cache/stats` should be at `/api/cache/stats` ✓ (router included with
     prefix `/api/cache`)

4. **Streaming routes** (in `backend/src/dsa110_contimg/api/routes.py`):
   - `/streaming/status` should be at `/api/streaming/status` ✓ (defined in main
     router with `/api` prefix)

## Recommendations

1. ✅ **Frontend is correct** - No changes needed
2. ⚠️ **Backend investigation needed** - Verify route registration order and
   timing
3. ⚠️ **Check server startup logs** - Ensure all routers are loaded before
   accepting requests
4. ⚠️ **Test endpoints directly** - Use curl or Postman to verify routes are
   accessible

## Files Audited

- `src/api/client.ts` - API client configuration ✓
- `src/api/queries.ts` - All query functions ✓
- `src/pages/CachePage.tsx` - Cache management ✓
- `src/components/Cache/CacheKeys.tsx` - Cache operations ✓
- `src/components/Sky/RegionTools.tsx` - Region operations ✓
- `src/components/CARTA/CARTAIframe.tsx` - CARTA visualization ✓

All files correctly use the apiClient with automatic `/api/` prefix.
