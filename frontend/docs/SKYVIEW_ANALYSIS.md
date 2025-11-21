# Sky View Page (`/sky`) - Implementation Analysis

**Date:** 2025-11-14  
**Purpose:** Detailed analysis of SkyViewPage implementation vs. documented
features

---

## 1. Components Already Implemented

### Page Component

- **`SkyViewPage.tsx`** (`frontend/src/pages/SkyViewPage.tsx`)
  - Main page component
  - Layout: ImageBrowser sidebar (4 cols) + Main display (8 cols)
  - State management for selected image, catalog overlay, regions

### Sky Components (`frontend/src/components/Sky/`)

#### Image Browser & Selection

- **`ImageBrowser.tsx`** ✅
  - Image list with filters
  - Search by MS path
  - Image type filter (image, pbcor, residual, psf, pb)
  - PB corrected filter (yes/no/all)
  - Displays: timestamp, noise level, beam size
  - Pagination support (limit/offset)

#### Image Display

- **`SkyViewer.tsx`** ✅
  - JS9 FITS viewer integration
  - Display ID: `skyViewDisplay`
  - Height: 600px
  - FITS URL: `/api/images/{image_id}/fits`

- **`ImageControls.tsx`** ✅
  - JS9 control panel (zoom, pan, colormap, scaling)
  - Grid overlay toggle
  - Display ID: `skyViewDisplay`

- **`ImageMetadata.tsx`** ✅
  - Cursor position tracking (pixel, RA/Dec, flux)
  - Image info display:
    - Path, type
    - Noise level (mJy)
    - Beam (major, minor, PA)
  - WCS coordinate display

#### Catalog Features

- **`CatalogOverlayJS9.tsx`** ✅
  - Catalog overlay for JS9 display
  - Uses `useCatalogOverlayByCoords(ra, dec, radius, catalog)`
  - Toggle switch in SkyViewPage
  - Radius: 1.5 degrees
  - Catalog: "all"

- **`CatalogOverlay.tsx`** ✅
  - Alternative catalog overlay (not used in SkyViewPage)
  - Uses `useCatalogOverlay(imageId, catalog, minFluxJy)`

- **`CatalogValidationPanel.tsx`** ✅
  - Catalog validation display
  - Uses `useCatalogValidation(msPath)` and `useRunCatalogValidation()`
  - Not currently used in SkyViewPage

#### Region Management

- **`RegionTools.tsx`** ✅
  - Create/edit regions on image
  - Display ID: `skyViewDisplay`
  - Image path required
  - Callback: `onRegionCreated(region)`

- **`RegionList.tsx`** ✅
  - List regions for image
  - Uses `useRegions(imagePath)`, `useDeleteRegion()`, `useUpdateRegion()`,
    `useRegionStatistics()`
  - Selection support: `onRegionSelect(region)`, `selectedRegionId`

#### Analysis Tools

- **`ProfileTool.tsx`** ✅
  - Profile extraction tool
  - Uses `useProfileExtraction()` mutation
  - Display ID: `skyViewDisplay`
  - Image ID required

- **`ImageFittingTool.tsx`** ✅
  - Image fitting tool
  - Uses `useImageFitting()` mutation
  - Uses `useRegions(imagePath)` for region selection
  - Display ID: `skyViewDisplay`
  - Image ID and path required

- **`FittingVisualization.tsx`** ✅
  - Fitting results visualization
  - Not currently used in SkyViewPage

- **`ProfilePlot.tsx`** ✅
  - Profile plot display
  - Not currently used in SkyViewPage

---

## 2. API Calls Being Made

### Direct API Calls (via React Query Hooks)

#### Image Queries

- **`useImages(filters)`** ✅
  - Endpoint: `GET /api/images`
  - Filters supported:
    - `limit` (default: 50)
    - `offset` (default: 0)
    - `ms_path` (search)
    - `image_type` (image, pbcor, residual, psf, pb)
    - `pbcor` (boolean)
  - Returns: `ImageList` with `items[]` and `total`

#### Catalog Queries

- **`useCatalogOverlayByCoords(ra, dec, radius, catalog)`** ✅
  - Endpoint:
    `GET /api/catalog/overlay?ra={ra}&dec={dec}&radius={radius}&catalog={catalog}`
  - Used in: `CatalogOverlayJS9`
  - Parameters:
    - `ra`: Image center RA (from `selectedImage.center_ra_deg`)
    - `dec`: Image center Dec (from `selectedImage.center_dec_deg`)
    - `radius`: 1.5 degrees
    - `catalog`: "all"

#### Region Queries

