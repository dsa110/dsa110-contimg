# Safeguard Integration Locations

## Priority 1: `utils/fitting.py` (CRITICAL)

### File: `src/dsa110_contimg/utils/fitting.py`

#### 1. Add imports at top (after existing imports)
```python
# Add after line ~20
from dsa110_contimg.utils.runtime_safeguards import (
    filter_non_finite_2d,
    validate_wcs_4d,
    wcs_pixel_to_world_safe,
    progress_monitor,
)
```

#### 2. Update `fit_2d_gaussian()` function (starts at line 134)

**Replace lines ~224-229** (manual non-finite filtering):
```python
# OLD:
finite_mask = np.isfinite(fit_data)
if np.sum(finite_mask) == 0:
    raise ValueError("No finite values in data for fitting")

fit_data = fit_data[finite_mask]
fit_x = fit_x[finite_mask]
fit_y = fit_y[finite_mask]

# NEW:
fit_data, fit_x, fit_y = filter_non_finite_2d(
    fit_data, fit_x, fit_y, min_points=10, warn=True
)
```

**Replace lines ~295-312** (manual WCS conversion):
```python
# OLD:
if wcs is not None:
    try:
        # Handle 4D WCS (common in radio astronomy)
        if hasattr(wcs, 'naxis') and wcs.naxis == 4:
            world_coords = wcs.all_pix2world(x_center, y_center, 0, 0, 0)
            center_wcs = {
                "ra": float(world_coords[0]),
                "dec": float(world_coords[1]),
            }
        else:
            sky_coord = wcs.pixel_to_world(x_center, y_center)
            center_wcs = {
                "ra": float(sky_coord.ra.deg),
                "dec": float(sky_coord.dec.deg),
            }
    except Exception as e:
        LOG.warning(f"Could not convert center to WCS: {e}")

# NEW:
wcs, is_4d, defaults = validate_wcs_4d(wcs)
if wcs:
    try:
        ra, dec = wcs_pixel_to_world_safe(wcs, x_center, y_center, is_4d, defaults)
        center_wcs = {"ra": ra, "dec": dec}
    except Exception as e:
        LOG.warning(f"Could not convert center to WCS: {e}")
```

**Add decorator to function (line 134)**:
```python
# OLD:
def fit_2d_gaussian(...):

# NEW:
@progress_monitor(operation_name="2D Gaussian Fitting", warn_threshold=10.0)
def fit_2d_gaussian(...):
```

#### 3. Update `fit_2d_moffat()` function (starts at line 346)

**Same changes as `fit_2d_gaussian()`**:
- Replace lines ~444-449 (non-finite filtering)
- Replace lines ~515-536 (WCS conversion)
- Add `@progress_monitor` decorator

---

## Priority 2: `utils/regions.py` (HIGH)

### File: `src/dsa110_contimg/utils/regions.py`

#### 1. Add imports at top
```python
# Add after line ~20
from dsa110_contimg.utils.runtime_safeguards import (
    validate_wcs_4d,
    wcs_world_to_pixel_safe,
    validate_image_shape,
    validate_region_mask,
)
```

#### 2. Update `create_region_mask()` function (starts at line 316)

**Add shape validation at start (after line ~322)**:
```python
# Add after: ny, nx = shape[:2]
ny, nx = validate_image_shape(
    np.zeros(shape[:2]), min_size=1
)[:2]  # Get ny, nx from validated shape
```

**Replace lines ~340-356** (manual WCS conversion):
```python
# OLD:
if wcs:
    try:
        ra = region.coordinates.get("ra_deg", 0)
        dec = region.coordinates.get("dec_deg", 0)
        
        # Handle 4D WCS (common in radio astronomy: RA, Dec, Frequency, Stokes)
        if hasattr(wcs, 'naxis') and wcs.naxis == 4:
            # Use all_pix2world for 4D WCS
            pixel_coords = wcs.all_world2pix([[ra, dec, 0, 0]], 0)[0]
            x, y = float(pixel_coords[0]), float(pixel_coords[1])
        else:
            # Standard 2D WCS
            x, y = wcs.wcs_world2pix([[ra, dec]], 0)[0]
            x, y = float(x), float(y)
        
        x, y = int(x), int(y)
    except Exception as e:
        # Fallback to center
        import logging
        logging.warning(f"Could not convert WCS coordinates: {e}, using image center")
        x, y = nx // 2, ny // 2

# NEW:
wcs, is_4d, defaults = validate_wcs_4d(wcs)
if wcs:
    try:
        ra = region.coordinates.get("ra_deg", 0)
        dec = region.coordinates.get("dec_deg", 0)
        x, y = wcs_world_to_pixel_safe(wcs, ra, dec, is_4d, defaults)
        x, y = int(x), int(y)
    except Exception as e:
        import logging
        logging.warning(f"Could not convert WCS coordinates: {e}, using image center")
        x, y = nx // 2, ny // 2
```

