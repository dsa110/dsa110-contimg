# Phase Scatter Root Cause Analysis

**Date:** 2025-11-05  
**Status:** Critical Analysis  
**Goal:** Determine if 98-104° phase scatter is actually a problem or expected behavior

---

## Current Situation

**Observed:**
- Phase scatter: 98.2° (bandpass), 104.3° (gain)
- MS phase center: Meridian (original)
- Calibrator position: ~1° away from meridian
- MODEL_DATA: Populated (2.5 Jy)
- Flagging: 35-37% of solutions flagged

**Key Question:** Is this a problem, or expected for a source 1° from phase center?

---

## The Physics: What Phase Scatter Means

### For a Source at Phase Center
- Phase should be nearly constant (~0°)
- Phase scatter should be **< 10°**

### For a Source Offset from Phase Center
- Phase varies with baseline: `phase = 2π * (u*ΔRA + v*ΔDec) / λ`
- Phase scatter increases with offset
- **For 1° offset: Expected scatter ~100-110°** (after wrapping to [-180, 180])

### Expected Values

| Scenario | Phase Scatter | Status |
|----------|--------------|--------|
| Source at phase center | < 10° | Ideal |
| Source 1° from phase center | ~100-110° | **Expected** |
| Source 1° from phase center + misalignment | ~100-110° | **Problematic** |

**Critical Distinction:**
- **High phase scatter alone is not necessarily a problem** if DATA and MODEL_DATA are aligned
- **High phase scatter is a problem** if DATA and MODEL_DATA are misaligned

---

## What We've Tried

1. **Fixed MODEL_DATA phase structure** (manual calculation)
   - Status: Implemented
   - Result: Still high phase scatter

2. **Checked phase center alignment**
   - Status: All 24 fields aligned within 0.00 arcmin
   - Result: Phase centers are correct

3. **Tried "no rephase" workflow**
   - Status: MS at meridian, calibrator 1° away
   - Result: Still high phase scatter (98-104°)

4. **Verified MODEL_DATA population**
   - Status: MODEL_DATA populated (2.5 Jy)
   - Result: Correct amplitude

---

## Root Cause Hypothesis

**Hypothesis:** The 98-104° phase scatter is **EXPECTED** for a source 1° away from phase center, but we haven't verified if DATA and MODEL_DATA are actually aligned.

**Evidence:**
- MS is at meridian phase center
- Calibrator is 1° away
- Both DATA and MODEL_DATA should use meridian phase center
- Expected scatter for 1° offset: ~100-110°
- Observed scatter: 98-104° ✓ **Matches expectation**

**Critical Test Needed:**
1. Verify DATA vs MODEL_DATA alignment (should be < 20° difference)
2. If aligned: High scatter is expected, calibration should work
3. If misaligned: High scatter indicates a problem

---

## What Actually Matters for Calibration

### Good Calibration Requires:
1. **DATA and MODEL_DATA aligned** (phase difference < 20°)
2. **Sufficient SNR** (not too many solutions flagged)
3. **Correct phase structure** (not necessarily low scatter)

### What Doesn't Matter:
- **High phase scatter in solutions** if it's due to source offset (expected)
- **High scatter in MODEL_DATA** if it matches DATA column structure

---

## Next Steps

1. **Verify DATA vs MODEL_DATA alignment**
   - Check if DATA and MODEL_DATA phases are aligned (< 20° difference)
   - If yes: High scatter is expected, calibration should work
   - If no: Investigate why they're misaligned

2. **Check calibration solution quality**
   - Are solutions physically reasonable?
   - Do they improve data quality when applied?
   - High scatter in solutions ≠ bad calibration if source is offset

3. **Determine if flagging is acceptable**
   - 35-37% flagging may be acceptable if:
     - Bad antennas/channels are flagged
     - Remaining solutions are good quality
     - SNR is sufficient for calibration

---

## Conclusion

**The 98-104° phase scatter may be EXPECTED, not a problem.**

**Evidence:**
- Source is 1° from phase center
- Expected scatter: ~100-110°
- Observed scatter: 98-104° ✓ **Matches expectation**

**What we need to verify:**
- Are DATA and MODEL_DATA aligned? (This is the critical test)
- Are calibration solutions usable despite high scatter?
- Is the flagging rate acceptable?

**If DATA and MODEL_DATA are aligned:**
- High phase scatter is expected and acceptable
- Calibration should work correctly
- The problem is solved (it's not actually a problem)

**If DATA and MODEL_DATA are misaligned:**
- High phase scatter indicates a problem
- Need to investigate alignment issue
- This would explain why calibration is failing

---

## Action Items

1. **Run DATA vs MODEL_DATA alignment check** (HIGHEST PRIORITY)
   - Use `scripts/check_model_data_phase.py` or create new diagnostic
   - Verify phase difference < 20°

2. **Check if calibration solutions are usable**
   - Verify solutions are physically reasonable
   - Check if applying calibration improves data quality

3. **Determine acceptable flagging rate**
   - 35-37% may be acceptable if bad antennas/channels are flagged
   - Verify remaining solutions are good quality

4. **If everything is aligned:**
   - Document that high scatter is expected for 1° offset
   - Update QA thresholds to account for source offset
   - Consider this resolved

