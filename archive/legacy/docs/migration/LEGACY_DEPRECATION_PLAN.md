# Legacy Code Deprecation Plan

## Overview

This document outlines the plan for migrating from legacy subprocess-based pipeline execution to the new pipeline framework, and eventually archiving the legacy code.

## Current State

- **New Pipeline**: Fully implemented, tested, and ready for production
- **Legacy Pipeline**: Still functional, controlled by `USE_NEW_PIPELINE` environment variable
- **Default**: Currently legacy (opt-in for new pipeline)

## Migration Strategy

### Phase 1: Make New Pipeline Default (Immediate)

1. **Flip the default** in `api/job_runner.py`:
   - Change `USE_NEW_PIPELINE` default from `"false"` to `"true"`
   - Legacy code remains available via `USE_LEGACY_PIPELINE=true`

2. **Add deprecation warnings** to legacy functions:
   - `run_workflow_job()` (legacy path)
   - `run_convert_job()`
   - `run_calibrate_job()`
   - `run_image_job()`

3. **Update documentation**:
   - README.md: Document new default
   - API docs: Note deprecation timeline
   - Developer guide: Migration instructions

### Phase 2: Transition Period (3-6 months)

**Keep legacy code in place** with:
- Clear deprecation warnings
- Full functionality maintained
- Easy rollback via `USE_LEGACY_PIPELINE=true`

**Monitor**:
- Error rates
- Performance metrics
- User feedback
- Any issues requiring rollback

### Phase 3: Archive Legacy Code (After 6+ months)

Once confident in new pipeline:
1. Move legacy functions to `archive/legacy/api/job_runner_legacy.py`
2. Create compatibility shim that imports from archive
3. Update all imports
4. Document archive location

## Implementation

### Step 1: Add Deprecation Warnings

```python
import warnings

def run_workflow_job(job_id: int, params: dict, products_db: Path):
    """Run full pipeline workflow: Convert → Calibrate → Image.
    
    .. deprecated:: 2025-11
        This function is deprecated. Use the new pipeline framework instead.
        Set USE_LEGACY_PIPELINE=true to continue using legacy behavior.
        Legacy code will be removed in a future release.
    """
    import os
    
    use_legacy = os.getenv("USE_LEGACY_PIPELINE", "false").lower() == "true"
    use_new = os.getenv("USE_NEW_PIPELINE", "true").lower() == "true"
    
    if not use_legacy and use_new:
        # New pipeline (default)
        from dsa110_contimg.pipeline.adapter import LegacyWorkflowAdapter
        adapter = LegacyWorkflowAdapter(products_db)
        adapter.run_workflow_job(job_id, params)
        return
    
    # Legacy path with deprecation warning
    warnings.warn(
        "Legacy pipeline execution is deprecated. "
        "Use new pipeline framework (default) or set USE_LEGACY_PIPELINE=true to suppress this warning. "
        "Legacy code will be removed in a future release.",
        DeprecationWarning,
        stacklevel=2
    )
    # ... rest of legacy code
```

### Step 2: Create Archive Structure

```
archive/legacy/
├── api/
│   ├── __init__.py
│   └── job_runner_legacy.py  # Moved legacy functions
├── README.md                  # Documentation
└── MIGRATION_GUIDE.md         # How to use legacy if needed
```

### Step 3: Compatibility Shim (Future)

```python
# api/job_runner.py (after archiving)
"""Legacy compatibility shim.

Legacy functions have been moved to archive/legacy/api/job_runner_legacy.py.
Import from there if needed, but prefer using the new pipeline framework.
"""

import warnings
from pathlib import Path

def run_workflow_job(job_id: int, params: dict, products_db: Path):
    """Legacy function - see archive/legacy/api/job_runner_legacy.py"""
    warnings.warn(
        "Legacy pipeline functions have been archived. "
        "Import from archive/legacy/api/job_runner_legacy if needed.",
        DeprecationWarning,
        stacklevel=2
    )
    from archive.legacy.api.job_runner_legacy import run_workflow_job as _legacy
    return _legacy(job_id, params, products_db)
```

## Rollback Plan

If issues arise:
1. Set `USE_LEGACY_PIPELINE=true` (or `USE_NEW_PIPELINE=false`)
2. Legacy code remains fully functional
3. Report issues for new pipeline fixes
4. Re-enable new pipeline after fixes

## Timeline

- **Week 1**: Flip default, add deprecation warnings
- **Months 1-6**: Monitor, gather feedback, fix issues
- **Month 6+**: Archive legacy code if confidence is high

## Benefits of This Approach

1. **Low Risk**: Legacy code remains available for rollback
2. **Clear Communication**: Deprecation warnings inform users
3. **Gradual Migration**: Users can adapt at their own pace
4. **Preserves History**: Code archived, not deleted
5. **Standard Practice**: Follows Python deprecation conventions

