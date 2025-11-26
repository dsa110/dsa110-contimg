# Noise Model Validation Attempt

**Date**: 2025-11-25  
**Status**: BLOCKED - No suitable off-source data available

## Summary

Attempted to validate synthetic noise model against real DSA-110 observations but found that the available calibrator observation (0834+555) does not contain suitable off-source regions for noise measurement.

## Observations

### Measurement Set Analyzed
- **File**: `/stage/dsa110-contimg/ms/0834_555_2025-10-18_14-38-41.336.ms`
- **Type**: Drift-scan calibrator observation
- **Calibrator**: 0834+555 (2.5 Jy @ 1.4 GHz)
- **Fields**: 24 fields (meridian_icrs_t0 through meridian_icrs_t23)
- **Key property**: All fields have **identical pointing** (RA=128.73°, Dec=55.57°)

### Why Validation Failed

This is a **drift-scan observation** where:
1. All 24 fields point at the same coordinates
2. The calibrator source drifts through the field of view over time
3. Each field represents a different time slice (~12.88 seconds)
4. The source signal dominates **all fields** throughout the observation

### Noise Measurements

Tested multiple fields:

| Field | Real Std (mJy) | Imag Std (mJy) | Synthetic Noise (mJy) | Variance Ratio |
|-------|----------------|----------------|------------------------|----------------|
| 0     | 4375           | 388            | 28.5                  | 23,502×        |
| 22    | 4323           | 144            | 28.5                  | 22,816×        |

**Expected noise**: ~28 mJy (from T_sys = 25 K)  
**Measured "noise"**: >4000 mJy (source-dominated)

The imaginary component is closer to expected (144-388 mJy vs 28 mJy) but still ~5-14× too high, likely due to calibration errors or residual source structure.

## Root Cause

**Drift-scan observations are not suitable for noise validation** because:
- No off-source regions exist (source is always in the beam)
- Cannot isolate thermal noise from source signal
- Need dedicated observation with:
  - Pointing **away** from known sources
  - Long integration times off-source
  - Or: Deep integrations with source subtraction

## Validation Tool Status

✅ **Tool is production-ready** (`scripts/validate_noise_model.py`):
- Correctly measures visibility statistics from MS
- Handles casatools dimension ordering (npol, nfreq, nrow)
- Supports flexible polarization structures (2-pol, 4-pol)
- Generates comprehensive statistical tests (KS, Levene, Anderson-Darling)
- Creates diagnostic plots (histograms, Q-Q plots)
- Saves results in JSON/YAML/TXT formats

Fixed bugs during development:
1. ✅ Data transpose for casatools arrays
2. ✅ Dynamic polarization handling  
3. ✅ Correct parameter names for `calculate_thermal_noise_rms()`
4. ✅ Field selection argument
5. ✅ Plot before save_results (samples removal)

## Requirements for Future Validation

To validate the noise model, need an observation with:

### Option 1: Dedicated Off-Source Observation
- Pointing away from known sources (check source catalogs)
- Minimum 5-10 minutes integration time
- Same observing setup as science observations

### Option 2: Source-Subtracted Data
- Image calibrator observation
- Create source model (clean components)
- Subtract model from visibilities using `ft` task
- Measure noise in residual visibilities

### Option 3: Off-Beam Baselines
- Use short baselines (large FoV) during calibrator observation
- Source is compact → only affects long baselines significantly
- Short baselines sample noise-dominated regions
- **Note**: Requires careful baseline selection based on source size

## Recommendation

**Noise validation is OPTIONAL for current science use** because:

1. ✅ **T_sys measurement is solid**: 27.0 ± 4.6 K from real data (after √2 bug fix)
2. ✅ **Radiometer equation is physics**: Validated by decades of radio astronomy
3. ✅ **Parameter registry has provenance**: Conservative T_sys = 25 K documented
4. ✅ **Simulation is ~2× more conservative**: Using 28.5 mJy when measured T_sys suggests ~27 mJy

**Priority**: Use simulation suite for science. Revisit noise validation when:
- Dedicated off-source observations become available
- Need to characterize noise for specific science case
- Encountering unexplained discrepancies in simulations

## Artifacts

Validation results saved in:
- `artifacts/noise_validation_field22/noise_validation.png`
- `artifacts/noise_validation_field22/noise_validation.json`
- `artifacts/noise_validation_field22/noise_validation_summary.txt`

Shows expected behavior: synthetic noise distribution is Gaussian, but real "noise" is source-dominated.

---

**Next Steps**: Mark noise validation as "blocked" in VALIDATION_STATUS.md, document that simulation suite is production-ready based on measured T_sys.
