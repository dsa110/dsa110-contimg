# Configuration Reference

**Last Updated:** 2025-01-XX  
**Purpose:** Comprehensive reference for all configuration options and environment variables

---

## Overview

The DSA-110 Continuum Imaging Pipeline uses a unified configuration system based on Pydantic models. Configuration can be loaded from:
- Environment variables (primary method)
- Configuration files (YAML/JSON)
- Python dictionaries (for programmatic configuration)

**Single Source of Truth:** `src/dsa110_contimg/pipeline/config.py`

---

## Quick Start

### Basic Configuration

```python
from dsa110_contimg.pipeline.config import PipelineConfig

# Load from environment variables (with automatic path validation)
config = PipelineConfig.from_env()

# Load without path validation (for testing)
config = PipelineConfig.from_env(validate_paths=False)

# Load with custom disk space requirement
config = PipelineConfig.from_env(required_disk_gb=100.0)
```

---

## Environment Variables

### Required Variables

These must be set for the pipeline to function:

| Variable | Description | Example |
|----------|-------------|---------|
| `PIPELINE_INPUT_DIR` | Input directory for UVH5 files | `/data/incoming` |
| `PIPELINE_OUTPUT_DIR` | Output directory for MS files | `/data/ms` |

### Optional Path Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PIPELINE_SCRATCH_DIR` | Scratch directory for temporary files | `None` | `/stage/dsa110-contimg` |
| `PIPELINE_STATE_DIR` | State directory for databases | `"state"` | `/data/dsa110-contimg/state` |

**Note:** If `PIPELINE_STATE_DIR` is not set, databases are created in `state/` relative to the current working directory.

### Conversion Configuration

| Variable | Description | Default | Range | Example |
|----------|-------------|---------|-------|---------|
| `PIPELINE_WRITER` | Writer strategy | `"auto"` | `auto`, `parallel-subband`, `pyuvdata` | `parallel-subband` |
| `PIPELINE_MAX_WORKERS` | Maximum parallel workers | `4` | 1-32 | `16` |
| `PIPELINE_EXPECTED_SUBBANDS` | Expected number of subbands | `16` | 1-32 | `16` |
| `PIPELINE_STAGE_TO_TMPFS` | Stage files to tmpfs | `"true"` | `true`, `false` | `true` |

**Validation:**
- `PIPELINE_MAX_WORKERS` and `PIPELINE_EXPECTED_SUBBANDS` are validated to be integers between 1 and 32
- Invalid values raise `ValueError` with clear error messages

### Calibration Configuration

| Variable | Description | Default | Range | Example |
|----------|-------------|---------|-------|---------|
| `PIPELINE_CAL_BP_MINSNR` | Minimum SNR for bandpass calibration | `3.0` | 1.0-10.0 | `3.5` |
| `PIPELINE_CAL_GAIN_SOLINT` | Gain solution interval | `"inf"` | String | `"inf"`, `"60s"` |
| `PIPELINE_DEFAULT_REFANT` | Default reference antenna | `"103"` | String | `"103"` |
| `PIPELINE_AUTO_SELECT_REFANT` | Automatically select reference antenna | `"true"` | `true`, `false` | `true` |

**Validation:**
- `PIPELINE_CAL_BP_MINSNR` is validated to be a float between 1.0 and 10.0

### Imaging Configuration

| Variable | Description | Default | Range | Example |
|----------|-------------|---------|-------|---------|
| `PIPELINE_FIELD` | Field name or coordinates | `None` | String | `"3C286"` |
| `PIPELINE_REFANT` | Reference antenna | `"103"` | String | `"103"` |
| `PIPELINE_GRIDDER` | Gridding algorithm | `"wproject"` | String | `"wproject"`, `"standard"` |
| `PIPELINE_WPROJPLANES` | W-projection planes (-1 for auto) | `"-1"` | Integer | `-1`, `128` |
| `PIPELINE_USE_NVSS_MASK` | Use NVSS-based mask for imaging | `"true"` | `true`, `false` | `true` |
| `PIPELINE_MASK_RADIUS_ARCSEC` | Mask radius around NVSS sources | `"60.0"` | 10.0-300.0 | `60.0`, `120.0` |

**Notes:**
- `PIPELINE_WPROJPLANES` is validated as an integer but has no range restrictions (negative values are valid for auto mode).
- `PIPELINE_USE_NVSS_MASK`: Masking provides 2-4x faster imaging by restricting cleaning to known source locations. Enabled by default for efficiency.
- `PIPELINE_MASK_RADIUS_ARCSEC`: Radius around each NVSS source in arcseconds. Default (60.0) is approximately 2-3× the beam size. Validated to be between 10.0 and 300.0 arcseconds.

---

## API Configuration

