# CARTA WebSocket Integration - Optional Enhancements

This document describes the optional enhancements implemented for the CARTA
WebSocket integration.

## Implemented Enhancements

### 1. Zoom and Pan Controls (`CARTAZoomPan.ts`)

**Features:**

- Mouse wheel zooming (zoom in/out)
- Click and drag panning
- Touch support (pinch to zoom, drag to pan)
- Programmatic zoom controls (zoomIn, zoomOut, reset, fitToCanvas)
- Coordinate transformation (screen ↔ image coordinates)

**Usage:**

```typescript
import { CARTAZoomPan } from "../components/CARTA";

const zoomPan = new CARTAZoomPan(
  canvas,
  {
    scale: 1.0,
    minScale: 0.1,
    maxScale: 10.0,
  },
  (state) => {
    // Handle state changes
  }
);

// Apply transform before drawing
zoomPan.applyTransform(ctx);
// ... draw image ...
zoomPan.restoreTransform(ctx);
```

### 2. Compression Handling (`CARTAImageRenderer.ts`)

**Supported Formats:**

- JPEG (magic bytes: FF D8 FF)
- PNG (magic bytes: 89 50 4E 47)
- Raw RGBA data

**Implementation:**

- Automatic format detection based on magic bytes
- Async decoding using HTML5 Canvas API
- Blob URL creation for image loading
- Pixel data extraction for rendering

**Benefits:**

- Reduced bandwidth usage
- Faster image loading
- Support for compressed tile formats from CARTA backend

### 3. Profile Plots (`CARTAProfilePlot.tsx`)

**Features:**

- Spatial profile visualization
- Spectral profile visualization
- Interactive charts using Recharts
- Tab-based switching between profile types
- Metadata display (file ID, channel, stokes, progress)

**Usage:**

```typescript
import CARTAProfilePlot from "../components/CARTA/CARTAProfilePlot";

<CARTAProfilePlot
  spatialProfile={spatialProfileData}
  spectralProfile={spectralProfileData}
  height={300}
/>
```

### 4. Histogram Display (`CARTAHistogram.tsx`)

**Features:**

- Region histogram visualization
- Bar chart using Recharts
- Statistical information (mean, std dev, bin count)
- Metadata display (region ID, file ID, channel, stokes)

**Usage:**

```typescript
import CARTAHistogram from "../components/CARTA/CARTAHistogram";

<CARTAHistogram
  histogramData={regionHistogramData}
  height={300}
/>
```

### 5. Region Type Selector (`CARTARegionSelector.tsx`)

**Supported Region Types:**

- Point
- Rectangle
- Ellipse
- Polygon
- Annulus

**Features:**

- Icon-based UI for region type selection
- Material-UI button group
- Tooltips for each region type
- Visual feedback for selected type

**Usage:**

```typescript
import CARTARegionSelector from "../components/CARTA/CARTARegionSelector";

<CARTARegionSelector
  selectedType={RegionType.RECTANGLE}
  onTypeChange={(type) => setRegionType(type)}
  disabled={false}
/>
```

### 6. Protocol Buffer Support (Future Enhancement)

**Current Status:**

- TypeScript interfaces defined in `cartaProtobuf.ts`
- JSON fallback encoding/decoding for development
- Structure ready for actual .proto file loading

**To Load Actual CARTA .proto Files:**

1. Download CARTA protobuf definitions:

   ```bash
   # Option 1: Clone CARTA repository
   git clone https://github.com/CARTAvis/carta-protobuf.git

   # Option 2: Use npm package (if available)
   npm install @carta-protobuf/definitions
   ```

2. Load in `cartaClient.ts`:
   ```typescript
   private async initializeProtobuf(): Promise<void> {
     try {
       this.root = await protobuf.load("path/to/carta.proto");
       logger.info("CARTA Protocol Buffer definitions loaded");
     } catch (error) {
       logger.warn("Failed to load .proto files, using JSON fallback:", error);
     }
   }
   ```

## Integration Example

Complete integration in `CARTAViewer.tsx`:

```typescript
import { CARTAZoomPan } from "./CARTAZoomPan";
import CARTAProfilePlot from "./CARTAProfilePlot";
import CARTAHistogram from "./CARTAHistogram";
import CARTARegionSelector from "./CARTARegionSelector";

// In component:
const [regionType, setRegionType] = useState<RegionType>(RegionType.RECTANGLE);
const [spatialProfile, setSpatialProfile] = useState<SpatialProfileData>();
const [spectralProfile, setSpectralProfile] = useState<SpectralProfileData>();
const [histogram, setHistogram] = useState<RegionHistogramData>();

// Setup zoom/pan
useEffect(() => {
  if (canvasRef.current) {
    const zoomPan = new CARTAZoomPan(canvasRef.current);
    // Use zoomPan for rendering
  }
}, []);

// Handle region type changes
const handleRegionTypeChange = (type: RegionType) => {
  setRegionType(type);
  // Update region creation logic
};
```

## Dependencies

**Required:**

- `recharts` - For profile plots and histograms
- `protobufjs` - For Protocol Buffer support (optional, JSON fallback available)

**Installation:**

```bash
cd frontend
npm install recharts protobufjs
```

## Performance Considerations

1. **Compression Handling:**
   - JPEG/PNG decoding is async and may cause slight delays
   - Consider caching decoded tiles
   - Use Web Workers for heavy decoding (future enhancement)

2. **Zoom/Pan:**
   - Transform is applied at render time
   - Consider using CSS transforms for better performance
   - Limit zoom range to prevent excessive memory usage

3. **Profile Plots:**
   - Recharts handles large datasets efficiently
   - Consider data sampling for very large profiles

## Future Enhancements

1. **Web Workers:**
   - Move JPEG/PNG decoding to Web Workers
   - Parallel tile processing

2. **Advanced Region Types:**
   - Implement polygon drawing with multiple points
   - Ellipse/annulus with proper control points
   - Region editing (move, resize, delete)

3. **Additional Visualizations:**
   - Contour plots
   - 3D surface plots
   - Multi-panel layouts

4. **Performance Optimizations:**
   - Tile caching
   - Level-of-detail (LOD) rendering
   - Virtual scrolling for large images

## Testing

To test the enhancements:

1. **Zoom/Pan:**
   - Load an image in CARTA viewer
   - Use mouse wheel to zoom
   - Click and drag to pan
   - Test touch gestures on mobile devices

2. **Compression:**
   - CARTA backend should send compressed tiles
   - Verify tiles render correctly
   - Check browser console for decoding errors

3. **Profile Plots:**
   - Create a region on an image
   - Verify spatial/spectral profiles appear
   - Test tab switching

4. **Histogram:**
   - Create a region
   - Verify histogram displays
   - Check statistical values

5. **Region Types:**
   - Select different region types
   - Create regions and verify they render correctly
   - Test region type switching

## Troubleshooting

**Issue: Tiles not rendering**

- Check browser console for decoding errors
- Verify tile data format matches expected compression type
- Ensure canvas context is available

**Issue: Zoom/Pan not working**

- Verify canvas element is properly initialized
- Check event listeners are attached
- Ensure canvas has proper dimensions

**Issue: Profile plots empty**

- Verify CARTA backend is sending profile data
- Check message handlers are registered
- Verify data format matches expected structure

**Issue: Region creation fails**

- Check region type is valid
- Verify control points are provided
- Ensure CARTA backend supports the region type
