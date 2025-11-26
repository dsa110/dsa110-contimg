# Running the DSA-110 Continuum Imaging Pipeline in Batch Mode

**Purpose**: This guide explains how to run the DSA-110 Continuum Imaging
Pipeline in batch mode for processing multiple observations, time windows, or
data files.

**Location**: `docs/how-to/batch_mode_guide.md`  
**Related**:

- [Using the Orchestrator CLI](USING_ORCHESTRATOR_CLI.md)
- [Batch Mode Development Assessment](../dev/analysis/batch_mode_development_assessment.md)

## Overview

Batch mode allows you to process multiple observations, time windows, or data
files in a single operation. The pipeline supports batch processing through:

1. **CLI Tools**: Command-line interfaces for each pipeline stage
2. **API Endpoints**: REST API endpoints for programmatic batch job submission
3. **Orchestrator Scripts**: High-level automation scripts for end-to-end
   workflows

## Batch Mode Capabilities by Stage

| Stage         | CLI Support | API Support | Batch Jobs | Status |
| ------------- | ----------- | ----------- | ---------- | ------ |
| Conversion    | ✓           | ✓           | ✗          | 95%    |
| Calibration   | ✓           | ✓           | ✓          | 100%   |
| Imaging       | ✓           | ✓           | ✓          | 100%   |
| Mosaic        | ✓           | Partial     | ✗          | 90%    |
| Photometry    | ✓           | Partial     | ✗          | 85%    |
| ESE Detection | ✗           | Partial     | ✗          | 60%    |

## Method 1: CLI-Based Batch Processing

### Conversion (UVH5 → MS)

Process multiple time windows using the orchestrator CLI:

```bash
# Process all groups in a time window (batch processing)
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-10-30 00:00:00" \
    "2025-10-31 00:00:00" \
    --writer parallel-subband \
    --stage-to-tmpfs
```

**What this does:**

- Discovers all subband groups in the specified time window
- Converts each complete group to MS format
- Organizes output: `ms/science/YYYY-MM-DD/<timestamp>.ms` or
  `ms/calibrators/YYYY-MM-DD/<timestamp>.ms`

**Options:**

- `--writer parallel-subband`: Use parallel subband writer (recommended)
- `--stage-to-tmpfs`: Stage data to tmpfs for faster I/O
- `--max-workers N`: Limit parallel workers (default: CPU count)

### Calibration

Batch calibration via CLI requires iterating over MS files:

```bash
# Find all MS files in a directory
MS_FILES=$(find /stage/dsa110-contimg/ms -name "*.ms" -type d)

# Process each MS file
for ms in $MS_FILES; do
    python -m dsa110_contimg.calibration.cli calibrate \
        "$ms" \
        --cal-field 0834+555 \
        --refant 103 \
        --solve-bandpass \
        --solve-gains
done
```

**Note**: For true batch processing with job tracking, use the API endpoints
(see Method 2).

### Imaging

Similar to calibration, batch imaging via CLI requires iteration:

```bash
# Find all calibrated MS files
MS_FILES=$(find /stage/dsa110-contimg/ms -name "*.ms" -type d)

# Image each MS file
for ms in $MS_FILES; do
    python -m dsa110_contimg.imaging.cli image \
        --ms "$ms" \
        --imagename "${ms}.image" \
        --field "" \
        --quality-tier standard
done
```

### Mosaic Creation

Mosaic CLI supports batch planning and building:

```bash
# Plan a mosaic for a time range
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name night_20251030 \
    --since 60300.0 \
    --until 60301.0 \
    --method weighted

# Build the mosaic
python -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name night_20251030 \
    --output /stage/dsa110-contimg/mosaics/night_20251030.img
```

## Method 2: API-Based Batch Processing

The API provides batch job endpoints with automatic job tracking, status
monitoring, and error handling.

### Setup

1. **Start the API server** (if not already running):

```bash
cd /data/dsa110-contimg
python -m dsa110_contimg.api.main
```

The API runs on `http://localhost:8000` by default.

2. **Verify API is running**:

```bash
curl http://localhost:8000/api/status
```

### Batch Calibration

Submit a batch calibration job:

