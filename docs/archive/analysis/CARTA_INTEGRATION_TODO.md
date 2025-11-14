# CARTA Integration TODO List

**Based on:** `docs/analysis/CARTA_INTEGRATION_ASSESSMENT.md`  
**Strategy:** Borrow algorithms and patterns from CARTA, reimplement in DSA-110 stack  
**Last Updated:** 2025-11-12

---

## High Priority - Core Visualization Improvements

### Phase 1: Complete JS9 Integration (Week 1)

- [ ] **Fix JS9 Image Loading Issues**
  - [ ] Debug and fix image loading in `SkyViewer.tsx`
  - [ ] Ensure FITS file serving endpoint (`/api/images/{id}/fits`) works correctly
  - [ ] Verify CASA image → FITS conversion pipeline
  - [ ] Add proper error handling for failed image loads
  - [ ] Test with various image sizes and formats
  - Time estimate: (2-3 days)
  - Files: `frontend/src/components/Sky/SkyViewer.tsx`, `src/dsa110_contimg/api/image_utils.py`

- [ ] **Implement Image Controls**
  - [ ] "Go To Coordinates" button functionality (RA/Dec input → pan to coordinates)
  - [ ] "Load Image" button functionality (file browser integration)
  - [ ] Zoom controls (Zoom In/Out/Reset) - connect to JS9 API
  - [ ] Colormap selector (grey, hot, cool, etc.) - connect to JS9
  - [ ] Grid toggle (WCS grid overlay)
  - [ ] Catalog overlay toggle (see Phase 1.2)
  - Time estimate: (2-3 days)
  - Files: `frontend/src/components/Sky/SkyViewer.tsx`

- [ ] **Add Image Metadata Display**
  - [ ] Display beam parameters (major, minor, PA)
  - [ ] Display noise level (mJy/beam)
  - [ ] Display WCS information (RA/Dec center, pixel scale)
  - [ ] Display observation metadata (MJD, integration time)
  - [ ] Add cursor position display (RA/Dec, pixel coordinates, flux value)
  - Time estimate: (1 day)
  - Files: `frontend/src/components/Sky/SkyViewer.tsx`, `frontend/src/pages/SkyViewPage.tsx`

### Phase 2: Catalog Overlay (Week 2)

- [ ] **Backend: Catalog Overlay API Endpoint**
  - [ ] Create `/api/catalog/overlay` endpoint
  - [ ] Accept parameters: `ra`, `dec`, `radius` (degrees), `catalog` (nvss/vlass/first/all)
  - [ ] Query `master_sources.sqlite3` for sources within FoV
  - [ ] Return source list with RA/Dec, flux, source ID
  - [ ] Add caching for frequently accessed regions
  - Time estimate: (1-2 days)
  - Files: `src/dsa110_contimg/api/routes.py`, `src/dsa110_contimg/catalog/query.py`

- [ ] **Frontend: Catalog Overlay Rendering**
  - [ ] Add catalog overlay layer to SkyViewer component
  - [ ] Transform catalog RA/Dec to image pixel coordinates using WCS
  - [ ] Render markers/circles on image canvas (using JS9 overlay or custom canvas)
  - [ ] Style markers by catalog type (NVSS=blue, VLASS=green, FIRST=red)
  - [ ] Scale marker size by flux (optional)
  - [ ] Add hover tooltip showing source info (name, flux, catalog)
  - Time estimate: (2-3 days)
  - Files: `frontend/src/components/Sky/SkyViewer.tsx`, `frontend/src/components/Sky/CatalogOverlay.tsx` (new)

- [ ] **Frontend: Catalog Interaction**
  - [ ] Add click-to-show-catalog-info interaction
  - [ ] Display catalog source details in sidebar panel
  - [ ] Link to source detail page (if exists)
  - [ ] Highlight selected source in overlay
  - [ ] Add filter controls (flux range, catalog type)
  - Time estimate: (1-2 days)
  - Files: `frontend/src/components/Sky/CatalogOverlay.tsx`, `frontend/src/pages/SkyViewPage.tsx`

