# linearmosaic Implementation - Primary Mosaicking Method

## Summary

Refactored mosaicking code to use CASA's `linearmosaic` tool as the **primary/default method**, with `imregrid` + `immath` as the **fallback method**.

## Changes Made

### 1. New Function: `_build_weighted_mosaic_linearmosaic()`

**Location:** `src/dsa110_contimg/mosaic/cli.py:885`

**Purpose:** Primary mosaicking method using CASA's built-in `linearmosaic` tool.

**Features:**
- Uses CASA's `linearmosaic` toolkit tool
- Implements optimal Sault weighting automatically
- Handles PB-weighted combination internally
- Requires PB images for all tiles (raises `MissingPrimaryBeamError` if missing)

**Workflow:**
1. Convert FITS to CASA format if needed
2. Regrid all tiles and PB images to common coordinate system
3. Extract coordinate system parameters from first tile
4. Create `linearmosaic` tool instance
5. Set optimal weighting type
6. Define output image with proper parameters
7. Make mosaic with PB-weighted combination

**API Usage:**
```python
from casatools import linearmosaic

lm = linearmosaic()
lm.setlinmostype('optimal')  # Optimal Sault weighting
lm.defineoutputimage(nx=nx, ny=ny, cellx=cellx, celly=celly, 
                     imagecenter=imagecenter, 
                     outputimage=output_path, 
                     outputweight=weight_path)
lm.makemosaic(images=regridded_tiles, 
              weightimages=regridded_pbs,
              imageweighttype=1,  # PB-corrected images
              weighttype=1)  # PB weight images
```

### 2. Renamed Function: `_build_weighted_mosaic_imregrid_immath()`

**Location:** `src/dsa110_contimg/mosaic/cli.py:1109`

**Purpose:** Fallback mosaicking method using explicit `imregrid` + `immath` tasks.

**Previous Name:** `_build_weighted_mosaic_vast_like()` (renamed to remove VAST reference)

**Features:**
- Explicit control over each step
- Handles PB-weighted and noise-weighted combinations
- More flexible (can work without PB images)
- Used when `linearmosaic` fails or is unavailable

### 3. Updated Wrapper: `_build_weighted_mosaic()`

**Location:** `src/dsa110_contimg/mosaic/cli.py:1444`

**Purpose:** Main entry point that tries `linearmosaic` first, falls back to `imregrid` + `immath`.

**Behavior:**
1. **Try `linearmosaic` first:**
   - Calls `_build_weighted_mosaic_linearmosaic()`
   - If successful, returns immediately

2. **Fallback to `imregrid` + `immath`:**
   - If `linearmosaic` fails with `CASAToolError` or `MissingPrimaryBeamError`
   - If `linearmosaic` fails with `MosaicError` (e.g., regridding issues)
   - Calls `_build_weighted_mosaic_imregrid_immath()`

3. **Error Handling:**
   - If both methods fail, raises `MosaicError` with context from both attempts

## Advantages of linearmosaic

1. **Built-in Optimal Weighting:** Implements optimal Sault weighting automatically
2. **Less Code:** Simpler implementation, fewer steps
3. **CASA Standard:** Uses CASA's recommended tool for linear mosaicking
4. **Automatic Handling:** CASA handles edge cases internally

## Advantages of Fallback Method

1. **Explicit Control:** Can see exactly what's happening at each step
2. **More Flexible:** Can handle cases without PB images
3. **Better Debugging:** Each step is separate and testable
4. **Proven:** Already working implementation

## Testing Recommendations

1. **Test with real data:** Verify `linearmosaic` produces correct mosaics
2. **Test fallback:** Ensure fallback works when PB images are missing
3. **Compare results:** Compare `linearmosaic` vs `imregrid` + `immath` outputs
4. **Error cases:** Test behavior when tiles fail regridding

## Migration Notes

- Old function name `_build_weighted_mosaic_vast_like()` renamed to `_build_weighted_mosaic_imregrid_immath()`
- Main entry point `_build_weighted_mosaic()` now tries `linearmosaic` first
- No changes needed to calling code - same function signature

## Future Considerations

- Could add configuration option to force fallback method
- Could add comparison metrics between methods
- Could optimize `linearmosaic` parameters based on testing

