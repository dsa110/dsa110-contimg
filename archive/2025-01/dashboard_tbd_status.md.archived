# Dashboard TBD (To Be Done) Status

## Summary

This document outlines all parts of the dashboard that are still incomplete, use mock data, or are marked as placeholders.

---

## 1. SkyView Page (Partially Complete)

**Status**: Foundation implemented, core functionality TBD

### Completed ✅
- JS9 library included via CDN in `index.html`
- `ImageBrowser` component - Browse and filter images
- `SkyViewer` component - Basic JS9 integration structure
- `/api/images` endpoint - Lists images from products database
- Image filtering and selection UI

### TBD / Incomplete ❌

#### Core Functionality
1. **JS9 Integration Not Complete**
   - JS9 display initialization works but image loading is incomplete
   - FITS file serving endpoint missing (`/api/files/{path}`)
   - CASA image to FITS conversion not implemented
   - Image loading error handling needs improvement

2. **Image Controls Not Functional**
   - "Go To Coordinates" button - No functionality
   - "Load Image" button - No functionality
   - Zoom controls (Zoom In/Out/Reset) - Placeholder buttons
   - Colormap selector - Placeholder button
   - Grid toggle - Placeholder button
   - Catalog overlay - Placeholder button

3. **Missing Features**
   - Coordinate navigation (RA/Dec input)
   - Image metadata display (beam, noise, WCS info)
   - Catalog overlays (NVSS, VLASS)
   - Measurement tools (cursor position, flux measurement)
   - Region selection tools
   - Export functionality (PNG, FITS download)

4. **Backend Requirements**
   - FITS file serving endpoint (`/api/files/{path}`)
   - CASA image to FITS conversion service
   - Catalog query endpoints
   - Image metadata extraction from FITS headers

**Location**: `frontend/src/pages/SkyViewPage.tsx` (still shows placeholder UI)

---

## 2. Mosaic Gallery Page (Uses Mock Data)

**Status**: UI complete, backend uses mock data

### Completed ✅
- Time range query interface
- Mosaic card display
- Status indicators
- Create mosaic button

### TBD / Incomplete ❌

1. **Backend Endpoints Use Mock Data**
   - `/api/mosaics/query` - Returns `generate_mock_mosaics()`
   - `/api/mosaics/create` - Returns mock response
   - No actual mosaic generation pipeline integration

2. **Missing Functionality**
   - "View" button - No navigation to SkyView
   - "FITS" download button - No file serving
   - "PNG" download button - No image conversion
   - Thumbnail generation - Uses placeholder if no thumbnail_path

3. **Backend Requirements**
   - Real mosaic query from database
   - Mosaic generation pipeline integration
   - Thumbnail generation service
   - File serving for FITS/PNG downloads

**Location**: 
- Frontend: `frontend/src/pages/MosaicGalleryPage.tsx`
- Backend: `src/dsa110_contimg/api/routes.py:595-610` (uses `generate_mock_mosaics`)

---

## 3. Source Monitoring Page (Uses Mock Data)

**Status**: UI complete, backend uses mock data

### Completed ✅
- AG Grid table implementation
- Source search interface
- Column definitions (RA, Dec, flux, variability)
- Pagination and filtering UI

### TBD / Incomplete ❌

1. **Backend Endpoint Uses Mock Data**
   - `/api/sources/search` - Returns `generate_mock_source_timeseries()`
   - No real source database integration
   - No flux timeseries calculation

2. **Missing Functionality**
   - Source search - No real catalog matching
   - Flux timeseries - No historical data
   - Variability detection - No statistical analysis
   - Source details - No drill-down view

3. **Backend Requirements**
   - Source catalog database integration
   - Flux timeseries calculation from images
   - Variability detection algorithms
   - Source matching across observations

**Location**:
- Frontend: `frontend/src/pages/SourceMonitoringPage.tsx`
- Backend: `src/dsa110_contimg/api/routes.py:611-620` (uses mock data)

---

## 4. Dashboard Page (Partially Mock)

**Status**: Mostly functional, some mock data

### Completed ✅
- Pipeline status display (real data)
- System metrics (real data)
- Recent observations table (real data)
- ESE Candidates panel

### TBD / Incomplete ❌

1. **ESE Candidates Uses Mock Data**
   - `/api/ese/candidates` - Returns `generate_mock_ese_candidates()`
   - No real ESE detection pipeline integration

