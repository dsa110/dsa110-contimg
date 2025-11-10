# QA Visualization Dashboard - Testing Guide

## Server Restart Required

The visualization API endpoints have been added to the codebase, but **the API server needs to be restarted** to load the new routes.

## Testing the Endpoints

### 1. Restart the API Server

If running via systemd:
```bash
sudo systemctl restart contimg-api.service
```

If running manually:
```bash
# Stop the current server (Ctrl+C or kill process)
# Then restart:
cd /data/dsa110-contimg
conda activate casa6
export PYTHONPATH=/data/dsa110-contimg/src:$PYTHONPATH
uvicorn dsa110_contimg.api.routes:create_app --factory --host 0.0.0.0 --port 8000
```

### 2. Verify Routes Are Registered

Check that visualization endpoints appear in OpenAPI schema:
```bash
curl http://localhost:8000/openapi.json | python3 -m json.tool | grep -A 5 "visualization"
```

Or visit the interactive docs:
```bash
# Open in browser
http://localhost:8000/docs
```

You should see a "visualization" tag with these endpoints:
- `GET /api/visualization/browse`
- `GET /api/visualization/fits/info`
- `GET /api/visualization/fits/view`
- `GET /api/visualization/casatable/info`
- `GET /api/visualization/casatable/view`
- `POST /api/visualization/notebook/generate`
- `POST /api/visualization/notebook/qa`
- `GET /api/visualization/notebook/{notebook_path}`
- `GET /api/visualization/qa/browse`

### 3. Test Directory Browsing

```bash
# Browse QA directory
curl "http://localhost:8000/api/visualization/browse?path=/data/dsa110-contimg/state/qa"

# Browse with filters
curl "http://localhost:8000/api/visualization/browse?path=/data/dsa110-contimg/state/qa&recursive=true&include_pattern=*.fits"
```

### 4. Test FITS File Endpoints

```bash
# Get FITS file info (replace with actual FITS file path)
curl "http://localhost:8000/api/visualization/fits/info?path=/data/dsa110-contimg/state/qa/my_ms/image.fits"

# Get FITS viewer HTML
curl "http://localhost:8000/api/visualization/fits/view?path=/data/dsa110-contimg/state/qa/my_ms/image.fits&width=800&height=800"
```

### 5. Test CASA Table Endpoints

```bash
# Get CASA table info (replace with actual MS path)
curl "http://localhost:8000/api/visualization/casatable/info?path=/stage/dsa110-contimg/ms/my_ms.ms"

# Get CASA table viewer HTML
curl "http://localhost:8000/api/visualization/casatable/view?path=/stage/dsa110-contimg/ms/my_ms.ms&max_rows=10&max_cols=5"
```

### 6. Test Notebook Generation

```bash
# Generate QA notebook
curl -X POST "http://localhost:8000/api/visualization/notebook/qa" \
  -H "Content-Type: application/json" \
  -d '{
    "ms_path": "/stage/dsa110-contimg/ms/my_ms.ms",
    "qa_root": "/data/dsa110-contimg/state/qa/my_ms",
    "output_path": "/data/dsa110-contimg/state/qa/my_ms/qa_report.ipynb"
  }'
```

### 7. Test from Browser

Once the server is restarted, you can test from the browser:

1. Navigate to `http://localhost:8000/docs`
2. Find the "visualization" section
3. Try the "Try it out" feature for each endpoint
4. Or navigate to `http://localhost:8000/ui/` for the dashboard frontend

## Expected Behavior

### Successful Response Examples

**Directory Browsing:**
```json
{
  "path": "/data/dsa110-contimg/state/qa",
  "entries": [
    {
      "name": "image.fits",
      "path": "/data/dsa110-contimg/state/qa/my_ms/image.fits",
      "type": "fits",
      "size": "2.5 MB",
      "modified_time": "2025-11-09T10:30:00",
      "is_dir": false
    }
  ],
  "total_files": 10,
  "total_dirs": 2,
  "fits_count": 5,
  "casatable_count": 1
}
```

**FITS Info:**
```json
{
  "path": "/data/dsa110-contimg/state/qa/my_ms/image.fits",
  "exists": true,
  "shape": [100, 100],
  "summary": "100×100+EXT",
  "header_keys": ["SIMPLE", "BITPIX", "NAXIS", ...],
  "naxis": 2,
  "error": null
}
```

**Notebook Generation:**
```json
{
  "notebook_path": "/data/dsa110-contimg/state/qa/my_ms/qa_report.ipynb",
  "success": true,
  "message": "Notebook generated successfully: /data/dsa110-contimg/state/qa/my_ms/qa_report.ipynb"
}
```

## Troubleshooting

### Routes Not Found (404)

- **Issue**: Server hasn't been restarted
- **Solution**: Restart the API server

### Import Errors

- **Issue**: Module import fails
- **Solution**: Check PYTHONPATH includes `/data/dsa110-contimg/src`

### Path Validation Errors (403)

- **Issue**: Path outside allowed directories
- **Solution**: Ensure paths are within:
  - `PIPELINE_STATE_DIR` (default: `state/`)
  - `PIPELINE_STATE_DIR/qa`
  - `PIPELINE_OUTPUT_DIR` (default: `/stage/dsa110-contimg/ms`)

### File Not Found (404)

- **Issue**: File/directory doesn't exist
- **Solution**: Verify the path exists and is accessible

## Next Steps

Once endpoints are verified:

1. **Frontend Integration**: Create React/Vue components that consume these endpoints
2. **JS9 Testing**: Verify FITS viewing works in browser with JS9
3. **Notebook Viewer**: Add notebook viewing capability to dashboard
4. **Error Handling**: Test error cases and edge conditions

