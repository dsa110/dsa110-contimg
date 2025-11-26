# Quick Start: Rigorous Noise Model Validation

**Goal**: Measure real DSA-110 system parameters and validate simulation in 15
minutes.

---

## Prerequisites

```bash
# Activate casa6 environment
conda activate casa6

# Navigate to repo
cd /data/dsa110-contimg
```

---

## 1. Measure System Parameters (5 min)

Find a recent calibrator observation:

```bash
# Example: Look for 3C286
ls -lt /stage/dsa110-contimg/ms/*3C286*.ms | head -n 1
```

Run measurement:

```bash
python scripts/measure_system_parameters.py \
    --ms /stage/dsa110-contimg/ms/YOUR_CALIBRATOR.ms \
    --calibrator "3C286" \
    --catalog-flux 15.0 \
    --output system_params.yaml \
    --plot
```

**Output**:

```
System Temperature: 52.3 K
SEFD: 1456 Jy
1-hour 5-sigma Sensitivity: 42.5 mJy
```

✅ **Check**: T_sys should be 40-80 K

---

## 2. Analyze Gain Stability (3 min)

```bash
python scripts/analyze_gain_stability.py \
    --caltable-dir /data/dsa110-contimg/products/caltables \
    --output gain_stability.yaml \
    --plot
```

**Output**:

```
Gain RMS (fractional): 0.085 (range: 0.045-0.132)
Phase Std (degrees): 12.4 (range: 7.2-18.9)
```

✅ **Check**: Gain RMS should be 1-15%, Phase Std should be 5-30°

---

## 3. Run Complete Characterization (5 min)

Automated workflow:

```bash
python scripts/characterize_dsa110_system.py \
    --ms-dir /stage/dsa110-contimg/ms \
    --caltable-dir /data/dsa110-contimg/products/caltables \
    --output-dir system_characterization/ \
    --update-registry
```

This will:

1. ✅ Measure T_sys from all calibrator observations
2. ✅ Analyze all caltables for stability
3. ✅ Update `simulations/config/dsa110_measured_parameters.yaml`
4. ✅ Generate comprehensive report

---

## 4. Validate Noise Model (2 min)

```bash
python scripts/validate_noise_model.py \
    --real-ms /stage/dsa110-contimg/ms/SOME_OBSERVATION.ms \
    --output-dir validation/ \
    --plot
```

**Output**:

```
Kolmogorov-Smirnov Test:
  Real component: p-value = 0.324 ✅
  Imag component: p-value = 0.401 ✅

Variance Comparison:
  Levene test (real): p-value = 0.156 ✅
  Levene test (imag): p-value = 0.201 ✅

Overall Validation: PASS ✅
Recommendation: Simulation noise model is statistically consistent with real data
```

✅ **Success**: All p-values > 0.05

---

## 5. Use Measured Parameters in Simulations

### Check Current Parameters

```bash
# View parameter registry
cat simulations/config/dsa110_measured_parameters.yaml
```

Look for `validation_status`:

- `"measured"` → ✅ Real data
- `"assumed"` → ⚠️ Needs measurement

### Run Simulation with Measured Parameters

```python
from dsa110_contimg.simulation.visibility_models import calculate_thermal_noise_rms

# Automatically loads from parameter registry
rms = calculate_thermal_noise_rms(
    integration_time_sec=12.88,
    channel_width_hz=244140.625,
    use_measured_params=True  # Default
)

print(f"Expected noise RMS: {rms*1e3:.2f} mJy")
```

If you see warnings like:

```
WARNING: Using assumed T_sys (not measured from real data)
```

→ Run measurement scripts to update parameters

---

## Example: Complete Workflow

```bash
#!/bin/bash
# File: quick_validation.sh

# Setup
conda activate casa6
cd /data/dsa110-contimg

# 1. Measure T_sys
echo "=== Measuring system parameters ==="
python scripts/measure_system_parameters.py \
    --ms /stage/dsa110-contimg/ms/2025-10-05_3C286.ms \
    --calibrator "3C286" \
    --catalog-flux 15.0 \
    --output system_params.yaml \
    --plot

# 2. Analyze gain stability
echo "=== Analyzing gain stability ==="
python scripts/analyze_gain_stability.py \
    --caltable-dir /data/dsa110-contimg/products/caltables \
    --output gain_stability.yaml \
    --plot

# 3. Full characterization with registry update
echo "=== Running full characterization ==="
python scripts/characterize_dsa110_system.py \
    --ms-dir /stage/dsa110-contimg/ms \
    --caltable-dir /data/dsa110-contimg/products/caltables \
    --output-dir system_characterization/ \
    --update-registry

# 4. Validate noise model
echo "=== Validating noise model ==="
python scripts/validate_noise_model.py \
    --real-ms /stage/dsa110-contimg/ms/2025-10-05_obs.ms \
    --output-dir validation/ \
    --plot

echo "=== DONE ==="
echo "Review results in:"
echo "  - system_characterization/report.pdf"
echo "  - validation/noise_validation_summary.txt"
echo "  - simulations/config/dsa110_measured_parameters.yaml"
```

Run with:

```bash
bash quick_validation.sh
```

---

## Troubleshooting

### Error: "No data found for field: 3C286"

**Solution**: Check field name in MS:

```bash
# List fields in MS
python -c "
from casacore import tables
tb = tables.table('/path/to/observation.ms/FIELD')
print(tb.getcol('NAME'))
tb.close()
"
```

Use exact field name from output.

### Error: "Parameter file not found"

**Solution**: File should exist at
`simulations/config/dsa110_measured_parameters.yaml`. If missing, it was created
earlier in this session. Check that path.

### Warning: "Using assumed T_sys"

**Solution**: This is expected on first run. After running measurement scripts,
this warning will disappear.

---

## Expected Outputs

### system_params.yaml

```yaml
measurement_date: "2025-11-25T14:23:15Z"
system_params:
  system_temperature_k: 52.3
  sefd_jy: 1456.2
  sensitivity_1hr_5sigma_mjy: 42.5
validation_status: "measured"
```

### gain_stability.yaml

```yaml
aggregate_statistics:
  gain_statistics:
    median_gain_rms_fractional: 0.085
    median_phase_std_deg: 12.4
validation_status: "measured"
```

### noise_validation_summary.txt

```
DSA-110 Noise Model Validation
==============================================================

Real Noise Statistics
--------------------------------------------------------------
Combined Std: 45.2 mJy
Number of Samples: 98765

Synthetic Noise Statistics
--------------------------------------------------------------
Combined Std: 44.8 mJy
Expected RMS: 44.5 mJy

Statistical Tests
--------------------------------------------------------------
Kolmogorov-Smirnov Test:
  Real component: p-value = 0.324
  Match: True

Variance Comparison:
  Levene test (real): p-value = 0.156
  Match: True

Summary
--------------------------------------------------------------
Overall Validation: True
Recommendation: Simulation noise model is statistically consistent with real data
```

---

## Next Steps

1. **Monthly Routine**: Rerun characterization monthly to track system stability
2. **After Maintenance**: Rerun after any hardware changes
3. **Documentation**: Update parameter registry notes with any observations
4. **Commit Changes**: Git commit updated parameters with measurement reports

See full documentation: `docs/reference/RIGOROUS_NOISE_VALIDATION.md`

---

**Estimated Time**: 15 minutes (first run may take longer if many files to
analyze)

**Status**: Implementation complete, validation in progress ⚠️

See `docs/state/TESTING_REPORT.md` for full testing status.
