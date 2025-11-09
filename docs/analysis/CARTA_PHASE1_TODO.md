# CARTA Integration - Phase 1 TODO (Working Document)

**Phase:** Core Visualization Improvements (Weeks 1-4)  
**Status:** Core Implementation Complete  
**Started:** 2025-01-XX  
**Completed:** 2025-01-XX  
**Reference:** `docs/analysis/CARTA_INTEGRATION_ASSESSMENT.md`  
**Completion Summary:** `docs/analysis/CARTA_PHASE1_COMPLETION.md`

---

## Week 1: Complete JS9 Integration

### Task 1.1: Debug and Fix JS9 Image Loading ✅
- [x] **Investigate current JS9 loading issues** (2025-01-XX)
  - [ ] Review `frontend/src/components/Sky/SkyViewer.tsx` implementation
  - [ ] Check browser console for errors when loading images
  - [ ] Verify JS9 library is properly loaded (check `window.JS9` availability)
  - [ ] Test image loading with sample FITS files
  - [ ] Document specific error messages and failure modes

- [x] **Fix FITS file serving endpoint** (2025-01-XX)
  - [x] Review `/api/images/{id}/fits` endpoint in `src/dsa110_contimg/api/routes.py`
  - [x] Verify endpoint correctly serves FITS files
  - [x] Check CORS headers if needed
  - [ ] Test endpoint with curl/Postman (pending testing)
  - [x] Ensure proper Content-Type headers (`application/fits` or `image/fits`)

- [x] **Fix CASA image → FITS conversion** (2025-01-XX)
  - [x] Review `src/dsa110_contimg/api/image_utils.py` conversion logic
  - [x] Fixed HTTPException import issue
  - [ ] Test conversion with sample CASA images (pending testing)
  - [x] Verify FITS headers are correct (WCS, beam info, etc.)
  - [x] Check file permissions and path handling
  - [x] Add error handling for conversion failures

- [ ] **Test with various image sizes and formats**
  - [ ] Test with small images (<10 MB)
  - [ ] Test with large images (>100 MB)
  - [ ] Test with PB-corrected images
  - [ ] Test with residual images
  - [ ] Verify performance is acceptable

**Files to modify:**
- `frontend/src/components/Sky/SkyViewer.tsx`
- `src/dsa110_contimg/api/routes.py`
- `src/dsa110_contimg/api/image_utils.py`

**Acceptance criteria:**
- Images load successfully in JS9 viewer
- No console errors
- Loading indicators work correctly
- Error messages are user-friendly

---

### Task 1.2: Implement Image Controls

- [ ] **Go To Coordinates functionality**
  - [ ] Add coordinate input UI (RA/Dec text fields or picker)
  - [ ] Add "Go To" button
  - [ ] Implement coordinate conversion (RA/Dec → pixel coordinates)
  - [ ] Use JS9 API to pan to coordinates (`JS9.SetPan`)
  - [ ] Validate coordinate input format
  - [ ] Handle coordinate system conversions (J2000, etc.)

- [ ] **Load Image button functionality**
  - [ ] Add file browser or image selector dropdown
  - [ ] Query `/api/images` endpoint for available images
  - [ ] Display image list with metadata (timestamp, field, noise)
  - [ ] On selection, load image via JS9.Load
  - [ ] Update image browser to show selected image

- [ ] **Zoom controls**
  - [ ] Add Zoom In button (connect to `JS9.SetZoom`)
  - [ ] Add Zoom Out button
  - [ ] Add Zoom Reset button (zoom to fit)
  - [ ] Add zoom level display
  - [ ] Test zoom performance with large images

- [ ] **Colormap selector**
  - [ ] Add colormap dropdown (grey, hot, cool, rainbow, etc.)
  - [ ] Connect to JS9 colormap API (`JS9.SetColormap`)
  - [ ] Store user preference in localStorage
  - [ ] Apply saved preference on image load

- [ ] **Grid toggle**
  - [ ] Add grid toggle button
  - [ ] Use JS9 grid overlay (`JS9.SetGrid`)
  - [ ] Toggle grid on/off
  - [ ] Style grid appropriately (WCS grid lines)

