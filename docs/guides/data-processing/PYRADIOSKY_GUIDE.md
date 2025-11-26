# pyradiosky Guide: Sky Model Management

## Overview

The pipeline now uses **pyradiosky** as the default for sky model construction.
This provides better sky model management, support for multiple catalog formats,
and advanced spectral modeling capabilities.

## What is pyradiosky?

`pyradiosky` is a Python package for creating and managing radio sky models. It
provides:

- **Structured sky model representation**: Point sources and diffuse emission
- **Multiple catalog formats**: VOTable, SkyH5, text files
- **Advanced spectral modeling**: Spectral indices, frequency-dependent models
- **Coordinate transformations**: ICRS, Galactic, etc.
- **Integration with pyuvdata**: For visibility prediction workflows

## Benefits

### 1. Better Sky Model Management

**Before (manual component lists):**

```python
# Manual construction, error-prone
from casatools import componentlist
cl = componentlist()
cl.addcomponent(dir="J2000 11h00m00s +55d00m00s", flux=2.3, ...)
```

**Now (pyradiosky):**

```python
# Structured, type-safe, well-tested
from pyradiosky import SkyModel
sky = SkyModel.from_votable_catalog('nvss.vot')
```

### 2. Multiple Catalog Formats

pyradiosky supports reading from:

- **VOTable**: Standard astronomical catalog format
- **SkyH5**: HDF5-based sky model format
- **Text files**: Custom formats
- **GLEAM**: GLEAM catalog integration
- **NVSS**: NVSS catalog (via our integration)

### 3. Advanced Spectral Modeling

```python
# Flat spectrum
sky = SkyModel(..., spectral_type='flat')

# Spectral index
sky = SkyModel(..., spectral_type='spectral_index', spectral_index=-0.7)

# Full spectrum
sky = SkyModel(..., spectral_type='full', freq_array=freqs)
```

### 4. Coordinate Transformations

```python
# Transform to different coordinate systems
sky.to_galactic()
sky.to_altaz(time, location)
```

### 5. Integration with Imaging

```python
# Generate FITS/PNG images from sky models
from dsa110_contimg.calibration.skymodel_image import write_skymodel_images

write_skymodel_images(sky, 'output', image_size=(1024, 1024),
                      pixel_scale_arcsec=5.0, beam_fwhm_arcsec=45.0)
```

## Usage

### Basic Usage (Automatic - No Changes Required)

The pipeline automatically uses pyradiosky internally. Your existing code works
as-is:

```python
from dsa110_contimg.calibration.skymodels import make_point_cl, make_nvss_component_cl

# Single point source (uses pyradiosky internally)
cl = make_point_cl('source', ra_deg, dec_deg, flux_jy=2.3,
                   freq_ghz=1.4, out_path='source.cl')

# NVSS sources (uses pyradiosky internally)
cl = make_nvss_component_cl(ra_deg, dec_deg, radius_deg=0.2,
                            min_mjy=10.0, freq_ghz=1.4, out_path='nvss.cl')
```

### Advanced Usage (Direct pyradiosky)

For advanced use cases, you can use pyradiosky directly:

```python
from pyradiosky import SkyModel
from dsa110_contimg.calibration.skymodels import convert_skymodel_to_componentlist, ft_from_cl

# Create sky model from catalog
sky = SkyModel.from_votable_catalog('nvss.vot')

# Or create manually
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np

skycoord = SkyCoord(ra=165.0*u.deg, dec=55.5*u.deg, frame='icrs')
stokes = np.zeros((4, 1, 1)) * u.Jy
stokes[0, 0, 0] = 2.3 * u.Jy

sky = SkyModel(
    name=['source'],
    skycoord=skycoord,
    stokes=stokes,
    spectral_type='flat',
    component_type='point',
)

# Convert to componentlist for CASA
cl_path = convert_skymodel_to_componentlist(sky, out_path='model.cl')

# Apply to MS
ft_from_cl(ms_path, cl_path)
```

### Creating NVSS Sky Models

```python
from dsa110_contimg.calibration.skymodels import make_nvss_skymodel

# Create pyradiosky SkyModel from NVSS
sky = make_nvss_skymodel(
    center_ra_deg=165.0,
    center_dec_deg=55.5,
    radius_deg=0.2,
    min_mjy=10.0,
    freq_ghz=1.4,
)

# Now you can manipulate the sky model
print(f"Found {sky.Ncomponents} sources")
print(f"Total flux: {sky.stokes[0, 0, :].sum().to('Jy').value:.3f} Jy")

# Convert to componentlist
cl_path = convert_skymodel_to_componentlist(sky, out_path='nvss.cl')
```

## Workflow

### Standard Pipeline Workflow

1. **Sky Model Creation**: Pipeline automatically uses pyradiosky
   - Single calibrator: `make_point_cl()` → pyradiosky → componentlist
   - NVSS sources: `make_nvss_component_cl()` → pyradiosky → componentlist

2. **Conversion**: pyradiosky SkyModel → CASA componentlist
   - Automatic via `convert_skymodel_to_componentlist()`
   - Handles spectral indices, coordinate formatting

3. **Application**: CASA `ft()` populates MODEL_DATA
   - Works with 2-pol MS files
   - Proven and reliable

### Custom Workflow

1. **Create/Read Sky Model**:

   ```python
   sky = SkyModel.from_votable_catalog('catalog.vot')
   # Or: sky = make_nvss_skymodel(...)
   ```

