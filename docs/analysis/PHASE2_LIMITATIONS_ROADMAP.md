# Phase 2 Limitations - Roadmap and Implementation Plan

**Date:** 2025-01-27  
**Status:** Planning  
**Reference:** `docs/analysis/PHASE2_WEEKS6-7_COMPLETION.md`

---

## Overview

This document outlines a prioritized plan for addressing the known limitations in Phase 2 (Image Fitting) implementation. Each limitation is analyzed for value, effort, and implementation approach.

---

## Priority 1: Region Mask Creation (HIGH PRIORITY) ✅ COMPLETED

### Current Status
- ✅ `create_region_mask()` function exists in `regions.py`
- ✅ Integrated into fitting API
- ✅ Fitting endpoint now properly creates and uses region masks
- ✅ Supports circle and rectangle regions
- ⚠️ Polygon regions not yet supported (returns empty mask)

### Value
- **HIGH** - Users expect region constraints to work
- Essential for accurate source fitting
- Already partially implemented (just needs integration)

### Effort
- **LOW-MEDIUM** - ~2-4 hours
- Leverage existing `create_region_mask()` function
- Minimal changes needed

### Implementation Status
- ✅ Completed on 2025-01-27
- ✅ Region mask creation integrated into `/api/images/{id}/fit` endpoint
- ✅ Supports circle and rectangle regions
- ✅ Proper error handling and validation
- See `docs/analysis/PRIORITY1_COMPLETION.md` for details

### Implementation Plan

**Step 1: Integrate Region Mask into Fitting API**
```python
# In routes.py, modify fit_image() endpoint:
from dsa110_contimg.utils.regions import create_region_mask

if region_id:
    # ... existing region lookup code ...
    
    # Create mask from region
    with fits.open(fits_path) as hdul:
        header = hdul[0].header
        data_shape = hdul[0].data.shape[:2]  # Get 2D shape
        
        region_mask = create_region_mask(
            shape=data_shape,
            region=region,
            wcs=wcs,
            header=header
        )
```

**Step 2: Handle Polygon Regions**
- Check if `create_region_mask` handles polygon regions
- If not, add polygon mask creation using `shapely` or manual pixel checking

**Step 3: Test**
- Test with circle regions
- Test with rectangle regions
- Test with polygon regions (if supported)
- Verify mask is applied correctly in fitting

**Files to Modify:**
- `src/dsa110_contimg/api/routes.py` - Integrate mask creation
- `src/dsa110_contimg/utils/regions.py` - Enhance if needed (polygon support)

**Estimated Time:** 2-4 hours

---

## Priority 2: Moffat Rotation Support (DEFERRED)

### Current Status
- ⚠️ `astropy.modeling.Moffat2D` doesn't support rotation directly
- ⚠️ Currently uses circular Moffat (no position angle)
- ⚠️ Less accurate for elliptical sources
- ✅ **Decision: Deferred** - To be added after validating more fundamental stages

### Value
- **MEDIUM** - Improves accuracy for elliptical sources
- Gaussian already supports rotation, so this is parity
- Less critical since Gaussian works well for most cases
- **Note:** Beams are highly elliptical (~3.2:1 ratio), but Gaussian handles this

### Effort
- **MEDIUM-HIGH** - ~4-8 hours
- Requires custom model or coordinate transformation
- More complex than region masks

### Decision Rationale
- Focus on core functionality first
- Validate fundamental stages before adding polish
- Gaussian already works for elliptical sources
- Can be added later when needed

### Implementation Options

**Option A: Rotated Coordinate System (Recommended)**
```python
# Transform coordinates before fitting
# Rotate coordinate system by PA, fit circular Moffat, rotate back
def fit_2d_moffat_rotated(...):
    # 1. Rotate coordinates by initial PA guess
    # 2. Fit circular Moffat in rotated space
    # 3. Transform parameters back
    # 4. Refine fit with rotation parameter
```