- [ ] **Catalog overlay toggle** (preview for Phase 1.2)
  - [ ] Add catalog overlay toggle button (disabled initially)
  - [ ] Prepare UI structure for Phase 1.2 integration
  - [ ] Add placeholder handler

**Files to modify:**
- `frontend/src/components/Sky/SkyViewer.tsx`
- `frontend/src/components/Sky/ImageControls.tsx` (new component)
- `frontend/src/pages/SkyViewPage.tsx`

**Acceptance criteria:**
- All controls work correctly
- UI is intuitive and responsive
- Controls persist user preferences
- No performance degradation

---

### Task 1.3: Add Image Metadata Display

- [ ] **Display beam parameters**
  - [ ] Extract beam info from FITS header or image metadata
  - [ ] Display: major axis, minor axis, position angle
  - [ ] Format: "12.3\" x 11.8\" PA 45°"
  - [ ] Show in sidebar or info panel

- [ ] **Display noise level**
  - [ ] Extract noise from image metadata or calculate from image
  - [ ] Display in mJy/beam
  - [ ] Format: "0.92 mJy/beam"
  - [ ] Show in info panel

- [ ] **Display WCS information**
  - [ ] Extract WCS from FITS header
  - [ ] Display: RA/Dec center, pixel scale, coordinate system
  - [ ] Format: "Center: 12:34:56.7, +42:03:12 (J2000)"
  - [ ] Show pixel scale: "0.5\"/pixel"

- [ ] **Display observation metadata**
  - [ ] Extract MJD from FITS header or database
  - [ ] Display integration time if available
  - [ ] Display observation timestamp (UTC)
  - [ ] Format: "Observed: 2025-01-15 13:28:03 UTC (MJD 60240.56)"

- [ ] **Cursor position display**
  - [ ] Track mouse position over image
  - [ ] Convert pixel coordinates to RA/Dec using WCS
  - [ ] Display: pixel (x, y), RA/Dec, flux value at cursor
  - [ ] Update in real-time as cursor moves
  - [ ] Format: "Pixel: (512, 384) | RA: 12:34:56.7, Dec: +42:03:12 | Flux: 0.45 mJy/beam"

**Files to modify:**
- `frontend/src/components/Sky/SkyViewer.tsx`
- `frontend/src/components/Sky/ImageMetadata.tsx` (new component)
- `src/dsa110_contimg/api/image_utils.py` (metadata extraction)

**Acceptance criteria:**
- All metadata displays correctly
- Cursor position updates smoothly
- WCS transformations are accurate
- Metadata is readable and well-formatted

---

## Week 2: Catalog Overlay

### Task 2.1: Backend - Catalog Overlay API Endpoint

- [ ] **Design API endpoint**
  - [ ] Define endpoint: `GET /api/catalog/overlay`
  - [ ] Define parameters: `ra`, `dec`, `radius` (degrees), `catalog` (nvss/vlass/first/all)
  - [ ] Define response format (JSON with source list)
  - [ ] Document API in docstring

- [ ] **Implement catalog query logic**
  - [ ] Review `src/dsa110_contimg/catalog/query.py` existing functions
  - [ ] Create `query_sources_in_fov()` function
  - [ ] Query `master_sources.sqlite3` for sources within radius
  - [ ] Filter by catalog type if specified
  - [ ] Return source list with: RA, Dec, flux, source_id, catalog_type

- [ ] **Add API endpoint to routes**
  - [ ] Add route handler in `src/dsa110_contimg/api/routes.py`
  - [ ] Add request validation (check parameters)
  - [ ] Add error handling
  - [ ] Add response model (Pydantic)
  - [ ] Test endpoint with sample queries

- [ ] **Add caching**
  - [ ] Implement caching for frequently accessed regions
  - [ ] Use cache key based on ra/dec/radius/catalog
  - [ ] Set appropriate cache TTL (e.g., 1 hour)
  - [ ] Test cache hit/miss behavior

