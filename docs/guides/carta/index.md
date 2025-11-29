# CARTA Integration Guide

**Last Updated:** November 29, 2025  
**Status:** ✅ Production Ready

CARTA (Cube Analysis and Rendering Tool for Astronomy) provides interactive
visualization of FITS images with advanced analysis capabilities. This guide
covers all aspects of CARTA integration with the DSA-110 Dashboard.

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Quick Start](quickstart.md) | Get started in 5 minutes |
| [Deployment](deployment.md) | Docker deployment and configuration |
| [Testing](testing.md) | Testing guide and verification |
| [Technical Reference](technical.md) | WebSocket enhancements, Protocol Buffers |

---

## Overview

CARTA integration is available in two modes:

1. **Iframe Mode** (default) - Embeds CARTA frontend via iframe, full functionality
2. **WebSocket Mode** - Native React integration with direct WebSocket connection

### Current Deployment Status

| Component | Status | URL |
|-----------|--------|-----|
| CARTA Container | ✅ Running | `carta-backend` |
| CARTA Version | 5.0.3 | - |
| Backend Port | 9002 | http://localhost:9002/ |
| Dashboard Integration | ✅ Active | http://localhost:3210/carta |

---

## Access Points

### 1. Main Navigation Menu

- **Location:** Top navigation bar → "CARTA"
- **Route:** `/carta`
- **Features:** Full integration page, mode toggle, file browser

### 2. Image Detail Pages

- **Location:** Any image detail page (`/images/:imageId`)
- **Action:** Click "View in CARTA" button
- **Route:** `/carta?file=<image_path>`

### 3. QA Tools Page

- **Location:** `/qa/carta`
- **Features:** CARTA-style QA visualization with Golden Layout

### 4. Data Browser

- **Location:** `/data` → select image → "View in CARTA"
- **Route:** `/data` → `/images/:imageId` → `/carta?file=<path>`

---

## Port Allocation

| Port | Service | Range | Notes |
|------|---------|-------|-------|
| **9002** | CARTA Backend | 9000-9099 (External) | WebSocket + Frontend |
| **9003** | Reserved | 9000-9099 (External) | Not currently used |

Environment variables:

```bash
# CARTA Backend (WebSocket + HTTP)
VITE_CARTA_BACKEND_URL=http://localhost:9002

# CARTA Frontend (for iframe mode, if separate)
VITE_CARTA_FRONTEND_URL=http://localhost:9002
```

---

## Data Volumes

CARTA has read-only access to:

- `/stage/dsa110-contimg` - Processed images and staging data
- `/data/dsa110-contimg` - Raw data and pipeline products

---

## File Structure

```
frontend/src/
├── components/CARTA/
│   ├── CARTAIframe.tsx          # Iframe integration
│   ├── CARTAViewer.tsx          # WebSocket viewer
│   ├── CARTAImageRenderer.ts    # Image rendering engine
│   ├── CARTAZoomPan.ts          # Zoom/pan controller
│   ├── CARTAProfilePlot.tsx     # Profile visualization
│   ├── CARTAHistogram.tsx       # Histogram visualization
│   ├── CARTARegionSelector.tsx  # Region type selector
│   └── index.ts                 # Component exports
├── services/
│   ├── cartaClient.ts           # WebSocket client
│   ├── cartaProtobuf.ts         # Protocol Buffer definitions
│   └── cartaProtoLoader.ts      # Proto file loader
└── pages/
    └── CARTAPage.tsx            # Main CARTA page
```

---

## Related Documentation

- [CARTA Official Docs](https://cartavis.org/)
- [CARTA GitHub](https://github.com/CARTAvis)
- [Dashboard Architecture](../../architecture/dashboard/dashboard_architecture.md)
