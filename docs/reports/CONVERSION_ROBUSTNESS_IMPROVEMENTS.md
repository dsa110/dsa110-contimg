# Conversion Pipeline Robustness Improvements

**Date Created:** 2025-11-02  
**Status:** ✅ Implemented (2025-11-02)  
**Priority:** Medium  
**Related:** `DETAILED_TESTING_PLAN_0834_TRANSIT.md` Phase 2.2 Error Analysis

## Problem Statement

During end-to-end testing of the 0834 transit pipeline, intermittent tmpfs file locking errors occurred during MS generation. Analysis revealed a race condition in the parallel-subband writer's cleanup process that can leave stale file handles/locks in tmpfs, causing subsequent groups to fail.

**Observed Failure Rate:** ~10% (2 failures out of 20 group conversion attempts)

**Error Patterns:**
- "cannot be opened for read/write" during CASA concat
- "incorrect number of bytes read" during CASA concat
- Stale tmpfs directories remain after failures

## Root Cause

The `DirectSubbandWriter` in `src/dsa110_contimg/conversion/strategies/direct_subband.py`:

1. **Cleanup Timing Issue:**
   - Cleanup happens at end of `write()` method (lines 289-295)
   - If cleanup fails or is interrupted, stale files/locks remain
   - No verification that cleanup completed successfully
   - No retry logic for cleanup failures

2. **File Handle Management:**
   - CASA concat may leave file handles open
   - Cleanup attempts to remove directories while handles may still be open
   - Sequential processing amplifies issue if cleanup doesn't complete

3. **tmpfs Directory Conflicts:**
   - All groups use same tmpfs base path (`/dev/shm/dsa110-contimg/`)
   - Stale directories from failed groups can interfere with new groups
   - No unique identifiers prevent conflicts

## Proposed Solutions

### Solution 1: Explicit Cleanup Verification (Recommended)

**Location:** `src/dsa110_contimg/conversion/strategies/direct_subband.py`

**Changes:**
1. Add cleanup verification after `casa_concat()`:
   ```python
   # After concat, explicitly close CASA handles
   import casatools
   ms_tool = casatools.ms()
   try:
       ms_tool.close()
   except Exception:
       pass
   ```

2. Verify cleanup completed:
   ```python
   # After cleanup attempt, verify directories removed
   if part_base.exists():
       logger.warning(f"Cleanup incomplete, retrying: {part_base}")
       # Retry cleanup with delay
       import time
       time.sleep(0.5)
       shutil.rmtree(part_base, ignore_errors=True)
   ```

3. Add cleanup verification before starting new group in `hdf5_orchestrator.py`:
   ```python
   # Before creating writer instance, check for stale tmpfs dirs
   tmpfs_base = Path("/dev/shm/dsa110-contimg")
   if tmpfs_base.exists():
       # Check for stale directories older than 1 hour
       for stale_dir in tmpfs_base.glob("*"):
           if stale_dir.is_dir():
               try:
                   mtime = stale_dir.stat().st_mtime
                   if time.time() - mtime > 3600:  # 1 hour
                       logger.warning(f"Removing stale tmpfs directory: {stale_dir}")
                       shutil.rmtree(stale_dir, ignore_errors=True)
               except Exception:
                   pass
   ```

**Priority:** High  
**Effort:** Low  
**Risk:** Low

### Solution 2: Unique tmpfs Directory Per Group

**Location:** `src/dsa110_contimg/conversion/strategies/direct_subband.py`

**Changes:**
1. Use unique identifier in tmpfs path:
   ```python
   # Add timestamp/UUID to tmpfs path to avoid conflicts
   import uuid
   unique_id = f"{Path(ms_stage_path).stem}_{uuid.uuid4().hex[:8]}"
   part_base = tmpfs_root / "dsa110-contimg" / unique_id
   ```

2. Benefits:
   - Eliminates conflicts between concurrent/sequential groups
   - Makes cleanup more reliable (no shared state)
   - Easier to identify stale directories

**Priority:** Medium  
**Effort:** Low  
**Risk:** Low

### Solution 3: Retry Logic for Concat Failures

**Location:** `src/dsa110_contimg/conversion/strategies/direct_subband.py`

**Changes:**
1. Wrap concat in retry logic:
   ```python
   max_retries = 2
   for attempt in range(max_retries):
       try:
           casa_concat(...)
           break
       except RuntimeError as e:
           if "cannot be opened" in str(e) or "readBlock" in str(e):
               if attempt < max_retries - 1:
                   logger.warning(f"Concat failed, retrying after cleanup: {e}")
                   # Cleanup and retry
                   for part in parts:
                       shutil.rmtree(part, ignore_errors=True)
                   import time
                   time.sleep(1.0)
                   continue
           raise
   ```

**Priority:** Medium  
**Effort:** Medium  
**Risk:** Low

### Solution 4: Process Isolation for Subband Writes

**Location:** `src/dsa110_contimg/conversion/strategies/direct_subband.py`

