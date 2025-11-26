# Quick Start: Rigorous DSA-110 Simulation Parameters

## TL;DR

Run this **once** to measure real DSA-110 parameters and replace assumptions:

```bash
conda activate casa6

# Full system characterization (auto-finds calibrator observations)
python scripts/characterize_dsa110_system.py \
    --ms-dir /stage/dsa110-contimg/ms \
    --caltable-dir /data/dsa110-contimg/products/caltables \
    --output-dir system_characterization/
```

**Output**: Updates
`backend/src/dsa110_contimg/simulation/config/dsa110_measured_parameters.yaml`
with measured values.

**Result**: Simulations now use **measured DSA-110 parameters** instead of
assumptions.

---

## What Gets Measured

| Parameter                  | Before (Assumed)    | After (Measured) | How                                   |
| -------------------------- | ------------------- | ---------------- | ------------------------------------- |
| System temperature (T_sys) | 50 K ← guess        | 51.2 ± 7.3 K     | Radiometer equation + calibrator flux |
| SEFD                       | Not calculated      | 382 ± 58 Jy      | From T_sys + antenna geometry         |
| Gain amplitude stability   | 10% ← generic       | 8.2 ± 1.4%       | Statistics from caltables             |
| Phase stability            | 10° ← generic       | 11.9 ± 2.1°      | Statistics from caltables             |
| Jy/K conversion            | 2.0 ← "calibrated"? | 2.1 ± 0.2        | From measured parameters              |

---

## Individual Measurements

If you want to run each step separately:

### 1. Measure T_sys from Calibrator (e.g., 3C286)

```bash
python scripts/measure_system_parameters.py \
    --ms /stage/dsa110-contimg/ms/3C286_2025-11-20.ms \
    --calibrator 3C286 \
    --output-dir measurements/tsys/ \
    --plot
```

**Reads**: Known flux (3C286 = 14.86 Jy @ 1.4 GHz)  
**Measures**: Off-source noise, applies radiometer equation  
**Outputs**: T_sys, SEFD per antenna with plots

### 2. Analyze Gain Stability from Caltables

```bash
python scripts/analyze_calibration_stability.py \
    --caltable /data/dsa110-contimg/products/caltables/observation.G0 \
    --output-dir measurements/stability/ \
    --plot
```

**Reads**: CASA gain table (.G0)  
**Measures**: Amplitude std, phase std, temporal drift  
**Outputs**: Stability statistics with comparison to defaults

### 3. Validate Noise Model

```bash
python scripts/validate_noise_model.py \
    --real-ms /stage/dsa110-contimg/ms/observation.ms \
    --system-temp-k 50 \
    --efficiency 0.7 \
    --n-synthetic 10000 \
    --output-dir measurements/validation/ \
    --plot
```

**Compares**: Real off-source noise vs synthetic  
**Tests**: KS test, Levene test (distribution + variance)  
**Outputs**: Statistical validation (PASS/FAIL)

---

## After Measurement

### Check Results

```bash
cat system_characterization/system_characterization_summary.txt
```

Look for:

- ✅ **Validation status**: "measured" (not "assumed")
- ✅ **Noise validation**: PASS rate ≥ 80%
- ✅ **Parameter uncertainties**: < 20%

### Update Simulation Config

The characterization script creates recommendations. **Manually** update:

```bash
vim backend/src/dsa110_contimg/simulation/config/dsa110_measured_parameters.yaml
```

Copy values from `system_characterization_summary.txt` into YAML fields.

### Verify Simulations Use Measured Values

Run simulation - should see:

```
INFO - Using measured parameter system_temperature: 51.2
INFO - Using measured parameter aperture_efficiency: 0.72
```

If you see warnings:

```
WARNING - Using default value for system_temperature: 50.0. Parameter not measured.
```

→ You forgot to update the YAML file.

---

## When to Re-Run

**Re-characterize** if:

- Hardware changes (new receivers, antenna repairs)
- Seasonal effects (summer vs winter T_sys)
- Calibration strategy changes
- Before publishing simulation-based results

**Typical cadence**: Quarterly or after major system changes

---

## Troubleshooting

### "No calibrator observations found"

```bash
# Check what's actually in your MS directory
ls /stage/dsa110-contimg/ms/*3C286* /stage/dsa110-contimg/ms/*3C48*

# If empty, point to correct directory or skip T_sys measurement:
python scripts/characterize_dsa110_system.py \
    --ms-dir /correct/path/to/ms \
    --caltable-dir /data/dsa110-contimg/products/caltables \
    --skip-tsys \
    --output-dir characterization/
```

### "Noise validation FAIL"

If statistical tests fail:

1. Check if T_sys estimate is reasonable (40-80 K range)
2. Ensure you're comparing same observation (not corrupted data)
3. Try different MS file (some may have RFI)
4. Increase `--n-synthetic` samples (default: 10000 → try 50000)

### "ImportError: CASA tools not found"

```bash
# Always activate casa6 environment first
conda activate casa6
which python  # Should show: .../casa6/bin/python
```

---

## Files Created

After running characterization:

```
system_characterization/
├── system_characterization_report.json    # Machine-readable
├── system_characterization_report.yaml    # Human-readable
├── system_characterization_summary.txt    # Quick overview
├── tsys_3C286_<obsid>/                    # T_sys measurements
│   ├── system_parameters.json
│   ├── system_parameters.yaml
│   ├── system_parameters_summary.txt
│   └── system_parameters.png              # Plots
├── stability_observation.G0/              # Gain stability
│   ├── calibration_stability.json
│   ├── calibration_stability.yaml
│   ├── calibration_stability_summary.txt
│   └── calibration_stability.png          # Plots
└── noise_validation_<obsid>/              # Noise model validation
    ├── noise_validation.json
    ├── noise_validation.yaml
    ├── noise_validation_summary.txt
    └── noise_validation.png                # Comparison plots
```

**Keep these** as documentation of when/how parameters were measured.

---

## Next Steps

1. **Run characterization** (see TL;DR above)
2. **Review results** in `system_characterization_summary.txt`
3. **Update YAML** with measured values
4. **Re-run E2E tests** with measured parameters:
   ```bash
   python simulations/scripts/run_e2e_test.py \
       --scenario simulations/config/scenarios/bright_calibrator.yaml \
       --output-dir e2e_validated/
   ```
5. **Document in papers**: Cite `SYSTEM_CHARACTERIZATION.md` for methodology

---

## References

- **Full documentation**: `docs/development/SYSTEM_CHARACTERIZATION.md`
- **Parameter schema**:
  `backend/src/dsa110_contimg/simulation/config/dsa110_measured_parameters.yaml`
- **Simulation code**:
  `backend/src/dsa110_contimg/simulation/visibility_models.py`
- **E2E testing**: `docs/state/E2E_TESTING_CAPABILITY.md`

---

## Summary

| Before                   | After                                           |
| ------------------------ | ----------------------------------------------- |
| ❌ Hardcoded assumptions | ✅ Measured from real data                      |
| ❌ No validation         | ✅ Statistical tests pass                       |
| ❌ No provenance         | ✅ Full documentation (dates, sources, methods) |
| ❌ Generic defaults      | ✅ DSA-110 specific parameters                  |
| ❌ Unknown uncertainties | ✅ Quantified uncertainties                     |

**Would I bet my life on the old parameters?** No.  
**Would I bet my life on the new measured parameters?** Much closer - they're
backed by real observations with quantified uncertainties.
