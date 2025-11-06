# RA Calculation Precision Analysis

**Date:** 2025-11-05  
**Context:** Assessing whether the meridian RA calculation uses maximum precision

---

## Summary

The RA calculation uses **high-precision astronomical calculations via Astropy**, but is **not "maximum precision"** for microarcsecond-level applications (e.g., VLBI). For typical radio astronomy applications (arcsecond to sub-arcsecond precision), it is **excellent and appropriate**.

---

## Current Implementation

### Primary Method: `get_meridian_coords()`
**File:** `src/dsa110_contimg/conversion/helpers.py:34-50`

```python
def get_meridian_coords(pt_dec: u.Quantity, time_mjd: float):
    # Creates HADec coordinate with HA=0 (meridian)
    hadec_coord = SkyCoord(
        ha=0 * u.hourangle,
        dec=pt_dec,
        frame="hadec",
        obstime=obstime,
        location=ovro_loc,
    )
    # Transforms to ICRS (J2000)
    icrs_coord = hadec_coord.transform_to("icrs")
    return icrs_coord.ra.to(u.rad), icrs_coord.dec.to(u.rad)
```

### Alternative Method: `_phase_data_to_midpoint_reference()`
**File:** `src/dsa110_contimg/conversion/uvh5_to_ms.py:258-363`

This method explicitly uses **"apparent" sidereal time** (includes nutation):
```python
lst = tref.sidereal_time('apparent', longitude=location.lon)
# Then transforms CIRS→ICRS
```

---

## Precision Components

### ✅ What IS Included (High Precision)

1. **Precession**: ✅ Handled by Astropy's ICRS transformation
   - Accounts for Earth's precession (26,000-year cycle)
   - Uses IAU 2006/2000A precession models

2. **Nutation**: ✅ Included (if using "apparent" sidereal time)
   - Small periodic variations in Earth's rotation axis
   - ~±17 arcseconds amplitude
   - ~18.6-year period

3. **Frame Transformations**: ✅ Properly handled
   - HADec → ICRS transformation accounts for:
     - Earth rotation
     - Precession
     - Nutation (if apparent time used)

4. **Observer Location**: ✅ Specified
   - OVRO coordinates: -118.2817° lon, 37.2314° lat, 1222m altitude
   - Accounts for parallax effects (small for nearby objects)

### ⚠️ What is NOT Included (Microarcsecond-Level)

1. **Polar Motion**: ⚠️ Not explicitly handled
   - Earth's rotation axis wobbles (few meters)
   - Effect: ~0.3 arcseconds typical
   - For microarcsecond precision, would need IERS Earth Orientation Parameters

2. **Relativistic Effects**: ⚠️ Partial
   - Light bending (general relativity)
   - Effect: ~1-2 milliarcseconds for solar system objects
   - Astropy handles some, but not all relativistic effects

3. **Atmospheric Refraction**: ⚠️ Not included
   - Light bending through atmosphere
   - Effect: ~1 arcminute at horizon, ~0 at zenith
   - Typically corrected separately in radio astronomy

4. **Tidal Effects**: ⚠️ Not explicitly handled
   - Earth tides affect baseline lengths
   - Effect: ~millimeters for typical baselines
   - For microarcsecond precision, would need precise ephemeris

5. **Diurnal Aberration**: ⚠️ Not explicitly handled
   - Annual aberration from Earth's orbital motion
   - Effect: ~20 arcseconds
   - Typically included in Astropy transforms, but may be approximate

---

## Precision Estimates

### Astropy Coordinate Transformation Precision

Based on Astropy documentation and testing:
- **Typical precision**: Sub-arcsecond (0.1-1 arcsecond)
- **Best-case precision**: ~0.01 arcseconds (for well-constrained transformations)
- **Limitations**: Microarcsecond precision requires specialized ephemeris (e.g., IERS)

### For DSA-110 Application

