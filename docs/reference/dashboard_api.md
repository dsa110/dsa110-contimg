# Dashboard API Reference

## Overview

The DSA-110 Pipeline Dashboard API provides RESTful JSON endpoints for monitoring pipeline status, system health, and data products.

**Base URL:** `http://localhost:8000/api`

**Authentication:** None (currently)

**Content-Type:** `application/json`

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

## ESE Detection Endpoints

### GET /ese/candidates

Get extreme scattering event (ESE) candidate sources above 5σ threshold.

**Query Parameters:**

- `limit` (optional): Maximum number of results (default: 100)
- `status` (optional): Filter by status (active, resolved, false_positive)

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
- `status`: Current status (active | resolved | false_positive)
- `notes`: Optional notes from manual review

**Refresh Rate:** Poll every 10 seconds

---

### GET /alerts/history

Get historical alert log for ESE candidates and system warnings.

**Query Parameters:**

- `limit` (optional): Maximum number of results (default: 50)
- `alert_type` (optional): Filter by type (ESE_CANDIDATE, CALIBRATOR_ISSUE, SYSTEM_WARNING)
- `severity` (optional): Filter by severity (info, warning, critical)

**Response:**

```json
[
  {
    "id": 123,
    "source_id": "NVSS J123456.7+420312",
    "alert_type": "ESE_CANDIDATE",
    "severity": "critical",
    "message": "New ESE candidate detected with 7.8σ deviation",
    "triggered_at": "2025-10-24T14:30:00Z",
    "resolved_at": null
  }
]
```

**Fields:**

- `source_id`: Associated source (if applicable)
- `alert_type`: Category of alert
- `severity`: info | warning | critical
- `message`: Human-readable description
- `triggered_at`: When alert was first triggered
- `resolved_at`: When alert was resolved (null if active)

**Refresh Rate:** Poll every 60 seconds (less time-critical)

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

**Parameters:**

- `start_time`: Start of time range (ISO 8601 UTC)
- `end_time`: End of time range (ISO 8601 UTC)

**Response:**

```json
{
  "mosaics": [
    {
      "id": 15,
      "name": "mosaic_2025-10-24_13-00",
      "path": "/data/mosaics/mosaic_2025-10-24_13-00.fits",
      "thumbnail_path": "/data/mosaics/mosaic_2025-10-24_13-00.png",
      "start_mjd": 60238.541667,
      "end_mjd": 60238.583333,
      "created_at": "2025-10-24T14:05:00Z",
      "status": "completed",
      "image_count": 12,
      "noise_jy": 0.00085,
      "source_count": 142,
      "coverage_deg2": 45.2
    }
  ],
  "total": 1
}
```

**Fields:**

- `name`: Human-readable mosaic identifier
- `path`: Full path to FITS file
- `thumbnail_path`: Path to PNG thumbnail (if available)
- `start_mjd`, `end_mjd`: Time range in Modified Julian Date
- `created_at`: When mosaic was generated
- `status`: pending | in_progress | completed | failed
- `image_count`: Number of individual images combined
- `noise_jy`: RMS noise level in Janskys
- `source_count`: Number of detected sources
- `coverage_deg2`: Sky coverage in square degrees

---

### POST /mosaics/create

Request generation of a new mosaic for a time range.

**Request Body:**

```json
{
  "start_time": "2025-10-24T15:00:00Z",
  "end_time": "2025-10-24T16:00:00Z",
  "name": "custom_mosaic_name"  // optional
}
```

**Response:**

```json
{
  "status": "pending",
  "message": "Mosaic generation queued",
  "mosaic_id": "mosaic_2025-10-24_15-00",
  "estimated_completion": "2025-10-24T16:10:00Z"
}
```

**Status Codes:**

- `202 Accepted`: Request queued successfully
- `400 Bad Request`: Invalid time range
- `409 Conflict`: Mosaic already exists for this time range

**Notes:**

- Mosaic generation is asynchronous
- Use `/mosaics/query` to check completion status
- Typical processing time: 5-10 minutes per hour of data

---

