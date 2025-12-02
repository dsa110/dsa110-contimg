# DSA-110 API Reference

**Complete API documentation for the DSA-110 Continuum Imaging Pipeline.**

!!! note "Version"
Last updated: Phase 4 completion (complexity reduction)

---

## Overview

The DSA-110 API provides REST endpoints for pipeline control, data access, and monitoring.

### Base URL

```
http://localhost:8000/api
```

### Interactive Documentation

When the API server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Response Format

All responses are JSON with consistent structure:

```json
{
  "status": "success",
  "data": { ... },
  "message": "Optional message"
}
```

Error responses:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description",
  "details": { ... }
}
```

### Authentication

Currently IP-based access control (private networks only). No API keys required for internal use.

---

## Health & Status

### GET /api/status

Pipeline status overview.

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "database": "connected"
}
```

---

### GET /api/health

Quick health check.

**Response:**

```json
{
  "status": "ok"
}
```

---

### GET /api/health/detailed

Detailed component health.

**Response:**

```json
{
  "database": { "status": "healthy", "latency_ms": 2.5 },
  "redis": { "status": "healthy", "latency_ms": 0.8 },
  "streaming": { "status": "running", "queue_depth": 3 }
}
```

---

### GET /api/health/services

External service health.

**Response:**

```json
{
  "services": [
    { "name": "database", "status": "healthy" },
    { "name": "redis", "status": "healthy" },
    { "name": "streaming_converter", "status": "running" }
  ]
}
```

---

## Streaming Service

### GET /api/streaming/status

Current streaming converter status.

**Response:**

```json
{
  "running": true,
  "queue_depth": 5,
  "processed_today": 142,
  "last_processed": "2025-12-01T10:30:00Z"
}
```

---

### POST /api/streaming/start

Start the streaming converter.

**Response:**

```json
{
  "status": "started",
  "message": "Streaming converter started"
}
```

---

### POST /api/streaming/stop

Stop the streaming converter.

**Response:**

```json
{
  "status": "stopped",
  "message": "Streaming converter stopped gracefully"
}
```

---

### POST /api/streaming/restart

Restart the streaming converter.

**Response:**

```json
{
  "status": "restarted",
  "message": "Streaming converter restarted"
}
```

---

### GET /api/streaming/metrics

Streaming performance metrics.

**Response:**

```json
{
  "total_processed": 1542,
  "failed_count": 3,
  "avg_processing_time_s": 45.2,
  "queue_depth": 5,
  "last_hour": {
    "processed": 12,
    "failed": 0
  }
}
```

---

## Job Management

### GET /api/jobs

List recent jobs.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |
| `status` | string | all | Filter: pending, running, completed, failed |
| `type` | string | all | Filter: convert, calibrate, image, workflow |

**Response:**

