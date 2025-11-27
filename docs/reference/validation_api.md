# Validation API Reference

## Overview

The DSA-110 Continuum Imaging Pipeline provides comprehensive validation
endpoints for assessing image quality, astrometry, flux scale, source
completeness, photometry, variability, mosaics, streaming, and database
consistency. All endpoints are prefixed with the base path
api/qa/images/{image_id}.

**Note:** The validation system uses a centralized configuration system. See
[Validation Guide](api_reference.md) for details on using the
configuration system in Python.

## Endpoints

### Get Catalog Validation Results

**GET** `/api/qa/images/{image_id}/catalog-validation`

Retrieve validation results for an image (cached if available).

**Parameters:**

- `image_id` (path): Image ID (integer) or image path (string)
- `catalog` (query, default: "nvss"): Reference catalog ("nvss" or "vlass")
- `validation_type` (query, default: "all"): Validation type ("astrometry",
  "flux_scale", "source_counts", or "all")

**Response:**

```json
{
  "astrometry": {
    "validation_type": "astrometry",
    "n_matched": 157,
    "mean_offset_ra": 0.0001,
    "mean_offset_dec": -0.0002,
    "rms_offset_arcsec": 0.85,
    "max_offset_arcsec": 2.3,
    "has_issues": false,
    "has_warnings": false,
    "issues": [],
    "warnings": []
  },
  "flux_scale": {
    "validation_type": "flux_scale",
    "n_matched": 142,
    "mean_flux_ratio": 1.02,
    "rms_flux_ratio": 0.15,
    "flux_scale_error": 0.02,
    "has_issues": false,
    "has_warnings": false
  },
  "source_counts": {
    "validation_type": "source_counts",
    "n_matched": 157,
    "n_catalog": 206,
    "n_detected": 162,
    "completeness": 0.762,
    "completeness_limit_jy": 0.00176,
    "has_issues": false,
    "has_warnings": false
  }
}
```

**Example:**

```bash
curl "http://localhost:8000/api/qa/images/123/catalog-validation?catalog=nvss&validation_type=all"
```

### Run Catalog Validation

**POST** `/api/qa/images/{image_id}/catalog-validation/run`

Run validation tests for an image and return results.

**Parameters:**

- `image_id` (path): Image ID (integer) or image path (string)
- `catalog` (query, default: "nvss"): Reference catalog ("nvss" or "vlass")
- `validation_types` (body, default: ["astrometry", "flux_scale",
  "source_counts"]): List of validation types to run

**Request Body:**

```json
{
  "catalog": "nvss",
  "validation_types": ["astrometry", "flux_scale", "source_counts"]
}
```

**Response:** Same as GET endpoint above.

**Example:**

```bash
curl -X POST "http://localhost:8000/api/qa/images/123/catalog-validation/run" \
  -H "Content-Type: application/json" \
  -d '{"catalog": "nvss", "validation_types": ["astrometry", "flux_scale"]}'
```

### Get HTML Validation Report

**GET** `/api/qa/images/{image_id}/validation-report.html`

Generate and return HTML validation report.

**Parameters:**

- `image_id` (path): Image ID (integer) or image path (string)
- `catalog` (query, default: "nvss"): Reference catalog ("nvss" or "vlass")
- `validation_types` (query, default: ["astrometry", "flux_scale",
  "source_counts"]): List of validation types to include
- `save_to_file` (query, default: false): Whether to save HTML report to file in
  QA directory

**Response:** HTML content (Content-Type: text/html)

**Example:**

```bash
# Get HTML report (returns HTML directly)
curl "http://localhost:8000/api/qa/images/123/validation-report.html?catalog=nvss&save_to_file=true"

# Open in browser
open "http://localhost:8000/api/qa/images/123/validation-report.html?catalog=nvss"
```

**Report Features:**

- Summary dashboard with overall status
- Data type banner (test vs. real data)
- Image visualization
- Astrometry metrics and plots
- Flux scale metrics and plots
- Source counts completeness analysis
- Enhanced visualizations:
  - Spatial distribution plots
  - Flux vs. offset correlation
  - Validation summary dashboard

### Generate HTML Validation Report

**POST** `/api/qa/images/{image_id}/validation-report/generate`

Generate HTML validation report and save to file.

**Parameters:**

- `image_id` (path): Image ID (integer) or image path (string)
- `catalog` (query, default: "nvss"): Reference catalog ("nvss" or "vlass")
- `validation_types` (body, default: ["astrometry", "flux_scale",
  "source_counts"]): List of validation types to include
- `output_path` (body, optional): Custom output path. If None, saves to QA
  directory.

**Request Body:**

```json
{
  "catalog": "nvss",
  "validation_types": ["astrometry", "flux_scale", "source_counts"],
  "output_path": "/path/to/custom/report.html"
}
```

**Response:**

