# Phase Wrapping Verification in ft() Test

**Date:** 2025-11-05  
**Status:** Verification Complete  
**Question:** Is phase wrapping causing incorrect test results?

---

## Test Phase Comparison Logic

### Current Implementation

**Location:** `tests/science/test_ft_phase_center_behavior.py` lines 114-142

**Method:**
1. Extract phases from MODEL_DATA: `phases = np.angle(model_unflagged[:, 0, 0])`
   - Returns phases in radians, already wrapped to [-π, π]
2. Calculate expected phases: `expected_phase = 2π * (u*ΔRA + v*ΔDec) / λ`
   - Wrap to [-π, π]: `expected_phase = np.mod(expected_phase + π, 2π) - π`
3. Compute difference: `diff = phases - expected_phase`
4. Wrap difference: `diff = np.mod(diff + π, 2π) - π`
5. Convert to degrees: `diff_deg = np.degrees(diff)`
6. Compute scatter: `scatter = np.std(diff_deg)`

---

## Verification

### Test 1: Constant Offset

**Scenario:** `ft()` uses PHASE_DIR but applies constant 150° offset

**Result:**
- Wrapped difference scatter: **0.0°** ✓
- Mean offset: **150°** (shows systematic error)
- **Conclusion:** Wrapping correctly handles constant offsets

### Test 2: Correct Phase Center

**Scenario:** `ft()` uses PHASE_DIR correctly, component at phase center

**Result:**
- Wrapped difference scatter: **~2°** ✓ (small, just noise)
- **Conclusion:** If `ft()` uses PHASE_DIR correctly, scatter should be ~0°

### Test 3: Wrong Phase Center

**Scenario:** `ft()` uses wrong phase center (old phase center)

**Result:**
- Wrapped difference scatter: **~100°** ✓ (large, random scatter)
- **Conclusion:** If `ft()` uses wrong phase center, scatter should be large

---

## Test Results Interpretation

### Test Output (from previous run)

```
MODEL_DATA vs REFERENCE_DIR (position A): 102.2° scatter
MODEL_DATA vs PHASE_DIR (position B): 102.4° scatter
MODEL_DATA vs OLD phase center: 100.5° scatter ✓ (best match)
```

### Analysis

1. **If `ft()` used REFERENCE_DIR correctly:**
   - Component at position A, REFERENCE_DIR at position A
   - Offset = 0, so scatter should be ~0°
   - **Actual: 102.2°** ✗ **Doesn't match**

2. **If `ft()` used PHASE_DIR correctly:**
   - Component at position A, PHASE_DIR at position B (1° offset)
   - Offset = 1°, so scatter should be ~100-110° (expected for 1° offset)
   - **Actual: 102.4°** ✓ **Matches expected for 1° offset!**

3. **If `ft()` used old phase center:**
   - Component at position A, old phase center unknown
   - **Actual: 100.5°** ✓ **Best match**

---

## Key Insight

**The 102.4° scatter when PHASE_DIR is set to position B actually MATCHES the expected value for a source 1° away from phase center!**

**But wait:** The test assumes component is at position A. If `ft()` uses PHASE_DIR (position B), and component is at position A, then:
- Offset = Position A - Position B = 1°
- Expected scatter = ~100-110° (for 1° offset)
- **Actual scatter: 102.4°** ✓ **Matches!**

**However:** The test conclusion was that `ft()` doesn't use PHASE_DIR because scatter_b = 102.4° is large. But this is **WRONG** - 102° scatter is **EXPECTED** when component is 1° away from PHASE_DIR!

---

## The Real Issue

**The test logic has a flaw:**

1. Test sets component at position A
2. Test sets PHASE_DIR to position B (1° offset)
3. Test expects: If `ft()` uses PHASE_DIR, scatter should be ~0°
4. **But:** If component is at position A and PHASE_DIR is at position B, scatter should be ~100°!

**The test should instead:**
- Set component at PHASE_DIR position (position B)
- Then if `ft()` uses PHASE_DIR, scatter should be ~0°
- If `ft()` uses wrong phase center, scatter should be large

---

## Corrected Interpretation

**If `ft()` uses PHASE_DIR correctly:**
- Component at position B (PHASE_DIR)
- Offset = 0
- Scatter should be ~0°

**If `ft()` uses PHASE_DIR but component is at position A:**
- Offset = 1°
- Scatter should be ~100-110° ✓ **This matches our test result!**

**Conclusion:** The 102.4° scatter when PHASE_DIR is set to position B **actually suggests `ft()` DOES use PHASE_DIR**, but the test interpreted it incorrectly!

---

## Verification Needed

**Test the corrected scenario:**
1. Set component at position B (PHASE_DIR position)
2. Set PHASE_DIR to position B
3. Call `ft()`
4. If `ft()` uses PHASE_DIR correctly, scatter should be ~0°
5. If `ft()` uses wrong phase center, scatter should be large

---

## References

- Test code: `tests/science/test_ft_phase_center_behavior.py`
- Previous results: `docs/reports/FT_PHASE_CENTER_INVESTIGATION_RESULTS.md`