```json
{
  "jobs": [
    {
      "id": "job_123",
      "type": "convert",
      "status": "completed",
      "created_at": "2025-12-01T10:00:00Z",
      "completed_at": "2025-12-01T10:02:30Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

### GET /api/jobs/{job_id}

Get job details.

**Response:**

```json
{
  "id": "job_123",
  "type": "convert",
  "status": "completed",
  "created_at": "2025-12-01T10:00:00Z",
  "completed_at": "2025-12-01T10:02:30Z",
  "parameters": {
    "input_path": "/data/incoming/2025-12-01T10:00:00_sb00.hdf5",
    "output_dir": "/stage/dsa110-contimg/ms"
  },
  "result": {
    "ms_path": "/stage/dsa110-contimg/ms/2025-12-01T10:00:00.ms"
  }
}
```

---

### POST /api/jobs/convert

Submit conversion job.

**Request Body:**

```json
{
  "input_path": "/data/incoming/2025-12-01T10:00:00_sb00.hdf5",
  "output_dir": "/stage/dsa110-contimg/ms",
  "options": {
    "writer": "parallel-subband",
    "scratch_dir": "/scratch"
  }
}
```

**Response:**

```json
{
  "job_id": "job_124",
  "status": "queued",
  "message": "Conversion job submitted"
}
```

---

### POST /api/jobs/calibrate

Submit calibration job.

**Request Body:**

```json
{
  "ms_path": "/stage/dsa110-contimg/ms/2025-12-01T10:00:00.ms",
  "options": {
    "fast_mode": false,
    "calibrator": "3C286"
  }
}
```

**Response:**

```json
{
  "job_id": "job_125",
  "status": "queued"
}
```

---

### POST /api/jobs/image

Submit imaging job.

**Request Body:**

```json
{
  "ms_path": "/stage/dsa110-contimg/ms/2025-12-01T10:00:00.ms",
  "output_dir": "/stage/dsa110-contimg/images",
  "options": {
    "imsize": 4096,
    "cell": "1.5arcsec",
    "niter": 50000
  }
}
```

**Response:**

```json
{
  "job_id": "job_126",
  "status": "queued"
}
```

---

### POST /api/jobs/workflow

Submit full pipeline workflow.

**Request Body:**

```json
{
  "input_path": "/data/incoming/2025-12-01T10:00:00_sb00.hdf5",
  "stages": ["convert", "calibrate", "image"],
  "options": {
    "fast_mode": true
  }
}
```

**Response:**

```json
{
  "workflow_id": "wf_001",
  "jobs": ["job_127", "job_128", "job_129"],
  "status": "queued"
}
```

---

## Data Access

### GET /api/images

List images.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination |
| `type` | string | all | continuum, dirty, residual |
| `min_noise` | float | - | Min noise (Jy) |
| `max_noise` | float | - | Max noise (Jy) |
| `dec_min` | float | - | Min declination (deg) |
| `dec_max` | float | - | Max declination (deg) |

**Response:**

```json
{
  "images": [
    {
      "id": "img_001",
      "path": "/stage/dsa110-contimg/images/2025-12-01T10:00:00.fits",
      "type": "continuum",
      "noise_jy": 0.0003,
      "center_ra_deg": 180.5,
      "center_dec_deg": 55.2,
      "created_at": "2025-12-01T10:05:00Z"
    }
  ],
  "total": 1542
}
```

---

### GET /api/images/{image_id}

Get image details.

**Response:**

```json
{
  "id": "img_001",
  "path": "/stage/dsa110-contimg/images/2025-12-01T10:00:00.fits",
  "type": "continuum",
  "noise_jy": 0.0003,
  "center_ra_deg": 180.5,
  "center_dec_deg": 55.2,
  "ms_path": "/stage/dsa110-contimg/ms/2025-12-01T10:00:00.ms",
  "calibrated": true,
  "metadata": {
    "bmaj": 0.015,
    "bmin": 0.012,
    "bpa": 45.0
  }
}
```

---

### GET /api/images/{image_id}/fits

Download FITS file.

**Response:** Binary FITS file with `Content-Type: application/fits`

---

### GET /api/ms

List Measurement Sets.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination |
| `status` | string | all | pending, calibrated, imaged, failed |
| `start_time` | string | - | ISO timestamp |
| `end_time` | string | - | ISO timestamp |

**Response:**

```json
{
  "measurement_sets": [
    {
      "path": "/stage/dsa110-contimg/ms/2025-12-01T10:00:00.ms",
      "status": "calibrated",
      "timestamp": "2025-12-01T10:00:00Z",
      "subband_count": 16,
      "calibration_tables": ["K.cal", "BP.cal", "G.cal"]
    }
  ],
  "total": 3542
}
```

---

### GET /api/ms/{ms_path}/metadata

Get MS metadata.

**Response:**

```json
{
  "path": "/stage/dsa110-contimg/ms/2025-12-01T10:00:00.ms",
  "n_baselines": 2016,
  "n_channels": 16384,
  "n_times": 24,
  "n_antennas": 64,
  "freq_range_mhz": [1280, 1530],
  "time_range": ["2025-12-01T10:00:00Z", "2025-12-01T10:05:00Z"],
  "phase_center": { "ra_deg": 180.5, "dec_deg": 55.2 }
}
```

---

### GET /api/sources

List detected sources.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination |
| `ra_min` | float | - | Min RA (deg) |
| `ra_max` | float | - | Max RA (deg) |
| `dec_min` | float | - | Min Dec (deg) |
| `dec_max` | float | - | Max Dec (deg) |
| `min_flux` | float | - | Min flux (Jy) |

**Response:**

```json
{
  "sources": [
    {
      "id": "src_001",
      "ra_deg": 180.523,
      "dec_deg": 55.215,
      "flux_jy": 0.025,
      "flux_err_jy": 0.003,
      "detection_count": 5
    }
  ],
  "total": 15423
}
```

---

### GET /api/sources/{source_id}/lightcurve

Get source light curve.

**Response:**

```json
{
  "source_id": "src_001",
  "measurements": [
    {
      "timestamp": "2025-12-01T10:00:00Z",
      "flux_jy": 0.025,
      "flux_err_jy": 0.003
    },
    {
      "timestamp": "2025-12-01T11:00:00Z",
      "flux_jy": 0.024,
      "flux_err_jy": 0.003
    }
  ]
}
```

---

## Calibration

### GET /api/caltables

List calibration tables.

**Response:**

```json
{
  "caltables": [
    {
      "path": "/stage/dsa110-contimg/caltables/K.cal",
      "type": "K",
      "ms_path": "/stage/dsa110-contimg/ms/2025-12-01T10:00:00.ms",
      "created_at": "2025-12-01T10:03:00Z"
    }
  ]
}
```

---

### GET /api/calibration/status

Calibration status for recent observations.

**Response:**

```json
{
  "recent": [
    {
      "ms_path": "/stage/dsa110-contimg/ms/2025-12-01T10:00:00.ms",
      "calibrated": true,
      "tables": ["K.cal", "BP.cal", "G.cal"],
      "quality": "good"
    }
  ]
}
```

---

## Mosaics

### GET /api/mosaics

List mosaics.

**Response:**

```json
{
  "mosaics": [
    {
      "id": "mosaic_001",
      "name": "dec55_2025-12-01",
      "status": "completed",
      "n_images": 24,
      "center_dec_deg": 55.0,
      "created_at": "2025-12-01T12:00:00Z"
    }
  ]
}
```

---

### POST /api/mosaics/create

Create a new mosaic.

**Request Body:**

```json
{
  "name": "dec55_2025-12-01",
  "image_ids": ["img_001", "img_002", "img_003"],
  "options": {
    "tier": "science",
    "weighting": "natural"
  }
}
```

**Response:**

```json
{
  "mosaic_id": "mosaic_002",
  "status": "queued",
  "job_id": "job_130"
}
```

---

### GET /api/mosaics/{mosaic_id}

Get mosaic details.

**Response:**

```json
{
  "id": "mosaic_001",
  "name": "dec55_2025-12-01",
  "status": "completed",
  "n_images": 24,
  "output_path": "/stage/dsa110-contimg/mosaics/dec55_2025-12-01.fits",
  "qa_metrics": {
    "rms_jy": 0.0002,
    "dynamic_range": 1500
  }
}
```

---

## Queue Management

### GET /api/queues

List active queues.

**Response:**

```json
{
  "queues": [
    {
      "name": "conversion",
      "pending": 5,
      "running": 2,
      "completed_today": 142
    },
    {
      "name": "imaging",
      "pending": 3,
      "running": 1,
      "completed_today": 89
    }
  ]
}
```

---

### GET /api/queues/stats

Queue statistics.

**Response:**

```json
{
  "total_pending": 8,
  "total_running": 3,
  "avg_wait_time_s": 30.5,
  "avg_processing_time_s": 120.3,
  "throughput_per_hour": 28.5
}
```

---

## Pipeline Execution

### GET /api/pipeline/executions

List pipeline executions.

**Response:**

```json
{
  "executions": [
    {
      "id": "exec_001",
      "status": "completed",
      "stages_completed": 5,
      "stages_total": 5,
      "duration_s": 180.5
    }
  ]
}
```

---

### GET /api/pipeline/workflow-status

Current pipeline workflow status.

**Response:**

```json
{
  "active_workflows": 2,
  "pending_stages": 5,
  "running_stages": 2,
  "avg_stage_duration_s": 45.2
}
```

---

## Monitoring

### GET /api/metrics/prometheus

Prometheus-format metrics.

**Response:** Plain text in Prometheus exposition format:

```
# HELP dsa110_conversion_total Total conversions
# TYPE dsa110_conversion_total counter
dsa110_conversion_total 1542