```json
{
  "success": true,
  "report_path": "/path/to/report.html",
  "image_path": "/path/to/image.fits",
  "catalog": "nvss"
}
```

**Example:**

```bash
curl -X POST "http://localhost:8000/api/qa/images/123/validation-report/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "catalog": "nvss",
    "validation_types": ["astrometry", "flux_scale", "source_counts"],
    "output_path": "/data/reports/validation_123.html"
  }'
```

## Validation Result Schema

### Astrometry Result

```json
{
  "validation_type": "astrometry",
  "image_path": "/path/to/image.fits",
  "catalog_used": "nvss",
  "n_matched": 157,
  "mean_offset_ra": 0.0001,  // degrees
  "mean_offset_dec": -0.0002,  // degrees
  "rms_offset_arcsec": 0.85,
  "max_offset_arcsec": 2.3,
  "has_issues": false,
  "has_warnings": false,
  "issues": [],
  "warnings": [],
  "matched_pairs": [  // Internal use only
    [detected_ra, detected_dec, catalog_ra, catalog_dec, offset_arcsec],
    ...
  ]
}
```

### Flux Scale Result

```json
{
  "validation_type": "flux_scale",
  "image_path": "/path/to/image.fits",
  "catalog_used": "nvss",
  "n_matched": 142,
  "mean_flux_ratio": 1.02,  // detected / catalog
  "rms_flux_ratio": 0.15,
  "flux_scale_error": 0.02,  // fractional error
  "has_issues": false,
  "has_warnings": false,
  "issues": [],
  "warnings": [],
  "matched_fluxes": [  // Internal use only
    [detected_flux_jy, catalog_flux_jy, ratio],
    ...
  ]
}
```

### Source Counts Result

```json
{
  "validation_type": "source_counts",
  "image_path": "/path/to/image.fits",
  "catalog_used": "nvss",
  "n_matched": 157,
  "n_catalog": 206,
  "n_detected": 162,
  "completeness": 0.762,  // overall completeness fraction
  "completeness_limit_jy": 0.00176,  // flux at which completeness drops below threshold
  "completeness_bins_jy": [0.00176, 0.00441, ...],  // flux bin edges
  "completeness_per_bin": [0.98, 0.90, ...],  // completeness per bin
  "catalog_counts_per_bin": [50, 40, ...],
  "detected_counts_per_bin": [49, 36, ...],
  "has_issues": false,
  "has_warnings": false,
  "issues": [],
  "warnings": []
}
```

## Error Responses

All endpoints may return standard HTTP error codes:

- **400 Bad Request**: Invalid parameters
- **404 Not Found**: Image not found
- **500 Internal Server Error**: Validation failed

Error response format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Configuration

Validation parameters can be configured via:

1. **YAML Configuration File** (recommended):

   ```yaml
   validation:
     enabled: true
     catalog: "nvss"
     validation_types: ["astrometry", "flux_scale", "source_counts"]
     generate_html_report: true
     min_snr: 5.0
     search_radius_arcsec: 10.0
     completeness_threshold: 0.95
   ```

2. **Environment Variables**:

   ```bash
   export PIPELINE_VALIDATION_ENABLED=true
   export PIPELINE_VALIDATION_CATALOG=nvss
   export PIPELINE_VALIDATION_MIN_SNR=5.0
   ```

3. **API Parameters**: Override defaults per request

## Examples

### Complete Validation Workflow

```bash
# 1. Run validation
RESULT=$(curl -X POST "http://localhost:8000/api/qa/images/123/catalog-validation/run" \
  -H "Content-Type: application/json" \
  -d '{"catalog": "nvss"}')

# 2. Generate HTML report
curl -X POST "http://localhost:8000/api/qa/images/123/validation-report/generate" \
  -H "Content-Type: application/json" \
  -d '{"catalog": "nvss", "output_path": "/data/reports/validation_123.html"}'

# 3. View report
open "http://localhost:8000/api/qa/images/123/validation-report.html?catalog=nvss"
```

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Run validation
response = requests.post(
    f"{BASE_URL}/qa/images/123/catalog-validation/run",
    json={"catalog": "nvss", "validation_types": ["astrometry", "flux_scale"]}
)
results = response.json()

# Check astrometry
astrometry = results["astrometry"]
if astrometry["rms_offset_arcsec"] > 2.0:
    print(f"Warning: High RMS offset: {astrometry['rms_offset_arcsec']:.2f} arcsec")

# Generate HTML report
response = requests.post(
    f"{BASE_URL}/qa/images/123/validation-report/generate",
    json={"catalog": "nvss"}
)
report_info = response.json()
print(f"Report saved to: {report_info['report_path']}")
```

## See Also

- [Validation Guide](api_reference.md)
- Configuration Guide
- [Pipeline Overview](../architecture/pipeline/pipeline_overview.md)
