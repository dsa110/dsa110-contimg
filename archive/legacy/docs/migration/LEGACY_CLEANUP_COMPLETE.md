# Legacy Code Cleanup - Complete ✅

**Date:** 2025-11-06  
**Status:** Complete

## Summary

All legacy subprocess-based job execution code has been removed from `/src/dsa110_contimg/` and archived to `/archive/legacy/api/job_runner_legacy.py`. The codebase now uses only the new pipeline framework for all job execution.

## What Changed

### Removed from `src/`
- All subprocess-based job functions (`run_convert_job`, `run_calibrate_job`, `run_apply_job`, `run_image_job`, `run_batch_*_job`)
- Legacy workflow implementation in `run_workflow_job`
- Helper functions for subprocess management (`_python_cmd_for_jobs`, `_src_path_for_env`)

### Added to `src/`
- `api/job_adapters.py`: Clean implementations using new pipeline framework
- `pipeline/stages_impl.py`: Added `CalibrationSolveStage` for solving calibration tables
- `api/job_runner.py`: Now imports from adapters (thin wrapper layer)

### Archived
- `archive/legacy/api/job_runner_legacy.py`: Complete legacy implementation preserved for reference

## Benefits

1. **Clean Codebase**: No deprecated code mixed with active code
2. **Clear Intent**: All code in `src/` is the current implementation
3. **Better Performance**: Direct function calls instead of subprocess overhead
4. **Preserved History**: Legacy code archived, not deleted
5. **No Breaking Changes**: API interface remains the same

## Migration Notes

- All existing API endpoints continue to work without changes
- Function signatures remain identical
- Internal implementation now uses new pipeline framework
- Legacy code available in archive for reference if needed

## Testing

All job functions have been tested and verified to work with the new pipeline framework:
- ✅ `run_convert_job` - Uses `ConversionStage`
- ✅ `run_calibrate_job` - Uses `CalibrationSolveStage`
- ✅ `run_apply_job` - Uses `CalibrationStage`
- ✅ `run_image_job` - Uses `ImagingStage`
- ✅ `run_workflow_job` - Uses `LegacyWorkflowAdapter`
- ✅ `run_batch_*_job` - Uses individual job adapters

## Next Steps

- Monitor production usage for any issues
- Consider removing archive after sufficient confidence period (6+ months)
- Continue improving new pipeline framework based on feedback

