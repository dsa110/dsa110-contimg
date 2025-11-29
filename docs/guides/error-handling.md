# Error Handling Guide

This document describes the error handling patterns used in the DSA-110
Continuum Imaging Pipeline.

## Overview

The pipeline uses a structured error handling approach with:

- **Custom exception hierarchy** for semantic clarity
- **Centralized logging** with structured output
- **Context propagation** for debugging
- **Recovery mechanisms** for transient failures

## Exception Hierarchy

All pipeline-specific exceptions inherit from `PipelineError`:

```
PipelineError (base)
├── SubbandGroupingError
│   └── IncompleteSubbandGroupError
├── ConversionError
│   ├── UVH5ReadError
│   └── MSWriteError
├── DatabaseError
│   ├── DatabaseMigrationError
│   ├── DatabaseConnectionError
│   └── DatabaseLockError
├── QueueError
│   └── QueueStateTransitionError
├── CalibrationError
│   ├── CalibrationTableNotFoundError
│   └── CalibratorNotFoundError
├── ImagingError
│   └── ImageNotFoundError
└── ValidationError
    ├── MissingParameterError
    └── InvalidPathError
```

## Using Custom Exceptions

### Basic Usage

```python
from dsa110_contimg.utils.exceptions import (
    ConversionError,
    UVH5ReadError,
)

# Raise with context
raise UVH5ReadError(
    file_path="/data/incoming/corrupt.hdf5",
    reason="Invalid magic number",
    group_id="2025-01-15T12:30:00",
)
```

### Wrapping Standard Exceptions

```python
from dsa110_contimg.utils.exceptions import wrap_exception, UVH5ReadError

try:
    h5py.File(path, 'r')
except OSError as e:
    raise wrap_exception(e, UVH5ReadError, file_path=path) from e
```

### Checking Recoverability

```python
from dsa110_contimg.utils.exceptions import is_recoverable

try:
    process_group(files)
except PipelineError as e:
    if is_recoverable(e):
        logger.warning(f"Recoverable error, continuing: {e}")
    else:
        logger.error(f"Fatal error: {e}")
        raise
```

## Logging Configuration

### Setup at Application Entry

```python
from dsa110_contimg.utils.logging_config import setup_logging

# Uses environment variables with defaults
setup_logging()

# Or explicit configuration
setup_logging(
    log_level="DEBUG",
    log_dir="/data/dsa110-contimg/state/logs",
    json_format=True,
)
```

### Environment Variables

| Variable                    | Default                         | Description           |
| --------------------------- | ------------------------------- | --------------------- |
| `PIPELINE_LOG_LEVEL`        | INFO                            | Logging level         |
| `PIPELINE_LOG_DIR`          | /data/dsa110-contimg/state/logs | Log directory         |
| `PIPELINE_LOG_FORMAT`       | text                            | Format (text or json) |
| `PIPELINE_LOG_MAX_SIZE`     | 50                              | Max file size in MB   |
| `PIPELINE_LOG_BACKUP_COUNT` | 10                              | Number of backups     |

### Log Files

| File              | Content                  |
| ----------------- | ------------------------ |
| `pipeline.log`    | All log messages         |
| `error.log`       | ERROR and above only     |
| `conversion.log`  | Conversion module logs   |
| `streaming.log`   | Streaming converter logs |
| `calibration.log` | Calibration module logs  |
| `imaging.log`     | Imaging module logs      |
| `api.log`         | API server logs          |
| `database.log`    | Database operation logs  |

## Context Propagation

### Using log_context

```python
from dsa110_contimg.utils.logging_config import log_context

with log_context(group_id="2025-01-15T12:30:00", pipeline_stage="conversion"):
    logger.info("Starting conversion")  # Includes context
    process_files()
    logger.info("Conversion complete")  # Same context
```

### Adding Extra Context to Logs

```python
logger.error(
    "Conversion failed",
    extra={
        "group_id": "2025-01-15T12:30:00",
        "file_path": "/data/incoming/obs.hdf5",
        "pipeline_stage": "conversion",
    }
)
```

### Logging Exceptions

