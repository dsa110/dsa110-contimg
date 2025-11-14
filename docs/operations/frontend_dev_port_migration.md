# Frontend Dev Server Port Migration: 5173 → 3210

**Date:** 2025-01-27  
**Status:** ✅ Completed

---

## Changes Made

### 1. Vite Configuration

**File:** `frontend/vite.config.ts`

- Changed port from `5173` to `3210`
- Added `resolve.dedupe` for date-fns
- Added `optimizeDeps` configuration for date-fns

### 2. Port Configuration

**File:** `config/ports.yaml`

- Updated `frontend_dev.default` from `5173` to `3210`
- Updated `frontend_dev.range` from `[5173, 5173]` to `[3210, 3210]`

### 3. Scripts Updated

**Files:**

- `frontend/scripts/start-dev-safe.sh` - Now uses `CONTIMG_FRONTEND_DEV_PORT`
  (defaults to 3210)
- `scripts/prevent-duplicate-services.sh` - Checks both 3210 and 5173 (migration
  period)
- `scripts/check-duplicate-services.sh` - Updated to check 3210 first

### 4. Package.json

**File:** `frontend/package.json`

- Changed `"dev"` script from `"bash scripts/start-dev-safe.sh || vite"` to
  `"vite"` (direct)
- Added `"dev:safe"` script for safe startup with duplicate prevention

---

## Date-fns Fix

### Root Cause

The `date-fns` package (v4.1.0) uses ESM exports, and Vite was having trouble
resolving it correctly. The package has:

- `"type": "module"` in package.json
- `"module": "index.js"` (ESM)
- `"main": "index.cjs"` (CommonJS)

### Solution

Added to `vite.config.ts`:

```typescript
resolve: {
  // Ensure proper module resolution for date-fns
  dedupe: ['date-fns'],
},
optimizeDeps: {
  include: ['date-fns'],
  esbuildOptions: {
    // Ensure date-fns is treated as ESM
    mainFields: ['module', 'main'],
  },
}
```

This ensures:

1. Vite deduplicates date-fns (prevents multiple versions)
2. date-fns is pre-bundled by Vite
3. ESM module is preferred over CommonJS

---

## Migration Period

During migration, scripts check both ports:

- **Primary:** 3210 (new default)
- **Fallback:** 5173 (old default, for existing instances)

This allows graceful migration without breaking existing setups.

---

## Verification

### Check Current Port

```bash
# Using port manager
python -c "from dsa110_contimg.config.ports import PortManager; print(PortManager().get_port('frontend_dev'))"

# Check running instance
lsof -i :3210
```

### Start Dev Server

```bash
# Direct (uses vite.config.ts port: 3210)
cd frontend && npm run dev

# Safe (with duplicate prevention)
cd frontend && npm run dev:safe
```

---

## Status

✅ **Port changed:** 5173 → 3210  
✅ **Date-fns fix:** Resolve configuration added  
✅ **Scripts updated:** All references updated  
✅ **Migration support:** Both ports checked during transition

---

**The frontend dev server now runs on port 3210 by default!**
