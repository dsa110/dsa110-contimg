# CASA Log Handling Investigation

**Date**: 2025-11-16  
**Issue**: CASA logs are being written to workspace root
(`/data/dsa110-contimg/src/`) instead of the designated log directory
(`/data/dsa110-contimg/state/logs/`)

## Key Findings

### How CASA Logging Works

1. **CASA writes logs to the current working directory (CWD)** when modules are
   first imported
2. **CASA does NOT respect environment variables** like `CASALOGDIR` or
   `CASA_LOG_DIR`
3. **Logs are created at import time**, not at runtime
4. **Once CASA is imported, changing CWD doesn't affect where new logs go** -
   logs are tied to the import location

### Root Cause Analysis

The problem occurs because:

1. **Module-level CASA imports** happen before we can set the CWD
   - Files with module-level imports:
     - `dsa110_contimg/beam/vp_builder.py` - imports `casatools` at module level
       (lines 16-18)
     - `dsa110_contimg/calibration/applycal.py` - imports `casatasks` at module
       level
     - `dsa110_contimg/calibration/flagging.py` - imports `casatasks` at module
       level
     - `dsa110_contimg/utils/coordinates.py` - imports `casatools` at module
       level
     - `dsa110_contimg/utils/fringestopping.py` - imports `casatools` at module
       level

2. **API route imports** happen inside route functions, but:
   - If CASA was already imported at module level elsewhere, the log location is
     already set
   - The CWD might not be set correctly when routes are called
   - `setup_casa_environment()` changes CWD globally, which is problematic for
     concurrent web requests

3. **Current setup** in `create_app()`:
   - Calls `setup_casa_environment()` which changes CWD to log directory
   - But this happens AFTER some modules may have already imported CASA
   - Global CWD change affects all API requests (not ideal for concurrent
     requests)

### Test Results

```bash
# Test: Import CASA in root directory
CWD before import: /data/dsa110-contimg/src
Logs before: 28
CASA imported
Logs after: 29
:warning_sign::variation_selector-16:  New log created in root directory!
```

**Conclusion**: CASA creates logs in whatever directory is the CWD when it's
first imported.

## Solution Options

### Option 1: Use Context Manager in API Routes (Recommended)

**Approach**: Wrap all CASA operations with `casa_log_environment()` context
manager

**Pros**:

- Granular control - only changes CWD during CASA operations
- Doesn't affect global state
- Safe for concurrent requests
- Can be nested safely

**Cons**:

- Requires code changes in all API routes that use CASA
- More verbose

**Implementation**:

```python
from dsa110_contimg.utils.cli_helpers import casa_log_environment

@router.get("/api/ms/{ms_path}/metadata")
def get_ms_metadata(ms_path: str) -> MSMetadata:
    with casa_log_environment():
        from casatools import table
        # ... CASA operations ...
```

### Option 2: Set CWD Very Early in Application Lifecycle

**Approach**: Set CWD to log directory before importing ANY modules that might
import CASA

**Pros**:

- Minimal code changes
- Works for all CASA imports

**Cons**:

- Global CWD change affects entire application
- Problematic for concurrent web requests
- May break other code that relies on CWD

**Implementation**:

```python
# In main.py or __init__.py, before any imports
import os
os.chdir('/data/dsa110-contimg/state/logs')
```

### Option 3: Move Module-Level Imports to Function Level

**Approach**: Change all module-level CASA imports to function-level imports

**Pros**:

- Allows setting CWD before each import
- More control over when CASA is imported

**Cons**:

- Requires changes to multiple files
- May impact performance (repeated imports)
- Some code may need CASA at module level for type hints

**Implementation**:

```python
# Before (module level):
from casatools import table

# After (function level):
def my_function():
    from casatools import table
    # ... use table ...
```

### Option 4: Hybrid Approach (Recommended for Production)

**Approach**: Combine Option 1 and Option 3

1. **Move critical module-level imports to function level** (especially in
   `vp_builder.py`)
2. **Use context manager in API routes** for all CASA operations
3. **Set CWD early in CLI scripts** using `setup_casa_environment()`

**Pros**:

- Best of both worlds
- Safe for concurrent requests
- Works for both CLI and API

**Cons**:

- Requires more code changes
- Need to identify all module-level imports

## Recommended Implementation Plan

### Phase 1: Immediate Fix (API Routes)

1. Wrap all CASA operations in API routes with `casa_log_environment()` context
   manager
2. Files to update:
   - `dsa110_contimg/api/routes.py` - Multiple routes use CASA
   - `dsa110_contimg/api/visualization_routes.py` - Multiple routes use CASA
   - `dsa110_contimg/api/batch_jobs.py` - Uses CASA

### Phase 2: Module-Level Import Fix

1. Move module-level CASA imports to function level in:
   - `dsa110_contimg/beam/vp_builder.py`
   - `dsa110_contimg/calibration/applycal.py`
   - `dsa110_contimg/calibration/flagging.py`
   - `dsa110_contimg/utils/coordinates.py`
   - `dsa110_contimg/utils/fringestopping.py`

### Phase 3: Cleanup

1. Run cleanup script to move existing logs
2. Monitor for new logs in root directory
3. Update documentation

## Files Requiring Changes

### High Priority (Module-Level Imports)

- `dsa110_contimg/beam/vp_builder.py` - Lines 16-18
- `dsa110_contimg/calibration/applycal.py` - Module-level import
- `dsa110_contimg/calibration/flagging.py` - Module-level import
- `dsa110_contimg/utils/coordinates.py` - Module-level import
- `dsa110_contimg/utils/fringestopping.py` - Module-level import

### Medium Priority (API Routes)

- `dsa110_contimg/api/routes.py` - Multiple routes (lines 3359, 3541, 3811,
  4977, etc.)
- `dsa110_contimg/api/visualization_routes.py` - Multiple routes (lines 1114,
  1144, 1234, etc.)
- `dsa110_contimg/api/batch_jobs.py` - Uses CASA

## Testing

After implementing fixes, verify:

1. No new CASA logs appear in workspace root
2. All CASA logs go to `/data/dsa110-contimg/state/logs/`
3. API routes still function correctly
4. CLI scripts still function correctly
5. Concurrent API requests don't interfere with each other

## Related Files

- `dsa110_contimg/utils/cli_helpers.py` - Contains `setup_casa_environment()`
  and `casa_log_environment()`
- `dsa110_contimg/utils/tempdirs.py` - Contains `derive_casa_log_dir()`
- `scripts/cleanup_casa_logs.py` - Cleanup script for existing logs
