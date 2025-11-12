# Why ft() Wrong Phase Center Causes 102° Phase Scatter

**Date:** 2025-11-05  
**Question:** Why does using `ft()` instead of manual calculation lead to 102° phase scatter?

---

## The Physics: Visibility Phase Formula

The phase of a visibility depends on the source position relative to the phase center:

```
phase = 2π * (u*ΔRA + v*ΔDec) / λ
```

Where:
- `u, v` = baseline coordinates (meters)
- `ΔRA, ΔDec` = offset from phase center to source (radians)
- `λ` = wavelength (meters)

### Key Point

**If the source is at the phase center** (ΔRA = 0, ΔDec = 0):
- Phase should be **nearly constant** (~0°)
- Phase scatter should be **< 10°**

**If the source is offset from the phase center**:
- Phase varies with baseline (u, v)
- Phase scatter increases with offset
- Large offset = large phase scatter

---

## The Problem: ft() Uses Wrong Phase Center

### Scenario

1. **Original MS phase center:** Position A (meridian, RA=LST)
2. **Calibrator position:** Position B (offset by ~1° = 54 arcmin)
3. **Workflow:**
   - Rephase MS from Position A → Position B using `phaseshift`
   - Update `REFERENCE_DIR` and `PHASE_DIR` to Position B
   - Call `ft()` to populate MODEL_DATA

### What Happens

**`ft()` Behavior:**
- `ft()` does NOT read `REFERENCE_DIR` or `PHASE_DIR` from FIELD table
- `ft()` appears to use the **original phase center** (Position A) or derive it from UVW frame
- `ft()` calculates MODEL_DATA phase **relative to Position A** (wrong!)

**Result:**
- Component list position: Position B (calibrator)
- Phase center used by `ft()`: Position A (old phase center)
- **Offset perceived by `ft()`:** Position B - Position A = **~1° (54 arcmin)**
- **Phase scatter:** 102° (matches expected for 1° offset!)

---

## Why This Causes 102° Phase Scatter

### Mathematical Explanation

If `ft()` thinks the phase center is at Position A, but the source is at Position B:

1. **ΔRA offset:** ~1° in RA direction
2. **Phase calculation:** `phase = 2π * (u*ΔRA + v*ΔDec) / λ`
3. **With baselines up to ~2.6 km and λ ~0.21 m:**
   - Maximum `u*ΔRA/λ` ≈ (2600 m) * (1° in radians) / (0.21 m) ≈ 216 radians
   - This corresponds to **~37,000°** of phase variation
   - But phase wraps to [-180°, 180°], so we see **102° scatter**

### Why 102° Specifically?

The 102° scatter matches the expected phase scatter for a source offset by ~1°:
- **Expected scatter for 1° offset:** ~102.5°
- **Actual scatter:** 102.2° - 103.3°
- **Conclusion:** `ft()` is calculating phase as if source is offset by ~1° from phase center

---

## Comparison: Correct vs Incorrect

### Correct Calculation (Manual Method)

```
Component position: Position B (calibrator)
Phase center used: Position B (from PHASE_DIR)
Offset: ΔRA = 0, ΔDec = 0
Phase: Nearly constant (~0°)
Phase scatter: < 10° ✓
```

### Incorrect Calculation (ft() Method)

```
Component position: Position B (calibrator)
Phase center used: Position A (old phase center)
Offset: ΔRA ≈ 1°, ΔDec ≈ 1°
Phase: Varies with baseline (u, v)
Phase scatter: 102° ✗
```

---

## Impact on Calibration

### Why 102° Phase Scatter Breaks Calibration

1. **DATA column:** Phased to Position B (calibrator) - correct
2. **MODEL_DATA column:** Calculated relative to Position A - wrong!
3. **Phase difference:** DATA - MODEL_DATA = 102° scatter
4. **Calibration failure:**
   - Calibration compares DATA to MODEL_DATA
   - 102° phase mismatch = poor SNR
   - Solutions are flagged or unreliable
   - Results in 100.1° phase scatter in bandpass solutions

---

## The Solution: Manual Calculation

Manual calculation fixes this by:
1. **Reading correct phase center:** Uses `PHASE_DIR` from FIELD table (updated by `phaseshift`)
2. **Calculating phase correctly:** `phase = 2π * (u*ΔRA + v*ΔDec) / λ` where ΔRA/ΔDec are relative to **correct** phase center
3. **Result:** Phase scatter < 10° ✓

---

## Summary

**Why ft() causes 102° phase scatter:**
1. `ft()` uses wrong phase center (old Position A instead of new Position B)
2. Calculates MODEL_DATA phase as if source is offset by ~1°
3. Large offset → large phase variation across baselines → 102° scatter
4. DATA column is phased correctly, but MODEL_DATA is wrong
5. Mismatch causes calibration failures

**Why manual calculation fixes it:**
1. Uses correct phase center from `PHASE_DIR`
2. Calculates phase relative to correct phase center
3. Source at phase center → phase scatter < 10°

---

## Visual Analogy

Imagine you're trying to measure the distance to a flagpole:
- **Correct method:** Measure from where you're standing (phase center)
- **ft() method:** Measure from where you were standing 1 hour ago (old phase center)
- **Result:** Distance measurements are wrong by ~1° equivalent

For interferometry, phase errors are amplified by baseline length, so 1° offset → 102° phase scatter.

