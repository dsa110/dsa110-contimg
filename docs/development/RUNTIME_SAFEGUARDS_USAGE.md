# Runtime Safeguards Usage Guide

## Overview

The `runtime_safeguards` module provides decorators, validators, and runtime checks that execute automatically to prevent common mistakes. These safeguards are built into the code itself, not just documentation.

## Quick Start

```python
from dsa110_contimg.utils.runtime_safeguards import (
    require_casa6_python,
    validate_wcs_4d,
    filter_non_finite_2d,
    log_progress,
    progress_monitor,
)

# Decorator ensures casa6 Python
@require_casa6_python
def my_pipeline_function():
    ...

# Automatic WCS 4D handling
wcs, is_4d, defaults = validate_wcs_4d(wcs)
ra, dec = wcs_pixel_to_world_safe(wcs, x, y, is_4d, defaults)

# Automatic non-finite filtering
data, x_coords, y_coords = filter_non_finite_2d(
    data, x_coords, y_coords, min_points=10
)

# Automatic progress monitoring
@progress_monitor(operation_name="Image Fitting", warn_threshold=10.0)
def fit_image(...):
    ...
```

## Safeguards by Category

### 1. Python Environment

**Problem**: Code runs in wrong Python environment.

**Solution**: Use `@require_casa6_python` decorator.

```python
from dsa110_contimg.utils.runtime_safeguards import require_casa6_python

@require_casa6_python
def critical_pipeline_function():
    """This function will fail if not in casa6 Python."""
    import casatools
    # ... use CASA tools
```

**Runtime Check**: Automatically checks `sys.executable` and CASA availability.

**Error**: Raises `RuntimeError` with helpful message if not in casa6.

---

### 2. WCS Handling (4D Support)

**Problem**: Code assumes 2D WCS, fails on 4D (radio astronomy standard).

**Solution**: Use safe WCS conversion functions.

```python
from dsa110_contimg.utils.runtime_safeguards import (
    validate_wcs_4d,
    wcs_pixel_to_world_safe,
    wcs_world_to_pixel_safe,
)

# Validate and detect 4D
wcs, is_4d, defaults = validate_wcs_4d(wcs)

# Safe pixel to world (handles both 2D and 4D)
ra, dec = wcs_pixel_to_world_safe(wcs, x, y, is_4d, defaults)

# Safe world to pixel
x, y = wcs_world_to_pixel_safe(wcs, ra, dec, is_4d, defaults)
```

**Runtime Check**: Automatically detects 4D WCS and uses appropriate conversion method.

**Error**: Raises `ValueError` if WCS is None when needed.

---

### 3. Non-Finite Values

**Problem**: NaN/Inf values cause astropy fitting to fail.

**Solution**: Use filtering functions before fitting.

```python
from dsa110_contimg.utils.runtime_safeguards import (
    filter_non_finite,
    filter_non_finite_2d,
)

# For 1D data
clean_data = filter_non_finite(data, min_points=10, warn=True)

# For 2D fitting (data + coordinates)
data, x_coords, y_coords = filter_non_finite_2d(
    data, x_coords, y_coords, min_points=10
)

# Now safe to fit
fitted_model = fitter(model, x_coords, y_coords, data)
```

**Runtime Check**: Validates minimum number of finite points, warns about filtering.

**Error**: Raises `ValueError` if insufficient finite points.

---

### 4. Progress Monitoring

**Problem**: Long operations appear hung, no feedback.

**Solution**: Use `log_progress` and `@progress_monitor` decorator.

```python
from dsa110_contimg.utils.runtime_safeguards import (
    log_progress,
    progress_monitor,
)

# Manual progress logging
start_time = time.time()
log_progress("Starting image fitting...")
# ... do work ...
log_progress("Image fitting completed", start_time)

# Automatic progress monitoring with decorator
@progress_monitor(operation_name="Gaussian Fitting", warn_threshold=10.0)
def fit_2d_gaussian(...):
    # Automatically logs start/end with timestamps
    # Warns if operation takes > 10 seconds
    ...
```

**Runtime Check**: Automatically ensures unbuffered output, logs timestamps.

**Warning**: Warns if operation exceeds threshold.

---

### 5. Input Validation

**Problem**: Invalid inputs cause cryptic errors later.

**Solution**: Use validation functions.

```python
from dsa110_contimg.utils.runtime_safeguards import (
    validate_image_shape,
    validate_region_mask,
)

# Validate image shape
ny, nx = validate_image_shape(data, min_size=10, max_size=10000)

# Validate region mask
mask = validate_region_mask(mask, image_shape=(ny, nx))
```

**Runtime Check**: Validates dimensions, handles multi-dimensional data.

**Error**: Raises `ValueError` with clear message if invalid.

---

## Integration Examples

### Example 1: Fitting Function with All Safeguards

