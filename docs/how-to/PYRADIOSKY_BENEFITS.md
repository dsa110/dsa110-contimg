# pyradiosky Benefits Summary

## Why pyradiosky?

The pipeline now uses **pyradiosky** as the default for sky model construction. Here's why this matters:

## Key Benefits

### 1. 🎯 Better Sky Model Management

**Before:** Manual component list construction
- Error-prone coordinate formatting
- No validation
- Limited manipulation capabilities

**Now:** Structured pyradiosky SkyModel
- Type-safe sky model objects
- Built-in validation
- Rich manipulation API

**Example:**
```python
# Before: Manual, error-prone
cl.addcomponent(dir="J2000 11h00m00s +55d00m00s", flux=2.3, ...)

# Now: Structured, validated
sky = SkyModel(name=['source'], skycoord=SkyCoord(...), stokes=..., ...)
```

### 2. 📚 Multiple Catalog Formats

**Supported Formats:**
- ✅ VOTable (standard astronomical format)
- ✅ SkyH5 (HDF5-based, efficient)
- ✅ Text files (custom formats)
- ✅ GLEAM catalog (built-in support)
- ✅ NVSS catalog (via our integration)

**Example:**
```python
# Read from any supported format
sky = SkyModel.from_votable_catalog('nvss.vot')
sky = SkyModel.from_skyh5('model.skyh5')
sky = SkyModel.from_text_catalog('sources.txt')
```

### 3. 🔬 Advanced Spectral Modeling

**Capabilities:**
- Flat spectrum models
- Spectral index models
- Full frequency-dependent models
- Custom spectral functions

**Example:**
```python
# Flat spectrum
sky = SkyModel(..., spectral_type='flat')

# Spectral index
sky = SkyModel(..., spectral_type='spectral_index', spectral_index=-0.7)

# Full spectrum
sky = SkyModel(..., spectral_type='full', freq_array=freqs)
```

### 4. 🌐 Coordinate Transformations

**Built-in Support:**
- ICRS (default)
- Galactic coordinates
- Alt-Az (for observation planning)
- Custom coordinate systems

**Example:**
```python
# Transform to Galactic
sky.to_galactic()

# Transform to Alt-Az for specific time/location
sky.to_altaz(time, location)
```

### 5. 🖼️ Sky Model Imaging

**Visualization:**
- Generate FITS images with WCS headers
- Create PNG visualizations
- Beam convolution support
- Customizable image parameters

**Example:**
```python
from dsa110_contimg.calibration.skymodel_image import write_skymodel_images

write_skymodel_images(sky, 'output', 
                      image_size=(1024, 1024),
                      pixel_scale_arcsec=5.0,
                      beam_fwhm_arcsec=45.0)
```

### 6. 🔄 Seamless Integration

**Backward Compatible:**
- Same API as before
- No code changes required
- Automatic pyradiosky usage

**Example:**
```python
# Your existing code works as-is
from dsa110_contimg.calibration.skymodels import make_point_cl

cl = make_point_cl('source', ra_deg, dec_deg, flux_jy=2.3, 
                   freq_ghz=1.4, out_path='source.cl')
# ↑ Now uses pyradiosky internally, but API is unchanged
```

### 7. 🛠️ Rich Manipulation API

**Operations:**
- Filter by flux, position, etc.
- Combine multiple sky models
- Select subsets of sources
- Transform coordinates
- Modify spectral properties

**Example:**
```python
# Filter by flux
sky.select(component_inds=sky.stokes[0, 0, :] > 0.01 * u.Jy)

# Combine sky models
combined = sky1 + sky2

# Select subset
subset = sky.select(component_inds=[0, 2, 5])
```

### 8. ✅ Well-Tested & Maintained

**Quality:**
- Active development
- Comprehensive test suite
- Used by multiple projects
- Regular updates

## Comparison: Before vs After

| Feature | Before (Manual) | After (pyradiosky) |
|---------|----------------|-------------------|
| **Sky Model Creation** | Manual component lists | Structured SkyModel objects |
| **Catalog Support** | NVSS only | Multiple formats (VOTable, SkyH5, etc.) |
| **Spectral Modeling** | Flat spectrum only | Flat, spectral index, full spectrum |
| **Coordinate Systems** | ICRS only | ICRS, Galactic, Alt-Az, custom |
| **Validation** | None | Built-in validation |
| **Manipulation** | Limited | Rich API |
| **Imaging** | Not available | FITS/PNG generation |
| **Error Handling** | Manual | Automatic validation |

## Real-World Impact

### For Developers
- ✅ Less code to maintain
- ✅ Fewer bugs (validation, type safety)
- ✅ Easier to extend (rich API)
- ✅ Better testing (structured objects)

### For Users
- ✅ More reliable sky models
- ✅ Support for more catalog formats
- ✅ Better visualization tools
- ✅ No code changes required

### For the Pipeline
- ✅ More robust sky model handling
- ✅ Better error messages
- ✅ Easier debugging
- ✅ Foundation for future improvements

## Migration Impact

**Zero Breaking Changes:**
- All existing code works as-is
- Same function signatures
- Same behavior
- Better internal implementation

**New Capabilities:**
- Direct pyradiosky access for advanced users
- Sky model imaging
- Better manipulation tools
- More catalog formats

## Summary

pyradiosky provides:
1. ✅ **Better tooling** - Structured, validated sky models
2. ✅ **More formats** - VOTable, SkyH5, text, etc.
3. ✅ **Advanced features** - Spectral modeling, coordinate transforms
4. ✅ **Visualization** - FITS/PNG image generation
5. ✅ **No disruption** - Backward compatible, no code changes needed

**Bottom line:** Better sky model management with zero migration effort.

## Learn More

- [pyradiosky User Guide](./PYRADIOSKY_GUIDE.md) - Comprehensive guide with examples
- [Technical Analysis](../analysis/pyradiosky_vs_componentlist.md) - Detailed comparison
- [Final Recommendation](../analysis/FINAL_RECOMMENDATION.md) - Decision rationale
- [Changelog](../changelog/PYRADIOSKY_DEFAULT_UPDATE.md) - Implementation details

