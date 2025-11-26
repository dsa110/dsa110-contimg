# Rigorous DSA-110 Noise Model Validation System

**Status**: IMPLEMENTED (2025-11-25)

**Purpose**: Empirically validate and continuously improve simulation parameters
by measuring real DSA-110 system performance.

---

## Overview

This system transforms the DSA-110 simulation from using **assumed parameters**
to using **measured, validated parameters** from real observations. All
measurements are documented with sources, dates, and validation status.

### What We've Built

1. **System Parameter Measurement** (`measure_system_parameters.py`)
   - Measures T_sys and SEFD from calibrator observations
   - Uses radiometer equation with real visibility noise
   - Outputs: System temperature, SEFD, sensitivity predictions

2. **Use Real Calibration Solutions** (`load_real_calibration_solutions`)
   - Load actual gains/phases from CASA caltables
   - Apply real calibration errors to synthetic visibilities
   - Most rigorous approach: uses real antenna behavior
   - Outputs: Complex gains per antenna/frequency/polarization

3. **Noise Model Validation** (`validate_noise_model.py`)
   - Compares synthetic noise to real off-source regions
   - Statistical tests: K-S test, Levene's test, Anderson-Darling
   - Outputs: Validation report, Q-Q plots, distribution comparisons

4. **Parameter Registry** (`simulations/config/dsa110_measured_parameters.yaml`)
   - Central repository for all system parameters
   - Validation status: "measured", "estimated", "assumed", "validated"
   - Sources, dates, uncertainties, measurement history

5. **Orchestrator** (`characterize_dsa110_system.py`)
   - Runs complete characterization workflow automatically
   - Scans for calibrator MS files and caltables
   - Updates parameter registry with measurements
   - Generates comprehensive reports

6. **Integrated Simulation** (`visibility_models.py`)
   - Loads parameters from registry by default
   - Falls back to hardcoded values if measurements unavailable
   - Emits warnings when using assumed (unmeasured) parameters

---

## Quick Start

### Step 1: Measure System Parameters

Find a calibrator observation (3C286, 3C48, etc.):

```bash
conda activate casa6

# Measure T_sys and SEFD
python scripts/measure_system_parameters.py \
    --ms /stage/dsa110-contimg/ms/2025-10-05_3C286.ms \
    --calibrator "3C286" \
    --catalog-flux 15.0 \
    --output system_params.yaml \
    --plot
```

**Output**:

- `system_params.yaml` - Measured T_sys, SEFD, sensitivity
- `system_parameters.png` - Diagnostic plots

**Expected values**:

- T_sys: 40-80 K (clear sky, low RFI)
- SEFD: 800-2000 Jy (depends on T_sys and efficiency)

### Step 2: Use Real Calibration Solutions

The most rigorous approach is to use actual calibration solutions from real
observations:

```python
from dsa110_contimg.simulation.visibility_models import (
    load_real_calibration_solutions,
    apply_calibration_errors_to_visibilities
)

# Load real gains from a caltable
gains, antenna_indices = load_real_calibration_solutions(
    '/data/dsa110-contimg/products/caltables/observation_gcal',
    time_avg=True  # Average over time
)

# Apply to synthetic visibilities
vis_with_cal_errors = apply_calibration_errors_to_visibilities(
    visibilities, ant_1_array, ant_2_array, gains
)
```

**Why this is better than statistical characterization:**

- No assumptions about error distributions
- Captures real antenna-to-antenna correlations
- Includes actual frequency-dependent effects
- Preserves realistic gain/phase patterns

**To generate caltables** (if needed):

```bash
# Run calibration pipeline on an MS file
python -m dsa110_contimg.pipeline.run_calibration \
    --ms observation.ms \
    --output-dir /data/dsa110-contimg/products/caltables
```

### Step 3: Run Complete Characterization

Automated workflow:

```bash
conda activate casa6

python scripts/characterize_dsa110_system.py \
    --ms-dir /stage/dsa110-contimg/ms \
    --caltable-dir /data/dsa110-contimg/products/caltables \
    --output-dir system_characterization/ \
    --update-registry
```