The API layer uses separate configuration (`ApiConfig`) with these environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PIPELINE_STATE_DIR` | Base state directory | `"state"` | `/data/dsa110-contimg/state` |
| `CAL_REGISTRY_DB` | Calibration registry database path | `{PIPELINE_STATE_DIR}/cal_registry.sqlite3` | `/data/state/cal_registry.sqlite3` |
| `PIPELINE_QUEUE_DB` | Queue database path | `{PIPELINE_STATE_DIR}/ingest.sqlite3` | `/data/state/ingest.sqlite3` |
| `PIPELINE_PRODUCTS_DB` | Products database path | `{PIPELINE_STATE_DIR}/products.sqlite3` | `/data/state/products.sqlite3` |
| `PIPELINE_EXPECTED_SUBBANDS` | Expected subbands (for API) | `16` | `16` |

**Validation:**
- `PIPELINE_EXPECTED_SUBBANDS` is validated to be an integer between 1 and 32

---

## Streaming Service Configuration

The streaming service uses these environment variables (with `CONTIMG_` prefix):

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `CONTIMG_INPUT_DIR` | Input directory | `/data/incoming` | `/data/incoming` |
| `CONTIMG_OUTPUT_DIR` | Output directory | `/stage/dsa110-contimg/ms` | `/data/ms` |
| `CONTIMG_QUEUE_DB` | Queue database | `state/ingest.sqlite3` | `/data/state/ingest.sqlite3` |
| `CONTIMG_REGISTRY_DB` | Registry database | `state/cal_registry.sqlite3` | `/data/state/cal_registry.sqlite3` |
| `CONTIMG_SCRATCH_DIR` | Scratch directory | `/stage/dsa110-contimg` | `/stage/dsa110-contimg` |
| `CONTIMG_EXPECTED_SUBBANDS` | Expected subbands | `16` | `16` |
| `CONTIMG_CHUNK_MINUTES` | Chunk duration (minutes) | `5.0` | `5.0` |
| `CONTIMG_LOG_LEVEL` | Log level | `INFO` | `INFO`, `DEBUG` |
| `CONTIMG_MONITOR_INTERVAL` | Monitor interval (seconds) | `60.0` | `60.0` |

**Validation:**
- `CONTIMG_EXPECTED_SUBBANDS`: Integer between 1 and 32
- `CONTIMG_CHUNK_MINUTES`: Float >= 0.1
- `CONTIMG_MONITOR_INTERVAL`: Float >= 1.0

---

## System Environment Variables

These are used by underlying libraries and tools:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `OMP_NUM_THREADS` | OpenMP thread count | `1` | `4` |
| `MKL_NUM_THREADS` | MKL thread count | `1` | `4` |
| `HDF5_USE_FILE_LOCKING` | HDF5 file locking | `FALSE` | `FALSE` |
| `TMPDIR` | Temporary directory | System default | `/scratch/tmp` |
| `CASA_TMPDIR` | CASA temporary directory | `TMPDIR` | `/scratch/tmp` |
| `PIPELINE_TELESCOPE_NAME` | Telescope name | `DSA_110` | `DSA_110` |

**Important:** Set `HDF5_USE_FILE_LOCKING=FALSE` to prevent file locking issues in parallel operations.

---

## Path Validation

By default, `PipelineConfig.from_env()` validates paths at load time:

- Input directory exists and is readable
- Output directory parent is writable
- Scratch directory (if specified) is writable
- State directory can be created
- Databases are accessible
- Sufficient disk space available (default: 50 GB)

**Disable validation:**
```python
config = PipelineConfig.from_env(validate_paths=False)
```

**Custom disk space requirement:**
```python
config = PipelineConfig.from_env(required_disk_gb=100.0)
```

**Validation Errors:**
- Raises `HealthCheckError` if validation fails
- Error message includes all issues found
- Example: `"Pipeline health check failed:\n  - Input directory does not exist: /data/incoming"`

---

## Configuration Classes

### PipelineConfig

Main configuration class containing all pipeline settings.

**Properties:**
- `paths: PathsConfig` - Path configuration
- `conversion: ConversionConfig` - Conversion settings
- `calibration: CalibrationConfig` - Calibration settings
- `imaging: ImagingConfig` - Imaging settings

**Methods:**
- `from_env(validate_paths=True, required_disk_gb=50.0)` - Load from environment
- `from_dict(data)` - Load from dictionary
- `to_dict()` - Convert to dictionary

### PathsConfig

Path configuration with computed database paths.

**Properties:**
- `input_dir: Path` - Input directory (required)
- `output_dir: Path` - Output directory (required)
- `scratch_dir: Optional[Path]` - Scratch directory (optional)
- `state_dir: Path` - State directory (default: `"state"`)

**Computed Properties:**
- `products_db: Path` - `{state_dir}/products.sqlite3`
- `registry_db: Path` - `{state_dir}/cal_registry.sqlite3`
- `queue_db: Path` - `{state_dir}/ingest.sqlite3`

### ConversionConfig

Conversion stage configuration.

**Properties:**
- `writer: str` - Writer strategy (default: `"auto"`)
- `max_workers: int` - Max workers (default: 16, range: 1-32)
- `stage_to_tmpfs: bool` - Use tmpfs staging (default: True)
- `expected_subbands: int` - Expected subbands (default: 16, range: 1-32)
- `skip_validation_during_conversion: bool` - Skip validation (default: True)
- `skip_calibration_recommendations: bool` - Skip recommendations (default: True)

### CalibrationConfig

Calibration stage configuration.

**Properties:**
- `cal_bp_minsnr: float` - BP minimum SNR (default: 3.0, range: 1.0-10.0)
- `cal_gain_solint: str` - Gain solution interval (default: `"inf"`)
- `default_refant: str` - Default reference antenna (default: `"103"`)
- `auto_select_refant: bool` - Auto-select reference antenna (default: True)

### ImagingConfig

Imaging stage configuration.

**Properties:**
- `field: Optional[str]` - Field name/coordinates (default: None)
- `refant: str` - Reference antenna (default: `"103"`)
- `gridder: str` - Gridding algorithm (default: `"wproject"`)
- `wprojplanes: int` - W-projection planes (default: -1, -1 = auto)
- `run_catalog_validation: bool` - Run catalog validation (default: True)
- `catalog_validation_catalog: str` - Catalog for validation (default: `"nvss"`)

---

## Default Values Summary

### Paths
- `PIPELINE_STATE_DIR`: `"state"` (relative to current directory)

### Conversion
- `PIPELINE_WRITER`: `"auto"`
- `PIPELINE_MAX_WORKERS`: `4`
- `PIPELINE_EXPECTED_SUBBANDS`: `16`
- `PIPELINE_STAGE_TO_TMPFS`: `true`

### Calibration
- `PIPELINE_CAL_BP_MINSNR`: `3.0`
- `PIPELINE_CAL_GAIN_SOLINT`: `"inf"`
- `PIPELINE_DEFAULT_REFANT`: `"103"`
- `PIPELINE_AUTO_SELECT_REFANT`: `true`

### Imaging
- `PIPELINE_REFANT`: `"103"`
- `PIPELINE_GRIDDER`: `"wproject"`
- `PIPELINE_WPROJPLANES`: `-1` (auto)
- `run_catalog_validation`: `true`
- `catalog_validation_catalog`: `"nvss"`

---

## Validation and Error Messages

### Type Validation

Invalid types raise `ValueError` with clear messages:

```python
# Invalid integer
ValueError: Invalid integer value for PIPELINE_MAX_WORKERS: 'abc'. 
Expected integer between 1 and 32.

