# Analysis: pyradiosky SkyModel vs Manual Component List Construction

## Executive Summary

**Recommendation: Adopt pyradiosky for sky model construction, but use DP3 (not CASA `ft()`) for visibility prediction.**

**Key Finding**: CASA's `ft()` is slow for populating MODEL_DATA. The codebase already has **DP3 integration** which is faster than CASA for visibility operations.

**Recommended Approach**:
1. **Use pyradiosky** for sky model construction and management (more complete, well-developed)
2. **Convert pyradiosky SkyModel → DP3 format** (or write directly to MODEL_DATA)
3. **Use DP3 predict** (already integrated, faster than `ft()`) to populate MODEL_DATA

**Benefits**:
- Faster MODEL_DATA population (DP3 vs CASA `ft()`)
- Better sky model management (pyradiosky's structured approach)
- More complete tooling (pyradiosky's format support, coordinate transforms)
- Avoids CASA `ft()` phase center bugs and WSClean compatibility issues

## Current Implementation

### Manual Component List Approach

The current implementation (`src/dsa110_contimg/calibration/skymodels.py`) uses CASA's `componentlist` tool directly:

```python
from casatools import componentlist as casa_cl

cl = casa_cl()
cl.addcomponent(
    dir=f"J2000 {ra_deg}deg {dec_deg}deg",
    flux=float(flux_jy),
    fluxunit="Jy",
    freq=freq_str,
    shape="point",
)
cl.rename(out_path)
```

**Key Functions:**
- `make_point_cl()`: Single point source component list
- `make_multi_point_cl()`: Multiple point sources
- `make_nvss_component_cl()`: NVSS catalog integration
- `ft_from_cl()`: Apply component list to MODEL_DATA via CASA `ft()`

### Current Workflow

1. **Catalog Selection**: Read NVSS catalog, filter by flux/radius
2. **Component List Creation**: Use CASA `componentlist` to create `.cl` file
3. **Model Application**: Use CASA `ft()` to populate MODEL_DATA column
4. **Calibration**: Use MODEL_DATA for bandpass/gain calibration

## pyradiosky SkyModel Capabilities

### What pyradiosky Offers

Based on the [pyradiosky documentation](https://pyradiosky.readthedocs.io/en/latest/skymodel.html):

1. **Structured Data Model**:
   - `SkyModel` class with well-defined attributes
   - Support for point sources and HEALPix diffuse maps
   - Multiple spectral types (full, flat, subband, spectral_index)
   - Stokes parameter handling (I, Q, U, V)

2. **File Format Support**:
   - Read: skyh5, GLEAM, VOTable, text catalogs, FHD
   - Write: skyh5 (HDF5), text catalogs
   - **Note**: No direct CASA componentlist (.cl) export capability

3. **Advanced Features**:
   - Coordinate transformations (J2000 ↔ Az/El)
   - Frequency interpolation (`at_frequencies()`)
   - Component selection and concatenation
   - Frame coherency calculations

4. **Integration**:
   - Works with `pyuvdata` for visibility data
   - Standardized format for radio astronomy workflows

## Critical Gap: CASA Componentlist Export

**Key Finding**: pyradiosky does **not** provide a direct method to export to CASA componentlist (`.cl`) format.

The library supports:
- `write_skyh5()`: HDF5 format
- `write_text_catalog()`: Text format (limited functionality)

But **not**:
- CASA componentlist export
- Direct integration with CASA `ft()`

### Implications

To use pyradiosky, we would need to:
1. Create `SkyModel` objects from catalogs
2. Manually convert `SkyModel` → CASA componentlist (write custom conversion code)
3. Still use CASA `ft()` to apply to MODEL_DATA

This adds an extra conversion step without eliminating the need for CASA componentlists.

## Comparison Matrix

| Feature | Manual Component List | pyradiosky SkyModel |
|---------|----------------------|---------------------|
| **CASA Integration** | ✓ Direct (native) | ✗ Requires conversion |
| **Dependencies** | CASA only | CASA + pyradiosky + dependencies |
| **Code Complexity** | Simple, direct | More complex (extra layer) |
| **Format Flexibility** | Limited (CASA only) | ✓ Multiple formats |
| **Catalog Reading** | Custom (NVSS) | ✓ Built-in (GLEAM, VOTable, etc.) |
| **Coordinate Transforms** | Manual | ✓ Built-in methods |
| **Spectral Modeling** | Basic (single freq) | ✓ Advanced (full, subband, index) |
| **Validation** | Manual checks | ✓ Built-in `check()` method |
| **Documentation** | Project-specific | ✓ Well-documented library |
| **Community Support** | Internal | ✓ Active community |

## Current Issues with Manual Approach

### Known Limitations

1. **Phase Center Bugs** (documented in code comments):
   - `ft()` doesn't use PHASE_DIR correctly after rephasing
   - Workaround: Manual MODEL_DATA calculation for single sources
   - Multi-component models still require `ft()` (no manual alternative)

2. **WSClean Compatibility**:
   - `ft()` crashes if MODEL_DATA already contains data from a previous WSClean run
   - **Why this happens**: WSClean can populate MODEL_DATA during imaging (especially in self-calibration workflows)
   - **Scenario**: MS was previously processed by WSClean → MODEL_DATA already populated → trying to re-seed with `ft()` → crash
   - **Workaround**: Clear MODEL_DATA before calling `ft()` (code already does this)

3. **Limited Format Support**:
   - Only CASA componentlist format
   - No direct support for other catalog formats

### Potential Solution: Direct Visibility Prediction

**Important clarification**: pyradiosky itself is **not incompatible with WSClean**. The issue is with CASA's `ft()` function, which crashes when trying to overwrite MODEL_DATA that was previously populated by WSClean (e.g., from a previous imaging run or self-calibration step).

**Potential advantage of pyradiosky**: If pyradiosky can work with `pyuvdata` or other tools to predict visibilities directly into MODEL_DATA, this could bypass CASA `ft()` entirely, solving the WSClean compatibility issue.

**Current limitation**: pyradiosky does not directly export to CASA componentlist format, so if we need to use CASA `ft()`, we would:
- Still need to use CASA `ft()` (same phase center bugs)
- Still need to clear MODEL_DATA before `ft()` (same WSClean issue)
- Add complexity of converting SkyModel → componentlist

**Alternative - DP3 (Already Integrated)**: The codebase already has DP3 integration (`src/dsa110_contimg/calibration/dp3_wrapper.py`) which can predict visibilities directly, bypassing CASA `ft()`. **DP3 is faster than CASA for visibility operations** (noted in code comments).

**Key Insight**: The speed issue is with CASA `ft()`, not with component lists themselves. The solution is to:
1. Use pyradiosky for better sky model management (more complete tooling)
2. Convert pyradiosky SkyModel → DP3 format (simple text format conversion)
3. Use DP3 predict instead of CASA `ft()` (already integrated, faster)

This combination gives both speed improvement and better tooling.

## Use Cases Where pyradiosky Would Help

### Scenario 1: Multi-Format Catalog Support

If we need to support multiple catalog formats (GLEAM, VOTable, etc.):

```python
# With pyradiosky
sky = SkyModel.from_gleam_catalog('gleam.vot')
sky = SkyModel.from_votable_catalog('nvss.vot')
# Then convert to componentlist...

# Current approach
# Custom read functions for each format
```

**Benefit**: Standardized catalog reading across formats

### Scenario 2: Advanced Spectral Modeling

If we need complex spectral models (subband, spectral index):

```python
# With pyradiosky
sky = SkyModel.from_file('catalog.skyh5')  # Full spectral info
sky.at_frequencies(freq_array)  # Interpolate to observation frequencies

# Current approach
# Manual spectral index calculations
```

**Benefit**: Built-in spectral modeling capabilities

### Scenario 3: Coordinate Transformations

If we need frequent coordinate transformations:

```python
# With pyradiosky
sky.transform_to('altaz', telescope_location=..., time=...)
alt_az = sky.alt_az

# Current approach
# Manual astropy coordinate transformations
```

**Benefit**: Convenient coordinate transformation methods

## Recommendations

### Recommended Approach: pyradiosky + DP3

**Primary recommendation**: Use pyradiosky for sky model construction, then use DP3 (not CASA `ft()`) for visibility prediction.

**Why this is better**:
1. **Speed**: DP3 is faster than CASA `ft()` (already noted in codebase)
2. **Better tooling**: pyradiosky is more complete and well-developed
3. **Avoids CASA bugs**: Bypasses `ft()` phase center issues and WSClean compatibility problems
4. **Format flexibility**: pyradiosky supports multiple catalog formats

**Implementation path**:
1. Use pyradiosky to construct SkyModel from catalogs (NVSS, GLEAM, VOTable, etc.)
2. Convert SkyModel → DP3 format (or write directly to MODEL_DATA via pyuvdata)
3. Use existing `predict_from_skymodel_dp3()` function (already integrated)

**Code sketch**:
```python
from pyradiosky import SkyModel
from dsa110_contimg.calibration.dp3_wrapper import predict_from_skymodel_dp3

# Read catalog with pyradiosky
sky = SkyModel.from_votable_catalog('nvss.vot')
# Or: sky = SkyModel.from_gleam_catalog('gleam.vot')

# Convert to DP3 format (or write directly to MODEL_DATA)
dp3_skymodel_path = convert_skymodel_to_dp3(sky, out_path='model.skymodel')

# Use DP3 predict (faster than ft())
predict_from_skymodel_dp3(ms_path, dp3_skymodel_path)
```

**Conversion function needed** (similar to existing `convert_nvss_to_dp3_skymodel()`):
```python
def convert_skymodel_to_dp3(
    sky: SkyModel,
    *,
    out_path: str,
    spectral_index: float = -0.7,
) -> str:
    """Convert pyradiosky SkyModel to DP3 sky model format.
    
    DP3 format: Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, 
                ReferenceFrequency, MajorAxis, MinorAxis, Orientation
    Example: s0c0,POINT,07:02:53.6790,+44:31:11.940,2.4,[-0.7],false,1400000000.0,,,
    """
    from astropy.coordinates import Angle
    
    with open(out_path, 'w') as f:
        for i in range(sky.Ncomponents):
            # Get component data
            ra = sky.skycoord[i].ra
            dec = sky.skycoord[i].dec
            flux_jy = sky.stokes[0, 0, i]  # I stokes, first frequency
            
            # Format RA/Dec
            ra_str = Angle(ra).to_string(unit='hour', precision=3)
            dec_str = Angle(dec).to_string(unit='deg', precision=3, alwayssign=True)
            
            # Get reference frequency
            if sky.spectral_type == 'spectral_index':
                ref_freq_hz = sky.reference_frequency[i].to('Hz').value
                spec_idx = sky.spectral_index[i]
            else:
                # Use first frequency as reference
                ref_freq_hz = sky.freq_array[0].to('Hz').value if sky.freq_array is not None else 1.4e9
                spec_idx = spectral_index
            
            # Write DP3 format line
            name = sky.name[i] if sky.name is not None else f"s{i}c{i}"
            f.write(f"{name},POINT,{ra_str},{dec_str},{flux_jy:.6f},[{spec_idx:.2f}],false,{ref_freq_hz:.1f},,,\n")
    
    return out_path
```

### Alternative: pyradiosky + pyuvdata (Direct MODEL_DATA Write)

If pyradiosky can work with pyuvdata to predict visibilities directly:
1. Use pyradiosky for sky model construction
2. Use pyuvdata to predict visibilities directly into MODEL_DATA
3. Bypass both CASA `ft()` and DP3

**Note**: This requires investigation - need to verify pyradiosky + pyuvdata integration for direct MODEL_DATA writing.

### Short Term (If Migration is Not Immediate)

**Continue using manual component list construction** but:
1. **Switch to DP3 predict** instead of CASA `ft()` (already available, faster)
2. Use existing `convert_nvss_to_dp3_skymodel()` function
3. Use `predict_from_skymodel_dp3()` instead of `ft_from_cl()`

This gives immediate speed improvement without requiring pyradiosky migration.

**Implementation sketch:**
```python
def make_component_cl_from_skymodel(sky: SkyModel, out_path: str) -> str:
    """Convert pyradiosky SkyModel to CASA componentlist."""
    from casatools import componentlist as casa_cl
    
    cl = casa_cl()
    try:
        for i in range(sky.Ncomponents):
            # Extract component data from SkyModel
            ra = sky.skycoord[i].ra.deg
            dec = sky.skycoord[i].dec.deg
            flux = sky.stokes[0, 0, i]  # I stokes, first freq
            
            cl.addcomponent(
                dir=f"J2000 {ra}deg {dec}deg",
                flux=float(flux),
                fluxunit="Jy",
                freq=f"{sky.reference_frequency.to('GHz').value}GHz",
                shape="point",
            )
        cl.rename(out_path)
    finally:
        cl.close()
        cl.done()
    
    return out_path
```

### Long Term (Full Integration)

**If pyradiosky adds CASA componentlist export**, or if we:
1. Need extensive multi-format catalog support
2. Require advanced spectral modeling
3. Want better integration with pyuvdata workflows

Then consider migrating to pyradiosky as the primary sky model representation.

## Dependencies and Installation

### Current Dependencies
- CASA (already required)
- astropy (for coordinate handling)
- numpy, pandas (for catalog processing)

### Additional for pyradiosky
- pyradiosky package
- h5py (for skyh5 format)
- Additional dependencies (see pyradiosky requirements)

**Installation check**: pyradiosky is **not currently installed** in the casa6 environment.

## Conclusion

**For speed and better tooling, adopt pyradiosky + DP3 approach**:

1. **Speed improvement**: DP3 is faster than CASA `ft()` (already integrated in codebase)
2. **Better sky model management**: pyradiosky provides structured, well-developed tooling
3. **Format flexibility**: Support for multiple catalog formats (GLEAM, VOTable, etc.)
4. **Avoids CASA bugs**: Bypasses `ft()` phase center issues and WSClean compatibility problems

**Implementation priority**:
1. **Immediate**: Switch from CASA `ft()` to DP3 predict (already available, faster)
2. **Short-term**: Add pyradiosky for sky model construction
3. **Short-term**: Implement `convert_skymodel_to_dp3()` function
4. **Long-term**: Investigate pyradiosky + pyuvdata for direct MODEL_DATA writing

**Key insight**: The bottleneck is CASA `ft()`, not component lists. The solution is to use DP3 (already integrated) for prediction, and pyradiosky for better sky model management.

## References

- [pyradiosky Documentation](https://pyradiosky.readthedocs.io/en/latest/skymodel.html)
- Current implementation: `src/dsa110_contimg/calibration/skymodels.py`
- CASA componentlist tool: `casatools.componentlist`