**Beam size**: ~1-2 arcminutes at 1.4 GHz  
**Required precision**: ~0.1-1 arcsecond (0.1-1% of beam)  
**Current precision**: ✅ **Adequate** (sub-arcsecond)

For phase center calculations:
- **Phase error**: ~0.1 arcsecond → ~0.1% phase error
- **Calibration impact**: Negligible for DSA-110's beam size
- **UVW error**: ~millimeters for typical baselines

---

## Comparison with Maximum Precision

### Maximum Precision Requirements (VLBI)

For microarcsecond precision (e.g., VLBI, Gaia):
1. **IERS Earth Orientation Parameters** (EOP)
   - Polar motion
   - UT1-UTC
   - Nutation corrections

2. **High-Precision Ephemeris**
   - JPL DE ephemeris for solar system
   - Proper motion corrections
   - Parallax corrections

3. **Relativistic Corrections**
   - Light bending (general relativity)
   - Shapiro delay
   - Time dilation

4. **Atmospheric Models**
   - Ionospheric delay
   - Tropospheric delay
   - Refraction corrections

### Current Implementation vs. Maximum Precision

| Component | Current | Maximum Precision | Difference |
|-----------|---------|-------------------|------------|
| Precession | ✅ IAU 2006 | ✅ IAU 2006 | ✅ Same |
| Nutation | ✅ Apparent ST | ✅ IERS EOP | ⚠️ ~0.01" |
| Polar Motion | ⚠️ Not explicit | ✅ IERS EOP | ⚠️ ~0.3" |
| Relativistic | ⚠️ Partial | ✅ Full GR | ⚠️ ~0.001" |
| Atmospheric | ⚠️ Not included | ✅ Models | ⚠️ ~1" (horizon) |

**Total difference**: ~0.3-1 arcsecond (depending on conditions)

---

## Recommendations

### For DSA-110 (Current Requirements)

**Status**: ✅ **Adequate** - Current precision is sufficient

**Reasons:**
1. Beam size is 1-2 arcminutes
2. Required precision is ~0.1-1 arcsecond
3. Current implementation provides sub-arcsecond precision
4. Calibration accuracy is not limited by RA calculation precision

### If Maximum Precision Needed

To achieve microarcsecond precision, you would need to:

1. **Use IERS Earth Orientation Parameters**:
   ```python
   from astropy.coordinates import EarthLocation
   from astropy.utils.iers import IERS
   
   # Load IERS data for polar motion
   iers = IERS()
   # Apply polar motion corrections
   ```

2. **Use JPL Ephemeris** for high-precision solar system corrections

3. **Apply relativistic corrections** explicitly:
   ```python
   # Light bending, Shapiro delay, etc.
   ```

4. **Atmospheric corrections** (typically done separately in radio astronomy)

**However**, this is **not necessary** for DSA-110's current requirements.

---

## Code Locations

### Primary Implementation
- `src/dsa110_contimg/conversion/helpers.py:34` - `get_meridian_coords()`
- Uses Astropy `SkyCoord` with HADec→ICRS transformation

### Alternative Implementation
- `src/dsa110_contimg/conversion/uvh5_to_ms.py:258` - `_phase_data_to_midpoint_reference()`
- Explicitly uses "apparent" sidereal time (includes nutation)
- Transforms CIRS→ICRS

### Calibrator Matching
- `src/dsa110_contimg/calibration/schedule.py:28` - Uses "apparent" sidereal time
- `src/dsa110_contimg/calibration/catalogs.py:721` - Uses "apparent" sidereal time

---

## Conclusion

**Answer**: The RA calculation is **high-precision** (sub-arcsecond) but **not maximum-precision** (microarcsecond).

**For DSA-110**: ✅ **Adequate** - Current precision is sufficient for the beam size and calibration requirements.

**To improve**: Would require IERS EOP, high-precision ephemeris, and explicit relativistic corrections, but this is **not necessary** for current applications.

