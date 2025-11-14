# CARTA Integration - Phase 2 TODO (Working Document)

**Phase:** Analysis Tools (Weeks 5-7)  
**Status:** Complete (Ready for Testing)  
**Started:** 2025-01-27  
**Week 5 Completed:** 2025-01-27  
**Weeks 6-7 Completed:** 2025-01-27  
**Reference:** `docs/analysis/CARTA_INTEGRATION_ASSESSMENT.md`  
**Related:** `docs/analysis/CARTA_INTEGRATION_TODO.md`

---

## Week 5: Spatial Profiler

### Task 2.1: Backend Profile Extraction API ✅

- [x] **Create profile extraction utility module** (Day 1) (2025-01-27)
  - [x] Create `src/dsa110_contimg/utils/profiling.py`
  - [x] Implement `extract_line_profile()` function
    - [ ] Accept image path (FITS), start/end coordinates (pixel or WCS)
    - [ ] Extract pixel values along line using Bresenham's algorithm or interpolation
    - [ ] Calculate distance along profile (arcsec or pixels)
    - [ ] Handle WCS conversion if coordinates are in RA/Dec
    - [ ] Return profile data: `{"distance": [...], "flux": [...], "error": [...]}`
  - [ ] Implement `extract_polyline_profile()` function
    - [ ] Accept list of coordinate points
    - [ ] Extract pixels along polyline segments
    - [ ] Calculate cumulative distance
  - [ ] Implement `extract_point_profile()` function (for ensemble profiles)
    - [ ] Accept center coordinate and radius
    - [ ] Extract radial profile (average in annuli)
    - [ ] Return radial distance vs flux
  - [ ] Add error handling for invalid coordinates, missing files
  - [ ] Add support for multi-dimensional FITS (handle Stokes, frequency axes)
  - Time estimate: (1 day)

- [x] **Create profile extraction API endpoint** (Day 1-2) (2025-01-27)
  - [ ] Add `/api/images/{id}/profile` endpoint to `src/dsa110_contimg/api/routes.py`
  - [ ] Accept query parameters:
    - `type`: `line`, `polyline`, or `point` (required)
    - `coordinates`: JSON array of coordinate pairs (required)
    - `coordinate_system`: `pixel` or `wcs` (default: `wcs`)
    - `width`: Width of profile extraction in pixels (default: 1, for averaging)
  - [ ] Validate input parameters
  - [ ] Resolve image path using `image_utils.resolve_image_path()`
  - [ ] Call appropriate profile extraction function
  - [ ] Return JSON response:
    ```json
    {
      "profile_type": "line",
      "distance": [0.0, 0.5, 1.0, ...],
      "flux": [0.1, 0.2, 0.15, ...],
      "error": [0.01, 0.01, 0.01, ...],
      "units": {
        "distance": "arcsec",
        "flux": "Jy/beam"
      },
      "coordinates": [[ra1, dec1], [ra2, dec2]]
    }
    ```
  - [ ] Add error handling and validation
  - [ ] Time estimate: (0.5-1 day)

**Files to create/modify:**
- `src/dsa110_contimg/utils/profiling.py` (new)
- `src/dsa110_contimg/api/routes.py` (modify)

**Acceptance criteria:**
- API endpoint accepts valid profile requests
- Returns correct profile data for line, polyline, and point profiles
- Handles both pixel and WCS coordinates
- Error messages are clear and actionable

---

### Task 2.2: Backend Profile Fitting ✅

