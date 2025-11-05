# Making ft() Work Correctly: Implementation Summary

**Date**: 2025-11-04  
**Status**: Implemented  
**Approach**: Verify UVW transformation, use ft() when verified, manual calculation as fallback

## Solution Overview

Instead of bypassing `ft()`, we now:
1. **Verify UVW transformation** after `phaseshift`
2. **Use `ft()`** when UVW transformation is verified
3. **Fall back to manual calculation** if UVW transformation fails

This approach ensures `ft()` works correctly when UVW is properly transformed, while maintaining reliability through manual calculation as a fallback.

## Implementation Details

### 1. UVW Verification Module

**File**: `src/dsa110_contimg/calibration/uvw_verification.py`

**Functions**:
- `verify_uvw_transformation()`: Verifies UVW was correctly transformed
- `get_uvw_statistics()`: Gets UVW coordinate statistics
- `calculate_expected_uvw_change()`: Calculates expected UVW change for phase shift
- `get_phase_center_from_ms()`: Reads phase center from MS

### 2. Updated Rephasing Workflow

**File**: `src/dsa110_contimg/calibration/cli.py`

**Workflow**:
1. Capture old phase center before rephasing
2. Run `phaseshift` to rephase MS
3. **Verify UVW transformation** using `verify_uvw_transformation()`
4. If verification passes: Use `ft()` (UVW correctly transformed)
5. If verification fails: Use manual calculation (UVW not correctly transformed)

**Key Changes**:
- Added UVW verification after `phaseshift`
- Removed `fixvis` fallback (user requirement)
- Added conditional logic to choose `ft()` vs manual calculation
- Store `use_manual_for_model_data` flag for later use

### 3. Conditional MODEL_DATA Population

**Logic**:
```python
if UVW_transformation_verified:
    use ft()  # UVW is correct, ft() will work
else:
    use manual calculation  # UVW may be wrong, bypass ft()
```

## Benefits

1. **Uses `ft()` when possible**: Prefers CASA's native functionality
2. **Reliable fallback**: Manual calculation ensures correctness even if UVW transformation fails
3. **No deprecated tools**: Removed `fixvis` dependency
4. **Automatic detection**: Detects UVW transformation failures automatically
5. **Transparent**: Clear logging of which method is used and why

## Testing Strategy

### Test Cases

1. **Small phase shift** (< 30 arcmin):
   - `phaseshift` should work correctly
   - UVW verification should pass
   - `ft()` should be used

2. **Large phase shift** (> 30 arcmin):
   - `phaseshift` may or may not work correctly
   - UVW verification will detect if it fails
   - Falls back to manual calculation if needed

3. **phaseshift failure**:
   - Exception caught
   - Falls back to manual calculation
   - Calibration continues

## Expected Behavior

### Success Case (UVW Correctly Transformed)

```
DEBUG: Running phaseshift...
DEBUG: phaseshift complete, verifying UVW transformation...
✓ UVW transformation verified: phaseshift correctly transformed UVW
DEBUG: Using ft() to populate MODEL_DATA (UVW transformation verified)...
```

### Fallback Case (UVW Transformation Failed)

```
DEBUG: Running phaseshift...
DEBUG: phaseshift complete, verifying UVW transformation...
WARNING: UVW transformation verification failed: [error message]
DEBUG: Will use manual MODEL_DATA calculation instead of ft()
DEBUG: Using manual MODEL_DATA calculation (UVW transformation was not verified)...
```

## Verification

After implementation, verify:
1. ✅ UVW verification detects transformation failures
2. ✅ `ft()` is used when UVW is correct
3. ✅ Manual calculation is used when UVW transformation fails
4. ✅ No `fixvis` references remain
5. ✅ Calibration works correctly in both cases

## Future Improvements

1. **Monitor UVW transformation success rate**: Track how often `phaseshift` succeeds vs fails
2. **Tune verification thresholds**: Adjust tolerance based on real-world data
3. **Report to CASA**: If `phaseshift` consistently fails for large shifts, document for CASA developers

