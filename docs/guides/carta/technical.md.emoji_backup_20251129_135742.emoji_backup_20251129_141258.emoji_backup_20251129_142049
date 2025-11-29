# CARTA Technical Reference

Advanced features, Protocol Buffers, and WebSocket enhancements.

---

## WebSocket Integration Features

### 1. Protocol Buffer Support

TypeScript interfaces for all CARTA messages:

- Message encoding/decoding utilities
- Header structure (8-byte format)
- JSON fallback for development
- Proto file loader utility

### 2. WebSocket Client

Full-featured WebSocket client:

- Connection management
- Automatic reconnection
- Request/response handling
- Message routing
- Error handling

### 3. Image Rendering

Canvas-based rendering engine:

- Tile composition
- Color mapping (gray, hot, viridis)
- Color scaling (linear, log, sqrt, asinh)
- Brightness/contrast controls

---

## Optional Enhancements

### Zoom and Pan Controls (`CARTAZoomPan.ts`)

**Features:**

- Mouse wheel zooming
- Click and drag panning
- Touch support (pinch to zoom)
- Programmatic controls
- Coordinate transformation

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

### Compression Handling (`CARTAImageRenderer.ts`)

**Supported Formats:**

- JPEG (magic bytes: FF D8 FF)
- PNG (magic bytes: 89 50 4E 47)
- Raw RGBA data

**Implementation:**

- Automatic format detection
- Async decoding using HTML5 Canvas API
- Blob URL creation for image loading
- Pixel data extraction for rendering

### Profile Plots (`CARTAProfilePlot.tsx`)

**Features:**

- Spatial profile visualization
- Spectral profile visualization
- Interactive charts (Recharts)
- Tab-based switching
- Metadata display

**Usage:**

```typescript
import CARTAProfilePlot from "../components/CARTA/CARTAProfilePlot";

<CARTAProfilePlot
  spatialProfile={spatialProfileData}
  spectralProfile={spectralProfileData}
  height={300}
/>;
```

### Histogram Display (`CARTAHistogram.tsx`)

**Features:**

- Region histogram visualization
- Bar chart using Recharts
- Statistical information
- Metadata display

**Usage:**

```typescript
import CARTAHistogram from "../components/CARTA/CARTAHistogram";

<CARTAHistogram histogramData={regionHistogramData} height={300} />;
```

### Region Types (`CARTARegionSelector.tsx`)

**Supported Regions:**

- Point
- Rectangle
- Ellipse
- Polygon
- Annulus

---

## Proto File Loading

### Automatic Discovery

The proto loader automatically discovers CARTA Protocol Buffer definitions:

- Multiple path support
- Download script provided
- Graceful fallback to JSON

### Download Script

```bash
./scripts/download-carta-protos.sh
```

---

## Component API Reference

### CARTAIframe

```typescript
interface CARTAIframeProps {
  cartaBackendUrl: string; // e.g., "http://localhost:9002"
  fitsFilePath?: string; // Optional file to pre-load
  height?: string; // Container height
}
```

### CARTAViewer

```typescript
interface CARTAViewerProps {
  backendUrl: string; // WebSocket URL
  fitsFilePath?: string; // Optional file to pre-load
  height?: string; // Container height
  showStatus?: boolean; // Show status bar
}
```

### CARTAClient

```typescript
interface CARTAClientConfig {
  backendUrl: string; // WebSocket URL
  reconnect?: boolean; // Auto-reconnect
  reconnectInterval?: number; // ms between reconnects
}

class CARTAClient {
  connect(): Promise<void>;
  disconnect(): void;
  openFile(path: string): Promise<FileInfo>;
  closeFile(fileId: number): Promise<void>;
  onMessage(type: string, handler: Function): void;
  setColorMap(colorMap: string): void;
  setScaling(scaling: string): void;
}
```

---

## Message Types

### File Operations

| Message    | Direction       | Description    |
| ---------- | --------------- | -------------- |
| OPEN_FILE  | Client → Server | Open FITS file |
| FILE_INFO  | Server → Client | File metadata  |
| CLOSE_FILE | Client → Server | Close file     |

### Image Data

| Message           | Direction       | Description         |
| ----------------- | --------------- | ------------------- |
| SET_IMAGE_VIEW    | Client → Server | Set view parameters |
| RASTER_IMAGE_DATA | Server → Client | Image tile data     |
| SET_COLORMAP      | Client → Server | Change color map    |

### Regions

| Message          | Direction       | Description          |
| ---------------- | --------------- | -------------------- |
| SET_REGION       | Client → Server | Create/modify region |
| REGION_STATS     | Server → Client | Region statistics    |
| REGION_HISTOGRAM | Server → Client | Region histogram     |

### Profiles

| Message               | Direction       | Description              |
| --------------------- | --------------- | ------------------------ |
| SET_SPATIAL_PROFILE   | Client → Server | Request spatial profile  |
| SPATIAL_PROFILE_DATA  | Server → Client | Spatial profile data     |
| SET_SPECTRAL_PROFILE  | Client → Server | Request spectral profile |
| SPECTRAL_PROFILE_DATA | Server → Client | Spectral profile data    |

---

## Future Enhancements

### Planned Features

1. **Complete Protocol Buffer Integration**

   - Full CARTA protobuf definitions
   - Binary message encoding/decoding

2. **Advanced Rendering**

   - WebGL acceleration
   - Contour overlays
   - Catalog overlay

3. **Analysis Tools**

   - Spectral line analysis
   - Moment maps
   - Position-velocity diagrams

4. **Pipeline Integration**
   - Auto-open pipeline output files
   - Link to source monitoring
   - QA report integration

---

## References

- [CARTA Documentation](https://cartavis.org/)
- [CARTA GitHub](https://github.com/CARTAvis)
- [Protocol Buffers](https://developers.google.com/protocol-buffers)
- [Recharts](https://recharts.org/)
