# DSA-110 System Characterization for Rigorous Simulation

## Overview

This document describes the methodology for measuring DSA-110 system parameters
from real observations to enable rigorous, validated simulation of radio
interferometry data. The approach replaces hardcoded assumptions with measured
values backed by real data.

## Motivation

Previous simulation approach:

- **System temperature (T_sys)**: 50 K ← **assumption**
- **Aperture efficiency (η)**: 0.7 ← **assumption**
- **Gain amplitude stability**: 10% ← **generic default**
- **Phase stability**: 10° ← **generic default**
- **Jy/K conversion**: 2.0 Jy/K ← **claimed "calibrated" but no source**

**Problem**: No validation against real DSA-110 observations means simulations
may not reflect actual system performance.

**Solution**: Measure these parameters from calibrator observations and
calibration tables to ensure quantitatively accurate simulations.

## Measurement Scripts

Four scripts are provided in `scripts/`:

1. **measure_system_parameters.py** - Extract T_sys and SEFD from calibrator
   observations
2. **analyze_calibration_stability.py** - Characterize gain/phase stability from
   caltables
3. **validate_noise_model.py** - Statistically compare simulated vs real noise
4. **characterize_dsa110_system.py** - Orchestrate all measurements and generate
   report

## Parameter Registry

All measured parameters are stored in:

```
backend/src/dsa110_contimg/simulation/config/dsa110_measured_parameters.yaml
```

**Schema** for each parameter:

```yaml
parameter_name:
  value: <numeric>
  unit: <string>
  uncertainty: <numeric>
  uncertainty_type: "std" | "systematic" | "combined"
  measurement_date: <ISO 8601>
  source_observations: [<MS paths or obs IDs>]
  derivation_method: <description>
  validation_status: "measured" | "validated" | "assumed" | "default"
  references: [<DOIs, papers, or docs>]
  notes: <additional info>
  last_updated: <ISO 8601>
  version: <semantic version>
```

## Theory and Methodology

### 1. System Temperature (T_sys) and SEFD

**Physical basis**: System temperature quantifies total noise power from:

- Sky brightness temperature
- Receiver noise
- Spillover and ground pickup
- CMB (2.7 K)

**Radiometer equation** for single baseline:

```
σ_vis = T_sys / (η * sqrt(2 * Δν * Δt * N_pol))
```

Where:

- σ_vis: RMS noise in visibility (K)
- T_sys: System temperature (K)
- η: Aperture efficiency
- Δν: Channel bandwidth (Hz)
- Δt: Integration time (s)
- N_pol: Number of polarizations

**System Equivalent Flux Density (SEFD)**:

```
SEFD = 2 * k_B * T_sys / (A_eff * η)
```

Where:

- k_B = 1.38×10⁻²³ J/K (Boltzmann constant)
- A_eff = η \* A_geom = effective collecting area
- A_geom = π \* (D/2)² = geometric area

For DSA-110 (D = 4.65 m):

- A_geom = 16.97 m²
- A_eff ≈ 11.88 m² (if η = 0.7)

**Measurement procedure**:

1. Observe known calibrator (e.g., 3C286: 14.86 Jy @ 1.4 GHz)
2. Extract visibility amplitudes for each baseline
3. Measure off-source RMS noise from real/imaginary components
4. Apply radiometer equation to solve for T_sys per antenna
5. Calculate SEFD from T_sys and antenna geometry
6. Average over antennas and frequencies

**Expected values**:

- T_sys: 40-80 K (typical L-band)
- SEFD: 300-500 Jy (for 4.65m dishes)
- Compare: VLA (25m) SEFD ~400 Jy, ASKAP (12m) SEFD ~2000 Jy

**Calibrator flux standards** (Perley & Butler 2017, ApJS 230, 7):

- 3C286: S = 14.86 \* (ν/1.4)^(-0.467) Jy
- 3C48: S = 16.23 \* (ν/1.4)^(-0.491) Jy
- 3C147: S = 22.45 \* (ν/1.4)^(-0.518) Jy
- 3C138: S = 8.36 \* (ν/1.4)^(-0.433) Jy

Typical uncertainty: ~3% (systematic) from flux scale.

### 2. Calibration Stability (Gain/Phase Errors)

**Physical basis**: Interferometric calibration solves for complex antenna gains
g_i that relate true sky visibilities V_true to observed visibilities:

```
V_obs(i,j) = g_i * g_j* * V_true(i,j) + noise
```

Gains vary due to:

- Atmospheric phase fluctuations (troposphere, ionosphere)
- Antenna pointing/tracking errors
- Receiver gain drifts (temperature, LO stability)
- Cable delays

**Measurement procedure**:

1. Read CASA caltable (e.g., `.G0` for gain solutions, `.B0` for bandpass)
2. Extract complex gain solutions: g_i(t, ν, p) per antenna, time, freq, pol
3. Compute amplitude: |g_i| and phase: arg(g_i)
4. Calculate statistics:
   - Amplitude std: σ(|g_i|) / <|g_i|> → fractional stability
   - Phase std: σ(arg(g_i)) → degrees
   - Wrapped phase RMS: sqrt(<1 - cos(φ - <φ>)>) → robust phase metric
5. Temporal trends: fit linear drift, identify outliers
6. Per-antenna distributions

**Expected values**:

- Gain amplitude std: 3-15% (depends on weather, integration time)
- Phase std: 5-20° (tropospheric + ionospheric contributions)
- VLA typical: 5-10% gain, 10-15° phase (good conditions)
- ASKAP: 3-5% gain, 5-10° phase (dry site, short baselines)

**Interpretation**:

- Low std → stable system, good for long integrations
- High std → may need shorter solution intervals or flagging
- Time drift → possible temperature effects or pointing drift

### 3. Noise Validation

**Physical basis**: Thermal noise from receiver and sky should follow:

- Complex Gaussian distribution
- Independent real and imaginary components
- σ_real = σ_imag = σ_vis
- Amplitude follows Rayleigh distribution
- Time-uncorrelated (white noise)

**Statistical tests**:

1. **Kolmogorov-Smirnov (KS) test**: Compare cumulative distributions
   - H0: Real and synthetic come from same distribution
   - p-value > 0.05 → distributions match (at 95% confidence)
   - Tests shape, not just mean/variance

2. **Levene's test**: Compare variances
   - H0: Variances are equal
   - p-value > 0.05 → variances match
   - More robust than F-test for non-normal data

3. **Anderson-Darling test**: Test Gaussian assumption
   - Tests if data is normally distributed
   - More sensitive than KS test to tails
   - Critical values at 15%, 10%, 5%, 2.5%, 1% significance

4. **Q-Q plot**: Visual comparison of quantiles
   - Should lie on diagonal if distributions match
   - Deviations indicate non-Gaussian or scale differences

**Measurement procedure**:

1. Extract visibility samples from off-source region in real MS
2. Generate synthetic noise with same bandwidth, integration time
3. Compare distributions using statistical tests
4. Adjust simulation parameters if tests fail
5. Iterate until validation passes

**Validation criteria**:

- KS test p-value > 0.05 (both real and imag)
- Levene test p-value > 0.05 (both real and imag)
- Q-Q plot deviations < 10%
- Amplitude distribution matches Rayleigh

### 4. Uncertainty Propagation

Measurement uncertainties combine:

**T_sys uncertainty**:

```
δT_sys / T_sys = sqrt[(δS_cal/S_cal)² + (δσ_vis/σ_vis)² + (δη/η)²]
```

Typical contributions:

- Calibrator flux: 3% (systematic)
- Noise measurement: 5-10% (statistical, depends on N_samples)
- Efficiency: 10% (unknown unless measured)
- **Combined**: ~12-15%

**Gain stability uncertainty**:

```
δσ_gain = σ_gain / sqrt(N_antennas * N_times)
```

For DSA-110: N_antennas = 117, N_times ~ 20 → δσ_gain ~ 2% of σ_gain

**Propagation to simulation**:

- Generate parameters from Gaussian: N(μ, σ²)
- For each simulation run, sample parameter values
- Ensemble of simulations captures uncertainty distribution

## Usage Examples

### Example 1: Measure T_sys from 3C286 Observation

```bash
conda activate casa6

python scripts/measure_system_parameters.py \
    --ms /stage/dsa110-contimg/ms/3C286_2025-11-20.ms \
    --calibrator 3C286 \
    --output-dir measurements/tsys_3C286 \
    --plot
```

**Output**:

- `system_parameters.json` - Per-antenna measurements
- `system_parameters.yaml` - Human-readable format
- `system_parameters_summary.txt` - Text report
- `system_parameters.png` - Diagnostic plots

**Typical results**:

```
T_sys: 52.3 ± 8.1 K (median: 50.8 K)
SEFD: 387.4 ± 62.1 Jy (median: 375.2 Jy)
```

### Example 2: Analyze Gain Stability from Caltable

```bash
python scripts/analyze_calibration_stability.py \
    --caltable /data/dsa110-contimg/products/caltables/observation.G0 \
    --output-dir measurements/stability \
    --plot
```

**Output**:

- `calibration_stability.json` - Per-antenna statistics
- `calibration_stability.yaml` - Human-readable
- `calibration_stability_summary.txt` - Text report
- `calibration_stability.png` - Stability plots

