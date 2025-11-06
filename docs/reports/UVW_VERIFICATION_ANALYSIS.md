# UVW Transformation Verification Analysis

**Date:** 2025-11-05  
**Issue:** Analyzing correctness of UVW transformation verification method  
**Status:** 🔍 **POTENTIAL ISSUE IDENTIFIED**

---

## Current Verification Method

**Location:** `src/dsa110_contimg/calibration/uvw_verification.py:verify_uvw_transformation()`

### How It Works

1. **Gets UVW statistics before and after rephasing:**
   - Calculates mean, std, range for U, V, W components
   - Uses `get_uvw_statistics()` which samples rows

2. **Calculates actual UVW change:**
   ```python
   u_change = abs(stats_after['u_mean'] - stats_before['u_mean'])
   v_change = abs(stats_after['v_mean'] - stats_before['v_mean'])
   w_change = abs(stats_after['w_mean'] - stats_before['w_mean'])
   max_change = max(u_change, v_change, w_change)
   ```

3. **Calculates expected UVW change:**
   ```python
   expected_change = baseline_length_meters * sin(separation_radians)
   ```

4. **Verifies:**
   - Transformation occurred: `max_change >= min_change_meters`
   - Transformation magnitude matches: `abs(max_change - expected_change) <= tolerance`

---

## The Problem

### Why Mean UVW Change May Not Be Reliable

**UVW coordinates are rotated, not translated.** When phase center changes, the UVW coordinate system rotates around the sky. This means:

1. **Individual baselines are rotated differently:**
   - Each baseline has a different orientation
   - Rotation affects each baseline's UVW differently
   - The change in UVW for each baseline depends on its orientation relative to the rotation axis

2. **Mean of rotated vectors doesn't follow simple formula:**
   - For a single baseline: `change ≈ baseline_length * sin(separation)` ✓
   - For an array of baselines: mean change depends on array geometry
   - Baselines in different directions may change in opposite directions, canceling out
   - Or they may reinforce, creating larger mean change

3. **Example:**
   - Consider a symmetric array with baselines pointing in all directions
   - Rotate phase center by 10 degrees
   - Individual baseline UVW changes: ~baseline_length * sin(10°) ≈ 0.17 * baseline_length
   - But mean change: could be near zero (if symmetric) or could be larger (if asymmetric)

### The Expected Change Formula Is Incomplete

`calculate_expected_uvw_change()` uses:
```python
expected_change = baseline_length * sin(separation)
```

This formula assumes:
- A single baseline at a specific orientation
- The rotation affects that baseline maximally
- But for an array, the mean change will be smaller (or could be larger) depending on geometry

**For a 54.7 arcmin phase shift (user's case):**
- Separation ≈ 0.016 radians
- sin(0.016) ≈ 0.016
- Expected change for 200m baseline: 200 * 0.016 ≈ 3.2 meters
- But mean change for an array might be much smaller due to cancellation

---

## What Should Be Verified Instead

### 1. CASA phaseshift Success (Already Done)
- `phaseshift` completes without errors ✓
- Output MS is created ✓

### 2. Phase Center Updated (Already Done)
- `PHASE_DIR` matches new phase center ✓
- `REFERENCE_DIR` updated to match ✓

### 3. Individual UVW Values (Spot Check)
Instead of comparing means, verify a few individual baselines:
- Sample a few specific baselines before/after
- Check that their UVW values changed by expected amount
- This is more reliable than mean comparison

### 4. Visibility Phase Consistency
- The most critical check: DATA column phases should match MODEL_DATA
- If phaseshift worked, DATA and MODEL_DATA should align
- This is verified indirectly through calibration success

---

## Current Implementation Assessment

### What's Good

1. ✅ **Checks that transformation occurred** (min_change check)
   - Detects if phaseshift didn't run or failed silently
   - This is useful

2. ✅ **Adjusts tolerance for large phase shifts**
   - Recognizes that phaseshift has limitations for very large shifts
   - Allows larger tolerance (>50 arcmin)

3. ✅ **Uses CASA's phaseshift** (the right tool)
   - phaseshift is the correct method for rephasing
   - It's been tested and verified by CASA developers

### What's Questionable

1. ⚠️ **Mean value comparison may give false negatives**
   - For symmetric arrays, mean change might be small
   - Verification might fail even when phaseshift worked correctly
   - This could cause unnecessary calibration failures

2. ⚠️ **Expected change formula is oversimplified**
   - Assumes single baseline orientation
   - Doesn't account for array geometry
   - May not match actual mean change for arrays

---

## Recommendations

### Option 1: Trust CASA phaseshift (Recommended)
- Remove or relax the mean-change verification
- Only check that:
  - phaseshift completed without errors
  - PHASE_DIR was updated correctly
  - REFERENCE_DIR matches PHASE_DIR
- If phaseshift succeeds, trust it (CASA's implementation is correct)

### Option 2: Improve Verification (More Robust)
- Instead of mean comparison, sample a few individual baselines
- For each sampled baseline, verify its UVW change matches expected
- This is more reliable but more complex

### Option 3: Make Verification Non-Blocking
- Keep current verification but make it warning-only
- Don't fail calibration if verification has issues
- Log warnings for investigation

---

## Conclusion

The current UVW verification method has a **fundamental flaw**: it compares mean UVW values, which may not change significantly even when individual baselines are correctly rotated. This could cause false negatives (rejecting correct transformations).

**However**, the verification is still useful as a sanity check to detect:
- Complete failure of phaseshift (no transformation at all)
- Very large discrepancies (obviously wrong transformations)

**For the user's case (54.7 arcmin phase shift):**
- The verification should pass if phaseshift worked correctly
- If it fails, it might be a false negative due to array geometry
- The tolerance adjustment (1.0 m for large shifts) helps, but may not be enough for all cases

**Recommendation:** Keep the verification but make it less strict, or add additional checks (like individual baseline sampling) for more reliable verification.

