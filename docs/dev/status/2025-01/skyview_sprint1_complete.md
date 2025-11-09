# SkyView Sprint 1 (Foundation) - Implementation Complete

## Date
2025-11-06

## Summary
✅ **Sprint 1 (Foundation) completed** - Basic image browsing and display functionality implemented

## Completed Features

### 1. Backend API Endpoints

#### `/api/images` (GET)
- ✅ Lists available images from products database
- ✅ Supports filtering by `ms_path`, `image_type`, `pbcor`
- ✅ Pagination with `limit` and `offset`
- ✅ Returns `ImageList` with metadata

#### `/api/images/{image_id}/fits` (GET) - **NEW**
- ✅ Serves FITS files for images
- ✅ Converts CASA images to FITS on-demand
- ✅ Caches converted FITS files (reuses existing `.fits` files)
- ✅ Returns FITS file stream with proper content type

### 2. Image Utilities

**New File**: `src/dsa110_contimg/api/image_utils.py`
- ✅ `get_fits_path()` - Finds or creates FITS file for an image
- ✅ `convert_casa_to_fits()` - Converts CASA images to FITS format
- ✅ `is_casa_image()` - Detects CASA image directories

### 3. Frontend Components

#### SkyViewPage (`frontend/src/pages/SkyViewPage.tsx`)
- ✅ Integrated `ImageBrowser` and `SkyViewer` components
- ✅ Two-column layout (browser sidebar + main display)
- ✅ Image selection state management
- ✅ Image metadata display (name, type, noise, beam)
- ✅ FITS URL construction for selected image

#### ImageBrowser (`frontend/src/components/Sky/ImageBrowser.tsx`)
- ✅ Already implemented (from Sprint 1 foundation)
- ✅ Lists images from `/api/images` endpoint
- ✅ Filtering by MS path, image type, PB correction
- ✅ Click to select image

#### SkyViewer (`frontend/src/components/Sky/SkyViewer.tsx`)
- ✅ JS9 integration (library loaded via CDN)
- ✅ Image loading from FITS endpoint
- ✅ Loading states and error handling
- ✅ Empty state when no image selected

### 4. JS9 Library
- ✅ Included via CDN in `frontend/index.html`
- ✅ CSS and JS loaded correctly
- ✅ Global `window.JS9` available

## Implementation Details

### FITS File Serving Flow

1. User selects image in `ImageBrowser`
2. `SkyViewPage` constructs FITS URL: `/api/images/{id}/fits`
3. Backend endpoint:
   - Looks up image path from database
   - Calls `get_fits_path()` to find or create FITS file
   - If CASA image, converts to FITS on-demand
   - Returns FITS file via `FileResponse`
4. `SkyViewer` component loads FITS via JS9:
   - Calls `JS9.Load(fitsUrl)`
   - JS9 handles FITS parsing and display
   - Shows loading spinner during conversion/load

### CASA to FITS Conversion

- Uses `casatasks.exportfits` when available
- Converts on-demand (first request)
- Caches result (reuses existing `.fits` file)
- Handles errors gracefully (returns 404 if conversion fails)

## Current Status

### ✅ Working
- Image browsing and selection
- FITS file serving endpoint
- CASA image conversion
- JS9 display initialization
- Image loading (when FITS available)

### ⚠️ Limitations
- CASA conversion requires CASA environment (may fail in some contexts)
- No coordinate navigation yet (Sprint 2)
- No image controls yet (colormap, zoom, etc.) (Sprint 2)
- No catalog overlays yet (Sprint 3)

## Testing

### Manual Testing Steps

1. **Start API server** (if not running)
2. **Navigate to SkyView page** in dashboard
3. **Browse images** in left sidebar
4. **Select an image** - should load in JS9 viewer
5. **Verify FITS conversion** - check backend logs for conversion messages

### Expected Behavior

- Image browser shows list of available images
- Clicking an image loads it in JS9 viewer
- If CASA image, backend converts to FITS automatically
- JS9 displays image with WCS coordinates
- Image metadata shown above viewer

## Files Modified

1. `src/dsa110_contimg/api/image_utils.py` - **NEW** - Image utility functions
2. `src/dsa110_contimg/api/routes.py` - Added `/api/images/{id}/fits` endpoint
3. `frontend/src/pages/SkyViewPage.tsx` - Integrated components
4. `frontend/src/components/Sky/SkyViewer.tsx` - Fixed image loading

## Next Steps (Sprint 2)

1. Coordinate navigation (RA/Dec input, go-to-coordinate)
2. Image controls (colormap, stretch, zoom)
3. Metadata panel (detailed image properties)
4. Enhanced error handling for conversion failures

## Notes

- FITS conversion is synchronous (may take time for large images)
- Consider async conversion with job queue for production
- JS9 handles most display features (pan, zoom, colormap) natively
- Additional controls can be added via JS9 API

