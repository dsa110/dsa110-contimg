# MS Phasing During Conversion

**Date:** 2025-11-05  
**Context:** Understanding what phase center is used when generating MS from UVH5

---

## Summary

When generating a Measurement Set from UVH5 data, the visibilities are **phased to the meridian at the midpoint of the observation**.

Specifically:
- **Right Ascension (RA)**: Local Sidereal Time (LST) at the midpoint of the observation, converted to ICRS (J2000)
- **Declination (Dec)**: The pointing declination (`phase_center_dec`) from the UVH5 metadata, converted to ICRS (J2000)
- **Hour Angle**: 0 (meridian = transit)

---

## Code Implementation

### Function: `phase_to_meridian()` 
**File:** `src/dsa110_contimg/conversion/helpers.py`  
**Lines:** 205-253

This function:
1. Gets the pointing declination from UVH5 metadata (`phase_center_dec`)
2. Computes the midpoint time of the observation
3. Calls `get_meridian_coords()` to get RA/Dec at meridian
4. Sets the phase center to these coordinates
5. Recomputes UVW coordinates

### Function: `get_meridian_coords()`
**File:** `src/dsa110_contimg/conversion/helpers.py`  
**Lines:** 34-50

```python
def get_meridian_coords(pt_dec: u.Quantity, time_mjd: float) -> Tuple[u.Quantity, u.Quantity]:
    """Compute the right ascension/declination of the meridian at OVRO."""
    # Creates a coordinate with:
    # - Hour Angle = 0 (meridian = transit)
    # - Declination = pt_dec (pointing declination)
    # - Transforms to ICRS (J2000) frame
```

**What it does:**
1. Creates a `SkyCoord` with `ha=0` (meridian/transit) and `dec=pt_dec`
2. Transforms from HADec frame to ICRS (J2000) frame
3. Returns RA and Dec in ICRS coordinates

---

## Phase Center Details

### Meridian Definition
- **Meridian**: The great circle passing through the celestial poles and the zenith
- **Hour Angle = 0**: Object is at meridian transit (highest in the sky)
- **RA = LST**: When HA=0, RA equals Local Sidereal Time

### Coordinate Frame
- **Input**: HADec (Hour Angle / Declination) frame at observation time
- **Output**: ICRS (J2000) frame for consistency with standard astronomical coordinates
- **Frame transformation**: Accounts for precession, nutation, and proper motion

### Time Reference
- **Reference time**: Midpoint of the observation (`mean(time_array)`)
- **Purpose**: Provides a stable phase center that doesn't drift during the observation

---

## Example

For an observation at OVRO (Longitude = -118.2817°):
- **Observation midpoint**: 2025-10-29 13:54:17 UTC
- **LST at midpoint**: ~20:30:00 (example)
- **Pointing declination**: 55.5° (from UVH5 metadata)
- **Phase center**: RA ≈ 20h30m (LST → ICRS), Dec = 55.5° (ICRS)

---

## Why Phase to Meridian?

1. **Stable reference**: Meridian provides a fixed celestial coordinate frame
2. **Standard practice**: Common in interferometry for initial phasing
3. **Facilitates rephasing**: Easy to rephase to specific sources later (e.g., calibrators)
4. **UVW consistency**: UVW coordinates are computed correctly for meridian phasing

---

## Relationship to Calibration

During calibration, the MS is typically **rephased** to the calibrator position:

1. **Initial MS**: Phased to meridian (RA=LST(midpoint), Dec=pointing_dec)
2. **During calibration**: Rephased to calibrator (RA=cal_ra, Dec=cal_dec) using `phaseshift`
3. **Purpose**: Ensures MODEL_DATA matches DATA column phase structure

**See:** `src/dsa110_contimg/calibration/cli.py` lines 1199-1369 for rephasing logic.

---

## Code Locations

### Main Conversion Flow
- `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py:342` - Calls `phase_to_meridian()`
- `src/dsa110_contimg/conversion/uvh5_to_ms.py:987` - Calls `phase_to_meridian()`
- `src/dsa110_contimg/conversion/strategies/direct_subband.py:495` - Uses `get_meridian_coords()` for per-subband phasing

### Helper Functions
- `src/dsa110_contimg/conversion/helpers.py:34` - `get_meridian_coords()`
- `src/dsa110_contimg/conversion/helpers.py:205` - `phase_to_meridian()`
- `src/dsa110_contimg/conversion/helpers.py:315` - `compute_and_set_uvw()` (recomputes UVW after phasing)

---

## Key Points

1. ✅ **MS is phased to meridian** (not to a specific source)
2. ✅ **RA = LST(midpoint)** at the observation location
3. ✅ **Dec = pointing declination** from UVH5 metadata
4. ✅ **Frame = ICRS (J2000)** for standard astronomical coordinates
5. ✅ **UVW coordinates are recomputed** to match the meridian phase center

---

## Verification

To check the phase center of a generated MS:

```python
from casacore.tables import table
import numpy as np

ms_path = "/data/ms/2025-10-29T13:54:17.ms"

with table(f"{ms_path}::FIELD", readonly=True, ack=False) as field_tb:
    # Check PHASE_DIR (actual phase center used for DATA column)
    if "PHASE_DIR" in field_tb.colnames():
        phase_dir = field_tb.getcol("PHASE_DIR")[0][0]  # Shape: (2,)
        ra_rad = phase_dir[0]
        dec_rad = phase_dir[1]
        ra_deg = np.rad2deg(ra_rad)
        dec_deg = np.rad2deg(dec_rad)
        print(f"Phase center: RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°")
    
    # Check REFERENCE_DIR (used for imaging/primary beam)
    if "REFERENCE_DIR" in field_tb.colnames():
        ref_dir = field_tb.getcol("REFERENCE_DIR")[0][0]
        ref_ra_deg = np.rad2deg(ref_dir[0])
        ref_dec_deg = np.rad2deg(ref_dir[1])
        print(f"Reference center: RA={ref_ra_deg:.6f}°, Dec={ref_dec_deg:.6f}°")
```

This should show coordinates at the meridian (RA ≈ LST at midpoint, Dec = pointing declination).

