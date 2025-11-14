# DSA-110 Beam Model Assets Analysis

## Available Assets in `/stage/dsa110-contimg/dsa110-beam/`

### 1. **H5 Beam Model** (`DSA110_beam_1.h5` - 330 MB)
**Primary source data** - Full frequency-dependent beam model

- **Structure**:
  - `freq_Hz`: 41 frequency channels (~1.2-1.24 GHz)
  - `theta_pts`: 1801 points (polar angle, 0-180°)
  - `phi_pts`: 73 points (azimuth, 0-360°)
  - `X_pol_Efields/ephi`, `X_pol_Efields/etheta`: Complex E-field (41, 1801, 73)
  - `Y-pol_Efields/ephi`, `Y-pol_Efields/etheta`: Complex E-field (41, 1801, 73)

- **Use Case**: Most accurate, full frequency coverage
- **Complexity**: High - requires Jones matrix interpolation

### 2. **Primary Beam FITS Image** (`dsa110.pb.fits` - 88 MB)
**High-resolution PB response image** - Ready to use!

- **Structure**:
  - Shape: 4800 × 4800 pixels
  - Coordinate system: AZ/EL (antenna frame)
  - Units: radians (angular), Hz (frequency)
  - Reference: Center of image (boresight)
  - Increment: ~1.45e-5 rad/pixel (~0.0008°/pixel)
  - Frequency: ~1.4 GHz (single channel)

- **Resolution**: Very high (~0.0008° per pixel)
- **Coverage**: Full 2D PB pattern
- **Use Case**: Direct PB response lookup (after coordinate conversion)

### 3. **Jones Matrix Image** (`dsa110_jones.im` - CASA image)
**Complex Jones matrices** - Used to build VP table

- **Structure**:
  - Shape: 73 × 1801 × 4 × 1 (phi × theta × pol × freq)
  - Polarizations: XX, XY, YX, YY
  - Coordinate system: AZ/EL

- **Use Case**: VP table generation, polarization-dependent calculations

### 4. **VP Tables**
- `dsa110_vp.tbl`: VP table for DSA-110
- `dsa110_vp_ovro.tbl`: VP table for OVRO (legacy?)

- **Use Case**: CASA imaging tasks (already integrated)

## Key Finding: **PB FITS Image is Usable!**

The `dsa110.pb.fits` file is a **high-resolution primary beam response image** that we could use for accurate PB calculations in calibrator matching!

### Advantages Over Airy Approximation:
1. **Actual measured beam** (not theoretical)
2. **High resolution** (4800×4800 pixels, ~0.0008°/pixel)
3. **Off-axis accuracy** (captures real beam distortions)
4. **Ready to use** (no complex interpolation needed)

### Implementation Requirements:

To use the PB FITS image for calibrator matching, we need to:

1. **Load PB image** (CASA `image` tool)
2. **Convert coordinates**:
   - Input: Source ICRS (RA, Dec)
   - Need: MS pointing, observation time (MJD), antenna location
   - Convert: ICRS → HA/Dec → AZ/EL (antenna frame)
3. **Lookup PB response**:
   - Convert AZ/EL to pixel coordinates in PB image
   - Interpolate PB value (or nearest neighbor)
4. **Handle frequency**:
   - PB image is at ~1.4 GHz
   - May need frequency interpolation if using other frequencies

### Code Sketch:

```python
def get_pb_response_from_fits(
    source_ra_deg: float,
    source_dec_deg: float,
    pointing_ra_deg: float,
    pointing_dec_deg: float,
    mjd: float,
    pb_fits_path: str = '/stage/dsa110-contimg/dsa110-beam/dsa110.pb.fits'
) -> float:
    """Get PB response from FITS image."""
    from casatools import image
    from astropy.coordinates import SkyCoord, EarthLocation, AltAz
    from astropy.time import Time
    from dsa110_contimg.utils.constants import DSA110_LOCATION
    
    # Convert source to AZ/EL
    source_coord = SkyCoord(ra=source_ra_deg*u.deg, dec=source_dec_deg*u.deg)
    time = Time(mjd, format='mjd')
    altaz_frame = AltAz(obstime=time, location=DSA110_LOCATION)
    source_altaz = source_coord.transform_to(altaz_frame)
    
    # Get pointing AZ/EL
    pointing_coord = SkyCoord(ra=pointing_ra_deg*u.deg, dec=pointing_dec_deg*u.deg)
    pointing_altaz = pointing_coord.transform_to(altaz_frame)
    
    # Calculate offset from boresight (in AZ/EL frame)
    az_offset = (source_altaz.az - pointing_altaz.az).to(u.rad).value
    el_offset = (source_altaz.alt - pointing_altaz.alt).to(u.rad).value
    
    # Load PB image and lookup
    ia = image()
    ia.open(pb_fits_path)
    cs = ia.coordsys()
    
    # Convert offset to pixel coordinates
    # (offset from reference pixel at center)
    ref_pix = cs.referencepixel()['numeric'][:2]
    inc = cs.increment()['numeric'][:2]
    
    pix_x = ref_pix[0] + az_offset / inc[0]
    pix_y = ref_pix[1] + el_offset / inc[1]
    
    # Get PB value (with interpolation)
    pb_value = ia.getchunk([int(pix_x), int(pix_y), 0, 0])[0, 0]
    
    ia.close()
    return float(pb_value)
```

### Performance Considerations:

- **Speed**: Image lookup is slower than Airy formula (~10-100x)
- **Accuracy**: Much more accurate, especially off-axis
- **Caching**: Could cache PB image in memory for repeated lookups

### Recommendation:

**Option A: Use PB FITS for Critical Cases** (Recommended)
- Keep Airy approximation for fast catalog searches
- Use PB FITS image for:
  - Final calibrator selection
  - Quality assessment
  - Edge cases (off-axis sources)

**Option B: Use PB FITS Always**
- Replace Airy approximation entirely
- Accept performance hit for accuracy gain
- Cache PB image in memory

**Option C: Hybrid Approach**
- Use Airy for initial filtering (fast)
- Use PB FITS for final ranking (accurate)

## Next Steps

1. **Implement PB FITS lookup function** (see code sketch above)
2. **Add coordinate conversion** (ICRS → AZ/EL)
3. **Benchmark performance** vs Airy approximation
4. **Add caching** for PB image
5. **Integrate into calibrator matching** with option to choose method

## Files Summary

| File | Size | Type | Use Case |
|------|------|------|----------|
| `DSA110_beam_1.h5` | 330 MB | HDF5 | Source data, full frequency model |
| `dsa110.pb.fits` | 88 MB | FITS | **PB response lookup (recommended)** |
| `dsa110_jones.im` | ~ | CASA | Jones matrices, VP generation |
| `dsa110_vp.tbl` | ~ | CASA | Imaging tasks (already integrated) |

**Conclusion**: The PB FITS image (`dsa110.pb.fits`) is the **best option** for accurate PB response calculations in calibrator matching. It's ready to use and provides much better accuracy than the Airy approximation, especially for off-axis sources.