```python
from dsa110_contimg.utils.logging_config import log_exception

try:
    process_file(path)
except ConversionError as e:
    log_exception(logger, e, custom_context="value")
    raise
```

## Error Handling Patterns

### Critical Operations

Wrap critical operations with try/except and log context:

```python
from dsa110_contimg.utils.exceptions import ConversionError
from dsa110_contimg.utils.logging_config import log_context, log_exception

def convert_group(group_id: str, files: list[str]) -> None:
    with log_context(group_id=group_id, pipeline_stage="conversion"):
        try:
            uvdata = load_subbands(files)
            write_ms(uvdata, output_path)
        except Exception as e:
            log_exception(logger, e)
            raise ConversionError(
                f"Failed to convert group: {e}",
                group_id=group_id,
                file_list=files,
                original_exception=e,
            ) from e
```

### Database Operations

```python
from dsa110_contimg.utils.exceptions import DatabaseError, DatabaseLockError

try:
    with get_session("products") as session:
        session.query(Image).all()
except OperationalError as e:
    if "database is locked" in str(e):
        raise DatabaseLockError("products", original_exception=e) from e
    raise DatabaseError(
        "Query failed",
        db_name="products",
        operation="query",
        original_exception=e,
    ) from e
```

### Streaming Queue State Updates

```python
from dsa110_contimg.utils.exceptions import QueueStateTransitionError

def update_state(group_id: str, from_state: str, to_state: str):
    if not is_valid_transition(from_state, to_state):
        raise QueueStateTransitionError(
            group_id=group_id,
            current_state=from_state,
            target_state=to_state,
            reason="Invalid state transition",
        )
```

### Graceful Degradation

For recoverable errors, log warning and continue:

```python
for group in groups:
    try:
        result = process_group(group)
        results["converted"].append(group.id)
    except IncompleteSubbandGroupError as e:
        logger.warning(str(e), extra=e.context)
        results["skipped"].append(group.id)
    except ConversionError as e:
        if is_recoverable(e):
            logger.error(str(e), extra=e.context)
            results["failed"].append({"id": group.id, "error": str(e)})
        else:
            raise
```

## Inspecting Logs

### View Recent Errors

```bash
tail -f /data/dsa110-contimg/state/logs/error.log
```

### Search for Specific Group

```bash
grep "group_id=2025-01-15T12:30:00" /data/dsa110-contimg/state/logs/pipeline.log
```

### Parse JSON Logs

```bash
# With jq
cat /data/dsa110-contimg/state/logs/pipeline.log | jq 'select(.level == "ERROR")'

# Filter by group
cat /data/dsa110-contimg/state/logs/pipeline.log | jq 'select(.group_id == "2025-01-15T12:30:00")'
```

### Check Queue Failures

```bash
sqlite3 /data/dsa110-contimg/state/ingest.sqlite3 \
  "SELECT group_id, error_type, error_message, retry_count
   FROM ingest_queue
   WHERE state = 'failed'
   ORDER BY completed_at DESC
   LIMIT 10;"
```

## Testing Error Paths

Unit tests for error handling are in `backend/tests/unit/`:

- `test_exceptions.py` - Exception class tests
- `test_logging_config.py` - Logging configuration tests
- `test_conversion_errors.py` - Conversion error handling tests

Run tests:

```bash
conda activate casa6
cd /data/dsa110-contimg/backend
python -m pytest tests/unit/test_exceptions.py -v
python -m pytest tests/unit/test_logging_config.py -v
python -m pytest tests/unit/test_conversion_errors.py -v
```

## Best Practices

1. **Always use custom exceptions** for pipeline-specific errors
2. **Include context** (group_id, file paths, stage) in every error
3. **Log at appropriate levels**: ERROR for failures, WARNING for recoverable
   issues
4. **Use log_context** for automatic context propagation
5. **Test error paths** with unit tests
6. **Check is_recoverable()** before deciding to halt or continue
7. **Record errors in database** for queue-based processing
8. **Review error logs** regularly for patterns

## See Also

- [DSA-110 Copilot Instructions](/.github/copilot-instructions.md)
- [Pipeline Architecture](../architecture/pipeline.md)
- [Streaming Converter](../operations/streaming.md)
