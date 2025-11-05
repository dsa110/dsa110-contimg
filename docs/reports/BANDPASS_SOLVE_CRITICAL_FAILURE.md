# Bandpass Solve Critical Failure: Low SNR Solutions

**Date:** 2025-11-04  
**Status:** Critical Issue  
**Severity:** High - Prevents successful calibration

---

## Problem Summary

Bandpass solve is failing with **80-90% of solutions flagged** due to SNR < 3.0, even with:
- ✓ MODEL_DATA populated correctly (2.50 Jy)
- ✓ MS rephased to calibrator position
- ✓ Field combination enabled (`--bp-combine-field`)
- ✓ SPW combination enabled (`--combine-spw`)
- ✓ No UV range cuts (maximizing data)
- ✓ Minimum SNR threshold at 3.0 (lowest recommended)

**Example Output:**
```
166 of 192 solutions flagged due to SNR < 3 in spw=0 (chan=47)
170 of 188 solutions flagged due to SNR < 3 in spw=0 (chan=46)
176 of 188 solutions flagged due to SNR < 3 in spw=0 (chan=45)
...
```

This indicates **genuine low SNR** in the data, not a configuration issue.

---

## Root Cause Analysis

### Possible Causes

1. **Phase Drifts in Raw Data** (MOST LIKELY)
   - Phase decorrelation from time-variable atmospheric/ionospheric effects
   - Phase drifts cause visibility amplitudes to decorrelate
   - **Solution**: Apply pre-bandpass phase-only calibration (`--prebp-phase`)

2. **RFI Contamination**
   - Radio frequency interference in specific channels
   - RFI causes incorrect visibility amplitudes
   - **Solution**: Flag RFI channels before calibration

3. **Calibrator Too Faint**
   - 0834+555 is 2.5 Jy (should be bright enough)
   - But if calibrator is resolved or has structure, SNR can be low
   - **Solution**: Check if calibrator is resolved on DSA-110 baselines

4. **Data Quality Issues**
   - Poor weather conditions during observation
   - Antenna issues (flagged antennas reducing baseline count)
   - System temperature problems
   - **Solution**: Check data quality metrics (flagging fraction, system temperature)

5. **Reference Antenna Issues**
   - Reference antenna (103) might be flagged or have poor data quality
   - **Solution**: Check reference antenna quality; use `--refant-ranking` to select better antenna

---

## Immediate Fixes to Try

### Fix 1: Pre-Bandpass Phase Correction (RECOMMENDED FIRST)

Apply phase-only calibration **before** bandpass to correct phase drifts:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --model-source catalog \
    --bp-combine-field \
    --combine-spw \
    --prebp-phase \
    --prebp-solint inf \
    --prebp-minsnr 3.0
```

**Why this helps:**
- Corrects phase drifts that cause decorrelation
- Improves SNR for bandpass solutions
- Applied before bandpass solve via `gaintable` parameter

### Fix 2: Lower SNR Threshold (TEMPORARY)

If phase correction doesn't help, lower the minimum SNR threshold:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --model-source catalog \
    --bp-combine-field \
    --combine-spw \
    --prebp-phase \
    --bp-minsnr 2.0  # Lower threshold (risky - may accept bad solutions)
```

**Warning:** Lowering minsnr below 3.0 risks accepting bad solutions. Only use if phase correction doesn't help.

### Fix 3: Check Reference Antenna Quality

Use automatic reference antenna selection based on data quality:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --auto-fields \
    --model-source catalog \
    --bp-combine-field \
    --combine-spw \
    --prebp-phase \
    --refant-ranking  # Auto-select best reference antenna
```

### Fix 4: Check Data Quality

Before calibration, check data quality:

```bash
# Check flagging fraction
python -m dsa110_contimg.qa.cli check_ms \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --verbose

# Check for RFI
python -m dsa110_contimg.qa.cli check_rfi \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms
```

---

## Diagnostic Steps

### 1. Check Flagging Fraction

```bash
# High flagging fraction (>50%) indicates data quality issues
# Check autocorrelations, system temperature, antenna issues
```

### 2. Check Visibility Amplitudes

```bash
# Low visibility amplitudes indicate:
# - Phase decorrelation
# - Calibrator too faint
# - RFI contamination
```

### 3. Check Phase Stability

```bash
# Large phase scatter indicates:
# - Phase drifts (needs pre-bandpass phase correction)
# - Atmospheric effects
# - Ionospheric effects
```

### 4. Check Reference Antenna

```bash
# Verify reference antenna (103) has:
# - Good data quality (low flagging)
# - Stable phases
# - Good SNR
```

---

## Expected Outcomes

### After Pre-Bandpass Phase Correction

- **Expected:** 50-70% solution retention (down from 10-20%)
- **If still failing:** Check data quality, RFI, reference antenna

### After Lowering minsnr

- **Expected:** 70-90% solution retention (but may include bad solutions)
- **Warning:** Quality may be compromised

### If All Fixes Fail

- **Likely cause:** Data quality issues (weather, RFI, system problems)
- **Action:** Flag problematic data or use different observation

---

## Code Locations

### Pre-Bandpass Phase Correction

- **Function**: `solve_prebandpass_phase()` in `src/dsa110_contimg/calibration/calibration.py` (line 350)
- **CLI Flag**: `--prebp-phase` in `src/dsa110_contimg/calibration/cli.py` (line 308)
- **Application**: Passed to `solve_bandpass()` via `prebandpass_phase_table` parameter

### SNR Threshold

- **CLI Flag**: `--bp-minsnr` in `src/dsa110_contimg/calibration/cli.py` (line 175)
- **Default**: 3.0 (from `CONTIMG_CAL_BP_MINSNR` env var)
- **Passed to**: `solve_bandpass()` via `minsnr` parameter (line 1354)

---

## Related Documentation

- **Bandpass Fixes**: `docs/howto/BANDPASS_CALIBRATION_FIXES.md`
- **Calibration Procedure**: `docs/howto/CALIBRATION_DETAILED_PROCEDURE.md`
- **Memory Lessons**: `MEMORY.md` (lines 329-346)

---

## Next Steps

1. **Immediate**: Try `--prebp-phase` flag (most likely fix)
2. **If still failing**: Check data quality metrics
3. **If data quality is poor**: Flag problematic data or use different observation
4. **If calibrator is too faint**: Consider using a brighter calibrator or longer integration time

---

## Status

**Status**: Critical - Investigation needed  
**Priority**: High - Blocks calibration pipeline  
**Next Action**: Apply pre-bandpass phase correction and report results