- [ ] **Add performance optimization**
  - [ ] Profile query performance
  - [ ] Add database indexes if needed
  - [ ] Optimize SQL query
  - [ ] Target: <100ms for typical FoV query

**Files to modify:**
- `src/dsa110_contimg/api/routes.py`
- `src/dsa110_contimg/catalog/query.py`
- `src/dsa110_contimg/api/models.py` (response models)

**Acceptance criteria:**
- Endpoint returns correct source list
- Query performance <100ms for typical FoV
- Caching works correctly
- Error handling is robust

---

### Task 2.2: Frontend - Catalog Overlay Rendering

- [ ] **Create CatalogOverlay component**
  - [ ] Create `frontend/src/components/Sky/CatalogOverlay.tsx`
  - [ ] Component accepts: image WCS, catalog data, visibility toggle
  - [ ] Component renders markers on canvas overlay
  - [ ] Handle coordinate transformations (RA/Dec → pixel)

- [ ] **Implement coordinate transformation**
  - [ ] Extract WCS from FITS header (via JS9 or API)
  - [ ] Convert catalog RA/Dec to pixel coordinates
  - [ ] Handle coordinate system conversions
  - [ ] Test transformation accuracy

- [ ] **Implement marker rendering**
  - [ ] Render markers/circles on canvas overlay
  - [ ] Style markers by catalog type (NVSS=blue, VLASS=green, FIRST=red)
  - [ ] Scale marker size by flux (optional, configurable)
  - [ ] Handle marker overlap/clustering
  - [ ] Ensure markers are clickable

- [ ] **Add hover tooltips**
  - [ ] Show tooltip on marker hover
  - [ ] Display: source name, flux, catalog type
  - [ ] Position tooltip near cursor
  - [ ] Style tooltip appropriately

- [ ] **Integrate with SkyViewer**
  - [ ] Add CatalogOverlay component to SkyViewer
  - [ ] Connect catalog toggle button (from Task 1.2)
  - [ ] Fetch catalog data when overlay enabled
  - [ ] Update overlay when image changes
  - [ ] Handle zoom/pan updates (re-render overlay)

**Files to modify:**
- `frontend/src/components/Sky/CatalogOverlay.tsx` (new)
- `frontend/src/components/Sky/SkyViewer.tsx`
- `frontend/src/api/queries.ts` (catalog query hook)

**Acceptance criteria:**
- Catalog overlay renders correctly
- Markers are positioned accurately
- Tooltips work smoothly
- Performance is acceptable (no lag)

---

### Task 2.3: Frontend - Catalog Interaction

- [ ] **Click-to-show-catalog-info**
  - [ ] Add click handler on catalog markers
  - [ ] Display source details in sidebar panel
  - [ ] Show: source name, RA/Dec, flux, catalog type, source ID
  - [ ] Add link to source detail page (if exists)

- [ ] **Highlight selected source**
  - [ ] Highlight clicked marker (change color/size)
  - [ ] Deselect previous selection
  - [ ] Persist selection during zoom/pan

- [ ] **Add filter controls**
  - [ ] Add flux range filter (min/max mJy)
  - [ ] Add catalog type filter (checkboxes: NVSS, VLASS, FIRST)
  - [ ] Update overlay when filters change
  - [ ] Store filter preferences in localStorage

- [ ] **Add catalog table view**
  - [ ] Create catalog table component
  - [ ] Display all sources in current FoV
  - [ ] Make table sortable (by flux, name, etc.)
  - [ ] Link table rows to markers (click row → highlight marker)
  - [ ] Add search/filter in table

**Files to modify:**
- `frontend/src/components/Sky/CatalogOverlay.tsx`
- `frontend/src/components/Sky/CatalogTable.tsx` (new)
- `frontend/src/pages/SkyViewPage.tsx`

**Acceptance criteria:**
- Click interaction works smoothly
- Filtering works correctly
- Table and overlay are synchronized
- UI is intuitive

---

### Task 2.4: Testing & Validation