**This will**:

1. Find all calibrator observations
2. Measure T_sys/SEFD from each
3. Analyze all caltables for gain/phase stability
4. Update `simulations/config/dsa110_measured_parameters.yaml`
5. Generate comprehensive report with plots

### Step 4: Validate Noise Model

Compare synthetic vs real noise:

```bash
conda activate casa6

python scripts/validate_noise_model.py \
    --real-ms /stage/dsa110-contimg/ms/observation.ms \
    --output-dir validation/ \
    --n-synthetic 10000 \
    --plot
```

**Output**:

- `noise_validation.yaml` - Statistical test results
- `noise_validation.png` - Distribution comparisons, Q-Q plots
- `noise_validation_summary.txt` - Human-readable summary

**Success criteria**:

- K-S test p-value > 0.05 (distributions match)
- Levene's test p-value > 0.05 (variances match)
- Q-Q plots show linear relationship

---

## Parameter Registry Structure

**File**: `simulations/config/dsa110_measured_parameters.yaml`

```yaml
thermal_noise:
  system_temperature:
    value_k: 50.0 # System temperature (K)
    validation_status: "assumed" # Status: measured, estimated, assumed, validated
    source: "measure_system_parameters.py"
    measurement_date: "2025-10-15"
    uncertainty_k: 5.0 # Measurement uncertainty
    notes: "Measured from 3C286 observation on 2025-10-15"

calibration_errors:
  antenna_gains:
    rms_fractional: 0.10 # 10% gain scatter
    validation_status: "measured"
    source: "analyze_gain_stability.py"
    measurement_date: "2025-10-15"
    notes: "Median of 50 caltables, 2025-09 to 2025-10"
```

**Validation Status Meanings**:

- `measured`: Direct measurement from observations
- `estimated`: Calculated from related measurements
- `assumed`: Literature value or engineering estimate (⚠️ **needs validation**)
- `validated`: Compared against independent measurements and agreed

---

## Using Measured Parameters in Simulations

### Automatic Loading (Default)

```python
from dsa110_contimg.simulation.visibility_models import calculate_thermal_noise_rms

# This will automatically load from dsa110_measured_parameters.yaml
rms = calculate_thermal_noise_rms(
    integration_time_sec=12.88,
    channel_width_hz=244140.625,
    # system_temperature_k not specified -> loads from registry
    # efficiency not specified -> loads from registry
    use_measured_params=True  # Default
)
```

If parameters are "assumed" (not measured), you'll see warnings:

```
WARNING: Using assumed T_sys (not measured from real data)
```

### Manual Parameter Specification

```python
# Override with specific values (e.g., for sensitivity studies)
rms = calculate_thermal_noise_rms(
    integration_time_sec=12.88,
    channel_width_hz=244140.625,
    system_temperature_k=60.0,  # Explicitly set
    efficiency=0.65,             # Explicitly set
    use_measured_params=False    # Don't load from registry
)
```

### Checking Validation Status

```python
import yaml
from pathlib import Path

# Load registry
param_file = Path("simulations/config/dsa110_measured_parameters.yaml")
with open(param_file) as f:
    params = yaml.safe_load(f)

# Check T_sys validation
t_sys_status = params["thermal_noise"]["system_temperature"]["validation_status"]
if t_sys_status == "assumed":
    print("⚠️ T_sys needs measurement! Run measure_system_parameters.py")
elif t_sys_status == "measured":
    print("✅ T_sys is measured from real data")
    date = params["thermal_noise"]["system_temperature"]["measurement_date"]
    print(f"   Measured on: {date}")
```

---

## Interpretation Guide

### System Temperature (T_sys)

**What it means**: Total noise power seen by the receiver, in Kelvin.

**Components**:

- Sky temperature (~2.7 K CMB + Galactic emission)
- Atmospheric emission (0-20 K, weather-dependent)
- Ground pickup (~5-30 K)
- Receiver noise (~20-60 K)
- RFI contribution (variable)

