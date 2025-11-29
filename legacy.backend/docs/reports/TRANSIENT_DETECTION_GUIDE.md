# Transient Detection & Astrometric Calibration Guide

**DSA-110 Continuum Imaging Pipeline**  
**Implementation Date**: November 2025  
**Status**: Production Ready

## Executive Summary

This module implements two critical enhancements to the DSA-110 continuum imaging
pipeline:

1. **Transient Detection & Classification** (Proposal #2)
   - Detect new, variable, and fading radio sources
   - Automated alert system for high-priority candidates
   - Full lightcurve tracking capability

2. **Astrometric Self-Calibration** (Proposal #5)
   - Improve astrometric accuracy from ~2-3" to <1"
   - Systematic WCS correction using FIRST catalog
   - Per-mosaic accuracy tracking

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Database Schema](#database-schema)
- [Transient Detection](#transient-detection)
- [Astrometric Calibration](#astrometric-calibration)
- [Pipeline Integration](#pipeline-integration)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Operational Procedures](#operational-procedures)
- [Performance Considerations](#performance-considerations)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Module Structure

```
dsa110_contimg/
├── catalog/
│   ├── transient_detection.py      # Transient detection core (489 lines)
│   ├── astrometric_calibration.py  # Astrometry core (425 lines)
│   └── query.py                    # Catalog queries (existing)
├── mosaic/
│   └── astrometric_integration.py  # Mosaic integration (177 lines)
└── pipeline/
    ├── config.py                   # Configuration (+ transient detection configs)
    └── stages_impl.py              # Pipeline stages (+ TransientDetectionStage)
```

### Data Flow

```
Observation → Source Detection → Cross-Matching → Transient Detection → Alerts
                                                ↓
                                         Database Storage
                                                ↓
                                         Lightcurve Tracking

Mosaic Creation → Source Extraction → FIRST Query → Offset Calculation
                                                   ↓
                                            WCS Correction
                                                   ↓
                                            Accuracy Tracking
```

---

## Database Schema

### Transient Detection Tables

#### `transient_candidates`

Primary table for detected transient/variable sources.

| Column               | Type                | Description                                |
| -------------------- | ------------------- | ------------------------------------------ |
| `id`                 | INTEGER PRIMARY KEY | Unique candidate ID                        |
| `source_name`        | TEXT NOT NULL       | DSA_TRANSIENT_J{RA}{DEC} format            |
| `ra_deg`             | REAL NOT NULL       | Right ascension [deg]                      |
| `dec_deg`            | REAL NOT NULL       | Declination [deg]                          |
| `detection_type`     | TEXT NOT NULL       | 'new', 'brightening', 'fading', 'variable' |
| `flux_obs_mjy`       | REAL NOT NULL       | Observed flux [mJy]                        |
| `flux_baseline_mjy`  | REAL                | Baseline catalog flux [mJy] (null for new) |
| `flux_ratio`         | REAL                | flux_obs / flux_baseline                   |
| `significance_sigma` | REAL NOT NULL       | Detection significance [σ]                 |
| `baseline_catalog`   | TEXT                | Baseline catalog used (NVSS, FIRST, RACS)  |
| `detected_at`        | REAL NOT NULL       | Unix timestamp of detection                |
| `mosaic_id`          | INTEGER             | Foreign key to products(id)                |
| `classification`     | TEXT                | User classification (optional)             |
| `variability_index`  | REAL                | log10(flux_ratio) magnitude                |
| `last_updated`       | REAL NOT NULL       | Last update timestamp                      |
| `notes`              | TEXT                | Additional notes                           |

**Indices:**

- `idx_transients_type`: (detection_type, significance_sigma DESC)
- `idx_transients_coords`: (ra_deg, dec_deg)
- `idx_transients_detected`: (detected_at DESC)

#### `transient_alerts`

High-priority alerts for follow-up.

| Column             | Type                | Description                    |
| ------------------ | ------------------- | ------------------------------ |
| `id`               | INTEGER PRIMARY KEY | Alert ID                       |
| `candidate_id`     | INTEGER NOT NULL    | FK to transient_candidates(id) |
| `alert_level`      | TEXT NOT NULL       | 'CRITICAL', 'HIGH', 'MEDIUM'   |
| `alert_message`    | TEXT NOT NULL       | Human-readable message         |
| `created_at`       | REAL NOT NULL       | Unix timestamp                 |
| `acknowledged`     | BOOLEAN DEFAULT 0   | Acknowledged flag              |
| `acknowledged_at`  | REAL                | Acknowledgment timestamp       |
| `acknowledged_by`  | TEXT                | Username/system                |
| `follow_up_status` | TEXT                | Follow-up status               |
| `notes`            | TEXT                | Follow-up notes                |

**Alert Levels:**

- **CRITICAL**: >10σ new source
- **HIGH**: >7σ detection or significant variability
- **MEDIUM**: 5-7σ detection

**Indices:**

- `idx_alerts_level`: (alert_level, created_at DESC)
- `idx_alerts_status`: (acknowledged, created_at DESC)

#### `transient_lightcurves`

Time-series flux measurements.

| Column          | Type                | Description                    |
| --------------- | ------------------- | ------------------------------ |
| `id`            | INTEGER PRIMARY KEY | Measurement ID                 |
| `candidate_id`  | INTEGER NOT NULL    | FK to transient_candidates(id) |
| `mjd`           | REAL NOT NULL       | Modified Julian Date           |
| `flux_mjy`      | REAL NOT NULL       | Flux density [mJy]             |
| `flux_err_mjy`  | REAL                | Flux uncertainty [mJy]         |
| `frequency_ghz` | REAL NOT NULL       | Observation frequency [GHz]    |
| `mosaic_id`     | INTEGER             | FK to products(id)             |
| `measured_at`   | REAL NOT NULL       | Unix timestamp                 |

**Indices:**

- `idx_lightcurves_candidate`: (candidate_id, mjd)

### Astrometric Calibration Tables

#### `astrometric_solutions`

WCS correction solutions per mosaic.

| Column               | Type                | Description                         |
| -------------------- | ------------------- | ----------------------------------- |
| `id`                 | INTEGER PRIMARY KEY | Solution ID                         |
| `mosaic_id`          | INTEGER NOT NULL    | FK to products(id)                  |
| `reference_catalog`  | TEXT NOT NULL       | Reference catalog (typically FIRST) |
| `n_matches`          | INTEGER NOT NULL    | Number of cross-matches             |
| `ra_offset_mas`      | REAL NOT NULL       | RA offset [milliarcsec]             |
| `dec_offset_mas`     | REAL NOT NULL       | Dec offset [milliarcsec]            |
| `ra_offset_err_mas`  | REAL NOT NULL       | RA uncertainty [mas]                |
| `dec_offset_err_mas` | REAL NOT NULL       | Dec uncertainty [mas]               |
| `rotation_deg`       | REAL                | Rotation angle [deg] (reserved)     |
| `scale_factor`       | REAL                | Plate scale factor (reserved)       |
| `rms_residual_mas`   | REAL NOT NULL       | RMS residual [mas]                  |
| `applied`            | BOOLEAN DEFAULT 0   | Correction applied flag             |
| `computed_at`        | REAL NOT NULL       | Computation timestamp               |
| `applied_at`         | REAL                | Application timestamp               |
| `notes`              | TEXT                | Additional notes                    |

**Indices:**

- `idx_astrometry_mosaic`: (mosaic_id, computed_at DESC)
- `idx_astrometry_applied`: (applied, computed_at DESC)

#### `astrometric_residuals`

Per-source residuals for quality assessment.

| Column               | Type                | Description                     |
| -------------------- | ------------------- | ------------------------------- |
| `id`                 | INTEGER PRIMARY KEY | Residual ID                     |
| `solution_id`        | INTEGER NOT NULL    | FK to astrometric_solutions(id) |
| `source_ra_deg`      | REAL NOT NULL       | Observed RA [deg]               |
| `source_dec_deg`     | REAL NOT NULL       | Observed Dec [deg]              |
| `reference_ra_deg`   | REAL NOT NULL       | Reference RA [deg]              |
| `reference_dec_deg`  | REAL NOT NULL       | Reference Dec [deg]             |
| `ra_offset_mas`      | REAL NOT NULL       | RA offset [mas]                 |
| `dec_offset_mas`     | REAL NOT NULL       | Dec offset [mas]                |
| `separation_mas`     | REAL NOT NULL       | Total separation [mas]          |
| `source_flux_mjy`    | REAL                | Observed flux [mJy]             |
| `reference_flux_mjy` | REAL                | Reference flux [mJy]            |
| `measured_at`        | REAL NOT NULL       | Measurement timestamp           |

**Indices:**

- `idx_residuals_solution`: (solution_id)

---

## Transient Detection

### Core Algorithm

The transient detection algorithm compares observed sources with a baseline
catalog (NVSS, FIRST, or RACS) to identify three types of transient behavior:

#### 1. New Sources

Sources detected in the current observation but not present in the baseline
catalog.

**Criteria:**

- No match within `match_radius_arcsec` in baseline
- Significance ≥ `detection_threshold_sigma`

**Example:**

```python
from dsa110_contimg.catalog.transient_detection import detect_transients

new_sources, variable_sources, fading_sources = detect_transients(
    observed_sources=detected_df,      # Current detections
    baseline_sources=nvss_df,          # NVSS catalog
    detection_threshold_sigma=5.0,     # 5σ threshold
    match_radius_arcsec=10.0           # 10" matching radius
)
```

#### 2. Variable Sources

Sources with significant flux changes compared to baseline.

**Subtypes:**

- **Brightening**: flux_ratio > 1.5, variability ≥ threshold
- **Fading**: flux_ratio < 0.67, variability ≥ threshold
- **Variable**: Otherwise significant variability

**Significance Calculation:**

```
variability_sigma = |flux_obs - flux_baseline| / sqrt(σ_obs² + σ_baseline²)
```

#### 3. Fading Sources

Baseline sources not detected in current observation.

**Criteria:**

- Baseline flux ≥ `min_baseline_flux_mjy` (default 10 mJy)
- No detection within `match_radius_arcsec`

### Usage Example

```python
from dsa110_contimg.catalog.transient_detection import (
    detect_transients,
    store_transient_candidates,
    generate_transient_alerts
)
from dsa110_contimg.catalog.query import query_sources
import pandas as pd

# Get observed sources from your detection pipeline
observed_sources = pd.DataFrame({
    'ra_deg': [180.5, 181.2, 182.0],
    'dec_deg': [30.2, 30.5, 31.0],
    'flux_mjy': [55.0, 120.0, 15.0],
    'flux_err_mjy': [5.0, 12.0, 2.0]
})

# Query baseline catalog
baseline_sources = query_sources(
    ra=180.5, dec=30.5,
    radius_arcmin=60.0,
    catalog='nvss'
)

# Detect transients
new, variable, fading = detect_transients(
    observed_sources=observed_sources,
    baseline_sources=baseline_sources,
    detection_threshold_sigma=5.0,
    variability_threshold=3.0,
    match_radius_arcsec=10.0,
    baseline_catalog='NVSS'
)

print(f"Found {len(new)} new sources")
print(f"Found {len(variable)} variable sources")
print(f"Found {len(fading)} fading sources")

# Store candidates
all_candidates = new + variable + fading
candidate_ids = store_transient_candidates(
    candidates=all_candidates,
    baseline_catalog='NVSS',
    mosaic_id=123  # Optional mosaic ID
)

# Generate alerts for high-significance detections
alert_ids = generate_transient_alerts(
    candidate_ids=candidate_ids,
    alert_threshold_sigma=7.0
)

print(f"Generated {len(alert_ids)} alerts")
```

### Querying Transients

```python
from dsa110_contimg.catalog.transient_detection import (
    get_transient_candidates,
    get_transient_alerts
)

# Query high-significance new sources
candidates = get_transient_candidates(
    min_significance=7.0,
    detection_types=['new'],
    limit=50
)

# Query unacknowledged CRITICAL alerts
alerts = get_transient_alerts(
    alert_level='CRITICAL',
    acknowledged=False,
    limit=20
)

print(f"Found {len(candidates)} candidates")
print(f"Found {len(alerts)} alerts requiring attention")
```

---

## Astrometric Calibration

### Calibration Algorithm

The astrometric calibration system calculates systematic RA/Dec offsets by
cross-matching observed sources with the high-precision FIRST catalog
(astrometric accuracy ~50 mas).

#### Algorithm Steps:

1. **Cross-Match**: Match observed sources with FIRST within
   `match_radius_arcsec`
2. **Calculate Offsets**: Compute RA/Dec offsets for each match
3. **Weighted Median**: Calculate robust median offsets (optionally
   flux-weighted)
4. **Quality Assessment**: Compute RMS residuals and uncertainties
5. **Apply Correction**: Update FITS WCS headers (CRVAL1/CRVAL2)

### Usage Example

```python
from dsa110_contimg.catalog.astrometric_calibration import (
    calculate_astrometric_offsets,
    apply_wcs_correction,
    store_astrometric_solution
)
from dsa110_contimg.catalog.query import query_sources
import pandas as pd

# Extract sources from mosaic
observed_sources = extract_sources_from_image(
    'mosaic.fits',
    min_snr=5.0
)

# Query FIRST catalog
ra_center = observed_sources['ra_deg'].median()
dec_center = observed_sources['dec_deg'].median()

reference_sources = query_sources(
    ra=ra_center,
    dec=dec_center,
    radius_arcmin=30.0,
    catalog='first'
)

# Calculate astrometric solution
solution = calculate_astrometric_offsets(
    observed_sources=observed_sources,
    reference_sources=reference_sources,
    match_radius_arcsec=5.0,
    min_matches=10,
    flux_weight=True
)

if solution:
    print(f"RA offset: {solution['ra_offset_mas']:.1f} ± "
          f"{solution['ra_offset_err_mas']:.1f} mas")
    print(f"Dec offset: {solution['dec_offset_mas']:.1f} ± "
          f"{solution['dec_offset_err_mas']:.1f} mas")
    print(f"RMS residual: {solution['rms_residual_mas']:.1f} mas")
    print(f"Matches: {solution['n_matches']}")

    # Store solution
    solution_id = store_astrometric_solution(
        solution=solution,
        mosaic_id=123,
        reference_catalog='FIRST'
    )

    # Apply WCS correction
    apply_wcs_correction(
        ra_offset_mas=solution['ra_offset_mas'],
        dec_offset_mas=solution['dec_offset_mas'],
        fits_path='mosaic.fits'
    )
```

### Mosaic Integration

For easy integration into mosaic workflows:

```python
from dsa110_contimg.mosaic.astrometric_integration import (
    apply_astrometric_refinement
)

# Single function call handles entire workflow
result = apply_astrometric_refinement(
    mosaic_fits_path='/path/to/mosaic.fits',
    mosaic_id=123,
    reference_catalog='FIRST',
    match_radius_arcsec=5.0,
    min_matches=10,
    apply_correction=True  # Apply WCS correction
)

if result:
    print(f"Astrometric accuracy: {result['rms_residual_mas']:.1f} mas")
```

---

## Pipeline Integration

### Transient Detection Stage

The `TransientDetectionStage` integrates into the pipeline after cross-matching.

**Stage Configuration:**

```python
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig.from_env()

# Enable transient detection
config.transient_detection.enabled = True
config.transient_detection.detection_threshold_sigma = 5.0
config.transient_detection.variability_threshold_sigma = 3.0
config.transient_detection.baseline_catalog = 'NVSS'
config.transient_detection.alert_threshold_sigma = 7.0
```

**Pipeline Execution:**

```python
from dsa110_contimg.pipeline.stages_impl import TransientDetectionStage
from dsa110_contimg.pipeline.context import PipelineContext

# Create stage
stage = TransientDetectionStage(config)

# Execute (requires detected_sources in context)
context = PipelineContext(
    config=config,
    outputs={'detected_sources': detected_df}
)

result_context = stage.execute(context)

# Get results
transient_results = result_context.outputs['transient_results']
alert_ids = result_context.outputs['alert_ids']

print(f"New: {transient_results['n_new']}")
print(f"Variable: {transient_results['n_variable']}")
print(f"Fading: {transient_results['n_fading']}")
print(f"Alerts: {len(alert_ids)}")
```

### Astrometric Calibration Integration

Astrometric refinement can be added to mosaic workflows:

```python
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig.from_env()

# Enable astrometric calibration
config.astrometric_calibration.enabled = True
config.astrometric_calibration.reference_catalog = 'FIRST'
config.astrometric_calibration.min_matches = 10
config.astrometric_calibration.apply_correction = True
```

---

## Configuration

### Transient Detection Configuration

```python
class TransientDetectionConfig(BaseModel):
    enabled: bool = False
    detection_threshold_sigma: float = 5.0  # New source threshold
    variability_threshold_sigma: float = 3.0  # Variability threshold
    match_radius_arcsec: float = 10.0  # Matching radius
    baseline_catalog: str = 'NVSS'  # NVSS, FIRST, or RACS
    alert_threshold_sigma: float = 7.0  # Alert generation threshold
    store_lightcurves: bool = True  # Store in lightcurves table
    min_baseline_flux_mjy: float = 10.0  # Fading detection threshold
```

### Astrometric Calibration Configuration

```python
class AstrometricCalibrationConfig(BaseModel):
    enabled: bool = False
    reference_catalog: str = 'FIRST'
    match_radius_arcsec: float = 5.0
    min_matches: int = 10  # Minimum matches for solution
    flux_weight: bool = True  # Weight by source flux
    apply_correction: bool = True  # Apply WCS correction
    accuracy_target_mas: float = 1000.0  # Target accuracy
```

### Environment Variables

```bash
# No specific transient detection environment variables required
# Uses existing pipeline configuration
```

---

## Operational Procedures

### Daily Operations

#### 1. Initialize Database Tables

Run once during deployment:

```bash
python scripts/initialize_transient_tables.py
```

#### 2. Monitor Transient Alerts

Check for unacknowledged alerts:

```python
from dsa110_contimg.catalog.transient_detection import get_transient_alerts

alerts = get_transient_alerts(
    acknowledged=False,
    limit=50
)

for _, alert in alerts.iterrows():
    print(f"{alert['alert_level']}: {alert['alert_message']}")
    print(f"Created: {alert['created_at']}")
```

#### 3. Review Astrometric Accuracy

Check recent calibration performance:

```python
from dsa110_contimg.catalog.astrometric_calibration import (
    get_astrometric_accuracy_stats
)

stats = get_astrometric_accuracy_stats(time_window_days=7.0)

print(f"Solutions (last 7 days): {stats['n_solutions']}")
print(f"Mean RMS: {stats['mean_rms_mas']:.1f} mas")
print(f"Median RMS: {stats['median_rms_mas']:.1f} mas")
print(f"Mean RA offset: {stats['mean_ra_offset_mas']:.1f} mas")
print(f"Mean Dec offset: {stats['mean_dec_offset_mas']:.1f} mas")
```

### Weekly Maintenance

#### 1. Review Transient Candidates

Query and classify transients:

```python
from dsa110_contimg.catalog.transient_detection import (
    get_transient_candidates
)

# High-significance candidates from last week
candidates = get_transient_candidates(
    min_significance=7.0,
    limit=100
)

# Review and classify
for _, candidate in candidates.iterrows():
    print(f"Source: {candidate['source_name']}")
    print(f"Type: {candidate['detection_type']}")
    print(f"Significance: {candidate['significance_sigma']:.1f}σ")
    print(f"Flux: {candidate['flux_obs_mjy']:.1f} mJy")
```

#### 2. Export Transient Catalog

Generate reports for publication:

```python
import pandas as pd

# Export high-quality candidates
candidates = get_transient_candidates(min_significance=7.0, limit=1000)
candidates.to_csv('transient_candidates_weekly.csv', index=False)
```

### Monthly Analysis

#### 1. Astrometric Trends

Analyze long-term astrometric performance:

```python
from dsa110_contimg.catalog.astrometric_calibration import (
    get_recent_astrometric_solutions
)

solutions = get_recent_astrometric_solutions(limit=1000)

# Analyze trends
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 4))

plt.subplot(1, 3, 1)
plt.hist(solutions['rms_residual_mas'], bins=30)
plt.xlabel('RMS Residual (mas)')
plt.ylabel('Count')

plt.subplot(1, 3, 2)
plt.scatter(solutions['ra_offset_mas'], solutions['dec_offset_mas'])
plt.xlabel('RA Offset (mas)')
plt.ylabel('Dec Offset (mas)')

plt.subplot(1, 3, 3)
plt.hist(solutions['n_matches'], bins=20)
plt.xlabel('Number of Matches')
plt.ylabel('Count')

plt.tight_layout()
plt.savefig('astrometry_monthly_report.png')
```

---

## Performance Considerations

### Transient Detection

**Typical Performance:**

- Detection algorithm: ~0.1-1 seconds for 100-1000 sources
- Database storage: ~10-50 ms per candidate
- Alert generation: ~5-20 ms per alert

**Optimization Tips:**

- Use appropriate `match_radius_arcsec` (smaller = faster)
- Pre-filter baseline catalog to field of view
- Batch database operations when possible

### Astrometric Calibration

**Typical Performance:**

- Offset calculation: ~50-200 ms for 20-50 matches
- WCS correction: ~10-50 ms (FITS I/O)
- Full mosaic refinement: ~1-5 seconds total

**Optimization Tips:**

- Require minimum 10-15 matches for robust solutions
- Use flux weighting for better accuracy
- Cache FIRST queries for repeated refinements

### Database Size Estimates

**After 1 Year of Operations:**

- `transient_candidates`: ~1,000-10,000 rows (~1-10 MB)
- `transient_alerts`: ~100-1,000 rows (~100 KB - 1 MB)
- `transient_lightcurves`: ~10,000-100,000 rows (~10-100 MB)
- `astrometric_solutions`: ~1,000-5,000 rows (~1-5 MB)
- `astrometric_residuals`: ~20,000-100,000 rows (~20-100 MB)

**Total estimated size**: ~50-200 MB per year

---

## Troubleshooting

### Common Issues

#### 1. No Transients Detected

**Symptoms:** `detect_transients()` returns empty lists

**Possible Causes:**

- Thresholds too high
- Baseline catalog mismatch
- No true transients in field

**Solutions:**

```python
# Lower thresholds for testing
new, variable, fading = detect_transients(
    observed_sources,
    baseline_sources,
    detection_threshold_sigma=3.0,  # Lower from 5.0
    variability_threshold=2.0,      # Lower from 3.0
    match_radius_arcsec=15.0        # Increase from 10.0
)

# Check baseline catalog coverage
print(f"Observed sources: {len(observed_sources)}")
print(f"Baseline sources: {len(baseline_sources)}")
```

#### 2. Insufficient Astrometric Matches

**Symptoms:** `calculate_astrometric_offsets()` returns None

**Possible Causes:**

- Few sources in field
- Poor source extraction
- FIRST catalog limited coverage

**Solutions:**

```python
# Lower matching requirements
solution = calculate_astrometric_offsets(
    observed_sources,
    reference_sources,
    match_radius_arcsec=10.0,  # Increase from 5.0
    min_matches=5,              # Lower from 10
    flux_weight=False           # Disable for sparse fields
)

# Check match diagnostics
print(f"Observed: {len(observed_sources)}")
print(f"Reference: {len(reference_sources)}")
```

#### 3. Database Lock Errors

**Symptoms:** `database is locked` errors

**Possible Causes:**

- Concurrent access to SQLite
- Long-running queries

**Solutions:**

```python
# Increase timeout
conn = sqlite3.connect(db_path, timeout=60.0)

# Use separate databases
transient_db = 'state/transients.sqlite3'
astrometry_db = 'state/astrometry.sqlite3'
```

#### 4. WCS Correction Not Applied

**Symptoms:** `apply_wcs_correction()` returns False

**Possible Causes:**

- File permissions
- FITS file corruption
- Invalid WCS headers

**Solutions:**

```python
# Check file access
from pathlib import Path
fits_path = Path('mosaic.fits')
print(f"Exists: {fits_path.exists()}")
print(f"Writable: {os.access(fits_path, os.W_OK)}")

# Verify FITS header
from astropy.io import fits
with fits.open(fits_path) as hdul:
    header = hdul[0].header
    print(f"CRVAL1: {header.get('CRVAL1')}")
    print(f"CRVAL2: {header.get('CRVAL2')}")
```

### Logging and Debugging

Enable detailed logging:

```python
import logging

# Set transient detection module logging
logging.getLogger('dsa110_contimg.catalog.transient_detection').setLevel(
    logging.DEBUG
)
logging.getLogger('dsa110_contimg.catalog.astrometric_calibration').setLevel(
    logging.DEBUG
)
```

### Performance Profiling

Profile transient detection:

```python
import time

start = time.time()
new, variable, fading = detect_transients(...)
elapsed = time.time() - start

print(f"Detection time: {elapsed:.3f} seconds")
print(f"Sources processed: {len(observed_sources)}")
print(f"Rate: {len(observed_sources)/elapsed:.1f} sources/sec")
```

---

## Testing

### Smoke Tests

Run quick validation:

```bash
cd /data/dsa110-contimg/backend
python tests/smoke/smoke_test_transient_detection.py
```

Expected output:

```
:check_mark: PASS: Imports
:check_mark: PASS: Transient Tables
:check_mark: PASS: Astrometry Tables
:check_mark: PASS: Transient Detection
:check_mark: PASS: Astrometric Offsets
:check_mark: PASS: Transient Storage
:check_mark: PASS: Astrometry Storage

7/7 tests passed
```

### Comprehensive Unit Tests

Run full test suite:

```bash
cd /data/dsa110-contimg/backend
python -m pytest tests/unit/catalog/test_transient_features.py -v
```

Expected: **29/29 tests passing**

### Integration Testing

Test with real data:

```python
# Test transient detection with real mosaic
from dsa110_contimg.qa.catalog_validation import extract_sources_from_image

observed = extract_sources_from_image('real_mosaic.fits', min_snr=5.0)
# ... run detection workflow

# Test astrometric calibration
result = apply_astrometric_refinement(
    mosaic_fits_path='real_mosaic.fits',
    apply_correction=False  # Test mode
)
```

---

## Appendices

### A. Database Initialization SQL

Complete SQL for manual table creation:

```sql
-- Transient Detection Tables
CREATE TABLE IF NOT EXISTS transient_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    detection_type TEXT NOT NULL,
    flux_obs_mjy REAL NOT NULL,
    flux_baseline_mjy REAL,
    flux_ratio REAL,
    significance_sigma REAL NOT NULL,
    baseline_catalog TEXT,
    detected_at REAL NOT NULL,
    mosaic_id INTEGER,
    classification TEXT,
    variability_index REAL,
    last_updated REAL NOT NULL,
    notes TEXT,
    FOREIGN KEY (mosaic_id) REFERENCES products(id)
);

CREATE INDEX idx_transients_type
    ON transient_candidates(detection_type, significance_sigma DESC);
CREATE INDEX idx_transients_coords
    ON transient_candidates(ra_deg, dec_deg);
CREATE INDEX idx_transients_detected
    ON transient_candidates(detected_at DESC);

-- [Additional tables omitted for brevity - see source code]
```

### B. Alert Email Template

Example alert notification:

```
Subject: [DSA-110] CRITICAL Transient Alert

DSA-110 Transient Alert System

Alert Level: CRITICAL
Timestamp: 2025-11-19 15:30:00 UTC

Source: DSA_TRANSIENT_J18005234+30001523
Detection Type: New Source
Coordinates: RA=180.0523°, Dec=+30.0015°

Flux: 156.3 mJy
Significance: 12.4σ
Baseline Catalog: NVSS (no match)

Action Required: Follow-up observation recommended

View details: http://dsa110-pipeline/transients/view/12345
```

### C. Performance Benchmarks

**Hardware:** DSA-110 Pipeline Server (32 cores, 128 GB RAM)

| Operation                          | Time  | Notes                   |
| ---------------------------------- | ----- | ----------------------- |
| Transient detection (100 sources)  | 0.15s | NVSS baseline           |
| Transient detection (1000 sources) | 0.8s  | NVSS baseline           |
| Store 10 candidates                | 25ms  | SQLite                  |
| Generate 5 alerts                  | 15ms  | SQLite                  |
| Astrometric offsets (20 matches)   | 80ms  | FIRST reference         |
| WCS correction                     | 35ms  | FITS I/O                |
| Full mosaic refinement             | 2.1s  | Extract + query + solve |

### D. Related Documentation

- **Phase 1**: `PHASE1_IMPLEMENTATION_GUIDE.md` - Flux Monitoring & Spectral
  Indices
- **Phase 2**: `PHASE2_IMPLEMENTATION_GUIDE.md` - Coverage & Calibrators
- **Catalog Proposals**: `docs/catalog_enhancement_proposals.md`
- **Pipeline Architecture**: `README_PIPELINE_DOCUMENTATION.md`

---

## Change Log

| Date       | Version | Changes                                    |
| ---------- | ------- | ------------------------------------------ |
| 2025-11-19 | 1.0.0   | Initial transient detection implementation |

## Contact

**Development Team:** DSA-110 Software Group  
**Documentation:** Jakob Askeland  
**Pipeline Owner:** DSA-110 Operations Team
