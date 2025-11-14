# CARTA User Access Guide

## Where Users Can Access CARTA

CARTA (Cube Analysis and Rendering Tool for Astronomy) is integrated into the
DSA-110 Dashboard in multiple locations, allowing users to visualize FITS images
from both published and staged data.

## Access Points

### 1. Main Navigation Menu

**Location:** Top navigation bar

**Access:** Click "CARTA" in the main navigation menu

**Route:** `/carta`

**Features:**

- Full CARTA integration page
- Toggle between iframe and WebSocket modes
- File browser for selecting FITS files
- Direct file path input
- Configuration for backend/frontend URLs

### 2. Image Detail Page

**Location:** Individual image detail pages

**Access:**

- Navigate to any image detail page (e.g., `/images/:imageId`)
- Click "View in CARTA" button in the image metadata section

**Route:** `/images/:imageId` → Button links to `/carta?file=<image_path>`

**Features:**

- Direct link to CARTA with the image file pre-loaded
- Automatically opens the image in CARTA viewer
- Works for both published and staged images

**Example:**

```
Image Detail Page → "View in CARTA" button → CARTA Page with file loaded
```

### 3. QA Tools Page

**Location:** QA Visualization section

**Access:**

- Navigate to `/qa`
- Access CARTA-style QA visualization

**Route:** `/qa/carta`

**Features:**

- CARTA-inspired layout with Golden Layout
- File browser integration
- FITS viewer
- CASA table viewer

### 4. Data Browser

**Location:** Data Browser page

**Access:**

- Navigate to `/data`
- Browse images (published or staged)
- Select an image to view details
- Use "View in CARTA" button from image detail page

**Route:** `/data` → `/images/:imageId` → `/carta?file=<path>`

## File Sources

### Published Images

**Location:** `/data/dsa110-contimg/products/images/`

**Access:**

- Via Data Browser (published tab)
- Via Image Detail pages
- Direct file path in CARTA

### Staged Images

**Location:** `/stage/dsa110-contimg/images/`

**Access:**

- Via Data Browser (staging tab)
- Via File Browser in CARTA page
- Direct file path in CARTA

## Usage Workflows

### Workflow 1: View Published Image in CARTA

1. Navigate to **Data Browser** (`/data`)
2. Select **Published** tab
3. Filter for **Images**
4. Click on an image to view details
5. Click **"View in CARTA"** button
6. Image opens in CARTA viewer

### Workflow 2: Browse and View Staged Images

1. Navigate to **CARTA** (`/carta`)
2. Click **File Browser** tab
3. Navigate to `/stage/dsa110-contimg/images/`
4. Select a FITS file
5. Switch to **CARTA Viewer** tab
6. Image loads in CARTA

### Workflow 3: Direct File Access

1. Navigate to **CARTA** (`/carta`)
2. Use File Browser to navigate to file location
3. Select FITS file
4. View in CARTA viewer

### Workflow 4: From Image Detail Page

1. Navigate to any image detail page (`/images/:imageId`)
2. Scroll to image metadata section
3. Click **"View in CARTA"** button
4. CARTA opens with the image loaded

## Integration Modes

### Option 1: Iframe Mode (Default)

**Best for:**

- Quick validation
- Full CARTA functionality
- Isolated environment

**Configuration:**

- Requires CARTA frontend running on port 9003
- Set `VITE_CARTA_FRONTEND_URL` environment variable

### Option 2: WebSocket Mode

**Best for:**

- Full dashboard integration
- Shared authentication
- Native React components

**Configuration:**

- Requires CARTA backend running on port 9002
- Set `VITE_CARTA_BACKEND_URL` environment variable
- Protocol Buffer support (in development)

## URL Parameters

CARTA page supports URL query parameters:

- `file=<path>` - Pre-load a FITS file
  - Example: `/carta?file=/stage/dsa110-contimg/images/image.fits`
- `mode=<iframe|websocket>` - Set integration mode
  - Example: `/carta?file=image.fits&mode=websocket`

## File Path Formats

CARTA accepts both absolute and relative paths:

**Absolute paths:**

- `/stage/dsa110-contimg/images/2025-01-15T10:30:00.img-image.fits`
- `/data/dsa110-contimg/products/images/image.fits`

**Relative paths:**

- `images/image.fits` (relative to CARTA backend root)

## Supported File Types

- **FITS files:** `.fits`, `.fits.gz`, `.fit`, `.fts`
- **CASA tables:** Directory-based tables (for CASA table viewer)

## Troubleshooting

### CARTA Not Loading

1. Verify CARTA backend is running: `curl http://localhost:9002/health`
2. Check environment variables in `frontend/.env`
3. Verify port allocation (9002 for backend, 9003 for frontend)

### File Not Found

1. Verify file path is accessible from CARTA backend
2. Check file permissions
3. Ensure file is in a mounted volume (for Docker)

### "View in CARTA" Button Not Appearing

1. Verify image has a `path` field
2. Check image detail page loads correctly
3. Verify CARTA route is accessible

## Related Documentation

- [CARTA Integration Guide](./carta_integration_guide.md)
- [CARTA Quick Start](./carta_quick_start.md)
- [Port Allocation](./carta_port_allocation.md)
