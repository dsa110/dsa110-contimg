# CARTA Integration Guide for DSA-110 Dashboard

## Overview

This guide outlines strategies for integrating CARTA (Cube Analysis and
Rendering Tool for Astronomy) into the DSA-110 Dashboard frontend. CARTA
provides powerful FITS file visualization and analysis capabilities that
complement the existing dashboard features.

## Current State

- **Frontend**: React 18 + TypeScript + Material-UI v6
- **WebSocket Support**: Already implemented (`frontend/src/api/websocket.ts`)
- **CARTA-Style UI**: `QACartaPage.tsx` exists but doesn't integrate actual
  CARTA
- **Golden Layout**: Already using `golden-layout` (CARTA also uses this)

## Integration Options

### Option 1: Iframe Embedding (Simplest)

**Architecture:**

```
Dashboard Frontend (React)
  └─> iframe → CARTA Frontend (standalone)
                └─> WebSocket → CARTA Backend
```

**Implementation:**

```typescript
// frontend/src/components/CARTA/CARTAIframe.tsx
import { Box, Paper } from "@mui/material";
import { useState, useEffect } from "react";

interface CARTAIframeProps {
  cartaBackendUrl: string; // e.g., "http://localhost:9002" (9000-9099 range for External Integrations)
  fitsFilePath?: string;
  height?: string;
}

export default function CARTAIframe({
  cartaBackendUrl,
  fitsFilePath,
  height = "800px",
}: CARTAIframeProps) {
  const [cartaUrl, setCartaUrl] = useState<string>("");

  useEffect(() => {
    // CARTA frontend URL - can be served from same origin or separate
    const frontendUrl = process.env.VITE_CARTA_FRONTEND_URL || "http://localhost:9003";
    const url = new URL(frontendUrl);

    // Pass backend URL and initial file as query params
    if (cartaBackendUrl) {
      url.searchParams.set("backend", cartaBackendUrl);
    }
    if (fitsFilePath) {
      url.searchParams.set("file", fitsFilePath);
    }

    setCartaUrl(url.toString());
  }, [cartaBackendUrl, fitsFilePath]);

  return (
    <Paper sx={{ height, width: "100%", overflow: "hidden" }}>
      <Box
        component="iframe"
        src={cartaUrl}
        sx={{
          width: "100%",
          height: "100%",
          border: "none",
        }}
        title="CARTA Viewer"
      />
    </Paper>
  );
}
```

**Usage in existing pages:**

```typescript
// frontend/src/pages/QACartaPage.tsx (modify existing)
import CARTAIframe from "../components/CARTA/CARTAIframe";

// In your component:
<CARTAIframe
  cartaBackendUrl="http://localhost:9002"
  fitsFilePath="/stage/dsa110-contimg/images/2025-01-15T10:30:00.img-image.fits"
  height="100%"
/>
```

**Pros:**

- Minimal code changes
- Full CARTA functionality
- Isolated from dashboard code
- Easy to update CARTA independently

**Cons:**

