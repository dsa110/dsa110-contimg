# CARTA Quick Start

Get CARTA running with the DSA-110 Dashboard in 5 minutes.

---

## Prerequisites

- Docker installed
- DSA-110 Dashboard running
- FITS files accessible in `/stage/dsa110-contimg` or `/data/dsa110-contimg`

---

## Step 1: Deploy CARTA Backend

```bash
docker run -d \
  --name carta-backend \
  --restart unless-stopped \
  -p 9002:3002 \
  -v /stage/dsa110-contimg:/stage/dsa110-contimg:ro \
  -v /data/dsa110-contimg:/data/dsa110-contimg:ro \
  cartavis/carta:latest
```

Verify it's running:

```bash
docker ps --filter "name=carta-backend"
curl http://localhost:9002/
```

---

## Step 2: Configure Dashboard

Create or update `frontend/.env`:

```bash
# CARTA Backend URL
VITE_CARTA_BACKEND_URL=http://localhost:9002

# CARTA Frontend URL (same as backend for v5+)
VITE_CARTA_FRONTEND_URL=http://localhost:9002
```

---

## Step 3: Access CARTA

1. Navigate to the dashboard: http://localhost:3210
2. Click "CARTA" in the navigation menu
3. Select integration mode (Iframe recommended)
4. Use File Browser to select a FITS file
5. View in CARTA Viewer

---

## Integration Modes

### Option 1: Iframe (Recommended)

**Pros:**
- Minimal setup, full CARTA functionality
- Isolated from dashboard code

**Cons:**
- Limited integration, separate authentication

**Setup:** Just deploy CARTA backend and set environment variables.

### Option 2: WebSocket

**Pros:**
- Full dashboard integration, shared state
- Native React components, Material-UI design

**Cons:**
- More complex, requires Protocol Buffer support

**Setup:** Same as iframe, but select "WebSocket" mode in CARTA page.

---

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
});
```

---

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend not connecting | Check: `curl http://localhost:9002/health` |
| Iframe not loading | Verify `VITE_CARTA_FRONTEND_URL` in `.env` |
| WebSocket fails | Use `ws://` not `http://` for WebSocket URL |
| Files not visible | Ensure FITS files are in mounted directories |

See [Testing Guide](testing.md) for detailed troubleshooting.

---

## Next Steps

- [Deployment Guide](deployment.md) - Production configuration
- [Testing Guide](testing.md) - Verification and testing
- [Technical Reference](technical.md) - Advanced features