# Out of range
ValueError: PIPELINE_MAX_WORKERS=50 is above maximum 32

# Invalid float
ValueError: Invalid float value for PIPELINE_CAL_BP_MINSNR: 'invalid'. 
Expected float between 1.0 and 10.0.
```

### Path Validation

Path validation errors raise `HealthCheckError`:

```python
from dsa110_contimg.pipeline.health import HealthCheckError

try:
    config = PipelineConfig.from_env()
except HealthCheckError as e:
    print(e)  # Lists all validation failures
```

---

## Examples

### Basic Usage

```python
from dsa110_contimg.pipeline.config import PipelineConfig

# Load with defaults and validation
config = PipelineConfig.from_env()

# Access configuration
print(config.paths.input_dir)
print(config.conversion.max_workers)
print(config.calibration.cal_bp_minsnr)
```

### Custom Configuration

```python
from dsa110_contimg.pipeline.config import PipelineConfig

# Load from dictionary
config = PipelineConfig.from_dict({
    "paths": {
        "input_dir": "/custom/input",
        "output_dir": "/custom/output",
    },
    "conversion": {
        "max_workers": 8,
        "expected_subbands": 16,
    },
})
```

### API Configuration

```python
from dsa110_contimg.api.config import ApiConfig

# Load API configuration
api_config = ApiConfig.from_env()

# Access database paths
print(api_config.registry_db)
print(api_config.queue_db)
print(api_config.products_db)
```

---

## Related Documentation

- **Environment Variables Reference**: `docs/reference/env.md`
- **Pipeline Health Checks**: `src/dsa110_contimg/pipeline/health.py`
- **Configuration Source**: `src/dsa110_contimg/pipeline/config.py`
- **API Configuration**: `src/dsa110_contimg/api/config.py`

---

**Last Updated:** 2025-01-XX  
**Maintained By:** Pipeline Development Team