**Typical results**:

```
Amplitude stability: 8.2% (median: 7.9%)
Phase stability: 12.3° (median: 11.8°)
Comparison with defaults: Sim=10%, Measured=7.9% (ratio: 0.79)
→ Consider updating to 7.9%
```

### Example 3: Validate Noise Model

```bash
python scripts/validate_noise_model.py \
    --real-ms /stage/dsa110-contimg/ms/observation.ms \
    --system-temp-k 50 \
    --efficiency 0.7 \
    --n-synthetic 10000 \
    --output-dir measurements/noise_validation \
    --plot
```

**Output**:

- `noise_validation.json` - Statistical test results
- `noise_validation.yaml` - Human-readable
- `noise_validation_summary.txt` - Text report
- `noise_validation.png` - Distribution comparisons

**Typical results**:

```
KS test (real): p-value = 0.23 (match: True)
KS test (imag): p-value = 0.31 (match: True)
Levene test (real): p-value = 0.45 (match: True)
Overall validation: PASS
```

### Example 4: Complete System Characterization

```bash
python scripts/characterize_dsa110_system.py \
    --ms-dir /stage/dsa110-contimg/ms \
    --caltable-dir /data/dsa110-contimg/products/caltables \
    --output-dir system_characterization/
```

**This orchestrates**:

1. Scans for all calibrator observations (3C286, 3C48, etc.)
2. Measures T_sys/SEFD from each calibrator
3. Analyzes up to 5 gain tables for stability
4. Validates noise model against real observations
5. Aggregates results across all measurements
6. Generates comprehensive report with parameter recommendations

**Output**:

- `system_characterization_report.json` - Full results
- `system_characterization_report.yaml` - Human-readable
- `system_characterization_summary.txt` - Text summary
- Subdirectories with individual measurement results

**Example summary**:

```
Recommended Parameters:
  system_temperature: 51.2 ± 7.3 K (measured, N=5 observations)
  sefd: 382.1 ± 58.4 Jy (measured, N=5 observations)
  gain_amplitude_std: 0.082 ± 0.014 (measured, N=5 caltables)
  gain_phase_std: 11.9 ± 2.1 deg (measured, N=5 caltables)

Noise Model Validation: VALIDATED (5/5 passed, 100%)
```

## Updating Simulation Code

After running characterization:

**1. Update YAML parameter file**:

Edit
`backend/src/dsa110_contimg/simulation/config/dsa110_measured_parameters.yaml`:

```yaml
system_parameters:
  system_temperature:
    value: 51.2 # From measurement
    unit: "K"
    uncertainty: 7.3
    uncertainty_type: "std"
    measurement_date: "2025-11-25T12:00:00Z"
    source_observations:
      - "/stage/dsa110-contimg/ms/3C286_2025-11-20.ms"
      - "/stage/dsa110-contimg/ms/3C48_2025-11-21.ms"
    derivation_method: "Radiometer equation applied to calibrator observations"
    validation_status: "measured" # Changed from "assumed"
    references:
      - "Perley & Butler 2017, ApJS 230, 7 (flux scale)"
    notes: "Based on 5 calibrator observations, 117 antennas"
    last_updated: "2025-11-25T12:00:00Z"
    version: "1.0.0" # Incremented from 0.1.0
```

**2. Simulation code automatically uses measured values**:

The updated `visibility_models.py` now loads parameters:

```python
from dsa110_contimg.simulation.visibility_models import (
    calculate_thermal_noise_rms,
    add_calibration_errors,
)

# Uses measured values from YAML automatically
rms = calculate_thermal_noise_rms(
    integration_time_sec=12.88,
    channel_width_hz=244140.625,
    # system_temperature_k not specified → loads from YAML
    # efficiency not specified → loads from YAML
)

# If YAML has validation_status="assumed", emits warning
# If validation_status="measured", uses value silently
```

**3. Disable parameter loading** (for testing):

```python
rms = calculate_thermal_noise_rms(
    integration_time_sec=12.88,
    channel_width_hz=244140.625,
    use_measured_params=False,  # Use hardcoded defaults
)
```

## Comparison with Other Facilities

### VLA (25m dishes, L-band)

- **T_sys**: 30-40 K (excellent receiver performance)
- **SEFD**: 300-420 Jy (depends on configuration)
- **Gain stability**: 3-5% (thermal control, short baselines)
- **Phase stability**: 10-15° (similar atmospheric path)

**Reference**: VLA Observational Status Summary (OSS)

### ASKAP (12m dishes, L-band)

