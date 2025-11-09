# Core Functionality Validation Plan

**Date:** 2025-01-27  
**Status:** PLANNING  
**Focus:** Validate Phase 2 features (Spatial Profiler, Image Fitting) with real data

---

## Overview

After completing Priority 1 (Region Mask Integration), we're deferring polish features (Moffat Rotation, Residual Visualization) to focus on **validating core functionality** with real DSA-110 data.

---

## Phase 2 Features to Validate

### 1. Spatial Profiler ✅ Implemented
- **Backend:** `src/dsa110_contimg/utils/profiling.py`
- **API:** `POST /api/images/{id}/profile`
- **Frontend:** `ProfileTool.tsx`, `ProfilePlot.tsx`
- **Features:**
  - Line profile extraction
  - Polyline profile extraction
  - Point profile extraction
  - 1D Gaussian/Moffat fitting

### 2. Image Fitting ✅ Implemented
- **Backend:** `src/dsa110_contimg/utils/fitting.py`
- **API:** `POST /api/images/{id}/fit`
- **Frontend:** `ImageFittingTool.tsx`, `FittingVisualization.tsx`
- **Features:**
  - 2D Gaussian fitting (with rotation)
  - 2D Moffat fitting (circular only)
  - Region-constrained fitting (Priority 1)
  - Initial guess estimation

### 3. Region Management ✅ Implemented
- **Backend:** `src/dsa110_contimg/utils/regions.py`
- **API:** `/api/regions` endpoints
- **Frontend:** `RegionTools.tsx`, `RegionList.tsx`
- **Features:**
  - Circle regions
  - Rectangle regions
  - Region statistics
  - Region-constrained fitting

---

## Validation Objectives

### 1. Functional Correctness
- [ ] All API endpoints respond correctly
- [ ] Frontend components render and interact properly
- [ ] Data flows correctly between frontend and backend
- [ ] Error handling works as expected

### 2. Accuracy Verification
- [ ] Profile extraction matches expected values
- [ ] Fitting results are physically reasonable
- [ ] Coordinate systems are correct (pixel ↔ WCS)
- [ ] Region masks constrain fitting correctly

### 3. Performance Testing
- [ ] Response times acceptable for typical images
- [ ] Large images handled gracefully
- [ ] No memory leaks or resource issues

### 4. Integration Testing
- [ ] Works with real DSA-110 FITS images
- [ ] Compatible with existing pipeline products
- [ ] Database integration works correctly

---

## Test Plan

### Phase 1: Unit Testing (Quick Verification) ✅ DONE
- **Status:** Completed for Priority 1
- **Results:** All tests passed
- **Files:** `test_priority1_quick.py`

### Phase 2: Integration Testing (Real Data)

#### Test 2.1: Spatial Profiler
**Test Cases:**
1. **Line Profile**
   - Draw line across a source
   - Verify profile extraction
   - Check coordinate conversion (pixel ↔ WCS)
   - Test 1D Gaussian fitting

2. **Point Profile**
   - Click on source center
   - Verify radius extraction
   - Check flux values reasonable

3. **Polyline Profile**
   - Draw polyline through multiple sources
   - Verify extraction along path
   - Check smoothness of profile

**Success Criteria:**
- Profiles extracted correctly
- Coordinates match expected values
- Fitting converges successfully
- Results physically reasonable

#### Test 2.2: Image Fitting
**Test Cases:**
1. **Gaussian Fitting (No Region)**
   - Fit source without region constraint
   - Verify parameters reasonable
   - Check chi-squared and R-squared
   - Verify WCS conversion

2. **Gaussian Fitting (With Region)**
   - Create circle region around source
   - Fit with region constraint
   - Verify fit constrained to region
   - Compare with unconstrained fit

3. **Moffat Fitting**
   - Fit circular source with Moffat
   - Compare with Gaussian fit
   - Verify circular profile (no rotation)

**Success Criteria:**
- Fits converge successfully
- Parameters physically reasonable
- Region constraints work correctly
- WCS coordinates accurate

#### Test 2.3: Region Management
**Test Cases:**
1. **Circle Region**
   - Create circle region
   - Verify saved to database
   - Test region statistics
   - Use in fitting

2. **Rectangle Region**
   - Create rectangle region
   - Verify saved correctly
   - Test region statistics

**Success Criteria:**
- Regions save correctly
- Statistics calculated accurately
- Regions work with fitting

---

## Test Data

### Available Test Images
- Location: `/stage/dsa110-contimg/images/`
- Format: FITS files
- Beam: Highly elliptical (~3.2:1 ratio)
- Sources: Unresolved compact sources

### Test Images to Use
1. **Primary beam corrected:** `*img-image-pb.fits`
2. **Standard images:** `*img-image.fits`
3. **Residual images:** `*img-residual.fits` (for testing)

---

## Validation Checklist

### Backend Validation
- [ ] API endpoints respond correctly
- [ ] Error handling works
- [ ] Database operations succeed
- [ ] Coordinate conversions accurate
- [ ] Fitting algorithms converge
- [ ] Region masks work correctly

### Frontend Validation
- [ ] Components render correctly
- [ ] User interactions work
- [ ] Data displays properly
- [ ] JS9 integration works
- [ ] Plotly visualizations render
- [ ] Error messages display

### Integration Validation
- [ ] End-to-end workflows function
- [ ] Data persistence works
- [ ] Coordinate systems consistent
- [ ] Performance acceptable

---

## Success Criteria

### Minimum Viable Validation
- ✅ All API endpoints functional
- ✅ Frontend components render
- ✅ Basic workflows work end-to-end
- ✅ No critical bugs or errors

### Full Validation
- ✅ All test cases pass
- ✅ Accuracy verified with real data
- ✅ Performance acceptable
- ✅ Error handling robust
- ✅ Documentation complete

---

## Next Steps

1. **Set up test environment**
   - Ensure API server can run
   - Verify database access
   - Check test image availability

2. **Run integration tests**
   - Test Spatial Profiler with real images
   - Test Image Fitting with real sources
   - Test Region Management workflow

3. **Document results**
   - Record test results
   - Note any issues found
   - Document workarounds if needed

4. **Fix issues**
   - Address any bugs found
   - Improve error handling if needed
   - Optimize performance if required

---

## Related Documents

- `docs/analysis/PHASE2_WEEKS6-7_COMPLETION.md` - Image fitting implementation
- `docs/analysis/PHASE2_WEEK5_COMPLETION.md` - Spatial profiler implementation
- `docs/analysis/PRIORITY1_COMPLETION.md` - Region mask implementation
- `docs/analysis/PRIORITY1_TEST_RESULTS.md` - Unit test results

---

**Status:** READY FOR VALIDATION

