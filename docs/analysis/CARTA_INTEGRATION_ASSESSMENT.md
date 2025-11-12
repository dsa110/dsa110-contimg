# CARTA Integration Assessment for DSA-110 Pipeline

**Date:** 2025-11-12  
**Tool:** CARTA (Cube Analysis and Rendering Tool for Astronomy)  
**Documentation:** https://carta.readthedocs.io/en/latest/

---

## Executive Summary

CARTA is a sophisticated astronomical visualization tool with GPU-accelerated rendering, client-server architecture, and advanced image analysis capabilities. This assessment evaluates which CARTA components could enhance the DSA-110 continuum imaging pipeline, focusing on image visualization, region management, catalog overlays, and analysis tools.

**Key Finding:** CARTA offers several valuable features that could significantly improve DSA-110's image visualization and analysis capabilities, particularly for QA workflows and source inspection. However, direct integration would require significant adaptation due to language differences (CARTA: C++/TypeScript, DSA-110: Python/FastAPI/React).

---

## Current DSA-110 Image Visualization State

### Existing Implementation

**Frontend (`frontend/src/components/Sky/SkyViewer.tsx`):**
- JS9-based FITS image viewer
- Basic image loading and display
- Limited interactivity (zoom, pan, colormap)
- Incomplete integration (image loading issues noted in TBD status)

**Backend (`src/dsa110_contimg/api/image_utils.py`):**
- FITS file serving endpoint (`/api/images/{id}/fits`)
- CASA image to FITS conversion
- Thumbnail generation
- Basic image metadata extraction

**QA Module (`src/dsa110_contimg/qa/`):**
- Image quality metrics (noise, beam, dynamic range)
- Diagnostic plots (calibration quality, flagging statistics)
- QA artifact serving

**Gaps Identified:**
1. Limited image viewer functionality (JS9 integration incomplete)
2. No region of interest (ROI) tools for photometry
3. No catalog overlay capabilities
4. No profile tools (spatial/spectral)
5. No image fitting capabilities
6. No multi-color image blending
7. No contour/vector field rendering

---

## CARTA Features Assessment

### 1. GPU-Accelerated Client-Side Rendering ⭐⭐⭐⭐⭐

**CARTA Capability:**
- GPU-accelerated rendering for large datasets
- Real-time interaction with multi-dimensional data cubes
- Efficient handling of large FITS images

**Relevance for DSA-110:**
- **High Value:** DSA-110 produces continuum images (2D) but could benefit from GPU acceleration for:
  - Large mosaics (60-minute mosaics with many tiles)
  - Multi-epoch image comparison
  - Real-time zoom/pan performance

**Integration Feasibility:**
- **Medium Complexity:** CARTA's rendering is C++/WebGL based
- **Alternative Approach:** Use WebGL libraries directly (e.g., `regl`, `deck.gl`) rather than CARTA's rendering engine
- **Recommendation:** Consider WebGL-based rendering libraries for improved performance, but don't integrate CARTA's rendering engine directly

**Borrowable Pattern:**
- Client-side rendering architecture (separate from server-side processing)
- Progressive image loading (low-res preview → full resolution)
- Tile-based rendering for large images

---

### 2. Region of Interest (ROI) Management ⭐⭐⭐⭐⭐

**CARTA Capability:**
- Shared regions with conserved solid angle
- Region import/export (CASA region format, DS9 format)
- Region annotations
- Analytics with shared regions (statistics, profiles)

**Relevance for DSA-110:**
- **Critical Value:** Essential for photometry workflows:
  - Define reference source regions for normalization
  - Select target source regions for forced photometry
  - Create exclusion regions (bad pixels, artifacts)
  - Region-based statistics (mean, RMS, peak flux)

**Current DSA-110 Gap:**
- Photometry uses catalog positions but no interactive region selection
- No way to visually define reference sources
- No region-based QA tools

**Integration Feasibility:**
- **High Feasibility:** Region management is largely algorithmic (coordinate transformations, statistics)
- **Implementation Approach:**
  1. Add region drawing tools to SkyViewer component (using JS9 or custom canvas)
  2. Store regions in database (`regions` table in products DB)
  3. Support CASA region format for compatibility
  4. Add region-based photometry API endpoints

