# Manual Calculation Correctness Assessment

**Date:** 2025-11-05  
**Question:** How certain are we that the manual calculation is 100% correct?

---

## 🎯 **Confidence Level: ~85-90%**

**Summary:** The core physics and mathematics are correct, but there are some assumptions and potential edge cases that haven't been fully verified.

---

## ✅ **What We're Confident About**

### **1. Core Visibility Formula (100% Confident)**

```python
phase = 2 * np.pi * (u * offset_ra_rad + v * offset_dec_rad) / wavelengths
```

**Why confident:**
- This is the **standard interferometry visibility phase formula**
- Mathematically correct: phase = 2π * baseline_projection / λ
- Used throughout radio astronomy literature
- Verified in textbooks (e.g., Thompson, Moran, Swenson)

### **2. Per-Field Phase Center Handling (100% Confident)**

```python
phase_center_ra_rad = phase_dir[row_field_idx][0][0]
phase_center_dec_rad = phase_dir[row_field_idx][0][1]
```

**Why confident:**
- Reads each field's own `PHASE_DIR`
- This is the correct approach for multi-field MS
- Verified by the fact that all 24 fields in test MS have same phase center after rephasing

### **3. Frequency/Wavelength Calculation (100% Confident)**

```python
wavelengths = 3e8 / freqs  # Speed of light / frequency
```

**Why confident:**
- Standard physics: λ = c / ν
- Uses correct speed of light (3e8 m/s)
- Reads frequencies from CHAN_FREQ correctly

### **4. Coordinate System and Units (95% Confident)**

**RA offset calculation:**
```python
offset_ra_rad = (ra_deg - phase_center_ra_deg) * np.pi / 180.0 * np.cos(phase_center_dec_rad)
offset_dec_rad = (dec_deg - phase_center_dec_deg) * np.pi / 180.0
```

**Why confident:**
- `cos(dec)` factor is correct for angular RA offsets (accounts for longitude convergence at poles)
- Degree to radian conversion is correct
- Matches standard astronomical coordinate transformations

**Potential issue:** The `cos(dec)` factor is applied to the **phase center's declination**, not the component's declination. For small offsets (< 1°), this is fine, but for large offsets it could introduce small errors. However, this is likely negligible for our use case.

---

## ⚠️ **What We're Less Certain About**

### **1. Phase Wrapping (85% Confident)**

```python
phase = np.mod(phase + np.pi, 2*np.pi) - np.pi  # Wrap to [-π, π]
```

**Why less certain:**
- Wraps to [-π, π] range, which is fine mathematically
- **Question:** Should phase be wrapped at all, or should it be continuous?
- **In practice:** Phase wrapping is fine for complex exponential calculation
- **But:** For comparison with DATA, continuous phase might be better

**Verification needed:**
- Compare wrapped vs unwrapped phase with actual DATA phase
- Check if wrapping introduces discontinuities that affect calibration

### **2. Complex Number Calculation (90% Confident)**

```python
model_complex = amplitude * (np.cos(phase) + 1j * np.sin(phase))
```

**Why confident:**
- This is equivalent to `amplitude * exp(i*phase)` ✓
- Mathematically correct
- Standard way to create complex visibilities

**Potential issue:**
- Could use `np.exp(1j * phase)` which might be slightly faster, but current approach is fine

### **3. Polarization Broadcasting (80% Confident)**

```python
model_data[row_idx, :, :] = model_complex[:, np.newaxis]
```

**Why less certain:**
- Broadcasts same complex value to all polarizations
- **Assumption:** Point source has same flux in all polarizations (unpolarized source)
- **For calibrators:** Usually unpolarized, so this is likely correct
- **But:** If calibrator is polarized, this would be wrong

**Verification needed:**
- Check if calibrator is polarized (for DSA-110, calibrators are typically unpolarized)
- Verify polarization structure in DATA vs MODEL_DATA

### **4. No Spectral Index (Known Limitation)**

```python
amplitude = float(flux_jy)  # Constant across all frequencies
```

**Why less certain:**
- Current implementation uses **constant flux** across all frequencies
- Real sources have spectral index: `S(ν) = S(ν₀) * (ν/ν₀)^α`
- **For 1.4 GHz bandpass:** Spectral index effects are small (typically α ≈ -0.7)
- **Impact:** Likely negligible for narrow bandwidth, but could matter for wide bandwidth

**Verification needed:**
- Compare with `ft()` output that includes spectral index
- Check if flux variation across channels affects calibration

---

## ❓ **What We Haven't Verified**

### **1. Direct Comparison with ft() Output**

**Missing test:**
- Run `ft()` on MS where all fields share same phase center (should work correctly)
- Compare `ft()` output with manual calculation output
- Should match exactly (within numerical precision)

