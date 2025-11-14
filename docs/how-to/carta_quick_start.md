# CARTA Integration Quick Start

## Overview

CARTA (Cube Analysis and Rendering Tool for Astronomy) integration is now
available in the DSA-110 Dashboard. Two integration options are implemented:

1. **Option 1: Iframe Integration** - Quick validation with minimal setup
2. **Option 2: WebSocket Integration** - Full native integration (requires
   Protocol Buffer support)

## Quick Start

### 1. Access CARTA Page

Navigate to: **`/carta`** in the dashboard

### 2. Configure Environment Variables

Create or update `frontend/.env`:

```bash
# CARTA Backend URL (WebSocket endpoint)
VITE_CARTA_BACKEND_URL=http://localhost:9002

# CARTA Frontend URL (for iframe integration only)
VITE_CARTA_FRONTEND_URL=http://localhost:9003
```

### 3. Deploy CARTA Backend

**Option A: Docker (Recommended)**

```bash
# Port 9002 follows port allocation strategy (9000-9099 for External Integrations)
docker run -d \
  --name carta-backend \
  -p 9002:3002 \
  -v /stage/dsa110-contimg:/data:ro \
  cartavis/carta-backend:latest
```

**Option B: Native Installation**

Follow [CARTA installation guide](https://cartavis.org/docs/installation/).

### 4. Test Integration

1. Start the dashboard: `npm run dev` (in `frontend/`)
2. Navigate to `/carta`
3. Select integration mode (iframe or websocket)
4. Use File Browser tab to select a FITS file
5. View in CARTA Viewer tab

## Integration Modes

### Option 1: Iframe (Quick Validation)

**Pros:**

- Minimal setup
- Full CARTA functionality
- Isolated from dashboard code

**Cons:**

- Limited integration
- Separate authentication
- Harder to share state

**Setup:**

1. Deploy CARTA backend
2. Deploy CARTA frontend (or use existing deployment)
3. Set `VITE_CARTA_FRONTEND_URL` in `.env`
4. Select "Option 1: Iframe" in CARTA page

### Option 2: WebSocket (Full Integration)

**Pros:**

- Full dashboard integration
- Shared authentication/state
- Native React components
- Matches Material-UI design

**Cons:**

- Requires Protocol Buffer support (TODO)
- More complex setup
- Rendering logic needs implementation

**Setup:**

1. Deploy CARTA backend
2. Set `VITE_CARTA_BACKEND_URL` in `.env`
3. Select "Option 2: WebSocket" in CARTA page

**Note:** WebSocket integration currently has placeholder rendering. Full
implementation requires:

- CARTA Protocol Buffer definitions
- Image rendering logic
- Region handling

## File Structure

```
frontend/src/
├── components/CARTA/
│   ├── CARTAIframe.tsx      # Option 1: Iframe component
│   ├── CARTAViewer.tsx      # Option 2: WebSocket component
│   └── index.ts             # Exports
├── services/
│   └── cartaClient.ts       # CARTA WebSocket client
└── pages/
    └── CARTAPage.tsx        # Main CARTA integration page
```

## Usage Examples

### Using CARTAIframe Component

```typescript
import { CARTAIframe } from "../components/CARTA";

<CARTAIframe
  cartaBackendUrl="http://localhost:9002"
  fitsFilePath="/stage/dsa110-contimg/images/file.fits"
  height="800px"
/>
```

### Using CARTAViewer Component

```typescript
import { CARTAViewer } from "../components/CARTA";

<CARTAViewer
  backendUrl="http://localhost:9002"
  fitsFilePath="/stage/dsa110-contimg/images/file.fits"
  height="800px"
  showStatus={true}
/>
```

### Using CARTA Client Directly

```typescript
import { CARTAClient } from "../services/cartaClient";

const client = new CARTAClient({
  backendUrl: "ws://localhost:9002",
});

await client.connect();
await client.openFile("/path/to/file.fits");

client.onMessage("FILE_INFO", (message) => {
  console.log("File info:", message);
}));
```

## Troubleshooting

### CARTA Backend Not Connecting

1. Verify backend is running: `curl http://localhost:9002/health`
2. Check WebSocket URL format (should start with `ws://` or `wss://`)
3. Check CORS settings in CARTA backend config
4. Verify firewall/network settings

### Iframe Not Loading

1. Verify CARTA frontend is accessible: `curl http://localhost:9003`
2. Check `VITE_CARTA_FRONTEND_URL` in `.env`
3. Check browser console for CORS errors
4. Verify backend URL is passed correctly

### WebSocket Connection Fails

1. Check backend URL format (use `ws://` not `http://`)
2. Verify Protocol Buffer support (currently placeholder)
3. Check browser console for WebSocket errors
4. Verify backend accepts WebSocket connections

## Next Steps

1. **Complete Protocol Buffer Integration**
   - Add CARTA protobuf definitions
   - Implement message encoding/decoding
   - Test with real CARTA backend

2. **Implement Rendering**
   - Add canvas rendering logic
   - Handle image data from CARTA
   - Implement region rendering

3. **Add Features**
   - Region creation/editing
   - Catalog overlay
   - Spectral line analysis
   - Export functionality

4. **Integration with Pipeline**
   - Auto-open pipeline output files
   - Link to source monitoring
   - QA report integration

## References

- [CARTA Documentation](https://cartavis.org/)
- [CARTA GitHub](https://github.com/CARTAvis)
- [Integration Guide](./carta_integration_guide.md)
