# How to Prove Implementation Completeness and Bandpass Quality

**Quick Reference Guide**

## Quick Proof (Code Only)

```bash
# Prove code completeness
python3 scripts/prove_bandpass_quality.py

# Expected output:
# ✓ Implementation is COMPLETE (all workflow steps present)
```

## Full Proof (Code + Quality)

### Step 1: Run Calibration

```bash
# Run calibration workflow (this will verify UVW automatically)
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --model-source catalog \
    --bp-combine-field \
    --combine-spw \
    --prebp-phase \
    --prebp-solint 30s \
    --prebp-minsnr 3.0
```

**Look for**:
- `✓ UVW transformation verified: phaseshift correctly transformed UVW`
- `✓ REFERENCE_DIR correctly aligned`
- `✓ MS rephased to calibrator position`
- Calibration completes successfully

### Step 2: Measure Quality

```bash
# Measure MODEL_DATA and bandpass quality
python3 scripts/prove_bandpass_quality.py \
    --ms /path/to/ms \
    --bandpass-table /path/to/bandpass.cal
```

**Expected Results**:

```
PROOF 1: MODEL_DATA Phase Scatter (Should be < 10°)
  Phase scatter: < 10.0°
  ✓ Phase scatter < 10°: PASS
  ✓ Phase center aligned: PASS
  ✓ PROOF: MODEL_DATA has correct phase structure

PROOF 2: Bandpass Solution Quality
  Flagging rate: < 50%
  Median SNR: >= 3.0
  ✓ Flagging rate < 50%: PASS
  ✓ Median SNR >= 3.0: PASS
  ✓ Amplitude in range: PASS
  ✓ PROOF: Bandpass solutions meet scientific standards

FINAL PROOF
  ✓ CONCLUSION: Implementation is COMPLETE and produces GOOD bandpass solutions
```

## What Each Proof Shows

### Proof 1: Code Completeness

**What it proves**:
- All workflow steps are present
- All code paths are handled
- Error handling is complete

**How to verify**:
```bash
python3 scripts/prove_bandpass_quality.py
```

**Success criteria**:
- All 9 workflow steps present ✓
- No missing code paths ✓

### Proof 2: MODEL_DATA Quality

**What it proves**:
- UVW transformation was verified
- ft() used correct phase center
- MODEL_DATA has correct phase structure

**How to verify**:
```bash
python3 scripts/prove_bandpass_quality.py --ms <ms_path>
```

**Success criteria**:
- Phase scatter < 10° ✓
- Phase center aligned (< 1 arcmin) ✓

### Proof 3: Bandpass Solution Quality

**What it proves**:
- Calibration workflow produces good solutions
- Bandpass solutions meet scientific standards
- Calibration is scientifically valid

**How to verify**:
```bash
python3 scripts/prove_bandpass_quality.py \
    --ms <ms_path> \
    --bandpass-table <bandpass.cal>
```

**Success criteria**:
- Flagging rate < 50% ✓
- Median SNR >= 3.0 ✓
- Amplitude in range [0.1, 10.0] ✓

## Troubleshooting

### If MODEL_DATA phase scatter > 10°

**Possible causes**:
1. UVW verification failed (check logs for "UVW transformation verification failed")
2. Phase center not updated correctly (check REFERENCE_DIR)
3. ft() using wrong phase center (check UVW transformation)

**Solution**: Check calibration logs for UVW verification status.

### If bandpass flagging rate > 50%

**Possible causes**:
1. MODEL_DATA still wrong (check phase scatter)
2. Pre-bandpass phase not applied correctly
3. Data quality issues (low SNR, RFI)
4. Calibrator too faint or resolved

**Solution**: Check MODEL_DATA quality first, then check data quality.

### If calibration fails with "UVW transformation failed"

**This is CORRECT behavior**:
- UVW verification detected that phaseshift didn't transform UVW correctly
- Calibration stops to prevent wrong results
- This proves the implementation is working correctly (catching errors)

**Solution**: 
1. Check if phaseshift succeeded
2. Check if MS needs manual rephasing
3. Report issue if phaseshift has a bug for large phase shifts

## Expected Improvements

### Before Fix

| Metric | Value | Status |
|--------|-------|--------|
| MODEL_DATA phase scatter | 103.3° | ✗ BAD |
| Bandpass flagging rate | 80-90% | ✗ BAD |
| Bandpass median SNR | < 3.0 | ✗ BAD |
| Calibration | Fails | ✗ BAD |

### After Fix

| Metric | Value | Status |
|--------|-------|--------|
| MODEL_DATA phase scatter | < 10° | ✓ GOOD |
| Bandpass flagging rate | < 50% | ✓ GOOD |
| Bandpass median SNR | >= 3.0 | ✓ GOOD |
| Calibration | Succeeds | ✓ GOOD |

## Summary

**To prove completeness**: Run `scripts/prove_bandpass_quality.py` (code-only check)

**To prove quality**: Run calibration workflow, then measure quality with `scripts/prove_bandpass_quality.py --ms <ms> --bandpass-table <table>`

**Expected result**: All proofs pass, indicating implementation is complete and produces good bandpass solutions.

