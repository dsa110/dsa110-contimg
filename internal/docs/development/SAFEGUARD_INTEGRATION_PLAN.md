# Safeguard Integration Plan

## Overview

This document outlines where to integrate runtime safeguards into the existing codebase to prevent common mistakes automatically.

## Priority Files for Integration

### 1. **HIGH PRIORITY**: `utils/fitting.py`

**Current Issues**:
- Manual non-finite filtering (can be missed)
- Manual 4D WCS handling (error-prone)
- No progress monitoring

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import (
    filter_non_finite_2d,
    validate_wcs_4d,
    wcs_pixel_to_world_safe,
    progress_monitor,
)

@progress_monitor(operation_name="2D Gaussian Fitting", warn_threshold=10.0)
def fit_2d_gaussian(fits_path, ...):
    # Replace manual filtering with:
    fit_data, fit_x, fit_y = filter_non_finite_2d(
        data[fit_mask], x_coords[fit_mask], y_coords[fit_mask], min_points=10
    )
    
    # Replace manual WCS conversion with:
    wcs, is_4d, defaults = validate_wcs_4d(wcs)
    if wcs:
        center_wcs = wcs_pixel_to_world_safe(wcs, x_center, y_center, is_4d, defaults)
```

**Files to Update**:
- `src/dsa110_contimg/utils/fitting.py`:
  - `fit_2d_gaussian()` - lines ~80-150
  - `fit_2d_moffat()` - lines ~150-220

---

### 2. **HIGH PRIORITY**: `utils/regions.py`

**Current Issues**:
- Manual 4D WCS handling (error-prone)
- No input validation

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import (
    validate_wcs_4d,
    wcs_world_to_pixel_safe,
    validate_region_mask,
    validate_image_shape,
)

def create_region_mask(shape, region, wcs=None, header=None):
    # Validate shape
    ny, nx = validate_image_shape(np.zeros(shape), min_size=1)
    
    # Safe WCS conversion
    wcs, is_4d, defaults = validate_wcs_4d(wcs)
    if wcs:
        x, y = wcs_world_to_pixel_safe(wcs, ra, dec, is_4d, defaults)
    
    # ... create mask ...
    
    # Validate mask
    mask = validate_region_mask(mask, (ny, nx))
    return mask
```

**Files to Update**:
- `src/dsa110_contimg/utils/regions.py`:
  - `create_region_mask()` - lines ~200-300

---

### 3. **MEDIUM PRIORITY**: `utils/profiling.py`

**Current Issues**:
- No progress monitoring for slow operations
- No performance warnings

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import (
    progress_monitor,
    check_performance_threshold,
)

@progress_monitor(operation_name="Point Profile Extraction", warn_threshold=10.0)
def extract_point_profile(...):
    # Automatically monitors progress and warns if slow
    ...
```

**Files to Update**:
- `src/dsa110_contimg/utils/profiling.py`:
  - `extract_point_profile()` - lines ~150-250 (slow operation)

---

### 4. **MEDIUM PRIORITY**: `api/routes.py`

**Current Issues**:
- No progress monitoring for API endpoints
- No performance warnings for users

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import (
    log_progress,
    check_performance_threshold,
)

@router.post("/images/{image_id}/fit")
def fit_image(...):
    start_time = time.time()
    log_progress(f"Starting fit for image {image_id}...")
    
    # ... do fitting ...
    
    elapsed = time.time() - start_time
    if check_performance_threshold("Image Fitting", elapsed, 10.0):
        # Warn user about slow operation
        pass
    
    return fit_result
```

**Files to Update**:
- `src/dsa110_contimg/api/routes.py`:
  - `/api/images/{image_id}/fit` endpoint
  - `/api/images/{image_id}/profile` endpoint

---

### 5. **LOW PRIORITY**: Pipeline Functions

**Current Issues**:
- No casa6 Python environment check

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import require_casa6_python

@require_casa6_python
def critical_pipeline_stage(...):
    # Will fail early if not in casa6
    import casatools
    ...