2. **Manipulate Sky Model** (optional):

   ```python
   # Filter by flux
   sky.select(component_inds=sky.stokes[0, 0, :] > 0.01 * u.Jy)

   # Transform coordinates
   sky.to_galactic()

   # Add spectral index
   sky.spectral_type = 'spectral_index'
   sky.spectral_index = -0.7
   ```

3. **Convert to Componentlist**:

   ```python
   cl_path = convert_skymodel_to_componentlist(sky, out_path='model.cl')
   ```

4. **Apply to MS**:
   ```python
   ft_from_cl(ms_path, cl_path)
   ```

## Key Functions

### Sky Model Creation

- `make_point_skymodel()`: Create pyradiosky SkyModel for single source
- `make_nvss_skymodel()`: Create pyradiosky SkyModel from NVSS catalog
- `make_point_cl()`: Create componentlist (uses pyradiosky internally)
- `make_nvss_component_cl()`: Create componentlist from NVSS (uses pyradiosky
  internally)

### Conversion

- `convert_skymodel_to_componentlist()`: Convert pyradiosky SkyModel → CASA
  componentlist

### Application

- `ft_from_cl()`: Apply componentlist to MS MODEL_DATA via CASA `ft()`

### Imaging

- `write_skymodel_images()`: Generate FITS/PNG images from sky models
- `write_skymodel_fits()`: Generate FITS image
- `write_skymodel_png()`: Generate PNG visualization

## Examples

### Example 1: Single Calibrator

```python
from dsa110_contimg.calibration.skymodels import make_point_cl, ft_from_cl

cl = make_point_cl(
    name='0834+555',
    ra_deg=129.5,
    dec_deg=55.3,
    flux_jy=2.3,
    freq_ghz=1.4,
    out_path='calibrator.cl'
)

ft_from_cl(ms_path, cl, field='0', usescratch=True)
```

### Example 2: NVSS Region

```python
from dsa110_contimg.calibration.skymodels import make_nvss_component_cl, ft_from_cl

cl = make_nvss_component_cl(
    center_ra_deg=165.0,
    center_dec_deg=55.5,
    radius_deg=0.2,
    min_mjy=10.0,
    freq_ghz=1.4,
    out_path='nvss.cl'
)

ft_from_cl(ms_path, cl, field='0', usescratch=True)
```

### Example 3: Custom Sky Model

```python
from pyradiosky import SkyModel
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np

# Create multiple sources
names = ['source1', 'source2', 'source3']
ras = [165.0, 165.1, 165.2] * u.deg
decs = [55.5, 55.6, 55.7] * u.deg
fluxes = [2.3, 1.5, 0.8] * u.Jy

skycoord = SkyCoord(ra=ras, dec=decs, frame='icrs')
stokes = np.zeros((4, 1, 3)) * u.Jy
stokes[0, 0, :] = fluxes

sky = SkyModel(
    name=names,
    skycoord=skycoord,
    stokes=stokes,
    spectral_type='flat',
    component_type='point',
)

# Convert and apply
from dsa110_contimg.calibration.skymodels import convert_skymodel_to_componentlist, ft_from_cl

cl_path = convert_skymodel_to_componentlist(sky, out_path='custom.cl')
ft_from_cl(ms_path, cl_path)
```

### Example 4: Generate Sky Model Image

```python
from dsa110_contimg.calibration.skymodels import make_nvss_skymodel
from dsa110_contimg.calibration.skymodel_image import write_skymodel_images

# Create sky model
sky = make_nvss_skymodel(
    center_ra_deg=165.0,
    center_dec_deg=55.5,
    radius_deg=0.2,
    min_mjy=10.0,
)

# Generate images
fits_path, png_path = write_skymodel_images(
    sky,
    'skymodel_output',
    image_size=(1024, 1024),
    pixel_scale_arcsec=5.0,
    center_ra_deg=165.0,
    center_dec_deg=55.5,
    beam_fwhm_arcsec=45.0,
)

print(f"FITS: {fits_path}")
print(f"PNG: {png_path}")
```

## Migration Notes

**No migration required!** The API remains the same. All existing code continues
to work:

- `make_point_cl()` - Same signature, uses pyradiosky internally
- `make_nvss_component_cl()` - Same signature, uses pyradiosky internally
- `ft_from_cl()` - Unchanged

The only change is that pyradiosky is now used internally, providing better sky
model management without requiring code changes.

## Dependencies

- `pyradiosky`: Required (installed in `casa6` environment)
- `astropy`: Required (already installed)
- `numpy`: Required (already installed)
- `casatools`: Required for componentlist conversion (already installed)

## Troubleshooting

### Import Error: pyradiosky not found

```bash
# Install pyradiosky in casa6 environment
/opt/miniforge/envs/casa6/bin/pip install pyradiosky
```

### Empty Sky Model

If `make_nvss_skymodel()` returns an empty sky model:

- Check that sources exist in the specified region
- Verify `min_mjy` threshold isn't too high
- Check `radius_deg` is large enough

### Componentlist Conversion Issues

If conversion fails:

- Verify sky model has valid coordinates
- Check that flux values are positive
- Ensure frequency is specified

## Further Reading

- [pyradiosky Documentation](https://pyradiosky.readthedocs.io/)
- [Analysis: pyradiosky vs Component List](../../archive/analysis/pyradiosky_vs_componentlist.md)
- [Final Recommendation](../../archive/analysis/FINAL_RECOMMENDATION.md)
- [Changelog: pyradiosky Default Update](../../changelog/PYRADIOSKY_DEFAULT_UPDATE.md)
