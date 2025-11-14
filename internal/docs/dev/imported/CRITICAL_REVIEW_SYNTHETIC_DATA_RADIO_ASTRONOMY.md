# Critical Review: Synthetic Data Generation from Radio Astronomy Perspective

**Date:** 2025-01-XX  
**Reviewer:** Expert Radio Astronomer Analysis  
**Status:** CRITICAL ISSUES FOUND

---

## Executive Summary

A critical review of the synthetic data generation code revealed **3 critical
bugs** in visibility calculations and **1 significant limitation** in noise
modeling. These issues would cause incorrect flux measurements and source size
estimates in synthetic data.

---

## Critical Issues Found

### 🔴 CRITICAL BUG #1: Incorrect Gaussian Visibility Formula

**Location:** `src/dsa110_contimg/simulation/visibility_models.py`, lines
141-150

**Problem:** The Gaussian visibility formula is mathematically incorrect. The
code calculates:

```python
sigma_u_lambda = 1.0 / (2.0 * np.pi * sigma_major_rad)
exponent = -2.0 * np.pi**2 * ((u_rot / sigma_u_lambda) ** 2 + ...)
```

This produces: `V = S * exp(-8*π⁴ * σ² * u²)`

**Correct Formula:** For a Gaussian source with angular size σ (in radians), the
visibility is:

```
V(u,v) = S * exp(-2*π² * σ² * (u² + v²))
```

**Impact:**

- Extended sources appear **much smaller** than requested
- Flux measurements will be incorrect
- Source size estimates from visibility fitting will be wrong
- Error factor: ~39.5 (4\*π²) too large in the exponent

**Fix Required:**

```python
# WRONG (current):
sigma_u_lambda = 1.0 / (2.0 * np.pi * sigma_major_rad)
exponent = -2.0 * np.pi**2 * ((u_rot / sigma_u_lambda) ** 2 + ...)

# CORRECT:
exponent = -2.0 * np.pi**2 * sigma_major_rad**2 * (u_rot**2 + v_rot**2)
```

---

### 🔴 CRITICAL BUG #2: Incorrect Disk Visibility Formula

**Location:** `src/dsa110_contimg/simulation/visibility_models.py`, lines
191-194

**Problem:** The disk visibility formula uses incorrect coordinate
transformation:

```python
radius_lambda = 1.0 / (2.0 * np.pi * radius_rad)
arg = 2.0 * np.pi * radius_lambda * rho_lambda
```

This produces: `arg = rho / radius_rad` (missing 2π factor and wrong
relationship)

**Correct Formula:** For a uniform disk with angular radius θ (in radians):

```
V(ρ) = 2*S * J₁(2π*θ*ρ) / (2π*θ*ρ)
```

where ρ = √(u² + v²) in wavelengths.

**Impact:**

- Disk sources appear **much larger** than requested
- Visibility nulls occur at wrong baselines
- Source size measurements will be incorrect
- Error: Missing 2π factor and inverted relationship

**Fix Required:**

```python
# WRONG (current):
radius_lambda = 1.0 / (2.0 * np.pi * radius_rad)
arg = 2.0 * np.pi * radius_lambda * rho_lambda

# CORRECT:
arg = 2.0 * np.pi * radius_rad * rho_lambda
```

---

### 🔴 CRITICAL BUG #3: Frequency-Dependent T_sys to Jy Conversion

**Location:** `src/dsa110_contimg/simulation/visibility_models.py`, lines 34-36

**Problem:** Hardcoded conversion factor `2.0 Jy/K` is only valid at ~1.4 GHz:

```python
t_sys_jy = system_temperature_k * 2.0  # Only correct at 1.4 GHz
```

**Correct Formula:** The conversion from system temperature to flux density is
frequency-dependent:

```
S = 2*k*T_sys / A_eff
```

where k = 1.38×10⁻²³ J/K and A_eff is the effective collecting area.

For an interferometer, this depends on the synthesized beam solid angle, which
is frequency-dependent.

**Impact:**

- Noise levels incorrect at frequencies other than 1.4 GHz
- SNR calculations wrong for multi-frequency observations
- Calibration quality tests may fail at different frequencies

**Fix Required:** Calculate conversion factor from frequency:

