# QA Visualization Framework - Dashboard Integration

This document describes how the QA visualization framework is integrated into the pipeline dashboard via REST API endpoints.

## Overview

The visualization framework is accessible through FastAPI endpoints under `/api/visualization/`. These endpoints enable the dashboard frontend to:

- Browse QA directories and files
- View FITS files with JS9
- Browse CASA Measurement Set tables
- Generate interactive Jupyter notebooks
- Explore QA artifacts

## API Endpoints

### Directory Browsing

#### `GET /api/visualization/browse`

Browse a directory and return file listing.

**Query Parameters:**
- `path` (required): Directory path to browse
- `recursive` (optional, default: false): Recursive directory scan
- `include_pattern` (optional): Include pattern (glob)
- `exclude_pattern` (optional): Exclude pattern (glob)

**Response:**
```json
{
  "path": "/state/qa/my_ms",
  "entries": [
    {
      "name": "image.fits",
      "path": "/state/qa/my_ms/image.fits",
      "type": "fits",
      "size": "2.5 MB",
      "modified_time": "2025-01-15T10:30:00",
      "is_dir": false
    }
  ],
  "total_files": 10,
  "total_dirs": 2,
  "fits_count": 5,
  "casatable_count": 1
}
```

**Example:**
```bash
curl "http://localhost:8000/api/visualization/browse?path=/state/qa&recursive=false"
```

### FITS File Viewing

#### `GET /api/visualization/fits/info`

Get metadata about a FITS file.

**Query Parameters:**
- `path` (required): Path to FITS file

**Response:**
```json
{
  "path": "/state/qa/my_ms/image.fits",
  "exists": true,
  "shape": [100, 100],
  "summary": "100×100+EXT",
  "header_keys": ["SIMPLE", "BITPIX", "NAXIS", ...],
  "naxis": 2,
  "error": null
}
```

#### `GET /api/visualization/fits/view`

Get HTML for viewing a FITS file with JS9.

**Query Parameters:**
- `path` (required): Path to FITS file
- `width` (optional, default: 600): Display width in pixels
- `height` (optional, default: 600): Display height in pixels

**Response:** HTML content with JS9 viewer embedded

**Example:**
```bash
curl "http://localhost:8000/api/visualization/fits/view?path=/state/qa/my_ms/image.fits&width=800&height=800"
```

### CASA Table Browsing

#### `GET /api/visualization/casatable/info`

Get metadata about a CASA Measurement Set table.

**Query Parameters:**
- `path` (required): Path to CASA table (MS directory)

**Response:**
```json
{
  "path": "/stage/dsa110-contimg/ms/my_ms.ms",
  "exists": true,
  "nrows": 1000000,
  "columns": ["DATA", "FLAG", "UVW", "ANTENNA1", "ANTENNA2", ...],
  "keywords": {"MS_VERSION": "2.0", ...},
  "subtables": ["ANTENNA", "FIELD", "SPECTRAL_WINDOW", ...],
  "is_writable": false,
  "error": null
}
```

#### `GET /api/visualization/casatable/view`

Get HTML summary for viewing a CASA table.

**Query Parameters:**
- `path` (required): Path to CASA table
- `max_rows` (optional, default: 10): Maximum rows to display
- `max_cols` (optional, default: 5): Maximum columns to display

**Response:** HTML content with table summary

### Notebook Generation

#### `POST /api/visualization/notebook/generate`

Generate a QA notebook programmatically.

**Request Body:**
```json
{
  "ms_path": "/stage/dsa110-contimg/ms/my_ms.ms",
  "qa_root": "/state/qa/my_ms",
  "artifacts": ["/state/qa/my_ms/image.fits"],
  "title": "QA Report for my_ms",
  "output_path": "/state/qa/my_ms/qa_report.ipynb"
}
```

**Response:**
```json
{
  "notebook_path": "/state/qa/my_ms/qa_report.ipynb",
  "success": true,
  "message": "Notebook generated successfully: /state/qa/my_ms/qa_report.ipynb"
}
```

#### `POST /api/visualization/notebook/qa`

Run MS QA and generate an interactive notebook from the results.