```python
from dsa110_contimg.utils.runtime_safeguards import (
    require_casa6_python,
    validate_wcs_4d,
    filter_non_finite_2d,
    validate_image_shape,
    progress_monitor,
    log_progress,
)

@require_casa6_python
@progress_monitor(operation_name="2D Gaussian Fitting", warn_threshold=10.0)
def fit_2d_gaussian_safe(fits_path, region_mask=None, wcs=None):
    """Fitting function with all safeguards."""
    from astropy.io import fits
    from astropy.modeling import models, fitting
    
    # Load and validate image
    with fits.open(fits_path) as hdul:
        data = hdul[0].data
        header = hdul[0].header
    
    # Validate shape
    ny, nx = validate_image_shape(data)
    
    # Validate WCS
    wcs, is_4d, defaults = validate_wcs_4d(wcs)
    
    # Prepare coordinates
    y_coords, x_coords = np.ogrid[:ny, :nx]
    
    # Apply region mask if provided
    if region_mask is not None:
        fit_mask = region_mask
    else:
        fit_mask = np.ones((ny, nx), dtype=bool)
    
    # Filter non-finite values
    fit_data, fit_x, fit_y = filter_non_finite_2d(
        data[fit_mask],
        x_coords[fit_mask],
        y_coords[fit_mask],
        min_points=10
    )
    
    # Now safe to fit
    model = models.Gaussian2D(...)
    fitter = fitting.LevMarLSQFitter()
    fitted_model = fitter(model, fit_x, fit_y, fit_data)
    
    return fitted_model
```

### Example 2: Region Creation with Safeguards

```python
from dsa110_contimg.utils.runtime_safeguards import (
    validate_wcs_4d,
    wcs_world_to_pixel_safe,
    validate_region_mask,
    log_progress,
)

def create_region_mask_safe(shape, region, wcs=None, header=None):
    """Create region mask with safeguards."""
    ny, nx = shape[:2]
    
    # Validate WCS
    wcs, is_4d, defaults = validate_wcs_4d(wcs)
    
    # Convert region center to pixels
    ra = region.coordinates.get("ra_deg", 0)
    dec = region.coordinates.get("dec_deg", 0)
    
    if wcs:
        x, y = wcs_world_to_pixel_safe(wcs, ra, dec, is_4d, defaults)
    else:
        x, y = nx // 2, ny // 2
    
    # Create mask based on region type
    mask = np.zeros((ny, nx), dtype=bool)
    
    if region.type == "circle":
        radius_pix = region.coordinates.get("radius_deg", 0.01) * 3600.0 / pixel_scale
        y_coords, x_coords = np.ogrid[:ny, :nx]
        mask = (x_coords - x)**2 + (y_coords - y)**2 <= radius_pix**2
    
    # Validate mask
    mask = validate_region_mask(mask, (ny, nx))
    
    return mask
```

---

## Module Initialization

The safeguards module automatically:

1. **Ensures unbuffered output** on import
2. **Warns if not in casa6** (but doesn't fail - allows testing)

```python
# This happens automatically on import
from dsa110_contimg.utils.runtime_safeguards import ...

# Output is now unbuffered
# Warning shown if not in casa6 (but code still runs)
```

---

## Best Practices

1. **Use decorators for critical functions**: `@require_casa6_python` for pipeline functions
2. **Use safe WCS functions**: Always use `wcs_pixel_to_world_safe` / `wcs_world_to_pixel_safe`
3. **Filter before fitting**: Always use `filter_non_finite_2d` before astropy fitting
4. **Monitor long operations**: Use `@progress_monitor` for operations > 1 second
5. **Validate inputs early**: Use validation functions at function entry

---

## Migration Guide

### Before (Unsafe)
```python
def fit_2d_gaussian(fits_path, wcs=None):
    data = fits.getdata(fits_path)
    sky_coord = wcs.pixel_to_world(x, y)  # Fails on 4D WCS
    fitted_model = fitter(model, x, y, data)  # Fails on NaN
```

### After (Safe)
```python
from dsa110_contimg.utils.runtime_safeguards import (
    validate_wcs_4d,
    wcs_pixel_to_world_safe,
    filter_non_finite_2d,
)

def fit_2d_gaussian(fits_path, wcs=None):
    data = fits.getdata(fits_path)
    wcs, is_4d, defaults = validate_wcs_4d(wcs)
    ra, dec = wcs_pixel_to_world_safe(wcs, x, y, is_4d, defaults)
    data, x, y = filter_non_finite_2d(data, x_coords, y_coords)
    fitted_model = fitter(model, x, y, data)  # Safe!
```

---

## Summary

Runtime safeguards provide:
- ✅ **Automatic checks** - Execute when code runs
- ✅ **Clear errors** - Helpful error messages
- ✅ **Warnings** - Non-fatal issues are warned
- ✅ **Easy to use** - Decorators and simple function calls
- ✅ **No performance overhead** - Minimal impact when safeguards pass

Use these safeguards throughout the codebase to prevent common mistakes automatically.


