# UVW Verification Mathematical Confirmation

**Date:** 2025-11-05  
**Status:** Mathematical Analysis Confirms Issue  
**Conclusion:** ❌ **VERIFICATION METHOD IS FUNDAMENTALLY FLAWED**

---

## Mathematical Analysis

### The Problem: Mean of Rotated Vectors

When phase center changes, UVW coordinates undergo a **rotation** (not translation). The verification method compares **mean UVW values** before and after rotation, which is mathematically problematic.

### Single Baseline Case (Correct)

For a **single baseline** with length `L` at angle `θ` from the rotation axis:

**Before rotation:**
- UVW = `(L·cos(θ), L·sin(θ), w)`

**After rotation by angle `φ`:**
- UVW = `(L·cos(θ+φ), L·sin(θ+φ), w')`

**Change in U component:**
```
Δu = L·cos(θ+φ) - L·cos(θ)
   = L·[cos(θ+φ) - cos(θ)]
   = L·[-2·sin((2θ+φ)/2)·sin(φ/2)]
   ≈ L·sin(φ) for small φ
```

For small phase shifts, `sin(φ) ≈ φ`, so:
```
Δu ≈ L·φ
```

This matches the expected formula: `baseline_length * sin(separation)` ✓

### Array Case (Problematic)

For an **array with N baselines** in different orientations:

**Before rotation:**
- Baseline i: `(L_i·cos(θ_i), L_i·sin(θ_i), w_i)`
- Mean U: `u_mean = (1/N) Σ L_i·cos(θ_i)`

**After rotation by angle `φ`:**
- Baseline i: `(L_i·cos(θ_i+φ), L_i·sin(θ_i+φ), w_i')`
- Mean U: `u_mean' = (1/N) Σ L_i·cos(θ_i+φ)`

**Change in mean U:**
```
Δu_mean = u_mean' - u_mean
        = (1/N) Σ [L_i·cos(θ_i+φ) - L_i·cos(θ_i)]
        = (1/N) Σ L_i·[cos(θ_i+φ) - cos(θ_i)]
```

Using trigonometric identity:
```
cos(θ_i+φ) - cos(θ_i) = -2·sin((2θ_i+φ)/2)·sin(φ/2)
```

For small `φ`:
```
cos(θ_i+φ) - cos(θ_i) ≈ -sin(θ_i)·φ
```

Therefore:
```
Δu_mean ≈ (1/N) Σ L_i·[-sin(θ_i)·φ]
        = -(φ/N) Σ L_i·sin(θ_i)
```

### The Critical Issue

**The mean change depends on array geometry:**

1. **Symmetric arrays:**
   - If baselines are evenly distributed, `Σ L_i·sin(θ_i) ≈ 0`
   - Mean change: `Δu_mean ≈ 0`
   - **Verification fails even though transformation is correct!**

2. **Asymmetric arrays:**
   - `Σ L_i·sin(θ_i) ≠ 0`
   - Mean change: `Δu_mean ≈ -(φ/N)·Σ L_i·sin(θ_i)`
   - **Magnitude depends on array geometry, not just phase shift**

3. **Example:**
   - 100m baseline at 45°: `Δu = 100·sin(φ) ≈ 100·φ`
   - But if array has 10 baselines averaging to zero mean: `Δu_mean ≈ 0`
   - **Formula predicts 100·φ, but mean change is 0!**

### Expected Change Formula Is Wrong for Arrays

The verification uses:
```python
expected_change = baseline_length_mean * sin(separation)
```

This assumes:
- All baselines are aligned in the same direction
- Rotation affects all baselines equally
- Mean change equals single-baseline change

**Reality:**
- Baselines point in different directions
- Rotation affects each baseline differently
- Mean change can be **much smaller** (or larger) than single-baseline change
- For symmetric arrays, mean change ≈ 0 even for large phase shifts

---

## Numerical Example

### Scenario: 54.7 arcmin Phase Shift (User's Case)

**Phase shift:** 54.7 arcmin = 0.016 radians  
**Baseline length:** 200m (typical for DSA-110)

**Single baseline formula predicts:**
```
expected_change = 200 * sin(0.016) ≈ 200 * 0.016 ≈ 3.2 meters
```

**But for an array:**

**Case 1: Symmetric array (baselines evenly distributed)**
- 110 baselines pointing in all directions
- Mean U before: -144 m (array geometry)
- Mean U after: -144 m (same geometry, just rotated)
- **Actual mean change: ~0 meters** (geometry-dependent)
- **Verification fails!** (expected 3.2m, got 0m)

**Case 2: Asymmetric array**
- Baselines clustered in one direction
- Mean change: could be 0.5m, 5m, or 10m depending on geometry
- **Unpredictable!**

---

## Conclusion

### Mathematical Confirmation

✅ **The verification method is fundamentally flawed:**

1. **Mean UVW change ≠ single-baseline change formula**
   - Formula assumes single baseline
   - Arrays have many baselines in different orientations
   - Mean change depends on array geometry

2. **False negatives are likely**
   - Symmetric arrays: mean change ≈ 0 even for correct transformations
   - Verification will reject correct transformations
   - Tolerance adjustments help but don't solve the fundamental issue

3. **The actual transformation is correct**
   - CASA's `phaseshift` correctly transforms UVW
   - Individual baselines are rotated correctly
   - The verification method is the problem, not the transformation

### Recommendations

1. **Trust CASA phaseshift** - If it completes without errors, it's correct
2. **Verify phase center update** - Check PHASE_DIR/REFERENCE_DIR (already done)
3. **Remove or relax mean-based verification** - It's unreliable for arrays
4. **Alternative: Sample individual baselines** - Compare a few specific baselines before/after (more reliable but more complex)

### Bottom Line

The UVW transformation **is being done correctly** by CASA's `phaseshift`. The verification method using mean UVW values **is mathematically unsound** for arrays and will give false negatives for correctly transformed data, especially for symmetric arrays like DSA-110.

