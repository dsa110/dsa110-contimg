# Critical MS Phasing Issue Identified

**Date:** 2025-11-04  
**Status:** Critical Issue  
**Severity:** High - Root cause of low SNR calibration failures

---

## Problem Summary

The MS phase center is **misaligned** with the calibrator position, causing severe phase decorrelation:

- **MS Phase Center**: RA=128.571864°, Dec=54.665223°
- **Calibrator Position**: RA=128.7287°, Dec=55.5725°
- **Separation**: **54.7 arcmin (0.91 degrees)**
- **Primary Beam FWHM**: ~2.0 degrees @ 1.4 GHz
- **Separation / FWHM**: 0.456 (within primary beam, but significant offset)

---

## Critical Findings

### 1. Large Phase Center Offset

**54.7 arcmin separation** between MS phase center and calibrator position causes:
- Phase decorrelation across the field
- Reduced visibility amplitudes
- Low SNR in calibration solutions

### 2. MODEL_DATA Phase Structure Issues

- **Phase scatter**: 103° (very high)
- **Amplitude**: Correct (2.500 Jy)
- **Issue**: MODEL_DATA phase structure is inconsistent due to phase center offset

### 3. DATA vs MODEL_DATA Misalignment

- **Phase difference scatter**: 103° (very high)
- **Amplitude ratio (DATA/MODEL)**: 0.0365 (DATA is 96% weaker than MODEL!)
- **Issue**: DATA and MODEL_DATA are severely misaligned, causing calibration failures

---

## Root Cause

The MS was **not properly rephased** to the calibrator position, even though the terminal output showed:
```
✓ MS already phased to calibrator position (offset: 0.00 arcmin)
```

This suggests:
1. **Rephasing check was incorrect** - the phase center wasn't actually updated
2. **OR rephasing was performed but phase center table wasn't updated**
3. **OR MODEL_DATA was populated before rephasing** and has incorrect phase structure

---

## Impact on Calibration

The large phase center offset causes:
1. **Phase decorrelation** - visibilities lose coherence
2. **Reduced amplitudes** - DATA amplitudes are 96% weaker than MODEL
3. **Low SNR** - calibration can't converge because DATA and MODEL don't match
4. **Failed solutions** - 80-90% of bandpass solutions flagged due to low SNR

---

## Solution

### Immediate Fix: Rephase MS to Calibrator Position

```bash
# Method 1: Use phaseshift task directly
python -c "
from casatasks import phaseshift
phaseshift(
    vis='/scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms',
    phasecenter='J2000 08h34m54.90s +55d34m21.00s',
    datacolumn='all'
)
"

# Method 2: Re-run calibration with explicit rephasing
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --model-source catalog \
    --bp-combine-field \
    --combine-spw \
    --prebp-phase \
    --prebp-minsnr 3.0
```

**Note:** The calibration CLI should automatically rephase, but the phase center check may be incorrect.

### Verify Rephasing

After rephasing, verify the phase center is correct:

```bash
python3 scripts/check_ms_phasing.py \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --calibrator 0834+555 \
    --cal-ra 128.7287 \
    --cal-dec 55.5725
```

**Expected results after rephasing:**
- Separation: < 1 arcmin
- Phase scatter: < 30 deg
- Phase difference scatter: < 30 deg
- Amplitude ratio: > 0.5

---

## Code Locations

### Rephasing Logic

- **Check**: `src/dsa110_contimg/calibration/model.py` (rephasing check)
- **Rephase**: `src/dsa110_contimg/calibration/model.py` (phaseshift call)
- **Phase Center Check**: May be checking wrong field or cached value

### Diagnostic Script

- **Location**: `scripts/check_ms_phasing.py`
- **Usage**: `python3 scripts/check_ms_phasing.py --ms <ms> --calibrator <name> --cal-ra <ra> --cal-dec <dec>`

---

## Verification Steps

1. **Check MS phase center**:
   ```python
   from casacore.tables import table
   with table("MS::FIELD") as tb:
       print(tb.getcol("REFERENCE_DIR")[0][0] * 180.0 / np.pi)
   ```

2. **Check calibrator position**:
   ```python
   # From catalog or manual input
   calibrator_ra = 128.7287  # degrees
   calibrator_dec = 55.5725  # degrees
   ```

3. **Compute separation**:
   ```python
   from astropy.coordinates import SkyCoord
   import astropy.units as u
   ms_coord = SkyCoord(ra=field_ra*u.deg, dec=field_dec*u.deg)
   cal_coord = SkyCoord(ra=cal_ra*u.deg, dec=cal_dec*u.deg)
   separation = ms_coord.separation(cal_coord)
   print(f"Separation: {separation.to(u.arcmin):.2f}")
   ```

---

## Expected Behavior After Fix

After proper rephasing:
- **Separation**: < 1 arcmin (ideally < 0.1 arcmin)
- **Phase scatter**: < 30 deg
- **Phase difference scatter**: < 30 deg
- **Amplitude ratio**: > 0.5 (DATA/MODEL)
- **Calibration SNR**: Much higher (50-70% solutions retained instead of 10-20%)

---

## Status

**Status**: Critical - Root cause identified  
**Priority**: High - Blocks calibration pipeline  
**Next Action**: Fix rephasing logic or manually rephase MS

---

## Related Issues

- **Bandpass Solve Critical Failure**: `docs/reports/BANDPASS_SOLVE_CRITICAL_FAILURE.md`
- **Pre-Bandpass Phase Solve Low SNR**: `docs/reports/PREBP_PHASE_SOLVE_LOW_SNR_ANALYSIS.md`

This phasing issue is likely the **root cause** of all calibration SNR problems.

