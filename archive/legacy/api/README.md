# Legacy Job Runner Archive

**Purpose:** Archive legacy subprocess-based job execution functions.

**Status:** Archived on 2025-11-06

**Replacement:** New pipeline framework in `src/dsa110_contimg/pipeline/`

## What's Here

This directory contains the legacy implementations of:
- `run_workflow_job()` - Legacy subprocess-based workflow execution
- `run_convert_job()` - Legacy subprocess-based conversion
- `run_calibrate_job()` - Legacy subprocess-based calibration
- `run_image_job()` - Legacy subprocess-based imaging
- `run_apply_job()` - Legacy subprocess-based calibration application
- `run_batch_*_job()` - Legacy batch job functions

## Why Archived

These functions used subprocess-based execution which:
- Had subprocess overhead
- Made error handling difficult
- Lacked retry policies
- Had limited observability

## Replacement

All functions now delegate to the new pipeline framework:
- Direct function calls (no subprocess overhead)
- Dependency resolution
- Retry policies
- Structured logging and metrics
- Better error handling

## Using Legacy Code

If you need to reference the legacy implementations:

```python
# Import from archive
from archive.legacy.api.job_runner_legacy import run_workflow_job as legacy_workflow

# Use legacy implementation
legacy_workflow(job_id, params, products_db)
```

**Note:** Legacy code is preserved for reference only. New code should use the pipeline framework.

## Migration

See `docs/migration/LEGACY_DEPRECATION_PLAN.md` for migration details.

