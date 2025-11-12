# DSA-110 Validation Guide

## Overview

The DSA-110 continuum imaging pipeline includes comprehensive validation capabilities for assessing image quality, astrometry, flux scale, source completeness, photometry, variability, mosaics, streaming, and database consistency. This guide explains how to use the validation system.

**Note:** The validation system has been enhanced with a centralized configuration system and new validation modules. See [QA System Implementation](../dev/qa_system_implementation_complete.md) for details.

## Quick Start

### Fast Pipeline Validation (<60 seconds)

For rapid validation of the entire pipeline (MS, calibration, images), use the fast validation system:

```python
from dsa110_contimg.qa.fast_validation import ValidationMode, validate_pipeline_fast

# Fast mode (<30s) - Aggressive sampling, skip expensive checks
result = validate_pipeline_fast(
    ms_path="/path/to/ms",
    caltables=["/path/to/cal.kcal"],
    image_paths=["/path/to/image.fits"],
    mode=ValidationMode.FAST,
)

# Standard mode (<60s) - Balanced detail/speed
result = validate_pipeline_fast(
    ms_path="/path/to/ms",
    caltables=["/path/to/cal.kcal"],
    image_paths=["/path/to/image.fits"],
    mode=ValidationMode.STANDARD,
)

# Check results
print(f"Passed: {result.passed}")
print(f"Timing: {result.timing}")
print(f"Errors: {result.errors}")
print(f"Warnings: {result.warnings}")
```

**Validation Modes:**
- `ValidationMode.FAST`: <30s, 0.5% sampling, skip expensive checks
- `ValidationMode.STANDARD`: <60s, 1% sampling, balanced detail/speed
- `ValidationMode.COMPREHENSIVE`: <5min, 10% sampling, full validation

See [Fast Validation Implementation](../dev/qa_fast_validation_implementation.md) for details.

### Running Validation via API

The simplest way to run validation is through the API:

```bash
# Get HTML validation report
curl "http://localhost:8000/api/qa/images/{image_id}/validation-report.html?catalog=nvss"

# Run validation and get JSON results
curl -X POST "http://localhost:8000/api/qa/images/{image_id}/catalog-validation/run" \
  -H "Content-Type: application/json" \
  -d '{"catalog": "nvss", "validation_types": ["astrometry", "flux_scale", "source_counts"]}'
```

### Running Validation in Python

```python
from dsa110_contimg.qa.catalog_validation import (
    validate_astrometry,
    validate_flux_scale,
    validate_source_counts,
)
from dsa110_contimg.qa.config import get_default_config

# Get default configuration
config = get_default_config()

# Run astrometry validation
astrometry_result = validate_astrometry(
    image_path="/path/to/image.fits",
    catalog="nvss",
    config=config.astrometry,
)

# Run flux scale validation
flux_result = validate_flux_scale(
    image_path="/path/to/image.fits",
    catalog="nvss",
    config=config.flux_scale,
)

# Run source counts validation
completeness_result = validate_source_counts(
    image_path="/path/to/image.fits",
    catalog="nvss",
    config=config.source_counts,
)
```

### Using Custom Configuration

```python
from dsa110_contimg.qa.config import QAConfig, AstrometryConfig

# Create custom configuration
custom_config = QAConfig()
custom_config.astrometry.max_offset_arcsec = 2.0  # More lenient threshold
custom_config.astrometry.min_match_fraction = 0.7  # Lower match requirement

# Use custom config
result = validate_astrometry(
    image_path="image.fits",
    catalog="nvss",
    config=custom_config.astrometry,
)
```

## Validation Types

### 1. Astrometry Validation

Validates the positional accuracy of detected sources by comparing with reference catalogs.

**Metrics:**
- Mean RA/Dec offsets
- RMS offset
- Maximum offset
- Number of matched sources

**Configuration:**
```python
from dsa110_contimg.qa.config import AstrometryConfig

config = AstrometryConfig(
    max_offset_arcsec=1.0,      # Maximum acceptable offset
    max_rms_arcsec=0.5,          # Maximum RMS offset
    min_match_fraction=0.8,      # Minimum fraction of sources that must match
    match_radius_arcsec=2.0,     # Matching radius
)
```

**Example:**
```python
from dsa110_contimg.qa.catalog_validation import validate_astrometry
from dsa110_contimg.qa.config import get_default_config

# Use default config
result = validate_astrometry(
    image_path="image.fits",
    catalog="nvss",
    config=get_default_config().astrometry,
)

# Or override specific parameters
result = validate_astrometry(
    image_path="image.fits",
    catalog="nvss",
    search_radius_arcsec=10.0,  # Override config
    config=get_default_config().astrometry,
)

print(f"Mean offset: {result.mean_offset_ra*3600:.2f} arcsec RA, "
      f"{result.mean_offset_dec*3600:.2f} arcsec Dec")
print(f"RMS offset: {result.rms_offset_arcsec:.2f} arcsec")
```

### 2. Flux Scale Validation

Compares measured fluxes with reference catalog fluxes to assess calibration accuracy.

**Metrics:**
- Mean flux ratio (detected/catalog)
- RMS flux ratio
- Flux scale error percentage
- Number of matched sources

