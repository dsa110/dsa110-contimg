# Validation Issues and Solutions

**Date:** 2025-01-27  
**Status:** IN PROGRESS

---

## Issues Encountered

### 1. Function Signature Mismatches ✅ FIXED
- **Issue:** Validation script used wrong parameter names
- **Fix:** Updated to match actual function signatures
- **Status:** Fixed

### 2. Non-Finite Values in Data ⚠️ NEEDS HANDLING
- **Issue:** FITS images contain NaN/Inf values causing fitting to fail
- **Error:** `NonFiniteValueError: Objective function has encountered a non-finite value`
- **Impact:** Gaussian/Moffat fitting fails on real data
- **Solution Needed:** Filter non-finite values before fitting

### 3. WCS Conversion Issues ⚠️ NEEDS FIXING
- **Issue:** 4D WCS (common in radio astronomy) not handled correctly
- **Error:** `TypeError: WCS projection has 4 dimensions, so expected 2...`
- **Impact:** Region mask creation fails
- **Solution Needed:** Handle 4D WCS properly

### 4. FITSFixedWarning ℹ️ COSMETIC
- **Issue:** Astropy warning about header fixes
- **Impact:** Clutters output
- **Solution:** Suppress warning (already attempted)

---

## Root Causes

### Real Data Characteristics
- DSA-110 images contain NaN/Inf values (common in radio astronomy)
- Images have 4D WCS (RA, Dec, Frequency, Stokes)
- Large image sizes (6300x6300 pixels)

### Code Gaps
- Fitting functions don't filter non-finite values
- WCS handling assumes 2D WCS
- Validation script needs better error handling

---

## Solutions Needed

### Priority 1: Filter Non-Finite Values in Fitting
**Location:** `src/dsa110_contimg/utils/fitting.py`

Add filtering before fitting:
```python
# Filter non-finite values
finite_mask = np.isfinite(fit_data)
fit_data = fit_data[finite_mask]
fit_x = fit_x[finite_mask]
fit_y = fit_y[finite_mask]
```

### Priority 2: Handle 4D WCS
**Location:** `src/dsa110_contimg/utils/regions.py` and validation script

Check WCS dimensionality:
```python
if wcs.naxis == 4:
    # Use spatial dimensions only
    center_world = wcs.all_pix2world(x, y, 0, 0, 0)
else:
    # Standard 2D WCS
    center_world = wcs.pixel_to_world_values(x, y)
```

### Priority 3: Better Error Handling
**Location:** Validation script

- Catch and report errors gracefully
- Continue testing other features if one fails
- Provide actionable error messages

---

## Quick Fixes

### Option 1: Fix Code (Recommended)
- Update fitting functions to filter non-finite values
- Update WCS handling for 4D WCS
- Re-run validation

### Option 2: Work Around in Validation
- Use smaller test regions
- Skip problematic images
- Test with synthetic data first

### Option 3: Test Individual Components
- Test each feature separately
- Use smaller, cleaner test images
- Validate incrementally

---

## Next Steps

1. **Fix non-finite value filtering** in fitting functions
2. **Fix 4D WCS handling** in regions and validation
3. **Re-run validation** with fixes
4. **Document any remaining issues**

---

**Status:** Blocked on code fixes for non-finite values and 4D WCS handling

