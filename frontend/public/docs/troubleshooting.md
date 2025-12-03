# DSA-110 Pipeline Troubleshooting Guide

This guide provides troubleshooting steps for common errors encountered when
using the DSA-110 Continuum Imaging Pipeline.

---

## Table of Contents

- [Calibration Errors](#calibration-errors)
  - [Missing Calibration Table](#calibration_missing_table)
  - [Calibration Apply Failed](#calibration_apply_failed)
- [Imaging Errors](#imaging-errors)
  - [TCLEAN Failed](#imaging_tclean_failed)
  - [Image Not Found](#image_not_found)
- [Data Errors](#data-errors)
  - [Measurement Set Not Found](#ms_not_found)
  - [Source Not Found](#source_not_found)
  - [Database Unavailable](#db_unavailable)
- [Photometry Errors](#photometry-errors)
  - [Bad Coordinates](#photometry_bad_coords)
- [Service Errors](#service-errors)
  - [Streaming Status Stale](#streaming_stale)
- [Validation Errors](#validation-errors)
  - [Input Validation Failed](#validation_failed)
- [Browser Console Warnings](#browser-console-warnings)
  - [React DevTools DCE Warning](#react-devtools-dce-warning)
  - [Duplicate Custom Element Definition](#duplicate-custom-element-definition)
  - [CSP frame-ancestors Warning](#csp-frame-ancestors-warning)
- [Server CSP Configuration](#server-csp-configuration)

---

## Calibration Errors

<a id="calibration_missing_table"></a>

### Missing Calibration Table

**Error Code:** `CAL_TABLE_MISSING`

**What it means:** The pipeline could not find a calibration table for the
specified Measurement Set. This typically happens when:

- Calibration has not been run for this observation
- The calibration table path is incorrect
- The calibration table has been moved or deleted

**How to fix:**

1. Check if calibration has been run for this observation
2. If not, run the calibration pipeline stage first
3. If calibration was run, verify the table path in the job logs
4. Re-run calibration if the table is corrupted or missing

**Related commands:**

```bash
# Check calibration status
dsa110-cli cal-status --ms /path/to/your.ms

# Run calibration
dsa110-cli calibrate --ms /path/to/your.ms --cal-type all
```

---

<a id="calibration_apply_failed"></a>

### Calibration Apply Failed

**Error Code:** `CAL_APPLY_FAILED`

**What it means:** The pipeline attempted to apply calibration solutions but
encountered an error. Common causes:

- Incompatible calibration table (different frequency setup)
- Corrupted calibration solutions
- Missing antenna or spectral window in the table

**How to fix:**

1. Check the job logs for specific error messages
2. Verify the calibration table matches the observation setup
3. Re-run calibration with fresh solutions
4. If using bandpass calibration, ensure the frequency coverage matches

**Related commands:**

```bash
# View cal table info
dsa110-cli cal-info --table /path/to/cal.tbl

# Apply calibration manually
dsa110-cli apply-cal --ms /path/to/your.ms --cal /path/to/cal.tbl
```

---

## Imaging Errors

<a id="imaging_tclean_failed"></a>

### TCLEAN Failed

**Error Code:** `IMAGE_CLEAN_FAILED`

**What it means:** The CASA `tclean` imaging task failed. This can happen due
to:

- Insufficient memory for the image size
- Invalid imaging parameters (cell size, image size)
- Corrupted or empty visibility data
- Disk space exhaustion

**How to fix:**

1. Check the imaging parameters are appropriate for your data:
   - Cell size should be ~1/5 of the synthesized beam
   - Image size should capture the primary beam
2. Ensure sufficient disk space and memory
3. Check that the input MS has valid data
4. Review the CASA log for specific errors

**Common parameter issues:**

```python
# Cell size too large -> undersampled image
# Cell size too small -> unnecessarily large image, memory issues

# Recommended starting point:
cell = '1arcsec'  # Adjust based on your resolution
imsize = [4096, 4096]  # Adjust based on field of view
```

---

<a id="image_not_found"></a>

### Image Not Found

**Error Code:** `IMAGE_NOT_FOUND`

**What it means:** The requested image could not be found in the database or
filesystem.

**How to fix:**

1. Verify the image ID is correct
2. Check if the imaging pipeline has completed
3. Ensure the image hasn't been archived or deleted
4. Search for the image using the data browser

---

## Data Errors

<a id="ms_not_found"></a>

### Measurement Set Not Found

**Error Code:** `MS_NOT_FOUND`

**What it means:** The specified Measurement Set path does not exist or is
inaccessible.

**How to fix:**

1. Verify the path is correct (check for typos)
2. Ensure you have read permissions for the directory
3. Check if the MS has been moved or archived
4. Use the MS browser to locate available datasets

**Related commands:**

```bash
# List available MS files
dsa110-cli list-ms --date 2025-01-15

# Check MS path
ls -la /path/to/your.ms
```

---

<a id="source_not_found"></a>

### Source Not Found

**Error Code:** `SOURCE_NOT_FOUND`

**What it means:** The requested source ID does not exist in the source catalog.

**How to fix:**

1. Verify the source ID is correct
2. Check if source extraction has been run on the relevant images
3. Use the source search to find sources by coordinates
4. The source may be below the detection threshold

---

<a id="db_unavailable"></a>

### Database Unavailable

**Error Code:** `PRODUCTS_DB_UNAVAILABLE`

**What it means:** The products database (SQLite) is not accessible. This
prevents queries for images, sources, and pipeline products.

**How to fix:**

1. Check the database file exists at the configured path
2. Verify file permissions allow read/write access
3. Ensure no other process has locked the database
4. If the database is corrupted, restore from backup

**Configuration:**

```bash
# Check database path in config
cat ~/.dsa110-contimg/config.yaml | grep db_path

# Test database connectivity
dsa110-cli db-check
```

---

## Photometry Errors

<a id="photometry_bad_coords"></a>

### Bad Coordinates

**Error Code:** `PHOTOMETRY_BAD_COORDS`

**What it means:** The coordinates provided for photometry measurement are
invalid or outside the image bounds.

**How to fix:**

1. Verify RA and Dec are in valid ranges:
   - RA: 0° to 360° (or 0h to 24h)
   - Dec: -90° to +90°
2. Ensure the coordinates are within the image field of view
3. Check the coordinate format matches what's expected (degrees vs. sexagesimal)

**Coordinate formats accepted:**

```
# Degrees (decimal)
ra=180.0, dec=-30.0

# Sexagesimal (hours for RA, degrees for Dec)
ra="12:00:00", dec="-30:00:00"
```

---

## Service Errors

<a id="streaming_stale"></a>

### Streaming Status Stale

**Error Code:** `STREAMING_STALE_STATUS`

**What it means:** The streaming service status has not been updated recently
(>120 seconds). This may indicate:

- The streaming service has stopped
- Network connectivity issues
- Clock synchronization problems

**How to fix:**

1. Check if the streaming service is running
2. Verify network connectivity to the streaming host
3. Check system clock synchronization
4. Restart the streaming service if necessary

**Related commands:**

```bash
# Check streaming service status
systemctl status dsa110-streaming

# Restart streaming service
sudo systemctl restart dsa110-streaming

# Check logs
journalctl -u dsa110-streaming -f
```

---

## Validation Errors

<a id="validation_failed"></a>

### Input Validation Failed

**Error Code:** `VALIDATION_FAILED`

**What it means:** The request contained invalid or missing required fields. The
error details will show which fields failed validation.

**How to fix:**

1. Review the validation errors in the response
2. Ensure all required fields are provided
3. Check field formats match the expected types
4. Refer to the API documentation for field requirements

**Common validation issues:**

- Missing required fields
- Invalid date formats (use ISO 8601: `2025-01-15T10:30:00Z`)
- Invalid coordinate values
- Path characters that need URL encoding

---

## Browser Console Warnings

Some console warnings you may see are **not errors in the application** but come
from browser extensions or development tools:

### React DevTools DCE Warning

**Message:** `React is running in production mode, but dead code elimination has not been applied`

**Source:** React DevTools browser extension (`installHook.js`)

**Why it happens:** This warning comes from the React DevTools extension when
running the development server. It's checking if your build has proper dead code
elimination.

**Resolution:** This is expected in development. The warning will not appear in
production builds (`npm run build`). You can safely ignore it during development.

### Duplicate Custom Element Definition

**Message:** `A custom element with name 'mce-autosize-textarea' has already been defined`

**Source:** Browser extensions (TinyMCE-related extensions, content editors)

**Why it happens:** A browser extension is trying to register a custom element
that's already registered. This is not from the DSA-110 application.

**Resolution:** Disable conflicting browser extensions, or ignore the warning.
It does not affect application functionality.

### CSP frame-ancestors Warning

**Message:** `The Content Security Policy directive 'frame-ancestors' is ignored when delivered via a <meta> element`

**Source:** Browser CSP parser

**Why it happens:** The `frame-ancestors` directive only works when set via HTTP
headers, not `<meta>` tags.

**Resolution:** For production, configure your web server to send CSP headers.
See the [Server Configuration](#server-csp-configuration) section below.

---

<a id="server-csp-configuration"></a>

## Server CSP Configuration

For production deployments, set Content Security Policy via HTTP headers instead
of `<meta>` tags. Here are configurations for common servers:

### FastAPI (Python Backend)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: blob: https://js9.si.edu; "
            "style-src 'self' 'unsafe-inline' https://js9.si.edu; "
            "script-src 'self' https://js9.si.edu https://cdnjs.cloudflare.com; "
            "connect-src 'self' http://127.0.0.1:* http://localhost:* ws://localhost:* ws://127.0.0.1:*; "
            "frame-ancestors 'self';"
        )
        return response

app = FastAPI()
app.add_middleware(CSPMiddleware)
```

### Nginx

```nginx
server {
    # ... other config ...

    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob: https://js9.si.edu; style-src 'self' 'unsafe-inline' https://js9.si.edu; script-src 'self' https://js9.si.edu https://cdnjs.cloudflare.com; connect-src 'self' http://127.0.0.1:* http://localhost:* ws://localhost:* ws://127.0.0.1:*; frame-ancestors 'self';";
}
```

### Apache

```apache
<IfModule mod_headers.c>
    Header set Content-Security-Policy "default-src 'self'; img-src 'self' data: blob: https://js9.si.edu; style-src 'self' 'unsafe-inline' https://js9.si.edu; script-src 'self' https://js9.si.edu https://cdnjs.cloudflare.com; connect-src 'self' http://127.0.0.1:* http://localhost:* ws://localhost:* ws://127.0.0.1:*; frame-ancestors 'self';"
</IfModule>
```

---

## Getting Help

If you encounter an error not covered in this guide:

1. **Check the logs:** Job logs often contain detailed error information
2. **View the trace ID:** Each error includes a trace ID for debugging
3. **Contact support:** Include the trace ID when reporting issues

**Useful commands:**

```bash
# View recent errors
dsa110-cli errors --recent 10

# Get detailed error info
dsa110-cli error-detail --trace-id <trace_id>
```