**Borrowable Components:**
- Region format parsers (CASA, DS9)
- Coordinate system transformations (pixel ↔ WCS)
- Region statistics calculation (mean, RMS, peak within region)
- Region export/import functionality

**Recommendation:** **HIGH PRIORITY** - Implement region management tools, borrowing CARTA's region format support and statistics algorithms.

---

### 3. Catalog Visualization & Overlay ⭐⭐⭐⭐⭐

**CARTA Capability:**
- SIMBAD catalog query
- VizieR catalog query
- Catalog overlay on images (custom mode, angular size mode)
- Linked catalog visualization (catalog table ↔ image overlay)
- Catalog filtering and sorting

**Relevance for DSA-110:**
- **High Value:** Critical for source identification and validation:
  - Overlay NVSS sources on images (already have catalog)
  - Overlay VLASS/FIRST sources for cross-matching
  - Visual verification of photometry measurements
  - Source identification during ESE candidate review

**Current DSA-110 State:**
- Has NVSS/VLASS/FIRST catalog in `master_sources.sqlite3`
- No catalog overlay in image viewer
- Catalog data available via API but not visualized

**Integration Feasibility:**
- **High Feasibility:** Catalog overlay is primarily coordinate transformation + rendering
- **Implementation Approach:**
  1. Add catalog overlay layer to SkyViewer component
  2. Query catalog API for sources within image FoV
  3. Transform catalog RA/Dec to image pixel coordinates
  4. Render markers/circles on image canvas
  5. Add click-to-show-catalog-info interaction

**Borrowable Components:**
- Catalog query patterns (cone search, FoV filtering)
- Overlay rendering techniques (marker styles, size scaling)
- Catalog table ↔ image synchronization patterns

**Recommendation:** **HIGH PRIORITY** - Implement catalog overlay, borrowing CARTA's overlay rendering patterns and catalog query approaches.

---

### 4. Spatial & Spectral Profilers ⭐⭐⭐⭐

**CARTA Capability:**
- Spatial profiler (cursor region, point region, line region, polyline region)
- Spectral profiler (single-profile mode, multiple-profile mode)
- Profile smoothing
- Profile fitting (Gaussian, Lorentzian, etc.)
- Export profiles

**Relevance for DSA-110:**
- **Medium Value:** Useful for source analysis:
  - Spatial profiles for source morphology (point source vs extended)
  - Flux profiles along lines (for extended sources)
  - Profile fitting for source characterization
  - Less critical for continuum imaging (no spectral dimension)

**Current DSA-110 Gap:**
- No profile tools
- Source analysis relies on peak flux measurements only
- No morphological analysis tools

**Integration Feasibility:**
- **Medium Feasibility:** Profile extraction is straightforward (pixel extraction along path)
- **Implementation Approach:**
  1. Add profile extraction API endpoint (extract pixels along line/polyline)
  2. Add profile plotting component (using Plotly.js)
  3. Add profile fitting (Gaussian, Moffat) using scipy
  4. Integrate into SkyViewer as overlay tool

**Borrowable Components:**
- Profile extraction algorithms (line/polyline pixel extraction)
- Profile fitting models (Gaussian, Lorentzian, Moffat)
- Profile smoothing techniques (Savitzky-Golay, Gaussian)

**Recommendation:** **MEDIUM PRIORITY** - Implement spatial profiler for source morphology analysis, especially useful for extended sources and ESE candidate verification.

---

### 5. Image Fitting ⭐⭐⭐

**CARTA Capability:**
- Image fitting (Gaussian, Moffat, etc.)
- Automatic initial guess
- Manual initial guess
- Fitting solvers (Levenberg-Marquardt, etc.)
- Fitting results visualization

**Relevance for DSA-110:**
- **Medium Value:** Could enhance photometry:
  - More accurate flux measurements (fitted flux vs peak flux)
  - Source size estimation (FWHM from Gaussian fit)
  - Deblending of confused sources
  - Less critical if forced photometry at catalog positions is sufficient