- **`useRegions(imagePath)`** ✅
  - Endpoint: `GET /api/regions?image_path={imagePath}`
  - Used in: `RegionList`, `ImageFittingTool`

- **`useCreateRegion()`** ✅ (Mutation)
  - Endpoint: `POST /api/regions`
  - Used in: `RegionTools`

- **`useUpdateRegion()`** ✅ (Mutation)
  - Endpoint: `PUT /api/regions/{region_id}`
  - Used in: `RegionList`

- **`useDeleteRegion()`** ✅ (Mutation)
  - Endpoint: `DELETE /api/regions/{region_id}`
  - Used in: `RegionList`

- **`useRegionStatistics(regionId)`** ✅
  - Endpoint: `GET /api/regions/{region_id}/statistics`
  - Used in: `RegionList`

#### Analysis Mutations

- **`useProfileExtraction()`** ✅ (Mutation)
  - Endpoint: `POST /api/images/{image_id}/profile`
  - Used in: `ProfileTool`

- **`useImageFitting()`** ✅ (Mutation)
  - Endpoint: `POST /api/images/{image_id}/fitting`
  - Used in: `ImageFittingTool`

### Indirect API Calls (via FITS URL)

- **`GET /api/images/{image_id}/fits`** ✅
  - Used by JS9 viewer via `fitsUrl` prop
  - Constructed from: `/api/images/${selectedImage.id}/fits`

### Missing API Calls (Not Used in SkyViewPage)

#### Image Detail

- **`useImageDetail(imageId)`** ❌
  - Endpoint: `GET /api/images/{image_id}`
  - **Status:** Available but not used
  - **Gap:** SkyViewPage uses `selectedImage` from ImageBrowser, but doesn't
    fetch full details

#### Image Measurements

- **`useImageMeasurements(imageId)`** ❌
  - Endpoint: `GET /api/images/{image_id}/measurements`
  - **Status:** Available but not used
  - **Gap:** Source statistics not displayed

#### Mosaic Queries (Separate Page)

- **`useMosaicQuery(request)`** ✅
  - Endpoint: `POST /api/mosaics/query`
  - **Status:** Used in `MosaicGalleryPage.tsx` (separate page)
  - **Gap:** Not integrated into SkyViewPage

- **`useCreateMosaic()`** ✅
  - Endpoint: `POST /api/mosaics/create`
  - **Status:** Used in `MosaicGalleryPage.tsx` (separate page)
  - **Gap:** Not integrated into SkyViewPage

---

## 3. Gaps: Current Code vs. Documentation

### ❌ Missing: Interactive Sky Map

**Documentation Requirements:**

- Observed fields (color-coded by observation time)
- Source density heatmap
- Calibrator positions
- Current/upcoming telescope pointing
- Click field → show observation details
- Zoom and pan controls
- Time range filtering
- Declination range filtering

**Current Status:** 📋 **Not Implemented**

- No sky map component exists
- No coverage visualization
- No heatmap display
- No telescope pointing display

**Gap Analysis:**

- **Component:** No `SkyMap.tsx` or similar component
- **API:** No API calls for field coverage or pointing data
- **Data:** No integration with pointing history or field coverage endpoints

---

### 🔄 Partial: Image Gallery

**Documentation Requirements:**

#### Grid View

- ✅ Thumbnail grid (4-6 images per row, responsive)
- ✅ Each thumbnail shows:
  - ✅ Observation timestamp
  - ❌ Field ID (not displayed)
  - ✅ Noise level
  - ❌ Source count (not displayed)
  - ❌ Calibrator status (not displayed)

**Current Implementation:**

- **`ImageBrowser.tsx`** uses **List** layout (not grid)
- Displays: filename, type chip, PB chip, timestamp, noise, beam
- Missing: Field ID, source count, calibrator status

**Gap Analysis:**

- **Layout:** List view instead of grid thumbnails
- **Data:** `ImageInfo` type may not include `field_id`, `source_count`,
  `calibrator_status`
- **Display:** Missing thumbnail images (only text list)

#### Filters

**Documentation Requirements:**

- ❌ Date range (start/end UTC)
- ❌ Declination range
- ❌ Quality threshold (noise level)
- ✅ Primary-beam corrected flag (`pbcor`)
- ❌ Calibrator detected flag
- ✅ Search by field ID or coordinates (partial: MS path search only)

**Current Implementation:**

- ✅ Image type filter (`image_type`)
- ✅ PB corrected filter (`pbcor`)
- ✅ MS path search (`ms_path`)
- ❌ Date range filter (not in `ImageFilters` type)
- ❌ Declination range filter (not in `ImageFilters` type)
- ❌ Quality threshold filter (not in `ImageFilters` type)
- ❌ Calibrator detected filter (not in `ImageFilters` type)
- ❌ Field ID search (not in `ImageFilters` type)
- ❌ Coordinate search (not in `ImageFilters` type)

