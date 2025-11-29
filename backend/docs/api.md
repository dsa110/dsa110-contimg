# DSA-110 API Documentation

## Overview

The DSA-110 Continuum Imaging Pipeline provides a REST API for accessing
measurement sets, images, sources, calibration data, and pipeline job status.

**Base URL:** `http://localhost:8000/api`

**Interactive Docs:** `http://localhost:8000/api/docs` (Swagger UI)

## Authentication

The API uses IP-based access control. See [security.md](security.md) for
details.

## Endpoints

### Health Check

```
GET /api/health
```

Returns API health status. Always accessible regardless of IP restrictions.

**Response:**

```json
{
  "status": "healthy",
  "service": "dsa110-contimg-api"
}
```

---

### Images

#### List Images

```
GET /api/images
```

Returns all registered images.

**Response:**

```json
[
  {
    "id": "1",
    "path": "/stage/dsa110-contimg/images/image1.fits",
    "qa_grade": "good",
    "created_at": "2025-11-28T20:21:31",
    "run_id": "job-2025-10-31-134906"
  }
]
```

#### Get Image Detail

```
GET /api/images/{image_id}
```

**Response:**

```json
{
  "id": "1",
  "path": "/stage/dsa110-contimg/images/image1.fits",
  "ms_path": "/stage/dsa110-contimg/ms/2025-10-31T13:49:06.ms",
  "cal_table": "/stage/dsa110-contimg/caltables/bandpass.cal",
  "pointing_ra_deg": 133.5,
  "pointing_dec_deg": 54.8,
  "qa_grade": "good",
  "qa_summary": "RMS 0.10 mJy, DR 1000, Beam 15.0\"",
  "run_id": "job-2025-10-31-134906",
  "created_at": "2025-11-28T20:21:31"
}
```

#### Download FITS File

```
GET /api/images/{image_id}/fits
```

Returns the FITS file as a binary download.

---

### Measurement Sets

#### Get MS Metadata

```
GET /api/ms/{encoded_path}/metadata
```

**Note:** The path must be URL-encoded.

**Example:**

```bash
curl "http://localhost:8000/api/ms/%2Fstage%2Fdsa110-contimg%2Fms%2F2025-10-31T13%3A49%3A06.ms/metadata"
```

**Response:**

```json
{
  "path": "/stage/dsa110-contimg/ms/2025-10-31T13:49:06.ms",
  "pointing_ra_deg": 133.52,
  "pointing_dec_deg": 54.84,
  "start_mjd": 60973.57,
  "end_mjd": 60973.58,
  "stage": "discovered",
  "qa_grade": "pending",
  "run_id": "job-2025-10-31-134906"
}
```

#### Get Calibrator Matches

```
GET /api/ms/{encoded_path}/calibrator-matches
```

Returns calibration tables associated with this measurement set.

---

### Sources

#### List Sources

```
GET /api/sources
```

Returns all detected sources.

#### Get Source Detail

```
GET /api/sources/{source_id}
```

**Example:**

```bash
curl "http://localhost:8000/api/sources/J1293249%2B525013"
```

**Response:**

```json
{
  "id": "J1293249+525013",
  "name": "J1293249+525013",
  "ra_deg": 129.3249,
  "dec_deg": 52.5013,
  "contributing_images": [
    {
      "image_id": "1",
      "path": "/stage/dsa110-contimg/images/image1.fits",
      "qa_grade": "good",
      "created_at": "2025-11-28T20:21:31"
    }
  ],
  "latest_image_id": "1"
}
```

#### Get Source Lightcurve

```
GET /api/sources/{source_id}/lightcurve
```

**Query Parameters:**

- `start_date` (optional): ISO format start date
- `end_date` (optional): ISO format end date

**Response:**

```json
{
  "source_id": "J1293249+525013",
  "data_points": [
    {
      "mjd": 60975.43,
      "flux_jy": 0.117,
      "flux_err_jy": 0.016,
      "snr": 73.9,
      "image_path": "/stage/dsa110-contimg/images/image1.fits"
    }
  ]
}
```

---

### Calibration Tables

#### Get Calibration Table Detail

```
GET /api/cal/{encoded_path}
```

**Response:**

```json
{
  "path": "/stage/dsa110-contimg/caltables/bandpass.cal",
  "table_type": "BP",
  "set_name": "0834_2025-10-25T14-11-19",
  "cal_field": "0~23",
  "refant": "104,105,106",
  "created_at": "2025-11-26T17:25:43",
  "source_ms_path": "/stage/dsa110-contimg/ms/0834.ms",
  "status": "active"
}
```

---

### Jobs & Provenance

#### Get Job Provenance

```
GET /api/jobs/{run_id}/provenance
```

Returns the full provenance chain for a pipeline job.

#### Get Job Logs

```
GET /api/jobs/{run_id}/logs?tail=100
```

Returns the last N lines of the job log.

---

### Quality Assurance

#### Get Image QA

```
GET /api/qa/image/{image_id}
```

#### Get MS QA

```
GET /api/qa/ms/{encoded_path}
```

#### Get Job QA

```
GET /api/qa/job/{run_id}
```

---

## Error Responses

All errors return a standardized envelope:

```json
{
  "code": "NOT_FOUND",
  "http_status": 404,
  "user_message": "Image not found: 999",
  "action": "Verify the image ID exists",
  "ref_id": "",
  "details": {},
  "trace_id": "abc123"
}
```

### Error Codes

| Code               | HTTP Status | Description                |
| ------------------ | ----------- | -------------------------- |
| `NOT_FOUND`        | 404         | Resource does not exist    |
| `VALIDATION_ERROR` | 422         | Invalid request parameters |
| `INTERNAL_ERROR`   | 500         | Server error               |
| `DB_UNAVAILABLE`   | 503         | Database connection failed |
| `FORBIDDEN`        | 403         | IP not in allowed list     |

---

## Testing

Run the test script to verify all endpoints:

```bash
cd /data/dsa110-contimg/backend
bash test_api_endpoints.sh
```
