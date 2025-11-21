# Directory Access and CARTA Integration Issues

**Date**: November 21, 2025

## Issues Identified

### 1. Sky View Image Browser Shows No Files

**Problem**: The Image Browser on the Sky View page returns empty results.

**Root Cause**:

- The Image Browser uses the `/api/images` endpoint which queries a PostgreSQL
  database
- The database has no registered images (returns `{"items":[],"total":0}`)
- Images need to be registered in the database before they appear in the browser

**Solution Options**:

**Option A: Register existing FITS files in database** (Recommended)

- Run the image registration script/command to scan `/stage/dsa110-contimg` and
  add files to database
- This is the intended workflow for the application

**Option B: Add filesystem-based image browsing**

- Modify the Image Browser to use the DirectoryBrowser component
- Point it to `/stage/dsa110-contimg` where FITS files exist
- Files found: `/stage/dsa110-contimg/tmp/`, `/stage/dsa110-contimg/test_data/`

### 2. CARTA Integration Not Working

**Two separate issues**:

#### Issue 2A: Iframe Mode Shows "Content is Blocked"

**Problem**: Browser security policy blocks iframe embedding from
`http://localhost:9003`

**Root Cause**:

- CARTA frontend running on port 9003 doesn't allow iframe embedding
- Same-origin policy or X-Frame-Options header blocks the embed
- This is a CARTA server configuration issue, not frontend code

**Solution**:

- Start CARTA with proper CORS/frame options
- Or use Option 2 (WebSocket) instead, which doesn't use iframes

#### Issue 2B: WebSocket Mode Shows "Connection Failed"

**Problem**: WebSocket connection to `ws://localhost:9002` fails

**Root Cause**:

- CARTA backend server not running on port 9002
- Backend URL points to localhost but service may not be started

**Solution**:

```bash
# Start CARTA backend on port 9002
carta_backend --port 9002 --base /stage/dsa110-contimg

# Start CARTA frontend on port 9003
# Point it to backend ws://localhost:9002
```

### 3. File Browsers Cannot Access `/stage/`

**Problem**: DirectoryBrowser validation rejects paths outside allowed
directories

**Current Allowed Directories**:

1. `state` (resolves to `/data/dsa110-contimg/state`)
2. `state/qa` (resolves to `/data/dsa110-contimg/state/qa`)
3. `/stage/dsa110-contimg/raw/ms` (from `PIPELINE_OUTPUT_DIR` env var)

**Files Actually Located At**:

- `/stage/dsa110-contimg/tmp/` - Test mosaics and processed images
- `/stage/dsa110-contimg/test_data/` - Test datasets with FITS files
- `/stage/dsa110-contimg/raw/ms` - Raw measurement sets (currently allowed)

**Backend Code Location**:
`/data/dsa110-contimg/src/dsa110_contimg/api/visualization_routes.py`

```python
def browse_directory(path: str, ...):
    # Current allowed paths:
    base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
    qa_base = base_state / "qa"
    output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/raw/ms"))

    for base_dir in [base_state, qa_base, output_dir]:
        # Validation happens here
```

## Recommended Solutions

### Fix 1: Expand Backend Allowed Directories

Add `/stage/dsa110-contimg` as an allowed base directory in
`visualization_routes.py`:

```python
def browse_directory(path: str, ...):
    base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
    qa_base = base_state / "qa"
    output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/raw/ms"))
    stage_base = Path("/stage/dsa110-contimg")  # ADD THIS

    for base_dir in [base_state, qa_base, output_dir, stage_base]:  # ADD stage_base
        # ... rest of validation
```

### Fix 2: Update DirectoryBrowser Initial Path

Change `DirectoryBrowser` component to default to `/stage/dsa110-contimg`
instead of `/data/dsa110-contimg/state/qa`:

**File**: `/data/dsa110-contimg/frontend/src/components/QA/DirectoryBrowser.tsx`

```tsx
export default function DirectoryBrowser({
  initialPath = "/stage/dsa110-contimg",  // Changed from "/data/dsa110-contimg/state/qa"
  onSelectFile,
  onSelectDirectory,
}: DirectoryBrowserProps) {
```

### Fix 3: Setup CARTA Services

Create systemd services or docker-compose entries for CARTA:

```yaml
# docker-compose.yml addition
carta-backend:
  image: cartavis/carta-backend:latest
  ports:
    - "9002:9002"
  volumes:
    - /stage/dsa110-contimg:/data:ro
  command: --port 9002 --base /data

carta-frontend:
  image: cartavis/carta-frontend:latest
  ports:
    - "9003:80"
  environment:
    - BACKEND_URL=ws://carta-backend:9002
```

### Fix 4: Register Images in Database

Add a script or API endpoint to scan and register FITS files:

```python
# Example registration logic
from pathlib import Path
from dsa110_contimg.database import products

def register_images_from_directory(base_path: Path):
    for fits_file in base_path.rglob("*.fits"):
        # Extract metadata from FITS header
        # Register in products database
        products.register_image(
            path=str(fits_file),
            image_type="mosaic",  # or detect from filename
            # ... other metadata
        )
```

## Testing Plan

1. **Test Directory Access**:

   ```bash
   curl "http://localhost:8000/api/directory/list?path=/stage/dsa110-contimg/tmp"
   # Should return file list, not 404
   ```

2. **Test CARTA Backend**:

   ```bash
   curl http://localhost:9002/health
   # Should return healthy status
   ```

3. **Test CARTA Frontend**:
   - Open http://localhost:9003
   - Should show CARTA interface (not blocked)

4. **Test Image Registration**:
   ```bash
   curl "http://localhost:8000/api/images?limit=5"
   # Should return registered images, not {"items":[],"total":0}
   ```

## Files to Modify

1. **Backend**:
   `/data/dsa110-contimg/src/dsa110_contimg/api/visualization_routes.py`
   - Add `/stage/dsa110-contimg` to allowed directories

2. **Frontend**:
   `/data/dsa110-contimg/frontend/src/components/QA/DirectoryBrowser.tsx`
   - Change default initialPath

3. **Frontend**:
   `/data/dsa110-contimg/frontend/src/components/DataBrowser/FileBrowser.tsx`
   - Update initialPath prop to DirectoryBrowser

4. **CARTA**: Setup CARTA services (docker-compose or systemd)

5. **Database**: Run image registration script

## Priority

1. **HIGH**: Expand backend allowed directories (enables /stage access)
2. **HIGH**: Register images in database (populates Image Browser)
3. **MEDIUM**: Setup CARTA services (enables visualization)
4. **LOW**: Update default paths (convenience improvement)

## Next Steps

1. Modify backend to allow `/stage/dsa110-contimg`
2. Restart backend API
3. Test directory browsing
4. Register FITS files in database
5. Setup CARTA services if visualization needed
