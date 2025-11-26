# Noise and Calibration Error Simulation - Rigor Assessment

**Date**: November 25, 2025  
**Question**: Is our simulation of thermal noise and calibration errors based directly on the DSA-110 radio telescope? How rigorously are we simulating these noise sources and errors? Could we be doing it more rigorously? Have we developed these methods by using other pipelines/codes as a reference?

---

## Executive Summary

**Rigor Level**: ⚠️ **MODERATE** - Theoretically sound but not empirically validated against DSA-110 measurements

**Key Findings**:
- ✅ Thermal noise uses correct radiometer equation
- ⚠️ System parameters are **HARDCODED ESTIMATES**, not measured values
- ⚠️ Calibration errors use **GENERIC DEFAULTS**, not DSA-110 specific
- ❌ No validation against real DSA-110 data
- ✅ Some inspiration from other pipelines (pyuvsim structure, CASA patterns)

---

## Detailed Analysis

### 1. Thermal Noise Implementation

#### Current Implementation (`visibility_models.py`)

```python
def calculate_thermal_noise_rms(
    integration_time_sec: float,
    channel_width_hz: float,
    system_temperature_k: float = 50.0,  # ⚠️ HARDCODED DEFAULT
    efficiency: float = 0.7,               # ⚠️ HARDCODED DEFAULT
    frequency_hz: float = 1.4e9,
) -> float:
    """Calculate RMS thermal noise for a single visibility.
    
    Uses the radiometer equation:
    sigma = T_sys / (eta * sqrt(2 * delta_nu * delta_t))
    """
    # Convert system temperature to Jy
    # At 1.4 GHz: ~2.0 Jy/K (calibrated value)  # ⚠️ WHERE IS THIS FROM?
    reference_freq_hz = 1.4e9
    conversion_factor = 2.0 * (reference_freq_hz / frequency_hz) ** 2
    t_sys_jy = system_temperature_k * conversion_factor
    
    # Radiometer equation
    rms_jy = t_sys_jy / (efficiency * np.sqrt(2.0 * delta_nu * delta_t))
    return rms_jy
```

#### Assessment

**✅ Correct Physics**:
- Uses standard radiometer equation
- Proper complex Gaussian noise (independent real/imaginary)
- Frequency-dependent scaling

**⚠️ Questionable Parameters**:

| Parameter | Current Value | Source | Issue |
|-----------|---------------|--------|-------|
| `T_sys` | 50K (default) | **Unknown** | No reference to DSA-110 measurements |
| `efficiency` | 0.7 | **Assumed** | No justification |
| `conversion_factor` | 2.0 Jy/K @ 1.4 GHz | **Comment says "calibrated value"** | But calibrated from what? |

**❌ Missing**:
- No citation to DSA-110 commissioning papers
- No reference to measured SEFD (System Equivalent Flux Density)
- No frequency-dependent T_sys variations
- No time/elevation-dependent effects

---

### 2. Calibration Error Implementation

#### Current Implementation (`visibility_models.py`)

```python
def add_calibration_errors(
    visibilities: np.ndarray,
    nants: int,
    gain_std: float = 0.1,        # ⚠️ GENERIC DEFAULT (10%)
    phase_std_deg: float = 10.0,  # ⚠️ GENERIC DEFAULT (10°)
    bandpass_std: float = 0.05,   # ⚠️ GENERIC DEFAULT (5%)
    rng: Optional[np.random.Generator] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Add realistic calibration errors to visibilities.
    
    Applies antenna-based gain and phase errors, and frequency-dependent
    bandpass variations.
    """
    # Generate antenna-based gains and phases
    gain_errors = rng.normal(1.0, gain_std, (nants, nfreqs, npols))
    phase_errors_deg = rng.normal(0.0, phase_std_deg, (nants, nfreqs, npols))
    
    # Add frequency-dependent bandpass variations
    bandpass_errors = rng.normal(1.0, bandpass_std, (nants, nfreqs, npols))
```

#### Assessment

**✅ Correct Structure**:
- Per-antenna errors (correct for radio interferometry)
- Applies to baselines via g_i × conj(g_j)
- Frequency-dependent bandpass variations

**⚠️ Generic Defaults**:

| Parameter | Current Default | DSA-110 Reality | Evidence |
|-----------|-----------------|-----------------|----------|
| Gain std | 10% | **Unknown** | No measurements cited |
| Phase std | 10° | **Unknown** | Likely varies with weather |
| Bandpass std | 5% | **Unknown** | Digital backend should be more stable |

