# Making ft() Work Correctly: Solution Design

**Date**: 2025-11-04  
**Status**: Design Document  
**Goal**: Fix `ft()` behavior without bypassing it

## Problem Statement

`ft()` determines phase center from UVW coordinate frame, not from FIELD table columns (`REFERENCE_DIR`/`PHASE_DIR`). For large phase shifts (54 arcmin), `phaseshift` may not correctly transform UVW coordinates, causing `ft()` to use the wrong phase center.

## Root Cause Analysis

### What We Know

1. **ft() behavior**: Uses UVW frame to determine phase center (tested and confirmed)
2. **phaseshift behavior**: Updates `PHASE_DIR` and should update UVW, but may fail for large shifts
3. **Current workflow**: Uses `phaseshift` only, which may not fully transform UVW

### Key Insight

The UVW coordinate frame defines the phase center for `ft()`. If UVW isn't correctly transformed, `ft()` will use the old phase center regardless of `REFERENCE_DIR`/`PHASE_DIR` values.

## Solution Strategy

### Phase 1: Verify UVW Transformation

**Goal**: Confirm that `phaseshift` correctly transforms UVW for large phase shifts.

**Approach**:
1. Create test to compare UVW before/after `phaseshift`
2. Verify UVW transformation matches expected geometric shift
3. Check if transformation is complete or partial

**Expected Outcome**: Either confirm `phaseshift` works correctly, or identify the specific failure mode.

### Phase 2: Ensure Proper UVW Transformation

**Goal**: Guarantee UVW is correctly transformed before calling `ft()`.

**Approach**: Multi-strategy approach with fallbacks:

#### Strategy A: Verify phaseshift Success (Primary)

1. **Run phaseshift** as currently done
2. **Verify UVW transformation**:
   - Compare UVW statistics before/after
   - Check if transformation magnitude matches expected shift
   - Verify UVW frame aligns with new phase center
3. **If UVW is correct**: Proceed with `ft()`
4. **If UVW is wrong**: Use Strategy B or C

#### Strategy B: Use fixvis for Large Shifts (Fallback)

1. **Detect large phase shift** (> 30 arcmin threshold)
2. **Use fixvis instead of (or in addition to) phaseshift**:
   - `fixvis` may handle large shifts differently
   - `fixvis` explicitly updates UVW coordinates
   - Deprecated but still functional
3. **Verify UVW transformation** after `fixvis`
4. **Proceed with `ft()`**

#### Strategy C: Two-Step Rephasing (If Needed)

1. **First pass**: Use `fixvis` to update UVW frame
2. **Second pass**: Use `phaseshift` for phase correction
3. **Verify both UVW and phase center**
4. **Proceed with `ft()`**

### Phase 3: Add UVW Verification

**Goal**: Detect UVW transformation failures before calling `ft()`.

**Approach**:
1. **Before rephasing**: Capture UVW statistics (mean, std, range)
2. **After rephasing**: Calculate expected UVW change based on phase shift
3. **Compare actual vs expected UVW change**:
   - For large phase shifts, UVW should change significantly
   - Expected change: ~baseline_length * sin(phase_shift_radians)
4. **If mismatch detected**: Flag error or use alternative method

### Phase 4: Optimize Workflow Order

**Goal**: Ensure `ft()` reads correct UVW frame.

**Approach**:
1. **Complete rephasing fully** before calling `ft()`
2. **Close and reopen MS** if needed (force fresh read of UVW)
3. **Verify UVW immediately before `ft()` call**
4. **Call `ft()` on freshly rephased MS**

## Implementation Plan

### Step 1: Add UVW Verification Function

```python
def verify_uvw_transformation(
    ms_path: str,
    old_phase_center: Tuple[float, float],
    new_phase_center: Tuple[float, float],
    tolerance_meters: float = 0.1
) -> bool:
    """Verify UVW was correctly transformed by phaseshift.
    
    Returns True if UVW transformation is correct, False otherwise.
    """
    # Calculate expected UVW change
    # Compare actual UVW change
    # Return True if within tolerance
```

### Step 2: Add UVW Transformation Check to Rephasing

```python
# After phaseshift
if not verify_uvw_transformation(ms_phased, old_phase, new_phase):
    # UVW transformation failed - try fixvis
    print("WARNING: phaseshift UVW transformation incomplete, using fixvis...")
    # Use fixvis as fallback
```

### Step 3: Use fixvis for Large Phase Shifts

```python
phase_shift_arcmin = calculate_separation(old_phase, new_phase)
if phase_shift_arcmin > 30.0:  # Large shift threshold
    # Use fixvis for large shifts
    fixvis(vis=args.ms, outputvis=ms_phased, phasecenter=...)
else:
    # Use phaseshift for small shifts
    phaseshift(vis=args.ms, outputvis=ms_phased, phasecenter=...)
```

### Step 4: Force Fresh UVW Read Before ft()

```python
# After rephasing, before ft()
# Close any open MS handles
# Reopen MS to force fresh UVW read
with table(ms_path, readonly=True) as t:
    # Verify UVW is correct
    uvw = t.getcol("UVW")
    # Check UVW statistics match expected

# Now call ft() - it will read fresh UVW
ft(vis=ms_path, complist=comp_path, ...)
```

## Testing Strategy

### Test 1: UVW Transformation Verification

**Test**: `tests/science/test_uvw_transformation_after_phaseshift.py`
- Verify UVW changes after phaseshift
- Check transformation magnitude
- Validate for both small and large phase shifts

### Test 2: ft() with Correct UVW

**Test**: `tests/science/test_ft_with_correct_uvw.py`
- Rephase MS with verified UVW transformation
- Call ft() and check MODEL_DATA phase scatter
- Should show < 1° scatter if UVW is correct

### Test 3: Large Phase Shift Handling

**Test**: `tests/science/test_large_phase_shift.py`
- Test phaseshift with 54 arcmin shift
- Test fixvis with 54 arcmin shift
- Compare UVW transformation quality
- Choose best method for large shifts

## Expected Outcomes

### Success Criteria

1. **UVW Transformation**: Correctly transformed by rephasing method
2. **ft() phase scatter**: < 1° (was 103°)
3. **MODEL_DATA alignment**: Correctly aligned with DATA
4. **Calibration SNR**: High (80-90% solution retention)

### Failure Modes and Mitigations

1. **phaseshift doesn't transform UVW**: Use `fixvis` as fallback
2. **fixvis also fails**: Use two-step approach (fixvis + phaseshift)
3. **UVW transformation incomplete**: Detect and flag error
4. **ft() still uses wrong phase center**: Investigate further (may be CASA bug)

## Alternative: Hybrid Approach

If UVW transformation cannot be guaranteed:

1. **Try phaseshift first** (preferred method)
2. **Verify UVW transformation**
3. **If verification fails**: Use manual calculation as fallback
4. **Log the issue** for CASA bug report

This maintains preference for `ft()` but has reliable fallback.

## Implementation Priority

1. **High**: Add UVW verification function
2. **High**: Add verification to rephasing workflow
3. **Medium**: Implement fixvis fallback for large shifts
4. **Low**: Two-step rephasing (if needed)

## Documentation Updates

1. Update calibration procedure with UVW verification step
2. Document fixvis usage for large phase shifts
3. Add troubleshooting guide for UVW transformation issues
4. Create CASA bug report template if issue persists