- [ ] **Testing & Validation**
  - [ ] Test catalog overlay with various image sizes
  - [ ] Test coordinate transformation accuracy
  - [ ] Verify catalog query performance (should be <100ms for typical FoV)
  - [ ] Test with images at different declinations
  - Time estimate: (1 day)

### Phase 3: Region Management (Weeks 3-4)

- [ ] **Backend: Region Storage API**
  - [ ] Create `regions` table in products DB schema
  - [ ] Fields: `id`, `name`, `type` (circle/rectangle/polygon), `coordinates` (JSON), `image_path`, `created_at`, `created_by`
  - [ ] Create `/api/regions` endpoints (GET, POST, PUT, DELETE)
  - [ ] Support region format conversion (CASA, DS9, JSON)
  - [ ] Add region validation (coordinates within image bounds)
  - Time estimate: (2-3 days)
  - Files: `src/dsa110_contimg/database/migrations.py`, `src/dsa110_contimg/api/routes.py`, `src/dsa110_contimg/utils/regions.py` (new)

- [ ] **Backend: Region Format Parsers**
  - [ ] Implement CASA region format parser (`.crtf`, `.rgn`)
  - [ ] Implement DS9 region format parser (`.reg`)
  - [ ] Implement JSON region format (internal)
  - [ ] Add region format conversion utilities
  - [ ] Support coordinate system conversion (pixel ↔ WCS)
  - Time estimate: (2-3 days)
  - Files: `src/dsa110_contimg/utils/regions.py` (new), consider using `astropy.regions` library

- [ ] **Backend: Region-Based Statistics API**
  - [ ] Create `/api/regions/{id}/statistics` endpoint
  - [ ] Calculate statistics within region: mean, RMS, peak, sum, pixel count
  - [ ] Support multiple regions (ensemble statistics)
  - [ ] Add region-based photometry (integrated flux, peak flux)
  - Time estimate: (2 days)
  - Files: `src/dsa110_contimg/api/routes.py`, `src/dsa110_contimg/utils/regions.py`

- [ ] **Frontend: Region Drawing Tools**
  - [ ] Add region drawing toolbar to SkyViewer
  - [ ] Implement circle tool (click center, drag radius)
  - [ ] Implement rectangle tool (click corner, drag opposite corner)
  - [ ] Implement polygon tool (click vertices, double-click to close)
  - [ ] Add region editing (move, resize, delete)
  - [ ] Add region naming/labeling
  - [ ] Store regions in database via API
  - Time estimate: (3-4 days)
  - Files: `frontend/src/components/Sky/SkyViewer.tsx`, `frontend/src/components/Sky/RegionTools.tsx` (new)

- [ ] **Frontend: Region Management UI**
  - [ ] Add region list widget (show all regions for current image)
  - [ ] Add region visibility toggle
  - [ ] Add region color/style customization
  - [ ] Add region import/export (CASA, DS9 formats)
  - [ ] Add region-based photometry display (show statistics in sidebar)
  - Time estimate: (2-3 days)
  - Files: `frontend/src/components/Sky/RegionList.tsx` (new), `frontend/src/pages/SkyViewPage.tsx`

- [ ] **Integration: Region-Based Photometry**
  - [ ] Add region selection to photometry workflow
  - [ ] Allow selecting reference source regions for normalization
  - [ ] Allow selecting target source regions for forced photometry
  - [ ] Update photometry API to accept region IDs
  - [ ] Store region associations in photometry database
  - Time estimate: (2-3 days)
  - Files: `src/dsa110_contimg/photometry/forced.py`, `src/dsa110_contimg/api/routes.py`

- [ ] **Testing & Validation**
  - [ ] Test region format parsing (CASA, DS9)
  - [ ] Test coordinate transformations (pixel ↔ WCS)
  - [ ] Test region statistics accuracy
  - [ ] Test region-based photometry workflow
  - Time estimate: (1-2 days)

---

## Medium Priority - Analysis Tools

### Phase 4: Spatial Profiler (Week 5)

