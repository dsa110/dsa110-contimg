# Automated ESE Detection Pipeline Implementation Summary

## Status: Complete (0% → 100%)

All components for automated ESE detection after photometry measurements have
been implemented.

## Implementation Overview

### 1. Automatic Variability Stats Computation

- **Status**: Complete
- **Location**: `src/dsa110_contimg/photometry/ese_pipeline.py`
- **Function**: `update_variability_stats_for_source()`
- **Functionality**:
  - Queries photometry table for source measurements
  - Computes variability statistics (mean, std, chi2_nu, sigma_deviation,
    eta_metric)
  - Updates `variability_stats` table with latest statistics
  - Handles idempotent updates (ON CONFLICT DO UPDATE)

### 2. Automatic ESE Candidate Detection

- **Status**: Complete
- **Location**: `src/dsa110_contimg/photometry/ese_pipeline.py`
- **Functions**:
  - `auto_detect_ese_for_new_measurements()`: Single-source detection after new
    measurement
  - `auto_detect_ese_after_photometry()`: Batch detection for multiple sources
- **Functionality**:
  - Automatically updates variability stats
  - Detects ESE candidates based on `sigma_deviation >= min_sigma`
  - Flags candidates in `ese_candidates` table
  - Returns list of detected candidates

### 3. Integration with Photometry Pipeline

- **Status**: Complete
- **Location**: `src/dsa110_contimg/api/job_adapters.py`
- **Function**: `run_batch_photometry_job()`
- **Integration Points**:
  1. After each photometry measurement:
     - Stores result in `photometry` table with `source_id`
     - Generates consistent source_id from coordinates (JHHMMSS+DDMMSS format)
     - Updates `source_id` and `mjd` columns if available
  2. Automatic ESE detection:
     - Calls `auto_detect_ese_for_new_measurements()` after storing measurement
     - Configurable via `auto_detect_ese` parameter (default: True)
     - Configurable `ese_min_sigma` threshold (default: 5.0)
     - Logs detected candidates

## Configuration

### Photometry Job Parameters

```python
{
    "auto_detect_ese": True,      # Enable/disable auto ESE detection (default: True)
    "ese_min_sigma": 5.0,        # Minimum sigma threshold (default: 5.0)
    # ... other photometry parameters
}
```

### API Usage

```bash
# Batch photometry with auto ESE detection (default)
curl -X POST http://localhost:8000/api/batch/photometry \
  -H "Content-Type: application/json" \
  -d '{
    "fits_paths": ["/path/to/image.fits"],
    "coordinates": [{"ra_deg": 120.0, "dec_deg": 45.0}],
    "params": {
      "auto_detect_ese": true,
      "ese_min_sigma": 5.0
    }
  }'

# Disable auto ESE detection
curl -X POST http://localhost:8000/api/batch/photometry \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "auto_detect_ese": false
    }
  }'
```

## Data Flow

```
Photometry Measurement
    ↓
Store in photometry table (with source_id)
    ↓
Update variability_stats for source
    ↓
Check sigma_deviation >= min_sigma
    ↓
If qualified: Flag in ese_candidates table
    ↓
Log detected candidate
```

## Source ID Generation

Sources are identified using IAU-style coordinate-based IDs:

- Format: `JHHMMSS+DDMMSS` (e.g., `J120000+450000`)
- Generated from RA/Dec coordinates rounded to nearest arcsecond
- Ensures consistent identification across measurements

## Database Schema

### photometry table

- `source_id`: Generated from coordinates
- `mjd`: Modified Julian Date (computed from measured_at)
- Other columns: image_path, ra_deg, dec_deg, peak_jyb, etc.

### variability_stats table

- Updated automatically after each photometry measurement
- Contains: n_obs, mean_flux_mjy, std_flux_mjy, sigma_deviation, etc.

### ese_candidates table

- Populated automatically when `sigma_deviation >= min_sigma`
- Contains: source_id, significance, flagged_at, status, etc.

## Error Handling

- **Missing tables**: Gracefully handles missing photometry/variability_stats
  tables
- **Failed updates**: Logs warnings but continues processing
- **ESE detection failures**: Non-fatal, logged but doesn't stop photometry job
- **Database errors**: Caught and logged, doesn't affect main photometry flow

## Performance Considerations

- **Incremental updates**: Only updates variability stats for measured sources
- **Single-source optimization**: `auto_detect_ese_for_new_measurements()`
  optimized for single-source updates
- **Batch processing**: `auto_detect_ese_after_photometry()` handles multiple
  sources efficiently
- **Non-blocking**: ESE detection runs asynchronously, doesn't block photometry
  measurements

## Test Coverage

### Unit Tests Created

1. **Pipeline Integration Tests** (`tests/unit/photometry/test_ese_pipeline.py`)
   - Test `update_variability_stats_for_source()`
   - Test `auto_detect_ese_for_new_measurements()`
   - Test `auto_detect_ese_after_photometry()`
   - Test error handling and edge cases

### Running Tests

```bash
# Run all ESE pipeline tests
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_pipeline.py -v

# Run specific test class
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_pipeline.py::TestAutoDetectESEForNewMeasurements -v
```

## Integration Points

### Photometry Job Adapter

- **File**: `src/dsa110_contimg/api/job_adapters.py`
- **Function**: `run_batch_photometry_job()`
- **Integration**: After storing each photometry measurement

### ESE Pipeline Module

- **File**: `src/dsa110_contimg/photometry/ese_pipeline.py`
- **Functions**:
  - `update_variability_stats_for_source()`
  - `auto_detect_ese_for_new_measurements()`
  - `auto_detect_ese_after_photometry()`

## Future Enhancements

Potential improvements:

1. Configurable batch size for variability stats updates
2. Caching of variability stats to reduce database queries
3. Parallel processing for multiple sources
4. Real-time alerts for high-significance candidates
5. Integration with monitoring/alerting systems

## Status: Complete

All automated ESE detection pipeline components are implemented, tested, and
integrated with the photometry pipeline. The system automatically:

- Stores photometry measurements with source IDs
- Computes variability statistics
- Detects and flags ESE candidates
- Logs detected candidates for review
