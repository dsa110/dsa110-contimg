# SkyView Implementation Plan

## Overview

The SkyView page will provide an interactive astronomical image viewer for DSA-110 continuum imaging pipeline products. This will enable users to visualize radio images, overlay catalogs, navigate coordinates, and perform basic measurements.

## User Requirements Analysis

### Primary Use Cases

1. **Quick Image Inspection**
   - View recently created images
   - Check image quality (noise, beam, coverage)
   - Verify calibration and imaging results

2. **Source Verification**
   - Overlay known catalogs (NVSS, VLASS) to verify detections
   - Compare pipeline images with reference catalogs
   - Identify calibrator sources

3. **Coordinate Navigation**
   - Navigate to specific RA/Dec coordinates
   - Center on known sources
   - Explore different regions of the sky

4. **Image Comparison**
   - Compare images from different time periods
   - Compare different imaging parameters
   - View before/after calibration

5. **Quality Assessment**
   - Visual inspection of image artifacts
   - Check primary beam correction
   - Verify mosaic coverage

### Key Features Needed

1. **Image Display**
   - FITS image rendering (CASA images converted to FITS)
   - Pan and zoom controls
   - Colormap selection (grayscale, viridis, plasma, etc.)
   - Stretch/scale controls (linear, log, sqrt, asinh)
   - Coordinate grid overlay
   - WCS coordinate display (RA/Dec)

2. **Image Selection**
   - Browse available images from products database
   - Filter by date, MS path, image type
   - Recent images list
   - Search by path or MS name

3. **Catalog Overlays**
   - NVSS catalog overlay (radio sources)
   - VLASS catalog overlay (if available)
   - Custom source lists
   - Toggle visibility
   - Source labels with flux information

4. **Measurement Tools**
   - Cursor position display (RA/Dec, pixel coordinates)
   - Flux measurement at cursor
   - Distance/angle measurement between points
   - Region selection (circles, rectangles)

5. **Metadata Display**
   - Image properties panel:
     - Beam size (major, minor, PA)
     - RMS noise
     - Peak flux
     - Image center coordinates
     - Image size (degrees, pixels)
     - Primary beam correction status
     - Creation timestamp
     - Associated MS path

6. **Export/Sharing**
   - Export current view as PNG
   - Download FITS file
   - Share image link (with coordinates/zoom state)

## Technical Implementation Plan

### Phase 1: Foundation (Core Display)

#### 1.1 Choose Image Viewer Library

**Option A: JS9 (JavaScript FITS Viewer)**
- **Pros**: 
  - Mature, well-maintained
  - Excellent FITS support
  - Good performance
  - Extensive features (regions, analysis)
- **Cons**:
  - Requires server-side FITS file serving
  - Less astronomy-specific UI

**Option B: Aladin Lite**
- **Pros**:
  - Astronomy-focused (CDS)
  - Built-in catalog support
  - WCS handling
  - Good for overlays
- **Cons**:
  - Heavier dependency
  - More complex integration

**Recommendation: JS9**
- Better for radio astronomy workflows
- More flexible for custom features
- Easier to integrate with React
- Good documentation

#### 1.2 Backend API Endpoints

**New Endpoints Needed:**

1. **`GET /api/images`** - List available images
   - Query params: `limit`, `offset`, `ms_path`, `type`, `pbcor`, `date_from`, `date_to`
   - Returns: `ImageList` with metadata

2. **`GET /api/images/{image_id}/metadata`** - Get detailed image metadata
   - Returns: Full image properties (beam, noise, WCS, etc.)

3. **`GET /api/images/{image_id}/fits`** - Serve FITS file
   - Converts CASA image to FITS if needed (on-demand)
   - Caches converted FITS files
   - Returns FITS file stream

4. **`GET /api/images/{image_id}/thumbnail`** - Get thumbnail
   - Returns PNG thumbnail for quick preview

5. **`POST /api/images/export-fits`** - Convert CASA image to FITS
   - Request: `{ "image_path": "..." }`
   - Returns: FITS file path or error

