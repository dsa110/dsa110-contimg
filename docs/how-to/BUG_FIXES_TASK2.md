# Bug Fixes: Task 2 Infrastructure Issues

## Summary

Fixed two critical bugs identified in the infrastructure improvements:

1. **Systemd Service ReadWritePaths**: Missing write access for build process
2. **SQLite Connection Resource Leak**: Connection not closed on exception

## Bug 1: Systemd Service ReadWritePaths

### Issue

The `ReadWritePaths` directive only included
`/data/dsa110-contimg/frontend/dist`, but the build script (`ExecStartPre`)
needs write access to the entire `/data/dsa110-contimg/frontend` directory for:

- Installing/updating `node_modules`
- Updating `package-lock.json`
- Creating build artifacts
- Temporary files during build

With `ProtectSystem=strict`, the build would fail with permission denied errors.

### Fix

**File:** `ops/systemd/dsa110-contimg-dashboard.service`

**Changed:**

```ini
# Before
ReadWritePaths=/data/dsa110-contimg/state/logs /data/dsa110-contimg/frontend/dist

# After
ReadWritePaths=/data/dsa110-contimg/state/logs /data/dsa110-contimg/frontend
```

**Impact:** Build script can now write to `node_modules`, `package-lock.json`,
and other frontend directory files during the build process.

## Bug 2: SQLite Connection Resource Leak

### Issue

In the health check endpoint, if `conn.execute("SELECT 1").fetchone()` raised an
exception, the SQLite connection opened on line 6510 would never be closed,
causing a resource leak. Each failed health check would leave an unclosed
connection.

### Fix

**File:** `src/dsa110_contimg/api/routes.py`

**Changed:**

```python
# Before
conn = sqlite3.connect(str(db_path), timeout=1.0)
conn.execute("SELECT 1").fetchone()
conn.close()
health_info["database"] = "connected"

# After
with sqlite3.connect(str(db_path), timeout=1.0) as conn:
    conn.execute("SELECT 1").fetchone()
health_info["database"] = "connected"
```

**Impact:** Connection is now guaranteed to be closed in all code paths
(success, exception, or early return) using Python's context manager protocol.

## Verification

### Bug 1 Verification

- ReadWritePaths now includes `/data/dsa110-contimg/frontend`
- Build script has necessary write permissions
- No permission denied errors during build

### Bug 2 Verification

- Context manager ensures connection closure
- No resource leaks on exceptions
- Proper cleanup in all code paths

## Testing

To verify the fixes:

1. **Test Build Permissions:**

   ```bash
   # Should succeed without permission errors
   sudo systemctl start dsa110-contimg-dashboard.service
   sudo journalctl -u dsa110-contimg-dashboard.service -f
   ```

2. **Test Health Check:**
   ```bash
   # Should work without connection leaks
   for i in {1..100}; do curl -s http://localhost:8000/health > /dev/null; done
   # Check for connection leaks (should see no increase in open file descriptors)
   ```

## Files Modified

- `ops/systemd/dsa110-contimg-dashboard.service` - Fixed ReadWritePaths
- `src/dsa110_contimg/api/routes.py` - Fixed SQLite connection resource leak

## Related Issues

These bugs were identified during code review of the infrastructure
improvements. Both are critical for production reliability:

- Bug 1 prevents successful builds in production
- Bug 2 causes resource exhaustion over time
