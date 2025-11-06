# ft() "Broken" Message Clarification

**Date:** 2025-11-05  
**Status:** Message Updated to Reflect Current Understanding  
**Priority:** Documentation Clarity

---

## Issue Identified

The calibration CLI was printing a contradictory message:
- `DEBUG: Using manual MODEL_DATA calculation (ft() is broken - see CASA_FUNCTION_BEHAVIOR_100_PERCENT_VERIFIED.md)...`
- `DEBUG: write_point_model_with_ft completed`

This was misleading because:
1. The code says "ft() is broken" but then calls `write_point_model_with_ft(..., use_manual=True)`
2. With `use_manual=True`, `ft()` is **not** being used - it's bypassed entirely
3. The message references a document (`CASA_FUNCTION_BEHAVIOR_100_PERCENT_VERIFIED.md`) that the user explicitly said not to trust

---

## Root Cause Analysis

### Previous Evidence (May Be Outdated)

Previous tests (see `docs/reports/FT_PHASE_CENTER_INVESTIGATION_RESULTS.md`) showed:
- `ft()` had ~102° phase scatter after rephasing
- `ft()` didn't match `REFERENCE_DIR` (102.2° scatter)
- `ft()` didn't match `PHASE_DIR` (102.4° scatter)
- `ft()` matched old phase center best (100.5° scatter)

**Hypothesis:** `ft()` uses UVW frame directly, and if UVW wasn't correctly transformed by `phaseshift`, `ft()` would fail.

### Current Situation

Since we fixed the UVW verification issues:
- We now trust that `phaseshift` correctly transforms UVW coordinates
- If UVW is correctly transformed, `ft()` should work correctly (if it uses UVW frame)
- The previous evidence may have been based on incorrect UVW transformations

### Why We Still Use Manual Calculation

We use manual calculation (`use_manual=True`) as a **conservative approach**:
- Guarantees correct phase structure regardless of `ft()` behavior
- Explicitly uses `REFERENCE_DIR` and UVW to compute phases
- Bypasses potential issues with `ft()` phase center detection
- More reliable than depending on `ft()` behavior

This is **not** because we've proven `ft()` is broken, but because manual calculation is more reliable.

---

## Code Changes

### Updated Message

**Before:**
```python
print(f"DEBUG: Using manual MODEL_DATA calculation (ft() is broken - see CASA_FUNCTION_BEHAVIOR_100_PERCENT_VERIFIED.md)...")
```

**After:**
```python
print(f"DEBUG: Using manual MODEL_DATA calculation (bypassing ft() for guaranteed phase correctness)...")
```

### Updated Comments

**Before:**
```python
# CRITICAL FIX: ft() does NOT use correct phase center (REFERENCE_DIR/PHASE_DIR).
# We verified through empirical testing that ft() has ~101° phase scatter even
# when component is at phase center. This causes 80%+ bandpass solution flagging.
# The manual calculation explicitly uses REFERENCE_DIR and UVW to compute correct phases.
```

**After:**
```python
# NOTE: Previous tests (see docs/reports/FT_PHASE_CENTER_INVESTIGATION_RESULTS.md) showed
# ft() had ~102° phase scatter after rephasing, suggesting it doesn't use REFERENCE_DIR/PHASE_DIR.
# However, the hypothesis was that ft() uses UVW frame, and if UVW wasn't correctly transformed,
# ft() would fail. Since we now trust phaseshift correctly transforms UVW, ft() may work correctly.
# We use manual calculation as a conservative approach to ensure correct phase structure.
# If you want to test ft() instead, set use_manual=False and verify MODEL_DATA phase structure.
```

---

## Implications

### Current Approach (Conservative)

- Uses manual calculation by default (`use_manual=True`)
- Guarantees correct phase structure
- More reliable than depending on `ft()` behavior
- No risk of calibration failures due to phase center issues

### Testing ft() (If Desired)

If you want to test whether `ft()` works correctly now that UVW transformation is fixed:
1. Set `use_manual=False` in the calibration CLI
2. Run calibration and verify MODEL_DATA phase structure
3. Check if phase scatter is < 1° (should be for point source at phase center)
4. If phase scatter is acceptable, `ft()` may work correctly

---

## Conclusion

The "ft() is broken" message was misleading because:
1. We're not using `ft()` (bypassing it with `use_manual=True`)
2. The evidence may be outdated (based on incorrect UVW transformations)
3. The message referenced a document the user doesn't trust

The updated message:
- Clarifies we're using manual calculation as a conservative approach
- Acknowledges previous test results but notes they may be outdated
- Suggests testing `ft()` if desired (with `use_manual=False`)
- Doesn't make definitive claims about `ft()` being broken

---

## Files Modified

1. `src/dsa110_contimg/calibration/cli.py`:
   - Updated debug message to clarify we're bypassing `ft()` for guaranteed correctness
   - Updated comments to reflect current understanding
   - Removed reference to `CASA_FUNCTION_BEHAVIOR_100_PERCENT_VERIFIED.md`

