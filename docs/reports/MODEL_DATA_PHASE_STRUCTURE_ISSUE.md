# MODEL_DATA Phase Structure Issue

**Date:** 2025-11-04  
**Status:** Critical Issue Identified  
**Priority:** Critical - Causes calibration failures

---

## Problem Summary

**MODEL_DATA has incorrect phase structure** despite:
- ✓ MS phase center correctly aligned (REFERENCE_DIR matches calibrator within 0.0018 arcmin)
- ✓ MODEL_DATA amplitude is correct (2.5 Jy, constant)
- ✗ MODEL_DATA phase scatter is 103.3° (expected < 10° for point source at phase center)

**Impact:**
- Pre-bandpass phase solve fails (102.5° phase scatter)
- Bandpass calibration fails (low SNR, high flagging)
- Calibration solutions are scientifically invalid

---

## Diagnostic Results

### MS Phase Center Status
- **REFERENCE_DIR:** RA=128.728753°, Dec=55.572499°
- **Calibrator:** RA=128.728700°, Dec=55.572500°
- **Separation:** 0.0018 arcmin ✓ (correctly aligned)

### MODEL_DATA Status
- **Amplitude:** median=2.500 Jy, std=0.000 Jy ✓ (correct)
- **Phase scatter:** 103.3° ✗ (should be < 10°)
- **Expected phase scatter:** 0.3° (based on source offset)
- **Actual - Expected phase scatter:** 103.3° ✗ (doesn't match expected)

### Root Cause Analysis

**The problem:** `ft()` calculated MODEL_DATA with **incorrect phase structure**.

**Evidence:**
1. MS phase center is correctly aligned (verified)
2. MODEL_DATA amplitude is correct (2.5 Jy constant)
3. MODEL_DATA phase scatter is 103.3° (should be ~0.3°)
4. Phase doesn't match expected structure

**Possible causes:**
1. `ft()` not using REFERENCE_DIR for phase calculations
2. Component list position doesn't match MS phase center exactly
3. `ft()` has a bug with phase calculation after rephasing
4. MODEL_DATA was written before rephasing and not properly recalculated

---

## Technical Details

### Expected Phase Structure

For a point source at the phase center:
- Phase should be **nearly constant** (or smoothly varying with UVW)
- Phase scatter should be **< 10 degrees**
- For offset < 0.1 arcsec: phase scatter should be **< 0.5 degrees**

### Actual Phase Structure

- Phase scatter: **103.3 degrees** (completely wrong)
- Phase range: -180° to +180° (full range, indicates random phase)
- Phase doesn't correlate with UVW (should for point source)

### Comparison with Expected

- **Expected phase scatter:** 0.3° (based on 0.1 arcsec offset)
- **Actual phase scatter:** 103.3°
- **Difference:** 103.0° (MODEL_DATA phase is completely wrong)

---

## Code Flow Analysis

### Current Workflow

1. MS rephased (REFERENCE_DIR updated) ✓
2. `clearcal()` called to clear MODEL_DATA ✓
3. MODEL_DATA manually cleared with zeros ✓
4. `ft()` called with component list at calibrator position ✓
5. MODEL_DATA written with wrong phase structure ✗

### Issue Location

**Function:** `write_point_model_with_ft()` in `src/dsa110_contimg/calibration/model.py`

**Problem:** `ft()` is called but produces MODEL_DATA with incorrect phase structure.

**Possible explanations:**
- `ft()` might not be using REFERENCE_DIR internally
- `ft()` might be using PHASE_DIR instead of REFERENCE_DIR
- Component list position might not match REFERENCE_DIR exactly
- There's a timing issue where `ft()` reads phase center before it's updated

---

## Investigation Needed

1. **Verify component list position**
   - Check if component list position exactly matches REFERENCE_DIR
   - Even 0.1 arcsec difference can cause phase scatter

2. **Check ft() phase center usage**
   - Does `ft()` use REFERENCE_DIR or PHASE_DIR?
   - Does `ft()` read phase center at the right time?

3. **Test ft() with explicit phase center**
   - Try calling `ft()` with explicit phase center parameter
   - Verify if this fixes the phase structure

4. **Check for timing issues**
   - Is there a delay between rephasing and MODEL_DATA population?
   - Does `ft()` cache phase center information?

---

## Recommended Fixes

### Option 1: Explicit Phase Center in ft()

If `ft()` supports explicit phase center, use it:

```python
ft(vis=ms_path, complist=comp_path, usescratch=True, 
   phasecenter=f"J2000 {ra_deg}deg {dec_deg}deg")
```

### Option 2: Verify Component List Position

Ensure component list position **exactly** matches REFERENCE_DIR:
- Check component list creation
- Verify coordinate precision
- Ensure no rounding errors

### Option 3: Force ft() to Re-read Phase Center

After rephasing, force `ft()` to re-read phase center:
- Close and reopen MS
- Or use explicit phase center parameter

### Option 4: Calculate MODEL_DATA Manually

If `ft()` can't be fixed, calculate MODEL_DATA manually:
- Use UVW and source position
- Calculate phase: `phase = 2π * (u*ΔRA + v*ΔDec) / λ`
- Set amplitude: constant flux

---

## Test Cases

### Test 1: Verify ft() Phase Center Usage

```python
# After rephasing, check what phase center ft() uses
# Compare with REFERENCE_DIR
```

### Test 2: Test Explicit Phase Center

```python
# Call ft() with explicit phasecenter parameter
# Compare MODEL_DATA phase structure
```

### Test 3: Manual MODEL_DATA Calculation

```python
# Calculate MODEL_DATA manually
# Compare phase structure with ft() output
```

---

## References

- CASA ft() documentation: https://casa.nrao.edu/casadocs/
- MODEL_DATA phase structure requirements
- Calibration phase center requirements

---

## Next Steps

1. **Immediate:** Investigate `ft()` phase center usage
2. **Short-term:** Test explicit phase center parameter
3. **Long-term:** Consider manual MODEL_DATA calculation if `ft()` can't be fixed

**Critical:** This issue must be fixed before calibration can proceed. Calibration solutions are currently scientifically invalid due to incorrect MODEL_DATA phase structure.