6. **`GET /api/catalogs/nvss`** - Query NVSS catalog
   - Query params: `ra`, `dec`, `radius_deg`
   - Returns: Catalog sources in region

#### 1.3 Frontend Components

**New Components:**

1. **`ImageBrowser`** - Image selection panel
   - List of available images
   - Filters and search
   - Image metadata preview

2. **`SkyViewer`** - Main image display component
   - JS9 integration
   - Wrapper for JS9 display
   - Event handlers for interactions

3. **`ImageControls`** - Display controls panel
   - Colormap selector
   - Stretch controls
   - Zoom controls
   - Grid toggle
   - Catalog overlay toggles

4. **`ImageMetadata`** - Metadata display panel
   - Image properties
   - Beam information
   - Quality metrics

5. **`CoordinateInput`** - Coordinate navigation
   - RA/Dec input
   - Go-to-coordinate button
   - Current position display

### Phase 2: Core Features

#### 2.1 Image Loading and Display

**Implementation Steps:**

1. Install JS9:
   ```bash
   npm install js9
   # Or use CDN in index.html
   ```

2. Create JS9 wrapper component:
   ```typescript
   // components/SkyViewer.tsx
   import { useEffect, useRef } from 'react';
   import JS9 from 'js9';
   
   export function SkyViewer({ imagePath }: { imagePath: string }) {
     const containerRef = useRef<HTMLDivElement>(null);
     
     useEffect(() => {
       if (!containerRef.current || !imagePath) return;
       
       // Initialize JS9
       JS9.Init(containerRef.current);
       
       // Load FITS file
       JS9.Load(imagePath);
       
       return () => {
         JS9.Close();
       };
     }, [imagePath]);
     
     return <div ref={containerRef} style={{ width: '100%', height: '600px' }} />;
   }
   ```

3. Add FITS file serving endpoint:
   - Check if FITS exists
   - If not, convert CASA image to FITS (async)
   - Return FITS file path
   - Cache converted files

#### 2.2 Image Browser

**Implementation Steps:**

1. Create API hook:
   ```typescript
   // api/queries.ts
   export function useImages(filters?: ImageFilters) {
     return useQuery({
       queryKey: ['images', filters],
       queryFn: async () => {
         const response = await apiClient.get<ImageList>('/api/images', { params: filters });
         return response.data;
       },
     });
   }
   ```

2. Create ImageBrowser component:
   - Display image list with thumbnails
   - Show metadata (date, MS path, type)
   - Click to load image
   - Filters for date range, type, etc.

#### 2.3 Coordinate Navigation

**Implementation Steps:**

1. Add coordinate input form
2. Convert RA/Dec to pixel coordinates
3. Use JS9 API to center on coordinates:
   ```javascript
   JS9.SetPan(ra, dec);
   ```

### Phase 3: Advanced Features

#### 3.1 Catalog Overlays

**Implementation Steps:**

1. Create catalog API endpoint:
   - Query NVSS for region
   - Return sources as JSON
   
2. Overlay sources on JS9:
   ```javascript
   // Add regions for each source
   JS9.AddRegions({
     type: 'circle',
     x: ra,
     y: dec,
     radius: 0.01, // degrees
     text: source.name
   });
   ```

3. Toggle visibility:
   - Show/hide catalog overlay
   - Filter by flux threshold

#### 3.2 Measurement Tools

**Implementation Steps:**

1. Use JS9 built-in measurement tools:
   - Cursor position display
   - Region selection
   - Flux measurement

2. Add custom measurement panel:
   - Display cursor RA/Dec
   - Show flux at cursor
   - Distance between points

#### 3.3 Image Comparison

**Implementation Steps:**

1. Add side-by-side view option
2. Load two images simultaneously
3. Synchronize pan/zoom
4. Compare tool (difference, ratio)

### Phase 4: Polish and Optimization

#### 4.1 Performance

- Cache FITS conversions
- Generate thumbnails on-demand
- Lazy load catalog data
- Optimize image serving

#### 4.2 User Experience