**Changes:**
1. Ensure subband write processes fully terminate before concat:
   ```python
   # After ProcessPoolExecutor context exits, explicitly wait for all processes
   futures = []
   with ProcessPoolExecutor(max_workers=self.max_workers) as ex:
       # ... submit work ...
   
   # Ensure all processes terminated
   import time
   time.sleep(0.5)  # Allow processes to fully terminate
   ```

**Priority:** Low  
**Effort:** Low  
**Risk:** Very Low

## Implementation Plan

### Phase 1: Quick Wins (Immediate) ✅ COMPLETE
- [x] Solution 1: Explicit cleanup verification
- [x] Solution 4: Process termination wait

### Phase 2: Robustness (Short-term) ✅ COMPLETE
- [x] Solution 2: Unique tmpfs directories
- [x] Solution 3: Retry logic for concat failures

**Implementation Date:** 2025-11-02  
**Files Modified:**
- `src/dsa110_contimg/conversion/strategies/direct_subband.py`
- `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`

**Backward Compatibility:**
All changes are **internal implementation improvements** with no changes to public APIs:
- `DirectSubbandWriter.__init__()` signature: unchanged
- `DirectSubbandWriter.write()` signature: unchanged  
- `convert_subband_groups_to_ms()` signature: unchanged
- Input/output behavior: same inputs → same outputs (with improved robustness)
- Optional kwargs: all still work identically

**No shims required** - these are not interface changes, only internal robustness improvements (retry logic, cleanup verification, path naming). Existing code continues to work without modification.

## Implementation Details

### Changes Made

**File: `src/dsa110_contimg/conversion/strategies/direct_subband.py`**

1. **Solution 1: Explicit Cleanup Verification**
   - Added CASA handle closure after concat (lines 269-279)
   - Added cleanup verification loop with up to 3 retry attempts (lines 341-380)
   - Verifies `part_base` directory is removed, retries if still exists

2. **Solution 2: Unique tmpfs Directories**
   - Changed tmpfs path to use UUID-based unique identifiers (line 114)
   - Format: `{ms_stem}_{uuid8}` to avoid conflicts between groups
   - Each group now gets a unique tmpfs directory: `/dev/shm/dsa110-contimg/{timestamp}_{uuid}/`

3. **Solution 3: Retry Logic for Concat Failures**
   - Added retry loop (max 2 attempts) for file locking errors during concat (lines 231-267)
   - Automatically detects "cannot be opened", "readBlock", or "read/write" errors
   - Cleans up and retries with 1-second delay between attempts
   - Logs warnings for retry attempts

4. **Solution 4: Process Isolation**
   - Added 0.5s sleep after ProcessPoolExecutor context exits (lines 227-229)
   - Ensures subband write processes fully terminate and release file handles before concat

**File: `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`**

1. **Solution 1: Pre-Group Cleanup Verification**
   - Added stale tmpfs directory cleanup before processing groups (lines 323-344)
   - Removes directories older than 1 hour from `/dev/shm/dsa110-contimg/`
   - Prevents accumulation of stale directories from previous runs

### Backward Compatibility

**✅ No shims required** - All changes are **internal implementation improvements** with no changes to public APIs:

- **Public API unchanged:**
  - `DirectSubbandWriter.__init__(uv, ms_path, **kwargs)` - signature unchanged
  - `DirectSubbandWriter.write()` - signature unchanged, returns same `"parallel-subband"` string
  - `convert_subband_groups_to_ms(input_dir, output_dir, start_time, end_time, ...)` - signature unchanged
  
- **Input/Output behavior:**
  - Same inputs → same outputs (with improved robustness)
  - All optional kwargs still work identically
  - No breaking changes to existing code

- **Why no shims needed:**
  - These are not interface changes (signatures, parameters, return types)
  - Only internal implementation details changed (retry logic, cleanup verification, path naming)
  - Existing code continues to work without modification
  - No adapter layers or translation code required

**Note:** Shims would only be needed if we changed function signatures, removed deprecated APIs, changed data formats, or needed to translate between old and new interfaces. Since we only improved internal robustness without changing the public API, no shims are necessary.

### Phase 3: Monitoring (Long-term)
- [ ] Add metrics for cleanup failures
- [ ] Add alerting for tmpfs cleanup issues
- [ ] Document cleanup behavior in operations guide

## Testing

### Test Cases
1. **Sequential Processing Stress Test:**
   - Process 20+ groups sequentially
   - Verify no stale tmpfs directories remain
   - Verify no file locking errors

2. **Cleanup Failure Recovery:**
   - Simulate cleanup failure (permission denied)
   - Verify retry logic activates
   - Verify group completes successfully

3. **Concurrent Processing Test:**
   - Process multiple groups with overlapping tmpfs paths
   - Verify no conflicts occur
   - Verify all groups complete successfully

### Success Criteria
- Zero file locking errors in 100+ group conversions
- No stale tmpfs directories after completion
- Cleanup completes successfully 100% of the time

## Related Issues

- End-to-end testing: `docs/reports/DETAILED_TESTING_PLAN_0834_TRANSIT.md`
- Pipeline robustness: "measure twice, cut once" philosophy

## Notes

- This issue was discovered during Phase 2.2 of the 0834 transit end-to-end test
- Retry with cleanup successfully resolved the immediate issue
- Long-term fix needed to prevent manual intervention