**Option B: Custom Rotated Moffat Model**
```python
# Create custom model using CompoundModel
from astropy.modeling import CompoundModel
# Combine Moffat2D with rotation transformation
```

**Option C: Use scipy.optimize Directly**
```python
# Define rotated Moffat function manually
# Use scipy.optimize.curve_fit with full parameter control
```

**Recommended Approach:** Option A (rotated coordinate system)
- Leverages existing astropy models
- More stable than custom models
- Easier to debug

**Files to Modify:**
- `src/dsa110_contimg/utils/fitting.py` - Add rotated Moffat fitting

**Estimated Time:** 4-8 hours

---

## Priority 3: Residual Visualization (DEFERRED)

### Current Status
- ✅ Residual statistics calculated (mean, std, max)
- ⚠️ No visual residual image overlay
- ⚠️ Users can't see where fit fails
- ✅ **Decision: Deferred** - To be added after validating more fundamental stages

### Value
- **MEDIUM** - Helps users assess fit quality visually
- Useful for debugging poor fits
- Nice-to-have feature

### Effort
- **MEDIUM** - ~4-6 hours
- Need to serve residual image or calculate client-side
- JS9 overlay integration

### Decision Rationale
- Focus on core functionality first
- Validate fundamental stages before adding polish
- Residual statistics already available (mean, std, max)
- Can be added later when needed

### Implementation Plan

**Step 1: Calculate Residual Image**
```python
# In fitting.py, already calculated:
residuals = data - fitted_values

# Add to return:
return {
    ...
    "residuals_image": residuals.tolist(),  # Or save as FITS
}
```

**Step 2: Serve Residual Image**
- Option A: Return residual data in API response (large payload)
- Option B: Save residual as temporary FITS, serve via endpoint
- Option C: Calculate client-side from fit parameters (complex)

**Step 3: Display in Frontend**
```typescript
// In FittingVisualization.tsx
// Add residual image overlay toggle
// Use JS9 to display residual as colormap overlay
```

**Recommended Approach:** Option B (temporary FITS file)
- Efficient for large images
- Reuses existing FITS serving infrastructure
- Clean separation of concerns

**Files to Modify:**
- `src/dsa110_contimg/utils/fitting.py` - Return residual image path
- `src/dsa110_contimg/api/routes.py` - Serve residual FITS
- `frontend/src/components/Sky/FittingVisualization.tsx` - Add residual overlay

**Estimated Time:** 4-6 hours

---

## Priority 4: Parameter Locking (LOW PRIORITY)

### Current Status
- ⚠️ All parameters are free to vary
- ⚠️ No way to fix certain parameters
- ⚠️ Users might want to fix known values (e.g., known position)

### Value
- **LOW-MEDIUM** - Power-user feature
- Useful for constrained fitting scenarios
- Not essential for basic use cases

### Effort
- **MEDIUM** - ~6-8 hours
- Requires UI changes + fitting logic modifications
- Need to handle parameter bounds/constraints

### Implementation Plan

**Step 1: Add Parameter Locking to API**
```python
# In routes.py
locked_parameters: Optional[Dict[str, Any]] = Body(None)

# In fitting.py
def fit_2d_gaussian(..., locked_params: Optional[Dict] = None):
    # Set parameter bounds to fixed values
    if locked_params:
        if 'amplitude' in locked_params:
            gaussian_model.amplitude.fixed = True
            gaussian_model.amplitude.value = locked_params['amplitude']
        # ... etc
```

**Step 2: Add UI Controls**
```typescript
// In ImageFittingTool.tsx
// Add checkboxes/inputs for each parameter
// Allow users to lock and set values
```

**Step 3: Update Fitting Logic**
- Modify astropy model to use `fixed=True` for locked parameters
- Ensure locked parameters aren't varied during fitting

**Files to Modify:**
- `src/dsa110_contimg/utils/fitting.py` - Add parameter locking
- `src/dsa110_contimg/api/routes.py` - Accept locked parameters
- `frontend/src/components/Sky/ImageFittingTool.tsx` - Add UI controls