- **T_sys**: 50 K (similar to DSA-110)
- **SEFD**: 2000 Jy (smaller dishes → higher SEFD)
- **Gain stability**: 3-10% (phased array feeds → complex)
- **Phase stability**: 5-10° (dry site, short baselines)

**Reference**: Hotan et al. 2021, PASA 38, e009

### MeerKAT (13.5m dishes, L-band)

- **T_sys**: 20-30 K (cryogenic receivers)
- **SEFD**: 400 Jy (excellent sensitivity)
- **Gain stability**: 2-5% (active thermal control)
- **Phase stability**: 5-15° (Karoo site)

**Reference**: Camilo et al. 2018, ApJ 856, 180

### DSA-110 Expected Performance

Based on geometry:

- **T_sys**: 50-70 K (ambient temperature receivers, similar to ASKAP)
- **SEFD**: 350-450 Jy (4.65m dishes, ~70% efficiency)
- **Gain stability**: 5-10% (no active thermal control)
- **Phase stability**: 10-20° (Owens Valley, dry site)

**After measurement**: Update with actual values from characterization.

## Validation Criteria

For publication-quality simulations:

**Requirements**:

1. ✅ T_sys measured from ≥3 independent calibrator observations
2. ✅ SEFD uncertainty < 20% (statistical + systematic)
3. ✅ Gain stability characterized from ≥5 caltables
4. ✅ Noise validation passes statistical tests (KS + Levene p > 0.05)
5. ✅ All parameters documented with provenance (sources, dates, methods)
6. ✅ References cited for calibrator flux standards
7. ✅ Comparison with similar facilities (within factor of 2)

**Optional enhancements**:

- Measure efficiency from holography or celestial calibrators
- Frequency-dependent T_sys (measure per subband)
- Time-dependent stability (diurnal, seasonal)
- Ionospheric phase screen (separate from troposphere)
- RFI characterization (spectral occupancy, time structure)

## Future Work

### Priority 1: RFI Simulation

**Not currently implemented** but important for testing flagging algorithms:

1. Narrowband RFI (satellite downlinks, radar)
2. Broadband RFI (lightning, arcing)
3. Time-variable RFI (intermittent sources)
4. Spectral line RFI (aircraft altimeters, GPS)

**Approach**:

- Measure RFI from real observations (FFT analysis)
- Model temporal/spectral characteristics
- Inject into simulations with realistic statistics

### Priority 2: Ionospheric Effects

Currently lumped into "phase stability". Separate effects:

1. TEC fluctuations (differential ionospheric delay)
2. Scintillation (amplitude variations)
3. Faraday rotation (polarization angle change)

**Approach**:

- Use GPS TEC maps for site location
- Model Kolmogorov turbulence with realistic outer scale
- Compute phase screens per antenna, time-evolving

### Priority 3: Antenna Failures

Simulate realistic failure modes:

1. Complete antenna outages (flagged)
2. Partial failures (high noise, bad phases)
3. Intermittent dropouts

**Approach**:

- Analyze real flagging statistics from database
- Model failure rates per antenna (Poisson process)
- Inject into simulations probabilistically

## References

### Calibrator Flux Standards

Perley, R.A., & Butler, B.J. 2017, "An Accurate Flux Density Scale from 50 MHz
to 50 GHz", ApJS 230, 7 (DOI: 10.3847/1538-4365/aa6df9)

### Radiometer Equation

Wilson, T.L., Rohlfs, K., & Hüttemeister, S. 2013, "Tools of Radio Astronomy",
6th ed., Springer (ISBN: 978-3-642-39950-3)

### Statistical Tests

- Kolmogorov-Smirnov: Massey, F.J. 1951, J. Amer. Stat. Assoc. 46, 68
- Anderson-Darling: Stephens, M.A. 1974, J. Amer. Stat. Assoc. 69, 730
- Levene's test: Levene, H. 1960, "Robust Tests for Equality of Variances",
  Contributions to Probability and Statistics

### Facility Comparisons

- VLA: https://science.nrao.edu/facilities/vla/docs/manuals/oss
- ASKAP: Hotan et al. 2021, PASA 38, e009
- MeerKAT: Camilo et al. 2018, ApJ 856, 180
- VAST Survey: Murphy et al. 2021, PASA 38, e054

## Contact

For questions about system characterization:

- Measurement methodology: See this document
- Script usage: Run with `--help` flag
- Parameter interpretation: Consult theory section above
- Results validation: Compare with facility benchmarks

## Change Log

- **v1.0.0 (2025-11-25)**: Initial rigorous characterization framework
  - Created 4 measurement scripts
  - Implemented parameter registry with provenance
  - Updated visibility_models.py to load measured parameters
  - Documented complete methodology and validation criteria
