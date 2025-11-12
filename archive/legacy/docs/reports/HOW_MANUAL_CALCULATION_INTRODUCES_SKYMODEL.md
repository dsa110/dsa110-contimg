# How Manual Calculation Introduces the Calibrator Skymodel

**Date:** 2025-11-05  
**Question:** How does the manual calculation introduce the calibrator skymodel?

---

## 📋 **Overview**

The manual calculation introduces the calibrator skymodel as a **point source** defined by:
1. **Position:** (RA, Dec) - passed as `ra_deg`, `dec_deg` parameters
2. **Flux:** Flux density in Jy - passed as `flux_jy` parameter
3. **Spectral model:** Constant flux (no spectral index in current implementation)

---

## 🔄 **Call Chain**

### **Step 1: CLI Gets Calibrator Information**

**Location:** `src/dsa110_contimg/calibration/cli.py`

Calibrator information comes from one of these sources:

1. **Auto-fields (--auto-fields):**
   ```python
   # Lines ~1004-1039
   calinfo = select_bandpass_from_catalog(...)
   name, ra_deg, dec_deg, flux_jy = calinfo  # Extracted from catalog
   ```

2. **Explicit coordinates (--cal-ra-deg, --cal-dec-deg, --cal-flux-jy):**
   ```python
   # Lines ~1821-1826
   ra_deg = float(args.cal_ra_deg)
   dec_deg = float(args.cal_dec_deg)
   flux_jy = float(getattr(args, 'cal_flux_jy', None) or 2.5)
   ```

### **Step 2: CLI Calls Manual Calculation**

**Location:** `src/dsa110_contimg/calibration/cli.py:1801-1803`

```python
model_helpers.write_point_model_with_ft(
    args.ms, float(ra_deg), float(dec_deg), float(flux_jy),
    field=field_sel, use_manual=True)  # ← use_manual=True triggers manual calculation
```

### **Step 3: Manual Calculation Function**

**Location:** `src/dsa110_contimg/calibration/model.py:_calculate_manual_model_data()`

**Function signature:**
```python
def _calculate_manual_model_data(
    ms_path: str,
    ra_deg: float,      # ← Calibrator RA position
    dec_deg: float,     # ← Calibrator Dec position
    flux_jy: float,     # ← Calibrator flux
    field: Optional[str] = None,
) -> None:
```

---

## 🔬 **How the Skymodel is Introduced**

### **1. Position: Component Location**

The calibrator position is used to calculate the **offset from phase center**:

```python
# Lines 137-139
# Calculate offset from this field's phase center to component
offset_ra_rad = (ra_deg - phase_center_ra_deg) * np.pi / 180.0 * np.cos(phase_center_dec_rad)
offset_dec_rad = (dec_deg - phase_center_dec_deg) * np.pi / 180.0
```

**Key point:** The offset is calculated **per field** using each field's own `PHASE_DIR`, ensuring correct phase structure even when fields have different phase centers.

### **2. Flux: Constant Amplitude**

The calibrator flux is used as the **constant amplitude**:

```python
# Lines 154-155
# Amplitude is constant (flux_jy)
amplitude = float(flux_jy)
```

**Note:** Current implementation uses **constant flux** (no spectral index). The `ft()` version supports spectral index via `reffreq_hz` and `spectral_index` parameters, but manual calculation does not yet implement spectral index.

### **3. Phase: Visibility Formula**

The phase is calculated using the standard visibility formula:

```python
# Lines 149-152
# Calculate phase for each channel using this field's phase center
# phase = 2π * (u*ΔRA + v*ΔDec) / λ
phase = 2 * np.pi * (u[row_idx] * offset_ra_rad + v[row_idx] * offset_dec_rad) / wavelengths
phase = np.mod(phase + np.pi, 2*np.pi) - np.pi  # Wrap to [-π, π]
```

**Where:**
- `u[row_idx]`, `v[row_idx]` = baseline coordinates (from UVW column)
- `offset_ra_rad`, `offset_dec_rad` = offset from phase center to component (calculated above)
- `wavelengths` = wavelength for each channel (calculated from CHAN_FREQ)

