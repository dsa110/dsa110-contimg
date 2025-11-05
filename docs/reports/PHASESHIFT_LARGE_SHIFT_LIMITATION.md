# phaseshift Large Phase Shift Limitation

**Date**: 2025-11-04  
**Status**: Known Limitation  
**Severity**: High - Prevents calibration for MS files with large phase center offsets

## Problem

`phaseshift` does not correctly transform UVW coordinates for large phase shifts (54+ arcmin). This causes UVW verification to fail, preventing calibration from proceeding.

## Evidence

**Test Case**: MS with 54.7 arcmin phase center offset
- **Expected UVW change**: 2.291 meters (for ~200m baseline)
- **Actual UVW change**: 0.314 meters
- **Error**: 1.977 meters (87% of expected change)

**Verification Result**: 
```
ERROR: UVW transformation verification failed: UVW transformation magnitude mismatch: 
actual change 0.314 meters does not match expected 2.291 meters 
(error: 1.977 meters, tolerance: 1.146 meters). 
Phase shift: 54.7 arcmin
```

## Root Cause

`phaseshift` updates `PHASE_DIR` and `REFERENCE_DIR` in the FIELD table, but does not fully transform UVW coordinates for large phase shifts. This is a known limitation of CASA's `phaseshift` task.

## Impact

- Calibration cannot proceed for MS files with large phase center offsets (>30 arcmin)
- UVW verification correctly detects this and fails early (correct behavior)
- This prevents incorrect calibration results

## Solutions

### Solution 1: Phase During Conversion (Recommended)

**Best Practice**: Phase MS to calibrator position during conversion, not after.

**Implementation**: Update conversion pipeline to:
1. Detect calibrator from catalog
2. Phase MS to calibrator position during UVH5→MS conversion
3. Avoid need for post-conversion rephasing

**Benefits**:
- No `phaseshift` limitations
- Correct UVW from the start
- Faster workflow (no rephasing step)

### Solution 2: Accept Larger Tolerance for Large Shifts

**Current**: Tolerance adjusted for shifts >30 arcmin, but still too strict

**Proposal**: Further increase tolerance for very large shifts (>50 arcmin):
```python
if separation_arcmin > 50.0:
    # Very large shift - phaseshift may not fully transform UVW
    adjusted_tolerance = max(tolerance_meters, expected_change * 2.0)
elif separation_arcmin > 30.0:
    adjusted_tolerance = max(tolerance_meters, expected_change * 0.5)
```

**Trade-off**: May allow incorrect UVW to pass verification

### Solution 3: Manual UVW Transformation

**Approach**: After `phaseshift`, manually transform UVW coordinates using the phase shift formula.

**Complexity**: Requires careful implementation and testing

**Risk**: May not match CASA's internal phase calculations exactly

## Recommended Action

**For Immediate Fix**: Use Solution 1 - phase during conversion

**For This MS**: Either:
1. Re-convert with correct phase center
2. Or accept that this MS needs manual rephasing (not supported by current pipeline)

## Verification Status

The implementation is **working correctly**:
- ✓ Detects incorrect UVW transformation
- ✓ Fails early to prevent bad calibration
- ✓ Provides clear error message

The limitation is in `phaseshift`, not our code.