## Source Monitoring Endpoints

### POST /sources/search

Search for sources and retrieve flux timeseries.

**Request Body:**

```json
{
  "source_id": "NVSS J123456.7+420312",
  "start_time": "2025-10-20T00:00:00Z",  // optional
  "end_time": "2025-10-24T23:59:59Z",    // optional
  "limit": 1000  // optional, default: 500
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
      "catalog": "NVSS",
      "flux_measurements": [
        {
          "timestamp": "2025-10-24T14:00:00Z",
          "mjd": 60238.583333,
          "flux_jy": 0.0145,
          "flux_err_jy": 0.0008,
          "chi_sq_nu": 1.2,
          "sigma_dev": 0.5,
          "image_path": "/data/images/2025-10-24_14-00.fits",
          "is_flagged": false
        }
      ],
      "mean_flux_jy": 0.0142,
      "std_flux_jy": 0.0015,
      "variability_index": 1.8
    }
  ],
  "total": 1
}
```

**Fields:**

- `source_id`: Primary identifier
- `ra_deg`, `dec_deg`: J2000 coordinates
- `catalog`: Source survey (NVSS, FIRST, etc.)
- `flux_measurements`: Array of time-ordered flux measurements
  - `timestamp`: Observation time (ISO 8601 UTC)
  - `mjd`: Modified Julian Date
  - `flux_jy`: Integrated flux density in Janskys
  - `flux_err_jy`: Flux measurement error (1σ)
  - `chi_sq_nu`: Reduced chi-squared (variability indicator)
  - `sigma_dev`: Deviation from mean in σ units
  - `image_path`: Path to source image
  - `is_flagged`: Manual quality flag
- `mean_flux_jy`: Mean flux over time range
- `std_flux_jy`: Standard deviation
- `variability_index`: χ²_ν-based variability metric

---

## Data Quality Endpoints

### GET /qa

Get quality assurance metrics for recent observations.

**Query Parameters:**

- `limit` (optional): Number of recent observations (default: 20)

**Response:**

```json
{
  "recent_qa": [
    {
      "group_id": "2025-10-24T14:00:00",
      "timestamp": "2025-10-24T14:05:00Z",
      "calibration_quality": {
        "phase_rms": 12.5,
        "amp_rms": 0.05,
        "success_rate": 0.94
      },
      "image_quality": {
        "noise_jy": 0.00085,
        "dynamic_range": 1250,
        "num_sources": 142
      },
      "flagging": {
        "percent_flagged": 8.2,
        "rfi_events": 3
      }
    }
  ]
}
```

---

## Calibration Endpoints

### GET /calibrator_matches

Get list of calibrator matches for target observations.

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

### GET /pointing_history

Get telescope pointing history for recent observations.

**Query Parameters:**

- `limit` (optional): Number of recent pointings (default: 50)

**Response:**

```json
{
  "pointings": [
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

## Error Responses

All endpoints may return error responses:

### 400 Bad Request

```json
{
  "detail": "Invalid time range: start_time must be before end_time"
}
```

### 404 Not Found

```json
{
  "detail": "Source not found: NVSS J123456.7+420312"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Database connection failed"
}
```

---

## Rate Limiting

Currently no rate limiting is enforced. Recommended polling intervals:

- Pipeline status: 10s
- System metrics: 10s
- ESE candidates: 10s
- Alert history: 60s
- Other endpoints: On-demand only

---

## CORS Configuration

The API allows cross-origin requests from:

- `http://localhost:5173` (Vite dev server)
- `http://127.0.0.1:5173`
- `http://10.42.0.148:5173` (SSH tunnel)

For production deployment, update CORS origins in `src/dsa110_contimg/api/routes.py`.

---

## Future Endpoints

Planned for future releases:

- `POST /api/sources/annotate` - Add manual annotations to sources
- `GET /api/vo/cone` - VO Cone Search for external tools
- `POST /api/alerts/slack` - Configure Slack webhooks
- `GET /api/user/preferences` - User-specific settings
- `PUT /api/ese/threshold` - Update ESE detection threshold