```bash
curl -X POST http://localhost:8000/api/batch/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "ms_paths": [
      "/stage/dsa110-contimg/ms/2025-10-30T13:00:00.ms",
      "/stage/dsa110-contimg/ms/2025-10-30T14:00:00.ms",
      "/stage/dsa110-contimg/ms/2025-10-30T15:00:00.ms"
    ],
    "parameters": {
      "field": "",
      "refant": "103",
      "solve_bandpass": true,
      "solve_gains": true,
      "gain_solint": "inf",
      "gain_calmode": "ap",
      "auto_fields": true,
      "min_pb": 0.5
    }
  }'
```

**Response:**

```json
{
  "id": 1,
  "type": "batch_calibrate",
  "status": "pending",
  "total_items": 3,
  "completed_items": 0,
  "failed_items": 0,
  "created_at": "2025-10-30T13:00:00Z"
}
```

**Check batch status:**

```bash
curl http://localhost:8000/api/batch/1
```

### Batch Calibration Application

Apply calibration tables to multiple MS files:

```bash
curl -X POST http://localhost:8000/api/batch/apply \
  -H "Content-Type: application/json" \
  -d '{
    "ms_paths": [
      "/stage/dsa110-contimg/ms/2025-10-30T13:00:00.ms",
      "/stage/dsa110-contimg/ms/2025-10-30T14:00:00.ms"
    ],
    "caltable_paths": [
      "/stage/dsa110-contimg/cal/2025-10-30T13:00:00.cal.K",
      "/stage/dsa110-contimg/cal/2025-10-30T13:00:00.cal.BP",
      "/stage/dsa110-contimg/cal/2025-10-30T13:00:00.cal.G"
    ]
  }'
```

### Batch Imaging

Submit a batch imaging job:

```bash
curl -X POST http://localhost:8000/api/batch/image \
  -H "Content-Type: application/json" \
  -d '{
    "ms_paths": [
      "/stage/dsa110-contimg/ms/2025-10-30T13:00:00.ms",
      "/stage/dsa110-contimg/ms/2025-10-30T14:00:00.ms"
    ],
    "parameters": {
      "imsize": 2048,
      "cell_arcsec": 1.5,
      "niter": 1000,
      "robust": 0.5,
      "quality_tier": "standard",
      "backend": "wsclean"
    }
  }'
```

### Batch ESE Detection

Detect ESE candidates across multiple sources:

```bash
curl -X POST http://localhost:8000/api/batch/ese-detect \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "ese-detect",
    "params": {
      "min_sigma": 5.0,
      "recompute": false,
      "source_ids": ["J120000+450000", "J121000+460000"],
      "use_parallel": true
    }
  }'
```

### Monitoring Batch Jobs

**List all batch jobs:**

```bash
curl http://localhost:8000/api/batch
```

**Get batch job details:**

```bash
curl http://localhost:8000/api/batch/{batch_id}
```

**Get batch job logs (SSE stream):**

```bash
curl http://localhost:8000/api/batch/{batch_id}/logs
```

## Method 3: Orchestrator Scripts (End-to-End Automation)

For complete workflow automation, use the mosaic orchestrator:

### Mosaic Orchestrator

The `MosaicOrchestrator` provides full end-to-end automation from HDF5 data to
published mosaic:

```python
from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

orchestrator = MosaicOrchestrator(
    products_db="/data/dsa110-contimg/state/products.sqlite3",
    cal_registry_db="/data/dsa110-contimg/state/cal_registry.sqlite3"
)

# Create mosaic centered on calibrator transit
published_path = orchestrator.create_mosaic_centered_on_calibrator(
    calibrator_name="0834+555",
    timespan_minutes=60,
    wait_for_published=True,
    poll_interval_seconds=30,
    max_wait_hours=24
)
```

**What this does:**

1. Finds calibrator transit time
2. Converts HDF5 to MS (if needed)
3. Forms observation group
4. Solves calibration
5. Applies calibration
6. Images all MS files
7. Creates mosaic
8. Waits for QA validation
9. Waits for automatic publishing

**CLI script:**

```bash
python scripts/mosaic/create_mosaic_centered.py \
    --calibrator 0834+555 \
    --timespan-minutes 60 \
    --poll-interval 30 \
    --max-wait-hours 24
```

## Best Practices

### 1. Resource Management

- **Limit parallel workers**: Use `--max-workers` to avoid overwhelming the
  system