**Estimated Time:** 6-8 hours

---

## Priority 5: Multiple Source Fitting (LOW PRIORITY)

### Current Status
- ⚠️ Only single source fitting supported
- ⚠️ No way to fit multiple sources simultaneously
- ⚠️ Users must fit sources one at a time

### Value
- **LOW** - Advanced feature
- Useful for blended sources
- Can be worked around with sequential fitting

### Effort
- **HIGH** - ~16-24 hours
- Requires significant refactoring
- Complex initial guess for multiple sources
- UI changes for managing multiple fits

### Implementation Plan

**Phase 1: Backend Support**
- Modify fitting functions to accept multiple initial guesses
- Use compound models (sum of Gaussians/Moffats)
- Handle parameter correlation

**Phase 2: Initial Guess**
- Implement source detection (peak finding)
- Automatic multi-source detection
- Or manual source selection

**Phase 3: Frontend**
- UI for selecting multiple sources
- Display multiple fit overlays
- Manage multiple fit results

**Recommended Approach:** Defer to Phase 3 or later
- High complexity
- Can be worked around with sequential fitting
- Better to stabilize single-source fitting first

**Estimated Time:** 16-24 hours (deferred)

---

## Recommended Implementation Order

### Immediate (Next Sprint)
1. **Priority 1: Region Mask Creation** (2-4 hours)
   - High value, low effort
   - Users expect this to work
   - Leverages existing code

### Deferred (After Core Validation)
2. **Priority 2: Moffat Rotation** (4-8 hours)
   - Medium value, medium-high effort
   - Improves model accuracy
   - Parity with Gaussian
   - **Deferred:** To be added after validating more fundamental stages

3. **Priority 3: Residual Visualization** (4-6 hours)
   - Medium value, medium effort
   - Improves user experience
   - Helps with fit quality assessment
   - **Deferred:** To be added after validating more fundamental stages

### Medium-term (Future Sprints)
4. **Priority 4: Parameter Locking** (6-8 hours)
   - Low-medium value, medium effort
   - Power-user feature
   - Can be added when needed

### Long-term (Future Phase)
5. **Priority 5: Multiple Source Fitting** (16-24 hours)
   - Low value, high effort
   - Advanced feature
   - Defer until core features are stable

---

## Quick Win: Region Mask Integration

Since `create_region_mask()` already exists, this can be implemented quickly:

**Implementation Steps:**
1. Import `create_region_mask` in `routes.py`
2. Call it when `region_id` is provided
3. Pass mask to fitting functions
4. Test with circle and rectangle regions

**Estimated Time:** 2-4 hours  
**Impact:** HIGH - Users expect this to work  
**Risk:** LOW - Leverages existing, tested code

---

## Summary

| Priority | Feature | Value | Effort | Status | ETA |
|----------|---------|-------|--------|--------|-----|
| 1 | Region Mask | HIGH | LOW-MED | ✅ COMPLETE | Done |
| 2 | Moffat Rotation | MED | MED-HIGH | 🔄 DEFERRED | After validation |
| 3 | Residual Viz | MED | MED | 🔄 DEFERRED | After validation |
| 4 | Parameter Lock | LOW-MED | MED | Deferred | 6-8h |
| 5 | Multi-Source | LOW | HIGH | Deferred | 16-24h |

**Total Estimated Effort:** 16-30 hours for priorities 1-3  
**Completed:** Priority 1 (Region Mask) ✅

---

**Next Action:** 
- ✅ Priority 1 (Region Mask) complete and verified
- 🔄 Priority 2 (Moffat Rotation) deferred - to be added after validating more fundamental stages
- 🔄 Priority 3 (Residual Visualization) deferred - to be added after validating more fundamental stages
- 📋 **Focus: Validate core functionality** - Test Phase 2 features (Spatial Profiler, Image Fitting) with real data