- Limited integration (can't share state easily)
- Separate authentication
- iframe communication complexity
- Harder to match dashboard styling

---

### Option 2: WebSocket Integration (Recommended)

**Architecture:**

```
Dashboard Frontend (React)
  └─> WebSocket Client (existing)
      └─> CARTA Backend (Protocol Buffers)
```

**Implementation Steps:**

#### Step 1: Install CARTA Protocol Buffer Types

```bash
cd /data/dsa110-contimg/frontend
npm install --save-dev @types/protobufjs protobufjs
```

#### Step 2: Create CARTA WebSocket Client

```typescript
// frontend/src/services/cartaClient.ts
import { WebSocketClient } from "../api/websocket";
import protobuf from "protobufjs";
import { logger } from "../utils/logger";

export interface CARTAConfig {
  backendUrl: string; // e.g., "ws://localhost:9002" (9000-9099 range for External Integrations)
  sessionId?: string;
}

export class CARTAClient {
  private wsClient: WebSocketClient;
  private root: protobuf.Root | null = null;
  private messageTypes: Map<string, any> = new Map();

  constructor(config: CARTAConfig) {
    this.wsClient = new WebSocketClient({
      url: config.backendUrl,
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
    });

    this.initializeProtobuf();
  }

  private async initializeProtobuf() {
    try {
      // Load CARTA protobuf definitions
      // You'll need to copy these from CARTA backend or use @carta-protobuf package if available
      this.root = await protobuf.load("/api/carta/protobuf/carta.proto");

      // Register message types
      this.messageTypes.set(
        "REGISTER_VIEWER",
        this.root.lookupType("carta.RegisterViewer")
      );
      this.messageTypes.set(
        "OPEN_FILE",
        this.root.lookupType("carta.OpenFile")
      );
      // ... more message types
    } catch (error) {
      logger.error("Failed to load CARTA protobuf definitions:", error);
    }
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.wsClient.on("open", () => {
        this.registerViewer().then(resolve).catch(reject);
      });

      this.wsClient.on("error", reject);
      this.wsClient.connect();
    });
  }

  private async registerViewer(): Promise<void> {
    const RegisterViewer = this.messageTypes.get("REGISTER_VIEWER");
    if (!RegisterViewer) {
      throw new Error("RegisterViewer message type not loaded");
    }

    const message = RegisterViewer.create({
      sessionId: "",
      clientFeatureFlags: {},
    });

    return this.sendMessage(RegisterViewer.encode(message).finish());
  }

  async openFile(filePath: string, fileId: number = 0): Promise<void> {
    const OpenFile = this.messageTypes.get("OPEN_FILE");
    if (!OpenFile) {
      throw new Error("OpenFile message type not loaded");
    }

    const message = OpenFile.create({
      directory: this.getDirectory(filePath),
      file: this.getFilename(filePath),
      fileId,
      hdu: "",
    });

    return this.sendMessage(OpenFile.encode(message).finish());
  }

  private getDirectory(filePath: string): string {
    const parts = filePath.split("/");
    parts.pop();
    return parts.join("/");
  }

  private getFilename(filePath: string): string {
    const parts = filePath.split("/");
    return parts[parts.length - 1];
  }

  private sendMessage(buffer: Uint8Array): Promise<void> {
    return new Promise((resolve, reject) => {
      // CARTA uses binary WebSocket messages
      if (this.wsClient.isConnected()) {
        (this.wsClient as any).ws?.send(buffer);
        resolve();
      } else {
        reject(new Error("WebSocket not connected"));
      }
    });
  }

  onMessage(handler: (message: any) => void): void {
    this.wsClient.on("message", (data: any) => {
      // Decode protobuf message
      // Implementation depends on CARTA's message format
      handler(data);
    });
  }

  disconnect(): void {
    this.wsClient.disconnect();
  }
}
```

#### Step 3: Create CARTA Viewer Component

```typescript
// frontend/src/components/CARTA/CARTAViewer.tsx
import { useEffect, useRef, useState } from "react";
import { Box, CircularProgress, Alert, Paper } from "@mui/material";
import { CARTAClient } from "../../services/cartaClient";
import { logger } from "../../utils/logger";

interface CARTAViewerProps {
  backendUrl: string;
  fitsFilePath?: string;
  height?: string;
}

export default function CARTAViewer({
  backendUrl,
  fitsFilePath,
  height = "800px",
}: CARTAViewerProps) {
  const [client, setClient] = useState<CARTAClient | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cartaClient = new CARTAClient({
      backendUrl: backendUrl.replace(/^http/, "ws"),
    });

    cartaClient
      .connect()
      .then(() => {
        setClient(cartaClient);
        setLoading(false);

        if (fitsFilePath) {
          cartaClient.openFile(fitsFilePath);
        }
      })
      .catch((err) => {
        logger.error("Failed to connect to CARTA:", err);
        setError(err.message);
        setLoading(false);
      });

    cartaClient.onMessage((message) => {
      // Handle CARTA messages (rendering data, region updates, etc.)
      // Render to canvas or update UI
    });

    return () => {
      cartaClient.disconnect();
    };
  }, [backendUrl, fitsFilePath]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height={height}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Failed to connect to CARTA: {error}
      </Alert>
    );
  }

  return (
    <Paper sx={{ height, width: "100%", overflow: "hidden" }}>
      <Box
        component="canvas"
        ref={canvasRef}
        sx={{
          width: "100%",
          height: "100%",
          display: "block",
        }}
      />
    </Paper>
  );
}
```

**Pros:**

- Full integration with dashboard
- Reuses existing WebSocket infrastructure
- Can share authentication/state
- Native React component
- Matches Material-UI design system

**Cons:**

- Requires CARTA backend deployment
- Protocol Buffer handling complexity
- Need to implement rendering logic
- More development effort

---

### Option 3: CARTA Backend API Wrapper (Most Flexible)

Create a REST/WebSocket API wrapper around CARTA backend that matches your
existing API patterns.

**Implementation:**

```typescript
// frontend/src/api/carta.ts
import { apiClient } from "./client";

export interface CARTAFileInfo {
  name: string;
  path: string;
  size: number;
  type: string;
}

export interface CARTARegion {
  id: string;
  type: "point" | "line" | "polygon" | "ellipse";
  controlPoints: Array<{ x: number; y: number }>;
}

export const cartaApi = {
  // List available FITS files
  listFiles: async (directory: string): Promise<CARTAFileInfo[]> => {
    const response = await apiClient.get(`/api/carta/files`, {
      params: { directory },
    });
    return response.data;
  },

  // Open a FITS file in CARTA
  openFile: async (filePath: string): Promise<{ sessionId: string }> => {
    const response = await apiClient.post(`/api/carta/open`, {
      filePath,
    });
    return response.data;
  },

  // Get image data for rendering
  getImageData: async (
    sessionId: string,
    fileId: number,
    channel: number,
    stokes: number
  ): Promise<ArrayBuffer> => {
    const response = await apiClient.get(`/api/carta/image`, {
      params: { sessionId, fileId, channel, stokes },
      responseType: "arraybuffer",
    });
    return response.data;
  },

  // Create a region
  createRegion: async (
    sessionId: string,
    region: CARTARegion
  ): Promise<CARTARegion> => {
    const response = await apiClient.post(`/api/carta/regions`, {
      sessionId,
      region,
    });
    return response.data;
  },
};
```

**Backend wrapper (Python):**

```python
# src/dsa110_contimg/api/carta.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/carta", tags=["carta"])

class CARTAFileInfo(BaseModel):
    name: str
    path: str
    size: int
    type: str

class CARTARegion(BaseModel):
    id: str
    type: str
    control_points: List[dict]

@router.get("/files")
async def list_files(directory: str) -> List[CARTAFileInfo]:
    """List FITS files available for CARTA."""
    # Use CARTA backend API or direct file system access
    # Return file list
    pass

@router.post("/open")
async def open_file(file_path: str) -> dict:
    """Open a file in CARTA backend and return session ID."""
    # Connect to CARTA backend, open file, return session
    pass

@router.get("/image")
async def get_image_data(
    session_id: str,
    file_id: int,
    channel: int,
    stokes: int
):
    """Get image data from CARTA backend."""
    # Query CARTA backend, return image data
    pass
```

**Pros:**

- Full control over API design
- Matches existing dashboard API patterns
- Can add custom features
- Easier to integrate with existing auth

**Cons:**

- Most development effort
- Need to implement all CARTA features
- Maintenance burden

---

## Recommended Approach: Hybrid (Option 2 + 3)

**Phase 1: Iframe Integration (Quick Win)**

- Deploy CARTA backend
- Embed CARTA frontend in iframe
- Get CARTA working quickly

**Phase 2: WebSocket Integration (Full Integration)**

- Implement CARTA WebSocket client
- Create native React components
- Replace iframe with native components

**Phase 3: Custom Features (Enhancement)**

- Add DSA-110 specific features
- Integrate with pipeline data
- Custom UI components

---

## Deployment Requirements

### CARTA Backend Deployment

1. **Install CARTA Backend:**

   ```bash
   # Follow CARTA installation guide
   # Typically involves building from source or using Docker
   ```

2. **Configure CARTA Backend:**

```yaml
# carta-config.yaml
# Port 9002 follows port allocation strategy (9000-9099 for External Integrations)
server:
  port: 3002  # Internal container port
  host: "0.0.0.0"

   file_access:
     root_directory: "/stage/dsa110-contimg"
     allowed_extensions: [".fits", ".image"]

   security:
     allowed_origins: ["http://localhost:5173", "https://your-dashboard-domain"]
```

3. **Docker Compose (if using Docker):**

```yaml
# docker-compose.yml addition
# Port 9002 follows port allocation strategy (9000-9099 for External Integrations)
carta-backend:
  image: cartavis/carta-backend:latest
  ports:
    - "9002:3002"  # Host:Container mapping
     volumes:
       - /stage/dsa110-contimg:/data:ro
     environment:
       - CARTA_CONFIG=/config/carta-config.yaml
```

---

## Integration with Existing Pages

### Update QACartaPage

```typescript
// frontend/src/pages/QACartaPage.tsx
import { useState } from "react";
import { Box, Tabs, Tab } from "@mui/material";
import CARTAViewer from "../components/CARTA/CARTAViewer";
import DirectoryBrowser from "../components/QA/DirectoryBrowser";

export default function QACartaPage() {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [tab, setTab] = useState(0);

  const handleFileSelect = (path: string, type: string) => {
    if (type === "fits") {
      setSelectedFile(path);
    }
  };

  return (
    <Box sx={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <Tabs value={tab} onChange={(_, v) => setTab(v)}>
        <Tab label="CARTA Viewer" />
        <Tab label="File Browser" />
      </Tabs>

      <Box sx={{ flex: 1, overflow: "hidden" }}>
        {tab === 0 && (
          <CARTAViewer
            backendUrl={process.env.VITE_CARTA_BACKEND_URL || "http://localhost:9002"}
            fitsFilePath={selectedFile || undefined}
            height="100%"
          />
        )}
        {tab === 1 && (
          <DirectoryBrowser onSelectFile={handleFileSelect} />
        )}
      </Box>
    </Box>
  );
}
```

---

## Environment Variables

Add to `.env`:

```bash
# CARTA Configuration
# Ports follow allocation strategy: 9000-9099 for External Integrations
VITE_CARTA_BACKEND_URL=http://localhost:9002
VITE_CARTA_FRONTEND_URL=http://localhost:9003  # If using iframe approach
```

---

## Testing

```typescript
// frontend/src/components/CARTA/__tests__/CARTAViewer.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import CARTAViewer from "../CARTAViewer";

// Mock WebSocket
jest.mock("../../services/cartaClient");

describe("CARTAViewer", () => {
  it("connects to CARTA backend", async () => {
    render(
      <CARTAViewer
        backendUrl="ws://localhost:9002"
        fitsFilePath="/test/file.fits"
      />
    );

    await waitFor(() => {
      expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    });
  });
});
```

---

## Next Steps

1. **Choose integration approach** (recommend Option 2)
2. **Deploy CARTA backend** (Docker or native)
3. **Implement WebSocket client** (or start with iframe)
4. **Create React components** for CARTA integration
5. **Update existing pages** to use CARTA components
6. **Test with real FITS files** from pipeline
7. **Add DSA-110 specific features** (source overlays, pipeline integration)

---

## References

- [CARTA Documentation](https://cartavis.org/)
- [CARTA GitHub](https://github.com/CARTAvis)
- [CARTA Backend API](https://github.com/CARTAvis/carta-backend)
- [CARTA Frontend](https://github.com/CARTAvis/carta-frontend)
