# Fix: UVW Misalignment Detection and Correction

**Date**: 2025-11-04  
**Issue**: High flagging rate (15-35% vs expected 2-3 solutions) due to MODEL_DATA phase scatter (104°)  
**Root Cause**: UVW coordinates in wrong phase center frame despite phase center matching  
**Fix**: Added UVW alignment check that forces rephasing when misaligned

## Problem

Even when MS phase center (`REFERENCE_DIR`) matches the calibrator (< 1 arcmin), UVW coordinates can still be in the wrong frame. This causes:

1. `ft()` to calculate MODEL_DATA using wrong phase center → 104° phase scatter
2. DATA/MODEL mismatch → Low SNR → High flagging rate (15-35%)

### Evidence

- **MODEL_DATA phase scatter**: 104.3° (should be < 10°)
- **UVW V mean**: -350.762 m (should be near 0 m)
- **Phase center**: Correctly aligned (0.00 arcmin offset)

The 104° scatter matches the expected scatter for the old phase center (54.7 arcmin offset), confirming MODEL_DATA was calculated using the wrong UVW frame.

## Solution

Added UVW alignment verification **even when phase center matches**:

```python
if sep_arcmin < 1.0:
    # CRITICAL: Even if phase center matches, UVW might be in wrong frame
    # Check UVW alignment - U and V means should be near zero for correctly phased MS
    uvw_stats = get_uvw_statistics(args.ms, n_sample=1000)
    u_mean_abs = abs(uvw_stats['u_mean'])
    v_mean_abs = abs(uvw_stats['v_mean'])
    max_offset = max(u_mean_abs, v_mean_abs)
    
    # For correctly phased MS, U/V means should be < 100 m
    if max_offset > 100.0:
        # Force rephasing to fix UVW
        needs_rephasing = True
    else:
        needs_rephasing = False
```

## How It Works

1. **Phase center check**: If separation < 1 arcmin, proceed to UVW check
2. **UVW statistics**: Calculate U/V means from UVW coordinates
3. **Threshold**: If max(U_mean, V_mean) > 100 m → UVW misaligned
4. **Action**: Force rephasing to transform UVW to correct frame
5. **Verification**: UVW transformation verified after rephasing (existing code)

## Expected Results

After fix:
- **UVW alignment**: U/V means < 100 m (near zero)
- **MODEL_DATA phase scatter**: < 10°
- **Bandpass flagging rate**: < 5% (2-3 solutions per SPW instead of 15-35%)

## Why This Happens

MS conversion may set phase center correctly, but UVW coordinates can remain in the original (meridian) frame. This occurs when:
- Conversion sets `REFERENCE_DIR` correctly but doesn't transform UVW
- Or UVW transformation is incomplete/incorrect during conversion

The fix ensures UVW is always correctly aligned before MODEL_DATA population, regardless of phase center match.