```python
# Approximate for DSA-110: A_eff scales as λ²
# At 1.4 GHz: ~2.0 Jy/K
# General: S = 2*k*T / (eta * A_physical)
# For interferometer, use synthesized beam area
freq_hz = ...  # Need frequency
lambda_m = 2.998e8 / freq_hz
# Conversion factor approximately: 2.0 * (1.4e9 / freq_hz)^2
conversion_factor = 2.0 * (1.4e9 / freq_hz) ** 2
t_sys_jy = system_temperature_k * conversion_factor
```

---

### ⚠️ SIGNIFICANT LIMITATION: Missing Frequency in Noise Calculation

**Location:** `src/dsa110_contimg/simulation/visibility_models.py`,
`add_thermal_noise()`

**Problem:** The `add_thermal_noise()` function doesn't receive frequency
information, so it cannot use the correct T_sys to Jy conversion.

**Impact:**

- Noise added is incorrect for frequencies other than 1.4 GHz
- Multi-frequency synthetic data will have wrong noise levels

**Fix Required:** Pass frequency information to `add_thermal_noise()` and use
frequency-dependent conversion.

---

## Additional Issues

### ⚠️ Position Angle Convention

**Location:** `src/dsa110_contimg/simulation/visibility_models.py`, lines
130-135

**Status:** Needs verification

The position angle rotation appears correct (standard rotation matrix), but
should verify:

- Position angle 0° = North (standard convention)
- Rotation direction (clockwise/counterclockwise)
- Coordinate system (u points East, v points North typically)

**Recommendation:** Add unit test with known source to verify PA rotation.

---

### ⚠️ Polarization Handling

**Location:** `src/dsa110_contimg/simulation/make_synthetic_uvh5.py`, line 257

**Status:** CORRECT

The division by 2.0 to split unpolarized flux between XX and YY is correct for
unpolarized sources.

---

### ⚠️ Radiometer Equation

**Location:** `src/dsa110_contimg/simulation/visibility_models.py`, line 43

**Status:** CORRECT

The radiometer equation implementation is correct:

```
σ = T_sys / (η * √(2 * Δν * Δt))
```

---

## Recommendations

### Immediate Actions (Critical)

1. **Fix Gaussian visibility formula** - This affects all extended source
   simulations
2. **Fix disk visibility formula** - This affects all disk source simulations
3. **Make T_sys to Jy conversion frequency-dependent** - Required for
   multi-frequency data

### Short-term Improvements

1. Add unit tests with known analytical results
2. Verify position angle convention with test cases
3. Add frequency parameter to noise functions
4. Document coordinate system conventions

### Long-term Enhancements

1. Add support for polarized sources
2. Add frequency-dependent system temperature
3. Add atmospheric noise models
4. Add RFI simulation

---

## Testing Recommendations

After fixes, verify:

1. **Gaussian source**: Generate 10 arcsec FWHM source, verify visibility falls
   to 50% at correct baseline
2. **Disk source**: Generate 5 arcsec radius disk, verify first null at correct
   baseline
3. **Noise**: Verify noise RMS scales correctly with frequency
4. **Point source**: Verify constant visibility (already correct)

---

## References

- Thompson, Moran, Swenson: "Interferometry and Synthesis in Radio Astronomy"
- Standard visibility formulas for extended sources
- Radiometer equation and system temperature conversion

---

**Status:** ✅ CRITICAL FIXES COMPLETED

---

## Fixes Applied

### ✅ Fixed: Gaussian Visibility Formula (2025-01-XX)

- **Changed:** Removed incorrect `sigma_lambda = 1/(2π*σ_rad)` calculation
- **Fixed:** Now uses direct formula: `V = S * exp(-2π² * σ² * (u² + v²))`
- **Verified:** Visibility at origin equals flux, decay matches expected
  behavior

### ✅ Fixed: Disk Visibility Formula (2025-01-XX)

- **Changed:** Removed incorrect `radius_lambda = 1/(2π*radius_rad)` calculation
- **Fixed:** Now uses direct formula: `arg = 2π * radius_rad * ρ`
- **Verified:** Visibility at origin equals flux, first null at correct baseline

### ✅ Fixed: Frequency-Dependent T_sys Conversion (2025-01-XX)

- **Changed:** Added `frequency_hz` parameter to `calculate_thermal_noise_rms()`
  and `add_thermal_noise()`
- **Fixed:** Conversion factor now scales as `2.0 * (1.4e9 / frequency_hz)²`
- **Updated:** `make_synthetic_uvh5.py` now passes mean frequency to noise
  function
- **Verified:** Noise calculation now frequency-dependent

---

**Status:** ✅ READY FOR SCIENCE VALIDATION (after testing)
