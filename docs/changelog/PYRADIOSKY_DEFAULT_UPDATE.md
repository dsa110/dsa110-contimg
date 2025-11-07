# pyradiosky Now Default for Sky Model Construction

## Summary

The pipeline now uses `pyradiosky` as the default for sky model construction. All sky model creation functions (`make_point_cl`, `make_nvss_component_cl`) now use `pyradiosky` internally, providing better sky model management while maintaining backward compatibility.

## Changes Made

### 1. Updated `src/dsa110_contimg/calibration/skymodels.py`

#### New Functions:
- **`make_point_skymodel()`**: Creates a `pyradiosky.SkyModel` for a single point source
- **`make_nvss_skymodel()`**: Creates a `pyradiosky.SkyModel` from NVSS sources in a region

#### Updated Functions:
- **`make_point_cl()`**: Now uses `pyradiosky` internally via `make_point_skymodel()` → `convert_skymodel_to_componentlist()`
- **`make_nvss_component_cl()`**: Now uses `pyradiosky` internally via `make_nvss_skymodel()` → `convert_skymodel_to_componentlist()`
- **`convert_skymodel_to_componentlist()`**: Enhanced to:
  - Handle empty sky models
  - Support spectral index when available
  - Properly format RA/Dec coordinates for CASA

## Benefits

1. **Better Sky Model Management**: `pyradiosky` provides robust sky model handling
2. **Multiple Catalog Formats**: Support for VOTable, SkyH5, and other formats
3. **Advanced Spectral Modeling**: Built-in support for spectral indices and frequency-dependent models
4. **Backward Compatible**: All existing code continues to work without changes
5. **Consistent API**: Same function signatures, internal implementation improved

## Migration

**No migration required!** The API remains the same:

```python
# This still works exactly as before
from dsa110_contimg.calibration.skymodels import make_point_cl, make_nvss_component_cl

# Single point source (now uses pyradiosky internally)
cl = make_point_cl('source', ra_deg, dec_deg, flux_jy=2.3, freq_ghz=1.4, out_path='source.cl')

# NVSS sources (now uses pyradiosky internally)
cl = make_nvss_component_cl(ra_deg, dec_deg, radius_deg=0.2, min_mjy=10.0, 
                             freq_ghz=1.4, out_path='nvss.cl')
```

## Direct pyradiosky Usage

For advanced use cases, you can also use `pyradiosky` directly:

```python
from pyradiosky import SkyModel
from dsa110_contimg.calibration.skymodels import convert_skymodel_to_componentlist

# Create sky model from catalog
sky = SkyModel.from_votable_catalog('nvss.vot')

# Convert to componentlist
cl = convert_skymodel_to_componentlist(sky, out_path='model.cl')
```

## Testing

All existing pipeline code should work without modification. The functions maintain the same API and behavior, but now use `pyradiosky` internally for better sky model management.

## Dependencies

- `pyradiosky` is now required (should be installed in `casa6` environment)
- All other dependencies remain the same

## Files Modified

- `src/dsa110_contimg/calibration/skymodels.py`: Updated to use pyradiosky as default

## Files Using These Functions (No Changes Required)

- `src/dsa110_contimg/imaging/cli_imaging.py`: Uses `make_point_cl` and `make_nvss_component_cl` (works as-is)

