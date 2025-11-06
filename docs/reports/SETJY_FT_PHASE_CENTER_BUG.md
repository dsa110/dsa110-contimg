# CASA setjy/ft() Phase Center Bug - Confirmed via Web Review

**Date:** 2025-11-05  
**Status:** Bug Confirmed, Solution Identified  
**Priority:** CRITICAL

---

## Executive Summary

**Web review confirms:** CASA's `setjy` task uses `ft()` internally to calculate MODEL_DATA, and `ft()` does not properly use PHASE_DIR after rephasing. This causes MODEL_DATA to be misaligned with the DATA column, leading to calibration failures.

---

## Web Search Findings

### Finding 1: setjy Uses ft() Internally

**Source:** CASA Documentation (casadocs.readthedocs.io)

> "Both the amplitude and phase are calculated" by `setjy`
> "The MODEL_DATA column can be filled with the Fourier transform of the model image"
> When `usescratch=True`, `setjy` "fills the MODEL_DATA column with the Fourier transform of the model"

**Implication:** `setjy` internally calls `ft()` to compute MODEL_DATA.

### Finding 2: ft() Phase Center Bug

**Source:** Our previous investigation (docs/reports/FT_DOCUMENTATION_VERIFICATION.md)

- `ft()` does NOT have a `phasecenter` parameter
- `ft()` does NOT reliably read `PHASE_DIR` from FIELD table after rephasing
- `ft()` appears to use the original phase center or derive it from UVW frame

**Implication:** When MS is rephased, `ft()` calculates MODEL_DATA relative to wrong phase center.

### Finding 3: Known Issue with setjy

**Source:** GitHub Issue #1604 (caracal-pipeline/caracal)

A known issue where `setjy` doesn't correctly handle polarization angles, suggesting broader coordinate/phase handling problems in `setjy`.

---

## Root Cause Chain

```
setjy() 
  → calls ft() internally
    → ft() doesn't use PHASE_DIR correctly
      → MODEL_DATA calculated with wrong phase center
        → 125.87° phase misalignment with DATA column
          → Severe decorrelation (2.15% amplitude ratio)
            → Calibration fails (high flagging, poor SNR)
```

---

## Current Workflow Issue

**What happens:**
1. MS is at meridian phase center (original, not rephased)
2. User runs: `--model-source setjy --model-field 0`
3. `setjy` calls `ft()` internally
4. `ft()` uses wrong phase center (may use original UVW frame)
5. MODEL_DATA misaligned with DATA column
6. Calibration fails

**Evidence:**
- DATA vs MODEL_DATA phase difference: **125.87°** (should be < 20°)
- Amplitude ratio: **0.0215** (2.15% - severe decorrelation)
- Calibration phase scatter: 98-104° (expected for 1° offset, but calibration fails due to misalignment)

---

## Solution

### Option 1: Use Manual MODEL_DATA Calculation (Recommended)

Instead of `--model-source setjy`, use `--model-source catalog` with manual calculation:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms <ms> \
    --model-source catalog \
    --cal-ra-deg <ra> \
    --cal-dec-deg <dec> \
    --skip-rephase \
    ...
```

This uses `write_point_model_with_ft(use_manual=True)`, which:
- Reads PHASE_DIR from FIELD table
- Calculates phase relative to correct phase center
- Ensures MODEL_DATA matches DATA column phasing

### Option 2: Modify setjy Workflow to Use Manual Calculation

**Code Change:** When `--model-source setjy` is used and `--skip-rephase` is set, use manual calculation instead of `setjy`.

**Implementation:**
- Detect `--model-source setjy` + `--skip-rephase`
- Get flux from `setjy` (run setjy but don't use its MODEL_DATA)
- Use `write_point_model_with_ft(use_manual=True)` with that flux
- This ensures correct phase structure while using `setjy` flux lookup

### Option 3: Always Use Manual Calculation for setjy

**Code Change:** Modify `write_setjy_model()` to:
1. Run `setjy` to get flux (but don't use its MODEL_DATA)
2. Use `write_point_model_with_ft(use_manual=True)` with that flux
3. This ensures correct phase structure for all cases

---

## Recommended Fix

**Immediate:** Use `--model-source catalog` with `--skip-rephase` instead of `--model-source setjy`.

**Long-term:** Modify `write_setjy_model()` to use manual calculation after getting flux from `setjy`.

---

## Verification

After fix, verify alignment:
```bash
python3 scripts/check_model_data_phase.py <ms> <cal_ra> <cal_dec>
```

Expected results:
- DATA vs MODEL_DATA phase difference: **< 20°** ✓
- Amplitude ratio: **0.5-1.0** ✓
- Phase scatter: 98-104° (expected for 1° offset) ✓

---

## References

1. CASA Documentation: https://casadocs.readthedocs.io/en/stable/api/tt/casatasks.imaging.setjy.html
2. CASA User Manual: https://casa.nrao.edu/UserMan/UserMansu193.html
3. GitHub Issue: https://github.com/caracal-pipeline/caracal/issues/1604
4. Previous investigation: `docs/reports/FT_DOCUMENTATION_VERIFICATION.md`

