# DSA-110 Dashboard: Backend API & Integration

**Date:** 2025-11-12  
**Status:** Consolidated backend API documentation  
**Audience:** Backend developers, frontend developers, API consumers

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Core Endpoints](#core-endpoints)
3. [ESE Detection Endpoints](#ese-detection-endpoints)
4. [Mosaic Endpoints](#mosaic-endpoints)
5. [Source Monitoring Endpoints](#source-monitoring-endpoints)
6. [Image Endpoints](#image-endpoints)
7. [Region Management Endpoints](#region-management-endpoints)
8. [Pointing & Observing Endpoints](#pointing-observing-endpoints)
9. [Streaming Service Endpoints](#streaming-service-endpoints)
10. [Control & Job Management Endpoints](#control-job-management-endpoints)
11. [Batch Job Endpoints](#batch-job-endpoints)
12. [MS Management Endpoints](#ms-management-endpoints)
13. [QA Visualization Endpoints](#qa-visualization-endpoints)
14. [Data Management Endpoints](#data-management-endpoints)
15. [Products Endpoints](#products-endpoints)
16. [Catalog Endpoints](#catalog-endpoints)
17. [Calibration Table Endpoints](#calibration-table-endpoints)
18. [UVH5 Endpoints](#uvh5-endpoints)
19. [Real-Time Updates](#real-time-updates)
20. [Data Access Layer](#data-access-layer)
21. [Error Handling](#error-handling)
22. [Authentication & Security](#authentication-security)

---

## API Overview

### Base URL

**Development:** `http://localhost:8000/api`  
**Production:** `https://dsa110-pipeline.caltech.edu/api`

### Content Type

All requests and responses use `application/json`.

### Authentication

**Current:** None (internal tool)  
**Future:** JWT tokens or API keys for production

### Response Format

**Success Response:**
```json
{
  "data": { ... },
  "status": "success"
}
```

**Error Response:**
```json
{
  "error": "Error message",
  "status": "error",
  "code": "ERROR_CODE"
}
```

---

## Core Endpoints

### GET /status

Get pipeline queue statistics and recent observations.

**Response:**
```json
{
  "queue": {
    "total": 150,
    "pending": 12,
    "in_progress": 3,
    "completed": 130,
    "failed": 5,
    "collecting": 2
  },
  "calibration_sets": [
    {
      "cal_group_id": "2025-10-13T13:28:03",
      "created_at": "2025-10-13T13:28:03Z",
      "num_targets": 15
    }
  ],
  "recent_groups": [
    {
      "group_id": "2025-10-24T14:00:00",
      "state": "completed",
      "subbands_present": 16,
      "expected_subbands": 16,
      "has_calibrator": true
    }
  ]
}
```

**Fields:**
- `queue`: Current processing queue statistics
- `calibration_sets`: Active calibration groups
- `recent_groups`: Last 20 observation groups with their processing state

**Refresh Rate:** Poll every 10 seconds for real-time updates

---

### GET /metrics/system

Get system health metrics (CPU, memory, disk, load).

**Response:**
```json
{
  "cpu_percent": 45.2,
  "mem_percent": 62.8,
  "disk_total": 5000000000000,
  "disk_used": 3200000000000,
  "disk_free": 1800000000000,
  "load_1": 2.15,
  "load_5": 1.87,
  "load_15": 1.54,
  "ts": "2025-10-24T14:30:00Z"
}
```

**Fields:**
- `cpu_percent`: CPU usage percentage (0-100)
- `mem_percent`: Memory usage percentage (0-100)
- `disk_*`: Disk space in bytes
- `load_*`: System load averages (1, 5, 15 minutes)
- `ts`: Timestamp of metrics collection

**Refresh Rate:** Poll every 10 seconds

---

### GET /metrics/system/history

Get historical system metrics.

**Query Parameters:**
- `limit` (optional): Number of historical points (default: 60)

**Response:**
```json
[
  {
    "cpu_percent": 45.2,
    "mem_percent": 62.8,
    "disk_total": 5000000000000,
    "disk_used": 3200000000000,
    "disk_free": 1800000000000,
    "load_1": 2.15,
    "load_5": 1.87,
    "load_15": 1.54,
    "ts": "2025-10-24T14:30:00Z"
  }
]
```

---

### GET /health

Health check endpoint for monitoring and load balancers.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-24T14:30:00Z",
  "databases": {
    "queue": "accessible",
    "products": "accessible",
    "registry": "accessible"
  },
  "disk": {
    "free_gb": 1800.0,
    "total_gb": 5000.0
  },
  "version": "0.1.0"
}
```

---

## ESE Detection Endpoints

### GET /ese/candidates

Get extreme scattering event (ESE) candidate sources above 5σ threshold.

**Query Parameters:**
- `limit` (optional): Maximum number of results (default: 100)
- `status` (optional): Filter by status (`active`, `resolved`, `false_positive`)

**Response:**
```json
{
  "candidates": [
    {
      "id": 42,
      "source_id": "NVSS J123456.7+420312",
      "ra_deg": 188.73625,
      "dec_deg": 42.05333,
      "first_detection_at": "2025-10-24T12:00:00Z",
      "last_detection_at": "2025-10-24T14:30:00Z",
      "max_sigma_dev": 7.8,
      "baseline_flux_jy": 0.0145,
      "peak_flux_jy": 0.0258,
      "status": "active",
      "notes": null
    }
  ],
  "total": 1
}
```

**Fields:**
- `source_id`: NVSS identifier (or other survey ID)
- `ra_deg`, `dec_deg`: J2000 coordinates in degrees
- `first_detection_at`: When variability was first detected
- `last_detection_at`: Most recent detection timestamp
- `max_sigma_dev`: Maximum σ deviation from baseline flux
- `baseline_flux_jy`: Mean flux density (Jy)
- `peak_flux_jy`: Peak flux density during event (Jy)
- `status`: Current status (`active` | `resolved` | `false_positive`)
- `notes`: Optional notes from manual review

**Refresh Rate:** Poll every 10 seconds

---

### GET /alerts/history

Get historical alert log for ESE candidates and system warnings.

**Query Parameters:**
- `limit` (optional): Maximum number of results (default: 50)

**Response:**
```json
[
  {
    "id": 123,
    "source_id": "NVSS J123456.7+420312",
    "alert_type": "ese_candidate",
    "severity": "critical",
    "message": "ESE candidate detected: 7.8σ deviation",
    "triggered_at": "2025-10-24T14:30:00Z",
    "resolved_at": null
  }
]
```

---

### GET /ese/candidates/{source_id}/lightcurve

Get light curve for an ESE candidate source.

**Response:** Same format as `/sources/{source_id}/lightcurve`

---

### GET /ese/candidates/{source_id}/postage_stamps

Get postage stamps for an ESE candidate source.

**Response:** Same format as `/sources/{source_id}/postage_stamps`

---

### GET /ese/candidates/{source_id}/variability

Get variability metrics for an ESE candidate source.

**Response:** Same format as `/sources/{source_id}/variability`

---

### GET /ese/candidates/{source_id}/external_catalogs

Query external catalogs for an ESE candidate source.

**Response:** Same format as `/sources/{source_id}/external_catalogs`

---

## Mosaic Endpoints

### POST /mosaics/query

Query mosaics by time range.

**Request Body:**
```json
{
  "start_time": "2025-10-24T13:00:00Z",
  "end_time": "2025-10-24T14:00:00Z"
}
```

**Response:**
```json
{
  "mosaics": [
    {
      "id": 15,
      "name": "mosaic_2025-10-24_13-00",
      "path": "/stage/.../mosaic.fits",
      "start_mjd": 60238.541667,
      "end_mjd": 60238.583333,
      "n_images": 12,
      "n_sources": 142,
      "noise_jy": 0.00085
    }
  ],
  "total": 1
}
```

---

### POST /mosaics/create

Generate a new mosaic from time range.

**Request Body:**
```json
{
  "start_time": "2025-10-24T15:00:00Z",
  "end_time": "2025-10-24T16:00:00Z",
  "name": "custom_mosaic_name"
}
```

**Response:**
```json
{
  "status": "not_implemented",
  "message": "Mosaic creation via API is not yet implemented. Use the mosaic CLI tools.",
  "mosaic_id": null
}
```

**Note:** Currently returns "not_implemented" - use CLI tools for mosaic generation.

---

### GET /mosaics/{mosaic_id}

Get detailed information about a specific mosaic.

**Response:**
```json
{
  "id": 15,
  "name": "mosaic_2025-10-24_13-00",
  "path": "/stage/.../mosaic.fits",
  "start_mjd": 60238.541667,
  "end_mjd": 60238.583333,
  "n_images": 12,
  "n_sources": 142,
  "noise_jy": 0.00085
}
```

---

### GET /mosaics/{mosaic_id}/fits

Download FITS file for a mosaic.

**Response:** FITS file download (binary)

---

## Source Monitoring Endpoints

### POST /sources/search

Search for sources with filtering and sorting.

**Request Body:**
```json
{
  "query": "NVSS J123456",
  "filters": {
    "variability_min": 3.0,
    "dec_min": 40.0,
    "dec_max": 45.0,
    "flux_min_mjy": 10.0
  },
  "sort": {
    "field": "sigma_deviation",
    "order": "desc"
  },
  "limit": 100,
  "offset": 0
}
```

**Response:**
```json
{
  "sources": [
    {
      "source_id": "NVSS J123456.7+420312",
      "ra_deg": 188.73625,
      "dec_deg": 42.05333,
      "nvss_flux_mjy": 145.0,
      "mean_flux_mjy": 153.0,
      "n_obs": 142,
      "chi2_nu": 8.3,
      "sigma_deviation": 6.2,
      "last_measured_at": "2025-10-24T14:30:00Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

---

### GET /sources/{source_id}

Get detailed information about a specific source.

**Response:**
```json
{
  "id": "NVSS J123456.7+420312",
  "name": "NVSS J123456.7+420312",
  "ra_deg": 188.73625,
  "dec_deg": 42.05333,
  "catalog": "NVSS",
  "n_meas": 142,
  "n_meas_forced": 15,
  "mean_flux_jy": 0.153,
  "std_flux_jy": 0.012,
  "max_snr": 38.1,
  "is_variable": true,
  "ese_probability": 0.75,
  "variability_metrics": {
    "v": 0.25,
    "eta": 0.12,
    "vs_mean": 0.15,
    "m_mean": 0.10,
    "n_epochs": 142
  }
}
```

---

### GET /sources/{source_id}/variability

Get variability metrics for a source.

**Response:**
```json
{
  "source_id": "NVSS J123456.7+420312",
  "v": 0.25,
  "eta": 0.12,
  "vs_mean": 0.15,
  "m_mean": 0.10,
  "n_epochs": 142
}
```

---

### GET /sources/{source_id}/lightcurve

Get light curve data for a source.

**Response:**
```json
{
  "source_id": "NVSS J123456.7+420312",
  "ra_deg": 188.73625,
  "dec_deg": 42.05333,
  "flux_points": [
    {
      "mjd": 60235.3,
      "time": "2025-10-20T07:12:00",
      "flux_jy": 0.198,
      "flux_err_jy": 0.0052,
      "image_id": "/stage/.../image.fits"
    }
  ],
  "normalized_flux_points": [...]
}
```

---

### GET /sources/{source_id}/detections

Get paginated detections for a source.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 25, max: 100)

**Response:**
```json
{
  "items": [
    {
      "id": null,
      "name": null,
      "image_id": 123,
      "image_path": "/stage/.../image.fits",
      "ra": 188.73625,
      "dec": 42.05333,
      "flux_peak": 198.0,
      "flux_peak_err": 5.2,
      "flux_int": 205.0,
      "flux_int_err": 6.1,
      "snr": 38.1,
      "forced": false,
      "mjd": 60235.3,
      "measured_at": "2025-10-20T07:12:00Z"
    }
  ],
  "total": 142,
  "page": 1,
  "page_size": 25
}
```

---

### GET /sources/{source_id}/postage_stamps

Get postage stamp cutouts for a source.

**Query Parameters:**
- `size_arcsec` (optional): Cutout size in arcseconds (default: 60.0)
- `max_stamps` (optional): Maximum number of stamps (default: 20)

**Response:**
```json
{
  "source_id": "NVSS J123456.7+420312",
  "stamps": [
    {
      "image_path": "/stage/.../image.fits",
      "mjd": 60235.3,
      "cutout_path": "/tmp/postage_stamps/..._cutout.fits"
    }
  ]
}
```

---

### GET /sources/{source_id}/external_catalogs

Query external catalogs (SIMBAD, NED, Gaia) for a source.

**Query Parameters:**
- `radius_arcsec` (optional): Search radius (default: 5.0)
- `catalogs` (optional): Comma-separated list (simbad,ned,gaia) or "all"
- `timeout` (optional): Query timeout in seconds (default: 30.0)

**Response:**
```json
{
  "source_id": "NVSS J123456.7+420312",
  "ra_deg": 188.73625,
  "dec_deg": 42.05333,
  "matches": {
    "simbad": {
      "catalog": "simbad",
      "matched": true,
      "main_id": "3C 123",
      "object_type": "Radio",
      "separation_arcsec": 2.1,
      "redshift": 0.2177
    },
    "ned": { ... },
    "gaia": { ... }
  },
  "query_time_sec": 1.2
}
```

---

## Image Endpoints

### GET /images

List available images with filtering.

**Query Parameters:**
- `limit` (optional): Maximum results (default: 100)
- `offset` (optional): Pagination offset (default: 0)
- `ms_path` (optional): Filter by MS path pattern
- `image_type` (optional): Filter by image type
- `pbcor` (optional): Filter by primary-beam correction status
- `start_date` (optional): Start date filter (ISO 8601)
- `end_date` (optional): End date filter (ISO 8601)
- `noise_max` (optional): Maximum noise level (Jy)
- `dec_min` (optional): Minimum declination (degrees, experimental)
- `dec_max` (optional): Maximum declination (degrees, experimental)
- `has_calibrator` (optional): Filter by calibrator detection (experimental)

**Response:**
```json
{
  "items": [
    {
      "id": 123,
      "path": "/stage/.../image.fits",
      "ms_path": "/stage/.../ms",
      "created_at": "2025-10-24T14:00:00Z",
      "type": "image",
      "beam_major_arcsec": 45.2,
      "noise_jy": 0.00085,
      "pbcor": true,
      "center_ra_deg": 188.73625,
      "center_dec_deg": 42.05333
    }
  ],
  "total": 150
}
```

---

### GET /images/{image_id}

Get detailed information about a specific image.

**Response:**
```json
{
  "id": 123,
  "path": "/stage/.../image.fits",
  "ms_path": "/stage/.../ms",
  "created_at": "2025-10-24T14:00:00Z",
  "type": "image",
  "beam_major_arcsec": 45.2,
  "beam_minor_arcsec": 42.1,
  "beam_pa_deg": 12.5,
  "noise_jy": 0.00085,
  "pbcor": true,
  "center_ra_deg": 188.73625,
  "center_dec_deg": 42.05333,
  "n_measurements": 142,
  "frequency_hz": 1.4e9,
  "bandwidth_hz": 100e6
}
```

---

### GET /images/{image_id}/fits

Download FITS file for an image.

**Response:** FITS file download (binary)

---

### GET /images/{image_id}/measurements

Get photometry measurements for an image.

**Response:**
```json
{
  "items": [
    {
      "source_id": "NVSS J123456.7+420312",
      "ra_deg": 188.73625,
      "dec_deg": 42.05333,
      "flux_peak_jy": 0.198,
      "flux_peak_err_jy": 0.0052,
      "flux_int_jy": 0.205,
      "snr": 38.1
    }
  ],
  "total": 142
}
```

---

### GET /images/{image_id}/profile

Get image profile (1D slice) along specified axis.

**Query Parameters:**
- `axis` (optional): "x" or "y" (default: "x")
- `position` (optional): Pixel position along perpendicular axis (default: center)

**Response:** JSON array of pixel values

---

### POST /images/{image_id}/fit

Fit a Gaussian to a source in an image.

**Request Body:**
```json
{
  "ra_deg": 188.73625,
  "dec_deg": 42.05333,
  "radius_arcsec": 30.0
}
```

**Response:**
```json
{
  "fitted": true,
  "peak_flux_jy": 0.198,
  "peak_ra_deg": 188.73626,
  "peak_dec_deg": 42.05334,
  "fwhm_major_arcsec": 45.2,
  "fwhm_minor_arcsec": 42.1,
  "pa_deg": 12.5
}
```

---

## Region Management Endpoints

### GET /regions

List regions for an image.

**Query Parameters:**
- `image_path` (optional): Filter by image path

**Response:**
```json
{
  "regions": [
    {
      "id": 1,
      "image_path": "/stage/.../image.fits",
      "region_type": "circle",
      "ra_deg": 188.73625,
      "dec_deg": 42.05333,
      "radius_arcsec": 30.0,
      "created_at": "2025-10-24T14:00:00Z"
    }
  ]
}
```

---

### POST /regions

Create a new region.

**Request Body:**
```json
{
  "image_path": "/stage/.../image.fits",
  "region_type": "circle",
  "ra_deg": 188.73625,
  "dec_deg": 42.05333,
  "radius_arcsec": 30.0
}
```

**Response:**
```json
{
  "id": 1,
  "message": "Region created successfully"
}
```

---

### GET /regions/{region_id}

Get a specific region by ID.

**Response:**
```json
{
  "id": 1,
  "image_path": "/stage/.../image.fits",
  "region_type": "circle",
  "ra_deg": 188.73625,
  "dec_deg": 42.05333,
  "radius_arcsec": 30.0
}
```

---

### PUT /regions/{region_id}

Update an existing region.

**Request Body:** Same as POST /regions

---

### DELETE /regions/{region_id}

Delete a region.

**Response:**
```json
{
  "message": "Region deleted successfully"
}
```

---

### GET /regions/{region_id}/statistics

Get statistics for pixels within a region.

**Response:**
```json
{
  "mean": 0.0012,
  "std": 0.0008,
  "min": 0.0001,
  "max": 0.0056,
  "sum": 0.45,
  "n_pixels": 375
}
```

---

## Pointing & Observing Endpoints

### GET /pointing_history

Get telescope pointing history.

**Query Parameters:**
- `start_mjd` (required): Start time in MJD
- `end_mjd` (required): End time in MJD

**Response:**
```json
{
  "items": [
    {
      "group_id": "2025-10-24T14:00:00",
      "ra_deg": 188.7,
      "dec_deg": 42.1,
      "timestamp": "2025-10-24T14:00:00Z"
    }
  ]
}
```

---

### GET /calibrator_matches

Get calibrator matches for target observations.

**Query Parameters:**
- `limit` (optional): Maximum results (default: 50)
- `matched_only` (optional): Return only matched calibrators (default: false)

**Response:**
```json
{
  "matches": [
    {
      "target_group_id": "2025-10-24T14:00:00",
      "calibrator_group_id": "2025-10-24T13:00:00",
      "time_diff_minutes": 60,
      "quality_score": 0.92
    }
  ]
}
```

---

### GET /observation_timeline

Get observation timeline with gap detection.

**Query Parameters:**
- `gap_threshold_hours` (optional): Gap threshold (default: 1.0)

**Response:**
```json
{
  "observations": [
    {
      "group_id": "2025-10-24T14:00:00",
      "start_mjd": 60238.5,
      "end_mjd": 60238.542,
      "duration_hours": 1.0
    }
  ],
  "gaps": [
    {
      "start_mjd": 60238.542,
      "end_mjd": 60239.0,
      "duration_hours": 11.0
    }
  ]
}
```

---

### GET /observation_timeline/plot

Get observation timeline as PNG plot.

**Query Parameters:** Same as `/observation_timeline`

**Response:** PNG image

---

### GET /groups/{group_id}

Get detailed information about an observation group.

**Response:**
```json
{
  "group_id": "2025-10-24T14:00:00",
  "state": "completed",
  "subbands_present": 16,
  "expected_subbands": 16,
  "has_calibrator": true,
  "created_at": "2025-10-24T14:00:00Z",
  "completed_at": "2025-10-24T15:30:00Z"
}
```

---

### POST /reprocess/{group_id}

Trigger reprocessing of an observation group.

**Response:**
```json
{
  "ok": true
}
```

---

## Streaming Service Endpoints

### GET /streaming/status

Get streaming service status.

**Response:**
```json
{
  "running": true,
  "pid": 12345,
  "uptime_seconds": 3600,
  "cpu_percent": 15.2,
  "memory_mb": 512,
  "queue_stats": {
    "total": 10,
    "pending": 2,
    "processing": 1
  }
}
```

---

### POST /streaming/start

Start the streaming service.

**Response:**
```json
{
  "status": "started",
  "pid": 12345,
  "message": "Streaming service started successfully"
}
```

---

### POST /streaming/stop

Stop the streaming service.

**Response:**
```json
{
  "status": "stopped",
  "message": "Streaming service stopped successfully"
}
```

---

### POST /streaming/restart

Restart the streaming service.

**Response:**
```json
{
  "status": "restarted",
  "pid": 12346,
  "message": "Streaming service restarted successfully"
}
```

---

### GET /streaming/config

Get current streaming service configuration.

**Response:**
```json
{
  "input_dir": "/data/incoming",
  "output_dir": "/stage/dsa110-contimg/ms",
  "batch_size": 10,
  "poll_interval": 5.0
}
```

---

### POST /streaming/config

Update streaming service configuration.

**Request Body:**
```json
{
  "input_dir": "/data/incoming",
  "output_dir": "/stage/dsa110-contimg/ms",
  "batch_size": 10,
  "poll_interval": 5.0
}
```

**Response:**
```json
{
  "status": "updated",
  "message": "Configuration updated successfully"
}
```

---

## Control & Job Management Endpoints

### GET /control/ms/list

Get list of Measurement Sets with filtering.

**Query Parameters:**
- `stage` (optional): Filter by processing stage
- `status` (optional): Filter by status
- `limit` (optional): Maximum results
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "ms_list": [
    {
      "path": "/stage/.../ms",
      "stage": "imaged",
      "status": "ok",
      "mid_mjd": 60238.5,
      "field_name": "J1234+42"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

---

### POST /control/jobs/create

Create a new pipeline job.

**Request Body:**
```json
{
  "job_type": "image",
  "ms_paths": ["/stage/.../ms1", "/stage/.../ms2"],
  "parameters": {
    "imsize": 2048,
    "cellsize": 1.5
  }
}
```

**Response:**
```json
{
  "job_id": "job_20251024_001",
  "status": "pending",
  "message": "Job created successfully"
}
```

---

### GET /jobs

Get list of jobs.

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Maximum results (default: 50)

**Response:**
```json
{
  "jobs": [
    {
      "id": 1,
      "job_type": "image",
      "status": "completed",
      "created_at": "2025-10-24T14:00:00Z",
      "completed_at": "2025-10-24T14:05:00Z",
      "ms_paths": ["/stage/.../ms1"]
    }
  ],
  "total": 50
}
```

---

### GET /jobs/id/{job_id}

Get job details by ID.

**Response:**
```json
{
  "id": 1,
  "job_type": "image",
  "status": "completed",
  "created_at": "2025-10-24T14:00:00Z",
  "completed_at": "2025-10-24T14:05:00Z",
  "ms_paths": ["/stage/.../ms1"],
  "parameters": { ... },
  "output_path": "/stage/.../image.fits"
}
```

---

### GET /jobs/id/{job_id}/logs

Stream job logs via Server-Sent Events (SSE).

**Response:** SSE stream with log lines

---

### POST /jobs/calibrate

Create a calibration job.

**Request Body:**
```json
{
  "ms_paths": ["/stage/.../ms1"],
  "parameters": {
    "calibrator_source": "3C123",
    "refant": "0"
  }
}
```

**Response:**
```json
{
  "id": 1,
  "status": "pending",
  "message": "Job created successfully"
}
```

---

### POST /jobs/apply

Create a calibration application job.

**Request Body:**
```json
{
  "ms_paths": ["/stage/.../ms1"],
  "caltable_paths": ["/stage/.../cal.K"]
}
```

**Response:** Same as `/jobs/calibrate`

---

### POST /jobs/image

Create an imaging job.

**Request Body:**
```json
{
  "ms_paths": ["/stage/.../ms1"],
  "parameters": {
    "imsize": 2048,
    "cellsize": 1.5,
    "niter": 1000
  }
}
```

**Response:** Same as `/jobs/calibrate`

---

### POST /jobs/convert

Create a UVH5 to MS conversion job.

**Request Body:**
```json
{
  "uvh5_paths": ["/data/incoming/file.uvh5"],
  "output_dir": "/stage/.../ms"
}
```

**Response:** Same as `/jobs/calibrate`

---

### POST /jobs/workflow

Create a workflow job (calibrate → apply → image).

**Request Body:**
```json
{
  "ms_paths": ["/stage/.../ms1"],
  "calibrate_params": { ... },
  "apply_params": { ... },
  "image_params": { ... }
}
```

**Response:** Same as `/jobs/calibrate`

---

## Batch Job Endpoints

### POST /batch/calibrate

Create a batch calibration job for multiple MS files.

**Request Body:**
```json
{
  "ms_paths": ["/stage/.../ms1", "/stage/.../ms2"],
  "parameters": { ... }
}
```

**Response:**
```json
{
  "batch_id": "batch_20251024_001",
  "status": "pending",
  "n_jobs": 2
}
```

---

### POST /batch/apply

Create a batch calibration application job.

**Request Body:** Same as `/batch/calibrate`

---

### POST /batch/image

Create a batch imaging job.

**Request Body:** Same as `/batch/calibrate`

---

### GET /batch

Get list of batch jobs.

**Response:**
```json
{
  "batches": [
    {
      "batch_id": "batch_20251024_001",
      "job_type": "calibrate",
      "status": "completed",
      "n_jobs": 2,
      "n_completed": 2,
      "created_at": "2025-10-24T14:00:00Z"
    }
  ]
}
```

---

### GET /batch/{batch_id}

Get batch job details.

**Response:**
```json
{
  "batch_id": "batch_20251024_001",
  "job_type": "calibrate",
  "status": "completed",
  "n_jobs": 2,
  "n_completed": 2,
  "jobs": [ ... ]
}
```

---

### POST /batch/{batch_id}/cancel

Cancel a batch job.

**Response:**
```json
{
  "status": "cancelled",
  "message": "Batch job cancelled"
}
```

---

## MS Management Endpoints

### GET /ms

List Measurement Sets with filtering.

**Query Parameters:**
- `search` (optional): Search term for MS path
- `limit` (optional): Maximum results (default: 50)

**Response:**
```json
{
  "ms_list": [
    {
      "path": "/stage/.../ms",
      "stage": "imaged",
      "status": "ok",
      "mid_mjd": 60238.5,
      "field_name": "J1234+42"
    }
  ],
  "total": 100
}
```

---

### GET /ms_index

List MS index entries.

**Query Parameters:**
- `stage` (optional): Filter by processing stage
- `status` (optional): Filter by status
- `limit` (optional): Maximum results (default: 100)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "ms_path": "/stage/.../ms",
      "stage": "imaged",
      "status": "ok",
      "mid_mjd": 60238.5
    }
  ]
}
```

---

### POST /ms/discover

Scan filesystem for MS files and register them in the database.

**Request Body:**
```json
{
  "search_paths": ["/stage/.../ms"],
  "recursive": true
}
```

**Response:**
```json
{
  "discovered": 10,
  "registered": 8,
  "skipped": 2
}
```

---

### GET /ms/{ms_path:path}/metadata

Get metadata for an MS file.

**Response:**
```json
{
  "path": "/stage/.../ms",
  "n_antennas": 110,
  "n_baselines": 5995,
  "n_channels": 1024,
  "frequency_hz": 1.4e9,
  "bandwidth_hz": 100e6,
  "duration_seconds": 3600,
  "field_ra_deg": 188.7,
  "field_dec_deg": 42.1
}
```

---

### GET /ms/{ms_path:path}/calibrator-matches

Get calibrator matches for an MS.

**Response:**
```json
{
  "matches": [
    {
      "calibrator_group_id": "2025-10-24T13:00:00",
      "time_diff_minutes": 60,
      "quality_score": 0.92
    }
  ]
}
```

---

### GET /ms/{ms_path:path}/existing-caltables

Get existing calibration tables for an MS.

**Response:**
```json
{
  "caltables": [
    {
      "path": "/stage/.../cal.K",
      "type": "K",
      "created_at": "2025-10-24T13:00:00Z",
      "compatible": true
    }
  ]
}
```

---

### POST /ms/{ms_path:path}/validate-caltable

Validate calibration table compatibility with an MS.

**Request Body:**
```json
{
  "caltable_path": "/stage/.../cal.K"
}
```

**Response:**
```json
{
  "compatible": true,
  "issues": [],
  "warnings": []
}
```

---

## QA Visualization Endpoints

### GET /qa/directories

Browse QA directory structure.

**Query Parameters:**
- `path` (optional): Directory path (default: root)

**Response:**
```json
{
  "path": "/stage/dsa110-contimg/qa",
  "directories": [
    {
      "name": "2025-10-24T13:28:03",
      "path": "/stage/.../qa/2025-10-24T13:28:03"
    }
  ],
  "files": [
    {
      "name": "amplitude_vs_time.png",
      "path": "/stage/.../qa/2025-10-24T13:28:03/amplitude_vs_time.png",
      "size": 123456,
      "modified": "2025-10-24T14:00:00Z"
    }
  ]
}
```

---

### GET /qa/fits/:path

Get FITS file information.

**Response:**
```json
{
  "path": "/stage/.../image.fits",
  "header": {
    "NAXIS": 2,
    "NAXIS1": 2048,
    "NAXIS2": 2048,
    "CRVAL1": 188.73625,
    "CRVAL2": 42.05333
  },
  "data_shape": [2048, 2048],
  "wcs": { ... }
}
```

---

### GET /qa/casa/:path

Get CASA table information.

**Response:**
```json
{
  "path": "/stage/.../cal.K",
  "table_type": "K",
  "num_rows": 1000,
  "columns": [
    {
      "name": "TIME",
      "dtype": "double",
      "shape": []
    }
  ]
}
```

---

### GET /qa

Get quality assurance metrics for recent observations.

**Query Parameters:**
- `limit` (optional): Number of recent observations (default: 100)

**Response:**
```json
{
  "items": [
    {
      "group_id": "2025-10-24T13:28:03",
      "timestamp": "2025-10-24T14:05:00Z",
      "artifact_type": "calibration",
      "path": "/stage/.../qa/2025-10-24T13:28:03/amplitude_vs_time.png"
    }
  ]
}
```

---

### GET /qa/file/{group}/{name}

Serve QA files with path traversal protection.

**Response:** File download (PNG, FITS, etc.)

---

### GET /qa/thumbs

Get QA thumbnails.

**Query Parameters:**
- `limit` (optional): Maximum results (default: 100)

**Response:** Same format as `/qa`

---

### GET /qa/calibration/{ms_path:path}

Get calibration QA metrics for an MS.

**Response:**
```json
{
  "ms_path": "/stage/.../ms",
  "calibration_quality": {
    "phase_rms": 12.5,
    "amp_rms": 0.05,
    "success_rate": 0.94
  },
  "flagging": {
    "percent_flagged": 8.2,
    "rfi_events": 3
  }
}
```

---

### GET /qa/calibration/{ms_path:path}/bandpass-plots

List available bandpass plots for an MS.

**Response:**
```json
{
  "plots": [
    {
      "filename": "bandpass_antenna_0.png",
      "path": "/stage/.../qa/bandpass_antenna_0.png"
    }
  ]
}
```

---

### GET /qa/calibration/{ms_path:path}/bandpass-plots/{filename}

Serve a specific bandpass plot file.

**Response:** PNG image

---

### GET /qa/calibration/{ms_path:path}/spw-plot

Get spectral window plot for calibration.

**Response:** PNG image

---

### GET /qa/calibration/{ms_path:path}/caltable-completeness

Get calibration table completeness metrics.

**Response:**
```json
{
  "completeness": 0.95,
  "missing_antennas": [],
  "missing_times": []
}
```

---

### GET /qa/{ms_path:path}

Get QA metrics for an MS path.

**Response:**
```json
{
  "ms_path": "/stage/.../ms",
  "calibration_qa": { ... },
  "image_qa": { ... },
  "flagging_stats": { ... }
}
```

---

### POST /qa/notebook/generate

Generate QA notebook.

**Request Body:**
```json
{
  "group_id": "2025-10-24T13:28:03",
  "notebook_type": "calibration",
  "output_path": "/stage/.../qa_notebook.ipynb"
}
```

**Response:**
```json
{
  "notebook_path": "/stage/.../qa_notebook.ipynb",
  "status": "generated"
}
```

---

## Data Management Endpoints

### GET /data

List data products with staging/published status.

**Response:**
```json
{
  "items": [
    {
      "data_id": "2025-10-24T14:00:00",
      "type": "image",
      "path": "/stage/.../image.fits",
      "status": "staging",
      "created_at": "2025-10-24T14:00:00Z"
    }
  ]
}
```

---

### GET /data/{data_id:path}

Get data product details.

**Response:**
```json
{
  "data_id": "2025-10-24T14:00:00",
  "type": "image",
  "path": "/stage/.../image.fits",
  "status": "staging",
  "lineage": { ... }
}
```

---

### POST /data/{data_id:path}/finalize

Finalize a data product (move from staging to published).

**Response:**
```json
{
  "status": "finalized",
  "message": "Data product finalized"
}
```

---

### POST /data/{data_id:path}/publish

Publish a data product.

**Response:**
```json
{
  "status": "published",
  "message": "Data product published"
}
```

---

### POST /data/{data_id:path}/auto-publish/enable

Enable auto-publish for a data product.

**Response:**
```json
{
  "status": "enabled",
  "message": "Auto-publish enabled"
}
```

---

### POST /data/{data_id:path}/auto-publish/disable

Disable auto-publish for a data product.

**Response:**
```json
{
  "status": "disabled",
  "message": "Auto-publish disabled"
}
```

---

### GET /data/{data_id:path}/auto-publish/status

Get auto-publish status for a data product.

**Response:**
```json
{
  "auto_publish": true
}
```

---

### GET /data/{data_id:path}/lineage

Get data lineage graph for a data product.

**Response:**
```json
{
  "data_id": "2025-10-24T14:00:00",
  "parents": [ ... ],
  "children": [ ... ],
  "dependencies": [ ... ]
}
```

---

## Products Endpoints

### GET /products

Get recent products.

**Query Parameters:**
- `limit` (optional): Maximum results (default: 50)

**Response:**
```json
{
  "items": [
    {
      "type": "image",
      "path": "/stage/.../image.fits",
      "created_at": "2025-10-24T14:00:00Z"
    }
  ]
}
```

---

## Catalog Endpoints

### GET /catalog/overlay

Get catalog sources for overlay on images.

**Query Parameters:**
- `ra` (required): RA center in degrees
- `dec` (required): Dec center in degrees
- `radius` (required): Search radius in degrees
- `catalog` (optional): Catalog type (nvss, vlass, first, all) (default: "all")

**Response:**
```json
{
  "sources": [
    {
      "ra_deg": 188.73625,
      "dec_deg": 42.05333,
      "flux_mjy": 145.0,
      "source_id": "NVSS J123456.7+420312",
      "catalog_type": "nvss"
    }
  ],
  "count": 1,
  "ra_center": 188.7,
  "dec_center": 42.1,
  "radius_deg": 0.5
}
```

---

## Calibration Table Endpoints

### GET /caltables

List available calibration tables.

**Query Parameters:**
- `cal_dir` (optional): Calibration directory path

**Response:**
```json
{
  "caltables": [
    {
      "path": "/stage/.../cal.K",
      "type": "K",
      "created_at": "2025-10-24T13:00:00Z",
      "ms_path": "/stage/.../ms"
    }
  ]
}
```

---

## UVH5 Endpoints

### GET /uvh5

List available UVH5 files for conversion.

**Query Parameters:**
- `input_dir` (optional): Input directory path
- `limit` (optional): Maximum results (default: 100)

**Response:**
```json
{
  "files": [
    {
      "path": "/data/incoming/file.uvh5",
      "size": 1234567890,
      "modified": "2025-10-24T14:00:00Z"
    }
  ]
}
```

---

## Real-Time Updates

### WebSocket: /api/ws/status

WebSocket endpoint for real-time status updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/status');
```

**Message Format:**
```json
{
  "type": "status_update",
  "data": {
    "pipeline_status": { ... },
    "metrics": { ... },
    "ese_candidates": { ... }
  }
}
```

**Message Types:**
- `status_update` - Pipeline status updates
- `metrics_update` - System metrics updates
- `ese_update` - ESE candidate updates

**Broadcast Frequency:** Every 10 seconds

---

### SSE: /api/sse/status

Server-Sent Events endpoint (fallback for WebSocket).

**Connection:**
```javascript
const eventSource = new EventSource('/api/sse/status');
```

**Message Format:** Same as WebSocket

---

## Data Access Layer

### Python Functions (`api/data_access.py`)

**Queue Management:**
- `fetch_queue_stats()` - Get queue statistics
- `fetch_recent_queue_groups()` - Get recent groups
- `fetch_calibration_sets()` - Get calibration sets

**ESE Detection:**
- `fetch_ese_candidates()` - Get ESE candidates
- `fetch_alert_history()` - Get alert history

**Source Monitoring:**
- `search_sources()` - Search sources
- `fetch_source_detail()` - Get source details
- `fetch_source_timeseries()` - Get flux timeseries

**Mosaics:**
- `query_mosaics()` - Query existing mosaics
- `create_mosaic_job()` - Create mosaic generation job

**Streaming Service:**
- `get_streaming_status()` - Get service status
- `start_streaming_service()` - Start service
- `stop_streaming_service()` - Stop service

---

## Error Handling

### Error Classification

**Network Errors:**
- Connection timeout
- DNS resolution failure
- Network unreachable

**Server Errors:**
- 500 Internal Server Error
- 503 Service Unavailable
- 502 Bad Gateway

**Client Errors:**
- 400 Bad Request
- 404 Not Found
- 422 Validation Error

### Error Response Format

```json
{
  "error": "Error message",
  "status": "error",
  "code": "ERROR_CODE",
  "details": { ... }
}
```

---

## Authentication & Security

### Current State

**No authentication** - Internal tool assumption

### Future Plans

**JWT Tokens:**
- Token-based authentication
- Role-based access control
- Token refresh mechanism

**API Keys:**
- Key-based authentication
- Rate limiting per key
- Key rotation

**CORS:**
- Configured for allowed origins
- Credentials support
- Preflight handling

---

## See Also

- [Dashboard Implementation Status](./dashboard_implementation_status.md) - Current implementation status
- [Dashboard Pages & Features](./dashboard_pages_and_features.md) - Page documentation
- [JS9 CASA Analysis API](./js9_casa_analysis_api.md) - JS9 CASA analysis endpoint documentation
- [JS9 CASA Analysis How-To](../how-to/js9_casa_analysis.md) - User guide for JS9 CASA analysis
- [Streaming Service Architecture](../concepts/streaming-architecture.md) - Streaming service details
- [Frontend Architecture](../concepts/dashboard_frontend_architecture.md) - Frontend integration

---

## Endpoint Summary

**Total Endpoints:** 100+  
**Router Structure:**
- `/api/status` - Status router (`routers/status.py`)
- `/api/images` - Images router (`routers/images.py`)
- `/api/products` - Products router (`routers/products.py`)
- `/api/mosaics` - Mosaics router (`routers/mosaics.py`)
- `/api/sources` - Photometry router (`routers/photometry.py`)
- `/api/catalog` - Catalogs router (`routers/catalogs.py`)
- `/api/visualization` - Visualization router (`visualization_routes.py`)
  - `/api/visualization/js9/analysis` - JS9 CASA analysis endpoint (see [JS9 CASA Analysis API](./js9_casa_analysis_api.md))
- Main routes - Additional endpoints in `routes.py`

**Note:** This document consolidates all API endpoints. For the most up-to-date endpoint list, see the FastAPI auto-generated docs at `/docs` (Swagger UI) or `/redoc` when the API server is running.

