# QA Visualization Framework - Dashboard Integration Summary

## Overview

The QA visualization framework is now fully integrated into the pipeline dashboard via REST API endpoints. All visualization features are accessible through `/api/visualization/` endpoints.

## What Was Implemented

### 1. API Endpoints (`api/visualization_routes.py`)

Created comprehensive REST API endpoints for:

- **Directory Browsing**: `GET /api/visualization/browse`
- **FITS File Info**: `GET /api/visualization/fits/info`
- **FITS File Viewer**: `GET /api/visualization/fits/view`
- **CASA Table Info**: `GET /api/visualization/casatable/info`
- **CASA Table Viewer**: `GET /api/visualization/casatable/view`
- **Notebook Generation**: `POST /api/visualization/notebook/generate`
- **QA Notebook Generation**: `POST /api/visualization/notebook/qa`
- **Notebook Serving**: `GET /api/visualization/notebook/{path}`
- **QA Directory Browsing**: `GET /api/visualization/qa/browse`

### 2. API Models

Created Pydantic models for request/response:
- `DirectoryEntry` - File/directory information
- `DirectoryListing` - Directory listing response
- `FITSInfo` - FITS file metadata
- `CasaTableInfo` - CASA table metadata
- `NotebookGenerateRequest` - Notebook generation request
- `NotebookGenerateResponse` - Notebook generation response
- `QANotebookRequest` - QA notebook request

### 3. Integration

- Integrated visualization router into main API (`api/routes.py`)
- Added path validation and security checks
- Configured CORS for dashboard access

## Access Points

### For Users (Dashboard Frontend)

All features are accessible via REST API:

```javascript
// Browse QA directory
GET /api/visualization/browse?path=/state/qa&recursive=false

// View FITS file
GET /api/visualization/fits/view?path=/state/qa/my_ms/image.fits

// Generate QA notebook
POST /api/visualization/notebook/qa
{
  "ms_path": "/stage/dsa110-contimg/ms/my_ms.ms",
  "qa_root": "/state/qa/my_ms"
}
```

### For Developers (Python API)

Still accessible via Python imports:

```python
from dsa110_contimg.qa import FITSFile, CasaTable, ls, generate_qa_notebook
```

## Security Features

- **Path Validation**: All endpoints validate paths are within allowed directories
- **File Type Validation**: FITS and CASA table endpoints validate file formats
- **Error Handling**: Comprehensive error handling with appropriate HTTP status codes

## Next Steps for Frontend Integration

1. **Create React/Vue Components**:
   - `FITSViewer` component that calls `/api/visualization/fits/view`
   - `DirectoryBrowser` component that calls `/api/visualization/browse`
   - `CasaTableViewer` component that calls `/api/visualization/casatable/view`
   - `NotebookGenerator` component that calls `/api/visualization/notebook/qa`

2. **JS9 Integration**:
   - Ensure JS9 static files are served correctly
   - Test FITS viewing in browser

3. **Notebook Viewer**:
   - Add notebook viewing capability in dashboard
   - Consider integrating Jupyter notebook viewer (e.g., `@jupyterlab/notebook`)

4. **Real-time Updates**:
   - Consider WebSocket integration for live QA updates
   - Add polling for directory changes

## Documentation

- **Dashboard Integration Guide**: `docs/QA_VISUALIZATION_DASHBOARD_INTEGRATION.md`
- **User Guide**: `docs/QA_VISUALIZATION_USER_GUIDE.md`
- **Usage Guide**: `docs/QA_VISUALIZATION_USAGE.md`
- **Access Guide**: `docs/QA_VISUALIZATION_ACCESS.md`

## Testing

To test the endpoints:

```bash
# Start the API server
python -m dsa110_contimg.api.main

# Test directory browsing
curl "http://localhost:8000/api/visualization/browse?path=/state/qa"

# Test FITS info
curl "http://localhost:8000/api/visualization/fits/info?path=/state/qa/my_ms/image.fits"

# Test notebook generation
curl -X POST "http://localhost:8000/api/visualization/notebook/qa" \
  -H "Content-Type: application/json" \
  -d '{"ms_path": "/stage/dsa110-contimg/ms/my_ms.ms", "qa_root": "/state/qa/my_ms"}'
```

## Status

✅ **Complete**: All API endpoints implemented and integrated
✅ **Complete**: Security and validation in place
✅ **Complete**: Documentation created
🚧 **Pending**: Frontend components (to be implemented by frontend team)
🚧 **Pending**: JS9 integration testing in browser
🚧 **Pending**: Notebook viewer integration

