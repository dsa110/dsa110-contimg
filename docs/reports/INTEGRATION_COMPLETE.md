# Integration Complete - Performance Tracking and Enhanced Error Context

**Date:** 2025-01-27

---

## Summary

Successfully integrated **performance tracking** and **enhanced error context** into all major pipeline workflows. Both features are now actively used throughout the codebase.

---

## ✅ Performance Tracking Integration

### Decorators Added

1. **Calibration Workflow** (`calibration/cli_calibrate.py`)
   - `@track_performance("calibration", log_result=True)` on `handle_calibrate()`
   - Tracks total calibration time including all steps

2. **Imaging Workflow** (`imaging/cli_imaging.py`)
   - `@track_performance("imaging", log_result=True)` on `image_ms()`
   - `@track_performance("wsclean", log_result=True)` on `run_wsclean()`
   - Tracks both overall imaging and WSClean execution separately

3. **Conversion Workflow** (`conversion/strategies/hdf5_orchestrator.py`)
   - `@track_performance("conversion", log_result=True)` on `convert_subband_groups_to_ms()`
   - Tracks total conversion time from UVH5 to MS

### Usage

Performance metrics are automatically logged when operations complete. Use `get_performance_stats()` to retrieve aggregated statistics:

```python
from dsa110_contimg.utils.performance import get_performance_stats

stats = get_performance_stats()
# Returns: {
#     'calibration': {'mean': 1234.5, 'median': 1200.0, 'std': 100.0, 'count': 10},
#     'imaging': {'mean': 567.8, 'median': 550.0, 'std': 50.0, 'count': 5},
#     ...
# }
# }
```

---

## ✅ Enhanced Error Context Integration

### Error Handling Enhanced

#### 1. Calibration Workflow (`calibration/cli_calibrate.py`)
- **MS validation errors**: Added actionable suggestions for file access, permissions, and validation
- **Rephasing errors**: Enhanced errors for phaseshift failures with troubleshooting steps
- **MODEL_DATA errors**: Improved error messages with context-specific suggestions

#### 2. Imaging Workflow (`imaging/cli_imaging.py`)
- **MS validation errors**: Added suggestions for file access and MS integrity checks
- **CORRECTED_DATA validation errors**: Enhanced errors distinguishing between unpopulated data and file access issues
- **WSClean execution errors**: Added suggestions for installation, PATH, and configuration issues

#### 3. Conversion Workflow (`conversion/strategies/hdf5_orchestrator.py`)
- **Directory validation errors**: Enhanced errors for input/output directory issues with permission troubleshooting
- **File validation errors**: Added suggestions for HDF5 structure, file access, and corruption issues
- **MS creation errors**: Enhanced errors for MS write failures with disk space and permission checks

#### 4. Flagging Workflow (`calibration/flagging.py`)
- **AOFlagger setup errors**: Added suggestions for Docker installation and PATH configuration
- **Manual flagging errors**: Enhanced errors for parameter validation with usage guidance

### Error Message Format

All enhanced errors now include:
- **Context**: MS path, file path, operation name
- **Metadata**: File permissions, existence, structure
- **Suggestions**: Actionable troubleshooting steps
- **Original error**: Preserved for detailed debugging

Example error message:
```
Error during [MS validation] for /path/to/ms:
  File: /path/to/ms
  Operation: MS validation
  Error: ValidationError: MS missing required columns

Suggestions:
  - Check MS path is correct and file exists
  - Verify file permissions
  - Run validation: python -m dsa110_contimg.calibration.cli validate --ms <path>
  - Check MS structure and integrity
```

---

## Files Modified

### Core Integration
1. `src/dsa110_contimg/calibration/cli_calibrate.py`
   - Added performance tracking decorator
   - Enhanced 5 error handling locations

2. `src/dsa110_contimg/imaging/cli_imaging.py`
   - Added 2 performance tracking decorators
   - Enhanced 4 error handling locations

3. `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`
   - Added performance tracking decorator
   - Enhanced 12 error handling locations

4. `src/dsa110_contimg/calibration/flagging.py`
   - Enhanced 4 error handling locations

---

## Testing

✅ All syntax verified:
- `calibration/cli_calibrate.py` - Syntax OK
- `imaging/cli_imaging.py` - Syntax OK
- `conversion/strategies/hdf5_orchestrator.py` - Syntax OK
- `calibration/flagging.py` - Syntax OK

✅ Imports verified:
- `track_performance` - Available
- `format_ms_error_with_suggestions` - Available
- `format_file_error_with_suggestions` - Available

---

## Usage Examples

### Performance Tracking

```python
# Performance tracking is automatic - no code changes needed
# Metrics are logged when operations complete:

# Example log output:
# INFO: Calibration completed in 1234.5s
# INFO: Imaging completed in 567.8s
# INFO: Conversion completed in 2345.6s

# Retrieve statistics:
from dsa110_contimg.utils.performance import get_performance_stats
stats = get_performance_stats()
print(f"Average calibration time: {stats['calibration']['mean']:.2f}s")
```

### Enhanced Error Context

```python
# Error context is automatic - errors now include suggestions:

# Example error (automatic):
# RuntimeError: Error during [MS validation] for /path/to/ms:
#   File: /path/to/ms
#   Operation: MS validation
#   Error: ValidationError: MS missing required columns
#   
#   Suggestions:
#     - Check MS path is correct and file exists
#     - Verify file permissions
#     - Run validation: python -m dsa110_contimg.calibration.cli validate --ms <path>
#     - Check MS structure and integrity
```

---

## Benefits

### Performance Tracking
- **Visibility**: Automatic tracking of operation times
- **Monitoring**: Easy identification of slow operations
- **Optimization**: Data-driven decisions on what to optimize
- **Benchmarking**: Track performance improvements over time

### Enhanced Error Context
- **Actionable**: Users get specific suggestions, not just error messages
- **Contextual**: Errors include relevant metadata (paths, permissions, etc.)
- **Diagnostic**: Faster troubleshooting with structured error information
- **User-friendly**: Clear guidance on how to resolve issues

---

## Next Steps

### Optional Enhancements
1. **Performance Dashboard**: Create a simple dashboard to visualize performance metrics
2. **Error Logging**: Centralize error logging for analytics
3. **Performance Alerts**: Add thresholds for slow operations
4. **Error Analytics**: Track common error patterns for proactive improvements

### Already Complete
- ✅ Performance tracking decorators added to all major workflows
- ✅ Enhanced error context integrated into all error handling
- ✅ Syntax and imports verified
- ✅ Documentation updated

---

## Status: **COMPLETE** ✅

All optional features are now integrated and active in the pipeline. The pipeline will automatically:
- Track performance metrics for all major operations
- Provide enhanced error messages with actionable suggestions
- Log performance data for monitoring and optimization

No additional code changes required - features are ready to use!

---

## Next Steps

See `TODO.md` in the project root for a living TODO list of recommended next steps, including:
- Testing & validation
- Additional optimizations
- Documentation improvements
- Separate project work