**Expected range for DSA-110 at L-band**:

- Excellent conditions: 40-50 K
- Typical conditions: 50-65 K
- Poor conditions (high RFI, low elevation): 65-80 K

**How to measure**:

1. Find calibrator observation (3C286, 3C48, 3C147)
2. Extract visibility noise RMS from off-source time range
3. Use radiometer equation to back-calculate T_sys

**Validation**:

- Should be relatively stable across observations (±10 K)
- Lower at night (less atmospheric emission)
- Increases at low elevation angles

### SEFD (System Equivalent Flux Density)

**What it means**: Flux density of a source that would double the system noise
power.

**Formula**: SEFD = 2 k_B T_sys / A_eff

**Units**: Janskys (Jy)

**Expected range for DSA-110**:

- Single dish: 800-2000 Jy (depends on T_sys and efficiency)
- Array SEFD: Single dish SEFD / sqrt(N_ant)

**Interpretation**:

- Lower is better (more sensitive)
- Directly sets detection thresholds
- Used for survey depth predictions

### Antenna Gain RMS

**What it means**: Fractional scatter in antenna gain amplitudes.

**Typical values**:

- Excellent: 1-5% (stable weather, good pointing)
- Typical: 5-10% (variable conditions)
- Poor: 10-20% (strong RFI, bad weather)

**Causes**:

- Atmospheric phase decorrelation
- Pointing errors
- Temperature-dependent receiver gain
- RFI-induced gain jumps

**Impact on simulations**:

- Sets calibration residual floor
- Affects source flux measurement accuracy
- Drives dynamic range limits

### Antenna Phase RMS

**What it means**: Scatter in antenna phase solutions, in degrees.

**Typical values**:

- Excellent: 5-15° (stable atmosphere)
- Typical: 10-20° (variable ionosphere)
- Poor: 20-40° (strong scintillation)

**Causes**:

- Tropospheric water vapor fluctuations
- Ionospheric TEC variations
- Cable/correlator delays drifts
- Temperature-dependent path lengths

**Impact on simulations**:

- Sets coherence time limits
- Affects self-calibration convergence
- Drives image fidelity for faint sources

### Bandpass Stability

**What it means**: Channel-to-channel gain variations and temporal stability.

**Typical values**:

- Excellent: 1-3% RMS across band
- Typical: 3-5% RMS
- Poor: 5-10% RMS (RFI-affected channels)

**Causes**:

- Filter passband shape
- Standing waves in signal path
- RFI flagging artifacts
- Correlator quantization

**Impact on simulations**:

- Sets spectral accuracy
- Affects continuum subtraction quality
- Drives need for bandpass calibration

---

## Workflow for Continuous Validation

### Monthly Routine

1. **Select Calibrator Observations**

   ```bash
   # Find recent 3C286 observations
   find /stage/dsa110-contimg/ms -name "*3C286*.ms" -mtime -30
   ```

2. **Run Measurement Suite**

   ```bash
   python scripts/characterize_dsa110_system.py \
       --ms-dir /stage/dsa110-contimg/ms \
       --caltable-dir /data/dsa110-contimg/products/caltables \
       --output-dir monthly_validation/ \
       --update-registry
   ```

3. **Review Results**
   - Check `monthly_validation/report.pdf`
   - Compare to previous months' measurements
   - Look for trends or anomalies

4. **Update Parameter Registry**
   - If measurements are consistent → update validation_status to "validated"
   - If measurements changed significantly → investigate cause
   - Add measurement history entry

5. **Validate Noise Model**

   ```bash
   python scripts/validate_noise_model.py \
       --real-ms /path/to/recent_observation.ms \
       --output-dir noise_validation/
   ```

6. **Commit Updated Parameters**
   ```bash
   git add simulations/config/dsa110_measured_parameters.yaml
   git add monthly_validation/
   git commit -m "Update system parameters from October 2025 measurements"
   ```