- Loading states
- Error handling
- Keyboard shortcuts
- Tooltips
- Help documentation

## Implementation Order

### Sprint 1: Foundation
1. Install JS9
2. Create basic SkyViewer component
3. Add image list API endpoint
4. Create ImageBrowser component
5. Basic image loading and display

### Sprint 2: Core Features
1. Coordinate navigation
2. Image controls (colormap, stretch, zoom)
3. Metadata display panel
4. FITS conversion endpoint

### Sprint 3: Catalogs
1. NVSS catalog API endpoint
2. Catalog overlay on images
3. Toggle visibility
4. Source labels

### Sprint 4: Advanced
1. Measurement tools
2. Image comparison
3. Export functionality
4. Thumbnail generation

### Sprint 5: Polish
1. Performance optimization
2. Error handling
3. Loading states
4. Documentation

## File Structure

```
frontend/src/
├── pages/
│   └── SkyViewPage.tsx          # Main page component
├── components/
│   ├── skyview/
│   │   ├── SkyViewer.tsx       # JS9 wrapper
│   │   ├── ImageBrowser.tsx    # Image selection
│   │   ├── ImageControls.tsx   # Display controls
│   │   ├── ImageMetadata.tsx   # Metadata panel
│   │   └── CoordinateInput.tsx # Coordinate nav
├── api/
│   ├── queries.ts              # Add image queries
│   └── types.ts                # Add image types
└── hooks/
    └── useJS9.ts               # JS9 integration hook

src/dsa110_contimg/api/
├── routes.py                   # Add image endpoints
└── models.py                   # Add image models

src/dsa110_contimg/api/
└── image_utils.py              # FITS conversion utilities
```

## API Models

```python
# api/models.py
class ImageInfo(BaseModel):
    id: int
    path: str
    ms_path: str
    created_at: datetime
    type: str  # "image", "pbcor", "residual", "psf", "pb"
    beam_major_arcsec: Optional[float]
    beam_minor_arcsec: Optional[float]
    beam_pa_deg: Optional[float]
    noise_jy: Optional[float]
    peak_flux_jy: Optional[float]
    pbcor: bool
    center_ra_deg: Optional[float]
    center_dec_deg: Optional[float]
    image_size_deg: Optional[float]
    pixel_size_arcsec: Optional[float]

class ImageList(BaseModel):
    items: List[ImageInfo]
    total: int

class ImageMetadata(BaseModel):
    image: ImageInfo
    wcs: Optional[Dict]  # WCS header information
    stats: Optional[Dict]  # Image statistics
```

## Dependencies

### Frontend
- `js9` - FITS image viewer (or CDN)
- `@types/js9` - TypeScript types (if available)

### Backend
- `casatasks.exportfits` - Already available
- `astropy` - For WCS handling (if needed)
- `numpy` - For image statistics

## Testing Strategy

1. **Unit Tests**
   - Image API endpoints
   - FITS conversion logic
   - Coordinate conversion utilities

2. **Integration Tests**
   - Image loading flow
   - Catalog overlay
   - Measurement tools

3. **E2E Tests**
   - Full user workflow
   - Image selection and display
   - Catalog overlay

## Success Criteria

1. ✓ Users can browse and select images
2. ✓ Images display correctly with WCS
3. ✓ Users can navigate to coordinates
4. ✓ Catalog overlays work correctly
5. ✓ Measurement tools provide accurate results
6. ✓ Performance is acceptable (< 2s load time)
7. ✓ Works with both CASA images and FITS files

## Future Enhancements

1. **Advanced Analysis**
   - Aperture photometry
   - Source finding
   - Image statistics

2. **Multi-wavelength Overlays**
   - Optical (DSS)
   - Infrared (WISE)
   - X-ray (if available)

3. **Time Series**
   - Animate through time
   - Light curves

4. **Collaboration**
   - Share views with URL parameters
   - Annotation tools
   - Comments

5. **Export Options**
   - High-resolution PNG
   - PDF reports
   - FITS cutouts