**Why this matters:**
- Would confirm that manual calculation produces same results as `ft()` when `ft()` works correctly
- Would catch subtle bugs in coordinate transformations or phase calculations

### **2. Edge Cases**

**Not tested:**
- Very large phase offsets (> 90°)
- Source near poles (dec ≈ ±90°)
- Very short baselines (u, v ≈ 0)
- Very long baselines (u, v >> typical)

**Why this matters:**
- Current implementation might have numerical issues at extremes
- Coordinate transformations might break near poles

### **3. Coordinate System Consistency**

**Not verified:**
- Are PHASE_DIR coordinates in same frame as component (ra_deg, dec_deg)?
- Both should be ICRS/J2000, but not explicitly checked
- Different coordinate frames would cause errors

### **4. UVW Coordinate System**

**Not verified:**
- Are UVW coordinates in same frame as phase center?
- UVW should be in ITRF (Earth-fixed) frame
- Phase center should be in ICRS (celestial) frame
- Transformation between frames is handled by CASA, but we assume it's correct

---

## 🔍 **Potential Issues to Check**

### **Issue 1: RA Offset Calculation**

**Current code:**
```python
offset_ra_rad = (ra_deg - phase_center_ra_deg) * np.pi / 180.0 * np.cos(phase_center_dec_rad)
```

**Potential problem:**
- Uses `cos(phase_center_dec_rad)` instead of `cos(component_dec_rad)`
- For small offsets, difference is negligible
- For large offsets (> 10°), could introduce errors

**Fix if needed:**
```python
# Use average declination or component declination
avg_dec_rad = np.mean([phase_center_dec_rad, np.deg2rad(dec_deg)])
offset_ra_rad = (ra_deg - phase_center_ra_deg) * np.pi / 180.0 * np.cos(avg_dec_rad)
```

### **Issue 2: Phase Wrapping**

**Current code:**
```python
phase = np.mod(phase + np.pi, 2*np.pi) - np.pi  # Wrap to [-π, π]
```

**Potential problem:**
- Wrapping might introduce discontinuities
- For comparison with DATA, continuous phase might be better

**Alternative:**
```python
# Don't wrap, keep continuous phase
phase = 2 * np.pi * (u * offset_ra_rad + v * offset_dec_rad) / wavelengths
# Or wrap to [0, 2π]
phase = np.mod(phase, 2*np.pi)
```

### **Issue 3: Polarization Handling**

**Current code:**
```python
model_data[row_idx, :, :] = model_complex[:, np.newaxis]  # Broadcasts to all polarizations
```

**Potential problem:**
- Assumes unpolarized source
- For polarized calibrator, would need Jones matrix or polarization-specific handling

**Fix if needed:**
```python
# Check if calibrator is polarized
# If polarized, apply polarization-specific flux
# For now, assume unpolarized (standard for calibrators)
```

---

## 📊 **Verification Recommendations**

### **High Priority:**

1. **Direct comparison with ft() output:**
   - Create test MS with all fields at same phase center
   - Run `ft()` (should work correctly)
   - Run manual calculation
   - Compare MODEL_DATA values (should match within numerical precision)

2. **Phase wrapping verification:**
   - Compare wrapped vs unwrapped phase
   - Check if wrapping affects calibration results

3. **Coordinate system verification:**
   - Verify PHASE_DIR and component coordinates are in same frame
   - Check UVW coordinate frame consistency

### **Medium Priority:**

4. **Spectral index test:**
   - Compare manual calculation (no spectral index) with `ft()` (with spectral index)
   - Check if flux variation affects calibration

5. **Edge case testing:**
   - Test with large phase offsets
   - Test near poles
   - Test with extreme baselines

### **Low Priority:**

6. **Polarization verification:**
   - Check if calibrator is polarized
   - Verify polarization broadcasting is correct

---

## ✅ **Conclusion**

**Confidence breakdown:**
- **Core physics/math:** 100% confident
- **Per-field phase center handling:** 100% confident
- **Coordinate transformations:** 95% confident
- **Phase wrapping:** 85% confident
- **Polarization handling:** 80% confident
- **Spectral index:** Known limitation (not implemented)

**Overall confidence: ~85-90%**

**Recommendation:**
1. The manual calculation is **likely correct** for the use case (point source calibrator, small offsets, unpolarized)
2. **High priority:** Direct comparison with `ft()` output when `ft()` works correctly
3. **Medium priority:** Verify phase wrapping and coordinate systems
4. **Low priority:** Add spectral index support if needed

**Current status:** The manual calculation works correctly in practice (fixes the phase scatter issue), but some edge cases and assumptions haven't been fully verified.

