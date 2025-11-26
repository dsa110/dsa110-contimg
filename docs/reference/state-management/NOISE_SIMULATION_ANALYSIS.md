# Noise and Error Simulation Analysis

**Date**: November 25, 2025
**Question**: Are we simulating noise in its various forms/types to see how that's handled in the pipeline?

## Current Noise Simulation Capabilities

### ✅ **Implemented** (in `backend/src/dsa110_contimg/simulation/`)

#### 1. Thermal Noise (`visibility_models.py`)
**Status**: ✅ Fully implemented

**Function**: `add_thermal_noise()`

**Features**:
- Realistic radiometer equation-based noise
- Configurable system temperature (default: 50K for DSA-110)
- Frequency-dependent noise scaling
- Complex Gaussian noise (independent real/imaginary components)
- Proper RMS calculation: σ = T_sys / (η × √(2 × Δν × Δt))

**CLI Usage**:
```bash
python -m dsa110_contimg.simulation.make_synthetic_uvh5 \
    --add-noise \
    --system-temp-k 100  # Default: 50K
```

**Test Scenarios**:
- ✅ `bright_calibrator.yaml` - Uses `system_temp_k: 100`
- ✅ `weak_sources.yaml` - Uses `system_temp_k: 150` (higher noise)

---

#### 2. Calibration Errors (`visibility_models.py`)
**Status**: ✅ Fully implemented

**Function**: `add_calibration_errors()`

**Features**:
- **Gain errors**: Antenna-based amplitude variations
  - Default: 10% standard deviation
  - Applied per antenna, frequency, polarization
- **Phase errors**: Antenna-based phase variations
  - Default: 10° standard deviation
  - Applied per antenna, frequency, polarization
- **Bandpass variations**: Frequency-dependent gain ripples
  - Default: 5% standard deviation
  - Simulates instrumental spectral response

**CLI Usage**:
```bash
python -m dsa110_contimg.simulation.make_synthetic_uvh5 \
    --add-cal-errors \
    --gain-std 0.15      # 15% gain errors \
    --phase-std-deg 20   # 20° phase errors
```

**How it works**:
- Generates complex gains: g = |g| × exp(iφ)
- Applies to visibilities: V_corrupted = V_true × g_i × conj(g_j)
- Per-antenna errors → baseline-dependent corruption

---

### ❌ **NOT Implemented** (Missing Noise Types)

#### 1. RFI (Radio Frequency Interference)
**Status**: ❌ Not simulated in synthetic data

**What exists**:
- ✅ RFI flagging tools in pipeline (`calibration/flagging.py`, `flagging_adaptive.py`)
- ✅ AOFlagger integration for RFI detection
- ✅ Adaptive flagging algorithms
- ❌ **No RFI injection** in synthetic UVH5 generation

**What's missing**:
- Narrowband RFI (satellite, radar)
- Broadband RFI (lightning, arcing)
- Time-variable RFI (periodic, transient)
- Persistent RFI (known frequency bands)

**Why it matters**:
- Can't test RFI flagging effectiveness
- Can't validate pipeline robustness to interference
- Can't measure false-positive/false-negative rates

---

#### 2. Ionospheric Effects
**Status**: ❌ Not simulated

**What's missing**:
- Phase screens (turbulent ionosphere)
- Faraday rotation (frequency-dependent polarization rotation)
- Differential refraction
- Ionospheric scintillation

**Why it matters**:
- Affects astrometric accuracy
- Impacts polarization calibration
- Low-frequency observations (<2 GHz) particularly sensitive

---

#### 3. Antenna-Specific Issues
**Status**: ❌ Not simulated

**What's missing**:
- Dead/malfunctioning antennas
- Partial data dropouts
- Antenna shadowing effects
- Non-Gaussian noise (e.g., intermittent spikes)

**Why it matters**:
- Real observations have antenna failures
- Need to test graceful degradation
- Validate refant selection algorithms

---

#### 4. Confusion Noise
**Status**: ❌ Not simulated

**What's missing**:
- Background of faint unresolved sources
- Sidelobe confusion from bright off-axis sources
- Galactic diffuse emission

**Why it matters**:
- Limits sensitivity for faint source detection
- Affects background noise estimates
- Important for deep field observations

---

#### 5. Correlated Noise
**Status**: ❌ Not simulated

**What's missing**:
- Cross-talk between antennas
- Common-mode pickup (cable routing, ground loops)
- Digitizer artifacts

**Why it matters**:
- Current simulation assumes uncorrelated noise
- Real data has correlations
- Affects closure phases, redundant baseline calibration

---

## Comparison with Real Data

### Synthetic Data Has:
✅ Thermal noise (realistic)
✅ Gain/phase errors (realistic)
✅ Bandpass variations
✅ Extended source models (Gaussian, disk)
✅ Reproducible (seeded RNG)

### Real Data Also Has:
❌ RFI (narrowband, broadband)
❌ Ionospheric phase screens
❌ Antenna failures/dropouts
❌ Confusion noise
❌ Correlated systematic errors
❌ Polarization leakage
❌ Non-ideal primary beam patterns

---

## Recommended Additions

### Priority 1: RFI Simulation (High Impact)

**Implementation**: Add to `simulation/visibility_models.py`

