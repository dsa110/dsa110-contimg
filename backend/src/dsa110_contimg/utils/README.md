# DSA-110 Pipeline Utilities

This module provides shared utilities for the DSA-110 Continuum Imaging Pipeline.

## Modules

### `exceptions.py` - Custom Exception Classes

Pipeline-specific exceptions for structured error handling:

```python
from dsa110_contimg.utils.exceptions import (
    # Base exception
    PipelineError,
    
    # Subband grouping errors
    SubbandGroupingError,
    IncompleteSubbandGroupError,
    
    # Conversion errors
    ConversionError,
    UVH5ReadError,
    MSWriteError,
    
    # Database errors
    DatabaseError,
    DatabaseMigrationError,
    DatabaseConnectionError,
    DatabaseLockError,
    
    # Queue errors
    QueueError,
    QueueStateTransitionError,
    
    # Calibration errors
    CalibrationError,
    CalibrationTableNotFoundError,
    CalibratorNotFoundError,
    
    # Imaging errors
    ImagingError,
    ImageNotFoundError,
    
    # Validation errors
    ValidationError,
    MissingParameterError,
    InvalidPathError,
    
    # Helpers
    wrap_exception,
    is_recoverable,
)

# Raise with context
raise ConversionError(
    "Conversion failed",
    group_id="2025-01-15T12:30:00",
    input_path="/data/incoming/obs.hdf5",
)

# Check if error is recoverable
if is_recoverable(error):
    logger.warning(f"Continuing after: {error}")
else:
    raise
```

### `logging_config.py` - Centralized Logging

Structured logging with context propagation:

```python
from dsa110_contimg.utils.logging_config import (
    setup_logging,
    log_context,
    get_logger,
    log_exception,
)

# Setup at application startup
setup_logging(log_level="INFO", json_format=True)

# Get a logger
logger = get_logger(__name__, pipeline_stage="conversion")

# Log with automatic context injection
with log_context(group_id="2025-01-15T12:30:00"):
    logger.info("Processing started")
    # ...
    logger.info("Processing complete")

# Log exceptions with full context
try:
    process_data()
except ConversionError as e:
    log_exception(logger, e)
    raise
```

### `constants.py` - Pipeline Constants

DSA-110 telescope parameters and coordinates:

```python
from dsa110_contimg.utils.constants import (
    DSA110_LOCATION,    # astropy EarthLocation
    DSA110_LATITUDE,    # degrees
    DSA110_LONGITUDE,   # degrees
    DSA110_LAT,         # radians
    DSA110_LON,         # radians
    DSA110_ALT,         # meters
)
```

### `antpos_local/` - Antenna Positions

Utilities for reading DSA-110 antenna positions:

```python
from dsa110_contimg.utils.antpos_local import get_itrf

# Get ITRF coordinates for all antennas
df = get_itrf()  # DataFrame with x_m, y_m, z_m columns
```

## Convenient Imports

Common utilities are re-exported from `dsa110_contimg.utils`:

```python
from dsa110_contimg.utils import (
    # Exceptions
    PipelineError,
    ConversionError,
    DatabaseError,
    # ...
    
    # Logging
    setup_logging,
    log_context,
    get_logger,
    log_exception,
    
    # Constants
    DSA110_LOCATION,
    DSA110_LATITUDE,
    DSA110_LONGITUDE,
)
```

## Environment Variables

The logging system respects these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_LOG_LEVEL` | INFO | Logging level |
| `PIPELINE_LOG_DIR` | /data/dsa110-contimg/state/logs | Log directory |
| `PIPELINE_LOG_FORMAT` | text | Format (text/json) |
| `PIPELINE_LOG_MAX_SIZE` | 50 | Max file size in MB |
| `PIPELINE_LOG_BACKUP_COUNT` | 10 | Backup file count |

## See Also

- [Error Handling Guide](../../../../docs/guides/error-handling.md)
- [Pipeline Architecture](../../../../docs/architecture/pipeline.md)
