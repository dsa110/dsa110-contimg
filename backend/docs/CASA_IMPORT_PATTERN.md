# CASA Import Pattern Guide

## Overview

CASA (Common Astronomy Software Applications) writes log files (`casa-YYYYMMDD-HHMMSS.log`) to the **current working directory** whenever `casatasks` or `casatools` modules are first imported. This can pollute the repository root with log files.

This guide documents the standard pattern used in this codebase to ensure CASA log files are written to the centralized logs directory (`/data/dsa110-contimg/state/logs/casa/`) instead of wherever the script happens to be running.

## The Problem

```python
# BAD: This creates a casa-*.log file in the current working directory
from casatasks import tclean
tclean(...)
```

When this import runs, CASA immediately writes a log file to `os.getcwd()`. If you're running from the repo root, you get log pollution.

## The Solution

### Option 1: Use `casa_log_environment()` Context Manager (Recommended)

Wrap CASA imports and calls inside the `casa_log_environment()` context manager:

```python
# GOOD: CASA logs go to the centralized logs directory
try:
    from dsa110_contimg.utils.tempdirs import casa_log_environment
    with casa_log_environment():
        from casatasks import tclean
except ImportError:
    # Fallback if tempdirs not available
    from casatasks import tclean

# Now use tclean normally
tclean(...)
```

The context manager:

1. Changes CWD to `/data/dsa110-contimg/state/logs/casa/`
2. Yields control for the import/execution
3. Restores the original CWD when done

### Option 2: Lazy Import with Caching

For modules that need CASA tasks in multiple functions, use a lazy import pattern:

```python
# At module level
_casa_gaincal = None

def _get_gaincal():
    """Lazily import gaincal with CASA log environment protection."""
    global _casa_gaincal
    if _casa_gaincal is None:
        try:
            from dsa110_contimg.utils.tempdirs import casa_log_environment
            with casa_log_environment():
                from casatasks import gaincal
                _casa_gaincal = gaincal
        except ImportError:
            from casatasks import gaincal
            _casa_gaincal = gaincal
    return _casa_gaincal

def my_function(ms_path):
    gaincal = _get_gaincal()
    gaincal(vis=ms_path, ...)
```

### Option 3: Early CWD Setup (For Scripts/Benchmarks)

For standalone scripts or benchmarks, set up the CASA log directory at the start:

```python
import os
import sys

# Set up CASA log directory before any CASA imports
try:
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    _casa_log_dir = derive_casa_log_dir()
    os.chdir(str(_casa_log_dir))
except (ImportError, OSError):
    pass  # Best effort

# Now CASA imports are safe
from casatasks import tclean
```

## Key Modules

### `dsa110_contimg.utils.tempdirs`

- `casa_log_environment()` - Context manager for CASA operations
- `derive_casa_log_dir()` - Returns the centralized CASA logs directory
- `setup_casa_logging()` - Sets CASALOGFILE environment variable

### `dsa110_contimg.utils.casa_init`

- `ensure_casa_path()` - Ensures CASAPATH is set correctly
- `setup_casa_log_directory()` - Sets up CASA logging (called at module import)
- `cleanup_stray_casa_logs()` - Utility to find/move stray log files

## Where CASA Logs Should Go

All CASA log files should be written to:

```text
/data/dsa110-contimg/state/logs/casa/
```

This path is configured via `settings.paths.casa_logs_dir` and can be overridden with the `CONTIMG_CASA_LOGS_DIR` environment variable.

## Checking for Stray Logs

To find CASA log files that have escaped to the wrong location:

```bash
# Find stray logs in the backend directory
find /data/dsa110-contimg/backend -name "casa-*.log" -type f

# Move them to the correct location
python -c "
from dsa110_contimg.utils.casa_init import cleanup_stray_casa_logs
found = cleanup_stray_casa_logs(delete=False)  # Set delete=True to remove instead
print(f'Found and moved {len(found)} stray log files')
"
```

## Troubleshooting: `.fuse_hidden*` Files

### Symptom

You see files like `.fuse_hidden00027adf00000101` appearing in `/data/dsa110-contimg/backend/`.

### Cause

These are **CASA log files** that have been deleted but are still held open by a running process. The `/data` directory is mounted as a FUSE filesystem (`fuseblk` - typically NTFS or exFAT). When a file is deleted on a FUSE filesystem while still open, it gets renamed to `.fuse_hidden*` instead of being immediately removed.

### Diagnosis

```bash
# Check filesystem type
mount | grep /data
# Output: /dev/sda1 on /data type fuseblk (...)

# Find which process has the file open
lsof +D /data/dsa110-contimg/backend/ 2>/dev/null | grep fuse_hidden

# Example output:
# python  17264 ubuntu  3w  REG  8,1  281  53049  /data/.../backend/.fuse_hidden00027adf00000101

# Check what the process is doing
ps aux | grep 17264
cat /proc/17264/cmdline | tr '\0' ' '
```

### Root Cause (Historical)

Prior to December 2024, `runtime_safeguards.py` called `check_casa6_python()` at **module import time**, which triggered `casatools` import and caused CASA to write log files to the current working directory.

The fix was:

1. **`casa_init.py`**: Added `_setup_casa_log_directory_early()` that runs at the top of the module, changing CWD to the logs directory _before_ any CASA imports can happen.

2. **`runtime_safeguards.py`**: Removed the module-level `check_casa6_python()` call. The check is now performed lazily only when `@require_casa6_python` decorated functions are called.

### Solution

1. **Restart the offending process** - The `.fuse_hidden*` file will disappear once the process releases the file handle:

   ```bash
   # If it's the ABSURD worker
   sudo systemctl restart absurd-worker
   ```

2. **Verify the fix is working** - After restarting, no new `.fuse_hidden*` or `casa-*.log` files should appear in the backend directory:

   ```bash
   # Watch for new files
   inotifywait -m -e create /data/dsa110-contimg/backend/

   # Or check after some time
   ls -la /data/dsa110-contimg/backend/.fuse_hidden* /data/dsa110-contimg/backend/casa-*.log 2>/dev/null
   ```

3. **Clean up old files** - Once processes are restarted:

   ```bash
   rm -f /data/dsa110-contimg/backend/.fuse_hidden*
   ```

### Prevention

The current codebase prevents this issue by:

1. **Early log directory setup**: `casa_init.py` changes CWD to the logs directory at module import time, before any CASA imports.

2. **Lazy CASA checks**: The `@require_casa6_python` decorator only imports CASA when decorated functions are actually called.

3. **Protected imports**: All CASA task imports use `casa_log_environment()` context manager.

## Adding New CASA Task Usage

When adding new code that uses `casatasks` or `casatools`:

1. **Never** use bare `from casatasks import X` at module level
2. **Always** wrap imports in `casa_log_environment()` or use the lazy import pattern
3. **Test** that running your code doesn't create log files in the CWD

## Why This Matters

- Log pollution makes the repo harder to navigate
- Git status shows many untracked files
- Disk space accumulates with stray logs
- CI/CD environments may fail with permission errors
- Consistent log location enables monitoring and cleanup

## Related Documentation

- `docs/dev-notes/analysis/casa_log_handling_investigation.md` - Original investigation
- `src/dsa110_contimg/utils/tempdirs.py` - Implementation details
- `src/dsa110_contimg/utils/casa_init.py` - CASA initialization utilities