**Current DSA-110 State:**
- Uses peak flux at catalog positions (forced photometry)
- No source fitting
- No deblending

**Integration Feasibility:**
- **High Feasibility:** Image fitting is well-established (scipy.optimize, astropy.modeling)
- **Implementation Approach:**
  1. Add image fitting API endpoint (fit Gaussian/Moffat to source)
  2. Integrate astropy.modeling for fitting
  3. Add fitting results to photometry database
  4. Add fitting visualization to SkyViewer

**Borrowable Components:**
- Fitting model definitions (Gaussian, Moffat parameterization)
- Initial guess algorithms (peak finding, moment-based estimates)
- Fitting result visualization patterns

**Recommendation:** **LOW-MEDIUM PRIORITY** - Consider adding image fitting for improved photometry accuracy, especially for extended sources or confused fields.

---

### 6. Multi-Color Image Blending ⭐⭐⭐

**CARTA Capability:**
- Multi-color image blending (RGB composition)
- Layer customization (colormap, scaling per layer)
- Region of interest and annotations on blended images
- Export color-blended images

**Relevance for DSA-110:**
- **Low-Medium Value:** Could be useful for:
  - Multi-epoch comparison (different epochs as RGB channels)
  - Mosaic visualization (different tiles as colors)
  - Less critical for single-epoch continuum imaging

**Current DSA-110 State:**
- Single-epoch images only
- No multi-color blending
- Mosaics are single combined images

**Integration Feasibility:**
- **Medium Feasibility:** Image blending is straightforward (pixel-wise combination)
- **Implementation Approach:**
  1. Add image blending API endpoint (combine multiple images as RGB)
  2. Add blending controls to SkyViewer
  3. Support different colormaps per channel

**Borrowable Components:**
- Blending algorithms (RGB composition, alpha blending)
- Layer management patterns (visibility, opacity, colormap per layer)

**Recommendation:** **LOW PRIORITY** - Consider for future multi-epoch comparison features, but not critical for current continuum imaging workflow.

---

### 7. Contour & Vector Field Rendering ⭐⭐

**CARTA Capability:**
- Contour rendering (multiple levels, smoothing modes)
- Vector field rendering (polarization vectors)
- Matching contours/vectors to raster images

**Relevance for DSA-110:**
- **Low Value:** Less relevant for continuum imaging:
  - Contours useful for source identification but JS9 already supports
  - Vector fields not applicable (no polarization analysis in current pipeline)
  - Could be useful for future polarization analysis

**Recommendation:** **LOW PRIORITY** - Not critical for current workflow, but consider for future polarization analysis features.

---

### 8. Moment Image Generator ⭐⭐

**CARTA Capability:**
- Moment image generation (moment-0, moment-1, moment-2)
- Position-velocity (PV) image generator

**Relevance for DSA-110:**
- **Low Value:** Not applicable to continuum imaging:
  - Moments are for spectral line data (velocity moments)
  - PV diagrams are for spectral line analysis
  - DSA-110 is continuum-only (no spectral dimension)

**Recommendation:** **NOT APPLICABLE** - Skip for continuum imaging pipeline.

---

### 9. Client-Server Architecture ⭐⭐⭐⭐

**CARTA Capability:**
- Separates UI (client) from data processing (server)
- Efficient handling of large datasets
- Distributed processing capabilities

**Relevance for DSA-110:**
- **High Value:** Already partially implemented:
  - FastAPI backend (server)
  - React frontend (client)
  - Could benefit from CARTA's patterns for:
    - Large image streaming (progressive loading)
    - Efficient data transfer (tiles, compression)
    - Server-side image processing (thumbnails, statistics)

**Current DSA-110 State:**
- Client-server architecture exists
- Basic image serving
- Could improve efficiency for large images/mosaics

**Borrowable Patterns:**
- Progressive image loading (low-res → high-res)
- Tile-based image serving for large images
- Server-side image processing (statistics, thumbnails)
- Efficient data transfer (compression, chunking)

