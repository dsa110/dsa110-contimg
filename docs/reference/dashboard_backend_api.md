# DSA-110 Dashboard: Backend API & Integration

**Date:** 2025-01-XX  
**Status:** Consolidated backend API documentation  
**Audience:** Backend developers, frontend developers, API consumers

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Core Endpoints](#core-endpoints)
3. [ESE Detection Endpoints](#ese-detection-endpoints)
4. [Mosaic Endpoints](#mosaic-endpoints)
5. [Source Monitoring Endpoints](#source-monitoring-endpoints)
6. [Streaming Service Endpoints](#streaming-service-endpoints)
7. [Control & Job Management Endpoints](#control--job-management-endpoints)
8. [QA Visualization Endpoints](#qa-visualization-endpoints)
9. [Real-Time Updates](#real-time-updates)
10. [Data Access Layer](#data-access-layer)
11. [Error Handling](#error-handling)
12. [Authentication & Security](#authentication--security)

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
- `source_id` (optional): Filter by source ID
- `alert_type` (optional): Filter by type (`ese_candidate`, `calibrator_missing`, `system_error`)

**Response:**
```json
{
  "alerts": [
    {
      "id": 123,
      "source_id": "NVSS J123456.7+420312",
      "alert_type": "ese_candidate",
      "severity": "critical",
      "message": "ESE candidate detected: 7.8σ deviation",
      "sent_at": "2025-10-24T14:30:00Z",
      "channel": "#ese-alerts",
      "success": true
    }
  ],
  "total": 1
}
```

---

## Mosaic Endpoints

### GET /mosaics/query

Query existing mosaics or initiate mosaic generation.

**Query Parameters:**
- `start_mjd` (required): Start time in MJD
- `end_mjd` (required): End time in MJD
- `dec_min` (optional): Minimum declination
- `dec_max` (optional): Maximum declination
- `query_only` (optional): If `true`, only query existing mosaics

**Response (Query Only):**
```json
{
  "mosaics": [
    {
      "id": 5,
      "name": "2025-10-24_hourly_12-13UTC",
      "path": "/stage/dsa110-contimg/mosaics/2025-10-24_hourly_12-13UTC.fits",
      "start_mjd": 60238.5,
      "end_mjd": 60238.542,
      "n_images": 12,
      "n_sources": 142,
      "noise_jy": 0.00085,
      "thumbnail_path": "/stage/.../thumbnail.png"
    }
  ],
  "total": 1
}
```

**Response (Generate):**
```json
{
  "job_id": "mosaic_20251024_001",
  "status": "pending",
  "message": "Mosaic generation job created"
}
```

---

### POST /mosaics/generate

Generate a new mosaic from time range.

**Request Body:**
```json
{
  "start_mjd": 60238.5,
  "end_mjd": 60238.542,
  "dec_min": 40.0,
  "dec_max": 45.0
}
```

**Response:**
```json
{
  "job_id": "mosaic_20251024_001",
  "status": "pending"
}
```

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

### GET /sources/:sourceId

Get detailed information about a specific source.

**Response:**
```json
{
  "source_id": "NVSS J123456.7+420312",
  "ra_deg": 188.73625,
  "dec_deg": 42.05333,
  "nvss_flux_mjy": 145.0,
  "vlass_flux_mjy": 98.0,
  "spectral_index": -0.7,
  "variability_stats": {
    "n_obs": 142,
    "mean_flux_mjy": 153.0,
    "std_flux_mjy": 12.0,
    "chi2_nu": 8.3,
    "sigma_deviation": 6.2
  },
  "timeseries": [
    {
      "mjd": 60235.3,
      "flux_mjy": 198.0,
      "error_mjy": 5.2,
      "snr": 38.1,
      "image_path": "/stage/.../image.fits"
    }
  ]
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

### GET /control/jobs

Get list of jobs.

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Maximum results
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "job_20251024_001",
      "job_type": "image",
      "status": "completed",
      "created_at": "2025-10-24T14:00:00Z",
      "completed_at": "2025-10-24T14:05:00Z"
    }
  ],
  "total": 50,
  "limit": 50,
  "offset": 0
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

- [Dashboard API Reference](./dashboard_api.md) - Detailed API reference
- [Streaming Service Architecture](../concepts/streaming-architecture.md) - Streaming service details
- [Frontend Architecture](../concepts/dashboard_frontend_architecture.md) - Frontend integration

