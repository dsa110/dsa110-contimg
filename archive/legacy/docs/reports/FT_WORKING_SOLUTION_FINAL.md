# Making ft() Work Correctly: Final Solution

**Date**: 2025-11-04  
**Status**: Implemented  
**Principle**: UVW transformation must succeed - no workarounds

## Core Principle

**If UVW coordinates are incorrect, DATA is phased to the wrong center.**
- Manual MODEL_DATA calculation won't help - DATA and MODEL_DATA will still mismatch
- Calibration will fail regardless of MODEL_DATA calculation method
- **UVW transformation must be verified and successful before proceeding**

## Solution Design

### Step 1: Verify UVW Transformation (MANDATORY)

**Approach**:
1. Capture old phase center before rephasing
2. Run `phaseshift` to rephase MS
3. **Verify UVW transformation** using `verify_uvw_transformation()`
4. **If verification fails: RAISE ERROR** - cannot proceed

**No fallbacks**: If UVW transformation fails, calibration cannot succeed.

### Step 2: Use ft() with Confidence

Once UVW transformation is verified:
- `ft()` will use correct UVW frame (which defines phase center)
- MODEL_DATA will have correct phase structure
- DATA and MODEL_DATA will align
- Calibration will succeed

## Implementation

### UVW Verification Function

**File**: `src/dsa110_contimg/calibration/uvw_verification.py`

**Key Functions**:
- `verify_uvw_transformation()`: Verifies UVW was correctly transformed
- `get_uvw_statistics()`: Gets UVW statistics for comparison
- `calculate_expected_uvw_change()`: Calculates expected UVW change

### Workflow Integration

**File**: `src/dsa110_contimg/calibration/cli.py`

**Workflow**:
1. Check if rephasing needed
2. Capture old phase center
3. Run `phaseshift`
4. **Verify UVW transformation** (MANDATORY)
5. **If verification fails: RAISE RuntimeError** - stop calibration
6. Update REFERENCE_DIR if needed
7. Use `ft()` to populate MODEL_DATA (UVW is correct, so ft() works)

## Error Handling

### UVW Verification Failure

**Response**: Raise `RuntimeError` with clear message:
```
"UVW transformation failed. Cannot calibrate MS with incorrect phase center. 
This may indicate a bug in phaseshift for large phase shifts, or incorrect 
MS phasing from conversion. Please check the MS phase center and re-run 
conversion or rephasing manually."
```

**Rationale**: 
- Better to fail early than produce wrong calibration
- Clear error message helps user diagnose root cause
- No silent failures that lead to confusing calibration errors

## Why This Approach is Correct

### Problem with Workarounds

If UVW is wrong:
- DATA is phased to wrong center (e.g., 54 arcmin offset)
- Manual MODEL_DATA calculation would use correct phase center
- Result: DATA and MODEL_DATA don't match
- Calibration fails with confusing errors

### Correct Approach

1. **Ensure UVW is correct first** (via verification)
2. **Then use ft()** (which will work because UVW is correct)
3. **No workarounds needed** (because root cause is fixed)

## Testing Strategy

### Test 1: UVW Verification Success
- Rephase MS with `phaseshift`
- Verify UVW transformation succeeds
- Confirm `ft()` produces correct MODEL_DATA

### Test 2: UVW Verification Failure
- Simulate UVW transformation failure
- Confirm calibration raises error (doesn't proceed)
- Verify error message is clear

### Test 3: Large Phase Shifts
- Test with 54 arcmin phase shift
- Verify `phaseshift` correctly transforms UVW
- If it fails, document as CASA bug

## Known Limitations

### phaseshift May Have Bugs

If `phaseshift` doesn't correctly transform UVW for large phase shifts:
- Our verification will detect it
- Calibration will fail with clear error
- User can report to CASA with reproducible test case

### No Alternative to phaseshift

Since `fixvis` is deprecated and not used:
- We rely on `phaseshift` working correctly
- If it doesn't work, we fail (better than wrong results)
- User must fix MS phasing manually or wait for CASA fix

## Success Criteria

1. ✓ UVW transformation verified before proceeding
2. ✓ Calibration fails fast if UVW is wrong (clear error)
3. ✓ `ft()` works correctly when UVW is correct
4. ✓ No precarious workarounds that mask root causes

## Documentation Updates

1. Update calibration procedure to emphasize UVW verification
2. Document error messages and troubleshooting
3. Create CASA bug report template if phaseshift fails
4. Explain why UVW correctness is mandatory

