# Priority 1 Precondition Checks Implementation

**Date:** 2025-11-02  
**Status:** COMPLETED

## Summary

Implemented Priority 1 precondition checks for post-applycal validation and imaging validation.

## Implementation Details

### 1. Post-Applycal Validation ✅

**File:** `src/dsa110_contimg/calibration/applycal.py`

**Changes:**
- Added `_verify_corrected_data_populated()` function (lines 13-78)
  - Verifies CORRECTED_DATA column exists
  - Verifies MS has data rows
  - Samples up to 10,000 rows to check non-zero fraction
  - Raises `RuntimeError` if < 1% of unflagged data is non-zero
  
- Updated `apply_to_target()` function (lines 81-146)
  - Added `verify: bool = True` parameter (default: enabled)
  - Calls `_verify_corrected_data_populated()` after `casa_applycal()` completes
  - Raises `RuntimeError` if verification fails
  - Provides clear error messages with diagnostics

**Behavior:**
- Verification runs by default after every `applycal` call
- Raises hard error if CORRECTED_DATA is not populated
- Can be disabled by passing `verify=False` (for callers that do their own verification)

**Updated Callers:**
- `apply_service.py`: Passes `verify=False` to avoid duplicate verification (it does its own)

### 2. Imaging MS Validation ✅

**File:** `src/dsa110_contimg/imaging/cli.py`

**Changes:**
- Added MS existence/readability validation at start of `image_ms()` (lines 362-389)
  - Verifies MS exists and is a directory
  - Verifies MS is readable (opens table)
  - Verifies MS has data rows
  - Verifies required columns exist: `['DATA', 'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW']`
  - Raises `RuntimeError` with clear error messages if validation fails

- Added CORRECTED_DATA quality validation (lines 391-420)
  - If CORRECTED_DATA column exists, samples up to 10,000 rows
  - Checks fraction of unflagged data that is non-zero
  - Logs warning if < 1% non-zero (suggests calibration may not have been applied)
  - Logs info if ≥ 1% non-zero (confirms calibration appears applied)
  - Non-fatal (logs warning, doesn't raise error) - allows imaging to proceed

**Behavior:**
- MS validation runs before any expensive imaging operations
- Raises hard error if MS is invalid (prevents wasted time)
- CORRECTED_DATA validation is non-fatal (warns but allows imaging)

## Testing

All code compiles successfully:
- ✅ `applycal.py` - no syntax errors
- ✅ `imaging/cli.py` - no syntax errors
- ✅ `apply_service.py` - no syntax errors

## Impact

### Benefits
1. **Prevents silent failures**: Post-applycal validation catches failed calibrations immediately
2. **Prevents wasted time**: Imaging validation catches invalid MS before expensive operations
3. **Clear error messages**: Users get actionable diagnostics when validation fails
4. **Consistent behavior**: All applycal calls verify CORRECTED_DATA by default

### Breaking Changes
- None - `verify=True` is default, existing code continues to work
- `apply_service.py` explicitly disables built-in verification (uses its own)

## Next Steps

**Priority 2 (Medium):**
- Disk space check before imaging (estimate image size, verify sufficient space)

**Priority 3 (Low):**
- Field validation before imaging (verify field selection exists)
- Image parameter validation (verify imsize/cell size reasonable)

