# ESE Detection Architecture

## Overview

The ESE (Extreme Scattering Event) detection system automatically identifies
radio sources with significant flux variability (>5σ) by analyzing photometry
measurements over time. This document describes the architecture and design
decisions.

## System Components

### 1. Core Detection Module

**File**: `src/dsa110_contimg/photometry/ese_detection.py`

**Key Functions**:

- `detect_ese_candidates()`: Main detection function
- `_recompute_variability_stats()`: Recompute statistics from photometry

**Responsibilities**:

- Query variability statistics
- Flag ESE candidates based on sigma threshold
- Manage `ese_candidates` table

### 2. Pipeline Integration Module

**File**: `src/dsa110_contimg/photometry/ese_pipeline.py`

**Key Functions**:

- `update_variability_stats_for_source()`: Update stats for single source
- `auto_detect_ese_for_new_measurements()`: Single-source auto-detection
- `auto_detect_ese_after_photometry()`: Batch auto-detection

**Responsibilities**:

- Automatic variability stats computation
- Automatic ESE candidate detection
- Integration with photometry pipeline

### 3. CLI Interface

**File**: `src/dsa110_contimg/photometry/cli.py`

**Command**: `ese-detect`

**Responsibilities**:

- Command-line interface for ESE detection
- Parameter parsing and validation
- JSON output formatting

### 4. API Endpoints

**File**: `src/dsa110_contimg/api/routes.py`

**Endpoints**:

- `POST /api/jobs/ese-detect`: Single job endpoint
- `POST /api/batch/ese-detect`: Batch job endpoint

**Responsibilities**:

- REST API for ESE detection
- Job creation and management
- Background task execution

### 5. Job Adapters

**File**: `src/dsa110_contimg/api/job_adapters.py`

**Functions**:

- `run_ese_detect_job()`: Single job execution
- `run_batch_ese_detect_job()`: Batch job execution

**Responsibilities**:

- Job execution logic
- Status updates
- Error handling

### 6. Photometry Integration

**File**: `src/dsa110_contimg/api/job_adapters.py`

**Function**: `run_batch_photometry_job()`

**Integration Points**:

- After photometry measurement storage
- Automatic ESE detection trigger
- Source ID generation

## Data Flow

### Manual Detection Flow

```
User Request (CLI/API)
    ↓
detect_ese_candidates()
    ↓
Query variability_stats (sigma_deviation >= min_sigma)
    ↓
Insert/Update ese_candidates table
    ↓
Return candidate list
```

### Automated Detection Flow

```
Photometry Measurement
    ↓
Store in photometry table (with source_id)
    ↓
update_variability_stats_for_source()
    ↓
Compute statistics (mean, std, sigma_deviation, etc.)
    ↓
Update variability_stats table
    ↓
auto_detect_ese_for_new_measurements()
    ↓
Check sigma_deviation >= min_sigma
    ↓
If qualified: Flag in ese_candidates table
    ↓
Log detected candidate
```

## Database Schema

### photometry Table

Stores individual photometry measurements:

```sql
CREATE TABLE photometry (
    image_path TEXT,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    nvss_flux_mjy REAL,
    peak_jyb REAL NOT NULL,
    peak_err_jyb REAL,
    measured_at REAL NOT NULL,
    source_id TEXT,  -- Generated from coordinates
    mjd REAL         -- Modified Julian Date
);
```

### variability_stats Table

Stores computed variability statistics per source:

```sql
CREATE TABLE variability_stats (
    source_id TEXT PRIMARY KEY,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    nvss_flux_mjy REAL,
    n_obs INTEGER DEFAULT 0,
    mean_flux_mjy REAL,
    std_flux_mjy REAL,
    min_flux_mjy REAL,
    max_flux_mjy REAL,
    chi2_nu REAL,
    sigma_deviation REAL,  -- Key metric for ESE detection
    eta_metric REAL,
    last_measured_at REAL,
    last_mjd REAL,
    updated_at REAL NOT NULL
);
```

### ese_candidates Table

Stores flagged ESE candidates:

```sql
CREATE TABLE ese_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    flagged_at REAL NOT NULL,
    flagged_by TEXT DEFAULT 'auto',
    significance REAL NOT NULL,  -- sigma_deviation value
    flag_type TEXT NOT NULL,
    notes TEXT,
    status TEXT DEFAULT 'active',
    investigated_at REAL,
    dismissed_at REAL,
    FOREIGN KEY (source_id) REFERENCES variability_stats(source_id)
);
```

## Variability Metrics

### Sigma Deviation

Primary metric for ESE detection:

```
sigma_deviation = max(|max_flux - mean_flux|, |min_flux - mean_flux|) / std_flux
```

- **5.0 sigma**: Standard ESE threshold
- **6.0+ sigma**: High confidence candidates
- **7.0+ sigma**: Very high confidence

### Chi-Squared Per Degree of Freedom

Measures goodness of fit:

```
chi2_nu = Σ((flux_i - mean_flux)² / err_i²) / (n_obs - 1)
```

### Eta Metric

Weighted variance metric (from VAST Tools):

```
eta = Σ(w_i * (flux_i - mean_weighted)²) / Σ(w_i)
```

where `w_i = 1 / err_i²`

## Source ID Generation

Sources are identified using IAU-style coordinate-based IDs:

**Format**: `JHHMMSS+DDMMSS`

**Generation**:

1. Round RA/Dec to nearest arcsecond
2. Convert to hours/minutes/seconds format
3. Format as
   `J{ra_h:02d}{ra_m:02d}{ra_s:02d}{dec_sign}{dec_d:02d}{dec_m:02d}{dec_s:02d}`

**Example**: RA=120.0°, Dec=45.0° → `J120000+450000`

**Benefits**:

- Consistent identification across measurements
- Human-readable format
- No database lookup required

## Configuration

### Photometry Job Parameters

```python
{
    "auto_detect_ese": True,      # Enable/disable auto-detection
    "ese_min_sigma": 5.0,        # Minimum sigma threshold
}
```

### Environment Variables

- `PIPELINE_PRODUCTS_DB`: Products database path
- `MASTER_SOURCES_DB`: Master sources database path

## Error Handling

### Graceful Degradation

- Missing tables: Logs warning, returns empty list
- Database errors: Caught and logged, doesn't crash pipeline
- Missing photometry: Skips source, continues processing

### Error Types

1. **Missing Database**: Returns empty list, logs warning
2. **Missing Tables**: Creates schema if possible, otherwise skips
3. **Computation Errors**: Logs error, continues with other sources
4. **Database Lock**: Uses timeout, retries if needed

## Performance Considerations

### Incremental Updates

- Only updates variability stats for measured sources
- Single-source optimization for new measurements
- Batch processing for multiple sources

### Database Optimization

- Indexes on `source_id` columns
- Efficient queries with WHERE clauses
- Connection pooling for API requests

### Scalability

- Background job execution for long-running tasks
- Batch processing for multiple sources
- Non-blocking auto-detection in photometry pipeline

## Testing Strategy

### Unit Tests

- Core detection logic (`test_ese_detection.py`)
- CLI interface (`test_ese_cli.py`)
- API endpoints (`test_ese_endpoints.py`)
- Job adapters (`test_ese_job_adapters.py`)
- Pipeline integration (`test_ese_pipeline.py`)

### Integration Tests

- End-to-end detection flow
- Database schema evolution
- Error handling scenarios

### Smoke Tests

- Quick validation of full pipeline
- Database verification
- Idempotency testing

## Future Enhancements

### Potential Improvements

1. **Caching**: Cache variability stats to reduce database queries
2. **Parallel Processing**: Process multiple sources in parallel
3. **Real-time Alerts**: Alert on high-significance candidates
4. **Monitoring**: Track detection success/failure rates
5. **Advanced Metrics**: Additional variability metrics (e.g., structure
   function)

### Integration Opportunities

1. **Dashboard**: Real-time ESE candidate display
2. **Alerting**: Email/Slack notifications for new candidates
3. **Analysis Tools**: Lightcurve visualization for candidates
4. **Cross-matching**: Match with external catalogs

## Related Documentation

- [ESE Detection Guide](../../how-to/ese_detection_guide.md)
- [Implementation Summary](../../dev/ese_detection_implementation_summary.md)
- [Automated Pipeline Summary](../../dev/ese_automated_pipeline_summary.md)
- [Database Schema](../../reference/database_schema.md)