# HELP dsa110_imaging_duration_seconds Imaging duration
# TYPE dsa110_imaging_duration_seconds histogram
dsa110_imaging_duration_seconds_bucket{le="60"} 100
```

---

### GET /api/metrics/system

System resource metrics.

**Response:**

```json
{
  "cpu_percent": 45.2,
  "memory_percent": 62.5,
  "disk_usage_gb": {
    "/data": { "used": 500, "total": 2000 },
    "/stage": { "used": 150, "total": 500 }
  }
}
```

---

### GET /api/observation_timeline

Observation timeline data.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start` | string | -24h | Start time |
| `end` | string | now | End time |

**Response:**

```json
{
  "observations": [
    {
      "timestamp": "2025-12-01T10:00:00Z",
      "status": "completed",
      "ms_path": "/stage/dsa110-contimg/ms/2025-12-01T10:00:00.ms"
    }
  ]
}
```

---

## WebSocket API

### /api/ws/status

Real-time status updates via WebSocket.

**Connect:**

```javascript
const ws = new WebSocket("ws://localhost:8000/api/ws/status");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Update:", data);
};
```

**Message Types:**

| Type               | Description                |
| ------------------ | -------------------------- |
| `job_update`       | Job status change          |
| `queue_update`     | Queue depth change         |
| `pipeline_update`  | Pipeline stage change      |
| `streaming_update` | Streaming converter status |