**Gap Analysis:**

- **Type Definition:** `ImageFilters` interface missing:
  ```typescript
  start_date?: string;
  end_date?: string;
  dec_min?: number;
  dec_max?: number;
  noise_max?: number;  // Quality threshold
  has_calibrator?: boolean;
  field_id?: string;
  center_ra?: number;
  center_dec?: number;
  radius?: number;
  ```

#### Pagination

- ✅ Configurable items per page (`limit`)
- ✅ Page navigation (via `offset`)
- ✅ Total count display

**Status:** ✅ **Fully Implemented**

---

### 🔄 Partial: Image Detail View

**Documentation Requirements:**

#### Full-Resolution Display

- ✅ Large image viewer (JS9 integration)
- ✅ Zoom and pan controls (`ImageControls`)
- ✅ Colormap selection (`ImageControls`)
- ✅ Scaling options (linear, log, sqrt) (`ImageControls`)
- ✅ Grid overlay toggle (`ImageControls`)
- ✅ Catalog overlay toggle (`CatalogOverlayJS9`)

**Status:** ✅ **Fully Implemented**

#### Metadata Panel

**Documentation Requirements:**

**Observation Details:**

- ❌ Date (not displayed in `ImageMetadata`)
- ❌ MJD (not displayed)
- ❌ Integration time (not displayed)

**Pointing Center:**

- ✅ RA/Dec (from `selectedImage.center_ra_deg/dec_deg`, displayed in cursor
  info)

**Field Size:**

- ❌ Field size (not displayed)

**Image Quality Metrics:**

- ✅ Noise level (mJy/beam) - displayed
- ✅ Synthesized beam (major, minor, PA) - displayed
- ❌ Noise/thermal ratio (not displayed)
- ❌ Dynamic range (not displayed)

**Frequency Information:**

- ❌ Center frequency (not displayed)
- ❌ Bandwidth (not displayed)

**Source Statistics:**

- ❌ Detected sources count (not displayed)
- ❌ NVSS matches count (not displayed)
- ❌ Variable sources count (not displayed)

**Calibration Information:**

- ❌ Calibrator name (not displayed)
- ❌ Separation from pointing center (not displayed)
- ❌ Measured vs. expected flux (not displayed)
- ❌ Calibration tables used (not displayed)

**Current Implementation:**

- **`ImageMetadata.tsx`** displays:
  - Path, type
  - Noise level (mJy)
  - Beam (major, minor, PA)
  - Cursor position (pixel, RA/Dec, flux)

**Gap Analysis:**

- **Data Source:** `ImageInfo` type may not include all required fields
- **API:** `useImageDetail(imageId)` available but not used
- **API:** `useImageMeasurements(imageId)` available but not used
- **Display:** Missing comprehensive metadata panel

#### Actions

**Documentation Requirements:**

- ✅ Download FITS file (via JS9 or direct URL)
- ❌ Download PNG image (not implemented)
- ❌ View source list (not implemented)
- ❌ Reprocess with different parameters (not implemented)
- ❌ View QA plots (not implemented)

**Gap Analysis:**

- **FITS Download:** Available via `/api/images/{image_id}/fits`
- **PNG Download:** No endpoint or UI button
- **Source List:** No link to source detail page or source list
- **Reprocess:** No reprocessing UI or API call
- **QA Plots:** No link to QA page or QA visualization

---

### ✅ Implemented: Mosaic Builder (Separate Page)

**Documentation Requirements:**

- ✅ Time-Range Query (`MosaicGalleryPage.tsx`)
- ✅ Start/End DateTime pickers (UTC timezone)
- ✅ MJD conversion support
- ❌ Declination range filter (not in query)
- ❌ Preview coverage map before generation
- ✅ Create new mosaic from time range
- ✅ Background processing with status updates
- ✅ Progress tracking (status indicators)
- ✅ List previously generated mosaics
- ✅ Thumbnail previews (when available)
- ✅ Metadata display (time range, source count, noise level, image count)
- ✅ Download options (FITS via `/api/mosaics/{mosaic_id}/fits`)
- ✅ Quick view button (navigate to `/mosaics/{mosaic_id}`)

**Status:** ✅ **Fully Implemented** (but in separate page `/mosaics`)

**Gap Analysis:**

- **Location:** Mosaic builder is in `MosaicGalleryPage.tsx`, not integrated
  into `SkyViewPage.tsx`