2. **Missing Features**
   - Alert history - Uses mock data (`/api/alerts/history`)
   - Real-time alerts - Not implemented
   - Alert filtering and management - Not implemented

**Location**:
- Backend: `src/dsa110_contimg/api/routes.py:587-593` (ESE candidates)
- Backend: `src/dsa110_contimg/api/routes.py:621-626` (Alert history)

---

## 5. Control Page (Functional)

**Status**: ✅ Fully functional

### Completed ✅
- MS list and filtering
- Job creation (calibrate, apply, image, convert)
- Job monitoring with EventSource logs
- Calibration table validation
- Workflow execution
- Batch operations
- UI/UX improvements (tooltips, error handling, keyboard shortcuts)

**No TBD items** - This page is production-ready.

---

## 6. Missing API Endpoints

### FITS File Serving
- **Endpoint**: `/api/files/{path}` (or similar)
- **Purpose**: Serve FITS files for JS9 viewer
- **Status**: ❌ Not implemented
- **Required for**: SkyView page

### Image Metadata Extraction
- **Endpoint**: `/api/images/{id}/metadata` (or enhance existing)
- **Purpose**: Extract WCS, beam, noise from FITS headers
- **Status**: ❌ Partially implemented (basic fields only)
- **Required for**: SkyView metadata display

### Catalog Query Endpoints
- **Endpoints**: `/api/catalogs/nvss`, `/api/catalogs/vlass`
- **Purpose**: Query external catalogs for overlays
- **Status**: ❌ Not implemented
- **Required for**: SkyView catalog overlays

### Mosaic Generation Pipeline
- **Integration**: Connect to actual mosaic generation
- **Status**: ❌ Not integrated
- **Required for**: Mosaic Gallery real data

### Source Timeseries Calculation
- **Endpoint**: Real `/api/sources/search` implementation
- **Purpose**: Calculate flux timeseries from images
- **Status**: ❌ Uses mock data
- **Required for**: Source Monitoring real data

---

## 7. Component Status

### Completed Components ✅
- `MSTable.tsx` - MS list display
- `Navigation.tsx` - Main navigation
- `ErrorBoundary.tsx` - Error handling
- `ESECandidatesPanel.tsx` - ESE display (uses mock data)
- `ImageBrowser.tsx` - Image selection (functional)
- `SkyViewer.tsx` - JS9 wrapper (structure only)

### Incomplete Components ❌
- `SkyViewer.tsx` - Needs FITS loading implementation
- Catalog overlay components - Not created
- Measurement tool components - Not created
- Region selection components - Not created

---

## Priority Recommendations

### High Priority
1. **SkyView Page Core Functionality**
   - Implement FITS file serving endpoint
   - Complete JS9 image loading
   - Make coordinate navigation functional
   - Add image metadata display

2. **Replace Mock Data with Real Endpoints**
   - Mosaic query from database
   - Source timeseries calculation
   - ESE detection pipeline integration

### Medium Priority
3. **SkyView Advanced Features**
   - Catalog overlays
   - Measurement tools
   - Export functionality

4. **Mosaic Gallery Integration**
   - Real mosaic generation
   - Thumbnail generation
   - File downloads

### Low Priority
5. **Source Monitoring Enhancement**
   - Real source matching
   - Historical flux analysis
   - Variability detection algorithms

---

## Files to Review

### Frontend
- `frontend/src/pages/SkyViewPage.tsx` - Placeholder UI
- `frontend/src/pages/MosaicGalleryPage.tsx` - Uses mock data
- `frontend/src/pages/SourceMonitoringPage.tsx` - Uses mock data
- `frontend/src/components/Sky/SkyViewer.tsx` - Incomplete implementation

### Backend
- `src/dsa110_contimg/api/routes.py:587-626` - Mock data endpoints
- `src/dsa110_contimg/api/mock_data.py` - Mock data generators
- Missing: FITS file serving, catalog queries, image metadata extraction

---

## Summary Statistics

- **Fully Functional Pages**: 1 (Control Page)
- **Partially Functional Pages**: 3 (Dashboard, Mosaic Gallery, Source Monitoring)
- **Placeholder Pages**: 1 (SkyView)
- **Mock Data Endpoints**: 4 (`/api/ese/candidates`, `/api/mosaics/*`, `/api/sources/search`, `/api/alerts/history`)
- **Missing Endpoints**: 3+ (FITS serving, catalog queries, enhanced image metadata)

