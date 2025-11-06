# Clear Path to Successful Bandpass Solve

**Date:** 2025-11-05  
**Status:** Recommended Workflow  
**Priority:** CRITICAL - Based on complete debugging and fixes

---

## Executive Summary

After extensive debugging, we've identified and fixed the root cause of bandpass calibration failures. Here is the **clear, tested path to success**:

**Key Principle:** Ensure DATA and MODEL_DATA are properly aligned, then use optimal parameters for SNR.

---

## Recommended Workflow

### Option 1: Rephase to Calibrator (RECOMMENDED)

**Best for:** Maximizing SNR by reducing decorrelation from source offset

#### Step 1: Rephase MS to Calibrator Position

**Why:** Reduces decorrelation from source being ~1° away from phase center
- Source at phase center → maximum coherence
- Reduces phase scatter from geometric decorrelation
- Improves SNR for calibration solutions

**Action:** Use `--auto-fields` or manually provide calibrator coordinates:
```bash
# Auto-detects calibrator and rephases
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --auto-fields \
    --cal-ra-deg 128.7287 \
    --cal-dec-deg 55.5725 \
    --cal-flux-jy 2.5
```

#### Step 2: MODEL_DATA Population (AUTOMATIC)

**Why:** Manual calculation ensures DATA and MODEL_DATA alignment after rephasing

**What happens automatically:**
- System detects rephasing was performed
- Uses manual MODEL_DATA calculation (bypasses ft() bug)
- Reads PHASE_DIR per field correctly
- Ensures DATA and MODEL_DATA phase structures match

**No action needed** - this is now automatic when using `--model-source catalog` with calibrator coordinates.

#### Step 3: Pre-Bandpass Phase Solve

**Why:** Corrects time-variable phase drifts that cause decorrelation

**Parameters:**
```bash
--prebp-phase \
--prebp-solint 30s \          # Time-variable phase drifts (not 'inf')
--prebp-minsnr 3.0 \          # Match bandpass threshold
--prebp-minblperant 4 \       # Ensure robust solutions
--prebp-spw 4~11 \            # Central 8 SPWs (avoid edge effects)
--prebp-table-name .bpphase.gcal
```

**Rationale:**
- `solint='30s'`: Handles time-variable atmospheric/ionospheric phase drifts
- `minsnr=3.0`: Phase-only solve is more robust, lower threshold acceptable
- Central SPWs: Avoid edge effects, better SNR

#### Step 4: Bandpass Solve

**Why:** Corrects frequency-dependent phase and amplitude variations

**Parameters:**
```bash
--bp-combine "scan,obs,field" \  # Maximize SNR by combining
--bp-minsnr 3.0 \                 # Reasonable threshold
--uvrange "" \                    # No UV cut (use all baselines)
--refant 106                      # Healthy reference antenna
```

**Rationale:**
- `combine='scan,obs,field'`: Maximize SNR by combining all available data
- `minsnr=3.0`: Lower threshold for marginal SNR cases
- `uvrange=""`: Use all baselines (DSA-110 is compact, short baselines fine)
- No UV cut: Avoids removing valuable data

#### Complete Command

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --auto-fields \
    --cal-ra-deg 128.7287 \
    --cal-dec-deg 55.5725 \
    --cal-flux-jy 2.5 \
    --model-source catalog \
    --refant 106 \
    --prebp-phase \
    --prebp-solint 30s \
    --prebp-minsnr 3.0 \
    --prebp-minblperant 4 \
    --prebp-spw 4~11 \
    --prebp-table-name .bpphase.gcal \
    --bp-combine "scan,obs,field" \
    --bp-minsnr 3.0 \
    --uvrange ""
```

---

### Option 2: Skip Rephasing (FALLBACK)

**Best for:** When calibrator is near meridian phase center, or when you want to use `setjy` without manual calculation

#### When to Use

- Calibrator is within ~0.2° of meridian phase center
- You want to use `setjy` standard catalog (not manual calculation)
- Data quality is excellent and SNR is high

#### Step 1: Skip Rephasing

```bash
--skip-rephase
```

**Why:** Keeps MS at meridian phase center, allowing `ft()` to work correctly

#### Step 2: MODEL_DATA Population

**Options:**
1. **setjy** (works correctly when not rephased):
   ```bash
   --model-source setjy \
   --model-field 0
   ```

2. **catalog** (still uses manual calculation):
   ```bash
   --model-source catalog \
   --cal-ra-deg 128.7287 \
   --cal-dec-deg 55.5725 \
   --cal-flux-jy 2.5
   ```

#### Step 3-4: Same as Option 1

Use same pre-bandpass phase and bandpass parameters.

#### Complete Command

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --skip-rephase \
    --model-source setjy \
    --model-field 0 \
    --refant 106 \
    --prebp-phase \
    --prebp-solint 30s \
    --prebp-minsnr 3.0 \
    --prebp-minblperant 4 \
    --prebp-spw 4~11 \
    --prebp-table-name .bpphase.gcal \
    --bp-combine "scan,obs,field" \
    --bp-minsnr 3.0 \
    --uvrange ""
```