- [ ] **Backend: Profile Extraction API**
  - [ ] Create `/api/images/{id}/profile` endpoint
  - [ ] Accept parameters: `type` (line/polyline), `coordinates` (pixel or WCS)
  - [ ] Extract pixel values along specified path
  - [ ] Return profile data (distance, flux, error)
  - [ ] Support multiple profiles (ensemble)
  - Time estimate: (2 days)
  - Files: `src/dsa110_contimg/api/routes.py`, `src/dsa110_contimg/utils/profiling.py` (new)

- [ ] **Backend: Profile Fitting**
  - [ ] Add profile fitting utilities (Gaussian, Moffat, Lorentzian)
  - [ ] Use `scipy.optimize` or `astropy.modeling` for fitting
  - [ ] Return fitted parameters (amplitude, center, width, etc.)
  - [ ] Return fitting statistics (chi-squared, reduced chi-squared)
  - Time estimate: (2 days)
  - Files: `src/dsa110_contimg/utils/profiling.py`

- [ ] **Frontend: Profile Plotting Component**
  - [ ] Create ProfilePlot component using Plotly.js
  - [ ] Display profile data (distance vs flux)
  - [ ] Overlay fitted model (if fitting performed)
  - [ ] Add interactive features (zoom, pan, hover tooltips)
  - [ ] Add profile smoothing controls (Savitzky-Golay, Gaussian)
  - Time estimate: (2 days)
  - Files: `frontend/src/components/Sky/ProfilePlot.tsx` (new)

- [ ] **Frontend: Profile Tool Integration**
  - [ ] Add profile tool to SkyViewer (draw line/polyline on image)
  - [ ] Extract profile when line drawn
  - [ ] Display profile plot in sidebar or modal
  - [ ] Add fitting controls (select model, fit, view results)
  - [ ] Add profile export (CSV, JSON)
  - Time estimate: (2-3 days)
  - Files: `frontend/src/components/Sky/SkyViewer.tsx`, `frontend/src/components/Sky/ProfilePlot.tsx`

- [ ] **Testing & Validation**
  - [ ] Test profile extraction accuracy
  - [ ] Test profile fitting with known sources
  - [ ] Validate fitted parameters (compare to known source properties)
  - Time estimate: (1 day)

### Phase 5: Image Fitting (Weeks 6-7) - Optional

- [ ] **Backend: Image Fitting API**
  - [ ] Create `/api/images/{id}/fit` endpoint
  - [ ] Accept parameters: `model` (Gaussian/Moffat), `initial_guess` (optional), `region` (optional)
  - [ ] Use `astropy.modeling` for fitting
  - [ ] Return fitted parameters (amplitude, center, size, etc.)
  - [ ] Return fitting statistics and residuals
  - Time estimate: (3-4 days)
  - Files: `src/dsa110_contimg/api/routes.py`, `src/dsa110_contimg/utils/fitting.py` (new)

- [ ] **Backend: Initial Guess Algorithms**
  - [ ] Implement peak finding for initial guess
  - [ ] Implement moment-based estimates (for extended sources)
  - [ ] Add automatic initial guess generation
  - Time estimate: (2 days)
  - Files: `src/dsa110_contimg/utils/fitting.py`

- [ ] **Frontend: Fitting Visualization**
  - [ ] Overlay fitted model on image (contour or ellipse)
  - [ ] Display fitted parameters in sidebar
  - [ ] Display residuals image (optional)
  - [ ] Add fitting controls (select model, set initial guess, fit)
  - Time estimate: (2-3 days)
  - Files: `frontend/src/components/Sky/SkyViewer.tsx`, `frontend/src/components/Sky/FittingPanel.tsx` (new)

- [ ] **Integration: Fitted Photometry**
  - [ ] Add option to use fitted flux instead of peak flux
  - [ ] Store fitted parameters in photometry database
  - [ ] Update photometry API to support fitted photometry
  - Time estimate: (2 days)
  - Files: `src/dsa110_contimg/photometry/forced.py`, `src/dsa110_contimg/database/migrations.py`

---

## Low Priority - Performance Optimization

### Phase 6: Progressive Image Loading (Week 8)

- [ ] **Backend: Tile-Based Image Serving**
  - [ ] Implement image tiling (split large images into tiles)
  - [ ] Create `/api/images/{id}/tiles/{z}/{x}/{y}` endpoint
  - [ ] Generate tiles on-demand or pre-generate
  - [ ] Add tile caching
  - Time estimate: (3-4 days)
  - Files: `src/dsa110_contimg/api/image_utils.py`, `src/dsa110_contimg/utils/tiling.py` (new)