- **Integration:** Documentation suggests mosaic builder should be part of Sky
  View page
- **Missing:** Declination range filter in mosaic query
- **Missing:** Preview coverage map before generation

---

## 4. Specific Gaps Summary

### Critical Missing Features

1. **Interactive Sky Map** ❌
   - No component exists
   - No API integration
   - No coverage visualization

2. **Image Gallery Grid View** 🔄
   - Currently list view, not grid
   - Missing thumbnails
   - Missing field ID, source count, calibrator status

3. **Advanced Filters** 🔄
   - Missing date range filter
   - Missing declination range filter
   - Missing quality threshold filter
   - Missing calibrator detected filter
   - Missing coordinate search

4. **Comprehensive Metadata Panel** 🔄
   - Missing observation details (date, MJD, integration time)
   - Missing frequency information
   - Missing source statistics
   - Missing calibration information

5. **Action Buttons** 🔄
   - Missing PNG download
   - Missing source list link
   - Missing reprocess button
   - Missing QA plots link

### API Integration Gaps

1. **`useImageDetail(imageId)`** - Available but not used
2. **`useImageMeasurements(imageId)`** - Available but not used
3. **Pointing history API** - Not integrated (for sky map)
4. **Field coverage API** - Not integrated (for sky map)
5. **Source list API** - Not linked from image detail

### Type Definition Gaps

**`ImageFilters` interface missing:**

```typescript
start_date?: string;        // Date range start
end_date?: string;          // Date range end
dec_min?: number;          // Declination range min
dec_max?: number;          // Declination range max
noise_max?: number;        // Quality threshold
has_calibrator?: boolean;  // Calibrator detected flag
field_id?: string;         // Field ID search
center_ra?: number;        // Coordinate search RA
center_dec?: number;       // Coordinate search Dec
radius?: number;           // Coordinate search radius
```

**`ImageInfo` type may be missing:**

```typescript
field_id?: string;          // Field identifier
source_count?: number;      // Detected sources count
calibrator_status?: string; // Calibrator detection status
observation_date?: string;  // Observation date
mjd?: number;              // Modified Julian Date
integration_time?: number; // Integration time (seconds)
frequency_center_hz?: number; // Center frequency
bandwidth_hz?: number;     // Bandwidth
calibrator_name?: string;   // Calibrator name
calibrator_separation_deg?: number; // Separation from pointing
calibrator_flux_measured_jy?: number; // Measured flux
calibrator_flux_expected_jy?: number; // Expected flux
calibration_tables?: string[]; // Calibration tables used
noise_thermal_ratio?: number; // Noise/thermal ratio
dynamic_range?: number;     // Dynamic range
nvss_matches_count?: number; // NVSS matches
variable_sources_count?: number; // Variable sources
```

---

## 5. Recommendations

### High Priority

1. **Add Interactive Sky Map Component**
   - Create `SkyMap.tsx` component
   - Integrate `usePointingHistory()` for telescope pointing
   - Integrate field coverage API (if available)
   - Add click handlers for field selection

2. **Enhance Image Gallery**
   - Convert `ImageBrowser` from list to grid layout
   - Add thumbnail display
   - Add missing fields (field_id, source_count, calibrator_status)

3. **Add Advanced Filters**
   - Extend `ImageFilters` type with date range, declination range, quality
     threshold
   - Add filter UI components (DatePicker, RangeSlider, etc.)
   - Update `ImageBrowser` to use new filters

4. **Enhance Metadata Panel**
   - Use `useImageDetail(imageId)` to fetch full image details
   - Use `useImageMeasurements(imageId)` for source statistics
   - Display all documented metadata fields

5. **Add Action Buttons**
   - PNG download button
   - Source list link
   - Reprocess button (if API available)
   - QA plots link

### Medium Priority

1. **Integrate Mosaic Builder into Sky View**
   - Add mosaic builder section to `SkyViewPage`
   - Or add link to mosaic gallery from Sky View

2. **Add Declination Range Filter to Mosaic Query**
   - Extend `MosaicQueryRequest` type
   - Add UI filter component

3. **Add Preview Coverage Map**
   - Create coverage visualization component
   - Show field coverage before mosaic generation

### Low Priority

1. **Add Profile/Fitting Visualization**
   - Integrate `FittingVisualization.tsx` and `ProfilePlot.tsx` into SkyViewPage
   - Display results from `ProfileTool` and `ImageFittingTool`

2. **Add Catalog Validation Panel**
   - Integrate `CatalogValidationPanel.tsx` into SkyViewPage
   - Show catalog validation results

---

**Last Updated:** 2025-11-14
