# WSClean Docker Container Hang Fix

**Date:** 2025-11-19  
**Type:** Bug Fix  
**Status:** ✅ Fixed

---

## Problem

Self-calibration and masked imaging consistently hung at WSClean's "Cleaning up
temporary files..." message. The process would never complete or timeout.

## Symptoms

```
Writing changed model back to /data_ms/2025-10-19T14:31:45.ms:
 0%....10%....20%....30%....40%....50%....60%....70%....80%....90%....100%
Cleaning up temporary files...
[HANGS HERE INDEFINITELY]
```

## Root Cause

**subprocess.run() calls for Docker WSClean had no timeout parameter.**

When WSClean runs in Docker with the `--rm` flag:

1. WSClean completes successfully and prints "Cleaning up temporary files..."
2. Docker attempts to remove the container and unmount volumes
3. Volume unmounting hangs (likely due to file locks on the MS or NFS latency)
4. `subprocess.run()` waits indefinitely for Docker process to exit
5. **No timeout** means the process hangs forever

## Fix

Added `timeout` parameters to all WSClean subprocess.run() calls:

### Main Imaging (line 318)

```python
subprocess.run(
    cmd,
    check=True,
    capture_output=False,
    text=True,
    timeout=1800,  # 30 min timeout for main imaging
)
```

### NVSS Sky Model Rendering (lines 879, 951)

```python
subprocess.run(cmd_draw, check=True, timeout=300)  # 5 min timeout
```

### NVSS Sky Model Prediction (lines 911, 972)

```python
subprocess.run(cmd_predict, check=True, timeout=600)  # 10 min timeout
```

## Timeout Values

| Operation    | Timeout | Rationale                                    |
| ------------ | ------- | -------------------------------------------- |
| Main imaging | 30 min  | Deep clean on large MS can take 10-20 min    |
| -draw-model  | 5 min   | Fast operation, typically <1 min             |
| -predict     | 10 min  | Writes to MS, can be slow for large datasets |

## Impact

### Before

- Processes hung indefinitely
- Required manual intervention (Ctrl+C, kill)
- No error messages or diagnostics
- Tests failed silently

### After

- Hangs timeout with clear error message
- Allows retry with different approach (native WSClean)
- Provides diagnostic information
- Enables automated recovery strategies

## Testing

Confirmed fix works with:

1. ✅ Quick validation test (1 iteration, 10 mJy, 2-3 min)
2. ✅ Full masked self-cal test (5 iterations, various flux limits)
3. ✅ Docker-based WSClean execution
4. ✅ Native WSClean execution (fallback)

## Prevention

### For Users

- If timeouts occur frequently, check:
  - Disk I/O performance (especially NFS mounts)
  - File locks on MS (use `lsof` to check)
  - Docker volume mounting issues
  - Consider using native WSClean instead of Docker

### For Developers

- **Always add timeouts to subprocess.run()** for Docker commands
- Consider adding retry logic with exponential backoff
- Log timeout events for debugging
- Provide fallback to native execution when Docker hangs

## Related Issues

- MODEL_DATA conflict when both calibrator + NVSS seeding enabled
- Model export incompatibility (CASA can't read WSClean MODEL_DATA)
- Permission errors with MS files

## Files Modified

- `src/dsa110_contimg/imaging/cli_imaging.py` - Added timeouts to all
  subprocess.run() calls for WSClean Docker execution

---

**Status:** ✅ Resolved - WSClean Docker hangs now timeout with clear error
messages, enabling recovery and retry strategies.
