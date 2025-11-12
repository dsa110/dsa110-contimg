# JS9 CASA Analysis API Reference

**Date:** 2025-11-12  
**Status:** complete  
**Related:** [Dashboard API](../reference/dashboard_backend_api.md)

---

## Endpoint

**POST** `/api/visualization/js9/analysis`

Execute CASA analysis tasks on FITS images for JS9 viewer integration.

---

## Request

### Headers

```
Content-Type: application/json
```

### Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | string | Yes | CASA task name: `imstat`, `imfit`, `imview`, `specflux`, or `imval` |
| `image_path` | string | Yes | Path to FITS image file (must be accessible to server) |
| `region` | object | No | JS9 region object (pixel coordinates) |
| `parameters` | object | No | Task-specific parameters |

### Region Object Format

```json
{
  "shape": "circle",
  "x": 100,
  "y": 200,
  "r": 50
}
```

**Supported shapes:**
- `circle` or `c`: Requires `x`, `y`, `r` (radius)
- `box` or `rectangle` or `r`: Requires `x`, `y`, `width`, `height`

### Task-Specific Parameters

#### imstat
No special parameters.

#### imfit
```json
{
  "model": "gaussian",
  "background": true
}
```

#### imview (contour generation)
```json
{
  "n_levels": 10,
  "smoothing_sigma": 1.0
}
```

#### specflux
No special parameters.

#### imval
```json
{
  "box": "10,20,100,200",
  "stokes": "I"
}
```

### Example Request

```json
{
  "task": "imstat",
  "image_path": "/stage/dsa110-contimg/images/2025-01-15T12:00:00.image.fits",
  "region": {
    "shape": "circle",
    "x": 256,
    "y": 256,
    "r": 50
  },
  "parameters": {}
}
```

---

## Response

### Success Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "task": "imstat",
  "result": {
    "DATA": {
      "mean": 0.001234,
      "std": 0.000567,
      "min": -0.002100,
      "max": 0.015600,
      "sum": 1234.567890,
      "rms": 0.000890,
      "npts": 7854
    }
  },
  "execution_time_sec": 0.234
}
```

### Error Response

**Status Code:** `400 Bad Request` or `500 Internal Server Error`

```json
{
  "success": false,
  "task": "imstat",
  "error": "Image file not found: /path/to/image.fits",
  "execution_time_sec": 0.001
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether task executed successfully |
| `task` | string | Task name that was executed |
| `result` | object | Task results (structure varies by task) |
| `error` | string | Error message (only if success=false) |
| `execution_time_sec` | float | Execution time in seconds (< 0.01 for cached) |

---

## Task Result Formats

### imstat Result

```json
{
  "DATA": {
    "mean": 0.001234,
    "std": 0.000567,
    "min": -0.002100,
    "max": 0.015600,
    "sum": 1234.567890,
    "rms": 0.000890,
    "npts": 7854
  }
}
```

### imfit Result

```json
{
  "fit": {
    "amplitude": 0.015,
    "center": [123.45, 67.89],
    "major_axis": 2.3,
    "minor_axis": 1.8,
    "pa": 45.0,
    "background": 0.001
  }
}
```

### imview Result (Contour Generation)

```json
{
  "contour_levels": [0.001, 0.002, 0.003, ...],
  "contour_paths": [
    {
      "level": 0.001,
      "paths": [
        {
          "x": [10, 11, 12, ...],
          "y": [20, 21, 22, ...]
        }
      ]
    }
  ],
  "image_shape": [512, 512],
  "data_range": {
    "min": 0.0001,
    "max": 0.02
  }
}
```

### specflux Result

```json
{
  "flux": {
    "DATA": {
      "mean": 0.001234,
      "sum": 1234.567890
    }
  },
  "note": "Spectral flux extraction via imstat"
}
```

### imval Result

```json
{
  "values": [0.001, 0.002, 0.0015, ...],
  "shape": [512, 512],
  "mask": [true, true, false, ...]
}
```

---

## Caching

Results are automatically cached based on:
- Task name
- Image path
- Region (if provided)
- Parameters

**Cache Behavior:**
- Cache key: SHA256 hash of request parameters
- Cache size: Maximum 100 entries (FIFO eviction)
- Cache duration: Until server restart or eviction
- Cached results: Execution time < 0.01s

**Cache Key Generation:**
```
SHA256(task + image_path + region_json + parameters_json)
```

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| `400` | Invalid request (invalid task name, non-FITS file, etc.) |
| `404` | Image file not found |
| `500` | Server error (CASA task failure, etc.) |

### Common Errors

**Invalid Task:**
```json
{
  "detail": "Invalid task 'invalid_task'. Valid tasks: ['imstat', 'imfit', 'imview', 'specflux', 'imval']"
}
```

**File Not Found:**
```json
{
  "detail": "Image file not found: /path/to/image.fits"
}
```

**Not a FITS File:**
```json
{
  "detail": "File is not a FITS image: /path/to/file.txt"
}
```

---

## Implementation Details

### Region Conversion

JS9 pixel coordinates are converted to CASA region format:

**Circle:**
```
circle[[x,y],radius]pix
```

**Box:**
```
box[[x,y],[width,height]]pix
```

### CASA Task Execution

Tasks are executed using `casatasks` module in the CASA6 environment:

```python
from casatasks import imstat, imfit, imval
```

### Result Serialization

Results are converted to JSON-serializable format:
- NumPy arrays → lists
- NumPy scalars → Python floats/ints
- Nested dictionaries → recursively converted

---

## Rate Limiting

Currently no rate limiting is implemented. Consider implementing if:
- High traffic expected
- Long-running tasks (imfit can be slow)
- Resource constraints

---

## Security Considerations

1. **Path Validation**: Image paths are validated to ensure they exist and are FITS files
2. **Region Validation**: Region coordinates are checked for validity
3. **Cache Security**: SHA256 used for cache keys (not MD5)
4. **Error Handling**: Errors don't expose sensitive information
5. **Input Sanitization**: All inputs are validated before use

---

## Examples

### Example 1: Image Statistics

```bash
curl -X POST http://localhost:8000/api/visualization/js9/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "task": "imstat",
    "image_path": "/stage/dsa110-contimg/images/image.fits"
  }'
```

### Example 2: Region-Based Statistics

```bash
curl -X POST http://localhost:8000/api/visualization/js9/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "task": "imstat",
    "image_path": "/stage/dsa110-contimg/images/image.fits",
    "region": {
      "shape": "circle",
      "x": 256,
      "y": 256,
      "r": 50
    }
  }'
```

### Example 3: Contour Generation with Parameters

```bash
curl -X POST http://localhost:8000/api/visualization/js9/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "task": "imview",
    "image_path": "/stage/dsa110-contimg/images/image.fits",
    "parameters": {
      "n_levels": 15,
      "smoothing_sigma": 2.0
    }
  }'
```

---

## Related Documentation

- [How-To Guide: JS9 CASA Analysis](../how-to/js9_casa_analysis.md)
- [Dashboard API Reference](./dashboard_backend_api.md)
- [CASA Tasks Documentation](https://casa.nrao.edu/docs/casa-reference/)

