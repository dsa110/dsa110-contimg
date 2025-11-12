# Root Cause: High Flagging Rate (15-35% vs Expected 2-3 Solutions)

**Date**: 2025-11-04  
**Issue**: Bandpass calibration flagging 15-35% of solutions per SPW instead of 2-3 solutions  
**Root Cause**: UVW coordinates not correctly transformed, causing MODEL_DATA phase scatter of 104°  
**Status**: CRITICAL

## Problem

With correct phase alignment, bandpass calibration should only flag 2-3 solutions (worst baselines/channels), not 15-35% (20-60 solutions per SPW).

## Root Cause Identified

**MODEL_DATA phase scatter: 104.3°** (should be < 10°)

This indicates MODEL_DATA was calculated using the **old phase center** (meridian), not the calibrator position.

### Evidence

1. **MODEL_DATA Phase Scatter**: 104.3°
   - Expected for old phase center (54.7 arcmin offset): ~98.5°
   - Expected for new phase center (0 arcmin offset): < 10°
   - **Actual**: 104.3° ✓ **Matches old phase center**

2. **UVW Statistics**:
   - U mean: -5.243 m (near zero ✓)
   - **V mean: -350.762 m** (HUGE offset ✗)**
   - W mean: -116.508 m (offset)
   - **For correctly phased MS, U and V means should both be near zero**

3. **Phase Center Check**:
   - REFERENCE_DIR: Correctly aligned (0.00 arcmin offset)
   - PHASE_DIR: Correctly aligned (0.00 arcmin offset)
   - **But UVW is still in old frame**

## Why This Happened

**Scenario**: MS phase center was already aligned (< 1 arcmin), so rephasing was skipped:

```python
if sep_arcmin < 1.0:
    needs_rephasing = False
    # Assumes UVW is correct since phase center matches
```

**Problem**: The MS was converted with correct phase center, but UVW coordinates may still be in the wrong frame if:
- Conversion didn't properly phase UVW
- Or UVW was incorrectly set during conversion

**Result**: 
- Phase center (REFERENCE_DIR) is correct ✓
- UVW coordinates are in old frame ✗
- `ft()` uses UVW → calculates MODEL_DATA for wrong phase center → 104° scatter

## Impact

- MODEL_DATA phase scatter: 104° (wrong)
- DATA/MODEL mismatch: Severe decorrelation
- SNR: Low (DATA and MODEL don't align)
- Flagging rate: 15-35% (instead of 2-3 solutions)

## Solution

**Need to verify UVW alignment even when phase center matches**:

1. Check UVW statistics (U/V means should be near zero)
2. If UVW is offset, rephase even if phase center matches
3. Or fix UVW directly if rephasing is not needed

## Verification

After fix, verify:
- MODEL_DATA phase scatter: < 10°
- UVW V mean: < ±100 m (near zero)
- Bandpass flagging rate: < 5% (2-3 solutions per SPW)