**Example Message:**

```json
{
  "type": "job_update",
  "data": {
    "job_id": "job_123",
    "status": "completed",
    "timestamp": "2025-12-01T10:05:00Z"
  }
}
```

---

## CLI Reference

### Conversion CLI

```bash
# Convert subband groups in time window
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-12-01T00:00:00" \
    "2025-12-01T23:59:59"

# Dry-run (preview only)
python -m dsa110_contimg.conversion.cli groups --dry-run ...

# Convert by calibrator transit
python -m dsa110_contimg.conversion.cli groups \
    --calibrator "3C286" \
    /data/incoming /stage/dsa110-contimg/ms

# Single file conversion
python -m dsa110_contimg.conversion.cli single \
    /data/incoming/observation.uvh5 \
    /stage/dsa110-contimg/ms/observation.ms
```

---

### Calibration CLI

```bash
# Run calibration
python -m dsa110_contimg.calibration.cli run \
    --ms /stage/dsa110-contimg/ms/observation.ms

# Fast mode (subset of data)
python -m dsa110_contimg.calibration.cli run \
    --ms /stage/dsa110-contimg/ms/observation.ms \
    --fast

# List calibration tables
python -m dsa110_contimg.calibration.cli list
```

---

### Imaging CLI

```bash
# Image a calibrated MS
python -m dsa110_contimg.imaging.cli image \
    --ms /stage/dsa110-contimg/ms/observation.ms \
    --imagename /stage/dsa110-contimg/images/observation

# With NVSS masking (default, faster)
python -m dsa110_contimg.imaging.cli image \
    --ms /stage/dsa110-contimg/ms/observation.ms \
    --imagename /stage/dsa110-contimg/images/observation \
    --mask-radius-arcsec 120.0

# Quick-look (smaller image)
python -m dsa110_contimg.imaging.cli image \
    --ms /stage/dsa110-contimg/ms/observation.ms \
    --imagename /stage/dsa110-contimg/images/observation \
    --quick
```

---

### Mosaic CLI

