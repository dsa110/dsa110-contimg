# Why Pre-Bandpass Phase Solve Also Shows Low SNR

**Date:** 2025-11-04  
**Status:** Analysis  
**Related:** `docs/reports/BANDPASS_SOLVE_CRITICAL_FAILURE.md`

---

## Observation

The pre-bandpass phase-only solve is also showing significant flagged solutions:
- **82 of 188 solutions flagged** (44%) in spw=0 due to SNR < 5
- **39 of 188 solutions flagged** (21%) in spw=1 due to SNR < 5
- **43 of 192 solutions flagged** (22%) in spw=2 due to SNR < 5

This is **better** than bandpass (80-90% flagged), but still problematic.

---

## Why Pre-Bandpass Phase Solve Also Fails

### Key Insight: Phase-Only Solve Still Requires Good Visibility Amplitudes

**Phase-only calibration (`calmode='p'`) does NOT solve for amplitudes**, but it **still requires good visibility amplitudes** to compute phase accurately.

### Why Phase Solve Needs Good Amplitudes

1. **Phase is computed from complex visibilities**: `phase = arg(V)`, where `V = |V| * exp(i*phase)`
   - If `|V|` (amplitude) is low or noisy, the phase measurement is unreliable
   - Low SNR in visibility amplitude → low SNR in phase solution

2. **SNR calculation includes amplitude**: CASA's `gaincal` computes SNR as:
   ```
   SNR = |model_visibility| / noise_level
   ```
   - If visibility amplitude is low (due to decorrelation, RFI, etc.), SNR is low
   - Even though we're only solving for phase, the SNR calculation uses amplitude

3. **Phase-only solve operates on raw, uncalibrated data**:
   - No previous corrections applied
   - If data quality is poor, phase solve will also fail

---

## Root Causes

### 1. Stricter SNR Threshold (MOST LIKELY)

**Pre-bandpass phase solve uses `minsnr=5.0` (default), while bandpass uses `minsnr=3.0`.**

This is actually **more strict** than bandpass! The pre-bandpass phase solve is rejecting solutions that bandpass might accept.

**Solution:** Lower pre-bandpass phase SNR threshold to match bandpass:

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
    --prebp-minsnr 3.0  # Lower from default 5.0 to match bandpass
```

### 2. Low Visibility Amplitudes (UNDERLYING CAUSE)

If visibility amplitudes are already low due to:
- **Phase decorrelation** (phase drifts causing amplitude reduction)
- **RFI contamination** (RFI causing incorrect amplitudes)
- **System temperature issues** (high noise, low signal)
- **Calibrator too faint** (low intrinsic flux)
- **Bad antennas** (flagged antennas reducing baseline count)

Then **both** phase-only and bandpass solves will fail because they both need good amplitudes.

### 3. Severe Phase Drifts

If phase drifts are severe enough (e.g., wrapping around 180°, or very rapid variations), even a phase-only solve might struggle because:
- Phase noise is too high
- Phase variations are faster than solution interval
- Phase wraps cause ambiguity in phase determination

### 4. Data Quality Issues

If the underlying data quality is poor (weather, RFI, system issues), no calibration solve will work well:
- Phase-only solve fails (needs good amplitudes)
- Bandpass solve fails (needs good amplitudes and phase coherence)

---

## Why Pre-Bandpass Phase Solve is Better (But Still Failing)

The pre-bandpass phase solve shows **44% flagged** vs **80-90% flagged** for bandpass because:

1. **Phase-only solve is simpler** - only solving for phase, not amplitude and phase
2. **Fewer degrees of freedom** - phase-only is more robust to amplitude variations
3. **But still needs good amplitudes** - can't solve phase if amplitudes are too low

---

## Solutions

### Solution 1: Lower Pre-Bandpass Phase SNR Threshold (RECOMMENDED)

Lower the pre-bandpass phase SNR threshold to match bandpass (3.0 instead of 5.0):

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
    --prebp-minsnr 3.0  # Match bandpass minsnr
```

**Why this helps:**
- Pre-bandpass phase solve is more strict (5.0) than bandpass (3.0)
- Lowering to 3.0 allows more solutions to be retained
- Phase-only solve is more robust, so lower threshold is acceptable

### Solution 2: Check Data Quality

If lowering SNR threshold doesn't help, check underlying data quality:

```bash
# Check flagging fraction
python -m dsa110_contimg.qa.cli check_ms \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --verbose

# Check for RFI
python -m dsa110_contimg.qa.cli check_rfi \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms

# Check visibility amplitudes
# Low amplitudes indicate decorrelation or data quality issues
```

### Solution 3: Check Reference Antenna

Verify reference antenna quality:

```bash
# Use automatic reference antenna selection
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --auto-fields \
    --model-source catalog \
    --bp-combine-field \
    --combine-spw \
    --prebp-phase \
    --prebp-minsnr 3.0 \
    --refant-ranking  # Auto-select best reference antenna
```

### Solution 4: Use Longer Solution Interval

If phase drifts are slow, use longer solution interval:

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
    --prebp-minsnr 3.0 \
    --prebp-solint inf  # Use entire scan (default)
```

---

## Expected Outcomes

### After Lowering Pre-Bandpass Phase SNR Threshold

- **Expected:** 10-30% flagged (down from 20-45%)
- **Rationale:** Phase-only solve is more robust, so lower threshold is acceptable
- **Impact:** More phase solutions retained → better bandpass SNR

### After Checking Data Quality

- **If data quality is good:** Pre-bandpass phase solve should work
- **If data quality is poor:** No calibration solve will work well

---

## Code Locations

### Pre-Bandpass Phase SNR Threshold

- **Default:** `5.0` in `src/dsa110_contimg/calibration/calibration.py` (line 358)
- **CLI Flag:** `--prebp-minsnr` in `src/dsa110_contimg/calibration/cli.py` (line 290)
- **Default:** `5.0` (line 292)

### Comparison with Bandpass

- **Bandpass minsnr:** `3.0` (default, from `CONTIMG_CAL_BP_MINSNR` env var)
- **Pre-bandpass minsnr:** `5.0` (default, hardcoded)
- **Issue:** Pre-bandpass is more strict, but phase-only solve is more robust

---

## Recommendations

1. **Lower pre-bandpass phase SNR threshold to 3.0** to match bandpass
2. **If still failing, check data quality** (flagging, RFI, system temperature)
3. **If data quality is poor, flag problematic data** or use different observation
4. **Consider using automatic reference antenna selection** (`--refant-ranking`)

---

## Key Takeaway

**Phase-only calibration still requires good visibility amplitudes** to compute phase accurately. If amplitudes are low due to decorrelation, RFI, or other issues, the phase solve will also fail, even though it's "only" solving for phase.

The pre-bandpass phase solve is showing **better results** (44% flagged vs 80-90% for bandpass) because phase-only solve is more robust, but it's still failing because the underlying data quality may be poor.