**Recommendation:** **MEDIUM PRIORITY** - Adopt CARTA's progressive loading and tile-based serving patterns for improved performance with large mosaics.

---

### 10. HDF5 Support ⭐⭐⭐

**CARTA Capability:**
- Native HDF5 (IDIA schema) image support
- Efficient HDF5 reading for large datasets

**Relevance for DSA-110:**
- **Low Value:** DSA-110 uses:
  - UVH5 input (HDF5 format) - already handled
  - FITS/CASA images output - standard formats
  - No need for HDF5 image format

**Recommendation:** **NOT APPLICABLE** - Skip HDF5 image support, FITS/CASA formats are sufficient.

---

## Integration Recommendations

### High Priority (Implement Soon)

1. **Region of Interest (ROI) Management**
   - **Why:** Critical for photometry workflows (reference source selection, target regions)
   - **Effort:** Medium (2-3 weeks)
   - **Approach:** 
     - Add region drawing tools to SkyViewer
     - Implement region format parsers (CASA, DS9)
     - Add region-based photometry API endpoints
     - Store regions in database

2. **Catalog Overlay**
   - **Why:** Essential for source identification and photometry verification
   - **Effort:** Medium (1-2 weeks)
   - **Approach:**
     - Add catalog overlay layer to SkyViewer
     - Query catalog API for sources in FoV
     - Transform RA/Dec to pixel coordinates
     - Render markers with click-to-info interaction

### Medium Priority (Consider for Next Phase)

3. **Spatial Profiler**
   - **Why:** Useful for source morphology analysis
   - **Effort:** Low-Medium (1 week)
   - **Approach:**
     - Add profile extraction API
     - Add profile plotting component
     - Integrate into SkyViewer

4. **Progressive Image Loading**
   - **Why:** Improve performance with large images/mosaics
   - **Effort:** Medium (1-2 weeks)
   - **Approach:**
     - Implement tile-based image serving
     - Add low-res preview → high-res loading
     - Use WebGL for efficient rendering

### Low Priority (Future Enhancements)

5. **Image Fitting**
   - **Why:** Improve photometry accuracy for extended sources
   - **Effort:** Medium (2 weeks)
   - **Approach:**
     - Add fitting API using astropy.modeling
     - Integrate into photometry pipeline
     - Add fitting visualization

6. **Multi-Color Image Blending**
   - **Why:** Useful for multi-epoch comparison
   - **Effort:** Low (1 week)
   - **Approach:**
     - Add blending API endpoint
     - Add blending controls to SkyViewer

---

## Implementation Strategy

### Phase 1: Core Visualization Improvements (Weeks 1-4)

**Goal:** Enhance current JS9-based viewer with essential features

1. **Complete JS9 Integration** (Week 1)
   - Fix image loading issues
   - Add proper FITS file serving
   - Implement CASA image → FITS conversion

2. **Catalog Overlay** (Week 2)
   - Add catalog query API endpoint (`/api/catalog/overlay?ra=&dec=&radius=`)
   - Add overlay rendering to SkyViewer
   - Add click-to-info interaction

3. **Region Management** (Weeks 3-4)
   - Add region drawing tools (circle, rectangle, polygon)
   - Implement region format parsers (CASA, DS9)
   - Add region storage API (`/api/regions`)
   - Add region-based statistics API

### Phase 2: Analysis Tools (Weeks 5-7)

**Goal:** Add analysis capabilities for source inspection

1. **Spatial Profiler** (Week 5)
   - Add profile extraction API
   - Add profile plotting component
   - Integrate into SkyViewer

2. **Image Fitting** (Weeks 6-7)
   - Add fitting API using astropy.modeling
   - Add fitting visualization
   - Integrate into photometry pipeline (optional)

### Phase 3: Performance Optimization (Weeks 8-9)

**Goal:** Improve performance for large images/mosaics

1. **Progressive Image Loading** (Week 8)
   - Implement tile-based serving
   - Add low-res preview → high-res loading

2. **WebGL Rendering** (Week 9)
   - Evaluate WebGL libraries (regl, deck.gl)
   - Implement WebGL-based rendering for large images

