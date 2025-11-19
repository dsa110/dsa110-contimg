# Frontend Restart Instructions

The frontend dev server needs to be restarted to pick up the `.env.development`
changes.

## Current Status

- ✅ API is working correctly on port 8010
- ✅ `.env.development` updated to `VITE_API_URL=http://localhost:8010`
- ✅ Frontend code updated to auto-scan MS files
- ⚠️ Frontend dev server still running with old configuration
- ⚠️ Vite proxy returning 500 errors

## Restart Steps

Since the frontend appears to be running in a container or as a background
process, you'll need to:

1. **Find the frontend process:**

   ```bash
   ps aux | grep -E "vite|npm.*dev"
   ```

2. **Restart the frontend dev server:**
   - If running via npm: `cd frontend && npm run dev`
   - If running in Docker: Restart the container
   - If running as a service: Restart the service

3. **Verify the restart:**
   - Check that Vite picks up the new `.env.development` file
   - Verify API calls go through the proxy correctly
   - Test that MS files appear in the dashboard

## Alternative: Direct API Connection

If the proxy continues to have issues, you can temporarily modify
`frontend/src/api/client.ts` to use the API URL directly:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8010";
```

This bypasses the Vite proxy and connects directly to the API.
