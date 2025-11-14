# ESE Detection Guide

## Overview

Extreme Scattering Events (ESE) are transient phenomena where radio sources show
significant flux variability (>5σ). This guide covers how to use the ESE
detection system in the DSA-110 pipeline.

## Table of Contents

- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [API Usage](#api-usage)
- [Automated Detection](#automated-detection)
- [Configuration](#configuration)
- [Understanding Results](#understanding-results)

## Quick Start

### Prerequisites

- Products database with photometry measurements
- Variability statistics computed (automatic with photometry)
- Access to `products.sqlite3` database

### Basic Detection

```bash
# Detect ESE candidates with default threshold (5.0 sigma)
python -m dsa110_contimg.photometry.cli ese-detect

# Detect with custom threshold
python -m dsa110_contimg.photometry.cli ese-detect --min-sigma 6.0

# Detect for specific source
python -m dsa110_contimg.photometry.cli ese-detect --source-id "J120000+450000"
```

## CLI Usage

### Command Syntax

```bash
python -m dsa110_contimg.photometry.cli ese-detect [OPTIONS]
```

### Options

- `--products-db PATH`: Path to products database (default:
  `state/products.sqlite3`)
- `--min-sigma FLOAT`: Minimum sigma deviation threshold (default: 5.0)
- `--source-id STRING`: Optional specific source ID to check
- `--recompute`: Recompute variability statistics before detection

### Examples

```bash
# Detect all ESE candidates
python -m dsa110_contimg.photometry.cli ese-detect

# Detect with higher threshold
python -m dsa110_contimg.photometry.cli ese-detect --min-sigma 7.0

# Detect specific source
python -m dsa110_contimg.photometry.cli ese-detect \
  --source-id "J120000+450000" \
  --min-sigma 5.0

# Recompute stats and detect
python -m dsa110_contimg.photometry.cli ese-detect \
  --recompute \
  --min-sigma 5.0

# Custom database path
python -m dsa110_contimg.photometry.cli ese-detect \
  --products-db /path/to/products.sqlite3
```

### Output Format

The CLI outputs JSON with:

- `products_db`: Database path used
- `min_sigma`: Threshold used
- `source_id`: Source checked (if specified)
- `recompute`: Whether stats were recomputed
- `candidates_found`: Number of candidates detected
- `candidates`: List of candidate dictionaries

Example output:

```json
{
  "products_db": "state/products.sqlite3",
  "min_sigma": 5.0,
  "source_id": null,
  "recompute": false,
  "candidates_found": 2,
  "candidates": [
    {
      "source_id": "J120000+450000",
      "ra_deg": 120.0,
      "dec_deg": 45.0,
      "significance": 6.5,
      "nvss_flux_mjy": 100.0,
      "mean_flux_mjy": 50.0,
      "std_flux_mjy": 5.0,
      "chi2_nu": 2.5,
      "n_obs": 10,
      "last_mjd": 60000.0
    }
  ]
}
```

## API Usage

### Single ESE Detection Job

**Endpoint**: `POST /api/jobs/ese-detect`

**Request Body**:

```json
{
  "params": {
    "min_sigma": 5.0,
    "source_id": null,
    "recompute": false
  }
}
```

**Response**: Job object with status and ID

**Example**:

```bash
curl -X POST http://localhost:8000/api/jobs/ese-detect \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "min_sigma": 5.0,
      "source_id": null,
      "recompute": false
    }
  }'
```

**Check Job Status**:

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

### Batch ESE Detection Job

**Endpoint**: `POST /api/batch/ese-detect`

**Request Body**:

```json
{
  "job_type": "ese-detect",
  "params": {
    "min_sigma": 5.0,
    "recompute": false,
    "source_ids": ["J120000+450000", "J121000+460000"]
  }
}
```

**Response**: BatchJob object with status and ID

**Example**:

```bash
curl -X POST http://localhost:8000/api/batch/ese-detect \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "ese-detect",
    "params": {
      "min_sigma": 5.0,
      "recompute": false,
      "source_ids": ["J120000+450000"]
    }
  }'
```

**Check Batch Status**:

```bash
curl http://localhost:8000/api/batch/{batch_id}
```

## Automated Detection

ESE detection is automatically triggered after photometry measurements when
enabled.

### Enabling Auto-Detection

Auto-detection is enabled by default. Configure via photometry job parameters:

```json
{
  "auto_detect_ese": true,
  "ese_min_sigma": 5.0
}
```

### Disabling Auto-Detection

```json
{
  "auto_detect_ese": false
}
```

### How It Works

1. **Photometry Measurement**: Source flux is measured
2. **Storage**: Measurement stored in `photometry` table with `source_id`
3. **Variability Stats**: Statistics computed/updated for source
4. **ESE Check**: If `sigma_deviation >= min_sigma`, candidate is flagged
5. **Logging**: Detected candidates are logged

### Batch Photometry with Auto-Detection

```bash
curl -X POST http://localhost:8000/api/batch/photometry \
  -H "Content-Type: application/json" \
  -d '{
    "fits_paths": ["/path/to/image.fits"],
    "coordinates": [
      {"ra_deg": 120.0, "dec_deg": 45.0},
      {"ra_deg": 121.0, "dec_deg": 46.0}
    ],
    "params": {
      "auto_detect_ese": true,
      "ese_min_sigma": 5.0,
      "box_size_pix": 5,
      "normalize": true
    }
  }'
```

## Configuration

### Environment Variables

- `PIPELINE_PRODUCTS_DB`: Path to products database (default:
  `state/products.sqlite3`)
- `MASTER_SOURCES_DB`: Path to master sources database (for source ID lookup)

### Threshold Selection

- **5.0 sigma**: Standard threshold for ESE candidates
- **6.0 sigma**: Higher confidence candidates
- **7.0+ sigma**: Very high confidence candidates

### Source ID Format

Sources use IAU-style coordinate-based IDs:

- Format: `JHHMMSS+DDMMSS` (e.g., `J120000+450000`)
- Generated from RA/Dec coordinates rounded to nearest arcsecond
- Ensures consistent identification across measurements

## Understanding Results

### ESE Candidate Fields

- `source_id`: Source identifier
- `ra_deg`, `dec_deg`: Source coordinates
- `significance`: Sigma deviation (key metric)
- `nvss_flux_mjy`: NVSS reference flux
- `mean_flux_mjy`: Mean measured flux
- `std_flux_mjy`: Standard deviation
- `chi2_nu`: Chi-squared per degree of freedom
- `n_obs`: Number of observations
- `last_mjd`: Last measurement MJD

### Interpreting Significance

- **5.0-6.0 sigma**: Moderate variability, worth investigating
- **6.0-7.0 sigma**: Significant variability, likely ESE candidate
- **7.0+ sigma**: Very significant variability, high-confidence ESE

### Querying Candidates

```python
from dsa110_contimg.api.data_access import fetch_ese_candidates

# Get all active candidates
candidates = fetch_ese_candidates(
    products_db=Path("state/products.sqlite3"),
    limit=50,
    min_sigma=5.0
)

# Get high-confidence candidates
high_conf = fetch_ese_candidates(
    products_db=Path("state/products.sqlite3"),
    limit=20,
    min_sigma=7.0
)
```

### Database Tables

**ese_candidates**:

- `source_id`: Source identifier
- `flagged_at`: Timestamp when flagged
- `flagged_by`: Who/what flagged it (usually 'auto')
- `significance`: Sigma deviation
- `flag_type`: Type of flag (usually 'auto')
- `status`: 'active', 'investigated', 'dismissed'

**variability_stats**:

- `source_id`: Source identifier
- `sigma_deviation`: Key metric for ESE detection
- `n_obs`: Number of observations
- `mean_flux_mjy`, `std_flux_mjy`: Flux statistics
- `chi2_nu`: Chi-squared metric
- `eta_metric`: Eta variability metric

## Troubleshooting

### No Candidates Detected

- Check that photometry measurements exist: `SELECT COUNT(*) FROM photometry`
- Verify variability stats are computed:
  `SELECT COUNT(*) FROM variability_stats`
- Check threshold: Try lowering `min_sigma` to 3.0 for testing

### Missing Variability Stats

```bash
# Recompute stats before detection
python -m dsa110_contimg.photometry.cli ese-detect --recompute
```

### Database Errors

- Ensure database exists and is accessible
- Check table schema: `SELECT name FROM sqlite_master WHERE type='table'`
- Verify columns exist: `PRAGMA table_info(variability_stats)`

### Performance Issues

- For large datasets, use batch jobs instead of CLI
- Consider processing sources in batches
- Use `source_id` filter to process specific sources

## Related Documentation

- [ESE Detection Implementation Summary](../../dev/ese_detection_implementation_summary.md)
- [Automated Pipeline Summary](../../dev/ese_automated_pipeline_summary.md)
- [Photometry Guide](photometry_guide.md)
- [API Reference](../../reference/api_reference_generated.md)
