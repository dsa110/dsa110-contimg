# CARTA WebSocket Integration - Testing Guide

This guide provides instructions for testing the CARTA WebSocket integration
with a real CARTA backend.

## Prerequisites

1. **CARTA Backend Running**
   - CARTA backend server must be running and accessible
   - Default port: 9002 (WebSocket)
   - Default frontend port: 9003 (HTTP)

2. **Frontend Environment**
   - Frontend development server running
   - Environment variables configured (see below)

3. **Test FITS Files**
   - Sample FITS files for testing
   - Files accessible to CARTA backend

## Environment Setup

### Frontend Environment Variables

Create or update `.env` in the frontend directory:

```bash
# CARTA Backend URL (WebSocket endpoint)
VITE_CARTA_BACKEND_URL=ws://localhost:9002

# CARTA Frontend URL (for iframe integration only)
VITE_CARTA_FRONTEND_URL=http://localhost:9003
```

### CARTA Backend Setup

1. **Install CARTA Backend**

   ```bash
   # Option 1: Docker (recommended)
   docker pull cartavis/carta-backend:latest
   docker run -d -p 9002:3002 -p 9003:3000 cartavis/carta-backend:latest

   # Option 2: From source
   git clone https://github.com/CARTAvis/carta-backend.git
   cd carta-backend
   npm install
   npm start
   ```

2. **Verify Backend is Running**

   ```bash
   # Check WebSocket endpoint
   curl http://localhost:9002/api/health

   # Or check in browser
   # http://localhost:9003
   ```

## Testing Steps

### 1. Basic Connection Test

1. Navigate to `/carta` in the frontend
2. Select "WebSocket" integration mode
3. Verify connection status shows "Connected" (green)
4. Check browser console for connection logs

**Expected:**

- Status bar shows "CARTA: Connected"
- No error messages in console
- Connection indicator is green

### 2. File Opening Test

1. In the File Browser tab, select a FITS file
2. Click "Open in Viewer"
3. Verify file opens successfully

**Expected:**

- File info displays in accordion
- Status shows "File loaded"
- File ID appears in status bar
- No error messages

### 3. Image Rendering Test

1. After opening a file, verify image renders
2. Check that tiles load and display
3. Verify image is visible on canvas

**Expected:**

- Image appears on canvas
- Tiles load progressively
- No rendering errors in console
- Image matches expected content

### 4. Zoom and Pan Test

1. **Mouse Wheel Zoom:**
   - Scroll mouse wheel up/down
   - Verify zoom in/out works
   - Check zoom limits (min/max)

2. **Click and Drag Pan:**
   - Click and drag on canvas
   - Verify image moves
   - Check pan boundaries

3. **Zoom Controls:**
   - Click zoom in/out buttons
   - Click "Fit to Screen" button
   - Verify controls work correctly

**Expected:**

- Smooth zooming without lag
- Panning works correctly
- Zoom controls respond immediately
- Image remains visible during operations

### 5. Region Creation Test

1. **Rectangle Region:**
   - Select rectangle tool
   - Click and drag on canvas
   - Verify rectangle preview appears
   - Release to create region
   - Check region appears in correct color

2. **Other Region Types:**
   - Test point, ellipse, polygon, annulus
   - Verify each type creates correctly
   - Check control points are correct

**Expected:**

- Preview shows while drawing
- Region appears after creation
- Region color is unique
- Region persists on canvas

### 6. Profile Plots Test

1. Create a region on an image
2. Wait for profile data
3. Click "Profiles" button
4. Verify spatial/spectral profiles display

**Expected:**

- Profile plots appear in sidebar
- Charts are interactive
- Data matches region selection
- Tabs switch between spatial/spectral

### 7. Histogram Test

1. Create a region
2. Wait for histogram data
3. Click "Histogram" button
4. Verify histogram displays

**Expected:**

- Histogram appears in sidebar
- Bar chart shows data distribution
- Statistics (mean, std dev) display
- Chart is interactive

### 8. Compression Handling Test

1. Configure CARTA backend to send compressed tiles (JPEG/PNG)
2. Open a file
3. Verify tiles decode correctly
4. Check rendering performance

**Expected:**

- Compressed tiles decode successfully
- No decoding errors in console
- Image renders correctly
- Performance is acceptable

### 9. Error Handling Test

1. **Connection Errors:**
   - Stop CARTA backend
   - Verify error message displays
   - Check retry functionality

2. **File Errors:**
   - Try opening invalid file
   - Verify error message
   - Check error recovery

**Expected:**

- Clear error messages
- Retry options available
- Graceful error handling
- No crashes or hangs

### 10. Multi-File Test

1. Open multiple files sequentially
2. Switch between files
3. Verify each file loads correctly
4. Check memory usage

**Expected:**

- Files load independently
- No memory leaks
- Previous files clean up correctly
- Switching is smooth

## Browser Console Checks

Monitor the browser console during testing:

**Good Signs:**

- `CARTA WebSocket connected`
- `CARTA viewer registered successfully`
- `File opened successfully`
- `Received raster tile data`
- `Region set successfully`

**Warning Signs:**

- `Failed to decode tile data`
- `WebSocket connection failed`
- `Failed to open file`
- `Protocol Buffer decode errors`

## Performance Benchmarks

Expected performance metrics:

- **Connection Time:** < 1 second
- **File Open Time:** < 2 seconds (small files)
- **Tile Rendering:** < 100ms per tile
- **Zoom/Pan Response:** < 50ms
- **Region Creation:** < 200ms

## Troubleshooting

### Connection Issues

**Problem:** Cannot connect to CARTA backend

- **Check:** Backend is running on correct port
- **Check:** Firewall/network settings
- **Check:** WebSocket URL is correct
- **Solution:** Verify `VITE_CARTA_BACKEND_URL` environment variable

### Rendering Issues

**Problem:** Images don't render

- **Check:** File opened successfully
- **Check:** Tiles are being received
- **Check:** Canvas context is available
- **Solution:** Check browser console for errors

### Region Issues

**Problem:** Regions don't appear

- **Check:** Region creation succeeded
- **Check:** Control points are valid
- **Check:** Region type is supported
- **Solution:** Verify region data in console

### Profile/Histogram Issues

**Problem:** Profiles/histograms don't display

- **Check:** Region was created
- **Check:** CARTA backend sends profile data
- **Check:** Message handlers are registered
- **Solution:** Verify message types match

## Automated Testing

For automated testing, create test scripts:

```typescript
// Example test structure
describe("CARTA Integration", () => {
  it("should connect to CARTA backend", async () => {
    // Test connection
  });

  it("should open FITS files", async () => {
    // Test file opening
  });

  it("should render images", async () => {
    // Test rendering
  });

  // ... more tests
});
```

## Next Steps

After successful testing:

1. **Performance Optimization:**
   - Profile rendering performance
   - Optimize tile decoding
   - Cache decoded tiles

2. **Feature Enhancement:**
   - Add more region types
   - Implement region editing
   - Add more visualization options

3. **Production Deployment:**
   - Configure production URLs
   - Set up monitoring
   - Document deployment process
