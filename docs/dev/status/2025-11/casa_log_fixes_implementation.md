# CASA Log Handling Fixes - Implementation Summary

**Date**: 2025-11-16  
**Status**: Phase 2 Complete, Phase 1 Partial, Phase 3 Complete

## Phase 2: Module-Level Import Fixes ✅ COMPLETE

Moved all module-level CASA imports to function level to prevent CASA from being
imported before CWD can be set.

### Files Fixed:

1. **dsa110_contimg/beam/vp_builder.py**
   - Moved `coordsys`, `image`, `vpmanager` imports to function level
   - 3 functions updated

2. **dsa110_contimg/calibration/applycal.py**
   - Moved `applycal` import to function level
   - 1 function updated

3. **dsa110_contimg/calibration/flagging.py**
   - Moved `flagdata` import to function level
   - 15+ functions updated

4. **dsa110_contimg/utils/coordinates.py**
   - Moved `casatools` import to function level
   - 2 functions updated

5. **dsa110_contimg/utils/fringestopping.py**
   - Moved `casatools` import to function level
   - 2 functions updated

## Phase 1: API Routes Context Manager 🔄 PARTIAL

Added context manager to one critical route as example. Full implementation
would require updating all routes that use CASA.

### Files Updated:

1. **dsa110_contimg/api/routes.py**
   - Added `casa_log_environment()` context manager to `get_ms_metadata()` route
   - Other routes still need updates (3542, 3812, 4978)

### Remaining Routes:

- `get_ms_calibrator_matches()` - Line 3542
- `validate_caltable_compatibility()` - Line 3812
- `get_caltable_plot()` - Line 4978
- Routes in `visualization_routes.py`
- Routes in `batch_jobs.py`

## Phase 3: Cleanup ✅ COMPLETE

- Cleanup script created and tested
- Existing logs can be moved with: `python scripts/cleanup_casa_logs.py`

## Testing

After Phase 2 fixes:

1. CASA should not be imported at module level
2. CWD should be set before CASA imports in functions
3. New CASA logs should go to `/data/dsa110-contimg/state/logs/`

## Next Steps

1. **Monitor for new logs in root directory** - If Phase 2 fix is sufficient,
   Phase 1 may not be needed
2. **If logs still appear in root**: Complete Phase 1 by adding context manager
   to all API routes
3. **Run cleanup script periodically** to move any logs that still appear in
   root

## Impact

- **Root Cause Fixed**: Module-level imports no longer cause early CASA
  initialization
- **API Routes**: Partial fix - one route updated as example
- **CLI Scripts**: Should work correctly with `setup_casa_environment()` call
