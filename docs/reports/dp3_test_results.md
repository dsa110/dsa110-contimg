# DP3 Test Results

## Build Status

✓ **DP3 Docker image built successfully**
- Image: `dp3-everybeam-0.7.4`
- Base: Ubuntu 24.04
- Dependencies: Casacore, EveryBeam 0.7.4, AOFlagger, IDG

## Test Results

### Sky Model Creation

✓ **DP3 sky model format created successfully**
- Created `/scratch/dsa110-contimg/test_wsclean/0702_445.skymodel`
- Format: DP3-compatible text format
- Contains calibrator 0702+445 (RA=07:02:53.679, Dec=+44:31:11.940, Flux=2.4 Jy)

### DP3 Predict Test

✗ **DP3 Predict failed: Polarization mismatch**

**Error:**
```
std exception detected: DP3 expects a measurement set with 4 polarizations
```

**Root Cause:**
- DP3's `MsReader.cc` (line 825-827) enforces 4 polarizations requirement
- DSA-110 MS files use 2 polarizations (CORR_TYPE=[9, 12] = RR, LL)
- This is a hard requirement in DP3's codebase

**DP3 Source Code:**
```cpp
// steps/MsReader.cc:825-827
if (polarizations.size() != 4) {
    throw std::runtime_error(
        "DP3 expects a measurement set with 4 polarizations");
}
```

## Limitations

### 1. Polarization Requirement

**Issue:** DP3 requires 4 polarizations (XX, XY, YX, YY or I, Q, U, V)
**DSA-110:** Uses 2 polarizations (RR, LL = Stokes I)

**Impact:**
- Cannot use DP3 Predict directly on DSA-110 MS files
- Cannot use DP3 ApplyCal directly on DSA-110 MS files

**Workarounds:**
1. **Convert MS to 4-pol format** (add dummy XY, YX, YY = 0)
2. **Use CASA ft()** for sky model seeding (current approach)
3. **Patch DP3** to support 2-pol (not recommended, requires code changes)

### 2. Calibration Table Format

**Issue:** DP3 ApplyCal requires ParmDB format
**DSA-110:** Uses CASA calibration tables (K, BP, G tables)

**Impact:**
- Cannot use DP3 ApplyCal with CASA tables directly
- Would need CASA→ParmDB conversion

**Workaround:**
- Continue using CASA `applycal` (already implemented)

## Recommendations

### For Sky Model Seeding

**Current Approach (Recommended):**
- Use CASA `ft()` for sky model seeding
- Performance: Adequate for current workflow
- Compatibility: Works with 2-pol MS files

**Alternative (If 4-pol conversion is feasible):**
- Create converter to add dummy XY, YX, YY polarizations
- Use DP3 Predict for faster seeding (2-3x speedup expected)
- Trade-off: Additional conversion step, larger MS files

### For Calibration Application

**Current Approach (Recommended):**
- Use CASA `applycal` for calibration application
- No format conversion needed
- Works with existing calibration tables

## Conclusion

**DP3 is not directly compatible with DSA-110 MS files** due to:
1. **4-polarization requirement** (hardcoded in DP3)
2. **ParmDB format requirement** for calibration tables

**Recommendation:**
- **Continue using CASA tools** (`ft()` for seeding, `applycal` for calibration)
- **Keep DP3 wrappers** for future use if polarization conversion is implemented
- **Monitor DP3 development** for potential 2-pol support or workarounds

## Future Work

If DP3 compatibility is desired:
1. Implement MS converter: 2-pol → 4-pol (add dummy polarizations)
2. Implement CASA→ParmDB converter for calibration tables
3. Benchmark performance gains vs conversion overhead