- [ ] **Test catalog overlay with various image sizes**
  - [ ] Test with small images (<10 MB)
  - [ ] Test with large images (>100 MB)
  - [ ] Test with different FoV sizes
  - [ ] Verify performance is acceptable

- [ ] **Test coordinate transformation accuracy**
  - [ ] Compare pixel coordinates with known sources
  - [ ] Test at different declinations
  - [ ] Verify WCS transformations are correct
  - [ ] Test edge cases (image boundaries, poles)

- [ ] **Test catalog query performance**
  - [ ] Measure query time for various FoV sizes
  - [ ] Test cache hit/miss behavior
  - [ ] Verify performance meets target (<100ms)
  - [ ] Test with large catalogs (10k+ sources)

- [ ] **Test with images at different declinations**
  - [ ] Test at Dec +40° (current pointing)
  - [ ] Test at other declinations if available
  - [ ] Verify coordinate transformations work correctly
  - [ ] Test catalog density variations

**Files to create/modify:**
- `tests/integration/test_catalog_overlay.py` (new)
- `tests/frontend/catalog-overlay.test.tsx` (new)

**Acceptance criteria:**
- All tests pass
- Performance meets targets
- Coordinate transformations are accurate
- No regressions in existing functionality

---

## Weeks 3-4: Region Management

### Task 3.1: Backend - Region Storage API

- [ ] **Design database schema**
  - [ ] Create `regions` table schema
  - [ ] Fields: `id`, `name`, `type` (circle/rectangle/polygon), `coordinates` (JSON), `image_path`, `created_at`, `created_by`
  - [ ] Add indexes for common queries
  - [ ] Create migration script

- [ ] **Implement database migration**
  - [ ] Add migration to `src/dsa110_contimg/database/migrations.py`
  - [ ] Create `regions` table
  - [ ] Add indexes
  - [ ] Test migration up/down

- [ ] **Create region storage API endpoints**
  - [ ] `GET /api/regions` - List regions (with filters: image_path, type)
  - [ ] `POST /api/regions` - Create region
  - [ ] `GET /api/regions/{id}` - Get region details
  - [ ] `PUT /api/regions/{id}` - Update region
  - [ ] `DELETE /api/regions/{id}` - Delete region
  - [ ] Add request/response models (Pydantic)

- [ ] **Add region validation**
  - [ ] Validate coordinates are within image bounds
  - [ ] Validate region type matches coordinates format
  - [ ] Validate JSON structure
  - [ ] Return clear error messages

- [ ] **Add region format conversion**
  - [ ] Support CASA region format (`.crtf`, `.rgn`)
  - [ ] Support DS9 region format (`.reg`)
  - [ ] Support JSON format (internal)
  - [ ] Add conversion utilities

**Files to modify:**
- `src/dsa110_contimg/database/migrations.py`
- `src/dsa110_contimg/api/routes.py`
- `src/dsa110_contimg/api/models.py`
- `src/dsa110_contimg/utils/regions.py` (new)

**Acceptance criteria:**
- Database schema is correct
- API endpoints work correctly
- Validation is robust
- Format conversion works

---

### Task 3.2: Backend - Region Format Parsers

- [ ] **Research existing libraries**
  - [ ] Evaluate `astropy.regions` library
  - [ ] Check if it supports CASA/DS9 formats
  - [ ] Decide: use library or implement custom parsers

- [ ] **Implement CASA region format parser**
  - [ ] Parse `.crtf` format (CASA region text format)
  - [ ] Parse `.rgn` format (CASA region binary format)
  - [ ] Convert to internal JSON format
  - [ ] Handle coordinate systems (pixel, WCS)

- [ ] **Implement DS9 region format parser**
  - [ ] Parse `.reg` format (DS9 region format)
  - [ ] Handle various region types (circle, box, polygon, etc.)
  - [ ] Convert to internal JSON format
  - [ ] Handle coordinate systems

- [ ] **Implement coordinate system conversion**
  - [ ] Convert pixel ↔ WCS coordinates
  - [ ] Handle different coordinate systems (J2000, etc.)
  - [ ] Test conversion accuracy