- [x] **Implement profile fitting functions** (Day 2-3) (2025-01-27)
  - [ ] Add fitting functions to `src/dsa110_contimg/utils/profiling.py`
  - [ ] Implement `fit_gaussian_profile()` function
    - [ ] Use `scipy.optimize.curve_fit` or `astropy.modeling.fitting`
    - [ ] Fit 1D Gaussian: `A * exp(-0.5 * ((x - x0) / sigma)^2)`
    - [ ] Return fitted parameters: amplitude, center, sigma, FWHM
    - [ ] Return fit statistics: chi-squared, reduced chi-squared, R-squared
    - [ ] Return fitted model values for plotting
  - [ ] Implement `fit_moffat_profile()` function
    - [ ] Fit 1D Moffat: `A * (1 + ((x - x0) / alpha)^2)^(-beta)`
    - [ ] Return fitted parameters: amplitude, center, alpha, beta
    - [ ] Return fit statistics
  - [ ] Implement `fit_lorentzian_profile()` function (optional)
    - [ ] Fit 1D Lorentzian: `A / (1 + ((x - x0) / gamma)^2)`
  - [ ] Add initial guess estimation (peak finding, width estimation)
  - [ ] Add bounds and constraints for fitting
  - [ ] Handle fitting failures gracefully
  - [ ] Time estimate: (1-2 days)

- [x] **Add profile fitting to API endpoint** (Day 3) (2025-01-27)
  - [ ] Extend `/api/images/{id}/profile` endpoint
  - [ ] Add optional query parameter: `fit_model` (`gaussian`, `moffat`, `lorentzian`, or `none`)
  - [ ] If `fit_model` is specified, perform fitting on extracted profile
  - [ ] Return fit results in response:
    ```json
    {
      "profile_type": "line",
      "distance": [...],
      "flux": [...],
      "error": [...],
      "fit": {
        "model": "gaussian",
        "parameters": {
          "amplitude": 0.5,
          "center": 2.3,
          "sigma": 1.2,
          "fwhm": 2.83
        },
        "statistics": {
          "chi_squared": 0.05,
          "reduced_chi_squared": 0.01,
          "r_squared": 0.98
        },
        "fitted_flux": [...]
      }
    }
    ```
  - [ ] Time estimate: (0.5 day)

**Files to modify:**
- `src/dsa110_contimg/utils/profiling.py` (modify)
- `src/dsa110_contimg/api/routes.py` (modify)

**Acceptance criteria:**
- Fitting functions work correctly for Gaussian and Moffat models
- Fit parameters are physically reasonable
- Fit statistics are calculated correctly
- API returns fit results when requested

---

### Task 2.3: Frontend Profile Plotting Component ✅

- [x] **Create ProfilePlot component** (Day 3-4) (2025-01-27)
  - [ ] Create `frontend/src/components/Sky/ProfilePlot.tsx`
  - [ ] Use Plotly.js or Recharts for plotting
  - [ ] Display profile data:
    - X-axis: Distance (arcsec or pixels)
    - Y-axis: Flux (Jy/beam)
    - Error bars if available
  - [ ] Display fitted model overlay if fit data is present
  - [ ] Add interactive features:
    - Zoom, pan
    - Hover tooltips showing exact values
    - Toggle between raw profile and fitted model
  - [ ] Display fit parameters and statistics in a panel
  - [ ] Add export functionality (PNG, CSV)
  - [ ] Time estimate: (1-2 days)

- [x] **Create ProfileTool component** (Day 4) (2025-01-27)
  - [ ] Create `frontend/src/components/Sky/ProfileTool.tsx`
  - [ ] Add UI controls:
    - Profile type selector (line, polyline, point)
    - "Draw Profile" button
    - "Clear Profile" button
    - Fit model selector (none, Gaussian, Moffat)
    - "Extract Profile" button
  - [ ] Integrate with JS9 for drawing:
    - Use JS9's drawing capabilities or custom overlay
    - Allow user to click/drag to define profile path
    - Visual feedback during drawing
  - [ ] Handle coordinate conversion (pixel ↔ WCS)
  - [ ] Call profile API endpoint when "Extract Profile" is clicked
  - [ ] Display ProfilePlot component with results
  - [ ] Time estimate: (1 day)

**Files to create:**
- `frontend/src/components/Sky/ProfilePlot.tsx` (new)
- `frontend/src/components/Sky/ProfileTool.tsx` (new)

**Acceptance criteria:**
- Users can draw profiles on JS9 image
- Profile data is displayed in an interactive plot
- Fitted models overlay correctly on profile data
- Fit parameters are clearly displayed

---

