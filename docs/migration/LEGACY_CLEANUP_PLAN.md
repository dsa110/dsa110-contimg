# Legacy Code Cleanup Plan

## Goal
Remove all legacy subprocess-based code from `/src/dsa110_contimg/` and archive it to `/archive/legacy/api/` for clarity and maintainability.

## Current State

**Legacy Functions in `api/job_runner.py`:**
- `run_workflow_job()` - ✅ Already has new implementation via `LegacyWorkflowAdapter`
- `run_convert_job()` - ⚠️ Called from API routes, needs new implementation
- `run_calibrate_job()` - ⚠️ Called from API routes, needs new implementation  
- `run_image_job()` - ⚠️ Called from API routes, needs new implementation
- `run_apply_job()` - ⚠️ Called from API routes, needs new implementation
- `run_batch_*_job()` - ⚠️ Called from API routes, needs new implementation

## Migration Strategy

### Phase 1: Create Individual Stage Adapters

Create adapters for each job type that use the new pipeline framework:

1. **`run_convert_job`** → Use `ConversionStage` directly
2. **`run_image_job`** → Use `ImagingStage` directly  
3. **`run_apply_job`** → Use `CalibrationStage` (applying tables)
4. **`run_calibrate_job`** → Create new `CalibrationSolveStage` (solving tables)
5. **`run_batch_*_job`** → Create batch workflow using new pipeline

### Phase 2: Archive Legacy Code

1. Copy legacy implementations to `archive/legacy/api/job_runner_legacy.py`
2. Remove legacy code from `src/dsa110_contimg/api/job_runner.py`
3. Replace with thin wrappers that use new pipeline

### Phase 3: Update Imports

All imports remain the same - functions still exist in `api/job_runner.py`, they just use new pipeline internally.

## Implementation Steps

1. ✅ Create archive directory structure
2. ⏳ Create `CalibrationSolveStage` for solving calibration tables
3. ⏳ Create individual job adapters using new pipeline stages
4. ⏳ Test all API endpoints work with new implementations
5. ⏳ Copy legacy code to archive
6. ⏳ Remove legacy code from src
7. ⏳ Update documentation

## Benefits

- **Clean codebase**: No deprecated code mixed with active code
- **Clear intent**: All code in `src/` is the current implementation
- **Preserved history**: Legacy code archived, not deleted
- **Easy reference**: Can still import from archive if needed
- **No breaking changes**: API interface remains the same

