# Frontend Dev Server Fix Summary

**Date:** 2025-01-27  
**Issues Fixed:** Port migration + date-fns errors + production vs dev conflict

---

## Problems Identified

### 1. Port Conflict

- **Issue:** `manage-services.sh start dashboard` was starting production build
  (serve -s dist) instead of dev server
- **Root Cause:** Script checks for `dist/` directory and prioritizes production
  build
- **Impact:** User couldn't access dev server on port 3210

### 2. Date-fns Import Errors

- **Issue:** Vite couldn't resolve `date-fns` imports
- **Root Cause:** date-fns v4.1.0 uses ESM exports, Vite needed proper
  configuration
- **Impact:** Components using date-fns failed to load (500 errors)

### 3. Port Migration

- **Issue:** Dev server was on 5173, needed to move to 3210
- **Root Cause:** Port assignment needed updating
- **Impact:** Inconsistent port usage

---

## Fixes Applied

### 1. Fixed manage-services.sh

**File:** `scripts/manage-services.sh`

**Change:** Removed production build check, always use dev server for
`start dashboard`

```bash
# Before: Checked for dist/ and started production build
if [ -d "dist" ]; then
    # Start production build
else
    # Start dev server
fi

# After: Always start dev server
echo "Using development server (vite dev)..."
npm run dev -- --host 0.0.0.0 --port $chosen_port
```

**Result:** `./scripts/manage-services.sh start dashboard` now always starts the
dev server.

### 2. Fixed date-fns Resolution

**File:** `frontend/vite.config.ts`

**Added:**

```typescript
resolve: {
  dedupe: ['date-fns'],
},
optimizeDeps: {
  include: ['date-fns'],
  esbuildOptions: {
    mainFields: ['module', 'main'],
  },
}
```

**Result:** date-fns now resolves correctly, imports work.

### 3. Port Migration: 5173 → 3210

**Files Updated:**

- `frontend/vite.config.ts` - Port changed to 3210
- `config/ports.yaml` - frontend_dev.default = 3210
- `frontend/scripts/start-dev-safe.sh` - Uses CONTIMG_FRONTEND_DEV_PORT
- `scripts/prevent-duplicate-services.sh` - Checks both ports (migration)

**Result:** Dev server now runs on port 3210 by default.

---

## Verification

### Server Status

```bash
# Check if running
lsof -i :3210

# Test HTTP
curl http://127.0.0.1:3210

# Check for errors
curl http://127.0.0.1:3210/src/components/Pipeline/ExecutionHistory.tsx | grep date-fns
```

### Expected Results

- ✅ Server listening on 0.0.0.0:3210
- ✅ HTTP 200 OK response
- ✅ date-fns imports resolve correctly
- ✅ No duplicate instances

---

## Usage

### Start Dev Server

```bash
# Method 1: Direct
cd frontend && npm run dev

# Method 2: Service management (now uses dev server)
./scripts/manage-services.sh start dashboard

# Method 3: Safe startup (with duplicate prevention)
cd frontend && npm run dev:safe
```

### Access Dashboard

- **URL:** http://localhost:3210
- **Network:** http://10.42.0.148:3210 (from other machines on network)

---

## Status

✅ **Port Migration:** Complete (5173 → 3210)  
✅ **Date-fns Fix:** Complete (resolve.dedupe + optimizeDeps)  
✅ **Production/Dev Conflict:** Fixed (always use dev server)  
✅ **Server Running:** Verified on port 3210

---

**The frontend dev server is now correctly configured and running on port
3210!**