**Request Body:**
```json
{
  "ms_path": "/stage/dsa110-contimg/ms/my_ms.ms",
  "qa_root": "/state/qa/my_ms",
  "thresholds": {},
  "gaintables": null,
  "extra_metadata": null,
  "output_path": "/state/qa/my_ms/qa_report.ipynb"
}
```

**Response:**
```json
{
  "notebook_path": "/state/qa/my_ms/qa_report.ipynb",
  "success": true,
  "message": "QA notebook generated successfully: /state/qa/my_ms/qa_report.ipynb"
}
```

#### `GET /api/visualization/notebook/{notebook_path}`

Serve a generated notebook file for download or viewing.

**Path Parameters:**
- `notebook_path`: Path to notebook file (relative to allowed directories)

**Response:** Notebook file (application/json)

### QA Directory Browsing

#### `GET /api/visualization/qa/browse`

Browse QA output directory interactively.

**Query Parameters:**
- `qa_root` (required): QA root directory

**Response:** Same as `/api/visualization/browse`

## Frontend Integration Examples

### Example 1: Display FITS File in Dashboard

```javascript
// Fetch FITS viewer HTML
async function displayFITS(fitsPath) {
  const response = await fetch(
    `/api/visualization/fits/view?path=${encodeURIComponent(fitsPath)}&width=800&height=800`
  );
  const html = await response.text();
  
  // Insert into dashboard
  document.getElementById('fits-viewer-container').innerHTML = html;
}
```

### Example 2: Browse QA Directory

```javascript
// Browse QA directory
async function browseQADirectory(qaRoot) {
  const response = await fetch(
    `/api/visualization/browse?path=${encodeURIComponent(qaRoot)}&recursive=false`
  );
  const data = await response.json();
  
  // Display file list
  data.entries.forEach(entry => {
    console.log(`${entry.name} (${entry.type})`);
  });
}
```

### Example 3: Generate QA Notebook

```javascript
// Generate QA notebook
async function generateQANotebook(msPath, qaRoot) {
  const response = await fetch('/api/visualization/notebook/qa', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ms_path: msPath,
      qa_root: qaRoot,
      output_path: `${qaRoot}/qa_report.ipynb`
    })
  });
  
  const result = await response.json();
  if (result.success) {
    // Download or display notebook
    window.open(`/api/visualization/notebook/${result.notebook_path}`);
  }
}
```

### Example 4: Display CASA Table Info

```javascript
// Get CASA table information
async function getCasaTableInfo(msPath) {
  const response = await fetch(
    `/api/visualization/casatable/info?path=${encodeURIComponent(msPath)}`
  );
  const info = await response.json();
  
  console.log(`Table: ${info.nrows} rows, ${info.columns.length} columns`);
  console.log(`Subtables: ${info.subtables.length}`);
}
```

## Security Considerations

### Path Validation

All endpoints validate that requested paths are within allowed directories:
- `PIPELINE_STATE_DIR` (default: `state/`)
- `PIPELINE_STATE_DIR/qa` (QA artifacts)
- `PIPELINE_OUTPUT_DIR` (default: `/stage/dsa110-contimg/ms`)

Paths outside these directories will return `403 Forbidden`.

### File Type Validation

- FITS endpoints validate file existence and format
- CASA table endpoints validate directory structure
- Notebook endpoints validate `.ipynb` extension

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters)
- `403`: Forbidden (path outside allowed directories)
- `404`: Not found (file/directory doesn't exist)
- `500`: Internal server error

Error responses include a `detail` field with error message:
```json
{
  "detail": "FITS file not found: /path/to/file.fits"
}
```

## CORS Configuration

The API includes CORS middleware configured for:
- Local development (`localhost`, `127.0.0.1`)
- Production servers (`lxd110h17`)

Additional origins can be configured in `api/routes.py`.

## Next Steps

1. **Frontend Components**: Create React/Vue components that consume these endpoints
2. **JS9 Integration**: Ensure JS9 static files are served correctly
3. **Notebook Viewer**: Add notebook viewing capability in dashboard
4. **Real-time Updates**: Consider WebSocket integration for live QA updates

## Related Documentation

- **Usage Guide**: `docs/QA_VISUALIZATION_USAGE.md`
- **Access Guide**: `docs/QA_VISUALIZATION_ACCESS.md`
- **Implementation Status**: `docs/QA_VISUALIZATION_IMPLEMENTATION_STATUS.md`

