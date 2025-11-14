# CASA API Fixes Needed Across Codebase

## Summary

The fixes applied to `mosaic/cli.py` and `mosaic/post_validation.py` addressed **immediate errors** but revealed **systemic issues** across the codebase that need comprehensive fixes.

## Issues Found

### 1. `.coordsys()` vs `.coordinates()` API Mismatch

**Problem**: `casacore.images.image` uses `coordinates()`, not `coordsys()`

**Files needing fixes**:
- `mosaic/cache.py` - line with `img.coordsys()`
- `mosaic/cli.py` - line with `img.coordsys()` (in different function)
- `mosaic/validation.py` - 2 instances of `img.coordsys()` and `pb_img.coordsys()`

**Status**: Only fixed in `generate_mosaic_metrics()` function, not elsewhere

### 2. CASAPATH Initialization Timing

**Problem**: `CASAPATH` must be set **before** importing any CASA modules, or casacore initializes with wrong search paths.

**Current status**:
- ✅ Fixed: `mosaic/cli.py`, `mosaic/post_validation.py`, `calibration/calibration.py`, `imaging/cli.py`, `imaging/cli_imaging.py`
- ❌ Missing: ~50 other files that import CASA modules

**Impact**: Files without `ensure_casa_path()` may:
- Fail to find Observatories table
- Use incorrect data paths
- Generate warnings/errors

### 3. `.close()` Method on casaimage

**Status**: Most `.close()` calls are on `table` and `connection` objects (correct). Need to verify `ia.close()` in `api/batch_jobs.py` - may be casatools image tool (different API).

## Recommended Fixes

### Immediate (High Priority)

1. **Fix all `.coordsys()` calls**:
   ```python
   # Change:
   coordsys = img.coordsys()
   # To:
   coordsys = img.coordinates()
   ```

2. **Add CASAPATH initialization to all CASA-importing files**:
   ```python
   from dsa110_contimg.utils.casa_init import ensure_casa_path
   ensure_casa_path()
   # THEN import CASA modules
   from casacore.images import image as casaimage
   ```

### Systematic Approach

1. Create a script to find all CASA imports
2. Add `ensure_casa_path()` to each file before imports
3. Replace all `.coordsys()` with `.coordinates()`
4. Verify no `casaimage.close()` calls (use `del` instead)

## Testing Strategy

After fixes:
1. Run unit tests for mosaic, imaging, calibration modules
2. Check for Observatories warnings in logs
3. Verify image operations work correctly

