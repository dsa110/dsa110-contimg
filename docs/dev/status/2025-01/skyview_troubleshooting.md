# SkyView Troubleshooting Guide

## Issue: "Loading pipeline status" or Infinite Loading Spinner

### Diagnosis

The message "Loading pipeline status" appears on the **Dashboard page**, not SkyView. If you're seeing this on SkyView, there may be a routing issue.

### Expected Behavior

**SkyView Page:**
- Should show "Image Browser" in the left sidebar
- Should display a list of images (11 synthetic images available)
- Should show "No image selected" in the main viewer area

**If you see "Loading pipeline status":**
- You're likely on the Dashboard page (`/dashboard`)
- Navigate to `/skyview` to see the SkyView page

### Quick Checks

1. **Verify API is running:**
   ```bash
   docker ps | grep contimg-api
   curl http://localhost:8010/api/images?limit=1
   ```

2. **Check frontend container:**
   ```bash
   docker ps | grep contimg-frontend
   ```

3. **Verify images in database:**
   ```bash
   /opt/miniforge/envs/casa6/bin/python -c "
   from pathlib import Path
   import sqlite3
   db = Path('/data/dsa110-contimg/state/products.sqlite3')
   conn = sqlite3.connect(str(db))
   cur = conn.execute('SELECT COUNT(*) FROM images')
   print(f'Images in database: {cur.fetchone()[0]}')
   "
   ```

### Common Issues

#### 1. API Container Not Running
**Symptom:** Infinite loading, no data

**Solution:**
```bash
cd /data/dsa110-contimg/ops/docker
docker-compose up -d api
```

#### 2. CORS/Connection Issues
**Symptom:** Network errors in browser console

**Solution:**
- Check Vite proxy configuration in `vite.config.ts`
- Verify API_PROXY_TARGET environment variable
- Check browser console for CORS errors

#### 3. No Images in Database
**Symptom:** "No images found" message

**Solution:**
```bash
# Generate synthetic images
/opt/miniforge/envs/casa6/bin/python scripts/create_synthetic_images.py
```

#### 4. Wrong Page/Route
**Symptom:** Seeing "Loading pipeline status" on SkyView

**Solution:**
- Navigate to `http://localhost:5173/skyview` (not `/dashboard`)
- Check browser URL bar

### Verification Steps

1. **API Health Check:**
   ```bash
   curl http://localhost:8010/api/status
   curl http://localhost:8010/api/images?limit=2
   ```

2. **Frontend Health Check:**
   - Open browser console (F12)
   - Check for errors
   - Verify network requests to `/api/images`

3. **Database Check:**
   ```bash
   # Should return 11
   /opt/miniforge/envs/casa6/bin/python -c "
   import sqlite3
   from pathlib import Path
   db = Path('/data/dsa110-contimg/state/products.sqlite3')
   conn = sqlite3.connect(str(db))
   print(conn.execute('SELECT COUNT(*) FROM images').fetchone()[0])
   "
   ```

### Expected API Response

When working correctly, `/api/images?limit=2` should return:
```json
{
  "items": [
    {
      "id": 1,
      "path": "/data/dsa110-contimg/state/images/2025-01-15T12:00:00.img.image.fits",
      "type": "5min",
      "pbcor": false,
      "noise_jy": 0.001,
      "beam_major_arcsec": 12.5
    }
  ],
  "total": 11
}
```

### Next Steps

If API is running and returning data but frontend still shows loading:

1. **Check browser console** for JavaScript errors
2. **Verify Vite proxy** is configured correctly
3. **Check network tab** to see if requests are being made
4. **Restart frontend container** if needed:
   ```bash
   docker restart contimg-frontend
   ```