```

**Files to Consider**:
- `src/dsa110_contimg/pipeline/` - critical pipeline stages
- `src/dsa110_contimg/conversion/` - MS conversion functions

---

## Integration Steps

### Phase 1: Core Utilities (HIGH PRIORITY)

1. **Update `utils/fitting.py`**:
   - [ ] Replace manual non-finite filtering with `filter_non_finite_2d()`
   - [ ] Replace manual WCS conversion with `wcs_pixel_to_world_safe()`
   - [ ] Add `@progress_monitor` decorator to `fit_2d_gaussian()` and `fit_2d_moffat()`

2. **Update `utils/regions.py`**:
   - [ ] Replace manual WCS conversion with `wcs_world_to_pixel_safe()`
   - [ ] Add `validate_image_shape()` at function entry
   - [ ] Add `validate_region_mask()` before returning

### Phase 2: API Layer (MEDIUM PRIORITY)

3. **Update `api/routes.py`**:
   - [ ] Add progress logging to `/api/images/{image_id}/fit`
   - [ ] Add progress logging to `/api/images/{image_id}/profile`
   - [ ] Add performance warnings for slow operations

4. **Update `utils/profiling.py`**:
   - [ ] Add `@progress_monitor` to `extract_point_profile()` (slow operation)

### Phase 3: Pipeline Functions (LOW PRIORITY)

5. **Add `@require_casa6_python` to critical functions**:
   - [ ] Identify critical pipeline functions that require CASA
   - [ ] Add decorator to those functions

---

## Example Integration: `utils/fitting.py`

### Before:
```python
def fit_2d_gaussian(fits_path, ...):
    # Manual non-finite filtering
    finite_mask = np.isfinite(fit_data)
    if np.sum(finite_mask) == 0:
        raise ValueError("No finite values")
    fit_data = fit_data[finite_mask]
    fit_x = fit_x[finite_mask]
    fit_y = fit_y[finite_mask]
    
    # Manual WCS conversion
    if wcs:
        if hasattr(wcs, 'naxis') and wcs.naxis == 4:
            world_coords = wcs.all_pix2world(x_center, y_center, 0, 0, 0)
            center_wcs = {"ra": world_coords[0], "dec": world_coords[1]}
        else:
            sky_coord = wcs.pixel_to_world(x_center, y_center)
            center_wcs = {"ra": sky_coord.ra.deg, "dec": sky_coord.dec.deg}
    
    # Fit
    fitted_model = fitter(gaussian_model, fit_x, fit_y, fit_data)
```

### After:
```python
from dsa110_contimg.utils.runtime_safeguards import (
    filter_non_finite_2d,
    validate_wcs_4d,
    wcs_pixel_to_world_safe,
    progress_monitor,
)

@progress_monitor(operation_name="2D Gaussian Fitting", warn_threshold=10.0)
def fit_2d_gaussian(fits_path, ...):
    # Automatic non-finite filtering with validation
    fit_data, fit_x, fit_y = filter_non_finite_2d(
        data[fit_mask], x_coords[fit_mask], y_coords[fit_mask], min_points=10
    )
    
    # Automatic WCS handling (2D or 4D)
    wcs, is_4d, defaults = validate_wcs_4d(wcs)
    if wcs:
        ra, dec = wcs_pixel_to_world_safe(wcs, x_center, y_center, is_4d, defaults)
        center_wcs = {"ra": ra, "dec": dec}
    
    # Fit (now safe)
    fitted_model = fitter(gaussian_model, fit_x, fit_y, fit_data)
```

**Benefits**:
- ✅ Less code (no manual checks)
- ✅ Automatic error handling
- ✅ Progress monitoring built-in
- ✅ Works with both 2D and 4D WCS automatically

---

## Testing After Integration

After integrating safeguards, verify:

1. **Non-finite filtering**: Test with NaN/Inf data
2. **4D WCS**: Test with real DSA-110 FITS files
3. **Progress monitoring**: Verify timestamps appear
4. **Performance warnings**: Verify warnings for slow operations
5. **Error messages**: Verify helpful error messages

---

## Rollout Strategy

1. **Start with `utils/fitting.py`** (most critical, most issues)
2. **Then `utils/regions.py`** (WCS issues)
3. **Then `api/routes.py`** (user-facing)
4. **Finally pipeline functions** (less critical)

Test each integration before moving to the next.

---

## Summary

**Priority Order**:
1. ✅ `utils/fitting.py` - Fix non-finite filtering and WCS
2. ✅ `utils/regions.py` - Fix WCS handling
3. ✅ `api/routes.py` - Add progress monitoring
4. ✅ `utils/profiling.py` - Add progress monitoring
5. ✅ Pipeline functions - Add casa6 checks

**Key Benefits**:
- Automatic error prevention
- Less code to maintain
- Better user experience
- Consistent error handling


