# CARTA Testing Guide

Instructions for testing CARTA WebSocket integration.

---

## Prerequisites

1. **CARTA Backend Running** - Port 9002 (WebSocket)
2. **Frontend Development Server** - Running with environment variables
3. **Test FITS Files** - Accessible to CARTA backend

---

## Environment Setup

### Frontend Environment Variables

Create or update `frontend/.env`:

```bash
VITE_CARTA_BACKEND_URL=ws://localhost:9002
VITE_CARTA_FRONTEND_URL=http://localhost:9002
```

### Verify Backend

```bash
# Check WebSocket endpoint
curl http://localhost:9002/api/health

# Check in browser
open http://localhost:9002
```

---

## Test Cases

### 1. Basic Connection Test

1. Navigate to `/carta` in the frontend
2. Select "WebSocket" integration mode
3. Verify connection status shows "Connected" (green)
4. Check browser console for connection logs

**Expected:**

- Status bar shows "CARTA: Connected"
- Connection indicator is green
- No error messages in console

### 2. File Opening Test

1. In File Browser tab, select a FITS file
2. Click "Open in Viewer"
3. Verify file opens successfully

**Expected:**

- File info displays in accordion
- Status shows "File loaded"
- File ID appears in status bar

### 3. Image Rendering Test

1. After opening a file, verify image renders
2. Check that tiles load and display
3. Verify image is visible on canvas

**Expected:**

- Image appears on canvas
- Tiles load progressively
- Image matches expected content

### 4. Zoom and Pan Test

1. Use mouse wheel to zoom in/out
2. Click and drag to pan
3. Test zoom controls in toolbar

**Expected:**

- Smooth zooming and panning
- Image stays in bounds
- Controls respond correctly

### 5. Color Map Test

1. Open Color Map panel
2. Change color map (gray, hot, viridis)
3. Adjust brightness/contrast

**Expected:**

- Color map changes immediately
- Brightness/contrast adjustable
- Image updates in real-time

### 6. Profile Plot Test

1. Click on image to get profiles
2. Check spatial profile tab
3. Check spectral profile tab

**Expected:**

- Profiles display correctly
- Charts are interactive
- Data matches cursor position

### 7. Histogram Test

1. Open histogram panel
2. Verify histogram displays
3. Check statistics

**Expected:**

- Histogram renders correctly
- Statistics are accurate
- Updates with region selection

### 8. Region Test

1. Select region type (rectangle, ellipse, etc.)
2. Draw region on image
3. Verify region statistics

**Expected:**

- Region draws correctly
- Statistics update
- Region can be modified

---

## Iframe Mode Tests

### 1. Iframe Loading

1. Select "Iframe" integration mode
2. Verify CARTA frontend loads in iframe
3. Check that file browser works

**Expected:**

- Iframe loads CARTA frontend
- No CORS errors
- File navigation works

### 2. File Pre-loading

1. Navigate to `/carta?file=/path/to/file.fits`
2. Verify file is auto-loaded

**Expected:**

- File loads automatically
- Image displays correctly

---

## Troubleshooting

### Backend Not Connecting

```bash
# Verify backend is running
docker ps --filter "name=carta-backend"

# Check backend health
curl http://localhost:9002/api/health

# View backend logs
docker logs carta-backend
```

### WebSocket Connection Fails

1. Check URL format: use `ws://` not `http://`
2. Check browser console for WebSocket errors
3. Verify backend accepts WebSocket connections
4. Check CORS settings

### Iframe Not Loading

1. Verify CARTA frontend accessible: `curl http://localhost:9002/`
2. Check `VITE_CARTA_FRONTEND_URL` in `.env`
3. Check browser console for CORS errors
4. Verify backend URL passed correctly

### Image Files Not Visible

1. Ensure FITS files are in mounted directories
2. Check container volume mounts: `docker inspect carta-backend`
3. Verify file permissions (container runs as `cartauser`)

### Rendering Issues

1. Check browser console for canvas errors
2. Verify WebGL support in browser
3. Test with smaller FITS file first
4. Check tile loading in network tab

---

## Performance Testing

### Large File Test

1. Open a large FITS file (> 1GB)
2. Monitor tile loading performance
3. Check memory usage in browser

### Multi-File Test

1. Open multiple files simultaneously
2. Switch between files
3. Verify no memory leaks

---

## Verification Checklist

| Test                            | Status |
| ------------------------------- | ------ |
| Backend running                 | ☐      |
| Frontend environment configured | ☐      |
| WebSocket connection            | ☐      |
| Iframe mode                     | ☐      |
| File opening                    | ☐      |
| Image rendering                 | ☐      |
| Zoom/pan                        | ☐      |
| Color maps                      | ☐      |
| Profiles                        | ☐      |
| Histogram                       | ☐      |
| Regions                         | ☐      |
| File pre-loading                | ☐      |
