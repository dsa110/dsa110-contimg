# Troubleshooting: API Errors in Dashboard

## Common Issue: Many API Errors in Chrome DevTools

When you see many API errors in the browser console, it's usually due to one of
these issues:

### 1. Path Validation Errors in Directory Browser

**Error:**
`Path /data is outside allowed directories: Absolute paths not allowed: /data`

**Root Cause:**

- The `/api/visualization/browse` endpoint validates paths against specific base
  directories
- It rejects absolute paths by default (`allow_absolute=False`)
- The DirectoryBrowser component may be sending absolute paths when users type
  "data/"

**Allowed Base Directories:**

- `PIPELINE_STATE_DIR` (defaults to `state/`)
- `PIPELINE_STATE_DIR/qa` (defaults to `state/qa/`)
- `PIPELINE_OUTPUT_DIR` (defaults to `/stage/dsa110-contimg/ms`)

**Fix Options:**

**Option A: Use Relative Paths in Frontend**

- Ensure DirectoryBrowser sends relative paths from allowed base directories
- Example: Instead of `/data`, use `../data` or navigate from `state/qa/` to
  `../data`

**Option B: Update Backend to Allow Absolute Paths**

- Modify `browse_directory` in `visualization_routes.py` to set
  `allow_absolute=True`:

```python
target_path = validate_path(path, base_dir, allow_absolute=True)
```

**Option C: Add `/data` as Allowed Base Directory**

- Add `/data` to the list of allowed base directories in `browse_directory`:

```python
data_dir = Path("/data")
for base_dir in [base_state, qa_base, output_dir, data_dir]:
    try:
        target_path = validate_path(path, base_dir, allow_absolute=True)
        break
    except ValueError as e:
        validation_errors.append(str(e))
        continue
```

### 2. Missing API Endpoints

**Symptom:** 404 errors for various API endpoints

**Common Missing Endpoints:**

- `/api/streaming/*` - Streaming control endpoints
- `/api/mosaics/*` - Mosaic creation/query endpoints
- `/api/sources/*` - Source search endpoints
- `/api/jobs/*` - Job submission endpoints
- `/api/batch/*` - Batch job endpoints
- `/api/operations/*` - Operations monitoring endpoints
- `/api/events/*` - Event statistics endpoints
- `/api/cache/*` - Cache statistics endpoints

**Check if Endpoint Exists:**

```bash
# Test endpoint directly
curl http://localhost:8000/api/<endpoint>

# Check backend routes
grep -r "@router.get\|@router.post" src/dsa110_contimg/api/ --include="*.py"
```

**Fix:** Ensure backend API routes are properly registered in `routes.py`

### 3. Backend Not Running or Not Accessible

**Symptom:** All API calls fail with connection errors

**Check:**

```bash
# Verify backend is running
ps aux | grep uvicorn

# Test backend health
curl http://localhost:8000/api/health

# Test through Vite proxy
curl http://localhost:5173/api/health
```

**Fix:**

```bash
cd /data/dsa110-contimg
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6
uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload
```

### 4. CORS Errors

**Symptom:** `Access-Control-Allow-Origin` errors in console

**Fix:** Ensure backend CORS middleware is configured correctly in `routes.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. Circuit Breaker Errors

**Symptom:** `Service temporarily unavailable. Please try again later.`

**Root Cause:** Frontend circuit breaker has opened due to too many failed
requests

**Fix:**

- Wait 30 seconds for circuit breaker to reset
- Or fix underlying API errors causing the failures
- Circuit breaker settings in `frontend/src/api/client.ts`:
  - `failureThreshold: 5` - Opens after 5 failures
  - `resetTimeout: 30000` - Resets after 30 seconds

### 6. Timeout Errors

**Symptom:** Request timeout errors (120 second timeout)

**Fix:**

- Check if backend is processing requests slowly
- Increase timeout in `apiClient` configuration if needed
- Check backend logs for slow queries

## Quick Diagnostic Steps

1. **Open Chrome DevTools (F12)**
   - Go to Network tab
   - Filter by "Failed" requests
   - Check the error message and status code

2. **Check Console Tab**
   - Look for JavaScript errors
   - Check for API error messages
   - Note the endpoint and error details

3. **Test Backend Directly**

   ```bash
   curl http://localhost:8000/api/health
   curl http://localhost:8000/api/status
   ```

4. **Test Through Vite Proxy**

   ```bash
   curl http://localhost:5173/api/health
   curl http://localhost:5173/api/status
   ```

5. **Check Backend Logs**
   - Look at the terminal where uvicorn is running
   - Check for Python exceptions or validation errors

## Common Error Patterns

### Pattern 1: Path Validation

```
Error: Path /data is outside allowed directories
Solution: Use relative paths or update backend validation
```

### Pattern 2: 404 Not Found

```
Error: 404 Not Found for /api/some-endpoint
Solution: Check if endpoint exists in backend routes
```

### Pattern 3: 500 Internal Server Error

```
Error: 500 Internal Server Error
Solution: Check backend logs for Python exceptions
```

### Pattern 4: Network Error

```
Error: Network Error / Failed to fetch
Solution: Check if backend is running and accessible
```

## Prevention

1. **After Backend Changes:**
   - Test all API endpoints manually
   - Check that routes are properly registered
   - Verify path validation logic

2. **After Frontend Changes:**
   - Test API calls in browser DevTools
   - Verify paths are in correct format
   - Check for CORS issues

3. **Regular Checks:**
   - Monitor browser console for errors
   - Check backend logs regularly
   - Test critical endpoints after deployments
