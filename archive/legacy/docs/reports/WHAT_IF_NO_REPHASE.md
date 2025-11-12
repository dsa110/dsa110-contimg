# What If We Don't Rephase? Would That Solve the Problem?

**Date:** 2025-11-05  
**Question:** What if we didn't rephase the data at all, would that also solve our problem?

---

## Scenario Analysis

### Current Situation

1. **Original MS phase center:** Meridian (Position A = RA=LST(midpoint), Dec=pointing_dec)
2. **Calibrator position:** Position B (~1° = 54 arcmin away from meridian)
3. **Current workflow:**
   - Rephase MS: Position A → Position B (using `phaseshift`)
   - `ft()` uses: Position A (old phase center) ❌
   - Result: 102° phase scatter (wrong!)

### What If We Don't Rephase?

**Scenario:** Keep MS at original meridian phase center (Position A)

1. **MS phase center:** Position A (meridian) ✓
2. **Calibrator position:** Position B (1° offset) ✓
3. **`ft()` would use:** Position A (which is the actual MS phase center) ✓
4. **Component list:** Position B (calibrator)
5. **MODEL_DATA calculation:** Source at Position B relative to Position A
6. **Result:** ~102° phase scatter (but this is CORRECT for a 1° offset!)

---

## Key Insight

### Why This Might Work

If we **don't rephase**:
- ✅ **MS phase center** = Position A (meridian)
- ✅ **`ft()` uses** Position A (matches MS phase center)
- ✅ **DATA column** phased to Position A (meridian)
- ✅ **MODEL_DATA** calculated relative to Position A (meridian)
- ✅ **Both DATA and MODEL_DATA** have phase structure for source 1° away
- ✅ **They should MATCH!**

### Why This Would Work

**The phase scatter would be ~102°, but that's CORRECT because:**
- The calibrator IS 1° away from the phase center
- Phase scatter of ~102° is expected for a 1° offset
- DATA and MODEL_DATA would both have the same phase structure
- Calibration would work because DATA and MODEL_DATA are aligned

---

## Comparison: Rephase vs Don't Rephase

### Option 1: Rephase (Current - Broken)

| Item | Value | Status |
|------|-------|--------|
| MS phase center | Position B (calibrator) | ✓ Correct |
| DATA column | Phased to Position B | ✓ Correct |
| `ft()` uses | Position A (old) | ❌ Wrong! |
| MODEL_DATA | Calculated relative to Position A | ❌ Wrong! |
| Phase scatter | 102° | ❌ Wrong (should be < 10°) |
| DATA vs MODEL | 145° mismatch | ❌ Misaligned |

**Result:** Calibration fails (DATA and MODEL_DATA misaligned)

### Option 2: Don't Rephase (Proposed)

| Item | Value | Status |
|------|-------|--------|
| MS phase center | Position A (meridian) | ✓ Correct |
| DATA column | Phased to Position A | ✓ Correct |
| `ft()` uses | Position A (matches MS) | ✓ Correct! |
| MODEL_DATA | Calculated relative to Position A | ✓ Correct! |
| Phase scatter | ~102° | ✓ Correct (source is 1° away) |
| DATA vs MODEL | ~0° mismatch | ✓ Aligned! |

**Result:** Calibration should work (DATA and MODEL_DATA aligned, even though scatter is high)

---

## Why Rephasing Seems Necessary (But Isn't)

### The Intuition

**Why we rephase:**
- Put calibrator at phase center → minimal phase scatter (< 10°)
- Better SNR for calibration
- Standard practice in interferometry

**The problem:**
- `ft()` doesn't work correctly after rephasing
- It uses old phase center instead of new one
- This breaks the alignment between DATA and MODEL_DATA

### The Alternative

**If we don't rephase:**
- Calibrator stays 1° away from phase center
- Phase scatter is ~102° (high, but CORRECT)
- `ft()` uses correct phase center (matches MS)
- DATA and MODEL_DATA are aligned
- Calibration should work!

---

## Trade-offs

### Don't Rephase (Use Meridian Phase Center)

**Pros:**
- ✅ `ft()` works correctly (uses MS phase center)
- ✅ DATA and MODEL_DATA aligned
- ✅ Calibration should work
- ✅ No need for manual MODEL_DATA calculation
- ✅ Simpler workflow

**Cons:**
- ⚠️ Phase scatter is ~102° (high, but correct for 1° offset)
- ⚠️ May have slightly lower SNR than if calibrator were at phase center
- ⚠️ But this is expected for a 1° offset

### Rephase (Current - Broken)

**Pros:**
- ✅ If `ft()` worked correctly, would give < 10° phase scatter
- ✅ Better SNR (if it worked)

**Cons:**
- ❌ `ft()` doesn't work correctly after rephasing
- ❌ DATA and MODEL_DATA misaligned
- ❌ Calibration fails
- ❌ Requires manual MODEL_DATA calculation workaround

---

## Recommendation

**If we don't rephase, we could:**

1. **Use `ft()` directly** (it would work correctly!)
2. **No need for manual calculation** (`use_manual=False` would work)
3. **DATA and MODEL_DATA would be aligned**
4. **Calibration should succeed**

**The catch:**
- Phase scatter would be ~102° instead of < 10°
- But this is CORRECT for a calibrator 1° away from phase center
- The important thing is that DATA and MODEL_DATA match

---

## Test This Hypothesis

To verify this would work:

1. **Skip rephasing** (comment out `_rephase_ms_to_calibrator()` call)
2. **Use `ft()` directly** (`use_manual=False`)
3. **Check MODEL_DATA phase scatter** (should be ~102°, but CORRECT)
4. **Check DATA vs MODEL_DATA alignment** (should be < 20°)
5. **Run calibration** (should work!)

---

## Conclusion

**Yes, not rephasing might solve the problem!**

The key insight:
- The problem isn't the 102° phase scatter itself
- The problem is that DATA and MODEL_DATA are misaligned
- If we don't rephase, `ft()` uses the correct phase center (meridian)
- DATA and MODEL_DATA would both be calculated relative to meridian
- They would match, even though scatter is high

**This is a simpler solution than manual calculation!**

---

## Next Steps

1. **Test hypothesis:** Skip rephasing, use `ft()` directly
2. **Verify:** Check DATA vs MODEL_DATA alignment
3. **If it works:** Update workflow to skip rephasing (or make it optional)
4. **If it doesn't work:** Stick with manual calculation after rephasing

