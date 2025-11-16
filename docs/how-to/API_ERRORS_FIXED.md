# API Errors - Diagnosis and Fixes

## Issues Found and Fixed

### 1. Path Validation Issue in `/api/visualization/browse` ✓ FIXED

**Problem:**

- The endpoint was rejecting all absolute paths, including
  `/stage/dsa110-contimg/ms` (the default output directory)
- Error: `"Absolute paths not allowed: /stage/dsa110-contimg/ms"`

**Root Cause:**

- `validate_path()` was called with `allow_absolute=False` by default
- This prevented browsing absolute paths even when they were within allowed base
  directories

**Fix Applied:**

- Modified `browse_directory()` in
  `src/dsa110_contimg/api/visualization_routes.py`
- Now checks if the base directory is absolute, and if so, allows absolute paths
- Code change:

```python
# Allow absolute paths if the base directory is absolute
# This is necessary because output_dir is typically an absolute path
allow_absolute = Path(base_dir).is_absolute()
target_path = validate_path(path, base_dir, allow_absolute=allow_absolute)
```

**Status:** Fixed in code. Backend needs to be restarted to apply changes.

### 2. Diagnostic Results

Most API endpoints are working correctly:

- ✓ `/api/status`
- ✓ `/api/health/summary`
- ✓ `/api/metrics/system`
- ✓ `/api/streaming/*` (all endpoints)
- ✓ `/api/pipeline/*` (all endpoints)
- ✓ `/api/events/*` (all endpoints)
- ✓ `/api/cache/*` (all endpoints)
- ✓ `/api/operations/*` (all endpoints)
- ✓ `/api/pointing-monitor/status`

## How to Identify Your Specific API Errors

### Step 1: Open Chrome DevTools

1. Press `F12` or right-click → "Inspect"
2. Go to the **Network** tab
3. Refresh the page (F5)
4. Filter by "Failed" or "XHR" requests

### Step 2: Check Error Details

For each failed request:

1. Click on the failed request
2. Check the **Status** column (404, 500, 403, etc.)
3. Go to the **Response** tab to see the error message
4. Go to the **Headers** tab to see the full URL

### Step 3: Common Error Patterns

#### Pattern 1: 404 Not Found

```
Status: 404
Response: {"detail": "Not found"}
```

**Meaning:** Endpoint doesn't exist or route not registered **Fix:** Check if
endpoint is defined in backend routes

#### Pattern 2: 403 Forbidden

```
Status: 403
Response: {"detail": "Path ... is outside allowed directories"}
```

**Meaning:** Path validation failed (should be fixed now) **Fix:** Restart
backend to apply the path validation fix

#### Pattern 3: 422 Validation Error

```
Status: 422
Response: {"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
```

**Meaning:** Request parameters are invalid **Fix:** Check the request
parameters match the API specification

#### Pattern 4: 500 Internal Server Error

```
Status: 500
Response: {"detail": "Internal server error"}
```

**Meaning:** Backend Python exception **Fix:** Check backend logs for Python
traceback

#### Pattern 5: Network Error / Failed to Fetch

```
Status: (failed) or CORS error
```

**Meaning:** Backend not running or CORS misconfiguration **Fix:**

- Check if backend is running: `ps aux | grep uvicorn`
- Check backend logs
- Verify CORS settings in `routes.py`

### Step 4: Export Error List

You can export the errors from DevTools:

1. In Network tab, right-click on the failed requests
2. Select "Save all as HAR with content"
3. Share the HAR file or list the errors

## Restart Backend to Apply Fixes

After the path validation fix, restart the backend:

```bash
# Kill existing backend
pkill -f uvicorn

# Restart backend
cd /data/dsa110-contimg
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6
uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload
```

## Test the Fix

After restarting, test the visualization endpoint:

```bash
# Test with absolute path (should work now)
curl "http://localhost:8000/api/visualization/browse?path=/stage/dsa110-contimg/ms"

# Test with relative path
curl "http://localhost:8000/api/visualization/browse?path=state"
```

## Next Steps

1. **Restart the backend** to apply the path validation fix
2. **Check Chrome DevTools** for remaining errors
3. **Share specific error messages** if issues persist:
   - Status code
   - Error message from Response tab
   - Endpoint URL from Headers tab

## Diagnostic Tools

Use the diagnostic script to test all endpoints:

```bash
cd /data/dsa110-contimg
bash docs/how-to/DIAGNOSE_API_ERRORS.sh
```

This will test all common endpoints and show which ones are failing.