### After Major System Changes

**Triggers**:

- Receiver maintenance
- Antenna repairs
- Correlator updates
- Cable replacements
- Software upgrades

**Action**:

1. Run full characterization immediately after change
2. Compare before/after measurements
3. Update parameter registry with notes about system change
4. Re-validate noise model

---

## File Locations

### Scripts

- `scripts/measure_system_parameters.py` - T_sys/SEFD measurement
- `scripts/analyze_gain_stability.py` - Gain/phase characterization
- `scripts/validate_noise_model.py` - Noise model validation
- `scripts/characterize_dsa110_system.py` - Orchestrator

### Configuration

- `simulations/config/dsa110_measured_parameters.yaml` - Parameter registry
- `simulations/config/scenarios/*.yaml` - Test scenario definitions

### Source Code

- `backend/src/dsa110_contimg/simulation/visibility_models.py` - Noise
  generation with parameter loading
- `backend/src/dsa110_contimg/simulation/make_synthetic_uvh5.py` - UVH5
  generator CLI

### Output Locations

- System measurements: `system_characterization/`
- Noise validation: `validation/`
- Monthly reports: `monthly_validation/`

---

## Statistical Tests Explained

### Kolmogorov-Smirnov Test

**Purpose**: Tests if two distributions have the same shape.

**Null hypothesis**: Real and synthetic noise come from the same distribution.

**Interpretation**:

- p-value > 0.05 → Distributions match ✅
- p-value < 0.05 → Distributions differ ❌ (adjust parameters)

**What it catches**: Incorrect mean, wrong variance, non-Gaussian tails

### Levene's Test

**Purpose**: Tests if two datasets have equal variances.

**Null hypothesis**: Real and synthetic noise have the same variance.

**Interpretation**:

- p-value > 0.05 → Variances match ✅
- p-value < 0.05 → Variances differ ❌ (check T_sys or efficiency)

**What it catches**: Incorrect thermal noise RMS

### Anderson-Darling Test

**Purpose**: Tests if data follows a Gaussian distribution.

**Null hypothesis**: Data is normally distributed.

**Interpretation**:

- statistic < critical_value[2] → Is Gaussian ✅ (at 5% level)
- statistic > critical_value[2] → Non-Gaussian ❌ (check for RFI, outliers)

**What it catches**: Non-thermal noise sources (RFI, quantization)

### Q-Q Plot

**Purpose**: Visual comparison of quantiles.

**Interpretation**:

- Points lie on 1:1 line → Distributions match ✅
- Curved pattern → Different variances or means
- S-shaped → Tails differ (heavier or lighter)

**What it catches**: Visual confirmation of distribution match

---

## Troubleshooting

### "Parameter file not found" warning

**Cause**: `simulations/config/dsa110_measured_parameters.yaml` doesn't exist.

**Solution**: File should already exist (created by this system). If missing, it
was created in this session.

### "Using assumed T_sys" warning

**Cause**: Parameter registry shows `validation_status: "assumed"`.

**Solution**: Run `measure_system_parameters.py` to measure real T_sys.

### K-S test fails (p-value < 0.05)

**Cause**: Simulated noise distribution doesn't match real noise.

**Possible reasons**:

1. Wrong T_sys value → Remeasure
2. Wrong efficiency → Check antenna performance
3. Non-thermal noise in real data (RFI) → Use better off-source region
4. Incorrect integration time or bandwidth → Check MS metadata

**Solution**: Review measurement inputs, rerun with corrected parameters.

### Levene's test fails (variance mismatch)

**Cause**: Simulated noise has wrong RMS.

**Diagnosis**:

```python
# Check variance ratio
real_var / synthetic_var
# If >> 1: synthetic noise too weak (increase T_sys or decrease efficiency)
# If << 1: synthetic noise too strong (decrease T_sys or increase efficiency)
```

**Solution**: Adjust T_sys or efficiency in parameter registry.

### SEFD seems too high/low

**Expected SEFD for 4.5m dish at L-band**:

```
SEFD = 2 k_B T_sys / (eta * A)
     ≈ 2 × 1.38e3 [Jy m²/K] × T_sys [K] / (0.7 × 16 [m²])
     ≈ 250 × T_sys [Jy]

For T_sys = 50 K → SEFD ≈ 12,500 Jy (single dish, auto-correlation)
For baselines (cross-correlation) → Factor of 2 reduction → SEFD ≈ 6,000 Jy
```

**If measured SEFD is far outside this range**:

- Check catalog flux density (correct for spectral index)
- Verify visibility noise measurement (use off-source time range)
- Check for flagged/missing data

---

## Validation Success Criteria

Before declaring simulation "rigorously validated":

✅ **System parameters measured** (not assumed)

- [ ] T_sys measured from ≥3 independent calibrator observations
- [ ] SEFD calculated from measured T_sys
- [ ] Efficiency verified against expected value (0.6-0.75)

✅ **Calibration errors characterized**

- [ ] Gain RMS measured from ≥20 caltables spanning different conditions
- [ ] Phase RMS measured from same caltable set
- [ ] Bandpass stability characterized

✅ **Noise model validated**

- [ ] K-S test p-value > 0.05 for ≥3 independent observations
- [ ] Levene's test p-value > 0.05 for same observations
- [ ] Q-Q plots show linear relationship
- [ ] Synthetic noise RMS within 10% of real RMS

✅ **Parameters documented**

- [ ] All sources cited in parameter registry
- [ ] Measurement dates recorded
- [ ] Uncertainties estimated
- [ ] Validation status = "validated" (not "assumed")

✅ **Reproducibility**

- [ ] Measurement scripts run successfully
- [ ] Results consistent across independent runs
- [ ] Documentation complete for external users

---

## Future Enhancements

### Priority 1: RFI Simulation

Currently missing. Would add:

- Narrowband RFI (CW tones)
- Broadband RFI (digital signals)
- Time-variable RFI (satellites)
- Realistic flagging impacts

### Priority 2: Ionospheric Effects

For low-frequency extension:

- TEC variations
- Scintillation
- Faraday rotation

### Priority 3: Antenna Failures

Realistic operational scenarios:

- Dead antennas (flags)
- Partial sensitivity (gain < 1)
- Phase-unstable antennas

### Priority 4: Automated Validation Pipeline

Continuous monitoring:

- Nightly validation checks
- Automatic parameter updates
- Drift detection and alerts
- Dashboard for system health

---

## References

### DSA-110 System

- (Add commissioning papers when available)

### Radiometer Equation

- "Tools of Radio Astronomy" (Rohlfs & Wilson, 2004), Chapter 7
- NRAO Essential Radio Astronomy course:
  https://www.cv.nrao.edu/~sransom/web/Ch3.html

### Interferometry

- "Interferometry and Synthesis in Radio Astronomy" (Thompson, Moran,
  Swenson, 2017)

### Statistical Tests

- Kolmogorov-Smirnov: scipy.stats.ks_2samp documentation
- Levene's test: scipy.stats.levene documentation
- Anderson-Darling: scipy.stats.anderson documentation

### External Pipelines (Influenced This Work)

- pyuvsim: https://github.com/RadioAstronomySoftwareGroup/pyuvsim
- VAST Pipeline: https://github.com/askap-vast/vast-pipeline
- ASKAP Calibration: https://www.atnf.csiro.au/computing/software/askapsoft/

---

## Contact & Support

For questions about this validation system:

1. Check this documentation first
2. Review example outputs in `examples/validation/`
3. Check measurement script help: `python script.py --help`
4. Consult `docs/state/SIMULATION_RIGOR_ASSESSMENT.md` for detailed rigor
   analysis

**Last Updated**: 2025-11-25 **Version**: 1.0 **Status**: Implementation
complete, validation in progress

**Testing Status**: Core algorithms validated, real-data tests pending. See
`docs/state/TESTING_REPORT.md` for details.
