# Final Recommendation: pyradiosky Integration

## Critical Finding

**DP3 cannot be used** - All MS files are 2-polarization, and DP3 requires 4 polarizations.

## Updated Recommendation

### Use pyradiosky for Sky Model Management + CASA ft() for Prediction

Since DP3 cannot handle 2-pol MS files, the workflow is:

1. **Use pyradiosky** for sky model construction and management
   - Better tooling than manual component lists
   - Support for multiple catalog formats
   - Advanced spectral modeling
   - Coordinate transformations

2. **Convert pyradiosky SkyModel → CASA componentlist**
   - Simple conversion (already have code structure)
   - CASA componentlist works with CASA ft()

3. **Use CASA ft()** for MODEL_DATA population
   - Works with 2-pol MS files
   - Proven and reliable
   - Already integrated

## Implementation

```python
from pyradiosky import SkyModel
from dsa110_contimg.calibration.skymodels import ft_from_cl

# Create/read sky model with pyradiosky
sky = SkyModel.from_votable_catalog('nvss.vot')
# Or: sky = SkyModel.from_gleam_catalog('gleam.vot')

# Convert to CASA componentlist
cl_path = convert_skymodel_to_componentlist(sky, out_path='model.cl')

# Use CASA ft() (works with 2-pol MS)
ft_from_cl(ms_path, cl_path)
```

## Benefits

Even without DP3, pyradiosky provides:
- ✓ Better sky model management
- ✓ Support for multiple catalog formats (GLEAM, VOTable, etc.)
- ✓ Advanced spectral modeling capabilities
- ✓ Coordinate transformation utilities
- ✓ Well-developed, maintained library

## What We Learned

1. **Rephasing + concatenation works** (but not needed if not using DP3)
2. **pyradiosky is valuable** for sky model management
3. **DP3 is not viable** for 2-pol MS files
4. **CASA ft() remains the solution** for MODEL_DATA population

## Next Steps

1. **Implement pyradiosky → componentlist conversion**
2. **Update existing functions** to use pyradiosky for catalog reading
3. **Keep CASA ft()** for MODEL_DATA population
4. **Remove DP3 integration** (or keep for future 4-pol MS support)

## Conclusion

**Use pyradiosky for better sky model management, but stick with CASA ft() for prediction** since DP3 cannot handle 2-pol MS files.

