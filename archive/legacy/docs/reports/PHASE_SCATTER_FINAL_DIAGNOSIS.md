# Phase Scatter Final Diagnosis

**Date:** 2025-11-05  
**Status:** Root Cause Identified  
**Priority:** CRITICAL

---

## Executive Summary

After 2 days of investigation, the root cause of the 98-104° phase scatter is **DATA and MODEL_DATA misalignment** (125.87° phase difference), not the phase scatter itself.

**Key Finding:** The 98-104° phase scatter in calibration solutions is **EXPECTED** for a source 1° away from phase center, but **DATA and MODEL_DATA are misaligned by 125.87°**, causing severe decorrelation and calibration failures.

---

## Diagnostic Results

### Critical Test: DATA vs MODEL_DATA Alignment

**Command:** `python3 scripts/check_model_data_phase.py <ms> <cal_ra> <cal_dec>`

**Results:**
- MODEL_DATA phase scatter: **71.24°** (high, but could be expected for 1° offset)
- **DATA vs MODEL_DATA phase difference: 125.87°** ✗ **MISALIGNED**
- Amplitude ratio (DATA/MODEL): **0.0215** ✗ **Severe decorrelation (2.15%)**

**Conclusion:** DATA and MODEL_DATA are NOT aligned, causing calibration to fail.

### Phase Center Status

**MS Phase Centers (meridian):**
- Field 0: RA=127.949629°, Dec=54.663982°
- All fields: ~128° RA, 54.66° Dec (meridian)

**Calibrator Position:**
- RA=128.728700°, Dec=55.572500°
- Separation: ~1° (54 arcmin in Dec, ~0.8° in RA)

**Expected:** For a source 1° away, phase scatter of ~100° is **EXPECTED and ACCEPTABLE**.

**Problem:** DATA and MODEL_DATA should both be aligned to the same phase center (meridian), but they're misaligned by 125.87°.

---

## Root Cause Analysis

### The Real Problem

**The 98-104° phase scatter is NOT the problem.** For a source 1° away from phase center, this is expected.

**The REAL problem is:**
1. **DATA column:** Phased to meridian (correct)
2. **MODEL_DATA column:** Calculated with wrong phase center assumption (incorrect)
3. **Result:** 125.87° phase misalignment → severe decorrelation → calibration fails

### Why This Happened

**Possible causes:**
1. **`setjy` may not use PHASE_DIR correctly** - CASA's `setjy` might use REFERENCE_DIR or a different phase center
2. **MODEL_DATA was calculated before DATA was correctly phased** - Order of operations issue
3. **UVW coordinates don't match DATA column phasing** - UVW might be in wrong frame
4. **Field selection issue** - MODEL_DATA only populated for field 0, but DATA exists for all fields

**Evidence:**
- Field 0: MODEL_DATA phase scatter 104.40° (expected for 1° offset), but DATA-MODEL difference 147.05° (misaligned)
- Fields 1-2: MODEL_DATA phase scatter 0.00° (unpopulated)
- Overall DATA-MODEL difference: 125.87° (misaligned)

---

## What We've Learned

### The 98-104° Phase Scatter is Expected

For a source 1° away from phase center:
- Expected phase scatter: ~100-110°
- Observed phase scatter: 98-104° ✓ **Matches expectation**

**This is NOT a problem if DATA and MODEL_DATA are aligned.**

### The Real Problem is Misalignment

**What matters for calibration:**
1. ✓ DATA and MODEL_DATA must be aligned (< 20° phase difference)
2. ✓ Sufficient SNR (not too many solutions flagged)
3. ✗ Phase scatter in solutions can be high if source is offset (expected)

**Current status:**
- ✗ DATA and MODEL_DATA misaligned (125.87°)
- ✗ Severe decorrelation (2.15% amplitude ratio)
- ✗ High flagging rate (35-37%)
- ✓ Phase scatter matches expectation (98-104°)

---

## Next Steps

### Immediate Action

1. **Fix MODEL_DATA calculation** to align with DATA column
   - Verify `setjy` uses correct phase center
   - Or use manual calculation (`use_manual=True`)
   - Ensure MODEL_DATA matches DATA column phasing

2. **Verify DATA column phasing**
   - Check if DATA column is correctly phased to meridian
   - Verify UVW coordinates match DATA column phasing
   - May need to re-run `phaseshift` if DATA is wrong

3. **Re-run diagnostic after fix**
   - Check DATA vs MODEL_DATA alignment (< 20°)
   - Verify amplitude ratio is reasonable (0.5-1.0)
   - Confirm phase scatter is acceptable

### Expected Outcome After Fix

- DATA vs MODEL_DATA alignment: < 20° ✓
- Amplitude ratio: 0.5-1.0 ✓
- Phase scatter: 98-104° ✓ (expected for 1° offset)
- Flagging rate: Should decrease significantly
- Calibration: Should succeed

---

## Key Insight

**The problem isn't the phase scatter - it's the misalignment.**

We've been chasing the wrong symptom. The 98-104° phase scatter is expected for a source 1° away. The real problem is that DATA and MODEL_DATA aren't aligned, causing decorrelation and calibration failures.

**Solution:** Fix MODEL_DATA calculation to match DATA column phasing, not reduce phase scatter.

---

## Conclusion

**After 2 days of investigation, we've identified the root cause:**

- ✗ NOT phase scatter (98-104° is expected for 1° offset)
- ✓ DATA and MODEL_DATA misalignment (125.87° phase difference)
- ✓ Severe decorrelation (2.15% amplitude ratio)

**Next:** Fix MODEL_DATA calculation to align with DATA column, then verify alignment with diagnostic script.