**❌ Missing Physics**:
- No time-varying gains (ionosphere, weather)
- No antenna-position-dependent errors
- No cross-polarization leakage
- No elevation-dependent gains
- No realistic gain stability timescales

---

### 3. Comparison with DSA-110 Reality

#### What We DON'T Know About DSA-110

**System Temperature (T_sys)**:
- ❌ No measured T_sys values found in code
- ❌ No reference to commissioning papers
- ❌ No measured SEFD curves
- ⚠️ Using "50K default" - is this realistic for 4.5m dishes at L-band?

**Calibration Stability**:
- ❌ No measured gain stability timescales
- ❌ No typical phase RMS from real data
- ❌ No bandpass shape characterization
- ❌ No ionospheric phase screen measurements

**Expected Values** (typical L-band systems):
- SEFD: ~5000-10000 Jy for small dishes
- T_sys: 50-100K (receiver + sky + spillover)
- Gain stability: 1-5% over hours
- Phase stability: 5-20° over minutes (ionosphere)

---

### 4. References to Other Pipelines/Codes

#### Evidence of External Influences

**pyuvsim** (Found in code):
- Directory structure: `backend/src/dsa110_contimg/simulation/pyuvsim/`
- Files: `telescope.yaml`, `antennas.csv`, `beams.yaml`
- **Purpose**: Uses pyuvsim-compatible configuration format
- **Evidence**: `build_antennas_csv.py` converts DSA-110 antenna positions to pyuvsim format

**CASA** (Implicit):
- Uses CASA-style MS format
- Integration time: 12.88s (matches CASA patterns)
- Some functions reference `simobserve` in QA code

**VAST Pipeline** (External Reference):
- Found in `archive/references/VAST/`
- **Forced photometry methods** clearly borrowed from VAST
- Likely inspired calibration/imaging patterns

#### What's NOT Referenced

❌ No citations to:
- DSA-110 commissioning papers
- Measured system performance
- Comparison with real observations
- Validation against known sources

---

### 5. How Rigorous Could We Be?

#### Priority 1: Empirical Validation (HIGH IMPACT)

**Action**: Measure noise from real DSA-110 observations

```python
# Proposed addition to visibility_models.py
def estimate_tsys_from_ms(
    ms_path: str,
    calibrator_field: int,
    expected_flux_jy: float,
) -> float:
    """Estimate T_sys from real calibrator observations.
    
    Args:
        ms_path: Path to calibrated MS
        calibrator_field: Field ID of flux calibrator
        expected_flux_jy: Known flux of calibrator
        
    Returns:
        Estimated T_sys in Kelvin
        
    Method:
        1. Measure RMS noise in off-source data
        2. Compare to radiometer equation
        3. Back-calculate T_sys
    """
    pass
```

**Deliverable**: Create `DSA110_SYSTEM_PARAMETERS.yaml`:
```yaml
# Measured system parameters from commissioning data
system_temperature:
  value_k: 75.0  # Measured median
  std_k: 15.0    # Typical variation
  reference: "DSA-110 Commissioning Report 2024"
  
sefd:
  value_jy: 7500  # At zenith, 1.4 GHz
  elevation_dependence: "SEFD(el) = SEFD_zen / sin(el)"
  
efficiency:
  correlator: 0.85  # Digital correlator efficiency
  system: 0.70      # Total system efficiency
  
calibration_stability:
  gain_rms_percent: 3.5  # Measured over 1 hour
  phase_rms_deg: 8.0     # Typical ionospheric contribution
  bandpass_stability_percent: 2.0  # Digital backend stability
  
reference_observations:
  - "2024-10-15_3C286_transit.ms"  # Example calibrator
  - "2024-11-03_J1331+3030_scan.ms"
```

---

#### Priority 2: Realistic Error Models (MEDIUM IMPACT)

**Current**: Static gain/phase errors
**Better**: Time-varying correlated errors

```python
def add_realistic_calibration_errors(
    visibilities: np.ndarray,
    nants: int,
    ntimes: int,
    time_array: np.ndarray,
    gain_timescale_min: float = 60.0,  # Gain drift timescale
    phase_timescale_min: float = 5.0,  # Phase drift timescale (ionosphere)
    **kwargs
) -> np.ndarray:
    """Add time-correlated calibration errors.
    
    Models:
    - Slow gain drifts (instrument temperature)
    - Fast phase variations (ionosphere)
    - Antenna-dependent phase screens
    """
    # Generate correlated time series for gains/phases
    # Use Gaussian process or AR(1) model for temporal correlation
    pass
```

---

#### Priority 3: Validation Suite (HIGH IMPACT)

**Create**: `backend/tests/validation/test_noise_model_accuracy.py`

