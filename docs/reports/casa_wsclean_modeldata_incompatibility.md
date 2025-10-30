# CASA ft() and WSClean MODEL_DATA Incompatibility

**Status:** Known Issue / Workaround Required  
**Date:** 2025-10-30  
**Severity:** High (Workflow Blocking)

## Summary

CASA's `ft()` task crashes with memory corruption errors (`"double free or corruption"` or `"corrupted size vs. prev_size"`) when attempting to write to `MODEL_DATA` that has been previously populated by WSClean or other external tools. This is a critical incompatibility that prevents using CASA imaging tools after WSClean has modified an MS.

## Error Messages

Two different crash patterns have been observed:

1. **From CASA ft():**
   ```
   RuntimeError: Please make sure MS is writable when using Imager::ft
   (file .../Imager.cc, line 4309)
   double free or corruption (out)
   ```

2. **From CASA clearcal():**
   ```
   RuntimeError: Error in Calibrater::initialize()
   corrupted size vs. prev_size
   ```

## Root Cause

WSClean modifies the `MODEL_DATA` column in a way that corrupts CASA's internal memory structures/metadata. The corruption occurs at a deep level that prevents CASA's Imager tool from safely accessing or modifying the MS, even though the MS appears readable via casacore.tables.

**Technical Details:**
- The MS can be opened read-only via casacore.tables without errors
- `MODEL_DATA` column exists and contains valid data
- File permissions and locks are correct
- However, any CASA operation that attempts to modify `MODEL_DATA` crashes
- Even removing and recreating the `MODEL_DATA` column triggers crashes
- Deep copying the MS also reveals corruption in subtables (SPECTRAL_WINDOW)

## Workaround

**CRITICAL:** Always seed `MODEL_DATA` with CASA `ft()` **BEFORE** running WSClean.

The correct workflow order is:
1. ✅ Seed `MODEL_DATA` with CASA `ft()` (using componentlists or images)
2. ✅ Run WSClean for imaging (reads seeded `MODEL_DATA`)

**DO NOT:**
- ❌ Run WSClean first, then CASA `ft()`
- ❌ Attempt to overwrite `MODEL_DATA` after WSClean has modified it
- ❌ Try to repair an MS that WSClean has already processed

## Current Implementation

The `image_ms()` function in `src/dsa110_contimg/imaging/cli.py` **already implements the correct workflow:**

```python
# Step 1: Seed MODEL_DATA with CASA ft() (lines 440-522)
if calib_ra_deg is not None:
    make_point_cl(...)
    ft_from_cl(ms_path, cl_path, ...)
    
if nvss_min_mjy is not None:
    make_nvss_component_cl(...)
    ft_from_cl(ms_path, cl_path, ...)

# Step 2: Run WSClean (line 556+)
_run_wsclean(...)  # Reads seeded MODEL_DATA
```

**This workflow prevents the issue from occurring** in normal operations.

## Attempted Solutions (None Worked)

The following approaches were attempted but failed:

1. ✅ **Fixed file permissions** - MS is writable by the correct user
2. ✅ **Removed lock files** - No stale locks preventing access
3. ✅ **Set CASACORE_TABLE_LOCKING=FALSE** - No effect
4. ✅ **Cleared MODEL_DATA before ft()** - Crashes during clearing
5. ✅ **Removed MODEL_DATA column** - Crashes during removal
6. ✅ **Deep copied MS** - Corruption persists, reveals subtable issues
7. ✅ **Used clearcal()** - Also crashes with corruption error

## Detection

A utility module `src/dsa110_contimg/calibration/ms_repair.py` provides functions to detect corruption:

```python
from dsa110_contimg.calibration.ms_repair import detect_ms_corruption, is_ms_safe_for_ft

is_corrupted, issues = detect_ms_corruption(ms_path)
if is_corrupted:
    print(f"MS is corrupted: {issues}")
    
if not is_ms_safe_for_ft(ms_path):
    print("MS is not safe for CASA ft()")
```

However, note that corruption may not be detectable via simple reads - it manifests only when attempting modifications.

## Prevention

1. **Always use the correct workflow order** (ft() before WSClean)
2. **Use separate MS copies** if you need to run both tools in different orders for testing
3. **Never attempt to repair** an MS that WSClean has modified - recreate from original data instead

## Impact

- **Development/Testing:** Test MS files processed by WSClean cannot be reused for CASA `ft()` testing
- **Production:** No impact if workflow order is followed correctly (as implemented)
- **Debugging:** Difficult to diagnose without understanding the workflow order requirement

## Related Files

- `src/dsa110_contimg/imaging/cli.py` - Implements correct workflow order
- `src/dsa110_contimg/calibration/skymodels.py` - Contains `ft_from_cl()` with warnings
- `src/dsa110_contimg/calibration/ms_repair.py` - Detection utilities (created but limited effectiveness)

## References

- CASA Imager.cc line 4309 - Error source location
- WSClean documentation - No mention of CASA compatibility issues
- CASA user forums - No documented reports of this specific issue found

## Notes

- This appears to be an **undocumented bug/incompatibility** between CASA and WSClean
- No general solutions exist in the CASA/WSClean communities
- The issue may be specific to certain CASA/WSClean versions
- Consider reporting to both CASA and WSClean development teams

## Future Actions

1. Monitor CASA/WSClean updates for fixes
2. Consider reporting to CASA support/WSClean GitHub
3. Document version compatibility matrix if issue is version-specific