### Task 2.4: Integrate Profile Tool into SkyViewer ✅

- [x] **Integrate ProfileTool into SkyViewPage** (Day 5) (2025-01-27)
  - [ ] Modify `frontend/src/pages/SkyViewPage.tsx`
  - [ ] Add ProfileTool component to the UI
  - [ ] Position appropriately (sidebar or toolbar)
  - [ ] Ensure proper state management
  - [ ] Test integration with existing components
  - [ ] Time estimate: (0.5 day)

- [x] **Add React Query hooks for profile API** (Day 5) (2025-01-27)
  - [ ] Modify `frontend/src/api/queries.ts`
  - [ ] Add `useProfileExtraction()` hook
    - [ ] Accept image ID, profile type, coordinates, fit model
    - [ ] Call `/api/images/{id}/profile` endpoint
    - [ ] Handle loading and error states
  - [ ] Add proper TypeScript types in `frontend/src/api/types.ts`
  - [ ] Time estimate: (0.5 day)

- [x] **JS9 Drawing Integration** (Day 5) (2025-01-27)
  - [x] Implement click handlers on JS9 canvas
  - [x] Capture pixel coordinates and convert to WCS
  - [x] Visualize profile path with JS9 overlays
  - [x] Support line, polyline, and point profile drawing
  - [x] Add radius dialog for point profiles

- [x] **Export Functionality** (Day 5) (2025-01-27)
  - [x] Add CSV export for profile data
  - [x] Export includes distance, flux, and error columns

- [ ] **Testing and refinement** (Day 5) - Ready for testing
  - [ ] Test with various image sizes
  - [ ] Test with different profile types
  - [ ] Test fitting with various source types
  - [ ] Verify coordinate systems work correctly
  - [ ] Fix any bugs or UI issues
  - [ ] Time estimate: (0.5 day)

**Files to modify:**
- `frontend/src/pages/SkyViewPage.tsx` (modify)
- `frontend/src/api/queries.ts` (modify)
- `frontend/src/api/types.ts` (modify)

**Acceptance criteria:**
- Profile tool is accessible from Sky View page
- Integration works smoothly with existing components
- No conflicts with catalog overlay or region tools

---

## Week 6-7: Image Fitting (Optional) ✅

### Task 2.5: Backend Image Fitting API ✅

- [x] **Create image fitting utility module** (Day 1-2) (2025-01-27)
  - [x] Create `src/dsa110_contimg/utils/fitting.py`
  - [x] Implement `fit_2d_gaussian()` function
    - [ ] Use `astropy.modeling.fitting` or `scipy.optimize`
    - [ ] Fit 2D Gaussian: `A * exp(-0.5 * (a*(x-x0)^2 + 2*b*(x-x0)*(y-y0) + c*(y-y0)^2))`
    - [ ] Return fitted parameters: amplitude, center (x, y), major/minor axes, PA
    - [ ] Return fit statistics and residuals
  - [ ] Implement `fit_2d_moffat()` function
    - [ ] Fit 2D Moffat profile
    - [ ] Return fitted parameters
  - [ ] Implement initial guess estimation:
    - [ ] Peak finding (maximum pixel)
    - [ ] Width estimation (moment-based or FWHM)
    - [ ] Background estimation (median or percentile)
  - [ ] Add support for fitting within a region (use region mask)
  - [ ] Add support for multiple sources (simultaneous fitting)
  - [ ] Time estimate: (2-3 days)