```python
def test_thermal_noise_vs_real_data():
    """Compare simulated noise to real off-source RMS.
    
    Steps:
    1. Load real MS with no source in pointing
    2. Measure RMS in data
    3. Generate synthetic observation with same parameters
    4. Compare RMS distributions
    5. Assert within 20% agreement
    """
    pass

def test_gain_stability_timescales():
    """Validate gain error timescales match observations.
    
    Steps:
    1. Load real MS with calibration solutions
    2. Measure gain variation timescales
    3. Generate synthetic with same timescales
    4. Compare power spectra of gain variations
    """
    pass
```

---

### 6. Recommendations

#### Immediate Actions (Can Do Now)

1. **Document Current Assumptions**:
   ```python
   # In visibility_models.py
   # ASSUMPTION: T_sys = 50K based on typical L-band receivers
   # WARNING: Not validated against DSA-110 commissioning data
   # TODO: Replace with measured values from real observations
   ```

2. **Add Configuration File**:
   ```yaml
   # simulations/config/dsa110_system_parameters.yaml
   # NOTE: These are ESTIMATES pending commissioning data validation
   
   thermal_noise:
     system_temperature_k: 50  # ASSUMPTION: Typical L-band
     uncertainty_k: 25         # ±50% uncertainty
     validation_status: "unvalidated"
   
   calibration_errors:
     gain_std: 0.10     # ASSUMPTION: Generic interferometer
     phase_std_deg: 10  # ASSUMPTION: Mid-latitude ionosphere
     validation_status: "unvalidated"
   ```

3. **Update Documentation**:
   - Add section to `simulations/README.md` on parameter sources
   - Create `docs/concepts/simulation_assumptions.md`
   - Flag all hardcoded values with sources or "UNVALIDATED"

#### Medium-Term Actions (Need Data)

1. **Commissioning Data Analysis**:
   - Analyze 10+ calibrator observations
   - Measure actual T_sys, SEFD
   - Characterize gain/phase stability
   - Document in commissioning report

2. **Empirical Parameter Extraction**:
   - Create `scripts/characterize_system_noise.py`
   - Create `scripts/measure_calibration_stability.py`
   - Generate `DSA110_SYSTEM_PARAMETERS.yaml` from real data

3. **Validation Against Reality**:
   - Compare synthetic vs real noise statistics
   - Validate calibration error timescales
   - Test image quality metrics match expectations

#### Long-Term Actions (Research Quality)

1. **Published Characterization**:
   - Write "DSA-110 System Performance" paper
   - Cite in simulation code
   - Make parameters citable (Zenodo DOI)

2. **Sophisticated Models**:
   - Ionospheric phase screen generator
   - Elevation-dependent SEFD
   - Weather-dependent T_sys variations
   - Cross-polarization leakage

3. **Benchmark Suite**:
   - Standard test cases with known answers
   - Regression tests against real data
   - Continuous validation pipeline

---

## Summary Table

| Aspect | Current State | Rigor Level | Improvement Path |
|--------|---------------|-------------|------------------|
| **Thermal Noise** | ⚠️ Correct equation, assumed parameters | MODERATE | Measure T_sys from real data |
| **Gain Errors** | ⚠️ Generic defaults | LOW | Characterize stability from caltables |
| **Phase Errors** | ⚠️ Generic defaults | LOW | Analyze ionospheric variations |
| **Bandpass** | ⚠️ Simple Gaussian | LOW | Model actual digital backend response |
| **Validation** | ❌ None | NONE | Compare to real observations |
| **Documentation** | ⚠️ Minimal comments | LOW | Document all assumptions |
| **References** | ❌ No citations | NONE | Cite commissioning papers |

---

## Conclusion

**Current Approach**: 
- ✅ **Theoretically correct** but **empirically unvalidated**
- ✅ Good enough for **algorithm development** and **qualitative testing**
- ❌ **NOT suitable** for rigorous sensitivity predictions
- ❌ **NOT peer-review quality** without validation

**To Achieve Rigor**:
1. **Measure** actual DSA-110 system parameters from real data
2. **Validate** simulations match observed noise statistics
3. **Document** all assumptions and their sources
4. **Cite** commissioning reports or published performance papers
5. **Create** validation suite comparing synthetic vs real

**Effort Required**:
- Immediate (documentation): 2-4 hours
- Medium-term (data analysis): 2-3 weeks
- Long-term (full validation): 2-3 months

**Priority**: 
- **HIGH** if using simulations for sensitivity predictions
- **MEDIUM** if only for algorithm testing
- **CRITICAL** if planning to publish simulation-based results