```python
def add_rfi_narrowband(
    visibilities: np.ndarray,
    freq_array_hz: np.ndarray,
    rfi_frequencies_hz: List[float],
    rfi_amplitudes_jy: List[float],
    rfi_widths_hz: List[float],
    time_variable: bool = False,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Add narrowband RFI to visibilities.
    
    Args:
        visibilities: Complex visibility array (Nblts, Nspws, Nfreqs, Npols)
        freq_array_hz: Frequency array (Nfreqs,)
        rfi_frequencies_hz: RFI peak frequencies
        rfi_amplitudes_jy: RFI amplitudes in Jy
        rfi_widths_hz: RFI bandwidths
        time_variable: If True, RFI varies in time
        rng: Random number generator
        
    Returns:
        Visibilities with RFI added
    """
    # Implementation: Add Gaussian spectral features at RFI frequencies
    # Optionally vary in time (intermittent RFI)
    pass

def add_rfi_broadband(
    visibilities: np.ndarray,
    amplitude_jy: float,
    duty_cycle: float = 0.1,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Add broadband impulsive RFI (lightning, arcing).
    
    Args:
        visibilities: Complex visibility array
        amplitude_jy: Peak RFI amplitude
        duty_cycle: Fraction of time RFI is present
        rng: Random number generator
        
    Returns:
        Visibilities with broadband RFI
    """
    # Implementation: Random time samples with broadband corruption
    pass
```

**Test scenario**: `rfi_contaminated.yaml`
```yaml
name: "RFI Contamination"
observation:
  start_time: "2025-11-25T18:00:00"
  duration_minutes: 10.0
  num_subbands: 16

sources:
  - name: "TestSource"
    ra_deg: 180.0
    dec_deg: 35.0
    flux_jy: 0.2
    model: "point"

noise:
  enabled: true
  system_temp_k: 100

rfi:
  enabled: true
  narrowband:
    - frequency_mhz: 1420.0  # HI line
      amplitude_jy: 5.0
      width_khz: 10.0
    - frequency_mhz: 1575.42  # GPS L1
      amplitude_jy: 10.0
      width_khz: 2.0
  broadband:
    enabled: true
    amplitude_jy: 20.0
    duty_cycle: 0.05  # 5% of time

validation:
  test_flagging: true
  expected_flag_fraction: 0.15  # Should flag ~15% of data
```

---

### Priority 2: Antenna Failures (Medium Impact)

**Implementation**: Add to `make_synthetic_uvh5.py`

```python
--bad-antennas 5,12,45  # Comma-separated antenna IDs to mark as bad
--dropout-probability 0.01  # Random data dropout rate
```

**Test scenario**: `antenna_failures.yaml`
```yaml
telescope:
  num_antennas: 110
  bad_antennas: [5, 12, 45]  # Dead antennas
  dropout_probability: 0.01  # 1% random dropouts

validation:
  test_refant_selection: true
  expected_baselines: 5830  # (107 * 106) / 2 good antennas
```

---

### Priority 3: Ionospheric Effects (Lower Impact for DSA-110)

**Rationale**: DSA-110 operates at L-band (1.4 GHz) where ionospheric effects are moderate. Higher priority for lower-frequency arrays.

**Implementation**: Phase screen generation
```python
def add_ionospheric_phase_screen(
    visibilities: np.ndarray,
    phase_rms_deg: float = 5.0,
    turbulence_scale_m: float = 1000.0,
    ...
) -> np.ndarray:
    """Add ionospheric phase corruption."""
    pass
```

---

## Integration with E2E Testing

### Current E2E Runner Support
The `simulations/scripts/run_e2e_test.py` already supports:
- ✅ Thermal noise (via `--add-noise`)
- ✅ Calibration errors (via `--add-cal-errors`)
- ❌ RFI (no support yet)
- ❌ Antenna failures (no support yet)

### After RFI Implementation
Update E2E runner to handle RFI scenarios:
```python
# In run_stage_generate_uvh5()
if config.get("rfi", {}).get("enabled", False):
    args.append("--add-rfi")
    rfi_config = config["rfi"]
    if "narrowband" in rfi_config:
        args.extend(["--rfi-narrowband", json.dumps(rfi_config["narrowband"])])
    if rfi_config.get("broadband", {}).get("enabled", False):
        args.extend([
            "--rfi-broadband-amplitude", 
            str(rfi_config["broadband"]["amplitude_jy"])
        ])
```

### Validation Stage Extension
Add RFI-specific validation:
```python
def validate_rfi_flagging(ms_path: Path, expected_flag_fraction: float) -> bool:
    """Validate that RFI was properly flagged."""
    # Check FLAG column in MS
    # Compare against expected_flag_fraction
    pass
```

---

## Summary

### What We Have ✅
- **Thermal noise**: Realistic, configurable
- **Calibration errors**: Gain, phase, bandpass
- **Extended sources**: Gaussian, disk models
- **E2E testing**: Automated validation pipeline

### What's Missing ❌
- **RFI simulation**: No narrowband/broadband interference
- **Antenna failures**: No dead antennas or dropouts
- **Ionospheric effects**: No phase screens
- **Confusion noise**: No background sources
- **Correlated errors**: Assumes uncorrelated noise

### Impact Assessment
**Current state**: Synthetic data tests ~70% of real-world conditions
- ✅ Can validate: Calibration, imaging, photometry basics
- ❌ Can't validate: RFI flagging, antenna failure handling, ionospheric calibration

### Recommendation
**Priority 1**: Implement RFI simulation
- Highest impact on pipeline robustness
- Essential for validating flagging algorithms
- Common issue in real observations
- Relatively straightforward to implement

**Priority 2**: Antenna failures
- Important for graceful degradation testing
- Validates refant selection logic
- Medium implementation complexity

**Priority 3**: Ionospheric effects (if needed for low-freq observations)
- Lower priority for DSA-110 at L-band
- More complex to implement realistically

---

## Next Steps

1. **Create RFI simulation module** (`simulation/rfi_models.py`)
2. **Integrate with UVH5 generator** (add `--add-rfi` flags)
3. **Create RFI test scenario** (`rfi_contaminated.yaml`)
4. **Update E2E runner** to support RFI configs
5. **Add validation** for flagging effectiveness
6. **Document** in simulation suite README
