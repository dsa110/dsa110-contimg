# ft() Phase Center Bug Fix

**Date:** 2025-11-05  
**Status:** Implemented  
**Priority:** CRITICAL - Root cause of 100°+ phase scatter

---

## Problem Summary

**Root Cause:** CASA's `ft()` task (used by `setjy` internally) does NOT use `PHASE_DIR` or `REFERENCE_DIR` from the FIELD table. Instead, it determines phase center from the DATA column's original phasing (UVW coordinates), which causes MODEL_DATA to be misaligned with DATA when the MS has been rephased.

**Impact:**
- 102-104° phase scatter in MODEL_DATA when MS is rephased
- MODEL_DATA misalignment with DATA column (125.87° phase difference)
- Calibration failures due to poor SNR
- High flagging rates (35-37%)

---

## Solution

### Automatic Use of Manual Calculation

**When rephasing is performed, automatically use manual MODEL_DATA calculation instead of `ft()`/`setjy`:**

1. **Catalog model (`--model-source catalog`):**
   - Already uses manual calculation (`use_manual=True`) when rephasing is done ✓
   - No changes needed

2. **setjy model (`--model-source setjy`):**
   - **NEW:** Detects if MS was rephased
   - If rephased AND calibrator coordinates available (`--cal-ra-deg`, `--cal-dec-deg`):
     - Uses manual calculation instead of `setjy`
     - Gets flux from `--cal-flux-jy` or uses default (2.5 Jy)
     - Warns user about phase center issues
   - If rephased BUT no coordinates available:
     - Falls back to `setjy` with warning
   - If NOT rephased:
     - Uses `setjy` normally (no issues when at meridian phase center)

3. **Component/Image models:**
   - These still use `ft()` (no easy conversion to manual calculation)
   - Warnings added to alert users

---

## Implementation Details

### Code Changes

**File:** `src/dsa110_contimg/calibration/cli.py`

1. **Track rephasing status:**
   ```python
   # Initialize flag
   ms_was_rephased = False
   
   # Set when rephasing occurs (two locations):
   # - Auto-fields case (line ~1076)
   # - Manual rephasing case (line ~1696)
   ms_was_rephased = True
   ```

2. **setjy model source handling (lines ~1770-1837):**
   - Check if `ms_was_rephased == True`
   - If yes AND calibrator coordinates available:
     - Use `write_point_model_with_ft(..., use_manual=True)`
   - If yes BUT no coordinates:
     - Warn user and fall back to `setjy`
   - If no:
     - Use `setjy` normally

---

## Verification

### Test Scenario

**Corrected test** (`scripts/test_ft_phase_dir_corrected.py`):
- Component at PHASE_DIR position
- If `ft()` uses PHASE_DIR correctly: Expected ~0° scatter
- **Actual result:** 104.5° scatter ✗
- **Conclusion:** `ft()` does NOT use PHASE_DIR

**Root cause confirmed:**
- `ft()` uses original meridian phase center (from DATA column)
- Component offset from meridian: ~1.2° (71.8 arcmin)
- Expected scatter for 1.2° offset: ~100-110°
- Actual scatter: 104.5° ✓ **Matches!**

---

## Usage

### Best Practice

**When rephasing MS:**
1. Use `--model-source catalog` with `--cal-ra-deg` and `--cal-dec-deg`
   - Automatically uses manual calculation ✓
2. If using `--model-source setjy`:
   - Provide `--cal-ra-deg`, `--cal-dec-deg`, and `--cal-flux-jy`
   - System will automatically use manual calculation ✓
3. Avoid `--model-source component` or `--model-source image` when rephasing
   - These still use `ft()` and may have phase center issues

**When NOT rephasing (`--skip-rephase`):**
- All model sources work correctly (ft() uses meridian phase center correctly)
- No special handling needed

---

## References

- Test script: `scripts/test_ft_phase_dir_corrected.py`
- Test results: `docs/reports/FT_PHASE_CENTER_TEST_RESULTS.md`
- Phase wrapping verification: `docs/reports/PHASE_WRAPPING_VERIFICATION.md`
- Root cause analysis: `docs/reports/FT_PHASE_CENTER_INVESTIGATION_RESULTS.md`