**Add mask validation before return (before line ~380)**:
```python
# Add before: return mask
mask = validate_region_mask(mask, (ny, nx))
return mask
```

---

## Priority 3: `api/routes.py` (MEDIUM)

### File: `src/dsa110_contimg/api/routes.py`

#### 1. Add imports at top
```python
# Add after line ~20
import time
from dsa110_contimg.utils.runtime_safeguards import (
    log_progress,
    check_performance_threshold,
)
```

#### 2. Update `/api/images/{image_id}/fit` endpoint

**Add progress monitoring (around line ~400)**:
```python
@router.post("/images/{image_id}/fit")
def fit_image(...):
    start_time = time.time()
    log_progress(f"Starting {model} fit for image {image_id}...")
    
    # ... existing code ...
    
    try:
        # Perform fitting
        if model == "gaussian":
            fit_result = fit_2d_gaussian(...)
        else:
            fit_result = fit_2d_moffat(...)
        
        elapsed = time.time() - start_time
        if check_performance_threshold(f"{model} fitting", elapsed, 10.0):
            # Operation was slow - could log or warn user
            pass
        
        log_progress(f"Completed {model} fit for image {image_id}", start_time)
        return fit_result
```

#### 3. Update `/api/images/{image_id}/profile` endpoint

**Add progress monitoring (similar to above)**

---

## Priority 4: `utils/profiling.py` (MEDIUM)

### File: `src/dsa110_contimg/utils/profiling.py`

#### 1. Add imports at top
```python
from dsa110_contimg.utils.runtime_safeguards import (
    progress_monitor,
)
```

#### 2. Update `extract_point_profile()` function

**Add decorator (around line ~150)**:
```python
@progress_monitor(operation_name="Point Profile Extraction", warn_threshold=10.0)
def extract_point_profile(...):
    # Function already exists, just add decorator
```

---

## Priority 5: Pipeline Functions (LOW)

### Files: `src/dsa110_contimg/pipeline/*.py`, `src/dsa110_contimg/conversion/*.py`

#### Identify critical CASA-dependent functions:
- Functions that import `casatools`
- Functions that use CASA tasks
- Critical pipeline stages

#### Add decorator:
```python
from dsa110_contimg.utils.runtime_safeguards import require_casa6_python

@require_casa6_python
def critical_pipeline_function(...):
    import casatools
    # ... function code ...
```

---

## Integration Checklist

### Phase 1: Core Utilities
- [ ] Update `utils/fitting.py` imports
- [ ] Update `fit_2d_gaussian()` with safeguards
- [ ] Update `fit_2d_moffat()` with safeguards
- [ ] Test fitting functions with safeguards

### Phase 2: Region Utilities
- [ ] Update `utils/regions.py` imports
- [ ] Update `create_region_mask()` with safeguards
- [ ] Test region mask creation

### Phase 3: API Layer
- [ ] Update `api/routes.py` imports
- [ ] Add progress monitoring to `/api/images/{image_id}/fit`
- [ ] Add progress monitoring to `/api/images/{image_id}/profile`
- [ ] Test API endpoints

### Phase 4: Profiling
- [ ] Update `utils/profiling.py` imports
- [ ] Add progress monitoring to `extract_point_profile()`
- [ ] Test profiling functions

### Phase 5: Pipeline
- [ ] Identify critical CASA functions
- [ ] Add `@require_casa6_python` decorator
- [ ] Test pipeline functions

---

## Testing After Integration

After each phase, run validation:

```bash
# Test fitting functions
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -u validate_backend_core.py

# Test API endpoints
# Start API server and test endpoints

# Test region creation
# Run region management tests
```

---

## Rollback Plan

If safeguards cause issues:

1. **Temporary**: Comment out safeguard decorators/calls
2. **Permanent**: Revert specific commits
3. **Debug**: Check safeguard module logs/warnings

Safeguards are designed to be non-breaking - they warn but don't fail unless critical (like casa6 requirement).