- [ ] **Add region export functionality**
  - [ ] Export regions to CASA format
  - [ ] Export regions to DS9 format
  - [ ] Export regions to JSON format
  - [ ] Add export endpoint: `GET /api/regions/{id}/export?format=`

**Files to modify:**
- `src/dsa110_contimg/utils/regions.py` (new)
- `src/dsa110_contimg/api/routes.py`

**Acceptance criteria:**
- Parsers handle all common formats
- Coordinate conversions are accurate
- Export functionality works correctly

---

### Task 3.3: Backend - Region-Based Statistics API

- [ ] **Design statistics API**
  - [ ] Endpoint: `GET /api/regions/{id}/statistics`
  - [ ] Calculate: mean, RMS, peak, sum, pixel count
  - [ ] Return statistics in JSON format

- [ ] **Implement statistics calculation**
  - [ ] Load image data (FITS or CASA)
  - [ ] Extract pixels within region
  - [ ] Calculate statistics (mean, RMS, peak, sum, count)
  - [ ] Handle edge cases (empty region, out of bounds)

- [ ] **Add ensemble statistics**
  - [ ] Support multiple regions: `POST /api/regions/statistics`
  - [ ] Calculate statistics for each region
  - [ ] Calculate ensemble statistics (mean of means, etc.)
  - [ ] Return combined results

- [ ] **Add region-based photometry**
  - [ ] Calculate integrated flux within region
  - [ ] Calculate peak flux within region
  - [ ] Calculate flux error (from noise map if available)
  - [ ] Return photometry results

**Files to modify:**
- `src/dsa110_contimg/api/routes.py`
- `src/dsa110_contimg/utils/regions.py`

**Acceptance criteria:**
- Statistics are calculated correctly
- Performance is acceptable
- Error handling is robust

---

### Task 3.4: Frontend - Region Drawing Tools

- [ ] **Create RegionTools component**
  - [ ] Create `frontend/src/components/Sky/RegionTools.tsx`
  - [ ] Add toolbar with drawing tools (circle, rectangle, polygon)
  - [ ] Add tool selection state
  - [ ] Style toolbar appropriately

- [ ] **Implement circle tool**
  - [ ] Click to set center
  - [ ] Drag to set radius
  - [ ] Show preview circle while dragging
  - [ ] Create region on mouse up
  - [ ] Store region coordinates

- [ ] **Implement rectangle tool**
  - [ ] Click to set first corner
  - [ ] Drag to set opposite corner
  - [ ] Show preview rectangle while dragging
  - [ ] Create region on mouse up
  - [ ] Store region coordinates

- [ ] **Implement polygon tool**
  - [ ] Click to add vertices
  - [ ] Show preview polygon
  - [ ] Double-click or button to close polygon
  - [ ] Create region on close
  - [ ] Store region coordinates

- [ ] **Add region editing**
  - [ ] Select region (click on region)
  - [ ] Move region (drag)
  - [ ] Resize region (drag handles)
  - [ ] Delete region (keyboard or button)
  - [ ] Update region via API

- [ ] **Add region naming/labeling**
  - [ ] Prompt for region name on creation
  - [ ] Display region name/label on region
  - [ ] Edit region name
  - [ ] Store name in database

**Files to modify:**
- `frontend/src/components/Sky/RegionTools.tsx` (new)
- `frontend/src/components/Sky/SkyViewer.tsx`
- `frontend/src/api/queries.ts` (region API hooks)

**Acceptance criteria:**
- Drawing tools work smoothly
- Regions are created correctly
- Editing is intuitive
- Performance is acceptable

---

### Task 3.5: Frontend - Region Management UI

- [ ] **Create RegionList component**
  - [ ] Create `frontend/src/components/Sky/RegionList.tsx`
  - [ ] Display list of regions for current image
  - [ ] Show region name, type, creation date
  - [ ] Make list sortable/filterable

- [ ] **Add region visibility toggle**
  - [ ] Toggle region visibility on/off
  - [ ] Update overlay when visibility changes
  - [ ] Store visibility state