- [ ] **Backend: Low-Resolution Preview**
  - [ ] Generate low-resolution preview images (thumbnail + medium-res)
  - [ ] Serve preview first, then load full resolution
  - [ ] Add preview caching
  - Time estimate: (1-2 days)
  - Files: `src/dsa110_contimg/api/image_utils.py`

- [ ] **Frontend: Progressive Loading**
  - [ ] Load low-res preview first
  - [ ] Load full resolution on demand (zoom in, user request)
  - [ ] Load tiles for large images (zoom/pan)
  - [ ] Add loading indicators
  - Time estimate: (2-3 days)
  - Files: `frontend/src/components/Sky/SkyViewer.tsx`

### Phase 7: WebGL Rendering (Week 9) - Optional

- [ ] **Evaluate WebGL Libraries**
  - [ ] Research `regl` library (lightweight WebGL wrapper)
  - [ ] Research `deck.gl` library (large-scale data visualization)
  - [ ] Evaluate performance vs JS9
  - [ ] Decide on library or custom WebGL implementation
  - Time estimate: (1-2 days)

- [ ] **Implement WebGL Rendering** (if decided)
  - [ ] Replace or supplement JS9 with WebGL rendering
  - [ ] Implement image rendering pipeline
  - [ ] Implement overlay rendering (catalog, regions)
  - [ ] Test performance with large images/mosaics
  - Time estimate: (1-2 weeks, depending on approach)

---

## Documentation & Testing

- [ ] **Update Documentation**
  - [ ] Document catalog overlay usage
  - [ ] Document region management workflow
  - [ ] Document profile tool usage
  - [ ] Add examples and tutorials
  - Time estimate: (2-3 days)
  - Files: `docs/how-to/`, `docs/tutorials/`

- [ ] **Add Integration Tests**
  - [ ] Test catalog overlay API endpoints
  - [ ] Test region management API endpoints
  - [ ] Test profile extraction API endpoints
  - [ ] Test end-to-end workflows (catalog overlay → region selection → photometry)
  - Time estimate: (2-3 days)
  - Files: `tests/integration/`

- [ ] **User Acceptance Testing**
  - [ ] Test with real DSA-110 images
  - [ ] Test with various image sizes and formats
  - [ ] Gather user feedback
  - [ ] Iterate based on feedback
  - Time estimate: (1 week)

---

## Summary

**Total Estimated Time:**
- Phase 1 (JS9 Integration): 1 week
- Phase 2 (Catalog Overlay): 1-2 weeks
- Phase 3 (Region Management): 2-3 weeks
- Phase 4 (Spatial Profiler): 1 week
- Phase 5 (Image Fitting): 2 weeks (optional)
- Phase 6 (Progressive Loading): 1-2 weeks
- Phase 7 (WebGL Rendering): 1-2 weeks (optional)
- Documentation & Testing: 1-2 weeks

**Total: 8-12 weeks for core features (Phases 1-4)**  
**Total: 13-19 weeks including optional features (Phases 5-7)**

**Priority Order:**
1. Phase 1: Complete JS9 Integration (blocking)
2. Phase 2: Catalog Overlay (high value)
3. Phase 3: Region Management (high value)
4. Phase 4: Spatial Profiler (medium value)
5. Phase 5: Image Fitting (low-medium value, optional)
6. Phase 6: Progressive Loading (performance optimization)
7. Phase 7: WebGL Rendering (performance optimization, optional)

---

## Notes

- All implementations should borrow algorithms/patterns from CARTA, not direct code integration (license compatibility)
- Consider using existing libraries where appropriate:
  - `astropy.regions` for region management
  - `astropy.modeling` for image fitting
  - `scipy.optimize` for optimization
  - `plotly.js` for plotting
- Focus on continuum imaging use case (2D images, no spectral dimension)
- Ensure compatibility with existing DSA-110 architecture (FastAPI backend, React frontend)
- Maintain backward compatibility with existing image viewer functionality