**Example:**
```python
from dsa110_contimg.qa.catalog_validation import validate_flux_scale
from dsa110_contimg.qa.config import get_default_config

result = validate_flux_scale(
    image_path="image.fits",
    catalog="nvss",
    config=get_default_config().flux_scale,
)

print(f"Mean flux ratio: {result.mean_flux_ratio:.3f}")
```

### 3. Source Counts Validation

Validates source detection completeness by comparing detected source counts with catalog.

**Example:**
```python
from dsa110_contimg.qa.catalog_validation import validate_source_counts
from dsa110_contimg.qa.config import get_default_config

result = validate_source_counts(
    image_path="image.fits",
    catalog="nvss",
    config=get_default_config().source_counts,
)

print(f"Completeness: {result.completeness:.1%}")
```

### 4. Photometry Validation (New)

Validates forced photometry accuracy and consistency across images.

**Example:**
```python
from dsa110_contimg.qa.photometry_validation import validate_forced_photometry
from dsa110_contimg.qa.config import get_default_config

result = validate_forced_photometry(
    image_path="image.fits",
    catalog_sources=catalog_sources,
    photometry_results=photometry_results,
    config=get_default_config().photometry,
)

print(f"Pass rate: {result.calculate_pass_rate():.1%}")
print(f"Mean flux error: {result.mean_flux_error_fraction:.3f}")
```

### 5. Variability/ESE Validation (New)

Validates variability detection and ESE (Extreme Scattering Event) candidate identification.

**Example:**
```python
from dsa110_contimg.qa.variability_validation import (
    validate_variability_detection,
    validate_ese_detection,
)
from dsa110_contimg.qa.config import get_default_config

# Validate single source variability
result = validate_variability_detection(
    source_id="source_001",
    photometry_history=photometry_history,
    config=get_default_config().variability,
)

# Validate ESE candidates
ese_result = validate_ese_detection(
    ese_candidates=ese_candidates,
    photometry_histories=photometry_histories,
    config=get_default_config().variability,
)
```

### 6. Mosaic Validation (New)

Validates mosaic image quality, overlap handling, and consistency.

**Example:**
```python
from dsa110_contimg.qa.mosaic_validation import validate_mosaic_quality
from dsa110_contimg.qa.config import get_default_config

result = validate_mosaic_quality(
    mosaic_path="mosaic.fits",
    tile_paths=["tile1.fits", "tile2.fits"],
    config=get_default_config().mosaic,
)

print(f"Seams detected: {result.n_seams_detected}/{result.n_overlaps}")
```

### 7. Streaming Validation (New)

Validates streaming pipeline continuity, latency, and data integrity.

**Example:**
```python
from dsa110_contimg.qa.streaming_validation import validate_streaming_continuity
from dsa110_contimg.qa.config import get_default_config
from datetime import datetime

result = validate_streaming_continuity(
    time_range_start=datetime(2025, 1, 1, 0, 0, 0),
    time_range_end=datetime(2025, 1, 1, 1, 0, 0),
    expected_files=expected_files,
    actual_files=actual_files,
    file_timestamps=file_timestamps,
    config=get_default_config().streaming,
)

print(f"Missing files: {result.n_missing_files}/{result.n_expected_files}")
print(f"Max latency: {result.max_latency_seconds:.1f}s")
```

### 8. Database Validation (New)

Validates database consistency, referential integrity, and data completeness.

**Example:**
```python
from dsa110_contimg.qa.database_validation import validate_database_consistency
from dsa110_contimg.qa.config import get_default_config

result = validate_database_consistency(
    db_path="products.sqlite3",
    expected_tables=["images", "photometry", "variability_stats"],
    file_registry=file_registry,
    config=get_default_config().database,
)

print(f"Orphaned records: {result.n_orphaned_records}")
print(f"Missing files: {result.n_missing_files}")
```

## Configuration System

All validators use a centralized configuration system. Default configurations are provided, but can be customized:

```python
from dsa110_contimg.qa.config import QAConfig, get_default_config

# Get default config
config = get_default_config()

# Customize specific thresholds
config.astrometry.max_offset_arcsec = 2.0
config.photometry.max_flux_error_fraction = 0.15
config.variability.min_chi_squared = 30.0

# Use in validations
result = validate_astrometry(..., config=config.astrometry)
```

## Error Handling

All validators use consistent error handling:

```python
from dsa110_contimg.qa.base import ValidationInputError, ValidationError

try:
    result = validate_astrometry(image_path="image.fits", ...)
except ValidationInputError as e:
    print(f"Invalid input: {e}")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Pipeline Integration

Validation is integrated into the pipeline via `pipeline_quality.py`:

```python
from dsa110_contimg.qa.pipeline_quality import (
    check_ms_after_conversion,
    check_calibration_quality,
    check_image_quality,
)
from dsa110_contimg.qa.config import get_default_config

config = get_default_config()

# Check MS quality
passed, metrics = check_ms_after_conversion(
    ms_path="data.ms",
    config=config,
)

# Check calibration quality
passed, results = check_calibration_quality(
    caltables=["K.cal", "BP.cal", "G.cal"],
    config=config,
)

# Check image quality
passed, metrics = check_image_quality(
    image_path="image.fits",
    config=config,
)
```

## See Also

- [Validation API Reference](../reference/validation_api.md)
- [QA System Implementation](../dev/qa_system_implementation_complete.md)
- [QA System Audit](../dev/analysis/qa_system_audit.md)