- [ ] **Add region color/style customization**
  - [ ] Allow user to set region color
  - [ ] Allow user to set line style (solid, dashed, etc.)
  - [ ] Allow user to set line width
  - [ ] Store preferences in database

- [ ] **Add region import/export**
  - [ ] Add import button (file picker)
  - [ ] Parse imported file (CASA/DS9 format)
  - [ ] Add regions to current image
  - [ ] Add export button
  - [ ] Export regions in selected format

- [ ] **Add region-based photometry display**
  - [ ] Show statistics in sidebar when region selected
  - [ ] Display: mean, RMS, peak, sum, pixel count
  - [ ] Display photometry results if available
  - [ ] Update statistics when region changes

**Files to modify:**
- `frontend/src/components/Sky/RegionList.tsx` (new)
- `frontend/src/pages/SkyViewPage.tsx`
- `frontend/src/components/Sky/SkyViewer.tsx`

**Acceptance criteria:**
- Region list displays correctly
- Import/export works
- Statistics display correctly
- UI is intuitive

---

### Task 3.6: Integration - Region-Based Photometry

- [ ] **Update photometry API**
  - [ ] Add region ID parameter to photometry endpoints
  - [ ] Support region-based photometry (in addition to catalog-based)
  - [ ] Calculate photometry within region
  - [ ] Return photometry results

- [ ] **Update photometry workflow**
  - [ ] Allow selecting reference source regions
  - [ ] Allow selecting target source regions
  - [ ] Update normalization to use region-based measurements
  - [ ] Store region associations in photometry database

- [ ] **Update database schema**
  - [ ] Add `region_id` column to `photometry_timeseries` table
  - [ ] Create migration
  - [ ] Update queries to support region-based photometry

- [ ] **Add UI for region-based photometry**
  - [ ] Add region selection to photometry workflow
  - [ ] Display region-based photometry results
  - [ ] Allow comparing region-based vs catalog-based photometry

**Files to modify:**
- `src/dsa110_contimg/photometry/forced.py`
- `src/dsa110_contimg/api/routes.py`
- `src/dsa110_contimg/database/migrations.py`
- `frontend/src/components/Photometry/` (new or existing)

**Acceptance criteria:**
- Region-based photometry works correctly
- Results are stored in database
- UI supports region selection
- Integration is seamless

---

### Task 3.7: Testing & Validation

- [ ] **Test region format parsing**
  - [ ] Test CASA format parsing
  - [ ] Test DS9 format parsing
  - [ ] Test coordinate transformations
  - [ ] Test edge cases (invalid formats, etc.)

- [ ] **Test coordinate transformations**
  - [ ] Test pixel ↔ WCS conversions
  - [ ] Verify accuracy with known coordinates
  - [ ] Test at different declinations
  - [ ] Test edge cases (image boundaries)

- [ ] **Test region statistics accuracy**
  - [ ] Compare statistics with known values
  - [ ] Test with different region types
  - [ ] Test with empty regions
  - [ ] Test with regions outside image bounds

- [ ] **Test region-based photometry workflow**
  - [ ] Test reference source selection
  - [ ] Test target source selection
  - [ ] Test normalization with region-based measurements
  - [ ] Compare results with catalog-based photometry

**Files to create/modify:**
- `tests/integration/test_regions.py` (new)
- `tests/frontend/regions.test.tsx` (new)

**Acceptance criteria:**
- All tests pass
- Statistics are accurate
- Workflow is functional
- No regressions

---

## Phase 1 Summary

**Total Tasks:** 20 major tasks across 3 weeks  
**Key Deliverables:**
1. Fully functional JS9 image viewer
2. Catalog overlay with interaction
3. Region management system
4. Region-based photometry integration

**Success Criteria:**
- All image controls work correctly
- Catalog overlay renders accurately
- Regions can be created, edited, and used for photometry
- Performance is acceptable
- No regressions in existing functionality

---

## Notes

- Work through tasks sequentially within each week
- Test each task before moving to next
- Update this document as tasks are completed
- Document any issues or blockers encountered
- Keep detailed commit messages for each change