---

## Technical Considerations

### Language Compatibility

**CARTA:** C++ (backend), TypeScript/JavaScript (frontend)  
**DSA-110:** Python (backend), TypeScript/JavaScript (frontend)

**Impact:**
- Cannot directly use CARTA's C++ backend components
- Can borrow algorithms and patterns (reimplement in Python)
- Can use CARTA's TypeScript/JavaScript patterns directly
- CARTA's client-side rendering could be adapted

### License Compatibility

**CARTA:** GNU General Public License version 3 (GPL-3)  
**DSA-110:** Need to verify license compatibility

**Impact:**
- GPL-3 requires derivative works to be GPL-3
- If DSA-110 is not GPL-3, cannot directly integrate CARTA code
- Can still borrow algorithms/patterns (reimplement independently)
- Can use CARTA as inspiration without code integration

**Recommendation:** Focus on borrowing algorithms and patterns rather than direct code integration to avoid license complications.

### Architecture Compatibility

**CARTA:** Standalone application (Electron or web app)  
**DSA-110:** Web-based dashboard (React + FastAPI)

**Impact:**
- CARTA's client-server patterns are compatible
- Can adapt CARTA's UI patterns to React components
- CARTA's server-side patterns can inform FastAPI endpoints

---

## Alternative Approaches

### Option 1: Direct CARTA Integration (Not Recommended)

**Approach:** Run CARTA as separate service, integrate via API

**Pros:**
- Full CARTA functionality available
- No reimplementation needed

**Cons:**
- Additional service to maintain
- License compatibility concerns
- Integration complexity
- Overkill for continuum imaging needs

**Recommendation:** Not recommended - too complex for current needs.

### Option 2: Borrow Patterns & Algorithms (Recommended)

**Approach:** Study CARTA's implementation, reimplement key features in DSA-110 stack

**Pros:**
- No license concerns
- Tailored to DSA-110 needs
- Better integration with existing codebase
- Can optimize for continuum imaging use case

**Cons:**
- Requires development effort
- Need to understand CARTA's algorithms

**Recommendation:** **RECOMMENDED** - Best balance of functionality and maintainability.

### Option 3: Use Alternative Libraries

**Approach:** Use existing JavaScript/Python libraries for similar functionality

**Examples:**
- **Region Management:** `astropy.regions` (Python), `astrojs-regions` (JavaScript)
- **Catalog Overlay:** Custom implementation using D3.js or Leaflet
- **Image Fitting:** `astropy.modeling` (Python), `scipy.optimize` (Python)
- **Profile Tools:** Custom implementation using pixel extraction + Plotly.js

**Recommendation:** Consider for specific features (e.g., astropy.regions for region management).

---

## Conclusion

CARTA offers valuable features that could significantly enhance DSA-110's image visualization and analysis capabilities. The most valuable borrowable components are:

1. **Region Management** - Critical for photometry workflows
2. **Catalog Overlay** - Essential for source identification
3. **Spatial Profiler** - Useful for source morphology analysis
4. **Progressive Loading Patterns** - Improve performance

**Recommended Approach:** Borrow algorithms and patterns from CARTA rather than direct integration, focusing on:
- Region format support (CASA, DS9)
- Catalog overlay rendering patterns
- Profile extraction algorithms
- Progressive image loading strategies

**Priority Implementation:**
1. Complete JS9 integration (fix current issues)
2. Add catalog overlay (high value, medium effort)
3. Add region management (high value, medium effort)
4. Add spatial profiler (medium value, low effort)

This approach provides the benefits of CARTA's features while maintaining DSA-110's architecture and avoiding license complications.

---

## References

- CARTA Documentation: https://carta.readthedocs.io/en/latest/
- CARTA GitHub: (search for repository)
- DSA-110 Frontend Design: `docs/concepts/frontend_design.md`
- DSA-110 SkyView Implementation: `frontend/src/components/Sky/SkyViewer.tsx`
- DSA-110 QA Module: `src/dsa110_contimg/qa/`