- **Monitor disk space**: Batch processing can generate large amounts of data
- **Use tmpfs staging**: Enable `--stage-to-tmpfs` for faster I/O during
  conversion

### 2. Error Handling

- **Check batch status regularly**: Monitor batch jobs via API endpoints
- **Handle partial failures**: Batch jobs continue processing even if individual
  items fail
- **Review failed items**: Use `GET /api/batch/{batch_id}` to see which items
  failed and why

### 3. Time Windows

- **Use appropriate time ranges**: Large time windows may take hours or days to
  process
- **Break into smaller chunks**: Process 1-2 hour windows for faster completion
- **Consider calibrator transits**: Use calibrator-centered windows for better
  calibration

### 4. Database Management

- **Use separate databases for testing**: Don't mix production and test data
- **Backup databases**: Regular backups of `products.sqlite3` and
  `cal_registry.sqlite3`
- **Monitor database size**: Large batch jobs can create large databases

### 5. Monitoring

- **Use API endpoints**: Check job status via `/api/batch/{batch_id}`
- **Watch logs**: Monitor SSE log streams for real-time progress
- **Set up alerts**: Configure notifications for batch job completion/failure

## Example Workflows

### Workflow 1: Process One Night of Data

```bash
# 1. Convert all data for the night
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-10-30 00:00:00" \
    "2025-10-31 00:00:00" \
    --writer parallel-subband \
    --stage-to-tmpfs

# 2. Find all MS files
MS_FILES=$(find /stage/dsa110-contimg/ms/science/2025-10-30 -name "*.ms" -type d)

# 3. Batch calibrate via API
curl -X POST http://localhost:8000/api/batch/calibrate \
  -H "Content-Type: application/json" \
  -d "{
    \"ms_paths\": [$(echo $MS_FILES | sed 's/ /","/g')],
    \"parameters\": {
      \"refant\": \"103\",
      \"solve_bandpass\": true,
      \"solve_gains\": true
    }
  }"

# 4. Wait for calibration to complete, then batch image
curl -X POST http://localhost:8000/api/batch/image \
  -H "Content-Type: application/json" \
  -d "{
    \"ms_paths\": [$(echo $MS_FILES | sed 's/ /","/g')],
    \"parameters\": {
      \"quality_tier\": \"standard\"
    }
  }"
```

### Workflow 2: Reprocess Historical Data

```bash
# Process data from multiple days
for date in 2025-10-28 2025-10-29 2025-10-30; do
    python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
        /data/incoming \
        /stage/dsa110-contimg/ms \
        "${date} 00:00:00" \
        "${date} 23:59:59" \
        --writer parallel-subband
done
```

### Workflow 3: Calibrator Transit Processing

```bash
# Process specific calibrator transit
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30 \
    --window-minutes 60 \
    --writer parallel-subband
```

## Troubleshooting

### Batch Jobs Stuck in "Pending"

- **Check API server**: Ensure the API server is running
- **Check background tasks**: Verify background task execution
- **Review logs**: Check API server logs for errors

### Individual Items Failing

- **Check error messages**: Use `GET /api/batch/{batch_id}` to see error details
- **Verify input files**: Ensure MS files exist and are accessible
- **Check disk space**: Ensure sufficient disk space for outputs

### Slow Batch Processing

- **Reduce parallel workers**: Lower `--max-workers` if system is overloaded
- **Process smaller batches**: Break large batches into smaller chunks
- **Use faster storage**: Use SSD or tmpfs for intermediate files

## Related Documentation

- [Using the Orchestrator CLI](USING_ORCHESTRATOR_CLI.md) - Conversion
  orchestrator details
- [Batch Mode Development Assessment](../dev/analysis/batch_mode_development_assessment.md) -
  Feature completeness
- [API Reference](../../reference/dashboard_backend_api.md) - Complete API
  documentation
- [Pipeline Testing Guide](../qa/PIPELINE_TESTING_GUIDE.md) - Testing batch workflows

## Summary

Batch mode provides three main approaches:

1. **CLI Tools**: Direct command-line execution for each stage
2. **API Endpoints**: Programmatic batch job submission with tracking
3. **Orchestrator Scripts**: End-to-end automation for complete workflows

Choose the method that best fits your workflow:

- **CLI**: Simple scripts and one-off processing
- **API**: Production systems with job tracking and monitoring
- **Orchestrator**: Complete automation from raw data to published products
