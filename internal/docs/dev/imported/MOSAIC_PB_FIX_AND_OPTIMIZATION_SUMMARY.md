# Mosaic PB Correction Fix and PNG Optimization - Summary

## Date: 2025-11-10

## Overview

This document summarizes the fixes and optimizations applied to the DSA-110 mosaic pipeline:
1. Primary Beam (PB) correction fix
2. FITS-to-PNG conversion optimization
3. End-to-end testing verification

## 1. Primary Beam Correction Fix

### Problem
Mosaics showed semi-circular patterns at tile edges, indicating incorrect PB correction. The `-pb.fits` files were not actually PB-corrected, but the code was telling `linearmosaic` they were (`imageweighttype=1`).

### Solution
- Changed `imageweighttype=0` in `_build_weighted_mosaic_linearmosaic()`
- Created `_build_weighted_mosaic()` wrapper function
- Updated both manual and streaming modes to use the wrapper
- Changed default `pbcor_only=False` to fetch uncorrected images

### Files Modified
- `src/dsa110_contimg/mosaic/cli.py`
- `src/dsa110_contimg/mosaic/streaming_mosaic.py`

### Verification
- ✓ Visual comparison confirmed artifacts resolved
- ✓ Code verification: `imageweighttype=0` set correctly
- ✓ Both modes use wrapper function
- ✓ End-to-end test passed

## 2. FITS-to-PNG Optimization

### Problem
Large mosaic images (102M pixels) took 60+ seconds or timed out during PNG conversion due to:
- Loading entire 388+ MB files into memory
- Computing percentiles on 100M+ pixels
- Rendering extremely large images

### Solution
- Changed `memmap=False` → `memmap=True` (memory mapping)
- Added automatic downsampling for arrays > 10M pixels
- Block averaging for efficient downsampling

### Performance
- **Before**: 60+ seconds or timeout
- **After**: ~21 seconds
- **Speedup**: ~3x faster

### Files Modified
- `src/dsa110_contimg/imaging/export.py`

## 3. Automatic PNG Visualization Generation

### Feature
Added automatic PNG visualization generation to the streaming mosaic pipeline. When a mosaic is created, a low-resolution PNG (optimized, ~21 seconds) is automatically generated alongside the mosaic.

### Implementation
- Integrated into `create_mosaic()` in `streaming_mosaic.py`
- Uses optimized `save_png_from_fits()` function
- Handles both FITS and CASA image formats
- Non-blocking: PNG generation failures don't fail mosaic creation

### Files Modified
- `src/dsa110_contimg/mosaic/streaming_mosaic.py`

## 4. End-to-End Testing

### Test Script
Created `scripts/test_streaming_mosaic_e2e.py` to verify:
1. PB correction fix is in place
2. Streaming mode uses correct wrapper
3. Mosaic builds successfully
4. Output files are created
5. PNG visualization is auto-generated

### Test Results
```
PB Correction Verification: ✓ PASSED
End-to-End Mosaic Build: ✓ PASSED
```

### Test Output
- Mosaic: `/stage/dsa110-contimg/tmp/streaming_mosaic_e2e_test/streaming_mosaic_e2e.image`
- Build time: ~7 minutes for 3 tiles
- All tiles regridded successfully
- Mosaic created with correct coordinate system

## Documentation

### New Documentation Files
1. `docs/dev/MOSAIC_PB_CORRECTION_FIX.md` - PB correction fix details
2. `docs/dev/FITS_TO_PNG_OPTIMIZATION.md` - PNG optimization details
3. `docs/dev/MOSAIC_PB_FIX_AND_OPTIMIZATION_SUMMARY.md` - This summary

### Updated Documentation
1. `docs/reference/LINEARMOSAIC_PARAMETERS.md` - Added DSA-110 pipeline default note

## Related Files

### Code
- `src/dsa110_contimg/mosaic/cli.py` - Mosaic building logic
- `src/dsa110_contimg/mosaic/streaming_mosaic.py` - Streaming mode
- `src/dsa110_contimg/imaging/export.py` - PNG conversion

### Tests
- `scripts/test_streaming_mosaic_e2e.py` - End-to-end test

### Documentation
- `docs/reference/LINEARMOSAIC_PARAMETERS.md` - Parameter reference
- `docs/dev/MOSAIC_PB_CORRECTION_FIX.md` - PB fix details
- `docs/dev/FITS_TO_PNG_OPTIMIZATION.md` - PNG optimization details

## Next Steps

1. ✓ PB correction fix implemented
2. ✓ PNG optimization implemented
3. ✓ Automatic PNG generation added to streaming pipeline
4. ✓ Documentation updated
5. ✓ End-to-end testing completed
6. ⏭ Production deployment (when ready)

## Status

**All tasks completed successfully!**

- PB correction fix verified and working
- PNG optimization verified and working
- Both manual and streaming modes tested
- Documentation complete

