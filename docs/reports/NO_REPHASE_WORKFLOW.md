# No-Rephase Calibration Workflow

**Date:** 2025-11-05  
**Status:** Workflow Implementation  
**Purpose:** Skip rephasing to allow ft() to work correctly without manual MODEL_DATA calculation

---

## Overview

This workflow skips rephasing to the calibrator position, allowing `ft()` to work correctly using the original meridian phase center. This avoids the need for manual MODEL_DATA calculation.

---

## Workflow

### Step 1: Skip Rephasing

**Action:** Use `--skip-rephase` flag to avoid rephasing MS to calibrator position

**Result:**
- MS stays at original meridian phase center
- `ft()` uses correct phase center (meridian)
- DATA and MODEL_DATA aligned (both relative to meridian)
- No manual MODEL_DATA calculation needed

### Step 2: Run Gaincal Phase-Only (Pre-Bandpass)

**Parameters:**
- `calmode='p'` (phase-only)
- `solint='30s'` (short solution interval)
- `minsnr=2.0` (lower threshold for phase-only)
- `minblperant=4` (minimum baselines per antenna)
- `refant=106` (reference antenna)
- `spw='4~11'` (central 8 SPWs only)
- Output table: `.bpphase.gcal` (custom name)

**Command:**
```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --refant 106 \
    --skip-rephase \
    --prebp-phase \
    --prebp-solint 30s \
    --prebp-minsnr 2.0 \
    --prebp-minblperant 4 \
    --prebp-spw 4~11 \
    --prebp-table-name .bpphase.gcal
```

### Step 3: Run Bandpass Calibration

**Parameters:**
- `solint='inf'` (per-channel solution)
- `bandtype='B'` (per-channel bandpass)
- `combine='scan, obs, field'` (combine across scans, observations, and fields)
- `gaintable=[.bpphase.gcal]` (use gaincal table from Step 2)

**Command:**
```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --refant 106 \
    --skip-rephase \
    --prebp-phase \
    --prebp-solint 30s \
    --prebp-minsnr 2.0 \
    --prebp-minblperant 4 \
    --prebp-spw 4~11 \
    --prebp-table-name .bpphase.gcal \
    --bp-combine "scan,obs,field"
```

---

## Implementation Details

### Code Changes

1. **Added `--skip-rephase` flag** to skip rephasing
2. **Added `--prebp-minblperant`** parameter for minimum baselines per antenna
3. **Added `--prebp-spw`** parameter for SPW selection
4. **Added `--prebp-table-name`** parameter for custom table name
5. **Added `--bp-combine`** parameter for custom combine string

### Modified Functions

1. **`solve_prebandpass_phase()`** - Added:
   - `minblperant` parameter
   - `spw` parameter for SPW selection
   - `table_name` parameter for custom table name

2. **`solve_bandpass()`** - Added:
   - `combine` parameter for custom combine string

3. **CLI `calibrate` command** - Added:
   - `--skip-rephase` flag
   - `--prebp-minblperant` argument
   - `--prebp-spw` argument
   - `--prebp-table-name` argument
   - `--bp-combine` argument

---

## Expected Results

### Without Rephasing

- ✅ MS phase center: Meridian (original)
- ✅ `ft()` uses: Meridian (correct!)
- ✅ MODEL_DATA: Calculated relative to meridian
- ✅ DATA column: Phased to meridian
- ✅ DATA vs MODEL_DATA: Aligned (< 20° phase difference)
- ⚠️ MODEL_DATA phase scatter: ~102° (but CORRECT for 1° offset)
- ✅ Calibration should work

### With Rephasing (Current - Broken)

- ✅ MS phase center: Calibrator position
- ❌ `ft()` uses: Meridian (wrong!)
- ❌ MODEL_DATA: Calculated relative to meridian (wrong!)
- ✅ DATA column: Phased to calibrator
- ❌ DATA vs MODEL_DATA: Misaligned (145° phase difference)
- ❌ Calibration fails

---

## Why This Works

**Key Insight:**
- The problem isn't the 102° phase scatter itself
- The problem is that DATA and MODEL_DATA are misaligned
- If we don't rephase, `ft()` uses the correct phase center (meridian)
- DATA and MODEL_DATA both relative to meridian → they match
- Calibration works even with high phase scatter (it's correct for 1° offset)

---

## Central 8 SPWs Selection

**For 16 SPWs (0-15):**
- Central 8 SPWs: SPWs 4-11
- SPW selection: `--prebp-spw 4~11`

**Rationale:**
- Avoid edge effects at band edges
- Use most stable central frequencies
- Better SNR in central portion of band

---

## Next Steps

1. **Test the workflow** with the new parameters
2. **Verify MODEL_DATA phase scatter** (should be ~102°, but correct)
3. **Verify DATA vs MODEL_DATA alignment** (should be < 20°)
4. **Run calibration** and check if phase scatter improves