- [x] **Create image fitting API endpoint** (Day 3) (2025-01-27)
  - [ ] Add `/api/images/{id}/fit` endpoint to `src/dsa110_contimg/api/routes.py`
  - [ ] Accept query parameters:
    - `model`: `gaussian` or `moffat` (required)
    - `region_id`: Optional region ID to fit within
    - `initial_guess`: Optional JSON with initial parameters
    - `fit_background`: Boolean (default: true)
  - [ ] Validate input parameters
  - [ ] Resolve image path
  - [ ] Extract region mask if region_id provided
  - [ ] Call fitting function
  - [ ] Return JSON response:
    ```json
    {
      "model": "gaussian",
      "parameters": {
        "amplitude": 0.5,
        "center": {"x": 100.5, "y": 200.3, "ra": 12.34, "dec": 56.78},
        "major_axis": 2.5,
        "minor_axis": 2.0,
        "pa": 45.0,
        "background": 0.01
      },
      "statistics": {
        "chi_squared": 0.05,
        "reduced_chi_squared": 0.01,
        "r_squared": 0.98
      },
      "residuals": {
        "mean": 0.001,
        "std": 0.01,
        "max": 0.05
      }
    }
    ```
  - [ ] Time estimate: (1 day)

**Files to create/modify:**
- `src/dsa110_contimg/utils/fitting.py` (new)
- `src/dsa110_contimg/api/routes.py` (modify)

**Acceptance criteria:**
- API endpoint accepts valid fitting requests
- Returns correct fitted parameters for 2D models
- Handles region constraints correctly
- Error messages are clear

---

### Task 2.6: Frontend Fitting Visualization ✅

- [x] **Create FittingVisualization component** (Day 4-5) (2025-01-27)
  - [ ] Create `frontend/src/components/Sky/FittingVisualization.tsx`
  - [ ] Display fitted model overlay on JS9 image:
    - Draw fitted ellipse (for Gaussian) or shape (for Moffat)
    - Show center point
    - Show major/minor axes
    - Show position angle
  - [ ] Display residuals image overlay (optional)
  - [ ] Add toggle to show/hide fitted model
  - [ ] Add color coding for fit quality
  - [ ] Time estimate: (1-2 days)

- [x] **Create ImageFittingTool component** (Day 5-6) (2025-01-27)
  - [ ] Create `frontend/src/components/Sky/ImageFittingTool.tsx`
  - [ ] Add UI controls:
    - Model selector (Gaussian, Moffat)
    - Region selector (use existing RegionList)
    - "Fit" button
    - "Clear Fit" button
  - [ ] Display fit results panel:
    - Fitted parameters (amplitude, center, size, PA)
    - Fit statistics
    - Residuals statistics
  - [ ] Integrate with FittingVisualization component
  - [ ] Add export functionality (fit parameters as JSON)
  - [ ] Time estimate: (1-2 days)

- [x] **Integrate into SkyViewPage** (Day 7) (2025-01-27)
  - [ ] Add ImageFittingTool to SkyViewPage
  - [ ] Add React Query hooks for fitting API
  - [ ] Test integration
  - [ ] Time estimate: (0.5 day)

**Files to create:**
- `frontend/src/components/Sky/FittingVisualization.tsx` (new)
- `frontend/src/components/Sky/ImageFittingTool.tsx` (new)

**Files to modify:**
- `frontend/src/pages/SkyViewPage.tsx` (modify)
- `frontend/src/api/queries.ts` (modify)
- `frontend/src/api/types.ts` (modify)

**Acceptance criteria:**
- Users can fit 2D models to sources in images
- Fitted models are visualized on the image
- Fit parameters are clearly displayed
- Integration works with region tools

---

## Summary

**Phase 2 Deliverables:**
1. ✅ Spatial Profiler (Week 5)
   - Backend profile extraction API
   - Backend profile fitting (Gaussian, Moffat)
   - Frontend profile plotting component
   - Frontend profile tool integration

2. ✅ Image Fitting (Weeks 6-7) - Complete
   - Backend image fitting API
   - Frontend fitting visualization
   - Integration with region tools

**Total Time Estimate:**
- Week 5 (Spatial Profiler): 5 days
- Weeks 6-7 (Image Fitting): 7 days (optional)

**Dependencies:**
- Phase 1 must be complete (JS9 integration, region management)
- Requires `scipy` and `astropy.modeling` packages
- Requires Plotly.js or Recharts for frontend plotting

**Next Steps After Phase 2:**
- Phase 3: Performance Optimization (Progressive Image Loading)
- Consider Phase 2.5: Catalog interaction improvements (click-to-info, filtering)