**Note:** You'll still see ~100° phase scatter, but this is **expected** for a source ~1° away from phase center. The key is that DATA and MODEL_DATA are aligned.

---

## What We Fixed

### 1. ft() Phase Center Bug ✓

**Problem:** `ft()` doesn't use PHASE_DIR, causing MODEL_DATA misalignment when rephased

**Solution:** Automatic manual MODEL_DATA calculation when rephasing is detected

**Status:** ✅ **FIXED** - Now automatic

### 2. Field Selection Bug ✓

**Problem:** Using single field instead of combined fields reduced SNR

**Solution:** Pass full field range when `combine_fields=True`

**Status:** ✅ **FIXED**

### 3. Pre-Bandpass Phase Defaults ✓

**Problem:** `solint='inf'` caused decorrelation, `minsnr=5.0` too strict

**Solution:** Default to `solint='30s'` and `minsnr=3.0`

**Status:** ✅ **FIXED**

### 4. MODEL_DATA Validation ✓

**Problem:** Unpopulated MODEL_DATA caused silent failures

**Solution:** Precondition checks with clear error messages

**Status:** ✅ **FIXED**

---

## Expected Results

### Success Criteria

1. **MODEL_DATA populated:** ✓ All non-zero values
2. **DATA/MODEL_DATA alignment:** < 20° phase difference (when rephased with manual calculation)
3. **Pre-bandpass phase solve:** < 30% flagged solutions
4. **Bandpass solve:** < 40% flagged solutions
5. **Phase scatter:** 
   - **With rephasing:** < 30° (source at phase center)
   - **Without rephasing:** ~100° (expected for 1° offset, but DATA/MODEL_DATA aligned)

### Quality Metrics

**Good calibration:**
- Bandpass phase scatter: < 30° (rephased) or < 100° (not rephased, but aligned)
- Flagged fraction: < 40%
- Median amplitude: Within 10% of expected flux
- Amplitude scatter: < 20%

**Poor calibration (investigate):**
- Flagged fraction: > 50%
- Phase scatter: > 120° (indicates misalignment)
- Amplitude scatter: > 50%

---

## Troubleshooting

### High Phase Scatter (> 100°)

**If rephased with manual calculation:**
- ✅ Check DATA/MODEL_DATA alignment (< 20° expected)
- ✅ Verify PHASE_DIR is correct in FIELD table
- ✅ Check if calibrator is resolved (causes decorrelation)

**If not rephased:**
- ⚠️ High scatter is expected for source offset
- ✅ Verify DATA/MODEL_DATA alignment (< 20° expected)
- ✅ High scatter is OK as long as DATA/MODEL_DATA match

### High Flagging Rate (> 50%)

**Possible causes:**
1. **Low SNR** - Check system temperature, weather conditions
2. **RFI** - Flag RFI channels before calibration
3. **Poor reference antenna** - Try different `--refant`
4. **Calibrator too faint** - Check if calibrator flux is correct
5. **Phase drifts** - Ensure pre-bandpass phase solve is enabled

**Solutions:**
- Lower `--bp-minsnr` to 2.0 (more aggressive)
- Increase `--prebp-minblperant` to 6 (more robust)
- Check flagging fraction in raw data
- Verify calibrator is strong enough (> 1 Jy)

### MODEL_DATA Not Populated

**Check:**
```python
# Verify MODEL_DATA is populated
from casacore.tables import table
with table('/path/to/ms') as tb:
    model_data = tb.getcol('MODEL_DATA', 0, 1)  # First row
    if np.allclose(np.abs(model_data), 0):
        print("ERROR: MODEL_DATA is all zeros!")
```

**Fix:**
- Ensure `--model-source` is specified
- If using catalog model, ensure calibrator coordinates are provided
- If using setjy, ensure field is correct

---

## Key Principles

1. **DATA/MODEL_DATA alignment is critical** - This is what we fixed
2. **Rephasing improves SNR** - Reduces decorrelation from source offset
3. **Pre-bandpass phase solve is essential** - Corrects time-variable drifts
4. **Combine everything possible** - Fields, scans, observations for maximum SNR
5. **Use appropriate thresholds** - Lower SNR for phase-only, higher for bandpass

---

## References

- Root cause analysis: `docs/reports/FT_PHASE_CENTER_FIX.md`
- Test results: `docs/reports/FT_PHASE_CENTER_TEST_RESULTS.md`
- No-rephase workflow: `docs/reports/NO_REPHASE_WORKFLOW.md`
- Bandpass fixes: `docs/reports/BANDPASS_CALIBRATION_FIXES.md`

---

## Summary

**The clear path to success:**

1. ✅ **Rephase to calibrator** (reduces decorrelation)
2. ✅ **Use manual MODEL_DATA calculation** (automatic when rephased)
3. ✅ **Pre-bandpass phase solve** with `solint='30s'`, `minsnr=3.0`
4. ✅ **Bandpass solve** with `combine='scan,obs,field'`, `minsnr=3.0`
5. ✅ **Verify quality metrics** (phase scatter, flagging fraction)

**All critical bugs are fixed. This workflow should succeed.**