### **4. Complex Visibilities: MODEL_DATA**

The complex visibilities are created:

```python
# Lines 157-163
# Create complex model: amplitude * exp(i*phase)
# Shape: (nchan,)
model_complex = amplitude * (np.cos(phase) + 1j * np.sin(phase))

# Broadcast to all polarizations: (nchan,) -> (nchan, npol)
model_data[row_idx, :, :] = model_complex[:, np.newaxis]
```

**Result:** `MODEL_DATA[row_idx, :, :]` contains the predicted complex visibilities for a point source at `(ra_deg, dec_deg)` with flux `flux_jy`.

---

## 📊 **Complete Flow Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CLI Gets Calibrator Info                                 │
│    - From catalog (--auto-fields)                           │
│    - OR explicit args (--cal-ra-deg, --cal-dec-deg, etc.)  │
│    → ra_deg, dec_deg, flux_jy                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CLI Calls write_point_model_with_ft()                    │
│    write_point_model_with_ft(                               │
│        ms_path, ra_deg, dec_deg, flux_jy,                   │
│        use_manual=True  ← Triggers manual calculation       │
│    )                                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Manual Calculation (_calculate_manual_model_data)        │
│                                                              │
│    For each row in MS:                                      │
│      a. Get field's PHASE_DIR (phase center)                │
│      b. Calculate offset: (ra_deg, dec_deg) - phase_center │
│      c. Get baseline: u, v from UVW                         │
│      d. Get wavelength: λ from CHAN_FREQ                    │
│      e. Calculate phase: 2π * (u*ΔRA + v*ΔDec) / λ         │
│      f. Create complex: flux_jy * exp(i*phase)              │
│      g. Write to MODEL_DATA[row_idx, :, :]                  │
│                                                              │
│    Result: MODEL_DATA contains predicted visibilities for   │
│            point source at (ra_deg, dec_deg) with flux_jy   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 **Key Differences from ft()**

### **ft() Approach:**
1. Creates component list (.cl file) with component at `(ra_deg, dec_deg)`
2. Calls CASA `ft()` to populate MODEL_DATA
3. `ft()` reads phase center from FIELD table (uses ONE phase center for ALL fields)
4. `ft()` calculates visibilities internally

### **Manual Calculation Approach:**
1. Directly calculates visibilities using visibility formula
2. Uses **each field's own PHASE_DIR** (per-field phase centers)
3. Explicitly calculates phase: `2π * (u*ΔRA + v*ΔDec) / λ`
4. Writes MODEL_DATA directly

---

## ⚠️ **Limitations**

### **Current Implementation:**
- ✅ Point source model (position, flux)
- ✅ Per-field phase center handling
- ✅ Frequency-dependent phase (via wavelength)
- ❌ **No spectral index** (flux is constant across frequency)

### **ft() Has Spectral Index:**
- `ft()` supports spectral index via `reffreq_hz` and `spectral_index` parameters
- Flux varies with frequency: `S(ν) = S(ν₀) * (ν/ν₀)^α`

### **Future Enhancement:**
To add spectral index support to manual calculation:
1. Add `spectral_index` parameter to `_calculate_manual_model_data()`
2. Calculate frequency-dependent flux: `flux(ν) = flux_jy * (ν/reffreq_hz)^spectral_index`
3. Use `flux(ν)` instead of constant `flux_jy` in amplitude calculation

---

## ✅ **Summary**

**How the calibrator skymodel is introduced:**

1. **Position:** `ra_deg`, `dec_deg` → Used to calculate offset from phase center
2. **Flux:** `flux_jy` → Used as constant amplitude
3. **Phase:** Calculated via visibility formula using offset, baseline (u,v), and wavelength
4. **Result:** `MODEL_DATA` contains predicted complex visibilities for a point source at calibrator position with calibrator flux

**Key advantage:** Manual calculation uses **each field's own PHASE_DIR**, ensuring correct phase structure even when fields have different phase centers, whereas `ft()` uses one phase center for all fields.