```bash
# Create mosaic from images
python -m dsa110_contimg.mosaic.cli create \
    --name "dec55_daily" \
    --images /stage/dsa110-contimg/images/*.fits \
    --output /stage/dsa110-contimg/mosaics/

# List mosaics
python -m dsa110_contimg.mosaic.cli list
```

---

### Photometry CLI

```bash
# Single source photometry
python -m dsa110_contimg.photometry.cli adaptive \
    --ms /stage/dsa110-contimg/ms/observation.ms \
    --ra 124.526792 --dec 54.620694 \
    --output-dir /tmp/results \
    --target-snr 5.0

# With MS access locking (for parallel runs)
python -m dsa110_contimg.photometry.cli adaptive \
    --ms /stage/dsa110-contimg/ms/observation.ms \
    --ra 124.526792 --dec 54.620694 \
    --serialize-ms-access
```

---

## Python API

### Pipeline Stages

```python
from dsa110_contimg.pipeline.stages_impl import (
    CatalogSetupStage,
    ConversionStage,
    CalibrationSolveStage,
    CalibrationStage,
    ImagingStage,
)
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.config import PipelineConfig

# Create config
config = PipelineConfig()

# Create context
context = PipelineContext(
    config=config,
    inputs={"input_path": "/data/observation.hdf5"}
)

# Execute stages
stage = ConversionStage(config)
result = stage.execute(context)
ms_path = result.outputs["ms_path"]
```

---

### Fast Metadata Access

```python
from dsa110_contimg.utils import FastMeta, get_uvh5_mid_mjd

# Quick helper
mid_mjd = get_uvh5_mid_mjd("/path/to/file.hdf5")

# Full metadata access
with FastMeta("/path/to/file.hdf5") as meta:
    times = meta.time_array
    freqs = meta.freq_array
    mid_mjd = meta.mid_time_mjd
```

---

### Database Access

```python
from dsa110_contimg.database.session import get_session
from dsa110_contimg.database.registry import ProductRegistry

# Query products
with get_session() as session:
    registry = ProductRegistry(session)
    images = registry.list_images(limit=10)

# Register new product
with get_session() as session:
    registry = ProductRegistry(session)
    registry.register_image(
        path="/stage/dsa110-contimg/images/new.fits",
        image_type="continuum"
    )
```

---

### ABSURD Task Queue

```python
from dsa110_contimg.absurd import AbsurdClient

async def main():
    client = AbsurdClient.from_env()
    await client.connect()

    # Spawn task
    task_id = await client.spawn(
        "convert_uvh5",
        {"input_path": "/data/observation.hdf5"}
    )

    # Check status
    status = await client.get_task_status(task_id)
    print(f"Task {task_id}: {status}")

    await client.close()
```

---

## Error Codes

| Code                  | HTTP Status | Description                     |
| --------------------- | ----------- | ------------------------------- |
| `NOT_FOUND`           | 404         | Resource not found              |
| `VALIDATION_ERROR`    | 400         | Invalid request parameters      |
| `DATABASE_ERROR`      | 500         | Database operation failed       |
| `CONVERSION_ERROR`    | 500         | Conversion failed               |
| `CALIBRATION_ERROR`   | 500         | Calibration failed              |
| `IMAGING_ERROR`       | 500         | Imaging failed                  |
| `QUEUE_ERROR`         | 500         | Queue operation failed          |
| `SERVICE_UNAVAILABLE` | 503         | Service temporarily unavailable |

---

## Rate Limiting

Default limits (configurable):

| Endpoint Type    | Rate Limit |
| ---------------- | ---------- |
| Read endpoints   | 100/minute |
| Write endpoints  | 20/minute  |
| Heavy operations | 5/minute   |

Rate limit headers:

- `X-RateLimit-Limit`: Max requests
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

---

## Related Documentation

- **[Quick Start](QUICKSTART.md)**: Get running in 5 minutes
- **[User Guide](USER_GUIDE.md)**: Operations and workflows
- **[Developer Guide](DEVELOPER_GUIDE.md)**: Contributing guidelines
- **[Architecture](ARCHITECTURE.md)**: System design
- **[Troubleshooting](TROUBLESHOOTING.md)**: Problem resolution
