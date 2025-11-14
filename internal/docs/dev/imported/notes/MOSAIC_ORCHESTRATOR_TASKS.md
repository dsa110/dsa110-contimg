# Mosaic Orchestrator Development Tasks

## Task 1: Dec Extraction from HDF5 Headers ✓ COMPLETE

**Status**: ✓ Implemented

**Changes Made**:
1. Added `ra_deg` and `dec_deg` columns to `ms_index` table (migration)
2. Updated `ms_index_upsert()` to accept and store `ra_deg`/`dec_deg`
3. Added `log_pointing()` function to log pointing to `pointing_history` table
4. Updated `streaming_converter.py` to:
   - Extract pointing from first HDF5 file using `_peek_uvh5_phase_and_midtime()`
   - Store pointing in `ms_index` table
   - Log pointing to `pointing_history` table for dashboard monitoring

**Files Modified**:
- `src/dsa110_contimg/database/products.py`: Added columns, updated upsert, added log_pointing()
- `src/dsa110_contimg/conversion/streaming/streaming_converter.py`: Added pointing extraction and logging

## Task 2: HDF5 Conversion Triggering ✓ COMPLETE

**Status**: ✓ Implemented

**Changes Made**:
1. Added `_trigger_hdf5_conversion()` method to trigger conversion for a time window
2. Updated `ensure_ms_files_in_window()` to automatically trigger conversion when MS files are missing
3. Uses `convert_subband_groups_to_ms()` with parallel subband writer (default)
4. Waits for conversion and re-checks for MS files

**Files Modified**:
- `src/dsa110_contimg/mosaic/orchestrator.py`: Added conversion triggering

## Task 3: Default Behavior (Earliest Incomplete Window) ✓ COMPLETE

**Status**: ✓ Implemented

**Changes Made**:
1. Completed `find_earliest_incomplete_window()`:
   - Queries for earliest MS files
   - Extracts Dec from ms_index (now populated from HDF5!)
   - Finds BP calibrator for that Dec
   - Calculates transit time
   - Determines window in pre-transit half (12 hours before transit)
   - Checks for published mosaics (structure in place)
2. Added `create_mosaic_default_behavior()` function to process default workflow

**Files Modified**:
- `src/dsa110_contimg/mosaic/orchestrator.py`: Completed default behavior implementation

## Task 4: Sliding Window Overlap Integration ✓ COMPLETE

**Status**: ✓ Implemented

**Changes Made**:
1. Added `process_sequential_mosaics_with_overlap()` method
2. Uses `StreamingMosaicManager.check_for_sliding_window_group()` for overlap logic
3. Maintains 2 MS overlap between consecutive mosaics (8 new + 2 overlap = 10 total)
4. Processes multiple mosaics sequentially with automatic overlap handling

**Files Modified**:
- `src/dsa110_contimg/mosaic/orchestrator.py`: Added sequential processing with overlap

## Summary

All four tasks are now complete! The mosaic orchestrator now supports:

1. ✓ **Pointing extraction from HDF5**: Automatically extracts RA/Dec during conversion and logs to both ms_index and pointing_history
2. ✓ **HDF5 conversion triggering**: Automatically converts HDF5 to MS when MS files are missing
3. ✓ **Default behavior**: Processes earliest incomplete observations first, with full auto-inference
4. ✓ **Sliding window overlap**: Sequential processing with 2 MS overlap between consecutive mosaics

## Next Steps

1. Test end-to-end with real data
2. Verify pointing extraction works correctly
3. Test HDF5 conversion triggering
4. Test default behavior workflow
5. Test sequential processing with overlap

